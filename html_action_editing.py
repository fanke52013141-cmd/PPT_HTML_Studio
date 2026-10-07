"""Object & action editing contract for HTML scenes (D01 pure core).

Registered action vocabulary over a normalized scene plan: enter
(显隐+位移), exit (退出：临时对象生命周期终点), emphasize (强调提升),
relation_draw (关系描绘：引线随讲解描绘). Compilation reuses the
engine's pure time interpolation semantics (smoothstep over
[startMs, startMs+durationMs], deterministic from t alone).

Manual edits are recorded separately with priority: a replanned plan
keeps manual overrides unless they conflict, and conflicts are returned
explicitly — never silently overwritten (AC11).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

REGISTERED_ACTIONS: Dict[str, Dict[str, Any]] = {
    "enter": {
        "label": "显隐入场",
        "params": {"startMs": True, "durationMs": True, "offsetX": False, "offsetY": False},
        "channels": ("enter",),
    },
    "exit": {
        "label": "退出消失",
        "params": {"startMs": True, "durationMs": True},
        "channels": ("exit",),
        "requires": "exit_object",
    },
    "emphasize": {
        "label": "强调提升",
        "params": {"startMs": True, "durationMs": True},
        "channels": ("emphasize",),
    },
    "relation_draw": {
        "label": "关系描绘",
        "params": {"startMs": True, "durationMs": True},
        "channels": ("relation",),
        "requires": "annotation_target",
    },
}


class ActionEditError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _num(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ActionEditError("ACTION_TIME_INVALID", f"{label} 必须是整数毫秒")
    return value


def normalize_object_actions(
    object_id: str,
    actions: List[Dict[str, Any]],
    *,
    scene_duration_ms: int,
    is_exit_object: bool = False,
    is_annotation_target: bool = False,
) -> List[Dict[str, Any]]:
    """Validate one object's action list; each registered channel may appear
    at most once and windows must not overlap (channel-conflict rule)."""
    if not actions:
        raise ActionEditError(
            "ACTION_ENTER_MISSING", f"对象 {object_id} 缺少 enter 入场动作"
        )
    used_channels: Dict[str, Dict[str, Any]] = {}
    normalized: List[Dict[str, Any]] = []
    for index, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            raise ActionEditError("ACTION_INVALID", f"动作 #{index} 不是对象")
        action_type = str(action.get("type") or "").strip()
        spec = REGISTERED_ACTIONS.get(action_type)
        if spec is None:
            raise ActionEditError(
                "ACTION_UNREGISTERED",
                f"动作 {action_type or '(空)'} 未注册；可用：{', '.join(REGISTERED_ACTIONS)}",
            )
        channel = spec["channels"][0]
        if channel in used_channels:
            raise ActionEditError(
                "ACTION_CHANNEL_CONFLICT",
                f"对象 {object_id} 的 {channel} 通道重复定义",
            )
        start = _num(action.get("startMs"), f"{object_id}.{action_type}.startMs")
        duration = _num(action.get("durationMs"), f"{object_id}.{action_type}.durationMs")
        if start < 0 or duration < 1:
            raise ActionEditError("ACTION_TIME_INVALID", f"{object_id}.{action_type} 时间区间不合法")
        if start + duration > scene_duration_ms:
            raise ActionEditError(
                "ACTION_TIME_OVERFLOW", f"{object_id}.{action_type} 越过作品时长"
            )
        if action_type == "exit" and not is_exit_object:
            raise ActionEditError(
                "ACTION_EXIT_NOT_TRANSITIONAL",
                f"对象 {object_id} 不是过渡对象，不能定义 exit",
            )
        if (
            action_type == "relation_draw"
            and not is_annotation_target
        ):
            raise ActionEditError(
                "ACTION_RELATION_NOT_ANNOTATION",
                f"对象 {object_id} 不是批注/关系对象，不能定义 relation_draw",
            )
        entry: Dict[str, Any] = {
            "type": action_type,
            "startMs": start,
            "durationMs": duration,
        }
        if action_type == "enter":
            entry["offsetX"] = int(action.get("offsetX") or 0)
            entry["offsetY"] = int(action.get("offsetY") or 12)
        used_channels[channel] = entry
        normalized.append(entry)
    if "enter" not in used_channels:
        raise ActionEditError(
            "ACTION_ENTER_MISSING", f"对象 {object_id} 缺少 enter 入场动作"
        )
    # 非重叠（同一对象内任意两动作窗口不得重叠；enter 之后才允许其他动作）。
    enter = used_channels["enter"]
    enter_end = enter["startMs"] + enter["durationMs"]
    for channel, window in used_channels.items():
        if channel == "enter":
            continue
        if window["startMs"] < enter_end:
            raise ActionEditError(
                "ACTION_WINDOW_OVERLAP",
                f"对象 {object_id} 的 {channel} 与 enter 时间窗重叠",
            )
    ordered = sorted(used_channels.values(), key=lambda w: w["startMs"])
    for earlier, later in zip(ordered, ordered[1:]):
        if later["startMs"] < earlier["startMs"] + earlier["durationMs"]:
            raise ActionEditError(
                "ACTION_WINDOW_OVERLAP",
                f"对象 {object_id} 动作时间窗相互重叠",
            )
    return ordered


def apply_action_edits(
    actions_by_object: Dict[str, List[Dict[str, Any]]],
    *,
    scene_duration_ms: int,
    manual_overrides: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    exit_objects: Optional[set] = None,
    annotation_targets: Optional[set] = None,
) -> Dict[str, Any]:
    """Compile per-object action lists; manual overrides win, and overrides
    that no longer apply to the replanned object set are returned as
    explicit conflicts instead of being dropped silently."""
    exit_objects = exit_objects or set()
    annotation_targets = annotation_targets or set()
    overrides = manual_overrides or {}
    compiled: Dict[str, List[Dict[str, Any]]] = {}
    conflicts: List[Dict[str, Any]] = []
    for object_id, actions in actions_by_object.items():
        source = overrides.get(object_id, actions)
        if object_id in overrides and object_id not in actions_by_object:
            conflicts.append({
                "object_id": object_id,
                "reason": "object_removed_by_replan",
                "override": overrides[object_id],
            })
            continue
        compiled[object_id] = normalize_object_actions(
            object_id,
            source,
            scene_duration_ms=scene_duration_ms,
            is_exit_object=object_id in exit_objects,
            is_annotation_target=object_id in annotation_targets,
        )
    for object_id, override in overrides.items():
        if object_id not in compiled and object_id not in actions_by_object:
            if not any(c["object_id"] == object_id for c in conflicts):
                conflicts.append({
                    "object_id": object_id,
                    "reason": "object_removed_by_replan",
                    "override": override,
                })
    return {"actions": compiled, "conflicts": conflicts}


def action_evidence(
    actions_by_object: Dict[str, List[Dict[str, Any]]],
    beat_map: Dict[str, Any],
) -> Dict[str, Any]:
    """AC11 evidence: per-object action windows plus the beat mapping."""
    return {
        "format": "hps.html.action_evidence",
        "version": "0.1.0",
        "objects": {
            object_id: sorted(
                actions, key=lambda a: (a["startMs"], a["type"])
            )
            for object_id, actions in actions_by_object.items()
        },
        "registered_actions": sorted(REGISTERED_ACTIONS),
        "beat_map": beat_map,
    }
