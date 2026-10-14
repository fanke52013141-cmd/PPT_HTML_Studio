"""A04 rejects plausible but unsupported semantic, source and frame evidence."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import uuid
import wave
import pytest
from html_semantic_qa import prepare,check_frames,validate_verdict,semantic_state,SemanticQAError
import html_semantic_review_service as service
from html_visual_review_service import HtmlReviewDependencies
from html_visual_store import save_scene
from pipeline_lifecycle import write_json_atomic
from database import SessionLocal,Project,LocalJob
from project_model_binding_service import FrozenModel,FrozenProjectModels
from html_semantic_qa_models import SemanticSubmitRequest,SemanticDecisionRequest

ROOT=Path(__file__).resolve().parents[1]


def test_html_tts_completion_uses_actual_semantic_binding_and_never_reveal_builder(case, monkeypatch):
    import tts_service
    monkeypatch.setattr(tts_service, "run_subprocess_bounded", lambda *a, **kw: pytest.fail("HTML must not build raster reveal timeline"))
    before = (case.run/"planning/html_visual/scene-token-03.json").read_bytes()
    result = tts_service._run_bind_reveal_timeline(SimpleNamespace(visual_backend="html", run_dir=str(case.run)))
    assert result.returncode == 0
    evidence = json.loads(result.stdout)
    assert evidence["pages"][0]["clock"] == "audio_timeline" and not evidence["author_written"]
    assert (case.run/"planning/html_visual/scene-token-03.json").read_bytes() == before


def test_html_tts_completion_rejects_mismatched_audio_source(case):
    import tts_service
    timeline = copy.deepcopy(case.timeline)
    timeline["segments"][0]["text"] = "unrelated audio"
    write_json_atomic(case.run/"slides/token-03/audio_timeline.json", timeline)
    result = tts_service._run_bind_reveal_timeline(SimpleNamespace(visual_backend="html", run_dir=str(case.run)))
    assert result.returncode == 1 and "HTML_AUDIO_BINDING_INVALID" in result.stderr


def test_course_real_adapter_checks_saved_plan_and_preserves_mismatched_manual_scene(case):
    from html_course_runtime import CourseActions
    from html_course_jobs import CourseBoundary
    actions = CourseActions(SimpleNamespace(repo_root=ROOT))
    project = SimpleNamespace(run_dir=str(case.run))
    assert actions.scene_ready(project, case.contract)
    path = case.run/"planning/html_visual/plan-token-03.json"
    plan = copy.deepcopy(case.plan); plan["beats"][0]["spoken_text"] = "unrelated manual source"
    write_json_atomic(path, plan)
    before = (case.run/"planning/html_visual/scene-token-03.json").read_bytes()
    with pytest.raises(CourseBoundary):
        actions.scene_ready(project, case.contract)
    assert (case.run/"planning/html_visual/scene-token-03.json").read_bytes() == before


def test_course_adapter_does_not_reuse_storyboard_after_article_update(case):
    import os
    from artifact_fingerprint import sha256_file
    from html_course_runtime import CourseActions
    actions = CourseActions(SimpleNamespace(repo_root=ROOT))
    project = SimpleNamespace(run_dir=str(case.run))
    source = case.run/"inputs/article.md"; source.parent.mkdir(); source.write_text("original article", encoding="utf-8")
    os.utime(source, (1, 1))
    contract = case.run/"planning/visual_contract.json"
    write_json_atomic(case.run/"planning/visual_contract.validation.json", {"valid": True, "contract_sha256": sha256_file(contract)})
    assert actions.contract(project)["slides"][0] == case.contract
    source.write_text("changed article", encoding="utf-8")
    os.utime(source, (contract.stat().st_mtime+1, contract.stat().st_mtime+1))
    assert actions.contract(project) is None


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@pytest.fixture
def case(tmp_path):
    fixture=ROOT/"html_engine/visual/fixtures/presentation-details"
    scene=read(fixture/"scene.json");binding=read(fixture/"binding.json");contract=read(fixture/"contract.json")
    plan=read(ROOT/"docs/plans/html-backend-development/evidence/a02-model-smoke-2026-10-13.json")["plan"]
    base=tmp_path/"planning/html_visual";base.mkdir(parents=True)
    save_scene(tmp_path,scene["id"],scene,0)
    write_json_atomic(base/f"plan-{scene['id']}.json",plan)
    write_json_atomic(base/f"binding-{scene['id']}.json",binding)
    write_json_atomic(tmp_path/"planning/visual_contract.json",{"slides":[contract]})
    audio=tmp_path/"slides"/scene["id"];audio.mkdir(parents=True)
    (audio/"tts_text.txt").write_text("".join(b["spoken_text"] for b in plan["beats"]),encoding="utf-8")
    # A decoded local silent fixture, explicitly not a speech-provider experiment.
    with wave.open(str(audio/"voice.mp3"),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b"\0\0"*16000*8)
    write_json_atomic(audio/"tts_metadata.json",{"fixture":"silent_audio_not_speech"})
    (audio/"subtitles.srt").write_text("fixture",encoding="utf-8")
    timeline={"duration_sec":8,"audio_content_duration_sec":8,"segments":[{"id":b["id"],"beat_id":b["id"],"start":i*2,"end":(i+1)*2,"text":b["spoken_text"]} for i,b in enumerate(plan["beats"])]}
    write_json_atomic(audio/"audio_timeline.json",timeline)
    return SimpleNamespace(run=tmp_path,scene=scene,plan=plan,binding=binding,contract=contract,timeline=timeline,slide=scene["id"])


def prepared(case):
    return prepare(case.scene,case.plan,case.binding,case.contract,case.timeline)


def good(beat):
    return {"verdict":"related","confidence":0.95,"evidence":[{"frameIndex":2,"targetId":beat["objects"][0]["id"],"observation":"fixture observation"}]}


def test_actual_audio_windows_and_action_identity(case):
    data=prepared(case)
    assert data["beats"][0]["times"]==[0,1000,1999]
    assert data["beats"][-1]["times"]==[6000,7000,7999]
    assert {a["actionId"] for a in data["bound_scene"]["motion"]}==set(case.binding["actions"])
    assert case.scene["durationMs"]!=data["bound_scene"]["durationMs"]


@pytest.mark.parametrize("mutation",["spoken","action","target","order"])
def test_source_tampering_rejected(case,mutation):
    if mutation=="spoken":case.plan["beats"][0]["spoken_text"]="changed speech"
    elif mutation=="action":case.binding["actions"][next(iter(case.binding["actions"]))]["beatId"]=case.plan["beats"][-1]["id"]
    elif mutation=="target":case.scene["nodes"][1]["id"]="invented"
    else:case.timeline["segments"].reverse()
    with pytest.raises(Exception):prepared(case)


def test_coverage_end_visibility_and_no_start_false_positive(case):
    data=prepared(case)
    frames=[{"beatId":b["id"],"frameIndex":i,"timeMs":t,"visible":{n["id"]:0 if i==0 else 1 for n in case.scene["nodes"]}} for b in data["beats"] for i,t in enumerate(b["times"])]
    assert check_frames(data,frames)==[]
    frames[2]["visible"][data["beats"][0]["expectedState"][0]["objectId"]]=0
    assert check_frames(data,frames)[0]["code"]=="SEMANTIC_TARGET_NOT_VISIBLE"
    with pytest.raises(SemanticQAError):check_frames(data,frames[:-1])


@pytest.mark.parametrize("change",["unknown_target","unknown_frame","no_evidence","fake_pass","nan"])
def test_unsupported_model_claims_cannot_pass(case,change):
    beat=prepared(case)["beats"][0];result=good(beat)
    if change=="unknown_target":result["evidence"][0]["targetId"]="figure-focus-guess"
    elif change=="unknown_frame":result["evidence"][0]["frameIndex"]=3
    elif change=="no_evidence":result["evidence"]=[]
    elif change=="fake_pass":result["passed"]=True
    else:result["confidence"]=float("nan")
    with pytest.raises(ValueError):validate_verdict(result,beat)


def test_semantic_negative_and_low_confidence_are_distinct(case):
    result=good(prepared(case)["beats"][0]);result["verdict"]="omitted"
    assert semantic_state([result])=="failed"
    result["verdict"]="related";result["confidence"]=0.79
    assert semantic_state([result])=="needs_review"


@pytest.fixture
def audited(case):
    inputs=service.source(case.run,case.slide,ROOT);calls=[]
    def generator(**kwargs):
        calls.append(kwargs)
        assert len(kwargs["image_paths"])==3 and kwargs["request_timeout"]==600
        user=json.loads(kwargs["user_prompt"])
        return {"verdict":"related","confidence":0.95,"evidence":[{"frameIndex":2,"targetId":user["objects"][0]["id"],"observation":"fixture observation"}]}
    deps=HtmlReviewDependencies(ROOT,generator)
    result=service.review(case.run,case.slide,inputs,{"model":"fixture","config_hash":"f"},deps=deps,generator=generator)
    return case,inputs,result,deps,generator,calls


def test_three_actual_frames_per_beat_and_separate_manual_decision(audited):
    case,inputs,result,deps,generator,calls=audited
    assert len(calls)==4
    current=service.status(case.run,case.slide,ROOT)
    assert current["engineering"]=="passed" and current["semantic"]=="passed"
    assert current["human"]=="pending" and current["audio"]=="pending" and not current["valid"]
    decision=SemanticDecisionRequest(expected_revision=inputs["revision"],report_key=result["key"],decision="approved",note="isolated fixture human decision")
    assert service.decide(case.run,case.slide,decision,ROOT)["valid"]
    service.review(case.run,case.slide,inputs,{"model":"fixture","config_hash":"f"},deps=deps,generator=generator)
    assert len(calls)==4, "known captured frames and returned responses must be reused"


@pytest.mark.parametrize("what",["frame","report","input","response"])
def test_evidence_tampering_and_changed_inputs_block_completion(audited,what):
    case,_,result,_,_,_=audited;directory=service.folder(case.run,case.slide)/result["key"]
    if what=="frame":(directory/"frames/beat-0-1.png").unlink()
    elif what=="report":
        report=read(directory/"report.json");report["semantic"]="failed";write_json_atomic(directory/"report.json",report)
    elif what=="input":
        timeline=copy.deepcopy(case.timeline);timeline["duration_sec"]=9;write_json_atomic(case.run/"slides"/case.slide/"audio_timeline.json",timeline)
    else:
        receipt=read(directory/"beat-0.json");receipt["response"]["confidence"]=0.2;write_json_atomic(directory/"beat-0.json",receipt)
    assert not service.status(case.run,case.slide,ROOT)["valid"]


def test_unknown_request_never_blindly_repeats(case):
    inputs=service.source(case.run,case.slide,ROOT);calls=[]
    def generator(**kw):calls.append(kw);raise TimeoutError("unknown")
    deps=HtmlReviewDependencies(ROOT,generator)
    for _ in range(2):
        with pytest.raises(SemanticQAError,match="EXTERNAL_OUTCOME_UNKNOWN"):
            service.review(case.run,case.slide,inputs,{"model":"fixture"},deps=deps,generator=generator)
    assert len(calls)==1


def test_persistent_job_freezes_model_and_preserves_negative_semantic_result(case):
    from html_semantic_review_jobs import SemanticReviewJobs
    model=FrozenModel("test","original-model",None,"fake","test",None,"h",max_tokens=4096)
    calls=[]
    class Capture:
        def submit(self,*args):calls.append(args)
    captured=[]
    def reviewer(*args,**kwargs):
        captured.append(kwargs["generator"].keywords["model_binding"].model)
        kwargs["progress"]({"completed_beats":4,"total_beats":4})
        return {"stage":"semantic_review","semantic":"failed","human":"pending"}
    jobs=SemanticReviewJobs(SessionLocal,HtmlReviewDependencies(ROOT,lambda **kw:None),executor=Capture(),freeze_models=lambda *a,**kw:FrozenProjectModels(0,model,model),reviewer=reviewer)
    project=Project(id="sem-"+uuid.uuid4().hex,name="isolated",account_id="default",visual_backend="html",run_dir=str(case.run))
    db=SessionLocal()
    try:
        db.add(project);db.commit();request=SemanticSubmitRequest(expected_revision=1)
        task=jobs.submit(db,project,case.slide,request)
        assert jobs.submit(db,project,case.slide,request)["reused"] and len(calls)==1
        jobs.freeze=lambda *a,**kw:pytest.fail("worker must use frozen model")
        args=calls[0];args[0](*args[1:]);db.expire_all()
        job=db.query(LocalJob).filter(LocalJob.id==task["id"]).one()
        assert job.status=="succeeded" and job.get_payload()["result"]["semantic"]=="failed"
        assert captured==["original-model"] and job.error is None
    finally:db.close()


def test_public_schemas_and_cli_are_registered():
    from agent_contract.capabilities import get_capability
    from cli.pptctl import build_parser
    for action in ("submit","status","decision"):
        assert get_capability("html_semantic."+action).mcp_tool_name=="ppt_html_semantic_"+action
    values=build_parser().parse_args(["html","semantic-submit","--project","p","--slide","s","--file","request.json"])
    assert values.capability_id=="html_semantic.submit"


def test_semantic_scene_cannot_downgrade_to_legacy_skip(case):
    path=case.run/f"planning/html_visual/scene-{case.slide}.json"
    changed=copy.deepcopy(case.scene);changed["version"]="0.5.0"
    write_json_atomic(path,changed)
    current=service.status(case.run,case.slide,ROOT)
    assert current["required"] and not current["valid"]


def test_video_gate_includes_semantic_but_static_pptx_remains_independent(case,monkeypatch):
    import html_creation_workflow as flow
    monkeypatch.setattr(flow,"html_readiness",lambda *a:{"ready":True,"issues":[]})
    monkeypatch.setattr(flow,"_audio_state",lambda *a:("ready","confirmed",[],{"confirmed":True}))
    monkeypatch.setattr(flow,"_validate_slide_binding",lambda *a:[])
    monkeypatch.setattr(flow,"_digital_human_state",lambda *a:("skipped",[],False))
    video=flow.target_readiness(case.run,ROOT,[case.slide],"video")
    assert not video["ready"] and any(i["code"]=="SEMANTIC_QA_REQUIRED" for i in video["issues"])
    assert flow.target_readiness(case.run,ROOT,[case.slide],"pptx")["ready"]


def test_web_and_agent_share_dispatch_and_account_gate(monkeypatch):
    import html_visual_review_routes as web
    import agent_api.routes as agent
    calls=[]
    def dispatch(mode,*args):calls.append(mode);return {"success":True,"semantic_qa":{}}
    monkeypatch.setattr(web,"_semantic_dispatch",dispatch)
    monkeypatch.setattr(agent,"_html_project_or_404",lambda *a:object())
    agent.agent_semantic_status("p","s",None)
    agent.agent_semantic_submit("p","s",SemanticSubmitRequest(expected_revision=1),None)
    assert calls==["status","submit"]
    def forbidden(*args):raise PermissionError("account")
    monkeypatch.setattr(agent,"_html_project_or_404",forbidden)
    with pytest.raises(PermissionError):agent.agent_semantic_status("p","s",None)


def test_persistent_unknown_outcome_blocks_submit_and_cancelled_job_never_restarts(case):
    from html_semantic_review_jobs import SemanticReviewJobs
    import html_task_store as task_store
    model=FrozenModel("test","model",None,"fake","test",None,"h")
    class Capture:
        def submit(self,*args):self.args=args
    executor=Capture()
    calls=[]
    def reviewer(*args,**kwargs):
        calls.append(1);kwargs["receipt_event"](0,{"state":"intent","request_key":"missing-upstream-reply"})
        raise SemanticQAError("SEMANTIC_EXTERNAL_OUTCOME_UNKNOWN")
    jobs=SemanticReviewJobs(SessionLocal,HtmlReviewDependencies(ROOT,lambda **kw:None),executor=executor,freeze_models=lambda *a,**kw:FrozenProjectModels(0,model,model),reviewer=reviewer)
    project=Project(id="sem-stop-"+uuid.uuid4().hex,name="isolated",account_id="default",visual_backend="html",run_dir=str(case.run))
    db=SessionLocal()
    try:
        db.add(project);db.commit();request=SemanticSubmitRequest(expected_revision=1)
        task=jobs.submit(db,project,case.slide,request)
        args=executor.args;args[0](*args[1:])
        db.expire_all();job=db.query(LocalJob).filter(LocalJob.id==task["id"]).one()
        assert job.status=="failed" and task_store.recovery_action(job)["requires_verification"]
        with pytest.raises(task_store.HtmlTaskError,match="EXTERNAL_OUTCOME_UNKNOWN"):
            jobs.submit(db,project,case.slide,request)
        assert len(calls)==1
        job.status="cancelled";db.commit()
        with pytest.raises(task_store.HtmlTaskError):jobs.submit(db,project,case.slide,request)
    finally:db.close()


def test_uncertain_can_only_be_resolved_by_explicit_current_human_note(audited):
    case,_,result,_,_,_=audited
    directory=service.folder(case.run,case.slide)/result["key"]
    from html_semantic_qa import seal
    report=read(directory/"report.json")
    for i,beat in enumerate(report["beats"]):
        beat["result"]["verdict"]="uncertain";beat["result"]["confidence"]=0.6
        receipt=read(directory/f"beat-{i}.json");receipt["response"]=beat["result"]
        write_json_atomic(directory/f"beat-{i}.json",seal({k:v for k,v in receipt.items() if k!="sha256"}))
    report["semantic"]="needs_review"
    write_json_atomic(directory/"report.json",seal({k:v for k,v in report.items() if k!="sha256"}))
    current=service.status(case.run,case.slide,ROOT)
    assert current["semantic"]=="needs_review" and not current["valid"]
    decision=SemanticDecisionRequest(expected_revision=1,report_key=result["key"],decision="approved",note="explicit fixture review resolves uncertain evidence")
    assert service.decide(case.run,case.slide,decision,ROOT)["valid"]
