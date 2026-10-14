"""A05 persistent coordinator faults; stage providers are explicit local doubles."""
import copy
import json
import uuid
from concurrent.futures import Future
from types import SimpleNamespace
import pytest
from database import SessionLocal, Project, LocalJob
from html_course_jobs import HtmlCourseJobs, CourseBoundary
from html_task_store import HtmlTaskError


class Executor:
    def submit(self, fn, *args):
        self.work = (fn, args)
        self.future = Future()
        return self.future

    def finish(self):
        fn, args = self.work
        fn(*args)
        self.future.set_result(None)


class Actions:
    def __init__(self):
        self.input_version = 1
        self.doc = {"slides": [{"slide_id": "page-1"}, {"slide_id": "page-2"}, {"slide_id": "page-3"}]}
        self.scenes = set()
        self.calls = []
        self.audio = False
        self.qa = {}
        self.approval = False
        self.output_valid = True
        self.design = False
        self.break_child = False

    def identity(self, project):
        return {"input": self.input_version}

    def contract(self, project):
        return copy.deepcopy(self.doc)

    def check_contract(self, project, frozen):
        if frozen and frozen != self.doc:
            raise CourseBoundary("paused", "storyboard", "source changed")

    def storyboard(self, db, project):
        self.calls.append("storyboard")
        self.doc = {"slides": [{"slide_id": "page-1"}]}

    def scene_ready(self, project, slide):
        return slide["slide_id"] in self.scenes

    def create(self, db, project, name, result=None):
        self.calls.append(name)
        job = LocalJob(id="child_"+uuid.uuid4().hex, project_id=project.id, job_type="fixture_child", status="succeeded", stage="completed", payload_json=json.dumps({"result": result or {}}))
        db.add(job); db.commit()
        return {"id": job.id}

    def produce(self, db, project, slide):
        sid = slide["slide_id"]
        if not self.design:
            self.scenes.add(sid)
        return self.create(db, project, "html:"+sid, {"stage": "design_review" if self.design else "saved", "slide_id": sid})

    def latest_page(self, db, project, sid):
        return None

    def narration(self, db, project):
        self.calls.append("narration")

    def audio_ready(self, project, contract):
        return self.audio

    def tts(self, db, project):
        self.audio = True
        return self.create(db, project, "tts")

    def semantic_status(self, project, sid):
        return self.qa.get(sid, {"semantic": "stale_or_missing"})

    def semantic(self, db, project, sid):
        self.qa[sid] = {"engineering": "passed", "semantic": "passed", "human": "pending"}
        return self.create(db, project, "semantic:"+sid)

    def approved(self, project, contract):
        return self.approval

    def render(self, db, project):
        return self.create(db, project, "render")

    def child(self, db, project, job_id):
        if self.break_child:
            self.break_child = False
            raise CourseBoundary("paused", "html_pages", "injected interruption")
        job = db.query(LocalJob).filter(LocalJob.id == job_id).one()
        return {"id": job.id, "status": job.status, "result": job.get_payload().get("result"), "can_resume": job.status == "interrupted"}

    def resume_child(self, db, project, job_id):
        self.calls.append("resume:"+job_id)
        job = db.query(LocalJob).filter(LocalJob.id == job_id).one()
        self.scenes.add(job.get_payload()["result"]["slide_id"])
        job.status = "succeeded"; db.commit()

    def completed(self, project, output):
        return self.output_valid and self.approval


@pytest.fixture
def course(tmp_path):
    with SessionLocal() as db:
        project = Project(id=uuid.uuid4().hex, name="isolated A05", account_id="default", visual_backend="html", run_dir=str(tmp_path))
        db.add(project); db.commit(); db.refresh(project); db.expunge(project)
    actions, executor = Actions(), Executor()
    jobs = HtmlCourseJobs(SessionLocal, actions, executor, poll_seconds=0)
    return SimpleNamespace(project=project, actions=actions, executor=executor, jobs=jobs)


def finish(c):
    result = c.jobs.start(c.project)
    c.executor.finish()
    return result["status"]["job_id"], c.jobs.status(c.project)["status"]


def test_whole_course_stops_for_current_approvals_then_reuses_all_children(course):
    c = course
    job_id, status = finish(c)
    assert status["status"] == "waiting_for_review" and status["current_stage"] == "approvals"
    assert "render" not in c.actions.calls
    assert len(status["children"]) == 7  # three HTML, TTS, three semantic tasks
    assert all(v["human"] == "pending" for v in c.actions.qa.values())
    child_calls = [x for x in c.actions.calls if x != "narration"]
    c.actions.approval = True
    resumed_id, status = finish(c)
    assert resumed_id == job_id and status["status"] == "completed"
    assert [x for x in c.actions.calls if x != "narration"] == child_calls + ["render"]
    assert c.jobs.start(c.project)["status"]["job_id"] == job_id


def test_design_confirmation_never_automatically_reconstructs(course):
    c = course; c.actions.design = True
    _, state = finish(c)
    assert state["status"] == "waiting_for_review" and state["slide_id"] == "page-1"
    assert c.actions.calls == ["html:page-1"]
    # Explicit external per-page confirmation changes its actual saved state.
    c.actions.scenes.add("page-1")
    _, state = finish(c)
    assert state["slide_id"] == "page-2"
    assert c.actions.calls == ["html:page-1", "html:page-2"]


def test_new_scheduler_instance_recovers_same_parent_and_child_ids(course):
    c = course; c.actions.break_child = True
    job_id, state = finish(c)
    child_id = state["children"]["html:page-1"]["id"]
    c.actions.scenes.discard("page-1")
    with SessionLocal() as db:
        parent = db.query(LocalJob).filter(LocalJob.id == job_id).one(); parent.status = "running"
        child = db.query(LocalJob).filter(LocalJob.id == child_id).one(); child.status = "interrupted"
        db.commit()
    c.executor = Executor(); c.jobs = HtmlCourseJobs(SessionLocal, c.actions, c.executor, 0)
    assert c.jobs.status(c.project)["status"]["status"] == "interrupted"
    new_id, status = finish(c)
    assert new_id == job_id and status["children"]["html:page-1"]["id"] == child_id
    assert c.actions.calls.count("html:page-1") == 1
    assert c.actions.calls.count("resume:"+child_id) == 1


def test_unknown_child_submit_window_does_not_create_replacement(course):
    c = course
    original = c.actions.produce
    def dropped(db, project, slide):
        original(db, project, slide)
        raise RuntimeError("lost child submission reply")
    c.actions.produce = dropped
    _, state = finish(c)
    assert state["status"] == "failed"
    assert state["children"]["html:page-1"]["state"] == "intent"
    with pytest.raises(HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        c.jobs.start(c.project)
    assert c.actions.calls == ["html:page-1"]


def test_unknown_storyboard_not_reissued(course):
    c = course; c.actions.doc = None
    def unknown(*args):
        c.actions.calls.append("storyboard")
        raise RuntimeError("supplier unknown")
    c.actions.storyboard = unknown
    _, state = finish(c)
    assert state["status"] == "failed"
    with pytest.raises(HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        c.jobs.start(c.project)
    assert c.actions.calls == ["storyboard"]


def test_semantic_failure_blocks_approval_and_render(course):
    c = course
    c.actions.scenes = {s["slide_id"] for s in c.actions.doc["slides"]}; c.actions.audio = True; c.actions.approval = True
    c.actions.qa["page-1"] = {"engineering": "passed", "semantic": "failed"}
    _, state = finish(c)
    assert state["status"] == "failed" and state["current_stage"] == "semantic"
    assert "render" not in c.actions.calls


def test_pause_boundary_and_current_content_create_distinct_version(course):
    c = course
    result = c.jobs.start(c.project)
    old_id = result["status"]["job_id"]
    c.jobs.pause(c.project); c.executor.finish()
    assert c.jobs.status(c.project)["status"]["status"] == "paused"
    assert not c.actions.calls
    c.actions.input_version += 1
    result = c.jobs.start(c.project)
    assert result["status"]["job_id"] != old_id
    c.executor.finish()


def test_changed_order_is_stale_and_new_course_preserves_scenes(course):
    c = course
    old_id, _ = finish(c)
    c.actions.doc["slides"].reverse()
    assert c.jobs.status(c.project)["status"]["historical"]
    new_id, _ = finish(c)
    assert new_id != old_id
    assert len([x for x in c.actions.calls if x.startswith("html:")]) == 3


def test_completed_output_revalidated_and_cancelled_parent_never_revives(course):
    c = course; c.actions.approval = True
    job_id, _ = finish(c)
    c.actions.output_valid = False
    assert c.jobs.status(c.project)["status"]["historical"]
    with pytest.raises(HtmlTaskError, match="输出或签收"):
        c.jobs.start(c.project)
    with SessionLocal() as db:
        job = db.query(LocalJob).filter(LocalJob.id == job_id).one(); job.status = "cancelled"; db.commit()
    with pytest.raises(HtmlTaskError, match="已取消"):
        c.jobs.start(c.project)


def test_shared_one_click_routes_html_and_keeps_manual_guard(course, monkeypatch):
    import one_click_orchestrator as orchestrator
    import html_course_runtime
    monkeypatch.setattr(html_course_runtime, "_jobs", course.jobs)
    result = orchestrator.start_one_click(course.project)
    assert result["status"]["backend"] == "html"
    orchestrator.pause_one_click(course.project); course.executor.finish()
    assert orchestrator.get_one_click_status(course.project)["status"]["status"] == "paused"
    course.project.ai_mode = "manual"
    with pytest.raises(orchestrator.ManualModeOneClickError):
        orchestrator.start_one_click(course.project)


@pytest.mark.parametrize("payload", [{"mode": "restart"}, {"start_from": "render"}])
def test_no_arbitrary_restart_or_stage_bypass(course, payload):
    with pytest.raises(HtmlTaskError):
        course.jobs.start(course.project, payload)


def test_course_and_child_ids_survive_actual_python_process_restart(tmp_path):
    import os
    import sys
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PPT_STUDIO_DB_PATH"] = str(tmp_path/"isolated.db")
    env["PPT_STUDIO_RUNS_DIR"] = str(tmp_path/"runs")
    code = r'''
import sys,json,uuid
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/"checks"))
from test_html_course_jobs import Actions,Executor
from html_course_jobs import HtmlCourseJobs
from database import init_db,SessionLocal,Project,LocalJob
init_db()
statefile=Path(sys.argv[2]);phase=sys.argv[1]
actions=Actions();executor=Executor()
if phase=="crash":
    with SessionLocal() as db:
        p=Project(id=uuid.uuid4().hex,name="process isolated course",account_id="default",visual_backend="html",run_dir=str(statefile.parent/"runs"))
        db.add(p);db.commit();db.refresh(p);db.expunge(p)
    def exit_during_child(*args):raise SystemExit("injected process loss")
    actions.child=exit_during_child
else:
    state=json.loads(statefile.read_text())
    actions.scenes=set(state["scenes"]);actions.calls=state["calls"];actions.audio=state["audio"];actions.qa=state["qa"]
    with SessionLocal() as db:
        p=db.query(Project).filter(Project.id==state["project_id"]).one();db.expunge(p)
    if phase=="approve":actions.approval=True
jobs=HtmlCourseJobs(SessionLocal,actions,executor,0)
prior=jobs.status(p)["status"]
submitted=jobs.start(p)
try:executor.finish()
except SystemExit:pass
with SessionLocal() as db:
    parent=db.query(LocalJob).filter(LocalJob.id==submitted["status"]["job_id"]).one()
    if phase=="crash":
        child_id=parent.get_payload()["children"]["html:page-1"]["id"]
        child=db.query(LocalJob).filter(LocalJob.id==child_id).one();child.status="interrupted";db.commit()
        actions.scenes.discard("page-1")
    state={"project_id":p.id,"job_id":parent.id,"parent_status":parent.status,"children":parent.get_payload()["children"],"prior_status":prior["status"],"scenes":list(actions.scenes),"calls":actions.calls,"audio":actions.audio,"qa":actions.qa}
statefile.write_text(json.dumps(state))
print(json.dumps(state))
'''
    states = []
    for phase in ("crash", "resume", "approve"):
        result = subprocess.run([sys.executable, "-c", code, phase, str(tmp_path/"state.json")], cwd=root, env=env, capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stderr
        states.append(json.loads(result.stdout.splitlines()[-1]))
    first, second, final = states
    assert first["parent_status"] == "running"
    assert second["prior_status"] == "interrupted" and second["parent_status"] == "waiting_for_review"
    assert final["parent_status"] == "succeeded"
    assert len({s["job_id"] for s in states}) == 1
    assert first["children"]["html:page-1"]["id"] == final["children"]["html:page-1"]["id"]
    for name in ("html:page-1", "html:page-2", "html:page-3", "tts", "semantic:page-1", "semantic:page-2", "semantic:page-3", "render"):
        assert final["calls"].count(name) == 1


def test_agent_html_checkpoints_reference_real_stage_entrypoints_and_refuse_generic_approval(course, monkeypatch):
    from agent_api import routes
    from agent_contract.models import CheckpointListResult, CheckpointApproveRequest
    from agent_contract.capabilities import CAPABILITIES
    from agent_api.errors import ValidationFailedError
    monkeypatch.setattr(routes, "_resolve_project", lambda *args: course.project)
    listing = routes.agent_list_checkpoints(course.project.id, None)
    model = CheckpointListResult.model_validate(listing)
    assert model.approval_mode == "existing_stage_endpoints"
    ids = {c.id for c in CAPABILITIES}
    assert all(c.capability in ids for c in model.checkpoints if c.capability)
    assert model.checkpoints[2].web_path.endswith("/steps/7/confirm")
    with pytest.raises(ValidationFailedError, match="通用checkpoint"):
        routes.agent_approve_checkpoint(course.project.id, "image_review", CheckpointApproveRequest(checkpoint="image_review", approved=True), None)


def test_web_html_one_click_preserves_image_backend_flags(course, monkeypatch):
    import one_click_routes as routes
    p = course.project; p.presentation_mode = "reveal"; p.mask_enabled = 1
    monkeypatch.setattr(routes, "_project_or_404", lambda *a: p)
    monkeypatch.setattr(routes, "get_config_value", lambda *a: False)
    monkeypatch.setattr(routes, "start_one_click", lambda *a: {"success": True, "status": {"backend": "html"}})
    db = SimpleNamespace(commit=lambda: None, refresh=lambda p: None)
    assert routes.start_one_click_route(p.id, {}, db)["status"]["backend"] == "html"
    assert p.presentation_mode == "reveal" and p.mask_enabled == 1


def test_html_source_storyboard_uses_frozen_planning_model_and_enabled_reasoning(course, monkeypatch):
    import storyboard_service
    import storyboard_project_config
    import project_model_binding_service
    from project_model_binding_service import FrozenModel, FrozenProjectModels
    model = FrozenModel(source="fixed", connection_id="fixture-planning", provider="zhipu", model="glm-5.3", endpoint="https://example.test/v4", api_key="fixture-secret", config_hash="fixture", max_tokens=64000, temperature=1.0, reasoning_effort="max")
    vision = FrozenModel(source="fixed", connection_id="fixture-vision", provider="zhipu", model="glm-5.3-flash", endpoint="https://example.test/v4", api_key="fixture-secret", config_hash="fixture-vision")
    monkeypatch.setattr(project_model_binding_service, "freeze_project_models", lambda *a, **kw: FrozenProjectModels(1, vision, vision, model))
    config, options = storyboard_project_config.resolve_html_step2_llm(course.project)
    assert config[2:] == ("glm-5.3", 1.0, 64000)
    assert options["extra_body"]["thinking"]["type"] == "enabled" and options["reasoning_effort"] == "max"
    captured = {}
    monkeypatch.setattr(storyboard_service, "_DEPENDENCIES", object())
    monkeypatch.setattr(storyboard_service, "execute_step2_json_llm", lambda **kw: captured.update(kw) or {})
    storyboard_service.run_step2_json_llm(project=course.project, system_prompt="fixture", user_prompt="fixture", artifact_prefix="step2_script_plan", schema_hint="fixture", trace_id="fixture")
    assert captured["llm_config"] == config and captured["vendor_options"] == options
    assert captured["timeout_sec"] == 600


def test_missing_image_preflight_waits_without_unknown_child_and_can_continue(course):
    c = course
    def missing(project, sid):
        raise CourseBoundary("waiting_for_user", "html_pages", "image connection required", sid)
    c.actions.preflight_page = missing
    job_id, state = finish(c)
    assert state["status"] == "waiting_for_user" and not state["children"]
    assert not c.actions.calls
    c.actions.preflight_page = lambda *args: None
    resumed_id, state = finish(c)
    assert resumed_id == job_id and state["status"] == "waiting_for_review"
