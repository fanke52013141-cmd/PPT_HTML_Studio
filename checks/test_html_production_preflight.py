"""Shared-renderer containment and full-frame checks for unsaved production scenes."""
import copy
import json
from pathlib import Path
import subprocess

import pytest

from html_production_service import compile_plan
from html_storyboard_planning import load_template_catalog
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError, review_scene, _geometry_preflight

ROOT = Path(__file__).resolve().parents[1]


def stage_scene():
    cases = json.loads((ROOT / "checks/fixtures/course-structure-plans.json").read_text(encoding="utf-8"))
    return compile_plan(cases[3]["plan"], cases[3]["contract"], load_template_catalog(ROOT))[0]


def test_body_that_fits_its_own_box_but_escapes_card_is_rejected(tmp_path):
    scene = stage_scene()
    next(n for n in scene["nodes"] if n["id"] == "stage-1")["body"] = "正文内容用于核验父卡片边界，不应超出实际卡片内部的可用空间。"
    before = copy.deepcopy(scene)
    deps = HtmlReviewDependencies(ROOT, lambda **kw: pytest.fail("No provider permitted"))
    diagnostic = review_scene(scene, run_dir=tmp_path, deps=deps, diagnostic=True,
                              preflight_dir=tmp_path / "blocked-preflight")
    assert diagnostic["geometry_preflight"]["status"] == "blocked_by_capacity"
    assert not (tmp_path / "blocked-preflight/report.json").exists()
    issue = next(i for i in diagnostic["capacityIssues"] if i["target"] == "stage-1")
    # Child height and line count fit: this regression needs the real parent boundary.
    assert [t["dimension"] for t in issue["triggers"]] == ["text_bottom_overflow"]
    assert issue["triggers"][0]["actual"] > 20
    strict = review_scene(scene, run_dir=tmp_path, deps=deps)
    assert not strict["passed"] and "CONTENT_CAPACITY_EXCEEDED" in strict["message"]
    assert scene == before


def test_arrow_crossing_is_in_original_full_frame_preflight(tmp_path):
    scene = stage_scene()
    arrow = next(n for n in scene["nodes"] if n["id"] == "relation-1")
    # Natural failure class: bottom-to-top diagonal through the stage-card text.
    arrow["from"]["point"] = {"x": 0.5, "y": 1}
    arrow["to"]["point"] = {"x": 0.5, "y": 0}
    before = copy.deepcopy(scene)
    report = review_scene(scene, run_dir=tmp_path,
                          deps=HtmlReviewDependencies(ROOT, lambda **kw: pytest.fail("No provider permitted")),
                          preflight_dir=tmp_path / "preflight")
    assert not report["passed"] and report["code"] == "GEOMETRY_PREFLIGHT_REJECTED"
    preflight = report["geometry_preflight"]
    assert any(i["reason"] == "stroke_crosses_text" and "relation-1" in i["targets"] for i in preflight["issues"])
    assert preflight["coverage"]["frame_complete"] and not preflight["coverage"]["continuous_time_verified"]
    assert preflight["coverage"]["fps"] == 30 and preflight["clock"] == "author"
    assert "times" not in preflight["coverage"]
    raw = json.loads((tmp_path / "preflight/report.json").read_text(encoding="utf-8"))
    assert len(raw["frames"]) == preflight["frame_count"] == len(raw["coverage"]["times"])
    assert (tmp_path / "preflight/spec.json").is_file() and raw["screenshots"]
    assert scene == before


@pytest.mark.parametrize("raw,returncode", [(None, 0), ([], 0), ({"passed": True, "coverage": {}}, 0),
                                         ({"passed": True, "coverage": None}, 0),
                                         ({"passed": True, "coverage": {"frame_complete": True}}, 0),
                                         ({"passed": True, "coverage": {"frame_complete": True}}, 1)])
def test_incomplete_checker_never_inherits_stale_pass(tmp_path, raw, returncode):
    directory = tmp_path / "preflight"
    directory.mkdir()
    stale = directory / "report.json"
    stale.write_text('{"passed":true,"coverage":{"frame_complete":true}}')

    def runner(args, **kwargs):
        assert not stale.exists()
        if raw is not None:
            stale.write_text(json.dumps(raw))
        return subprocess.CompletedProcess(args, returncode, "", "")

    with pytest.raises(HtmlReviewError) as caught:
        _geometry_preflight(stage_scene(), tmp_path, HtmlReviewDependencies(ROOT, lambda **kw: None, runner), directory)
    assert caught.value.code == "GEOMETRY_PREFLIGHT_FAILED"
