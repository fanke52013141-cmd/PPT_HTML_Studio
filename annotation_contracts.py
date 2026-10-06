# -*- coding: utf-8 -*-
"""勾画标注模块的内部契约:模型、枚举、严格校验与序列化。

对应《勾画标注模块开发与验收交接》第 5 节。职责边界:

- 纯模块:不导入 server、FastAPI、数据库或任何应用装配代码;所有函数
  都是显式入参的纯函数/不可变数据类。
- 校验产出结构化 ``Issue`` 列表(path/code/message),由路由层翻译为
  422/409 等响应;契约层不直接抛 HTTP 异常。
- 字符范围统一为 Unicode 码点 ``[start, end)``(Python str 原生索引即
  码点);UTF-16 转换是前端的显式职责,组合字符边界由交互层遵守。
- 颜色为 ``#RRGGBB``;数值必须有限(NaN/Infinity 一律拒绝,写出时
  ``allow_nan=False`` 兜底)。
- 服务端分配 annotation_id/revision;客户端提交只带内容与 expected_revision。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "ANNOTATION_SCHEMA_VERSION",
    "ANNOTATION_SETTINGS_FILE",
    "ANNOTATION_PAGE_FILE",
    "DEFAULT_CANVAS",
    "LIMITS",
    "Issue",
    "collect_issues",
    "slice_codepoints",
    "anchor_quote_matches",
    "next_annotation_id",
    "AnnotationTarget",
    "AnnotationAnchor",
    "AnnotationStyle",
    "AnnotationTiming",
    "AnnotationStatus",
    "AnnotationProtection",
    "AnnotationInputs",
    "AnnotationItem",
    "AnnotationPage",
    "AnnotationSettings",
    "default_annotation_settings",
    "page_item_counts",
]

ANNOTATION_SCHEMA_VERSION = 1
ANNOTATION_SETTINGS_FILE = "annotation_settings.json"
ANNOTATION_PAGE_FILE = "annotations.json"

# 标准画布;W3 文字布局层落地后由 canvas profile 显式传入,禁止在组件里
# 重复硬编码(此处常量仅作缺省回退)。
DEFAULT_CANVAS: Tuple[int, int] = (1920, 1080)

# 内容状态
CONTENT_STATUSES = ("draft", "confirmed", "disabled")
# 空间状态
SPATIAL_STATUSES = ("valid", "needs_review", "stale")
# 时间状态
TEMPORAL_STATUSES = (
    "awaiting_audio",
    "word_aligned",
    "sentence_fallback",
    "manual",
    "failed",
    "stale",
)
# 样式类型(首期三种;后续版本扩展)
STYLE_TYPES = ("ellipse", "underline", "highlighter")
# 保留方式
HOLD_MODES = ("beat_end", "slide_end", "duration")
# 触发模式
TRIGGER_MODES = ("anchor_start", "manual")
# 目标类型
TARGET_KINDS = ("text", "region")
# 保护来源
PROTECTION_SOURCES = ("ai", "manual")
# 强调程度
EMPHASIS_LIMITS = {"weak": 1, "moderate": 2, "strong": 3}
EMPHASIS_LEVELS = tuple(EMPHASIS_LIMITS)
RECOMMENDATION_CATEGORIES = ("conclusion", "contrast", "condition", "action", "evidence", "concept")

# 用户可编辑的条目字段(服务端 diff 维护 modified_fields 的合法域)
MODIFIABLE_FIELDS = (
    "target",
    "anchor",
    "style",
    "timing",
    "protection.locked",
    "status.content",
)

LIMITS = {
    "max_items_per_slide": 40,
    "max_polygons_per_target": 12,
    "max_path_points_per_target": 512,
    "max_ops_per_request": 80,
    "quote_max_chars": 200,
    "context_max_chars": 120,
    "reason_max_chars": 500,
}

_ANNOTATION_ID_RE = re.compile(r"^ann_[0-9]{3,}$")
_BEAT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,96}$")
_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Issue:
    """一条结构化校验问题;path 定位到 JSON 字段路径。"""

    path: str
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


def collect_issues(issues: Sequence[Issue]) -> List[Dict[str, str]]:
    return [issue.to_dict() for issue in issues]


# ---------------------------------------------------------------- 基础校验


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_int(
    issues: List[Issue], path: str, value: Any, *, minimum: int, maximum: int
) -> Optional[int]:
    if not _is_int(value):
        issues.append(Issue(path, "not_int", f"{path} 必须是整数"))
        return None
    if not (minimum <= value <= maximum):
        issues.append(Issue(path, "out_of_range", f"{path} 必须在 [{minimum}, {maximum}] 内,收到 {value}"))
        return None
    return value


def _check_number(
    issues: List[Issue], path: str, value: Any, *, minimum: float, maximum: float
) -> Optional[float]:
    if not _finite_number(value):
        issues.append(Issue(path, "not_number", f"{path} 必须是有限数值"))
        return None
    if not (minimum <= float(value) <= maximum):
        issues.append(
            Issue(path, "out_of_range", f"{path} 必须在 [{minimum}, {maximum}] 内,收到 {value}")
        )
        return None
    return float(value)


def _check_str(
    issues: List[Issue], path: str, value: Any, *, maximum: int, allow_empty: bool = False
) -> Optional[str]:
    if not isinstance(value, str):
        issues.append(Issue(path, "not_str", f"{path} 必须是字符串"))
        return None
    if not value and not allow_empty:
        issues.append(Issue(path, "empty", f"{path} 不能为空"))
        return None
    if len(value) > maximum:
        issues.append(Issue(path, "too_long", f"{path} 长度超过 {maximum}"))
        return None
    return value


def _check_enum(issues: List[Issue], path: str, value: Any, allowed: Sequence[str]) -> Optional[str]:
    if value not in allowed:
        issues.append(Issue(path, "bad_enum", f"{path} 必须是 {list(allowed)} 之一,收到 {value!r}"))
        return None
    return value


def _check_color(issues: List[Issue], path: str, value: Any) -> Optional[str]:
    if not isinstance(value, str) or not _COLOR_RE.match(value):
        issues.append(Issue(path, "bad_color", f"{path} 必须是 #RRGGBB 颜色"))
        return None
    return value.upper()


def _check_hash(issues: List[Issue], path: str, value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        issues.append(Issue(path, "bad_hash", f"{path} 必须是 64 位小写十六进制 sha256 或 null"))
        return None
    return value


def _check_points(
    issues: List[Issue], path: str, value: Any, canvas: Tuple[int, int]
) -> Optional[List[List[int]]]:
    if not isinstance(value, list) or not value:
        issues.append(Issue(path, "bad_polygon", f"{path} 必须是非空多边形数组"))
        return None
    if len(value) > LIMITS["max_polygons_per_target"]:
        issues.append(Issue(path, "too_many", f"{path} 多边形数量超过 {LIMITS['max_polygons_per_target']}"))
        return None
    result: List[List[int]] = []
    for index, polygon in enumerate(value):
        poly_path = f"{path}[{index}]"
        if not isinstance(polygon, list) or len(polygon) != 4:
            issues.append(Issue(poly_path, "bad_polygon", f"{poly_path} 必须是 4 个 [x, y] 顶点"))
            return None
        points: List[List[int]] = []
        for point_index, point in enumerate(polygon):
            if not isinstance(point, list) or len(point) != 2 or not all(_is_int(v) for v in point):
                issues.append(Issue(poly_path, "bad_point", f"{poly_path}[{point_index}] 必须是 [x, y] 整数"))
                return None
            x, y = point
            if not (0 <= x <= canvas[0] and 0 <= y <= canvas[1]):
                issues.append(
                    Issue(poly_path, "out_of_canvas", f"{poly_path}[{point_index}] 超出画布 {list(canvas)}")
                )
                return None
            points.append([x, y])
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        if max(xs) - min(xs) < 1 or max(ys) - min(ys) < 1:
            issues.append(Issue(poly_path, "degenerate", f"{poly_path} 退化(宽或高小于 1 像素)"))
            return None
        result.append(points)
    return result


def slice_codepoints(text: str, start: int, end: int) -> str:
    """按 Unicode 码点切片 ``[start, end)``;越界时钳制。"""
    return text[max(0, start): max(0, end)]


def anchor_quote_matches(text: str, anchor: "AnnotationAnchor") -> bool:
    """校验 anchor.quote 与码点切片一致(occurrence 仅辅助消歧)。"""
    return slice_codepoints(text, anchor.range_start, anchor.range_end) == anchor.quote


# ---------------------------------------------------------------- 模型


@dataclass(frozen=True)
class AnnotationTarget:
    """画面目标:文字候选引用或人工区域几何。"""

    kind: str
    layout_revision: Optional[int]
    token_ids: Tuple[str, ...]
    polygons: Tuple[Tuple[Tuple[int, int], ...], ...]
    quote: Optional[str]
    granularity: str
    mask_group_ids: Tuple[str, ...]
    path_points: Tuple[Tuple[int, int], ...] = ()
    path_strokes: Tuple[Tuple[Tuple[int, int], ...], ...] = ()

    @staticmethod
    def from_payload(
        data: Any, issues: List[Issue], *, canvas: Tuple[int, int], path: str = "target"
    ) -> Optional["AnnotationTarget"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        kind = _check_enum(issues, f"{path}.kind", data.get("kind"), TARGET_KINDS)
        layout_revision = data.get("layout_revision")
        if layout_revision is not None:
            layout_revision = _check_int(
                issues, f"{path}.layout_revision", layout_revision, minimum=1, maximum=10**9
            )
        raw_token_ids = data.get("token_ids", [])
        token_ids: Tuple[str, ...] = ()
        if kind == "text":
            if not isinstance(raw_token_ids, list) or not raw_token_ids:
                issues.append(Issue(f"{path}.token_ids", "required", "文字目标必须携带非空 token_ids"))
            else:
                token_ids = tuple(
                    _check_str(issues, f"{path}.token_ids[{i}]", v, maximum=96)
                    or str(v)
                    for i, v in enumerate(raw_token_ids)
                )
        polygons = _check_points(issues, f"{path}.polygons", data.get("polygons"), canvas)
        raw_path = data.get("path_points", [])
        path_points: Tuple[Tuple[int, int], ...] = ()
        if raw_path:
            if kind != "region":
                issues.append(Issue(f"{path}.path_points", "bad_kind", "自由笔迹只能用于区域目标"))
            elif not isinstance(raw_path, list) or len(raw_path) < 2:
                issues.append(Issue(f"{path}.path_points", "bad_path", "自由笔迹至少需要 2 个点"))
            elif len(raw_path) > LIMITS["max_path_points_per_target"]:
                issues.append(Issue(f"{path}.path_points", "too_many", f"自由笔迹点数不能超过 {LIMITS['max_path_points_per_target']}"))
            else:
                checked_path: List[Tuple[int, int]] = []
                for index, point in enumerate(raw_path):
                    if not isinstance(point, list) or len(point) != 2 or not all(_is_int(v) for v in point):
                        issues.append(Issue(f"{path}.path_points[{index}]", "bad_point", "笔迹点必须是 [x, y] 整数"))
                        checked_path = []
                        break
                    x, y = point
                    if not (0 <= x <= canvas[0] and 0 <= y <= canvas[1]):
                        issues.append(Issue(f"{path}.path_points[{index}]", "out_of_canvas", f"笔迹点超出画布 {list(canvas)}"))
                        checked_path = []
                        break
                    checked_path.append((x, y))
                if checked_path and len(set(checked_path)) >= 2:
                    if polygons:
                        target_xs = [point[0] for polygon in polygons for point in polygon]
                        target_ys = [point[1] for polygon in polygons for point in polygon]
                        bounds = (min(target_xs), min(target_ys), max(target_xs), max(target_ys))
                        if any(not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]) for x, y in checked_path):
                            issues.append(Issue(f"{path}.path_points", "outside_target", "自由笔迹必须位于区域目标范围内"))
                        else:
                            path_points = tuple(checked_path)
                    else:
                        path_points = tuple(checked_path)
                elif checked_path:
                    issues.append(Issue(f"{path}.path_points", "degenerate", "自由笔迹至少要包含 2 个不同的点"))
        path_strokes = ()
        raw_strokes = data.get("path_strokes", [])
        if raw_strokes:
            if raw_path:
                issues.append(Issue(f"{path}.path_strokes", "ambiguous_path", "不能同时提供单笔与多笔轨迹"))
            elif not isinstance(raw_strokes, list) or len(raw_strokes) > 12:
                issues.append(Issue(f"{path}.path_strokes", "bad_path", "多笔轨迹必须为最多 12 笔的数组"))
            else:
                checked_strokes = []
                for index, points in enumerate(raw_strokes):
                    single = AnnotationTarget.from_payload(
                        {**data, "path_strokes": [], "path_points": points}, issues,
                        canvas=canvas, path=f"{path}.path_strokes[{index}]",
                    )
                    if single and single.path_points:
                        checked_strokes.append(single.path_points)
                    else:
                        issues.append(Issue(f"{path}.path_strokes[{index}]", "bad_path", "每笔至少需要两个不同的点"))
                path_strokes = tuple(checked_strokes)
        elif not isinstance(raw_strokes, list):
            issues.append(Issue(f"{path}.path_strokes", "bad_path", "多笔轨迹必须为数组"))
        quote = data.get("quote")
        if kind == "text":
            quote = _check_str(
                issues, f"{path}.quote", quote, maximum=LIMITS["quote_max_chars"], allow_empty=True
            )
        granularity = _check_enum(
            issues, f"{path}.granularity", data.get("granularity", "word"), ("char", "word", "line", "region")
        )
        raw_groups = data.get("mask_group_ids", [])
        mask_group_ids: Tuple[str, ...] = ()
        if raw_groups:
            if not isinstance(raw_groups, list):
                issues.append(Issue(f"{path}.mask_group_ids", "not_list", f"{path}.mask_group_ids 必须是数组"))
            else:
                mask_group_ids = tuple(
                    _check_str(issues, f"{path}.mask_group_ids[{i}]", v, maximum=96) or str(v)
                    for i, v in enumerate(raw_groups)
                )
        if None in (kind, polygons, granularity):
            return None
        return AnnotationTarget(
            kind=kind or "region",
            layout_revision=layout_revision,
            token_ids=tuple(t for t in token_ids if t),
            polygons=tuple(tuple((p[0], p[1]) for p in polygon) for polygon in polygons),
            quote=quote,
            granularity=granularity or "region",
            mask_group_ids=mask_group_ids,
            path_points=path_points,
            path_strokes=path_strokes,
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "kind": self.kind,
            "layout_revision": self.layout_revision,
            "token_ids": list(self.token_ids),
            "polygons": [[list(point) for point in polygon] for polygon in self.polygons],
            "quote": self.quote,
            "granularity": self.granularity,
            "mask_group_ids": list(self.mask_group_ids),
        }
        if self.path_points:
            payload["path_points"] = [list(point) for point in self.path_points]
        if self.path_strokes:
            payload["path_strokes"] = [[list(point) for point in stroke] for stroke in self.path_strokes]
        return payload


@dataclass(frozen=True)
class AnnotationAnchor:
    """讲稿锚点:beat + 码点范围 + 消歧上下文。"""

    beat_id: str
    range_start: int
    range_end: int
    quote: str
    occurrence: int
    context_before: str
    context_after: str

    @staticmethod
    def from_payload(data: Any, issues: List[Issue], *, path: str = "anchor") -> Optional["AnnotationAnchor"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        beat_id = _check_str(issues, f"{path}.beat_id", data.get("beat_id"), maximum=96)
        if beat_id is not None and not _BEAT_ID_RE.match(beat_id):
            issues.append(Issue(f"{path}.beat_id", "bad_id", "beat_id 只能包含字母、数字、下划线和连字符"))
            beat_id = None
        unit = data.get("offset_unit", "unicode_codepoint")
        if unit != "unicode_codepoint":
            issues.append(Issue(f"{path}.offset_unit", "bad_enum", "offset_unit 仅支持 unicode_codepoint"))
        range_start = _check_int(issues, f"{path}.range[0]", (data.get("range") or [None, None])[0], minimum=0, maximum=10**6)
        range_end = _check_int(issues, f"{path}.range[1]", (data.get("range") or [None, None])[1], minimum=0, maximum=10**6)
        if range_start is not None and range_end is not None and range_start >= range_end:
            issues.append(Issue(f"{path}.range", "bad_range", "range 必须满足 start < end"))
        quote = _check_str(issues, f"{path}.quote", data.get("quote"), maximum=LIMITS["quote_max_chars"])
        occurrence = _check_int(
            issues, f"{path}.occurrence", data.get("occurrence", 1), minimum=1, maximum=999
        )
        context_before = _check_str(
            issues, f"{path}.context_before", data.get("context_before", ""), maximum=LIMITS["context_max_chars"], allow_empty=True
        ) or ""
        context_after = _check_str(
            issues, f"{path}.context_after", data.get("context_after", ""), maximum=LIMITS["context_max_chars"], allow_empty=True
        ) or ""
        if None in (beat_id, quote, occurrence) or range_start is None or range_end is None:
            return None
        return AnnotationAnchor(
            beat_id=beat_id or "",
            range_start=range_start,
            range_end=range_end,
            quote=quote or "",
            occurrence=occurrence or 1,
            context_before=context_before,
            context_after=context_after,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "offset_unit": "unicode_codepoint",
            "range": [self.range_start, self.range_end],
            "quote": self.quote,
            "occurrence": self.occurrence,
            "context_before": self.context_before,
            "context_after": self.context_after,
        }


@dataclass(frozen=True)
class AnnotationStyle:
    """笔迹样式:UI 中 opacity 显示为 0–100 的"笔迹浓度",存储为 0–1。"""

    type: str
    color: str
    opacity: float
    width: int
    padding: int
    seed: int

    @staticmethod
    def from_payload(data: Any, issues: List[Issue], *, path: str = "style") -> Optional["AnnotationStyle"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        style_type = _check_enum(issues, f"{path}.type", data.get("type"), STYLE_TYPES)
        color = _check_color(issues, f"{path}.color", data.get("color"))
        opacity = _check_number(issues, f"{path}.opacity", data.get("opacity"), minimum=0.0, maximum=1.0)
        width = _check_int(issues, f"{path}.width", data.get("width"), minimum=1, maximum=40)
        padding = _check_int(issues, f"{path}.padding", data.get("padding"), minimum=0, maximum=80)
        seed = _check_int(issues, f"{path}.seed", data.get("seed"), minimum=0, maximum=2**31 - 1)
        if None in (style_type, color, opacity, width, padding, seed):
            return None
        return AnnotationStyle(
            type=style_type or "ellipse",
            color=color or "#F46A38",
            opacity=float(opacity or 0.85),
            width=int(width or 5),
            padding=int(padding or 8),
            seed=int(seed or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "color": self.color,
            "opacity": self.opacity,
            "width": self.width,
            "padding": self.padding,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class AnnotationTiming:
    """触发与保留:offset 为相对锚点起点的用户偏移(秒)。

    trigger_mode=manual 时必须提供 manual_start_sec(音频文件起点为 0 的
    显式起笔时间);此时该时间不参与自动重排。
    """

    trigger_mode: str
    offset_sec: float
    draw_duration_sec: float
    hold_mode: str
    hold_duration_sec: Optional[float]
    exit_duration_sec: float
    manual_start_sec: Optional[float] = None
    time_reference: str = "slide"

    @staticmethod
    def from_payload(data: Any, issues: List[Issue], *, path: str = "timing") -> Optional["AnnotationTiming"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        trigger = _check_enum(issues, f"{path}.trigger_mode", data.get("trigger_mode", "anchor_start"), TRIGGER_MODES)
        offset = _check_number(issues, f"{path}.offset_sec", data.get("offset_sec", 0.0), minimum=-5.0, maximum=5.0)
        draw_duration = _check_number(
            issues, f"{path}.draw_duration_sec", data.get("draw_duration_sec"), minimum=0.05, maximum=10.0
        )
        hold_mode = _check_enum(issues, f"{path}.hold_mode", data.get("hold_mode", "beat_end"), HOLD_MODES)
        hold_duration: Optional[float] = None
        if hold_mode == "duration":
            hold_duration = _check_number(
                issues, f"{path}.hold_duration_sec", data.get("hold_duration_sec"), minimum=0.05, maximum=120.0
            )
        elif data.get("hold_duration_sec") is not None:
            issues.append(
                Issue(f"{path}.hold_duration_sec", "not_allowed", "仅 hold_mode=duration 允许 hold_duration_sec")
            )
        exit_duration = _check_number(
            issues, f"{path}.exit_duration_sec", data.get("exit_duration_sec", 0.15), minimum=0.0, maximum=5.0
        )
        manual_start: Optional[float] = None
        reference = _check_enum(issues, f"{path}.time_reference", data.get("time_reference", "slide"), ("slide", "audio"))
        if data.get("manual_start_sec") is not None:
            manual_start = _check_number(
                issues, f"{path}.manual_start_sec", data.get("manual_start_sec"), minimum=0.0, maximum=3600.0
            )
        if trigger == "manual" and manual_start is None:
            issues.append(Issue(f"{path}.manual_start_sec", "required", "manual 触发必须提供 manual_start_sec"))
        if trigger != "manual" and data.get("manual_start_sec") is not None:
            issues.append(Issue(f"{path}.manual_start_sec", "not_allowed", "仅 trigger_mode=manual 允许 manual_start_sec"))
        if None in (trigger, offset, draw_duration, hold_mode, exit_duration):
            return None
        return AnnotationTiming(
            trigger_mode=trigger or "anchor_start",
            offset_sec=float(offset or 0.0),
            draw_duration_sec=float(draw_duration or 0.6),
            hold_mode=hold_mode or "beat_end",
            hold_duration_sec=hold_duration,
            exit_duration_sec=float(exit_duration or 0.0),
            manual_start_sec=manual_start,
            time_reference=reference or "slide",
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "trigger_mode": self.trigger_mode,
            "offset_sec": self.offset_sec,
            "draw_duration_sec": self.draw_duration_sec,
            "hold_mode": self.hold_mode,
            "exit_duration_sec": self.exit_duration_sec,
        }
        if self.hold_mode == "duration":
            payload["hold_duration_sec"] = self.hold_duration_sec
        if self.trigger_mode == "manual":
            payload["manual_start_sec"] = self.manual_start_sec
            payload["time_reference"] = self.time_reference
        return payload


@dataclass(frozen=True)
class AnnotationStatus:
    content: str
    spatial: str
    temporal: str

    @staticmethod
    def from_payload(data: Any, issues: List[Issue], *, path: str = "status") -> Optional["AnnotationStatus"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        content = _check_enum(issues, f"{path}.content", data.get("content", "draft"), CONTENT_STATUSES)
        spatial = _check_enum(issues, f"{path}.spatial", data.get("spatial", "valid"), SPATIAL_STATUSES)
        temporal = _check_enum(issues, f"{path}.temporal", data.get("temporal", "awaiting_audio"), TEMPORAL_STATUSES)
        if None in (content, spatial, temporal):
            return None
        return AnnotationStatus(content=content or "draft", spatial=spatial or "valid", temporal=temporal or "awaiting_audio")

    def to_dict(self) -> Dict[str, Any]:
        return {"content": self.content, "spatial": self.spatial, "temporal": self.temporal}


@dataclass(frozen=True)
class AnnotationProtection:
    source: str
    modified_fields: Tuple[str, ...]
    locked: bool

    @staticmethod
    def from_payload(data: Any, issues: List[Issue], *, path: str = "protection") -> Optional["AnnotationProtection"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        source = _check_enum(issues, f"{path}.source", data.get("source", "manual"), PROTECTION_SOURCES)
        raw_modified = data.get("modified_fields", [])
        modified_fields: Tuple[str, ...] = ()
        if isinstance(raw_modified, list):
            for value in raw_modified:
                if value not in MODIFIABLE_FIELDS:
                    issues.append(Issue(f"{path}.modified_fields", "bad_field", f"未知可修改字段 {value!r}"))
                else:
                    modified_fields += (value,)
        else:
            issues.append(Issue(f"{path}.modified_fields", "not_list", "modified_fields 必须是数组"))
        locked = data.get("locked", False)
        if not isinstance(locked, bool):
            issues.append(Issue(f"{path}.locked", "not_bool", "locked 必须是布尔"))
            locked = False
        if source is None:
            return None
        return AnnotationProtection(source=source, modified_fields=modified_fields, locked=bool(locked))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "modified_fields": list(self.modified_fields),
            "locked": self.locked,
        }


@dataclass(frozen=True)
class AnnotationInputs:
    """输入版本摘要:服务端计算,客户端不可伪造。"""

    image_hash: Optional[str]
    narration_hash: Optional[str]
    audio_hash: Optional[str]

    @staticmethod
    def from_payload(data: Any, issues: List[Issue], *, path: str = "inputs") -> Optional["AnnotationInputs"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        image_hash = _check_hash(issues, f"{path}.image_hash", data.get("image_hash"))
        narration_hash = _check_hash(issues, f"{path}.narration_hash", data.get("narration_hash"))
        audio_hash = _check_hash(issues, f"{path}.audio_hash", data.get("audio_hash"))
        return AnnotationInputs(image_hash=image_hash, narration_hash=narration_hash, audio_hash=audio_hash)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_hash": self.image_hash,
            "narration_hash": self.narration_hash,
            "audio_hash": self.audio_hash,
        }


@dataclass(frozen=True)
class AnnotationItem:
    """单条标注(规范结构见交接文档 5.2)。"""

    annotation_id: str
    target: AnnotationTarget
    anchor: Optional[AnnotationAnchor]
    style: AnnotationStyle
    timing: AnnotationTiming
    status: AnnotationStatus
    protection: AnnotationProtection
    inputs: AnnotationInputs
    accepted_degradation: Optional[Dict[str, Any]] = None
    review_issues: Tuple[Dict[str, Any], ...] = ()
    confirmed_inputs: Optional[Dict[str, Any]] = None
    recommendation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "schema_version": ANNOTATION_SCHEMA_VERSION,
            "annotation_id": self.annotation_id,
            "target": self.target.to_dict(),
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "style": self.style.to_dict(),
            "timing": self.timing.to_dict(),
            "status": self.status.to_dict(),
            "protection": self.protection.to_dict(),
            "inputs": self.inputs.to_dict(),
            "accepted_degradation": self.accepted_degradation,
            "review_issues": [dict(issue) for issue in self.review_issues],
            "confirmed_inputs": self.confirmed_inputs,
        }
        if self.recommendation:
            payload["recommendation"] = dict(self.recommendation)
        return payload

    @staticmethod
    def from_payload(
        data: Any,
        issues: List[Issue],
        *,
        canvas: Tuple[int, int],
        path: str = "item",
        require_id: bool = True,
    ) -> Optional["AnnotationItem"]:
        if not isinstance(data, dict):
            issues.append(Issue(path, "not_object", f"{path} 必须是对象"))
            return None
        annotation_id = data.get("annotation_id")
        if require_id:
            if not isinstance(annotation_id, str) or not _ANNOTATION_ID_RE.match(annotation_id):
                issues.append(Issue(f"{path}.annotation_id", "bad_id", "annotation_id 必须形如 ann_001"))
                annotation_id = None
        else:
            annotation_id = None
        target = AnnotationTarget.from_payload(data.get("target"), issues, canvas=canvas, path=f"{path}.target")
        anchor_data = data.get("anchor")
        anchor = None
        if anchor_data is not None:
            anchor = AnnotationAnchor.from_payload(anchor_data, issues, path=f"{path}.anchor")
        style = AnnotationStyle.from_payload(data.get("style"), issues, path=f"{path}.style")
        timing = AnnotationTiming.from_payload(data.get("timing"), issues, path=f"{path}.timing")
        status = AnnotationStatus.from_payload(data.get("status", {}), issues, path=f"{path}.status")
        protection = AnnotationProtection.from_payload(
            data.get("protection", {}), issues, path=f"{path}.protection"
        )
        inputs = AnnotationInputs.from_payload(data.get("inputs", {}), issues, path=f"{path}.inputs")
        if None in (target, style, timing, status, protection, inputs):
            return None
        confirmed_inputs = data.get("confirmed_inputs")
        if confirmed_inputs is not None and not isinstance(confirmed_inputs, dict):
            issues.append(Issue(f"{path}.confirmed_inputs", "not_object", "confirmed_inputs 必须是对象或 null"))
            confirmed_inputs = None
        accepted = data.get("accepted_degradation")
        if accepted is not None and not isinstance(accepted, dict):
            issues.append(Issue(f"{path}.accepted_degradation", "not_object", "accepted_degradation 必须是对象或 null"))
            accepted = None
        review_issues = data.get("review_issues") or []
        review_tuple: Tuple[Dict[str, Any], ...] = ()
        if isinstance(review_issues, list):
            for review_entry in review_issues:
                if isinstance(review_entry, dict):
                    review_tuple += (dict(review_entry),)
        else:
            issues.append(Issue(f"{path}.review_issues", "not_list", "review_issues 必须是数组"))
        recommendation = data.get("recommendation")
        if recommendation is not None:
            if not isinstance(recommendation, dict):
                issues.append(Issue(f"{path}.recommendation", "not_object", "recommendation 必须是对象或 null"))
                recommendation = None
            else:
                category = recommendation.get("category")
                priority = recommendation.get("priority")
                reason = recommendation.get("reason", "")
                if category not in RECOMMENDATION_CATEGORIES:
                    issues.append(Issue(f"{path}.recommendation.category", "bad_enum", "重点类型无效"))
                if not _is_int(priority) or not 1 <= priority <= 3:
                    issues.append(Issue(f"{path}.recommendation.priority", "bad_range", "priority 必须为 1 至 3"))
                if not isinstance(reason, str) or len(reason) > 200:
                    issues.append(Issue(f"{path}.recommendation.reason", "bad_string", "reason 最多 200 个字符"))
                recommendation = {
                    "category": category,
                    "priority": priority,
                    "reason": reason,
                }
        return AnnotationItem(
            annotation_id=annotation_id or "",
            target=target,  # type: ignore[arg-type]
            anchor=anchor,
            style=style,  # type: ignore[arg-type]
            timing=timing,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            protection=protection,  # type: ignore[arg-type]
            inputs=inputs,  # type: ignore[arg-type]
            accepted_degradation=accepted,
            review_issues=review_tuple,
            confirmed_inputs=confirmed_inputs,
            recommendation=recommendation,
        )


def next_annotation_id(existing_ids: Sequence[str]) -> str:
    """分配下一个 annotation_id:ann_001 起步,单调递增不复用。"""
    used = 0
    for value in existing_ids:
        match = re.match(r"^ann_(\d+)$", value)
        if match:
            used = max(used, int(match.group(1)))
    return f"ann_{used + 1:03d}"


@dataclass(frozen=True)
class AnnotationPage:
    """页级包装:revision + 条目 + AI 原始建议快照。"""

    slide_id: str
    revision: int
    items: Tuple[AnnotationItem, ...]
    ai_suggestion_snapshot: Optional[Dict[str, Any]] = None
    updated_at: str = ""

    @staticmethod
    def from_payload(
        data: Any, issues: List[Issue], *, canvas: Tuple[int, int]
    ) -> Optional["AnnotationPage"]:
        if not isinstance(data, dict):
            issues.append(Issue("page", "not_object", "页面数据必须是对象"))
            return None
        schema = data.get("schema_version")
        if schema != ANNOTATION_SCHEMA_VERSION:
            issues.append(Issue("schema_version", "bad_version", f"schema_version 必须是 {ANNOTATION_SCHEMA_VERSION}"))
        slide_id = _check_str(issues, "slide_id", data.get("slide_id"), maximum=64)
        revision = _check_int(issues, "revision", data.get("revision"), minimum=1, maximum=10**9)
        raw_items = data.get("items", [])
        if not isinstance(raw_items, list):
            issues.append(Issue("items", "not_list", "items 必须是数组"))
            raw_items = []
        if len(raw_items) > LIMITS["max_items_per_slide"]:
            issues.append(Issue("items", "too_many", f"每页条目超过 {LIMITS['max_items_per_slide']}"))
        items: List[AnnotationItem] = []
        seen_ids = set()
        for index, raw in enumerate(raw_items):
            item = AnnotationItem.from_payload(raw, issues, canvas=canvas, path=f"items[{index}]")
            if item is None:
                continue
            if item.annotation_id in seen_ids:
                issues.append(Issue(f"items[{index}].annotation_id", "duplicate", "annotation_id 重复"))
                continue
            seen_ids.add(item.annotation_id)
            items.append(item)
        snapshot = data.get("ai_suggestion_snapshot")
        if snapshot is not None and not isinstance(snapshot, dict):
            issues.append(Issue("ai_suggestion_snapshot", "not_object", "ai_suggestion_snapshot 必须是对象或 null"))
            snapshot = None
        if slide_id is None or revision is None:
            return None
        return AnnotationPage(
            slide_id=slide_id,
            revision=revision,
            items=tuple(items),
            ai_suggestion_snapshot=snapshot,
            updated_at=str(data.get("updated_at") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": ANNOTATION_SCHEMA_VERSION,
            "slide_id": self.slide_id,
            "revision": self.revision,
            "items": [item.to_dict() for item in self.items],
            "ai_suggestion_snapshot": self.ai_suggestion_snapshot,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class AnnotationSettings:
    """项目级勾画设置;enabled 决定是否带入视频。

    decision 记录用户对模块六的显式决策:'none'(未决策)/
    'no_annotations'(明确本项目不添加勾画)。完成状态由决策驱动,
    与 enabled 解耦(第二轮优化方案 3.2)。
    """

    revision: int
    enabled: bool
    defaults: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""
    decision: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": ANNOTATION_SCHEMA_VERSION,
            "revision": self.revision,
            "enabled": self.enabled,
            "defaults": dict(self.defaults),
            "updated_at": self.updated_at,
            "decision": self.decision,
        }


def default_annotation_settings() -> AnnotationSettings:
    return AnnotationSettings(
        revision=1,
        enabled=False,
        defaults={
            "color": "#F46A38",
            "opacity": 0.85,
            "width": 5,
            "padding": 8,
            "draw_duration_sec": 0.6,
            "exit_duration_sec": 0.15,
            "emphasis": "moderate",
        },
        updated_at="",
    )


def page_item_counts(page: Optional[AnnotationPage]) -> Dict[str, int]:
    """页内条目按内容状态计数;无页面视为未使用。"""
    counts = {"total": 0, "draft": 0, "confirmed": 0, "disabled": 0}
    if page is None:
        return counts
    for item in page.items:
        counts["total"] += 1
        counts[item.status.content] = counts.get(item.status.content, 0) + 1
    return counts
