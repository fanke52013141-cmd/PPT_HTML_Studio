"""Candidate-only repair evidence; injected model, real graph/browser/editor."""

import copy
import json
from pathlib import Path

import pytest

from html_candidate_agent import repair_candidate
from html_visual_review_service import (
    HtmlReviewDependencies,
    HtmlReviewError,
    review_scene,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def draft(tmp_path):
    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/condensation.json").read_text(
            encoding="utf-8"
        )
    )
    scene["themeRef"]["id"] = "neutral-baseline"
    scene["version"] = "0.5.0"
    node = next(n for n in scene["nodes"] if n["id"] == "headline")
    node["presentation"] = {"typography": {"text": {"fontSizePx": 80}}}
    directory = tmp_path / "planning"
    directory.mkdir()
    (directory / "visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": scene["id"], "narration_beats": []}]}),
        encoding="utf-8",
    )
    return tmp_path, scene


def patch():
    return {
        "action": "patch",
        "operations": [
            {
                "targetId": "headline",
                "kind": "set_text_style",
                "part": "text",
                "values": {"fontSizePx": 28},
            }
        ],
    }


def test_unsaved_capacity_failure_real_screenshot_agent_and_strict_recheck(draft):
    run, scene = draft
    original = copy.deepcopy(scene)
    calls = []

    def model(**kw):
        import inspect
        from json_llm_service import _generate_json_with_configured_llm

        inspect.signature(_generate_json_with_configured_llm).bind(**kw)
        calls.append(kw)
        assert Path(kw["image_paths"][0]).read_bytes().startswith(b"\x89PNG")
        assert json.loads(kw["user_prompt"])["diagnostic"]["capacityIssues"]
        return patch()

    deps = HtmlReviewDependencies(ROOT, model)
    assert not review_scene(scene, run_dir=run, deps=deps)["passed"]
    diagnosis = review_scene(scene, run_dir=run, deps=deps, diagnostic=True)
    assert not diagnosis["passed"] and diagnosis["diagnosticOnly"]
    result = repair_candidate(scene, None, run_dir=run, deps=deps)
    assert result["report"]["passed"] and len(calls) == 1
    assert result["summary"]["framework"] == "LangGraph"
    assert scene == original
    assert not list((run / "planning/html_visual").glob("scene-*.json"))
    assert result["scene"]["beats"] == original["beats"]
    assert result["scene"]["motion"] == original["motion"]


def test_manual_protection_and_budget_preserve_original(draft):
    run, scene = draft
    original = copy.deepcopy(scene)
    calls = []

    def model(**kw):
        calls.append(kw)
        return patch()

    manual = {
        "protected_paths": [
            [
                "scene",
                "nodes",
                "headline",
                "presentation",
                "typography",
                "text",
                "fontSizePx",
            ]
        ]
    }
    with pytest.raises(HtmlReviewError, match="未通过"):
        repair_candidate(
            scene,
            None,
            run_dir=run,
            deps=HtmlReviewDependencies(ROOT, model),
            manual=manual,
            max_rounds=2,
        )
    assert len(calls) == 2 and scene == original
    record = next(
        (run / "planning/html_visual/candidates").rglob("operation-error.json")
    )
    assert (
        json.loads(record.read_text(encoding="utf-8"))["code"]
        == "MANUAL_FIELD_PROTECTED"
    )


def test_stop_and_noncapacity_failure_do_not_save(draft):
    run, scene = draft
    calls = []

    def model(**kw):
        calls.append(kw)
        return {"action": "stop", "message": "需要换模板，超出允许范围"}

    deps = HtmlReviewDependencies(ROOT, model)
    with pytest.raises(HtmlReviewError):
        repair_candidate(scene, None, run_dir=run, deps=deps)
    assert len(calls) == 1
    broken = copy.deepcopy(scene)
    broken["nodes"][0]["unregistered"] = True
    diagnostic = review_scene(broken, run_dir=run, deps=deps, diagnostic=True)
    assert not diagnostic["passed"] and not diagnostic.get("capacityIssues")
    with pytest.raises(HtmlReviewError):
        repair_candidate(broken, None, run_dir=run, deps=deps)
    assert len(calls) == 1
