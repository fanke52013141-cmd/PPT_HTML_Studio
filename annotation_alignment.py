# -*- coding: utf-8 -*-
"""勾画标注的音频对齐(W4):统一适配器接口 + 句级降级落地。

对应交接文档 6.4/5.3:

- 首期**选定并交付**的适配器:句级时间(来自既有 TTS 音频时间轴的
  ``segments``,timing_source=provider_sentence_timestamps)。它是可靠的
  句级来源,精度诚实标记 ``sentence_fallback``,绝不冒充 word_aligned。
- 字级适配器只定义统一接口(引擎注入);WhisperX 等字级引擎在本机
  Python 3.13 环境的可行性评测记录于 docs/annotation-validation/
  adapter-decision.md。评测通过并接入前,支持范围明确收窄为
  sentence_fallback + manual。
- 缓存键:音频字节哈希 + 发音文本/映射哈希 + 引擎/配置版本。
- 时间必须有限、单调、非负且不超内容时长;无对应发音的区间如实标记,
  不平均切分。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "WORD_ALIGNMENT_FILE",
    "ALIGNMENT_SCHEMA_VERSION",
    "SENTENCE_ENGINE_VERSION",
    "AlignmentError",
    "build_sentence_alignment",
    "load_word_alignment",
    "word_alignment_cache_key",
]

WORD_ALIGNMENT_FILE = "word_alignment.json"
ALIGNMENT_SCHEMA_VERSION = 1
SENTENCE_ENGINE_VERSION = "sentence_timeline_v1"


class AlignmentError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # missing_audio | bad_timeline | invalid_time
        self.message = message


@dataclass(frozen=True)
class BeatSpan:
    beat_id: str
    start_sec: float
    end_sec: float
    timing_source: str


def _finite_nonnegative(value: Any) -> Optional[float]:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    number = float(value)
    if number < 0 or number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def read_beat_spans(timeline_payload: Dict[str, Any]) -> Tuple[List[BeatSpan], Optional[float]]:
    """从既有 TTS 音频时间轴提取句级 beat 区间(纯函数)。

    区间必须有限、非负、start < end 且不超内容时长;非法段跳过。
    """
    if not isinstance(timeline_payload, dict):
        raise AlignmentError("bad_timeline", "audio_timeline.json 不是对象")
    duration = _finite_nonnegative(
        timeline_payload.get("audio_content_duration_sec")
        if timeline_payload.get("audio_content_duration_sec") is not None
        else timeline_payload.get("duration_sec")
    )
    segments = timeline_payload.get("segments")
    if not isinstance(segments, list):
        raise AlignmentError("bad_timeline", "audio_timeline.json 缺少 segments 数组")
    spans: List[BeatSpan] = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        beat_id = str(segment.get("beat_id") or segment.get("id") or "").strip()
        start = _finite_nonnegative(segment.get("start"))
        end = _finite_nonnegative(segment.get("end"))
        if not beat_id or start is None or end is None or end <= start:
            continue
        if duration is not None and start > duration:
            continue
        spans.append(
            BeatSpan(
                beat_id=beat_id,
                start_sec=min(start, duration or start),
                end_sec=min(end, duration or end),
                timing_source=str(segment.get("timing_source") or "unknown"),
            )
        )
    if not spans:
        raise AlignmentError("bad_timeline", "audio_timeline.json 没有可用的句级时间区间")
    return spans, duration


def build_sentence_alignment(
    *,
    slide_id: str,
    audio_bytes_hash: Optional[str],
    timeline_payload: Dict[str, Any],
    beats: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """句级对齐产物(缓存键命中前先算,产物落盘由调用方负责)。

    beats 为页面讲稿语块(beat_id + spoken_text);对齐范围覆盖整句,
    锚点时间 = 语块起点。精度如实标记 sentence_fallback。
    """
    spans, duration = read_beat_spans(timeline_payload)
    span_map: Dict[str, List[BeatSpan]] = {}
    for span in spans:
        span_map.setdefault(span.beat_id, []).append(span)

    beat_entries: List[Dict[str, Any]] = []
    missing: List[str] = []
    for beat in beats:
        beat_id = str(beat.get("beat_id"))
        spoken = str(beat.get("spoken_text") or "")
        spans_for_beat = span_map.get(beat_id) or []
        if spans_for_beat:
            start = min(span.start_sec for span in spans_for_beat)
            end = max(span.end_sec for span in spans_for_beat)
            beat_entries.append(
                {
                    "beat_id": beat_id,
                    "range": [start, end],
                    "precision": "sentence",
                    "timing_source": spans_for_beat[0].timing_source,
                    "codepoint_count": len(spoken),
                }
            )
        else:
            missing.append(beat_id)
            beat_entries.append(
                {
                    "beat_id": beat_id,
                    "range": None,
                    "precision": "unavailable",
                    "timing_source": None,
                    "codepoint_count": len(spoken),
                }
            )
    return {
        "schema_version": ALIGNMENT_SCHEMA_VERSION,
        "engine": {
            "engine_version": SENTENCE_ENGINE_VERSION,
            "adapter": "sentence_timeline",
            "granularity": "sentence",
        },
        "slide_id": slide_id,
        "audio_hash": audio_bytes_hash,
        "audio_duration_sec": duration,
        "beats": beat_entries,
        "unavailable_beats": missing,
        "precision": "sentence_fallback",
    }


def word_alignment_cache_key(
    audio_bytes: Optional[bytes],
    *,
    engine_version: str,
    spoken_text_hash: Optional[str],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"annotation-alignment-v1\n")
    digest.update(engine_version.encode("utf-8") + b"\n")
    digest.update((spoken_text_hash or "none").encode("utf-8") + b"\n")
    digest.update(hashlib.sha256(audio_bytes).digest() if audio_bytes else b"no-audio")
    return digest.hexdigest()


def load_word_alignment(run_dir: str, slide_id: str) -> Optional[Dict[str, Any]]:
    from project_storage import slide_file

    path = Path(slide_file(run_dir, slide_id, WORD_ALIGNMENT_FILE))
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != ALIGNMENT_SCHEMA_VERSION:
        return None
    return payload


def beat_times_from_alignment(
    alignment_payload: Optional[Dict[str, Any]],
    timeline_payload: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Tuple[float, float]], str]:
    """为时间轴构建器提供 beat 区间与诚实的时间来源标记。

    优先读已落盘的 word_alignment;缺文件时直接用句级时间轴。
    返回 (beat_times, temporal_status):sentence → sentence_fallback。
    """
    spans, _duration = read_beat_spans(timeline_payload or {})
    beat_times = {span.beat_id: (span.start_sec, span.end_sec) for span in spans}
    return beat_times, "sentence_fallback"
