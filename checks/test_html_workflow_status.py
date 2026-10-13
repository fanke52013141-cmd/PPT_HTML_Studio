"""S07 project isolation, original request recovery and version display."""
import json
from pathlib import Path
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import SessionLocal, LocalJob, Project
from repository_paths import RUNS_DIR
import html_task_store as store
from html_workflow_jobs import HtmlWorkflowJobs
from html_visual_review_service import HtmlReviewDependencies
from artifact_fingerprint import sha256_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case(tmp_path):
    db = SessionLocal()
    pid = "s07-" + uuid.uuid4().hex
    project = Project(id=pid, name="S07", account_id="default",
                      visual_backend="html", run_dir=str(Path(RUNS_DIR) / pid))
    db.add(project)
    db.commit()
    planning = Path(project.run_dir) / "planning"
    planning.mkdir(parents=True)
    (planning / "visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": "s1"}]}), encoding="utf-8")
    from html_build_snapshot import create_generation_snapshot
    frozen = create_generation_snapshot(project.run_dir, {"slide_id": "s1"}, repo_root=ROOT)
    task = store.submit_task(db, project_id=project.id, task_type="html_plan_generate",
                             submission_key=uuid.uuid4().hex,
                             payload={"slide_id": "s1", "snapshot_id": frozen["snapshot_id"], "source_revision": 0,
                                      "contract_sha256": sha256_json({"slide_id": "s1"})})
    yield db, project, db.get(LocalJob, task["id"])
    db.close()


def test_shared_task_status_is_project_scoped_and_not_approval(case, monkeypatch):
    import html_visual_review_routes as web
    import agent_api.routes as agent
    db, project, job = case
    monkeypatch.setattr(web, '_jobs', HtmlWorkflowJobs(SessionLocal,
        HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **_: {}),
        executor=SimpleNamespace(submit=lambda *args: None)))
    app = FastAPI()
    app.include_router(web.router)
    app.include_router(agent.router)
    app.dependency_overrides[web._get_db] = lambda: db
    app.dependency_overrides[agent.get_db] = lambda: db
    store.mark_running(db, job.id)
    store.mark_succeeded(db, job.id, {"stage": "design_review", "saved": {"changed": False}})
    with TestClient(app) as client:
        suffix = f"/projects/{project.id}/html-review/tasks/{job.id}"
        first = client.get("/api" + suffix)
        second = client.get("/api/agent/v1" + suffix)
        assert first.status_code == second.status_code == 200
        assert first.json()["task"] == second.json()["task"]
        assert first.json()["task"]["stage"] == "design_review"
        assert first.json()["task"]["input_state"] == "current"
        current_suffix = f"/projects/{project.id}/html-review/s1/task/current"
        assert client.get('/api' + current_suffix).json()['task'] == first.json()['task']
        assert client.get('/api/agent/v1' + current_suffix).json()['task'] == first.json()['task']
        web_resume = client.post('/api' + suffix + '/resume', json={})
        agent_resume = client.post('/api/agent/v1' + suffix + '/resume', json={})
        assert web_resume.status_code == agent_resume.status_code == 200
        assert web_resume.json()['task'] == agent_resume.json()['task']
        assert web_resume.json()['task']['input_state'] == 'current'
        assert web_resume.json()['task']['reused'] is True
        other = Project(id="s07-other-" + uuid.uuid4().hex, name="Other", account_id="default",
                        visual_backend="html", run_dir=str(Path(project.run_dir) / "other"))
        db.add(other)
        db.commit()
        assert client.get(f"/api/projects/{other.id}/html-review/tasks/{job.id}").status_code == 404
    summaries = store.recent_task_summaries(db, project.id, run_dir=project.run_dir)
    assert summaries[0]["slide_id"] == "s1"
    assert "result" not in summaries[0] and "submission_key" not in summaries[0]


@pytest.mark.parametrize("status,stages,attempt", [
    ("cancelled", {}, 1), ("failed", {"image:x": {"state": "unknown"}}, 1),
    ("interrupted", {}, 3),
])
def test_resume_refuses_cancel_unknown_and_exhausted(case, status, stages, attempt):
    db, project, job = case
    job.status = status
    payload = job.get_payload()
    payload.update(attempt=attempt, production_stages=stages)
    job.payload_json = store.json_dumps(payload)
    db.commit()
    service = HtmlWorkflowJobs(SessionLocal, HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **_: {}))
    with pytest.raises(store.HtmlTaskError) as error:
        service.resume(db, project, job)
    assert error.value.status_code == 409
    assert not store.task_view(job, project.run_dir)["recovery"]["can_resume"]


def test_resume_preserves_frozen_design_options_and_reuses_active(case, monkeypatch):
    import html_build_snapshot as snapshots
    db, project, job = case
    service = HtmlWorkflowJobs(SessionLocal, HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **_: {}))
    # A repeated click on an active task cannot schedule another worker.
    assert service.resume(db, project, job)["id"] == job.id
    job.status = "interrupted"
    payload = job.get_payload()
    payload["input"]["snapshot_id"] = "a" * 64
    job.payload_json = store.json_dumps(payload)
    db.commit()
    folder = Path(project.run_dir) / ("planning/html_visual/builds/" + "a" * 64)
    (folder / "input").mkdir(parents=True)
    contract = {"slide_id": "s1"}
    options = {"design_candidate_key": "b" * 64, "asset_instruction": "简化轮廓"}
    for file, data in ((folder / "input/contract.json", contract),
                       (folder / "input/options.json", options),
                       (Path(project.run_dir) / "planning/visual_contract.json", {"slides": [contract]})):
        file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(snapshots, "verify_snapshot", lambda _: {"source_revision": 0, "snapshot_id": "a" * 64})
    calls = []
    monkeypatch.setattr(service, "submit", lambda *args, **kwargs: calls.append((args, kwargs)) or {"id": job.id})
    assert service.resume(db, project, job)["id"] == job.id
    assert calls[0][0][2] == contract
    assert calls[0][1] == {"options": options, "expected_snapshot": "a" * 64}
    # New content must not be overwritten by continuing the old request.
    (Path(project.run_dir) / "planning/visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": "s1", "title": "new"}]}), encoding="utf-8")
    with pytest.raises(store.HtmlTaskError):
        service.resume(db, project, job)
    assert len(calls) == 1


def test_stale_success_and_recovery_advice(case, monkeypatch):
    import html_visual_store
    db, project, job = case
    store.mark_running(db, job.id)
    store.mark_succeeded(db, job.id, {"saved": {"revision": 1}})
    monkeypatch.setattr(html_visual_store, "_read_revision", lambda _: {"revision": 2})
    assert store.task_view(job, project.run_dir)["input_state"] == "stale"
    assert store.recent_task_summaries(db, project.id, run_dir=project.run_dir)[0]["input_state"] == "stale"


def test_changed_storyboard_without_author_edit_is_stale(case):
    db, project, job = case
    assert store.task_view(job, project.run_dir)["input_state"] == "current"
    (Path(project.run_dir) / "planning/visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": "s1", "title": "new"}]}), encoding="utf-8")
    assert store.task_view(job, project.run_dir)["input_state"] == "stale"


def test_current_slide_task_not_lost_after_twenty_other_tasks(case):
    db, project, job = case
    for i in range(25):
        store.submit_task(db, project_id=project.id, task_type="html_plan_generate",
                          submission_key=str(i), payload={"slide_id": "other"})
    assert not any(t["id"] == job.id for t in store.recent_task_summaries(db, project.id))
    assert store.current_slide_task(db, project.id, "s1", project.run_dir)["id"] == job.id
    assert store.current_slide_task(db, project.id, "missing", project.run_dir) is None


def test_broken_frozen_dependency_is_not_current(case):
    db, project, job = case
    folder = Path(project.run_dir) / "planning/html_visual/builds" / job.get_payload()["input"]["snapshot_id"]
    (folder / "input/contract.json").write_text('{}', encoding='utf-8')
    assert store.task_view(job, project.run_dir)["input_state"] == "stale"
    assert not store.task_view(job, project.run_dir)["recovery"]["can_resume"]


def test_real_resubmission_keeps_job_budget_and_blocks_model_change(case):
    db, project, _ = case
    calls = []
    service = HtmlWorkflowJobs(SessionLocal, HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **_: {}),
                               executor=SimpleNamespace(submit=lambda *args: calls.append(args)))
    task = service.submit(db, project, {"slide_id": "s1"})
    store.mark_failed(db, task['id'], 'interrupted')
    resumed = service.resume(db, project, db.get(LocalJob, task['id']))
    assert resumed['id'] == task['id'] and resumed['attempt'] == 2
    assert len(calls) == 2
    assert service.resume(db, project, db.get(LocalJob, task['id']))['id'] == task['id']
    assert len(calls) == 2
    store.mark_failed(db, task['id'], 'interrupted')
    service.freeze_models = lambda _: SimpleNamespace(summary=lambda: {'text': {'provider': 'changed', 'model': 'other', 'config_hash': 'new'}})
    with pytest.raises(store.HtmlTaskError, match='代码、模型或依赖已变化'):
        service.resume(db, project, db.get(LocalJob, task['id']))
    assert len(calls) == 2


def test_export_display_projection_excludes_private_paths():
    from html_delivery_status import delivery_evidence
    value = delivery_evidence({"export_evidence": {"snapshot_id": "s", "work_dir": "private",
                              "pages": [{"slide_id": "s1", "reused": True, "file": "private"}]}})
    assert value == {"snapshot_id": "s", "pages": [{"slide_id": "s1", "reused": True}]}
