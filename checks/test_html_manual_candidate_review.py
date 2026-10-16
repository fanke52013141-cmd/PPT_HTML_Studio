from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

import pytest

import html_manual_candidate_review as review


@pytest.mark.parametrize("mismatch", [False, True])
def test_interrupted_multiround_candidate_replays_and_restores_files(monkeypatch, tmp_path, mismatch):
    from artifact_fingerprint import sha256_json
    from html_design_reconstruction import PROMPT_VERSION
    from html_visual_review_service import REVIEW_DIR
    job = SimpleNamespace(id="original", job_type="html_plan_generate", status="interrupted")
    def write(relative, value):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path
    initial = {"id": "slide_001", "marker": 0}
    layout = {"id": "slide_001", "marker": 3}
    allocated = {"id": "slide_001", "marker": 4}
    repaired = {"id": "slide_001", "marker": 5}
    design_bytes = b"original-design-fixture"
    design_hash = hashlib.sha256(design_bytes).hexdigest()
    design_record = {"image_sha256": design_hash}
    design_key = sha256_json(design_record)
    base = "planning/html_visual/candidates/slide_001"
    design = write(f"{base}/designs/{design_key}/candidate.json", design_record).parent / "design-reference.png"
    design.write_bytes(design_bytes)
    stages = {"json:pending": {"state": "intent", "kind": "json", "lookup_supported": False}}
    for key, value in {"phase:compile": {"scene": initial, "binding": {}}, "phase:plan": {},
                       "phase:design_understanding": {"design_sha256": design_hash, "result": {}}}.items():
        path = write(f"stages/{key.split(':')[-1]}.json", value)
        stages[key] = {"state": "returned", "kind": "json", "file": path.relative_to(tmp_path).as_posix(),
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    view = {"slide_id": "slide_001", "input_state": "current", "source_revision": 0,
            "snapshot_id": "snapshot", "stages": stages, "recovery": {"requires_verification": True}}
    monkeypatch.setattr(review, "task_view", lambda *_: view)
    monkeypatch.setattr(review, "_read_revision", lambda *_: {"revision": 0})
    monkeypatch.setattr("html_runtime_skills.load_runtime_skill", lambda *_a, **_k: SimpleNamespace(identity={"fixture": True}))
    write("planning/html_visual/builds/snapshot/input/options.json", {"design_candidate_key": design_key})
    write("planning/html_visual/builds/snapshot/input/contract.json", {"narration_beats": []})
    write(f"{base}/layout-agent/example/0/scene.json", initial)
    write(f"{base}/layout-agent/example/3/scene.json", layout)
    write(f"{base}/layout-agent/example/result.json", {"passed": True, "rounds": [{}, {}, {}]})
    write(f"{base}/layout-agent/example/3/strict-review.json", {"passed": True, "scene_sha256": hashlib.sha256(json.dumps(layout, ensure_ascii=False, sort_keys=True).encode()).hexdigest()})
    identity = sha256_json({"scene": layout, "binding": {}, "design": design_hash, "manual": None,
                           "prompt": PROMPT_VERSION, "runtime_skill": {"fixture": True},
                           "understanding": {"design_sha256": design_hash, "result": {}}})
    audit = f"{base}/design-reconstruction/{identity}"
    write(f"{audit}/allocation-applied.json", {"source": "validated_model_understanding", "scene": allocated, "operations": []})
    preview = write(f"{audit}/0/current.png", {}).resolve()
    preview.write_bytes(b"fixture-render")
    write(f"{audit}/allocation-capacity-repair.json", {"scene": repaired, "binding": {}, "report": {"passed": True},
        "summary": {"rounds": [{"response": {"action": "patch", "operations": [{"kind": "set_presentation"}]}}]}})
    monkeypatch.setattr("html_design_agent.apply_allocations", lambda *_a, **_k: (allocated, []))
    monkeypatch.setattr("html_scene_editing.resources", lambda *_: {"assets": [], "pack": {}})
    monkeypatch.setattr("html_scene_repair.candidate_from_document", lambda *_a, **_k: {"scene": repaired})
    manifest = write("planning/html_visual/resources.json", {"assets": [], "fixture_metadata": "retain"})
    old_report = write(f"{REVIEW_DIR}/report-slide_001.json", {"retain": True})
    old_shot = write(f"{REVIEW_DIR}/review-slide_001.png", {})
    old_shot.write_bytes(b"previous-shot")
    before = {p: p.read_bytes() for p in (manifest, old_report, old_shot)}
    def render(scene, **_):
        assert scene == repaired
        old_shot.write_bytes(b"different" if mismatch else b"fixture-render")
        return {"passed": True, "screenshot": old_shot.relative_to(tmp_path).as_posix()}
    monkeypatch.setattr("html_visual_review_service.review_scene", render)
    if mismatch:
        with pytest.raises(review.ManualCandidateError, match="CANDIDATE_PREVIEW_CHANGED"):
            review.inspect_candidate(job, tmp_path, "slide_001", tmp_path)
    else:
        result = review.inspect_candidate(job, tmp_path, "slide_001", tmp_path)
        assert result["_scene"] == repaired and result["engineering"] == "passed"
        assert result["decision"] is None and result["model_fidelity"] == "unknown"
    assert all(p.read_bytes() == value for p, value in before.items())
    assert job.status == "interrupted"
    assert not list(tmp_path.glob(f"{base}/manual-reviews/*"))


@pytest.mark.parametrize("status", ["failed", "interrupted"])
@pytest.mark.parametrize("request_state", ["unknown", "intent"])
def test_unresolved_current_request_can_reach_evidence_validation(monkeypatch, tmp_path, status, request_state):
    job = SimpleNamespace(id="original", job_type="html_plan_generate", status=status)
    monkeypatch.setattr(review, "task_view", lambda *_: {
        "slide_id": "slide_001", "input_state": "current", "source_revision": 0,
        "stages": {"json:pending": {"state": request_state, "kind": "json", "lookup_supported": False}},
        "recovery": {"requires_verification": True},
    })
    monkeypatch.setattr(review, "_read_revision", lambda *_: {"revision": 0})
    def evidence_required(*_):
        raise review.ManualCandidateError("CANDIDATE_STAGE_NOT_RETURNED")
    monkeypatch.setattr(review, "_stage_json", evidence_required)
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_STAGE_NOT_RETURNED"):
        review.inspect_candidate(job, tmp_path, "slide_001", tmp_path)
    assert job.status == status and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("status,states", [
    ("running", [{"state": "intent", "kind": "json", "lookup_supported": False}]),
    ("cancelled", [{"state": "unknown", "kind": "json", "lookup_supported": False}]),
    ("interrupted", [{"state": "intent", "kind": "json", "lookup_supported": True}]),
    ("interrupted", [{"state": "unknown", "kind": "json", "lookup_supported": False}, {"state": "intent", "kind": "image"}]),
])
def test_candidate_does_not_relax_active_cancelled_or_multiple_unknowns(monkeypatch, tmp_path, status, states):
    job = SimpleNamespace(id="original", job_type="html_plan_generate", status=status)
    monkeypatch.setattr(review, "task_view", lambda *_: {
        "slide_id": "slide_001", "input_state": "current",
        "stages": {str(i): state for i, state in enumerate(states)},
        "recovery": {"requires_verification": True},
    })
    with pytest.raises(review.ManualCandidateError):
        review.inspect_candidate(job, tmp_path, "slide_001", tmp_path)
    assert job.status == status and list(tmp_path.iterdir()) == []


def test_unknown_candidate_requires_current_failed_original(monkeypatch, tmp_path):
    job = SimpleNamespace(id="html-original", job_type="html_plan_generate", status="failed")
    monkeypatch.setattr(review, "task_view", lambda _job, _run: {
        "slide_id": "slide_001", "input_state": "stale", "stages": {},
    })
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_TASK_NOT_CURRENT"):
        review.inspect_candidate(job, tmp_path, "slide_001", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_human_decision_is_immutable_and_does_not_change_original_job(monkeypatch, tmp_path):
    job = SimpleNamespace(id="html-original", job_type="html_plan_generate", status="failed")
    path = Path(tmp_path) / "review.json"
    packet = {"key": "a" * 64, "job_id": job.id, "source_revision": 0,
              "scene_sha256": "b" * 64, "design_sha256": "c" * 64,
              "preview_sha256": "d" * 64, "engineering": "failed", "decision": None,
              "_decision_path": path}
    monkeypatch.setattr(review, "inspect_candidate", lambda *_args: {
        **packet, "decision": review._json(path) if path.is_file() else None,
    })
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_DECISION_INVALID"):
        review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                key=packet["key"], decision="accept", note="short")
    result = review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                     key=packet["key"], decision="reject", note="标注框遮挡主体，尚不可接受")
    assert result["decision"]["decision"] == "reject"
    assert result["decision"]["author_saved"] is False
    assert result["decision"]["model_fidelity"] == "unknown"
    assert job.status == "failed"
    assert review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                   key=packet["key"], decision="reject", note="标注框遮挡主体，尚不可接受") == result
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_ALREADY_DECIDED"):
        review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                key=packet["key"], decision="accept", note="现在决定接受此候选")


def test_engineering_failure_cannot_be_accepted(monkeypatch, tmp_path):
    job = SimpleNamespace(id="html-original", job_type="html_plan_generate", status="failed")
    monkeypatch.setattr(review, "inspect_candidate", lambda *_args: {
        "key": "a" * 64, "decision": None, "engineering": "failed",
    })
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_ENGINEERING_FAILED"):
        review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                key="a" * 64, decision="accept", note="这份候选可以接受")
    assert list(tmp_path.iterdir()) == []
