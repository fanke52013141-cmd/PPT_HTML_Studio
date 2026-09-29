# -*- coding: utf-8 -*-
"""annotation_timeline 单测:边界约束、audio_start 一次叠加、冲突调度、
manual 不重排、越界 needs_review、确定性哈希。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_contracts import (  # noqa: E402
    AnnotationAnchor,
    AnnotationItem,
    AnnotationStatus,
    AnnotationStyle,
    AnnotationTarget,
    AnnotationTiming,
)
from annotation_timeline import (  # noqa: E402
    build_annotation_timeline,
    timeline_hash,
)

BEAT_TIMES = {
    "slide_001_beat_001": (0.0, 3.0),
    "slide_001_beat_002": (3.0, 6.0),
}
SLIDE_DURATION = 8.0


def _item(
    annotation_id="ann_001",
    beat_id="slide_001_beat_001",
    offset=0.0,
    draw=0.6,
    hold="beat_end",
    hold_duration=None,
    exit=0.15,
    trigger="anchor_start",
    manual_start=None,
    content="confirmed",
):
    target = AnnotationTarget(
        kind="region", layout_revision=None, token_ids=(),
        polygons=(((100, 200), (400, 200), (400, 260), (100, 260)),),
        quote=None, granularity="region", mask_group_ids=(),
    )
    anchor = AnnotationAnchor(
        beat_id=beat_id, range_start=0, range_end=1, quote="x",
        occurrence=1, context_before="", context_after="",
    ) if beat_id else None
    style = AnnotationStyle(type="ellipse", color="#F46A38", opacity=0.8, width=5, padding=8, seed=1)
    timing = AnnotationTiming(
        trigger_mode=trigger, offset_sec=offset, draw_duration_sec=draw,
        hold_mode=hold, hold_duration_sec=hold_duration, exit_duration_sec=exit,
        manual_start_sec=manual_start,
    )
    return AnnotationItem(
        annotation_id=annotation_id, target=target, anchor=anchor, style=style,
        timing=timing, status=AnnotationStatus(content=content, spatial="valid", temporal="word_aligned"),
        protection=None, inputs=None,
    ) if False else _mk(annotation_id, target, anchor, style, timing, content)


def _mk(annotation_id, target, anchor, style, timing, content):
    from annotation_contracts import AnnotationInputs, AnnotationProtection

    return AnnotationItem(
        annotation_id=annotation_id, target=target, anchor=anchor, style=style,
        timing=timing, status=AnnotationStatus(content=content, spatial="valid", temporal="word_aligned"),
        protection=AnnotationProtection(source="manual", modified_fields=(), locked=False),
        inputs=AnnotationInputs(image_hash=None, narration_hash=None, audio_hash=None),
    )


def _build(items, beat_times=None, slide_duration=SLIDE_DURATION, canvas=(1920, 1080)):
    return build_annotation_timeline(
        slide_id="slide_001",
        items=items,
        canvas=canvas,
        beat_times=beat_times if beat_times is not None else BEAT_TIMES,
        slide_duration=slide_duration,
        image_hash="a" * 64,
        narration_hash="b" * 64,
        audio_hash="c" * 64,
        confirmed_input_hashes={},
    )


def test_basic_event_bounds_and_offset_once():
    payload, issues = _build([_item(offset=-0.1, draw=0.6)])
    assert issues == []
    event = payload["events"][0]
    # 音频内起点 0.0 + offset(-0.1) → 钳制到 0
    assert event["start_sec"] == 0.0
    assert event["draw_end_sec"] == 0.6
    assert event["hold_end_sec"] == 3.0  # beat_end
    assert event["exit_end_sec"] == 3.15
    assert 0 <= event["start_sec"] < event["draw_end_sec"] <= event["hold_end_sec"] <= event["exit_end_sec"] <= SLIDE_DURATION
    assert event["timing_source"] == "anchor"


def test_manual_event_retains_user_path_in_timeline():
    from dataclasses import replace

    item = _item(trigger="manual", beat_id=None, manual_start=0.0, hold="slide_end")
    path = [(100, 100), (140, 120), (180, 110)]
    target = replace(item.target, path_points=tuple(path))
    item = replace(item, target=target)
    from annotation_geometry import build_manual_path_stroke

    strokes = [build_manual_path_stroke(path)]
    payload, issues = _build([_with_strokes(item, strokes)])
    assert issues == []
    assert tuple(map(tuple, payload["events"][0]["strokes"][0]["points"])) == tuple(path)


def test_offline_builder_uses_project_canvas_snapshot(tmp_path):
    import json
    from scripts.build_annotation_timeline import _read_canvas

    profile_dir = tmp_path / "planning"
    profile_dir.mkdir()
    (profile_dir / "canvas_profile.json").write_text(
        json.dumps({"width": 1080, "height": 1920}), encoding="utf-8",
    )
    assert _read_canvas(tmp_path) == (1080, 1920)


def test_timeline_preserves_portrait_canvas_dimensions():
    payload, issues = _build([], canvas=(1080, 1920))
    assert issues == []
    assert payload["canvas"] == [1080, 1920]


def _with_strokes(item, strokes):
    class ItemWithStrokes:
        def __init__(self):
            self.__dict__.update(item.__dict__)
            self.strokes = strokes

    return ItemWithStrokes()


def test_audio_start_added_exactly_once():
    # 语块起点本身已含 audio_start;offset 只在起点上加一次
    beat_times = {"slide_001_beat_001": (2.0, 5.0)}
    payload, issues = _build([_item(offset=0.5)], beat_times=beat_times)
    event = payload["events"][0]
    assert issues == []
    assert event["start_sec"] == 2.5  # 2.0 + 0.5,没有二次叠加


def test_hold_modes():
    payload, issues = _build([
        _item("ann_001", hold="slide_end"),
        _item("ann_002", beat_id="slide_001_beat_002", hold="duration", hold_duration=2.0),
    ])
    assert issues == []
    by_id = {e["annotation_id"]: e for e in payload["events"]}
    # slide_end:退出收敛在页尾内(hold = 页长 - exit)
    assert by_id["ann_001"]["hold_end_sec"] == SLIDE_DURATION - 0.15
    assert by_id["ann_001"]["exit_end_sec"] == SLIDE_DURATION
    # duration: draw_end(3.0+0.6=3.6) + 2.0
    assert by_id["ann_002"]["hold_end_sec"] == 5.6
    assert by_id["ann_002"]["exit_end_sec"] == 5.75


def test_conflict_within_tolerance_delayed():
    # 两条锚点同起点:首笔 0.15s,第二条延后 0.15s ≤ 容忍窗口
    payload, issues = _build([_item("ann_001", draw=0.15), _item("ann_002", draw=0.4)])
    by_id = {e["annotation_id"]: e for e in payload["events"]}
    assert issues == []
    assert by_id["ann_002"]["scheduling_note"] == "delayed"
    assert by_id["ann_002"]["start_sec"] == by_id["ann_001"]["draw_end_sec"]


def test_conflict_beyond_tolerance_needs_review():
    # 第一条绘制 1.0s,第二条延后 1.0 > 0.2 容忍 → needs_review
    payload, issues = _build([
        _item("ann_001", draw=1.0),
        _item("ann_002", draw=0.4),
    ])
    assert any(issue["annotation_id"] == "ann_002" and issue["reason"] == "conflict_beyond_tolerance" for issue in issues)
    by_id = {e["annotation_id"]: e for e in payload["events"]}
    assert "ann_002" not in by_id  # 被拒条目不生成事件


def test_manual_timing_not_rescheduled():
    payload, issues = _build([
        _item("ann_001", trigger="manual", manual_start=1.0, draw=1.0),
        _item("ann_002", trigger="manual", manual_start=1.2, draw=0.4),
    ])
    assert issues == []
    by_id = {e["annotation_id"]: e for e in payload["events"]}
    # manual 起笔不因冲突重排
    assert by_id["ann_002"]["start_sec"] == 1.2
    assert by_id["ann_002"]["timing_source"] == "manual"
    assert by_id["ann_002"]["scheduling_note"] == ""


def test_exceeds_slide_duration_reported():
    # 语块终点 3.0 超过页长 0.8:beat_end hold 使 exit_end 越界
    payload, issues = _build(
        [_item()],
        beat_times={"slide_001_beat_001": (0.0, 3.0)},
        slide_duration=0.8,
    )
    assert any(issue["reason"] == "exceeds_slide_duration" for issue in issues)
    assert payload["events"] == []


def test_missing_anchor_time_reported():
    payload, issues = _build([_item(beat_id="slide_001_beat_099")])
    assert any(issue["reason"] == "missing_anchor_time" for issue in issues)
    assert payload["events"] == []


def test_manual_without_start_reported():
    payload, issues = _build([_item(trigger="manual", manual_start=None)])
    assert any(issue["reason"] == "missing_manual_start" for issue in issues)


def test_disabled_items_excluded():
    payload, issues = _build([_item(content="disabled")])
    assert payload["events"] == [] and issues == []


def test_deterministic_hash():
    payload1, _ = _build([_item("ann_001"), _item("ann_002")])
    payload2, _ = _build([_item("ann_001"), _item("ann_002")])
    assert timeline_hash(payload1) == timeline_hash(payload2)
    payload3, _ = _build([_item("ann_001", offset=0.1), _item("ann_002")])
    assert timeline_hash(payload1) != timeline_hash(payload3)


def test_inputs_recorded():
    payload, _ = _build([_item()])
    assert payload["inputs"]["image_hash"] == "a" * 64
    assert payload["resolver_version"] == "annotation_timeline_v1"
    assert payload["slide_duration_sec"] == SLIDE_DURATION
