# -*- coding: utf-8 -*-
"""勾画失效矩阵测试(交接 8.2):图片/讲稿/音频三类变化,保留与失效分离。"""
from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_contracts import AnnotationItem  # noqa: E402
from annotation_invalidation import (  # noqa: E402
    invalidate_for_audio_change,
    invalidate_for_image_change,
    invalidate_for_narration_change,
)
from annotation_store import AnnotationStore, AnnotationStoreDependencies  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402

CANVAS = (1920, 1080)


class _Project:
    def __init__(self, run_dir):
        self.run_dir = str(run_dir)


def _store():
    return AnnotationStore(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))


def _confirmed_page(run_dir: Path, *, anchored=True, temporal="word_aligned"):
    from annotation_contracts import (
        AnnotationAnchor,
        AnnotationInputs,
        AnnotationPage,
        AnnotationProtection,
        AnnotationStatus,
        AnnotationStyle,
        AnnotationTarget,
        AnnotationTiming,
    )

    target = AnnotationTarget(
        kind="region" if not anchored else "text",
        layout_revision=1 if anchored else None,
        token_ids=("tok_001_0000",) if anchored else (),
        polygons=(((100, 200), (400, 200), (400, 260), (100, 260)),),
        quote="9月30日" if anchored else None,
        granularity="word" if anchored else "region",
        mask_group_ids=(),
    )
    anchor = AnnotationAnchor(
        beat_id="slide_001_beat_001", range_start=0, range_end=4, quote="报名截止",
        occurrence=1, context_before="", context_after="",
    ) if anchored else None
    item = AnnotationItem(
        annotation_id="ann_001",
        target=target,
        anchor=anchor,
        style=AnnotationStyle(type="ellipse", color="#F46A38", opacity=0.8, width=5, padding=8, seed=1),
        timing=AnnotationTiming(
            trigger_mode="anchor_start", offset_sec=0.0, draw_duration_sec=0.6,
            hold_mode="beat_end", hold_duration_sec=None, exit_duration_sec=0.15,
        ),
        status=AnnotationStatus(content="confirmed", spatial="valid", temporal=temporal),
        protection=AnnotationProtection(source="manual", modified_fields=("style",), locked=True),
        inputs=AnnotationInputs(image_hash="a" * 64, narration_hash="b" * 64, audio_hash=None),
        confirmed_inputs={"image_hash": "a" * 64, "narration_hash": "b" * 64, "revision": 3},
    )
    store = _store()
    from annotation_contracts import AnnotationPage

    store.write_page(str(run_dir), "slide_001", AnnotationPage(slide_id="slide_001", revision=3, items=(item,)))
    (run_dir / "slides" / "slide_001" / "text_layout.json").write_text("{}", encoding="utf-8")
    (run_dir / "slides" / "slide_001" / "annotation_timeline.json").write_text("{}", encoding="utf-8")


def _run_dir(tmp_path):
    (tmp_path / "slides" / "slide_001").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_image_change_removes_layout_and_timeline_marks_stale(tmp_path):
    run_dir = _run_dir(tmp_path)
    _confirmed_page(run_dir, anchored=False)
    project = _Project(run_dir)

    removed = invalidate_for_image_change(project, "slide_001")
    names = {p.name for p in removed}
    assert "text_layout.json" in names and "annotation_timeline.json" in names
    # 布局/时间轴文件已删除
    assert not (run_dir / "slides" / "slide_001" / "text_layout.json").exists()
    assert not (run_dir / "slides" / "slide_001" / "annotation_timeline.json").exists()
    # 条目:stale + 确认失效;几何与锁定证据保留
    page = _store().read_page(str(run_dir), "slide_001", canvas=CANVAS)
    item = page.items[0]
    assert page.revision == 4
    assert item.status.content == "draft"
    assert item.status.spatial == "stale"
    assert item.protection.locked is True
    assert item.protection.modified_fields == ("style",)
    assert item.target.polygons != ()
    assert item.confirmed_inputs is None


def test_narration_change_keeps_spatial_resets_anchor_state(tmp_path):
    run_dir = _run_dir(tmp_path)
    _confirmed_page(run_dir, anchored=True, temporal="word_aligned")
    project = _Project(run_dir)

    removed = invalidate_for_narration_change(project, "slide_001")
    names = {p.name for p in removed}
    assert "annotation_timeline.json" in names
    assert "text_layout.json" not in names  # 文字布局不受讲稿影响
    assert (run_dir / "slides" / "slide_001" / "text_layout.json").exists()

    page = _store().read_page(str(run_dir), "slide_001", canvas=CANVAS)
    item = page.items[0]
    assert item.status.content == "draft"
    assert item.status.temporal == "stale"
    assert item.status.spatial == "valid"  # 空间选择保留
    assert item.style.color == "#F46A38"  # 样式保留
    assert item.protection.locked is True
    assert item.confirmed_inputs is None


def test_audio_change_resets_only_temporal(tmp_path):
    run_dir = _run_dir(tmp_path)
    _confirmed_page(run_dir, anchored=True, temporal="word_aligned")
    project = _Project(run_dir)

    removed = invalidate_for_audio_change(project, "slide_001")
    names = {p.name for p in removed}
    assert "annotation_timeline.json" in names

    page = _store().read_page(str(run_dir), "slide_001", canvas=CANVAS)
    item = page.items[0]
    assert item.status.content == "draft"
    assert item.status.temporal == "awaiting_audio"
    assert item.status.spatial == "valid"
    assert item.anchor.quote == "报名截止"  # 讲稿关联保留
    assert item.confirmed_inputs is None


def test_missing_page_is_noop(tmp_path):
    run_dir = _run_dir(tmp_path)
    project = _Project(run_dir)
    assert invalidate_for_image_change(project, "slide_001") == []
    assert invalidate_for_narration_change(project, "slide_001") == []
    assert invalidate_for_audio_change(project, "slide_001") == []


def test_disabled_items_untouched(tmp_path):
    run_dir = _run_dir(tmp_path)
    _confirmed_page(run_dir, anchored=False)
    # 手工禁用
    page_path = run_dir / "slides" / "slide_001" / "annotations.json"
    page = json.loads(page_path.read_text(encoding="utf-8"))
    page["items"][0]["status"]["content"] = "disabled"
    page_path.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
    project = _Project(run_dir)

    invalidate_for_image_change(project, "slide_001")
    page = _store().read_page(str(run_dir), "slide_001", canvas=CANVAS)
    assert page.items[0].status.content == "disabled"  # 禁用条目保持原状


def test_invalidation_service_image_hook(tmp_path):
    """invalidation_service 的图片清理路径会联动勾画失效。"""
    from invalidation_service import clear_slide_visual_derivatives

    run_dir = _run_dir(tmp_path)
    _confirmed_page(run_dir, anchored=False)
    (run_dir / "reveal_manifest.json").write_text("{}", encoding="utf-8")
    project = _Project(run_dir)

    clear_slide_visual_derivatives(project, "slide_001")
    assert not (run_dir / "slides" / "slide_001" / "text_layout.json").exists()
    page = _store().read_page(str(run_dir), "slide_001", canvas=CANVAS)
    assert page.items[0].status.spatial == "stale"
