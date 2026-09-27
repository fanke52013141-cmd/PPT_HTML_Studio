# -*- coding: utf-8 -*-
"""勾画标注时间轴构建器(W4):纯函数,确定性输出。

对应交接文档 7.2:

- 每个事件包含 annotation_id、目标引用、受限笔迹(首期由覆盖层按几何
  实时绘制,timeline 记录锚点时间与样式,路径细节数据由 W5 路径生成器
  补充进 strokes 字段)、start/draw_end/hold_end/exit_end、时间来源。
- 边界约束:``0 <= start < draw_end <= hold_end <= exit_end <= slide_duration``;
  时间不足返回 needs_review,不产生负 duration,不静默延长视频。
- 页面事件时间 = 锚点音频内时间 + 用户 offset(offset 只加一次)。
- 同一时刻默认一个主要绘制动作:冲突在容忍窗口(默认 0.2s)内延后,
  超窗口或超出语块结束时间进入 needs_review。显式 manual 定时不重排。
- 静态页/无锚点条目:temporal=manual 时必须带 manual_start_sec。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "TIMELINE_SCHEMA_VERSION",
    "ANNOTATION_TIMELINE_FILE",
    "RESOLVER_VERSION",
    "CONFLICT_TOLERANCE_SEC",
    "TimelineEvent",
    "build_annotation_timeline",
    "timeline_hash",
]

TIMELINE_SCHEMA_VERSION = 1
ANNOTATION_TIMELINE_FILE = "annotation_timeline.json"
RESOLVER_VERSION = "annotation_timeline_v1"
CONFLICT_TOLERANCE_SEC = 0.2
_MIN_DRAW = 0.05
_MIN_EXIT = 0.0


@dataclass(frozen=True)
class TimelineEvent:
    annotation_id: str
    beat_id: Optional[str]
    target_kind: str
    token_ids: Tuple[str, ...]
    style_type: str
    color: str
    opacity: float
    width: int
    padding: int
    seed: int
    start_sec: float
    draw_end_sec: float
    hold_end_sec: float
    exit_end_sec: float
    timing_source: str  # anchor|manual
    scheduling_note: str  # "" | delayed | needs_review 原因
    needs_review: bool
    strokes: Tuple[Dict[str, Any], ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "beat_id": self.beat_id,
            "target": {"kind": self.target_kind, "token_ids": list(self.token_ids)},
            "style": {
                "type": self.style_type, "color": self.color, "opacity": self.opacity,
                "width": self.width, "padding": self.padding, "seed": self.seed,
            },
            "strokes": [dict(s) for s in self.strokes],
            "start_sec": round(self.start_sec, 4),
            "draw_end_sec": round(self.draw_end_sec, 4),
            "hold_end_sec": round(self.hold_end_sec, 4),
            "exit_end_sec": round(self.exit_end_sec, 4),
            "timing_source": self.timing_source,
            "scheduling_note": self.scheduling_note,
            "needs_review": self.needs_review,
        }


def _resolve_start(item: Any, beat_times: Dict[str, Tuple[float, float]]) -> Tuple[Optional[float], str, bool]:
    """返回 (锚点起笔时间, 时间来源, needs_review)。"""
    timing = item.timing
    if timing.trigger_mode == "manual":
        if timing.manual_start_sec is None:
            return None, "manual", True
        return float(timing.manual_start_sec), "manual", False
    if item.anchor is None:
        return None, "anchor", True
    beat = beat_times.get(item.anchor.beat_id)
    if beat is None:
        return None, "anchor", True
    return beat[0] + timing.offset_sec, "anchor", False


def _resolve_hold_end(hold_mode: str, hold_duration: Optional[float], beat_end: Optional[float], slide_duration: float, draw_end: float, exit_duration: float) -> Tuple[Optional[float], Optional[float]]:
    """返回 (hold_end, exit_end);非法窗口返回 (None, None)。

    slide_end 语义:笔迹保留到页尾,退出动画收敛在页尾之内
    (hold_end = 页长 - exit),否则 exit_end 必然越过页长边界。
    """
    if hold_mode == "beat_end":
        return beat_end, (beat_end + exit_duration) if beat_end is not None else None
    if hold_mode == "slide_end":
        hold = slide_duration - exit_duration
        if hold < draw_end:
            return None, None
        return hold, slide_duration
    if hold_mode == "duration":
        if hold_duration is None:
            return None, None
        hold = draw_end + hold_duration
        return hold, hold + exit_duration
    return None, None


def build_annotation_timeline(
    *,
    slide_id: str,
    items: List[Any],
    beat_times: Dict[str, Tuple[float, float]],
    slide_duration: float,
    image_hash: Optional[str],
    narration_hash: Optional[str],
    audio_hash: Optional[str],
    confirmed_input_hashes: Dict[str, Optional[str]],
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """构建页级 annotation_timeline 载荷;返回 (载荷, 全页 needs_review 原因)。

    items 为 AnnotationItem(或同形对象);beat_times: beat_id -> (起点, 终点),
    音频文件起点为 0。页长口径复用 build_remotion_props 的统一值。
    """
    events: List[TimelineEvent] = []
    issues: List[Dict[str, str]] = []
    # 排序:锚点时间 -> 用户顺序 -> 稳定 ID
    def sort_key(item: Any):
        start, _source, _rev = _resolve_start(item, beat_times)
        return (start if start is not None else float("inf"), item.annotation_id)

    ordered = sorted(items, key=sort_key)
    last_main_draw_end = -1.0
    for item in ordered:
        if item.status.content == "disabled":
            continue
        timing = item.timing
        start, source, review = _resolve_start(item, beat_times)
        note = ""
        if start is None:
            issues.append({
                "annotation_id": item.annotation_id,
                "reason": "missing_anchor_time" if source == "anchor" else "missing_manual_start",
            })
            continue
        if start < 0:
            start = 0.0
        draw_duration = max(_MIN_DRAW, float(timing.draw_duration_sec))
        draw_end = start + draw_duration
        beat_end = beat_times.get(item.anchor.beat_id, (None, None))[1] if item.anchor else None
        hold_end, exit_end = _resolve_hold_end(
            timing.hold_mode, timing.hold_duration_sec, beat_end, slide_duration, draw_end,
            max(_MIN_EXIT, float(timing.exit_duration_sec)),
        )
        if hold_end is None or exit_end is None or hold_end < draw_end:
            issues.append({
                "annotation_id": item.annotation_id,
                "reason": "hold_window_invalid" if hold_end is not None else "missing_hold_reference",
            })
            continue
        if draw_end > slide_duration or exit_end > slide_duration:
            issues.append({"annotation_id": item.annotation_id, "reason": "exceeds_slide_duration"})
            continue
        # 冲突调度:manual 不重排;anchor 冲突在容忍窗口内延后
        if start < last_main_draw_end and source == "anchor":
            delayed_start = last_main_draw_end
            if delayed_start - start > CONFLICT_TOLERANCE_SEC:
                issues.append({"annotation_id": item.annotation_id, "reason": "conflict_beyond_tolerance"})
                continue
            shifted = delayed_start
            draw_end = shifted + draw_duration
            if hold_end < draw_end:
                issues.append({"annotation_id": item.annotation_id, "reason": "conflict_exceeds_hold"})
                continue
            note = "delayed"
            start = shifted
            if exit_end > slide_duration:
                issues.append({"annotation_id": item.annotation_id, "reason": "exceeds_slide_duration"})
                continue
        last_main_draw_end = max(last_main_draw_end, draw_end)
        events.append(
            TimelineEvent(
                annotation_id=item.annotation_id,
                beat_id=item.anchor.beat_id if item.anchor else None,
                target_kind=item.target.kind,
                token_ids=tuple(item.target.token_ids),
                style_type=item.style.type,
                color=item.style.color,
                opacity=item.style.opacity,
                width=item.style.width,
                padding=item.style.padding,
                seed=item.style.seed,
                start_sec=start,
                draw_end_sec=draw_end,
                hold_end_sec=hold_end,
                exit_end_sec=exit_end,
                timing_source=source,
                scheduling_note=note,
                needs_review=review,
                strokes=tuple(getattr(item, "strokes", ()) or ()),
            )
        )

    payload = {
        "schema_version": TIMELINE_SCHEMA_VERSION,
        "resolver_version": RESOLVER_VERSION,
        "slide_id": slide_id,
        "canvas": [1920, 1080],
        "inputs": {
            "image_hash": image_hash,
            "narration_hash": narration_hash,
            "audio_hash": audio_hash,
            "confirmed_input_hashes": dict(confirmed_input_hashes or {}),
        },
        "slide_duration_sec": round(float(slide_duration), 4),
        "events": [event.to_dict() for event in events],
        "needs_review": list(issues),
    }
    return payload, issues


def timeline_hash(payload: Dict[str, Any]) -> str:
    """规范化哈希:同输入两次构建必须一致(确定性门)。"""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
