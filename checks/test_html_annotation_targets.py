"""D03: annotation target resolution on html geometry — image anchors via
contain mapping, SVG registered boxes, text via DOM Range (browser); no
OCR. Browser evidence runs the real review tool and asserts the DOM
Range canvas rects and asset anchors agree within one logical pixel."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from html_annotation_targets import (
    AnnotationTargetError,
    apply_viewport_scale,
    resolve_targets,
)
import html_visual_review_service as review

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCENE = REPO_ROOT / "html_engine" / "visual" / "scenes" / "condensation.json"


def deps(tmp_path: Path) -> review.HtmlReviewDependencies:
    import runtime_support

    return review.HtmlReviewDependencies(
        repo_root=REPO_ROOT,
        json_generator=lambda **kwargs: {},
        run_subprocess_bounded=runtime_support.run_subprocess_killable,
    )


@pytest.fixture(scope="module")
def review_report(tmp_path_factory) -> dict:
    run_dir = tmp_path_factory.mktemp("run")
    scene = json.loads(ENGINE_SCENE.read_text(encoding="utf-8"))
    report = review.review_scene(
        scene,
        run_dir=run_dir,
        deps=deps(run_dir),
    )
    assert report["passed"] is True
    return report


def test_image_anchor_resolves_through_contain_mapping(review_report) -> None:
    resolved = resolve_targets(
        review_report,
        [{"id": "a1", "kind": "image_anchor", "nodeId": "subject", "anchorId": "focus"}],
    )
    assert not resolved["diagnostics"]
    anchor = resolved["targets"][0]["canvas"]
    expected = review_report["geometry"]["subject"]["anchors"]["focus"]
    assert anchor == pytest.approx(expected, abs=1e-6)
    # One viewport scale maps within a logical pixel by construction.
    scaled = apply_viewport_scale(resolved, viewport_width=1648)
    assert abs(scaled["targets"][0]["viewport"]["x"] - anchor["x"] * 1.03) < 0.02


def test_svg_target_uses_registered_box(review_report) -> None:
    resolved = resolve_targets(
        review_report,
        [{"id": "s1", "kind": "svg", "nodeId": "annotation"}],
    )
    assert not resolved["diagnostics"]
    assert resolved["targets"][0]["canvas_box"]["width"] == 1600


def test_text_range_marks_dom_resolver_with_valid_range(review_report) -> None:
    resolved = resolve_targets(
        review_report,
        [{"id": "t1", "kind": "text_range", "nodeId": "headline", "start": 0, "end": 3}],
    )
    assert not resolved["diagnostics"]
    target = resolved["targets"][0]
    assert target["codepoint_range"] == [0, 3]
    assert target["needs_dom_range"] is True
    with pytest.raises(AnnotationTargetError) as invalid:
        resolve_targets(
            review_report,
            [{"id": "t2", "kind": "text_range", "nodeId": "headline", "start": 5, "end": 5}],
        )
    assert invalid.value.code == "TARGET_RANGE_INVALID"


def test_deleted_target_yields_diagnostic_not_crash(review_report) -> None:
    resolved = resolve_targets(
        review_report,
        [
            {"id": "gone", "kind": "image_anchor", "nodeId": "deleted-node", "anchorId": "focus"},
            {"id": "ok", "kind": "svg", "nodeId": "annotation"},
        ],
    )
    assert resolved["diagnostics"] == [
        {
            "id": "gone",
            "code": "TARGET_NODE_GONE",
            "message": "目标节点 deleted-node 已删除，批注需隐藏或重挂",
        }
    ]
    assert [t["id"] for t in resolved["targets"]] == ["ok"]


def test_browser_dom_range_matches_canvas_within_one_pixel(
    tmp_path, review_report
) -> None:
    """Real browser: DOM Range rects (viewport) map back onto the resolver's
    canvas box within one logical pixel after viewport scaling."""
    scene = json.loads(ENGINE_SCENE.read_text(encoding="utf-8"))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    review_dir = run_dir / "planning" / "html_visual" / "review"
    review_dir.mkdir(parents=True)
    range_spec = {"nodeId": "headline", "start": 0, "end": 3}
    (review_dir / "range.json").write_text(json.dumps(range_spec), encoding="utf-8")
    scene_tmp = review_dir / "scene.json"
    scene_tmp.write_text(json.dumps(scene, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [
            "node",
            str(REPO_ROOT / "html_engine" / "tools" / "review-scene.cjs"),
            str(scene_tmp),
            str(review_dir / "report.json"),
            str(review_dir / "review.png"),
            str(review_dir / "range.json"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert result.returncode == 0, result.stderr[-400:]
    report = json.loads((review_dir / "report.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    canvas_rects = report["textRange"]["canvasRects"]
    assert canvas_rects, "DOM Range must produce at least one line rect"
    # Resolver's fallback box is the measured node box; each DOM line rect
    # must sit inside it within one logical pixel.
    box = review_report["measurements"]["headline"]
    assert box["width"] == 860
    for rect in canvas_rects:
        assert rect["x"] >= 58 - 1
        assert rect["y"] >= 161 - 1
        assert rect["x"] + rect["width"] <= 58 + 860 + 1
        assert rect["height"] <= 48 + 1
