"""E transport/checkpoint evidence. Model providers are fixtures, not live calls."""
import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw
from pydantic import ValidationError

from checks.test_html_workflow_acceptance import plan_for
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from html_visual_store import load_scene_with_revision
from html_production_service import produce_scene
from html_design_candidates import candidate_directory, current_design
from html_reference_package import verify_package
from html_production_models import HtmlProduceRequest

ROOT = Path(__file__).resolve().parents[1]


def png():
    image = Image.new("RGBA", (128, 128))
    ImageDraw.Draw(image).ellipse((16, 16, 112, 112), fill="#888888")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def case(tmp_path, monkeypatch):
    source = json.loads((ROOT / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    plan, contract = plan_for(source, "e1")
    requests, llm_calls = [], []
    def generator(**kw):
        llm_calls.append(kw)
        from checks.html_design_agent_fixture import response_for
        agent_result = response_for(kw)
        if agent_result is not None:
            return agent_result
        if kw.get("artifact_prefix", "").startswith("design-reconstruct-"):
            return {"status":"unchanged","message":"fixture only; no visual approval"}
        return copy.deepcopy(plan)
    def provider(prompt, **kw):
        requests.append({"prompt": prompt, **kw, "sent_hashes": [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in kw["reference_paths"]]})
        return png()
    monkeypatch.setattr("html_production_service.review_scene", lambda *a, **kw: {"passed": True})
    deps = HtmlReviewDependencies(repo_root=ROOT, json_generator=generator)
    return SimpleNamespace(run=tmp_path, contract=contract, deps=deps, provider=provider,
                           requests=requests, llm_calls=llm_calls)


def run(case, **options):
    return produce_scene(case.contract, run_dir=case.run, deps=case.deps, provider=case.provider, options=options)


def test_allocation_precedes_subject_generation_and_observation_is_consumed(case):
    first = run(case)
    result = run(case, design_candidate_key=first["design"]["key"])
    assert result["saved"]["changed"]
    allocation = next(k for k in case.llm_calls if k.get("artifact_prefix", "").startswith("design_understanding-"))
    data = json.loads(allocation["user_prompt"])
    assert any(v["assetMode"] == "generate" for v in data["capabilities"].values())
    assert "fixture observation only" in case.requests[-1]["prompt"]
    assert result["saved"]["changed"] and not (case.run/"planning/html_visual/approval-e1.json").exists()


def test_accepted_legacy_design_cannot_be_resumed_as_semantic_plan(case):
    first = run(case)
    with pytest.raises(HtmlReviewError) as caught:
        run(case, design_candidate_key=first["design"]["key"], plan_version="0.2.0")
    assert caught.value.code == "PLAN_VERSION_MISMATCH"


def test_unsupported_allocation_stops_before_paid_subject_and_author_write(case):
    first = run(case)
    from checks.html_design_agent_fixture import response_for
    def generator(**kw):
        if kw.get("artifact_prefix", "").startswith("design_understanding-"):
            data = json.loads(kw["user_prompt"])
            # The observation table must still cover every input object even when
            # the allocation itself is unsupported; only the allocation is empty.
            return {"status":"unsupported","objects":[],"feature_observations":response_for(kw)["feature_observations"],"issues":[{"targetId":data["objects"][0]["id"],"route":"capabilities","requirement":"unsupported_presentation","evidence":"fixture unsupported shape"}]}
        return response_for(kw)
    case.deps = HtmlReviewDependencies(ROOT,generator)
    with pytest.raises(HtmlReviewError) as caught:
        run(case,design_candidate_key=first["design"]["key"])
    assert caught.value.code == "DESIGN_ALLOCATION_UNSUPPORTED"
    assert len(case.requests)==1 and not (case.run/"planning/html_visual/scene-e1.json").exists()


def test_semantic_generated_image_identity_reaches_new_compiler(case):
    from checks.test_html_semantic_plan import semantic_plan
    plan = semantic_plan(case.contract)
    from checks.html_design_agent_fixture import response_for
    case.deps = HtmlReviewDependencies(ROOT, lambda **kw: response_for(kw) or ({"status":"unchanged","message":"fixture only"} if kw.get("artifact_prefix","").startswith("design-reconstruct-") else copy.deepcopy(plan)))
    first = run(case,plan_version="0.2.0")
    assert first["stage"] == "design_review"
    result = run(case,design_candidate_key=first["design"]["key"])
    assert result["saved"]["changed"]
    scene = json.loads((case.run/"planning/html_visual/scene-e1.json").read_text(encoding="utf-8"))
    assert scene["version"] == "0.6.0"
    assert next(n for n in scene["nodes"] if n["type"] == "image")["assetRef"]["id"].startswith("project-")


@pytest.mark.parametrize('model,size', [('gpt-image-1.5', '1536x1024'), ('gpt-image-2.5-flare-vip', '1280x720')])
def test_design_size_preserves_legacy_capability_and_records_actual_dimensions(case, model, size):
    first = produce_scene(case.contract, run_dir=case.run, deps=case.deps, provider=case.provider,
                          model_summary={'image': {'model': model}})
    assert first['stage'] == 'design_review'
    assert case.requests[0]['size'] == size
    receipt = json.loads(next((case.run/'planning/html_visual/candidates/e1').glob('design-*.request.json')).read_text(encoding='utf-8'))
    assert receipt['requested_size'] == size
    assert receipt['actual_size'] == [128, 128] and receipt['size_verified'] is False


def test_failed_unsaved_candidate_routes_agent_before_save(case, monkeypatch):
    calls = []
    def agent(scene, binding, **kw):
        calls.append(kw)
        return {"scene": scene, "binding": binding, "report": {"passed": True},
                "summary": {"passed": True, "rounds": ["fixture"]}}
    monkeypatch.setattr("html_candidate_agent.repair_candidate", agent)
    monkeypatch.setattr("html_production_service.review_scene", lambda *a, **kw:
                        {"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED: title"})
    first = run(case)
    result = run(case, design_candidate_key=first["design"]["key"])
    assert len(calls) == 1 and result["saved"]["changed"]
    assert result["layout_agent"]["passed"]


def test_agent_failure_rolls_back_previous_scene_resources_revision(case, monkeypatch):
    from html_visual_store import save_scene
    scene = json.loads((ROOT / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    scene["id"] = "e1"
    save_scene(case.run, "e1", scene, 0)
    resource = case.run / "planning/html_visual/resources.json"
    resource.write_text('{"assets":[]}', encoding="utf-8")
    paths = [case.run / "planning/html_visual/scene-e1.json", resource,
             case.run / "planning/html_visual/revision.json"]
    before = {p: p.read_bytes() for p in paths}
    first = run(case)
    def agent(*a, **kw):
        raise HtmlReviewError("agent rejected", code="CANDIDATE_AGENT_REJECTED")
    monkeypatch.setattr("html_candidate_agent.repair_candidate", agent)
    monkeypatch.setattr("html_production_service.review_scene", lambda *a, **kw:
                        {"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED: intro"})
    with pytest.raises(HtmlReviewError, match="agent rejected"):
        run(case, design_candidate_key=first["design"]["key"])
    assert before == {p: p.read_bytes() for p in paths}


def test_stop_resume_real_package_and_no_duplicate_planning(case):
    first = run(case)
    assert first["stage"] == "design_review" and not first["saved"]["changed"]
    assert len(case.requests) == 1 and not case.requests[0]["transparent_background"]
    assert load_scene_with_revision(case.run, "e1") is None
    assert not (case.run / "planning/html_visual/resources.json").exists()
    key = first["design"]["key"]
    folder = candidate_directory(case.run, "e1", key)
    record = json.loads((folder / "candidate.json").read_text(encoding="utf-8"))
    pack = verify_package(case.run / record["reference_package"])
    assert pack["manifest"]["palette"]["id"] == "neutral"
    assert pack["manifest"]["style"]["id"] == "neutral-baseline"
    assert all(a["role"] == "classification" for a in pack["manifest"]["attachments"])
    assert pack["references"] == case.requests[0]["reference_paths"]
    assert "黑、灰、白" in case.requests[0]["prompt"]
    assert "html-design-reference/0.3.1" in case.requests[0]["prompt"]
    catalog = json.loads((ROOT / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    layout = next(value for value in catalog["layouts"] if {"id": value["id"], "version": value["version"]} == record["plan"]["layoutRef"])
    geometry = pack["content"]["layoutGeometry"]
    assert geometry["canvas"] == layout["canvas"]
    assert geometry["slots"] == {slot: layout["slots"][slot]["box"] for slot in record["plan"]["slots"]}
    assert "layoutGeometry" in case.requests[0]["prompt"]
    assert '"tone"' not in case.requests[0]["prompt"]
    assert record["plan"]["slots"]["card-1"]["tone"] == "pink"
    assert "catalog_sha256" not in case.requests[0]["prompt"]
    second = run(case, design_candidate_key=key)
    assert len(case.llm_calls) == 4 and len(case.requests) == 2
    assert case.requests[-1]["transparent_background"]
    assert str(folder / "design-reference.png") in case.requests[-1]["reference_paths"]
    assert second["scene"]["themeRef"]["id"] == "neutral-baseline"
    assert second["review"]["passed"]
    assert not (case.run / "planning/html_visual/approval-e1.json").exists()
    assert current_design(run_dir=case.run, contract=case.contract, repo_root=ROOT)["design"]["status"] == "accepted_for_reconstruction"
    repeated = run(case, design_candidate_key=key)
    assert not repeated["saved"]["changed"] and len(case.requests) == 2


def test_explicit_supplied_asset_still_requires_page_design(case):
    case.contract["visual_groups"] = [{"id": "subject", "available_assets": [
        {"assetRef": {"id": "condensation", "version": "0.1.0"}}
    ]}]
    with pytest.raises(HtmlReviewError) as caught:
        produce_scene(case.contract, run_dir=case.run, deps=case.deps, provider=None)
    assert caught.value.code == "DESIGN_PROVIDER_MISSING"
    first=run(case)
    result=run(case,design_candidate_key=first["design"]["key"])
    assert result["review"]["passed"]
    assert result["saved"]["changed"]
    assert len(case.llm_calls) == 4
    assert len(case.requests) == 1
    assert next(n for n in result["scene"]["nodes"] if n["type"] == "image")["assetRef"]["id"] == "condensation"


def test_supplied_asset_version_mismatch_cannot_generate_or_save(case):
    case.contract["visual_groups"] = [{"id": "subject", "available_assets": [
        {"assetRef": {"id": "condensation", "version": "99.0.0"}}
    ]}]
    with pytest.raises(HtmlReviewError) as exc:
        run(case)
    assert exc.value.code == "SUPPLIED_ASSET_INVALID"
    assert not case.requests
    assert load_scene_with_revision(case.run, "e1") is None


@pytest.mark.parametrize("change", ["contract", "revision", "models", "definitions"])
def test_stale_checkpoint_stops_before_asset_requests(case, monkeypatch, change):
    first = run(case)
    kwargs = {}
    if change == "contract":
        case.contract["source"] = "new content"
    elif change == "revision":
        from pipeline_lifecycle import write_json_atomic
        write_json_atomic(case.run / "planning/html_visual/revision.json", {"revision": 1})
    elif change == "models":
        kwargs["model_summary"] = {"image": {"config_hash": "changed"}}
    else:
        monkeypatch.setattr("html_design_candidates.definition_identity", lambda *a: "changed")
    with pytest.raises(HtmlReviewError) as exc:
        produce_scene(case.contract, run_dir=case.run, deps=case.deps, provider=case.provider,
                      options={"design_candidate_key": first["design"]["key"]}, **kwargs)
    assert exc.value.code == "DESIGN_STALE"
    assert len(case.requests) == 1 and load_scene_with_revision(case.run, "e1") is None


@pytest.mark.parametrize("target", ["design", "attachment"])
def test_corrupt_candidate_or_reference_is_rejected(case, target):
    first = run(case)
    folder = candidate_directory(case.run, "e1", first["design"]["key"])
    file = folder / "design-reference.png" if target == "design" else Path(case.requests[0]["reference_paths"][0])
    file.write_bytes(b"changed")
    with pytest.raises(HtmlReviewError) as exc:
        run(case, design_candidate_key=first["design"]["key"])
    assert exc.value.code in {"DESIGN_CANDIDATE_INVALID", "REFERENCE_PACKAGE_INVALID"}
    assert len(case.requests) == 1


def test_request_cache_and_local_design_revision(case):
    first = run(case)
    assert run(case)["design"]["key"] == first["design"]["key"]
    assert len(case.requests) == 1
    revised = run(case, design_instruction="减少边框，增强标题层级")
    assert revised["design"]["key"] != first["design"]["key"]
    assert len(case.requests) == 2 and "减少边框" in case.requests[-1]["prompt"]
    assert candidate_directory(case.run, "e1", first["design"]["key"]).is_dir()


def test_single_asset_retry_reuses_design_and_plan(case):
    first = run(case)
    key = first["design"]["key"]
    initial = run(case, design_candidate_key=key)
    before = load_scene_with_revision(case.run, "e1")
    assert not current_design(run_dir=case.run, contract=case.contract, repo_root=ROOT)["design"]["stale"]
    retried = run(case, design_candidate_key=key, asset_instruction="更清晰的轮廓")
    assert len(case.llm_calls) == 7 and len(case.requests) == 3
    assert case.requests[-1]["transparent_background"]
    assert "更清晰的轮廓" in case.requests[-1]["prompt"]
    assert initial["scene"]["nodes"][0] == retried["scene"]["nodes"][0]
    assert before["scene"]["nodes"][0] == load_scene_with_revision(case.run, "e1")["scene"]["nodes"][0]


def test_reconstruction_recovery_reuses_subject_with_changed_observation(case):
    first = run(case)
    key = first["design"]["key"]
    initial = run(case, design_candidate_key=key)
    original_generator = case.deps.json_generator

    def generator(**kwargs):
        result = original_generator(**kwargs)
        if kwargs.get("artifact_prefix", "").startswith("design_understanding-"):
            for obj in result["objects"]:
                obj["appearance"] = "同一已接受画面的另一种观察措辞"
        return result

    case.deps = HtmlReviewDependencies(ROOT, generator)
    recovered = run(case, design_candidate_key=key)
    assert len(case.requests) == 2  # One design and one subject; no repeated paid image.
    assert recovered["scene"] == initial["scene"]


def test_reference_hashes_participate_in_approval_inputs(case):
    from html_input_manifest import resolved_scene_inputs
    first = run(case)
    result = run(case, design_candidate_key=first["design"]["key"])
    before = resolved_scene_inputs(result["scene"], case.run, ROOT)
    file = Path(case.requests[0]["reference_paths"][0])
    file.write_bytes(b"changed")
    after = resolved_scene_inputs(result["scene"], case.run, ROOT)
    assert before["digest"] != after["digest"]
    assert any(v is None for k, v in after["files"].items() if k.startswith("production_reference/"))


def test_asset_failure_keeps_existing_scene_and_receipt(case):
    first = run(case); key = first["design"]["key"]
    run(case, design_candidate_key=key)
    old = load_scene_with_revision(case.run, "e1")
    receipt = case.run / "planning/html_visual/candidates/e1/design-acceptance.json"
    previous = receipt.read_bytes()
    def broken(*a, **kw):
        raise ValueError("fixture provider failure")
    case.provider = broken
    with pytest.raises(ValueError):
        run(case, design_candidate_key=key, asset_instruction="new subject")
    assert load_scene_with_revision(case.run, "e1") == old and receipt.read_bytes() == previous


def test_neutral_theme_reuses_registered_geometry():
    catalog = json.loads((ROOT / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    theme = json.loads((ROOT / "html_engine/visual/themes/neutral-baseline.json").read_text(encoding="utf-8"))
    assert any(t["id"] == theme["id"] for t in catalog["themes"])
    for color in list(theme["colors"].values()) + [v for pair in theme["gradients"].values() for v in pair]:
        assert color[1:3] == color[3:5] == color[5:7]
    assert theme["shapes"]["shadowRGB"] == "34 34 34"


def test_gray_reference_removes_runtime_tones_without_changing_literal_text():
    from html_reference_package import design_content
    plan = {"slide_id": "test", "templateRef": {}, "layoutRef": {},
            "slots": {"header": {"kind": "header", "title": "蓝色也是正文事实"},
                      "summary": {"kind": "summary", "from": {"text": "blue", "tone": "blue"}},
                      "headline": {"kind": "text", "runs": [{"text": "green", "tone": "green"}]}}}
    original = copy.deepcopy(plan)
    content = design_content(plan, {"asset_needs": []})
    assert plan == original
    assert content["slots"]["summary"]["from"] == {"text": "blue"}
    assert content["slots"]["headline"]["runs"] == [{"text": "green"}]
    assert content["title"] == "蓝色也是正文事实"


def test_sdk_receives_attachment_bytes_and_low_1k_hint(tmp_path, monkeypatch):
    import ai_provider_service as service
    from html_image_provider import configured_image
    path = tmp_path / "reference.png"
    path.write_bytes(png())
    seen = []
    closed = []
    def edit(**params):
        seen.append({**params, "image": [f.read() for f in params["image"]]})
        return b"response"
    client = SimpleNamespace(images=SimpleNamespace(edit=edit), close=lambda: closed.append(True))
    monkeypatch.setattr(service, "get_openai_client", lambda **kw: client)
    monkeypatch.setattr(service, "_governed_image_request", lambda base, call: call())
    monkeypatch.setattr(service, "is_toapis_image_provider", lambda *a: False)
    monkeypatch.setattr(service, "extract_image_bytes_from_response", lambda response: response)
    binding = SimpleNamespace(require_ready=lambda: None, api_key="fixture-only", endpoint="https://fixture.invalid/v1", model="gpt-image-2.5-sunburst-official", provider="openai")
    assert configured_image("fixture", reference_paths=[path], transparent_background=False, model_binding=binding) == b"response"
    assert seen[0]["image"] == [path.read_bytes()] and "background" not in seen[0]
    assert seen[0]["quality"] == "low" and seen[0]["extra_body"]["metadata"]["resolution"] == "1K"
    configured_image("fixture", reference_paths=[path], model_binding=binding)
    assert seen[1]["background"] == "transparent" and len(closed) == 2


def test_toapis_receives_1k_low_and_actual_paths(tmp_path, monkeypatch):
    import ai_provider_service as service
    from html_image_provider import configured_image
    seen = []
    monkeypatch.setattr(service, "is_toapis_image_provider", lambda *a: True)
    monkeypatch.setattr(service, "generate_image_response", lambda *a, **kw: seen.append(kw) or b"image")
    monkeypatch.setattr(service, "extract_image_bytes_from_response", lambda r: r)
    binding = SimpleNamespace(require_ready=lambda: None, api_key="fixture-only", endpoint="https://fixture.invalid", model="fixture", provider="toapis")
    path = tmp_path / "ref.png"; path.write_bytes(png())
    configured_image("fixture", reference_paths=[path], transparent_background=False, model_binding=binding)
    assert seen[0]["public_config"] == {"toapis_resolution": "1k", "toapis_quality": "low"}
    assert seen[0]["reference_paths"] == [str(path)] and not seen[0]["transparent_background"]


@pytest.mark.parametrize("options", [{"unknown": True}, {"design_candidate_key": "../x"},
                                        {"design_candidate_key": "a" * 64, "design_instruction": "   "},
                                        {"design_candidate_key": "a" * 64, "design_instruction": "change", "asset_instruction": "change"},
                                        {"asset_instruction": "change"}])
def test_strict_request(options):
    with pytest.raises(ValidationError):
        HtmlProduceRequest.model_validate(options)


def test_design_revision_reuses_plan_and_attaches_original_without_author_write(case):
    first = run(case)
    key = first["design"]["key"]
    before_calls = len(case.llm_calls)
    old_record = json.loads((candidate_directory(case.run, "e1", key) / "candidate.json").read_text(encoding="utf-8"))
    revised = run(case, design_candidate_key=key, design_instruction="仅调整标签位置，保留原构图")
    assert len(case.llm_calls) == before_calls
    assert len(case.requests) == 2
    assert Path(case.requests[-1]["reference_paths"][-1]) == candidate_directory(case.run, "e1", key) / "design-reference.png"
    assert "最后一张附件" in case.requests[-1]["prompt"]
    new_record = json.loads((candidate_directory(case.run, "e1", revised["design"]["key"]) / "candidate.json").read_text(encoding="utf-8"))
    assert new_record["plan"] == old_record["plan"]
    assert new_record["brief"] == old_record["brief"]
    assert new_record["candidate"]["design_revision"]["source_key"] == key
    assert revised["stage"] == "design_review" and revised["saved"]["changed"] is False
    assert not (case.run / "planning/html_visual/scene-e1.json").exists()
    assert not (case.run / "planning/html_visual/design-acceptance.json").exists()


def test_web_agent_payload_parity_and_current_design(tmp_path, monkeypatch):
    import uuid
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from database import SessionLocal, Project, get_db
    from repository_paths import RUNS_DIR
    from agent_api.routes import router as agent_router
    import html_visual_review_routes as routes
    from pipeline_lifecycle import write_json_atomic
    requests = []
    class Jobs:
        def submit(self, db, project, contract, options=None):
            requests.append(options)
            return {"id": "fixture-task", "status": "queued"}
    monkeypatch.setattr(routes, "_jobs", Jobs())
    monkeypatch.setattr(routes, "_dependencies", routes.HtmlReviewDependencies(ROOT, lambda **kw: {}))
    pid = "e-http-" + uuid.uuid4().hex[:8]
    run_dir = Path(RUNS_DIR) / pid
    write_json_atomic(run_dir / "planning/visual_contract.json", {"slides": [{"slide_id": "s1"}]})
    db = SessionLocal()
    try:
        db.add(Project(id=pid, name="E fixture", account_id="default", visual_backend="html", run_dir=str(run_dir)))
        db.commit()
        app = FastAPI(); app.include_router(routes.router); app.include_router(agent_router)
        app.dependency_overrides[routes._get_db] = lambda: db
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            for prefix in ("/api", "/api/agent/v1"):
                base = f"{prefix}/projects/{pid}/html-review/s1"
                body = {"design_candidate_key": "a" * 64, "asset_instruction": "fixture retry"}
                assert client.post(base + "/produce", json=body).status_code == 200
                assert requests[-1] == {**body, "design_instruction": "", "plan_version": "0.2.0", "repair_relation_points": "",
                                       "runner": "legacy", "pi_limits": None, "max_image_calls": 0}
                reused = {"reuse_design_candidate_key": "b" * 64}
                assert client.post(base + "/produce", json=reused).status_code == 200
                assert requests[-1]["reuse_design_candidate_key"] == reused["reuse_design_candidate_key"]
                assert requests[-1]["design_candidate_key"] is None
                repaired = {**reused, "plan_version": "0.2.0", "repair_relation_points": "按原图修正端点"}
                assert client.post(base + "/produce", json=repaired).status_code == 200
                assert requests[-1]["repair_relation_points"] == repaired["repair_relation_points"]
                assert client.post(base + "/produce", json={"plan_version":"0.2.0"}).status_code == 200
                assert requests[-1]["plan_version"] == "0.2.0"
                assert client.post(base + "/produce", json={"unknown": True}).status_code == 422
                assert client.get(base + "/design/current").json()["design"] is None
    finally:
        db.close()


def test_persistent_design_stop_and_revision_identity(case):
    import uuid
    from database import SessionLocal, Project, LocalJob
    from repository_paths import RUNS_DIR
    from html_workflow_jobs import HtmlWorkflowJobs
    from pipeline_lifecycle import write_json_atomic
    pid = "e-job-" + uuid.uuid4().hex[:8]
    case.run = Path(RUNS_DIR) / pid
    write_json_atomic(case.run / "planning/visual_contract.json", {"slides": [case.contract]})
    class Capture:
        def submit(self, *args): self.args = args
    capture = Capture()
    db = SessionLocal()
    try:
        project = Project(id=pid, name="E fixture", account_id="default", visual_backend="html", run_dir=str(case.run))
        db.add(project); db.commit()
        jobs = HtmlWorkflowJobs(SessionLocal, case.deps, provider=case.provider, executor=capture)
        first = jobs.submit(db, project, case.contract)
        assert jobs.submit(db, project, case.contract)["reused"]
        capture.args[0](*capture.args[1:])
        db.expire_all()
        job = db.query(LocalJob).filter_by(id=first["id"]).one()
        assert job.status == "succeeded" and job.stage == "design_review", {
            "status": job.status, "stage": job.stage, "error": job.error}
        assert job.get_payload()["result"]["stage"] == "design_review"
        from html_creation_workflow import project_status
        status = project_status(project, run_dir=case.run, repo_root=ROOT, slide_ids=["e1"], db=db)
        stage = next(s for s in status["workflow"]["stages"] if s["id"] == "design_and_assets")
        assert stage["status"] == "needs_review"
        outputs = next(s for s in status["workflow"]["stages"] if s["id"] == "review_and_output")["targets"]
        assert not outputs["html_snapshot_pptx"]["ready"] and not outputs["mp4_video"]["ready"]
        write_json_atomic(case.run / "planning/html_visual/revision.json", {"revision": 1})
        second = jobs.submit(db, project, case.contract)
        assert second["id"] != first["id"] and not second["reused"]
    finally:
        db.close()
