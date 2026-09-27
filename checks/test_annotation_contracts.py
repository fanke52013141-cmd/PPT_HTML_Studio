# -*- coding: utf-8 -*-
"""annotation_contracts 纯校验测试:模型、枚举、范围、Unicode、序列化。"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_contracts import (  # noqa: E402
    ANNOTATION_SCHEMA_VERSION,
    AnnotationAnchor,
    AnnotationItem,
    AnnotationPage,
    AnnotationSettings,
    AnnotationStatus,
    AnnotationStyle,
    AnnotationTiming,
    AnnotationTarget,
    Issue,
    anchor_quote_matches,
    default_annotation_settings,
    next_annotation_id,
    page_item_counts,
    slice_codepoints,
)

CANVAS = (1920, 1080)


def _target_payload(**overrides):
    payload = {
        "kind": "text",
        "layout_revision": 3,
        "token_ids": ["token_07"],
        "polygons": [[[800, 400], [960, 400], [960, 445], [800, 445]]],
        "quote": "9月30日",
        "granularity": "word",
        "mask_group_ids": [],
    }
    payload.update(overrides)
    return payload


def _anchor_payload(**overrides):
    payload = {
        "beat_id": "slide_001_beat_002",
        "offset_unit": "unicode_codepoint",
        "range": [7, 12],
        "quote": "九月三十日",
        "occurrence": 1,
        "context_before": "报名时间到",
        "context_after": "截止",
    }
    payload.update(overrides)
    return payload


def _item_payload(**overrides):
    payload = {
        "schema_version": ANNOTATION_SCHEMA_VERSION,
        "annotation_id": "ann_001",
        "target": _target_payload(),
        "anchor": _anchor_payload(),
        "style": {"type": "ellipse", "color": "#F46A38", "opacity": 0.85, "width": 5, "padding": 8, "seed": 1382},
        "timing": {"trigger_mode": "anchor_start", "offset_sec": -0.1, "draw_duration_sec": 0.6, "hold_mode": "beat_end", "exit_duration_sec": 0.15},
        "status": {"content": "draft", "spatial": "valid", "temporal": "awaiting_audio"},
        "protection": {"source": "ai", "modified_fields": [], "locked": False},
        "inputs": {"image_hash": "a" * 64, "narration_hash": "b" * 64, "audio_hash": None},
    }
    payload.update(overrides)
    return payload


def _parse_item(payload):
    issues: list[Issue] = []
    item = AnnotationItem.from_payload(payload, issues, canvas=CANVAS)
    return item, issues


def test_valid_item_round_trip():
    item, issues = _parse_item(_item_payload())
    assert item is not None and not issues
    restored, restore_issues = _parse_item(item.to_dict())
    assert restored is not None and not restore_issues
    assert restored.to_dict() == item.to_dict()
    assert item.style.color == "#F46A38"
    assert item.timing.offset_sec == -0.1
    assert item.anchor.range_start == 7 and item.anchor.range_end == 12


def test_region_target_without_anchor_allowed():
    payload = _item_payload(
        target=_target_payload(kind="region", token_ids=[], quote=None, granularity="region"),
        anchor=None,
    )
    item, issues = _parse_item(payload)
    assert item is not None and not issues
    assert item.anchor is None


@pytest.mark.parametrize(
    "overrides,path_fragment",
    [
        ({"target": _target_payload(kind="circle")}, "target.kind"),
        ({"target": _target_payload(polygons=[])}, "target.polygons"),
        ({"target": _target_payload(polygons=[[[800, 400], [960, 400], [960, 445], [800, 445], [1, 1]]])}, "bad_polygon"),
        ({"target": _target_payload(polygons=[[[800, 400], [960, 400], [960, 445], [800, 2000]]])}, "out_of_canvas"),
        ({"target": _target_payload(polygons=[[[800, 400], [801, 400], [801, 400], [800, 400]]])}, "degenerate"),
        ({"target": _target_payload(token_ids=[])}, "token_ids"),
        ({"anchor": _anchor_payload(range=[12, 7])}, "bad_range"),
        ({"anchor": _anchor_payload(occurrence=0)}, "occurrence"),
        ({"anchor": _anchor_payload(beat_id="bad id!")}, "beat_id"),
        ({"anchor": _anchor_payload(offset_unit="utf16")}, "offset_unit"),
        ({"style": {"type": "arrow", "color": "#F46A38", "opacity": 0.8, "width": 5, "padding": 8, "seed": 1}}, "style.type"),
        ({"style": {"type": "ellipse", "color": "orange", "opacity": 0.8, "width": 5, "padding": 8, "seed": 1}}, "style.color"),
        ({"style": {"type": "ellipse", "color": "#F46A38", "opacity": 1.5, "width": 5, "padding": 8, "seed": 1}}, "style.opacity"),
        ({"style": {"type": "ellipse", "color": "#F46A38", "opacity": 0.8, "width": 0, "padding": 8, "seed": 1}}, "style.width"),
        ({"timing": {"trigger_mode": "anchor_start", "offset_sec": 0.0, "draw_duration_sec": 0.6, "hold_mode": "duration", "exit_duration_sec": 0.1}}, "hold_duration_sec"),
        ({"timing": {"trigger_mode": "anchor_start", "offset_sec": 0.0, "draw_duration_sec": 0.01, "hold_mode": "beat_end", "exit_duration_sec": 0.1}}, "draw_duration_sec"),
        ({"timing": {"trigger_mode": "anchor_start", "offset_sec": 0.0, "draw_duration_sec": 0.6, "hold_mode": "beat_end", "hold_duration_sec": 3.0, "exit_duration_sec": 0.1}}, "not_allowed"),
        ({"status": {"content": "done", "spatial": "valid", "temporal": "awaiting_audio"}}, "status.content"),
        ({"protection": {"source": "ghost", "modified_fields": [], "locked": False}}, "protection.source"),
        ({"protection": {"source": "ai", "modified_fields": ["nope"], "locked": False}}, "modified_fields"),
        ({"inputs": {"image_hash": "xyz", "narration_hash": None, "audio_hash": None}}, "inputs.image_hash"),
        ({"annotation_id": "annotation-1"}, "annotation_id"),
    ],
)
def test_invalid_payloads_report_structured_issues(overrides, path_fragment):
    item, issues = _parse_item(_item_payload(**overrides))
    joined = ";".join(f"{issue.path}#{issue.code}" for issue in issues)
    assert issues, "expected at least one issue"
    assert path_fragment in joined


def test_nan_and_infinity_rejected():
    item, issues = _parse_item(
        _item_payload(style={"type": "ellipse", "color": "#F46A38", "opacity": float("nan"), "width": 5, "padding": 8, "seed": 1})
    )
    assert any(issue.code == "not_number" for issue in issues)
    item, issues = _parse_item(
        _item_payload(timing={"trigger_mode": "anchor_start", "offset_sec": math.inf, "draw_duration_sec": 0.6, "hold_mode": "beat_end", "exit_duration_sec": 0.1})
    )
    assert any(issue.code == "not_number" for issue in issues)


def test_unicode_codepoint_slicing_and_quote_match():
    # 组合家庭 emoji = 5 个码点(3 人 + 2 个 ZWJ);切片必须按码点而非 UTF-16 单元
    text = "开始👨‍👩‍👧报名9月30日截止"
    assert slice_codepoints(text, 0, 2) == "开始"
    assert len("👨‍👩‍👧") == 5
    # 码点:开0 始1 👨2 ‍3 👩4 ‍5 👧6 报7 名8 9→9 月10 3→11 0→12 日13 截14 止15
    anchor = AnnotationAnchor.from_payload(
        _anchor_payload(range=[9, 14], quote="9月30日"), []
    )
    assert anchor is not None
    assert anchor_quote_matches(text, anchor)
    bad = AnnotationAnchor.from_payload(_anchor_payload(range=[9, 14], quote="十月一日"), [])
    assert not anchor_quote_matches(text, bad)


def test_next_annotation_id_monotonic_no_reuse():
    assert next_annotation_id([]) == "ann_001"
    assert next_annotation_id(["ann_001"]) == "ann_002"
    assert next_annotation_id(["ann_001", "ann_003", "ann_002"]) == "ann_004"
    assert next_annotation_id(["ann_999"]) == "ann_1000"


def test_page_validation_duplicate_ids_and_version():
    payload = {
        "schema_version": ANNOTATION_SCHEMA_VERSION,
        "slide_id": "slide_001",
        "revision": 2,
        "items": [_item_payload(), _item_payload(annotation_id="ann_001")],
        "ai_suggestion_snapshot": None,
        "updated_at": "",
    }
    issues: list[Issue] = []
    page = AnnotationPage.from_payload(payload, issues, canvas=CANVAS)
    assert any(issue.code == "duplicate" for issue in issues)
    assert page is not None and len(page.items) == 1

    issues = []
    AnnotationPage.from_payload({**payload, "schema_version": 99}, issues, canvas=CANVAS)
    assert any(issue.code == "bad_version" for issue in issues)


def test_status_defaults_and_counts():
    settings = default_annotation_settings()
    assert settings.enabled is False and settings.revision == 1
    assert settings.defaults["color"] == "#F46A38"

    assert page_item_counts(None) == {"total": 0, "draft": 0, "confirmed": 0, "disabled": 0}
    item, _ = _parse_item(_item_payload())
    page = AnnotationPage(slide_id="slide_001", revision=1, items=(item,))
    assert page_item_counts(page)["draft"] == 1


def test_status_temporal_enums_accepted():
    for temporal in ("awaiting_audio", "word_aligned", "sentence_fallback", "manual", "failed", "stale"):
        status = AnnotationStatus.from_payload({"content": "draft", "spatial": "valid", "temporal": temporal}, [])
        assert status is not None and status.temporal == temporal


def test_timing_duration_mode_round_trip():
    timing = AnnotationTiming.from_payload(
        {"trigger_mode": "anchor_start", "offset_sec": 0.0, "draw_duration_sec": 0.6, "hold_mode": "duration", "hold_duration_sec": 3.5, "exit_duration_sec": 0.2},
        [],
    )
    assert timing is not None
    payload = timing.to_dict()
    assert payload["hold_duration_sec"] == 3.5
    # 默认值补全后可再次解析
    assert AnnotationTiming.from_payload(payload, []) is not None
