"""Local adapter outcomes are evidence, never a supplier receipt or retry permission."""
import json
from pathlib import Path

import pytest

from html_candidate_agent import repair_candidate
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("failure", [False, True])
def test_request_timing_survives_stop_or_transport_exception(tmp_path, monkeypatch, failure):
    scene = json.loads((ROOT / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    scene["version"] = "0.5.0"
    (tmp_path / "diagnostic.png").write_bytes(b"explicit test double")
    monkeypatch.setattr("html_candidate_agent.review_scene", lambda *args, **kwargs: {
        "passed": False, "message": "CONTENT_CAPACITY_EXCEEDED", "screenshot": "diagnostic.png",
        "capacityIssues": [{"target": "headline", "triggers": []}]})
    calls = []

    def model(**kwargs):
        calls.append(kwargs)
        if failure:
            raise TimeoutError("provider secret request payload must not be copied")
        return {"action": "stop", "message": "No safe edit"}

    with pytest.raises(TimeoutError if failure else HtmlReviewError):
        repair_candidate(scene, None, run_dir=tmp_path, deps=HtmlReviewDependencies(ROOT, model), max_rounds=1)
    assert len(calls) == 1
    folder = next(tmp_path.glob("planning/html_visual/candidates/*/layout-agent/*/0"))
    request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
    raw = (folder / "request-outcome.json").read_text(encoding="utf-8")
    result = json.loads(raw)
    assert result["request_id"] == request["request_id"]
    assert result["elapsed_ms"] >= 0 and result["request_timeout_seconds"] == 180
    assert result["state"] == ("exception" if failure else "returned")
    assert result["submission_state"] == "unverified"
    assert result["usage"] is None and result["cost"] is None
    assert "provider secret" not in raw
    if failure:
        assert result["error_class"] == "TimeoutError"
        assert not (folder / "response.json").exists()
        summary = json.loads((folder.parent / "result.json").read_text(encoding="utf-8"))
        assert summary["status"] == "execution_failed"
