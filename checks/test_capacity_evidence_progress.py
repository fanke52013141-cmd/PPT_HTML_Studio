"""Capacity trigger progress under fixed DOM boxes; no paid providers."""
import copy
import json
from pathlib import Path

import pytest
from html_repair_progress import RepairProgress
from html_candidate_agent import repair_candidate
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from test_html_candidate_agent import draft

ROOT = Path(__file__).resolve().parents[1]


def evidence(lines, *, reverse=False, limit=2):
    triggers = [{"dimension": "line_count", "actual": lines, "limit": limit, "tolerance": 0, "unit": "lines"},
                {"dimension": "box_height", "actual": 75.125, "limit": 48, "tolerance": 1, "unit": "canvas_px"}]
    if reverse:
        triggers.reverse()
    return {"capacityIssues": [{"target": "headline", "measured": {"height": 75.125, "scrollHeight": 75, "clientHeight": 75},
                               "effectiveLimits": {"width": 100, "height": 48, "maxLines": limit}, "triggers": triggers}]}


def test_line_progress_is_not_hidden_by_unchanged_dom_box():
    tracker = RepairProgress()
    assert tracker.observe({"font": 80}, None, evidence(6)) is None
    assert tracker.observe({"font": 70}, None, evidence(5)) is None
    assert tracker.observe({"font": 60}, None, evidence(5, reverse=True)) == "unchanged_measurements"


def test_effective_limit_changes_are_measurement_facts():
    tracker = RepairProgress()
    assert tracker.observe({"width": 100}, None, evidence(5)) is None
    assert tracker.observe({"width": 110}, None, evidence(5, limit=3)) is None


def test_saved_report_details_preserve_trigger_progress_without_prose_noise():
    def wrapped(lines, text):
        raw = evidence(lines)["capacityIssues"][0]
        raw["triggers"][0]["message"] = text
        return {"issues": [{"code": "CONTENT_CAPACITY_EXCEEDED", "targets": ["headline"], "details": raw}]}
    tracker = RepairProgress()
    assert tracker.observe({"font": 80}, None, wrapped(6, "first")) is None
    assert tracker.observe({"font": 70}, None, wrapped(5, "improved")) is None
    assert tracker.observe({"font": 60}, None, wrapped(5, "wording only")) == "unchanged_measurements"


@pytest.mark.parametrize("mode,expected_calls,stop", [
    ("improves_to_pass", 2, None), ("unchanged", 1, "unchanged_measurements"),
    ("improves_but_exhausted", 2, "budget_exhausted"),
])
def test_actual_agent_consumes_triggers_and_preserves_bounded_stop(draft, monkeypatch, mode, expected_calls, stop):
    run, scene = draft
    original = copy.deepcopy(scene)
    (run/"capacity.png").write_bytes(b"isolated screenshot double")
    calls, events = [], []
    def review(candidate, **kwargs):
        size = next(n for n in candidate["nodes"] if n["id"] == "headline")["presentation"]["typography"]["text"]["fontSizePx"]
        if mode == "improves_to_pass" and size <= 60:
            return {"passed": True}
        lines = 6 if mode == "unchanged" else int(size // 10)
        return {"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED: line_count",
                **evidence(lines), "screenshot": "capacity.png"}
    def model(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        issue = payload["diagnostic"]["capacityIssues"][0]
        assert issue["effectiveLimits"]["height"] == 48
        assert issue["measured"]["scrollHeight"] == issue["measured"]["clientHeight"]
        assert issue["triggers"][0]["dimension"] == "line_count"
        assert issue["triggers"][1]["unit"] == "canvas_px"
        assert payload["remainingDecisions"] == 2 - len(calls)
        assert "protectedPaths" in payload
        calls.append(payload)
        return {"action": "patch", "operations": [{"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 80 - 10 * len(calls)}}]}
    monkeypatch.setattr("html_candidate_agent.review_scene", review)
    deps = HtmlReviewDependencies(ROOT, model)
    if stop:
        with pytest.raises(HtmlReviewError):
            repair_candidate(scene, None, run_dir=run, deps=deps, max_rounds=2, progress=events.append)
        assert events[-1]["next_action"]["reason"] == stop
        assert events[-1]["next_action"]["automatic_retry"] is False
    else:
        result = repair_candidate(scene, None, run_dir=run, deps=deps, max_rounds=2)
        assert result["report"]["passed"]
    assert len(calls) == expected_calls
    assert scene == original
    assert not (run/"planning/html_visual/scene-condensation.json").exists()
