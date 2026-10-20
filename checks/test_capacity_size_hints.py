"""Capacity facts and geometry suggestions must describe the same bounded edit."""
from html_candidate_agent import _capacity_size_hint, _geometry_constraints


def test_outgoing_request_uses_same_measured_size_for_geometry(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import pytest
    from html_candidate_agent import repair_candidate
    from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError

    root = Path(__file__).resolve().parents[1]
    scene = json.loads((root / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    scene["version"] = "0.5.0"
    (tmp_path / "diagnostic.png").write_bytes(b"explicit diagnostic test double")
    monkeypatch.setattr("html_candidate_agent.review_scene", lambda *args, **kwargs: {
        "passed": False, "message": "CONTENT_CAPACITY_EXCEEDED",
        "screenshot": "diagnostic.png", "capacityIssues": [{"target": "summary", "triggers": [
            {"dimension": "box_height", "actual": 180, "limit": 90, "unit": "canvas_px"},
            {"dimension": "box_height", "actual": 140, "limit": 90, "unit": "canvas_px"},
        ]}]})
    calls = []

    def capture(**kwargs):
        calls.append(kwargs)
        node = next(n for n in json.loads(kwargs["user_prompt"])["nodes"] if n["id"] == "summary")
        assert node["geometryConstraints"]["suggestedPresentation"]["height"] == node["capacitySizeHint"]["height"]["suggestedOuter"]
        assert kwargs["request_timeout"] == 180
        return {"action": "stop", "message": "Test capture only"}

    with pytest.raises(HtmlReviewError):
        repair_candidate(scene, None, run_dir=tmp_path, deps=HtmlReviewDependencies(root, capture))
    assert len(calls) == 1


def test_multiple_measurements_keep_largest_requirement_regardless_of_order():
    node = {"id": "summary", "slot": "summary"}
    layout = {"slots": {"summary": {"box": {"x": 58, "y": 660, "width": 1477, "height": 110}}}}
    issues = [{"target": "summary", "triggers": [
        {"dimension": "box_height", "actual": 180, "limit": 90, "unit": "canvas_px"},
        {"dimension": "box_height", "actual": 140, "limit": 90, "unit": "canvas_px"},
        {"dimension": "scroll_height", "actual": 900, "limit": 90, "unit": "css_px"},
    ]}]
    hints = _capacity_size_hint(node, layout, issues)
    assert hints["height"]["suggestedOuter"] == 200
    issues[0]["triggers"].reverse()
    assert _capacity_size_hint(node, layout, issues) == hints
    geometry = _geometry_constraints(node, {"motion": [{"targetId": "summary", "offsetY": 12}]}, layout, [], hints)
    assert geometry["suggestedPresentation"]["height"] == 200
    assert geometry["suggestedPresentation"]["offsetY"] == -72
    assert geometry["feasible"]


def test_safe_canvas_position_outside_public_tool_range_is_not_feasible():
    node = {"id": "summary", "slot": "summary", "presentation": {"height": 600}}
    layout = {"slots": {"summary": {"box": {"x": 58, "y": 660, "width": 1477, "height": 110}}}}
    result = _geometry_constraints(node, {"motion": []}, layout, [])
    assert result["offsetLimitsAtSuggestedSize"]["minOffsetY"] == -400
    assert result["offsetLimitsAtSuggestedSize"]["maxOffsetY"] == -460
    assert not result["feasible"]
