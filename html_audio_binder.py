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
            raise AudioBindingError(
                "AUDIO_TIMESTAMP_INVALID", "音频时间轴段格式不合法"
            )
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
        if start < 0 or end <= start:
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
    if not isinstance(duration, (int, float)) or duration <= 0:
        duration = audio_timeline.get("duration_sec")
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise AudioBindingError(
            "AUDIO_DURATION_MISSING", "audio_timeline 缺少可用的音频时长"
        )
    return float(duration)


def bind_scene_to_audio(
    scene: dict[str, Any],
    audio_timeline: dict[str, Any],
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
    motions = bound.get("motion")
    if not isinstance(motions, list) or not motions:
        raise AudioBindingError(
            "SCENE_MOTION_MISSING", "场景缺少动作定义，不能绑定讲解时间"
        )
    for action in motions:
        start_ms = action.get("startMs")
        duration = action.get("durationMs")
        if not isinstance(start_ms, (int, float)) or not isinstance(duration, (int, float)):
            raise AudioBindingError(
                "SCENE_MOTION_INVALID", f"动作时间不合法：{action.get('targetId')}"
            )
        new_start = int(round(float(start_ms) * scale))
        new_duration = int(round(float(duration) * scale))
        # 末帧保持：任何动作都不得越过音频时长。
        new_start = min(new_start, max(duration_ms - 1, 0))
        if new_start + new_duration > duration_ms:
            new_duration = max(duration_ms - new_start, 1)
        action["startMs"] = new_start
        action["durationMs"] = max(new_duration, 1)
    # Provenance stays OUT of the scene document: the author schema is
    # strict, and binding metadata belongs to the derived-artifact manifest
    # (see binding_report / html_render_runner).
    return bound


def binding_metadata(scene: dict[str, Any], audio_timeline: dict[str, Any]) -> dict[str, Any]:
    """Provenance record for the render/export manifest (not scene input)."""
    segments = audio_timeline.get("segments") or []
    duration = audio_timeline.get("audio_content_duration_sec") or audio_timeline.get("duration_sec")
    scene_duration = scene.get("durationMs") or 0
    scale = (float(duration) * 1000 / scene_duration) if duration and scene_duration else None
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
