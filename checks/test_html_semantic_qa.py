"""A04 source-bound semantic gates: real browser evidence, stubbed model only."""
import copy
import json
from pathlib import Path

import pytest

from html_build_snapshot import json_bytes
from html_semantic_qa import (SemanticQAError, prepare_inputs, check_frames,
                              evaluate_response, report_checks, seal)
from html_semantic_review import review_semantic_scene, semantic_status
from html_visual_review_service import HtmlReviewDependencies, approve_scene, approval_status, HtmlReviewError
from html_visual_store import save_scene
from test_html_object_decomposition import decomposition_plan, normalize
from test_html_semantic_motion import CONTRACT_SLIDE, timeline
from test_html_narration_semantics import ROOT, CATALOG
from html_production_service import compile_plan


def fixture_inputs():
    raw = decomposition_plan()
    raw["slide_id"] = CONTRACT_SLIDE["slide_id"]
    plan = normalize(raw, CONTRACT_SLIDE)
    scene, binding = compile_plan(plan, CONTRACT_SLIDE, CATALOG)
    return plan, scene, binding, timeline()


def write_run(run):
    plan, scene, binding, audio = fixture_inputs()
    save_scene(run, scene["id"], scene, 0)
    for path, value in [("planning/visual_contract.json", {"slides": [CONTRACT_SLIDE]}),
                        (f"planning/html_visual/plan-{scene['id']}.json", plan),
                        (f"planning/html_visual/binding-{scene['id']}.json", binding),
                        (f"slides/{scene['id']}/audio_timeline.json", audio)]:
        p = run / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(json_bytes(value))
    # Explicit fake media: tests verify source freezing, never claim listen/decode.
    (run / f"slides/{scene['id']}/voice.mp3").write_bytes(b"synthetic-audio-source-test")
    return scene


def evaluator(verdict="related", confidence=.95):
    def call(**kwargs):
        assert len(kwargs["image_paths"]) == 3
        assert all(Path(p).is_file() for p in kwargs["image_paths"])
        data = json.loads(kwargs["user_prompt"])
        return {"verdict": verdict, "confidence": confidence,
                "evidence": [{"quote": data["spoken_text"], "frameIndices": [1, 2],
                              "objectIds": [data["targets"][0]["objectId"]],
                              "reason": "模拟评估结果，仅检验门禁和证据绑定"}]}
    return call


@pytest.fixture(scope="module")
def reviewed(tmp_path_factory):
    run = tmp_path_factory.mktemp("semantic-qa")
    scene = write_run(run)
    deps = HtmlReviewDependencies(ROOT, evaluator())
    report = review_semantic_scene(scene, run_dir=run, deps=deps)
    return run, scene, deps, report


def test_frozen_real_browser_frames_and_independent_states(reviewed):
    run, scene, deps, report = reviewed
    assert report["checks"] == {"engineering": "passed", "semantic": "passed", "audio": "pending_review", "human": "pending_review"}
    assert not report["approval_granted"]
    status = semantic_status(scene, run)
    assert status["valid"] and status["passed"]
    folder = run / report["evidence_path"]
    raw = json.loads((folder / "semantic-frames.json").read_text(encoding="utf-8"))
    assert len(raw["frames"]) == 6
    assert raw["frames"][0]["states"]["stat-1"]["opacity"] == 0
    assert raw["frames"][2]["states"]["stat-1"]["opacity"] == 1
    approval = approve_scene(scene, run_dir=run, deps=deps)
    assert approval["semantic_report_digest"] == report["report_digest"]
    assert approval_status(scene, run_dir=run, deps=deps, slide_id=scene["id"])["valid"]


@pytest.mark.parametrize("verdict,confidence,status", [("omitted", .95, "failed"), ("contradictory", .95, "failed"),
                                                     ("uncertain", .95, "pending_review"), ("related", .5, "pending_review")])
def test_semantic_decisions_do_not_grant_engineering_or_human_approval(verdict, confidence, status):
    plan, scene, binding, audio = fixture_inputs()
    response = {"verdict": verdict, "confidence": confidence, "evidence": [{"quote": plan["beats"][0]["spoken_text"],
                "frameIndices": [1], "objectIds": [plan["beats"][0]["targets"][0]["objectId"]], "reason": "缺少相应表达"}]}
    frames = [{"states": {n["id"]: {"opacity": 1} for n in scene["nodes"]}} for _ in range(3)]
    result = evaluate_response(response, plan["beats"][0], frames)
    checks = report_checks("passed", [result])
    assert checks["semantic"] == status and checks["engineering"] == "passed"
    assert checks["human"] == checks["audio"] == "pending_review"


def test_engineering_pass_cannot_override_reported_semantic_omission(tmp_path):
    scene = write_run(tmp_path)
    deps = HtmlReviewDependencies(ROOT, evaluator("omitted"))
    report = review_semantic_scene(scene, run_dir=tmp_path, deps=deps)
    assert report["checks"]["engineering"] == "passed" and report["checks"]["semantic"] == "failed"
    with pytest.raises(HtmlReviewError, match="语义"):
        approve_scene(scene, run_dir=tmp_path, deps=deps)


def test_missing_report_and_changed_audio_cannot_reuse_approval(reviewed, tmp_path):
    run, scene, deps, report = reviewed
    assert not semantic_status(scene, tmp_path)["valid"]
    with pytest.raises(HtmlReviewError, match="语义"):
        approve_scene(scene, run_dir=tmp_path, deps=deps)
    voice = run / f"slides/{scene['id']}/voice.mp3"
    original = voice.read_bytes()
    try:
        voice.write_bytes(b"changed source")
        assert not semantic_status(scene, run)["valid"]
        assert not approval_status(scene, run_dir=run, deps=deps, slide_id=scene["id"])["valid"]
    finally:
        voice.write_bytes(original)


def test_rehashed_pointer_cannot_change_semantic_outcome(reviewed):
    run, scene, deps, report = reviewed
    pointer = run / f"planning/html_visual/semantic-review/current-{scene['id']}.json"
    original = pointer.read_bytes()
    try:
        changed = copy.deepcopy(report)
        changed.pop("report_digest")
        changed["checks"]["human"] = "passed"
        pointer.write_bytes(json_bytes(seal(changed)))
        assert not semantic_status(scene, run)["valid"]
    finally:
        pointer.write_bytes(original)


def test_frame_deletion_and_terminal_only_cannot_satisfy_coverage(reviewed):
    run, scene, deps, report = reviewed
    plan, author, binding, audio = fixture_inputs()
    bound, spec = prepare_inputs(plan, CONTRACT_SLIDE, author, binding, audio, CATALOG)
    folder = run / report["evidence_path"]
    raw = json.loads((folder / "semantic-frames.json").read_text(encoding="utf-8"))
    for frames in (raw["frames"][1:], raw["frames"][-1:]):
        with pytest.raises(SemanticQAError, match="COVERAGE"):
            check_frames(bound, plan, spec, {"frames": frames, "pageErrors": []})


def test_source_object_action_and_beat_identity_are_revalidated():
    plan, scene, binding, audio = fixture_inputs()
    changed = copy.deepcopy(scene)
    changed["nodes"][0]["title"] = "未授权改稿"
    with pytest.raises(SemanticQAError, match="PLAN_SCENE"):
        prepare_inputs(plan, CONTRACT_SLIDE, changed, binding, audio, CATALOG)
    binding["actions"][scene["motion"][0]["actionId"]]["beatId"] = plan["beats"][1]["id"]
    with pytest.raises(SemanticQAError, match="ACTION_BEAT"):
        prepare_inputs(plan, CONTRACT_SLIDE, scene, binding, audio, CATALOG)


def test_response_must_cite_existing_frames_objects_and_verbatim_narration():
    plan, scene, binding, audio = fixture_inputs()
    response = {"verdict": "related", "confidence": .95, "evidence": [{"quote": "模型编造的原句", "frameIndices": [1],
                "objectIds": [scene["nodes"][0]["id"]], "reason": "无法引用"}]}
    with pytest.raises(SemanticQAError, match="EVIDENCE"):
        evaluate_response(response, plan["beats"][0], [{"states": {scene["nodes"][0]["id"]: {}}}])


def test_related_decision_cannot_cite_only_background_or_hidden_target():
    plan, scene, binding, audio = fixture_inputs()
    response = {"verdict": "related", "confidence": .95, "evidence": [{"quote": plan["beats"][0]["spoken_text"],
                "frameIndices": [1], "objectIds": ["header"], "reason": "背景不能冒充讲解目标"}]}
    frames = [{"states": {n["id"]: {"opacity": 0 if n["id"] == "stat-1" else 1} for n in scene["nodes"]}} for _ in range(3)]
    with pytest.raises(SemanticQAError, match="TARGET_EVIDENCE"):
        evaluate_response(response, plan["beats"][0], frames)
    response["evidence"][0]["objectIds"] = ["stat-1"]
    with pytest.raises(SemanticQAError, match="TARGET_EVIDENCE"):
        evaluate_response(response, plan["beats"][0], frames)


def test_missing_png_and_rehashed_deleted_frame_are_blocked(reviewed):
    from html_build_snapshot import fresh_hash
    run, scene, deps, report = reviewed
    folder = run / report["evidence_path"]
    pointer = run / f"planning/html_visual/semantic-review/current-{scene['id']}.json"
    receipt = folder / "semantic-report.json"
    raw_path = folder / "semantic-frames.json"
    png = folder / "beat-0-0.png"
    original = {p: p.read_bytes() for p in (pointer, receipt, raw_path, png)}
    try:
        png.unlink()
        assert not semantic_status(scene, run)["valid"]
        png.write_bytes(original[png])
        raw = json.loads(original[raw_path])
        raw["frames"].pop(0)
        raw_path.write_bytes(json_bytes(raw))
        changed = copy.deepcopy(report)
        changed.pop("report_digest")
        for entry in changed["evidence"]:
            if entry["path"] == raw_path.name:
                entry["sha256"] = fresh_hash(raw_path)
        forged = json_bytes(seal(changed))
        pointer.write_bytes(forged)
        receipt.write_bytes(forged)
        assert not semantic_status(scene, run)["valid"]
    finally:
        for p, data in original.items():
            p.write_bytes(data)


def test_unavailable_provider_is_pending_without_retry_or_approval(tmp_path):
    scene = write_run(tmp_path)
    calls = []
    def unavailable(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("provider unavailable")
    deps = HtmlReviewDependencies(ROOT, unavailable)
    report = review_semantic_scene(scene, run_dir=tmp_path, deps=deps)
    assert len(calls) == 2
    assert report["checks"]["semantic"] == "pending_review" and not report["passed"]
    assert semantic_status(scene, tmp_path)["valid"]
    with pytest.raises(HtmlReviewError, match="语义"):
        approve_scene(scene, run_dir=tmp_path, deps=deps)


def test_model_cannot_change_sources_during_review(tmp_path):
    scene = write_run(tmp_path)
    def changed(**kwargs):
        path = tmp_path / f"slides/{scene['id']}/audio_timeline.json"
        audio = json.loads(path.read_text(encoding="utf-8"))
        audio["segments"][0]["text"] = "改变权威输入"
        path.write_bytes(json_bytes(audio))
        return evaluator()(**kwargs)
    with pytest.raises(SemanticQAError, match="SOURCE_CHANGED"):
        review_semantic_scene(scene, run_dir=tmp_path, deps=HtmlReviewDependencies(ROOT, changed))
    assert not semantic_status(scene, tmp_path)["valid"]


def test_web_and_agent_review_dispatch_same_semantic_service(reviewed, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from agent_api import routes as agent
    import html_visual_review_routes as web
    import html_visual_review_service as service
    import project_path_service
    run, scene, deps, report = reviewed
    monkeypatch.setattr(web, "_html_project", lambda pid, db: SimpleNamespace(id=pid))
    monkeypatch.setattr(agent, "_html_project_or_404", lambda pid, db: SimpleNamespace(id=pid))
    monkeypatch.setattr(project_path_service, "project_run_dir_or_500", lambda project: run)
    monkeypatch.setattr(web, "project_run_dir_or_500", lambda project: run)
    monkeypatch.setattr(web, "_service_deps", lambda: deps)
    monkeypatch.setattr(agent, "_agent_review_deps", lambda: deps)
    monkeypatch.setattr(web, "_dependencies", deps)
    # HTTP dispatch uses the already reviewed browser evidence; no extra provider calls.
    import html_semantic_review as semantic
    monkeypatch.setattr(semantic, "project_review_dependencies", lambda project, deps: deps)
    calls = []
    def reviewed_result(scene, **kwargs):
        calls.append(scene["id"])
        return copy.deepcopy(report)
    monkeypatch.setattr(semantic, "review_semantic_scene", reviewed_result)
    app = FastAPI()
    app.include_router(web.router)
    app.include_router(agent.router)
    with TestClient(app) as client:
        for prefix in ("/api", "/api/agent/v1"):
            result = client.post(f"{prefix}/projects/qa-test/html-review/{scene['id']}/review", json={})
            assert result.status_code == 200, result.text
            body = result.json()
            returned = body.get("review", body.get("report"))
            assert returned["checks"] == report["checks"]
        image = client.get(f"/api/projects/qa-test/html-review/{scene['id']}/screenshot?beat_index=0&frame_index=1")
        assert image.status_code == 200 and image.headers["content-type"] == "image/png"
        invalid = client.get(f"/api/projects/qa-test/html-review/{scene['id']}/screenshot?beat_index=99&frame_index=1")
        assert invalid.status_code == 409
    assert len(calls) == 2
    assert service.approval_status(scene, run_dir=run, deps=deps, slide_id=scene["id"])["valid"]


def test_real_token_page_five_sentence_three_requires_semantic_evidence(tmp_path):
    from test_html_semantic_motion import real_timing_plan
    fixture = json.loads((ROOT / "checks/fixtures/a03-real-s08-timings.json").read_text(encoding="utf-8"))
    page = fixture["pages"][-1]
    plan, scene, binding = real_timing_plan(page, return_plan=True)
    contract = {"slide_id": page["slide_id"], "narration_beats": page["narration_beats"]}
    save_scene(tmp_path, scene["id"], scene, 0)
    for path, value in [("planning/visual_contract.json", {"slides": [contract]}),
                        (f"planning/html_visual/plan-{scene['id']}.json", plan),
                        (f"planning/html_visual/binding-{scene['id']}.json", binding),
                        (f"slides/{scene['id']}/audio_timeline.json", page["audio_timeline"])]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(json_bytes(value))
    (tmp_path / f"slides/{scene['id']}/voice.mp3").write_bytes(b"fixture-media-not-a-listening-test")
    calls = []
    def review(**kwargs):
        data = json.loads(kwargs["user_prompt"])
        calls.append(data)
        if data["spoken_text"] == page["narration_beats"][2]["spoken_text"]:
            response = evaluator("omitted")(**kwargs)
            response["evidence"][0]["reason"] = "画面只复述原句，未具体表达输出预留空间与实际用量检查；不能因强调对象而通过。"
            return response
        return evaluator()(**kwargs)
    report = review_semantic_scene(scene, run_dir=tmp_path, deps=HtmlReviewDependencies(ROOT, review))
    assert report["checks"]["engineering"] == "passed"
    assert report["checks"]["semantic"] == "failed"
    assert len(calls) == 4 and report["evaluations"][2]["status"] == "failed"
    assert "预留" in calls[2]["spoken_text"]
    assert not report["passed"]


def test_review_reuses_project_text_binding_and_records_public_identity(monkeypatch):
    from types import SimpleNamespace
    from html_semantic_review import project_review_dependencies
    import project_model_binding_service
    model = SimpleNamespace(summary=lambda: {"provider": "fixture", "model": "vision-evaluator", "config_hash": "public-hash"})
    monkeypatch.setattr(project_model_binding_service, "freeze_project_models", lambda project, required: SimpleNamespace(text=model))
    calls = []
    deps = project_review_dependencies(SimpleNamespace(), HtmlReviewDependencies(ROOT, lambda **kwargs: calls.append(kwargs)))
    deps.json_generator(system_prompt="test")
    assert calls[0]["model_binding"] is model and calls[0]["request_timeout"] == 90
    assert calls[0]["strict_response"] is True
    assert deps.semantic_model_identity["model"] == "vision-evaluator"
    assert "api_key" not in deps.semantic_model_identity


def test_multimodal_review_does_not_retry_or_repair_invalid_json(monkeypatch):
    import json_llm_service as llm
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="invalid-json"))])
    monkeypatch.setattr(llm, "get_openai_client", lambda **kwargs: client)
    monkeypatch.setattr(llm, "get_setting", lambda key, *args: {"llm_api_key": "fixture", "llm_model": "fixture-model"}.get(key, ""))
    monkeypatch.setattr(llm, "parse_json_or_repair_with_llm", lambda **kwargs: pytest.fail("评估不得调用文字修复"))
    with pytest.raises(json.JSONDecodeError):
        llm._generate_json_with_configured_llm(system_prompt="fixture", user_prompt="fixture", run_dir=".",
                                              artifact_prefix="test", schema_hint="{}", strict_response=True)
    assert client.chat.completions.create.call_count == 1
    assert client.close.call_count == 1
