"""Local candidate/store/service integration, without live providers or real projects."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from database import Project
from pipeline_lifecycle import write_json_atomic
import storyboard_plan_store as store
import storyboard_service as service
from html_course_runtime import CourseActions
from test_script_qualifier_fidelity import SOURCE, plan


@pytest.fixture
def flow(tmp_path, monkeypatch):
    project = Project(id="isolated-review", name="test", run_dir=str(tmp_path),
        target_duration_sec=None, step_status='{"2":"in_progress"}')
    article = {"title": "test", "content": SOURCE, "summary": ""}
    calls = []
    monkeypatch.setattr(service, "project_or_404", lambda *args: project)
    monkeypatch.setattr(service, "read_project_article_source", lambda *args: dict(article))
    monkeypatch.setattr(service, "read_step2_prompts_for_project", lambda *args, **kw: {"script_system": "custom", "script_output_example": "{}"})
    monkeypatch.setattr(service, "write_project_log", lambda *args, **kw: None)
    monkeypatch.setattr(service, "run_step2_json_llm", lambda **kw: calls.append(kw) or plan("没有统一标准。"))
    return SimpleNamespace(project=project, article=article, calls=calls, root=tmp_path)


def generate(flow):
    with pytest.raises(HTTPException) as error:
        service.execute_step2_script_plan.__wrapped__(flow.project.id, None)
    assert error.value.detail["code"] == "SCRIPT_QUALIFIER_REVIEW_REQUIRED"
    return error.value.detail["script_review"]


def corrected(review):
    return {**plan(SOURCE), "review_id": review["review_id"]}


def test_candidate_survives_reload_and_fix_does_not_regenerate_script(flow):
    review = generate(flow)
    loaded = service.get_step2_script_plan(flow.project.id, None)
    assert loaded["script_plan"] is None
    assert loaded["script_review"] == review
    assert not (flow.root/"planning/slide_script_plan.json").exists()
    # A second request must return the same candidate before any paid call.
    assert generate(flow)["review_id"] == review["review_id"]
    assert len(flow.calls) == 1
    with pytest.raises(HTTPException):
        service.update_step2_script_plan(flow.project.id, plan(SOURCE), None)
    bad = {**plan("没有统一标准。"), "review_id": review["review_id"]}
    with pytest.raises(HTTPException):
        service.update_step2_script_plan(flow.project.id, bad, None)
    response = service.update_step2_script_plan(flow.project.id, corrected(review), None)
    assert response["script_review"]["status"] == "resolved"
    assert not response["script_review"]["stale"]
    assert store.saved_script(flow.project) == plan(SOURCE)
    original = json.loads((flow.root/"planning/script_reviews"/(review["review_id"]+".json")).read_text(encoding="utf-8"))
    assert original["candidate"] == plan("没有统一标准。")
    with pytest.raises(HTTPException):
        service.update_step2_script_plan(flow.project.id, corrected(review), None)
    stages = []
    actions = CourseActions(SimpleNamespace(repo_root=Path(__file__).resolve().parents[1],
        read_project_article_source=lambda *args, **kw: flow.article,
        pipeline_service_factory=lambda *args: SimpleNamespace(
            storyboard_script=lambda: pytest.fail("corrected script must not be regenerated"),
            storyboard_visual=lambda: stages.append("visual") or {"success": True},
            storyboard_compose=lambda: stages.append("compose") or {"success": True})))
    actions.storyboard(None, flow.project)
    assert stages == ["visual", "compose"]
    assert len(flow.calls) == 1


def test_pending_keeps_official_and_downstream_bytes_and_blocks_compose(flow):
    official = plan("以当地公告为准。")
    write_json_atomic(flow.root/"planning/slide_script_plan.json", official)
    write_json_atomic(flow.root/"planning/visual_contract.json", {"old": True})
    audio = flow.root/"audio.wav"; audio.write_bytes(b"existing-audio")
    review = generate(flow)
    assert store.saved_script(flow.project) == official
    assert audio.read_bytes() == b"existing-audio"
    assert json.loads((flow.root/"planning/visual_contract.json").read_text()) == {"old": True}
    with pytest.raises(HTTPException) as error:
        service.compose_step2_visual_contract(flow.project.id, None)
    assert error.value.detail["script_review"]["review_id"] == review["review_id"]
    response = service.update_step2_script_plan(flow.project.id, corrected(review), None)
    assert response["visual_stale"] and response["workflow_pending"]
    assert audio.read_bytes() == b"existing-audio"
    assert json.loads((flow.root/"planning/visual_contract.json").read_text()) == {"old": True}


@pytest.mark.parametrize("change", ["article", "official", "candidate"])
def test_stale_source_official_or_review_identity_cannot_overwrite(flow, change):
    review = generate(flow)
    payload = corrected(review)
    if change == "article":
        flow.article["content"] += "原文更新。"
    elif change == "official":
        write_json_atomic(flow.root/"planning/slide_script_plan.json", plan("另一个编辑者已保存。"))
    else:
        payload["review_id"] = "old-version"
    before = store.saved_script(flow.project)
    with pytest.raises(HTTPException) as error:
        service.update_step2_script_plan(flow.project.id, payload, None)
    assert error.value.status_code == 409
    assert store.saved_script(flow.project) == before


def test_source_changes_during_model_request_are_not_applied(flow, monkeypatch):
    def model(**kw):
        flow.article["content"] += "在途更新。"
        return plan(SOURCE)
    monkeypatch.setattr(service, "run_step2_json_llm", model)
    with pytest.raises(HTTPException) as error:
        service.execute_step2_script_plan.__wrapped__(flow.project.id, None)
    assert "SCRIPT_REVIEW_STALE" in error.value.detail
    assert store.saved_script(flow.project) is None


def test_stale_candidate_can_be_superseded_by_explicit_valid_generation(flow, monkeypatch):
    review = generate(flow)
    flow.article["content"] += "原文更新。"
    monkeypatch.setattr(service, "run_step2_json_llm", lambda **kw: plan(SOURCE))
    result = service.execute_step2_script_plan.__wrapped__(flow.project.id, None)
    assert result["success"]
    loaded = service.get_step2_script_plan(flow.project.id, None)
    assert loaded["script_review"]["status"] == "superseded"
    assert loaded["script_plan"] == plan(SOURCE)
    assert (flow.root/"planning/script_reviews"/(review["review_id"]+".json")).is_file()


def test_manual_risky_edit_also_retains_candidate_without_overwriting_official(flow):
    official = plan("请以公告为准。")
    write_json_atomic(flow.root/"planning/slide_script_plan.json", official)
    with pytest.raises(HTTPException) as error:
        service.update_step2_script_plan(flow.project.id, plan("没有统一标准。"), None)
    review = error.value.detail["script_review"]
    assert review["status"] == "pending"
    assert service.get_step2_script_plan(flow.project.id, None)["script_review"] == review
    assert store.saved_script(flow.project) == official
    result = service.update_step2_script_plan(flow.project.id, corrected(review), None)
    assert result["script_review"]["status"] == "resolved"
    assert not flow.calls


def test_current_visual_mapping_is_reused_after_review_correction(flow):
    from storyboard_planning import _step2_script_plan_fingerprint
    review = generate(flow)
    service.update_step2_script_plan(flow.project.id, corrected(review), None)
    write_json_atomic(flow.root/"planning/slide_visual_plan.json", {
        "source_script_hash": _step2_script_plan_fingerprint(plan(SOURCE)), "slides": []})
    calls = []
    adapter = CourseActions(SimpleNamespace(repo_root=Path(__file__).resolve().parents[1],
        read_project_article_source=lambda *args, **kw: flow.article,
        pipeline_service_factory=lambda *_: SimpleNamespace(
            storyboard_script=lambda: pytest.fail("do not regenerate corrected script"),
            storyboard_visual=lambda: pytest.fail("do not regenerate current mapping"),
            storyboard_compose=lambda: calls.append("compose") or {"success": True})))
    adapter.storyboard(None, flow.project)
    assert calls == ["compose"]


def test_http_routes_preserve_review_payload_and_allow_explicit_correction(flow):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from storyboard_routes import router
    app = FastAPI()
    app.include_router(router)
    base = f"/api/projects/{flow.project.id}/steps/2"
    with TestClient(app) as client:
        generated = client.post(base + "/script/execute", json={})
        assert generated.status_code == 409
        detail = generated.json()["detail"]
        assert detail["automatic_retry"] is False
        review = detail["script_review"]
        loaded = client.get(base + "/script/result")
        assert loaded.status_code == 200
        assert loaded.json()["script_plan"] is None
        assert loaded.json()["script_review"]["review_id"] == review["review_id"]
        assert client.post(base + "/script/execute", json={}).status_code == 409
        assert len(flow.calls) == 1
        assert client.put(base + "/script/result", json=plan(SOURCE)).status_code == 409
        saved = client.put(base + "/script/result", json=corrected(review))
        assert saved.status_code == 200
        assert saved.json()["script_plan"] == plan(SOURCE)
        assert saved.json()["script_review"]["status"] == "resolved"
        assert not saved.json()["script_review"]["stale"]
        assert client.put(base + "/script/result", json=corrected(review)).status_code == 409
        assert len(flow.calls) == 1
