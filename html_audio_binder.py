"""Bind existing confirmed audio timelines to HTML scene documents (D02).

Pure mapping layer between the already-confirmed narration pipeline
(``audio_timeline.json`` segments in seconds, shared with the image
route) and the html visual scene (milliseconds, per-slide). The
second→millisecond conversion happens exactly once, at this boundary;
scene motion times are rebased proportionally so the scene ends with
the narration. No TTS reselection, no re-synthesis: unchanged audio
stays reusable.
"""

from __future__ import annotations

import copy
import math
import re
from typing import Any, Iterable


class AudioBindingError(Exception):
    """Rejected binding with a diagnostic code for callers to surface."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _segments(audio_timeline: dict[str, Any]) -> list[dict[str, Any]]:
    segments = audio_timeline.get("segments")
    if not isinstance(segments, list) or not segments:
        raise AudioBindingError(
            "AUDIO_TIMESTAMP_MISSING",
            "audio_timeline.json 缺少 segments[]，不能绑定动作时间",
        )
    previous_end = 0.0
    for segment in segments:
        if not isinstance(segment, dict):
            raise AudioBindingError("AUDIO_TIMESTAMP_INVALID", "音频时间轴段格式不合法")
        start, end = segment.get("start"), segment.get("end")
        text = segment.get("text")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise AudioBindingError(
                "AUDIO_TIMESTAMP_INVALID", "音频时间轴 start/end 必须是数字"
            )
        if not isinstance(text, str) or not text.strip():
            raise AudioBindingError(
                "AUDIO_BEAT_TEXT_MISSING", "音频时间轴段缺少旁白文本"
            )
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
        ):
            raise AudioBindingError(
                "AUDIO_TIMESTAMP_INVALID",
                f"音频时间轴段区间不合法：{segment.get('id')}",
            )
        if start < previous_end:
            raise AudioBindingError(
                "AUDIO_TIMESTAMP_OVERLAP",
                f"音频时间轴段重叠或乱序：{segment.get('id')}",
            )
        previous_end = end
    return segments


def _audio_duration_sec(audio_timeline: dict[str, Any]) -> float:
    duration = audio_timeline.get("audio_content_duration_sec")
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(duration)
        or duration <= 0
    ):
        duration = audio_timeline.get("duration_sec")
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(duration)
        or duration <= 0
    ):
        raise AudioBindingError(
            "AUDIO_DURATION_MISSING", "audio_timeline 缺少可用的音频时长"
        )
    return float(duration)


def _binding_actions(
    scene: dict[str, Any],
    binding: dict[str, Any] | None,
    beat_ids: set[str],
) -> dict[str, dict[str, Any]]:
    """Validate explicit motion bindings before using any of them.

    The editor validates persisted documents too, but this module is also used
    directly by readiness and render paths. A malformed explicit binding must
    never silently fall back to the scene's authored absolute time.
    """
    if scene.get("version") in ("0.6.0", "0.7.0"):
        from html_motion_binding import validate_binding
        try:
            return validate_binding(scene, binding, beat_ids)
        except ValueError as exc:
            raise AudioBindingError("AUDIO_BINDING_INVALID", str(exc)) from exc
    motions = scene.get("motion")
    if not isinstance(motions, list):
        raise AudioBindingError("SCENE_MOTION_INVALID", "场景动作列表格式不合法")

    valid_actions: set[str] = set()
    for action in motions:
        if (
            not isinstance(action, dict)
            or not isinstance(action.get("targetId"), str)
            or not action["targetId"]
            or not isinstance(action.get("type"), str)
            or not action["type"]
        ):
            raise AudioBindingError("SCENE_MOTION_INVALID", "动作目标或类型缺失")
        key = f"{action['targetId']}:{action['type']}"
        if key in valid_actions:
            raise AudioBindingError(
                "SCENE_MOTION_INVALID", f"动作身份重复：{key}"
            )
        valid_actions.add(key)

    if binding is None:
        return {}
    if (
        not isinstance(binding, dict)
        or set(binding) != {"format", "version", "mode", "actions"}
        or binding.get("format") != "hps.html.motion_binding"
        or binding.get("version") != "0.1.0"
        or binding.get("mode") != "beat_ids"
        or not isinstance(binding.get("actions"), dict)
    ):
        raise AudioBindingError("AUDIO_BINDING_INVALID", "动作语块绑定格式不合法")

    actions = binding["actions"]
    stale = sorted(set(actions) - valid_actions)
    if stale:
        raise AudioBindingError(
            "AUDIO_BINDING_TARGET_GONE", f"绑定目标已不存在：{', '.join(stale)}"
        )
    for key, link in actions.items():
        if (
            not isinstance(link, dict)
            or set(link) != {"beatId", "edge", "offsetMs"}
            or not isinstance(link.get("beatId"), str)
            or not link["beatId"]
        ):
            raise AudioBindingError(
                "AUDIO_BINDING_INVALID", f"绑定字段错误：{key}"
            )
        if link["beatId"] not in beat_ids:
            raise AudioBindingError(
                "AUDIO_BEAT_MISSING", f"缺少语块 {link['beatId']}"
            )
        if (
            link.get("edge") not in ("start", "end")
            or type(link.get("offsetMs")) is not int
            or abs(link["offsetMs"]) > 120000
        ):
            raise AudioBindingError(
                "AUDIO_BINDING_INVALID", f"边界或偏移错误：{key}"
            )
    return actions


def bind_scene_to_audio(
    scene: dict[str, Any],
    audio_timeline: dict[str, Any],
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a new scene whose duration/beats/motion follow the audio.

    - seconds→milliseconds happens once per value, right here
    - subtitle beats are the confirmed narration segments (empty gaps stay
      empty; the last ending beat defines the work duration tail)
    - motion keeps its relative position: ``startMs`` scales to the audio
      duration; durations clamp so nothing outlives the narration
    """
    segments = _segments(audio_timeline)
    duration_ms = int(round(_audio_duration_sec(audio_timeline) * 1000))
    scene_duration_ms = scene.get("durationMs")
    if not isinstance(scene_duration_ms, (int, float)) or scene_duration_ms <= 0:
        raise AudioBindingError("SCENE_DURATION_INVALID", "场景时长不合法")

    scale = duration_ms / float(scene_duration_ms)
    windows = {}
    for segment in segments:
        beat_id = segment.get("beat_id") or segment.get("id")
        if not beat_id:
            raise AudioBindingError("AUDIO_BEAT_ID_MISSING", "音频段缺少稳定语块 ID")
        start, end = round(segment["start"] * 1000), round(segment["end"] * 1000)
        if start >= duration_ms or end > duration_ms:
            raise AudioBindingError("AUDIO_BEAT_OVERFLOW", "语块超过音频内容时长")
        if beat_id in windows and not segment.get("beat_id"):
            raise AudioBindingError("AUDIO_BEAT_DUPLICATE", "音频语块 ID 重复")
        previous = windows.get(beat_id, (start, end))
        windows[beat_id] = (min(start, previous[0]), max(end, previous[1]))
    bound = copy.deepcopy(scene)
    bound["durationMs"] = duration_ms
    bound["beats"] = [
        {
            "startMs": int(round(float(segment["start"]) * 1000)),
            "endMs": min(int(round(float(segment["end"]) * 1000)), duration_ms),
            "text": segment["text"],
        }
        for segment in segments
    ]
    semantic = scene.get("version") in ("0.6.0", "0.7.0")
    motions = bound.get("motion")
    if not isinstance(motions, list) or (not motions and not semantic):
        raise AudioBindingError(
            "SCENE_MOTION_MISSING", "场景缺少动作定义，不能绑定讲解时间"
        )
    binding_actions = _binding_actions(scene, binding, set(windows))
    if semantic:
        _validate_semantic_audio(binding, segments)
    for action in motions:
        start_ms = action.get("startMs")
        duration = action.get("durationMs")
        if not isinstance(start_ms, (int, float)) or not isinstance(
            duration, (int, float)
        ):
            raise AudioBindingError(
                "SCENE_MOTION_INVALID", f"动作时间不合法：{action.get('targetId')}"
            )
        from html_motion_binding import motion_identity
        link = binding_actions.get(motion_identity(action))
        if link is not None:
            edge = 1 if link.get("edge") == "end" else 0
            new_start = windows[link["beatId"]][edge] + link["offsetMs"]
            new_duration = int(duration)
            if new_start < 0 or new_start >= duration_ms:
                raise AudioBindingError("AUDIO_OFFSET_OVERFLOW", "手工偏移越过作品边界")
            if semantic:
                start, end = windows[link["beatId"]]
                if not start <= new_start < end:
                    raise AudioBindingError("AUDIO_ACTION_WINDOW", "动作偏移越过绑定语块")
                new_duration = min(new_duration, end - new_start)
        elif binding is not None:
            # Unbound decorative actions keep their declared absolute timing.
            new_start, new_duration = int(start_ms), int(duration)
        else:
            # Explicit compatibility for old unbound experiments only.
            new_start = int(round(float(start_ms) * scale))
            new_duration = int(round(float(duration) * scale))
        # 末帧保持：任何动作都不得越过音频时长。
        new_start = min(new_start, max(duration_ms - 1, 0))
        if new_start + new_duration > duration_ms:
            new_duration = max(duration_ms - new_start, 1)
        action["startMs"] = new_start
        action["durationMs"] = max(new_duration, 1)
    if semantic:
        _check_semantic_action_windows(bound)
    # Provenance stays OUT of the scene document: the author schema is
    # strict, and binding metadata belongs to the derived-artifact manifest
    # (see binding_report / html_render_runner).
    return bound


def _validate_semantic_audio(binding, segments):
    """Subtitle parts may remove punctuation; all spoken characters must match."""
    order, text_by_beat = [], {}
    for segment in segments:
        identity = segment.get("beat_id") or segment.get("id")
        if not order or order[-1] != identity:
            if identity in order:
                raise AudioBindingError("AUDIO_BEAT_ORDER", "语块分段不是连续顺序")
            order.append(identity)
        text_by_beat[identity] = text_by_beat.get(identity, "") + segment["text"]
    source = binding["sourceBeats"]
    if order != [b["id"] for b in source]:
        raise AudioBindingError("AUDIO_BEAT_ORDER", "音频语块与权威原句顺序不一致")
    for b in source:
        signature = lambda text: re.sub(r"[^\w]", "", text, flags=re.UNICODE)
        if signature(text_by_beat[b["id"]]) != signature(b["spoken_text"]):
            raise AudioBindingError("AUDIO_TEXT_MISMATCH", f"音频原句不一致：{b['id']}")


def _check_semantic_action_windows(scene):
    by_target = {}
    for action in scene["motion"]:
        by_target.setdefault(action["targetId"], []).append(action)
    for actions in by_target.values():
        ordered = sorted(actions, key=lambda a: a["startMs"])
        for a, b in zip(ordered, ordered[1:]):
            if a["startMs"] == b["startMs"]:
                raise AudioBindingError("AUDIO_ACTION_OVERLAP", "同一对象动作不能同时开始")
            a["durationMs"] = min(a["durationMs"], b["startMs"] - a["startMs"])
        initial = ordered[0]["targetId"] in scene["initialVisibleIds"]
        if not initial and ordered[0]["type"] != "enter":
            raise AudioBindingError("AUDIO_ACTION_ORDER", "对象必须先入场再强调")


def binding_metadata(
    scene: dict[str, Any], audio_timeline: dict[str, Any]
) -> dict[str, Any]:
    """Provenance record for the render/export manifest (not scene input)."""
    segments = audio_timeline.get("segments") or []
    duration = audio_timeline.get("audio_content_duration_sec") or audio_timeline.get(
        "duration_sec"
    )
    scene_duration = scene.get("durationMs") or 0
    scale = (
        (float(duration) * 1000 / scene_duration)
        if duration and scene_duration
        else None
    )
    return {
        "source": "existing_audio",
        "audioDurationMs": int(round(float(duration) * 1000)) if duration else None,
        "beatCount": len(segments) if isinstance(segments, list) else 0,
        "timeScale": round(scale, 6) if scale else None,
    }


def binding_report(scenes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(scenes)
    return {
        "boundScenes": len(items),
        "totalDurationMs": sum(int(s.get("durationMs", 0)) for s in items),
        "audioSource": "existing_audio",
    }


def editor_timing(scene, bound, audio_timeline, binding):
    """Read-only editor projection, called after the same binder validated input."""
    from html_motion_binding import motion_identity

    windows = {}
    for segment in _segments(audio_timeline):
        identity = segment.get("beat_id") or segment.get("id")
        start, end = round(segment["start"] * 1000), round(segment["end"] * 1000)
        item = windows.setdefault(identity, {"beatId": identity, "startMs": start, "endMs": end, "text": ""})
        item["endMs"] = max(item["endMs"], end)
        item["text"] += segment["text"]
    effective = {motion_identity(a): a for a in bound["motion"]}
    actions = []
    for action in scene["motion"]:
        identity = motion_identity(action)
        resolved = effective[identity]
        link = (binding or {}).get("actions", {}).get(identity)
        window = windows.get(link["beatId"]) if link else None
        reasons = []
        if resolved["durationMs"] < action["durationMs"]:
            end = resolved["startMs"] + resolved["durationMs"]
            if window and end == window["endMs"]:
                reasons.append("beat_end")
            if end == bound["durationMs"]:
                reasons.append("audio_end")
            if any(a["targetId"] == action["targetId"] and a["startMs"] == end for a in bound["motion"]):
                reasons.append("next_action")
        actions.append({"id": identity, "targetId": action["targetId"], "type": action["type"],
                        "authorDurationMs": action["durationMs"], "effectiveStartMs": resolved["startMs"],
                        "effectiveDurationMs": resolved["durationMs"], "beatId": link["beatId"] if link else None,
                        "offsetMs": link["offsetMs"] if link else None, "clippedBy": reasons,
                        "editable": bool(window and resolved["durationMs"] >= 100)})
    media_seconds = audio_timeline.get("duration_sec")
    media_duration = round(media_seconds * 1000) if type(media_seconds) in (int, float) and math.isfinite(media_seconds) and media_seconds > 0 else bound["durationMs"]
    return {"durationMs": bound["durationMs"], "mediaDurationMs": media_duration,
            "beats": list(windows.values()), "actions": actions}
