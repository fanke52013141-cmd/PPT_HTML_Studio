# -*- coding: utf-8 -*-
"""annotation_planner 单测:最小载荷、校验、假 ID/坏 JSON、重复剔除、保护。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_contracts import AnnotationPage  # noqa: E402
from annotation_planner import (  # noqa: E402
    AnnotationPlanningError,
    AnnotationPlanner,
    AnnotationPlannerDependencies,
)
from annotation_prompt_templates import (  # noqa: E402
    BUILTIN_ANNOTATION_PLAN_SYSTEM_PROMPT,
    AnnotationPromptStore,
    compose_plan_prompts,
)

SPOKEN = "报名截止时间到9月30日18点"  # "9月30日" = 码点 [7, 12)
BEATS = [{"beat_id": "slide_001_beat_001", "spoken_text": SPOKEN}]
CANDIDATES = [
    {"token_id": "tok_001_0000", "text": "9", "granularity": "char", "polygon": [[100, 300], [130, 300], [130, 340], [100, 340]]},
    {"token_id": "tok_001_0001", "text": "月", "granularity": "char", "polygon": [[130, 300], [160, 300], [160, 340], [130, 340]]},
    {"token_id": "tok_001_0002", "text": "3", "granularity": "char", "polygon": [[160, 300], [190, 300], [190, 340], [160, 340]]},
    {"token_id": "tok_001_0003", "text": "0", "granularity": "char", "polygon": [[190, 300], [220, 300], [220, 340], [190, 340]]},
    {"token_id": "tok_001_0004", "text": "日", "granularity": "char", "polygon": [[220, 300], [250, 300], [250, 340], [220, 340]]},
]


def _store(tmp_path=None):
    class _IO:
        def __init__(self):
            self.files = {}

        def write(self, path, payload):
            self.files[str(path)] = payload

        def read(self, path):
            return self.files.get(str(path))

    io = _IO()
    store = AnnotationPromptStore(
        read_json_file=io.read,
        write_json_atomic=io.write,
        prompts_path_for=lambda run_dir: f"{run_dir}/planning/annotation_prompts.json",
    )
    return store, io


def _planner(store, llm_payload):
    calls = []

    def llm_generate(**kwargs):
        calls.append(kwargs)
        if isinstance(llm_payload, Exception):
            raise llm_payload
        return llm_payload

    return AnnotationPlanner(AnnotationPlannerDependencies(prompt_store=store, llm_generate=llm_generate)), calls


def _run(planner, tmp_path, **kwargs):
    return planner.plan_slide(
        str(tmp_path), "slide_001", BEATS, CANDIDATES, None,
        emphasis=kwargs.pop("emphasis", "moderate"),
        image_hash="a" * 64, narration_hash="b" * 64,
        now_iso="t0", **kwargs,
    )


def test_valid_suggestion_becomes_ai_item(tmp_path):
    store, _io = _store()
    planner, calls = _planner(store, {
        "suggestions": [{
            "beat_id": "slide_001_beat_001",
            "range": [7, 12],
            "quote": "9月30日",
            "target_candidate_ids": ["tok_001_0000", "tok_001_0001", "tok_001_0002", "tok_001_0003", "tok_001_0004"],
            "style": "ellipse",
            "reason": "关键截止日期",
            "ambiguous": False,
        }]
    })
    items, snapshot, issues = _run(planner, tmp_path)
    assert issues == []
    assert len(items) == 1
    item = items[0]
    assert item.protection.source == "ai"
    assert item.status.content == "draft"
    assert item.status.spatial == "valid"
    assert item.target.quote == "9月30日"
    assert len(item.target.token_ids) == 5
    assert len(item.target.polygons) == 5
    assert item.anchor.range_start == 7 and item.anchor.range_end == 12
    # 系统生成字段不在模型输出中,种子/颜色由程序填充
    assert item.style.color == "#F46A38"
    # 快照保留原始建议
    assert snapshot["suggestions"][0]["quote"] == "9月30日"
    # user payload 不含坐标
    sent = json.loads(calls[0]["user_prompt"])
    assert all("polygon" not in c for c in sent["candidates"])
    assert sent["emphasis"] == "moderate"
    assert sent["protected_items"] == []


def test_unknown_token_and_beat_rejected(tmp_path):
    store, _ = _store()
    planner, _ = _planner(store, {
        "suggestions": [
            {"beat_id": "nope", "range": [7, 12], "quote": "9月30日", "target_candidate_ids": ["tok_001_0000"], "style": "ellipse"},
            {"beat_id": "slide_001_beat_001", "range": [7, 12], "quote": "9月30日", "target_candidate_ids": ["tok_ghost"], "style": "ellipse"},
        ]
    })
    items, _snapshot, issues = _run(planner, tmp_path)
    assert items == []
    codes = {issue.code for issue in issues}
    assert "unknown_beat" in codes and "unknown_token" in codes


def test_quote_mismatch_rejected(tmp_path):
    store, _ = _store()
    planner, _ = _planner(store, {
        "suggestions": [{
            "beat_id": "slide_001_beat_001", "range": [7, 12], "quote": "10月1日",
            "target_candidate_ids": ["tok_001_0000"], "style": "underline",
        }]
    })
    items, _snapshot, issues = _run(planner, tmp_path)
    assert items == []
    assert any(issue.code == "quote_mismatch" for issue in issues)


def test_bad_style_and_range_rejected(tmp_path):
    store, _ = _store()
    planner, _ = _planner(store, {
        "suggestions": [{
            "beat_id": "slide_001_beat_001", "range": [0, 1000], "quote": SPOKEN,
            "target_candidate_ids": ["tok_001_0000"], "style": "arrow",
        }]
    })
    items, _snapshot, issues = _run(planner, tmp_path)
    assert items == []
    codes = {issue.code for issue in issues}
    assert "bad_enum" in codes and "too_long" in codes


def test_duplicate_suggestion_deduped(tmp_path):
    store, _ = _store()
    suggestion = {
        "beat_id": "slide_001_beat_001", "range": [7, 12], "quote": "9月30日",
        "target_candidate_ids": ["tok_001_0000"], "style": "ellipse",
    }
    planner, _ = _planner(store, {"suggestions": [suggestion, dict(suggestion, style="underline")]})
    items, _snapshot, issues = _run(planner, tmp_path)
    assert len(items) == 1  # 同语块同短语只保留一条


def test_llm_failure_raises_planning_error(tmp_path):
    store, _ = _store()
    planner, _ = _planner(store, RuntimeError("upstream down"))
    with pytest.raises(AnnotationPlanningError):
        _run(planner, tmp_path)


def test_malformed_structure_reports_not_crashes(tmp_path):
    store, _ = _store()
    planner, _ = _planner(store, {"unexpected": True})
    items, snapshot, issues = _run(planner, tmp_path)
    assert items == []
    assert any(issue.code == "bad_structure" for issue in issues)
    assert snapshot["suggestions"] is None


def test_line_granularity_marks_needs_review(tmp_path):
    store, _ = _store()
    line_candidates = [{"token_id": "line_001_000", "text": "整行文字", "granularity": "line", "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]}]
    planner, _ = _planner(store, {
        "suggestions": [{
            "beat_id": "slide_001_beat_001", "range": [0, 2], "quote": "报名",
            "target_candidate_ids": ["line_001_000"], "style": "highlighter",
        }]
    })
    items, _snapshot, issues = planner.plan_slide(
        str(tmp_path), "slide_001", BEATS, line_candidates, None,
        emphasis="moderate", image_hash="a" * 64, narration_hash="b" * 64, now_iso="t0",
    )
    # 整行候选 quote "报名" 与讲稿切片一致即可;粒度诚实标记 line → needs_review
    assert len(items) == 1
    assert items[0].target.granularity == "line"
    assert items[0].status.spatial == "needs_review"


def test_ambiguous_marks_review_issue(tmp_path):
    store, _ = _store()
    planner, _ = _planner(store, {
        "suggestions": [{
            "beat_id": "slide_001_beat_001", "range": [7, 12], "quote": "9月30日",
            "target_candidate_ids": ["tok_001_0000"], "style": "ellipse",
            "ambiguous": True, "reason": "画面与讲稿写法不同",
        }]
    })
    items, _snapshot, _issues = _run(planner, tmp_path)
    assert items[0].status.spatial == "needs_review"
    assert items[0].review_issues and items[0].review_issues[0]["code"] == "ambiguous"


def test_protected_items_reflect_locked_page(tmp_path):
    store, _ = _store()
    # 构造一页含 locked 条目的页面
    from annotation_contracts import AnnotationItem

    issues = []
    item = AnnotationItem.from_payload({
        "annotation_id": "ann_001",
        "target": {"kind": "region", "layout_revision": None, "token_ids": [], "polygons": [[[0, 0], [10, 0], [10, 10], [0, 10]]], "quote": None, "granularity": "region", "mask_group_ids": []},
        "style": {"type": "ellipse", "color": "#123456", "opacity": 0.5, "width": 3, "padding": 2, "seed": 1},
        "timing": {"trigger_mode": "anchor_start", "offset_sec": 0, "draw_duration_sec": 0.5, "hold_mode": "beat_end", "exit_duration_sec": 0.1},
        "protection": {"source": "manual", "modified_fields": ["style"], "locked": True},
    }, issues, canvas=(1920, 1080))
    assert item is not None and not issues
    page = AnnotationPage(slide_id="slide_001", revision=2, items=(item,))

    planner, calls = _planner(store, {"suggestions": []})
    _run(planner, tmp_path, page=page) if False else planner.plan_slide(
        str(tmp_path), "slide_001", BEATS, CANDIDATES, page,
        emphasis="weak", image_hash="a" * 64, narration_hash="b" * 64, now_iso="t0",
    )
    sent = json.loads(calls[0]["user_prompt"])
    assert sent["protected_items"] == [{"quote": "", "style": "ellipse", "locked": True}]
    assert sent["emphasis"] == "weak"


def test_prompt_store_builtin_and_override_roundtrip(tmp_path):
    store, io = _store()
    prompt, source = store.effective_system_prompt("run1")
    assert source == "builtin" and prompt == BUILTIN_ANNOTATION_PLAN_SYSTEM_PROMPT

    store.save_override("run1", "自定义规则:只圈日期", expected_revision=None, now_iso="t1")
    prompt, source = store.effective_system_prompt("run1")
    assert source == "project" and prompt == "自定义规则:只圈日期"

    # revision 冲突
    import pytest as _pytest
    from fastapi import HTTPException

    with _pytest.raises(HTTPException) as excinfo:
        store.save_override("run1", "x", expected_revision=0, now_iso="t2")
    assert excinfo.value.status_code == 409

    # 用户自定义内容重置后回到内置
    store.reset_override("run1", now_iso="t3")
    prompt, source = store.effective_system_prompt("run1")
    assert source == "builtin"


def test_compose_payload_minimal_fields():
    prompts = compose_plan_prompts(
        system_prompt="S",
        beats=BEATS,
        candidates=CANDIDATES,
        protected_items=[],
        emphasis="moderate",
    )
    payload = json.loads(prompts["user"])
    # 最小必要:无坐标、无多边形、无哈希、无时间字段
    assert set(payload.keys()) == {"beats", "candidates", "protected_items", "emphasis"}
    assert set(payload["beats"][0].keys()) == {"beat_id", "spoken_text"}
    assert set(payload["candidates"][0].keys()) == {"token_id", "text", "granularity"}
