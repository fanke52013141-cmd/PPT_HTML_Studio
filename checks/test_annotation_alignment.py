# -*- coding: utf-8 -*-
"""annotation_alignment 单测:句级区间提取、非法时间、缺失区间、缓存键。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_alignment import (  # noqa: E402
    AlignmentError,
    beat_times_from_alignment,
    build_sentence_alignment,
    read_beat_spans,
    word_alignment_cache_key,
)

TIMELINE = {
    "slide_id": "slide_001",
    "duration_sec": 8.638,
    "audio_content_duration_sec": 8.638,
    "timing_source": "provider_sentence_timestamps",
    "segments": [
        {"beat_id": "slide_001_beat_001", "start": 0.0, "end": 3.743, "text": "第一句", "timing_source": "provider_sentence_timestamps"},
        {"id": "slide_001_beat_002__part_01", "beat_id": "slide_001_beat_002", "start": 3.743, "end": 6.2, "text": "第二句", "timing_source": "provider_sentence_timestamps"},
    ],
}

BEATS = [
    {"beat_id": "slide_001_beat_001", "spoken_text": "很多人第一次听到"},
    {"beat_id": "slide_001_beat_002", "spoken_text": "因为它在不同领域意思完全不一样"},
    {"beat_id": "slide_001_beat_003", "spoken_text": "这一段没有对应音频"},
]


def test_read_beat_spans_maps_beats():
    spans, duration = read_beat_spans(TIMELINE)
    assert duration == 8.638
    assert [s.beat_id for s in spans] == ["slide_001_beat_001", "slide_001_beat_002"]
    assert spans[0].start_sec == 0.0 and spans[1].end_sec == 6.2
    assert spans[0].timing_source == "provider_sentence_timestamps"


def test_invalid_segments_skipped():
    broken = {
        "audio_content_duration_sec": 5.0,
        "segments": [
            {"beat_id": "b1", "start": 0.0, "end": 1.0},
            {"beat_id": "b2", "start": 2.0, "end": 1.0},   # end <= start 跳过
            {"beat_id": "b3", "start": -1.0, "end": 2.0},  # 负起点跳过
            {"beat_id": "b4", "start": 0.5, "end": 2.5},
            {"beat_id": "b5", "start": 9.0, "end": 10.0},  # 超内容时长跳过
            {"beat_id": "b6", "start": "x", "end": 2.0},   # 非数值跳过
        ],
    }
    spans, _ = read_beat_spans(broken)
    assert [s.beat_id for s in spans] == ["b1", "b4"]


def test_no_usable_segments_raises():
    with pytest.raises(AlignmentError) as excinfo:
        read_beat_spans({"segments": []})
    assert excinfo.value.code == "bad_timeline"


def test_sentence_alignment_precision_is_honest():
    payload = build_sentence_alignment(
        slide_id="slide_001",
        audio_bytes_hash="c" * 64,
        timeline_payload=TIMELINE,
        beats=BEATS,
    )
    assert payload["precision"] == "sentence_fallback"  # 绝不冒充 word_aligned
    assert payload["engine"]["granularity"] == "sentence"
    by_beat = {b["beat_id"]: b for b in payload["beats"]}
    assert by_beat["slide_001_beat_001"]["precision"] == "sentence"
    assert by_beat["slide_001_beat_001"]["range"] == [0.0, 3.743]
    assert by_beat["slide_001_beat_002"]["range"] == [3.743, 6.2]
    # 无对应发音的语块如实标记 unavailable
    assert by_beat["slide_001_beat_003"]["precision"] == "unavailable"
    assert payload["unavailable_beats"] == ["slide_001_beat_003"]


def test_cache_key_sensitive_to_audio_and_engine():
    base = word_alignment_cache_key(b"audio-bytes", engine_version="v1", spoken_text_hash="t" * 64)
    assert base == word_alignment_cache_key(b"audio-bytes", engine_version="v1", spoken_text_hash="t" * 64)
    assert base != word_alignment_cache_key(b"other-audio", engine_version="v1", spoken_text_hash="t" * 64)
    assert base != word_alignment_cache_key(b"audio-bytes", engine_version="v2", spoken_text_hash="t" * 64)
    assert base != word_alignment_cache_key(b"audio-bytes", engine_version="v1", spoken_text_hash="x" * 64)


def test_beat_times_for_timeline_builder():
    beat_times, temporal = beat_times_from_alignment(None, TIMELINE)
    assert temporal == "sentence_fallback"
    assert beat_times["slide_001_beat_001"] == (0.0, 3.743)
    assert beat_times["slide_001_beat_002"] == (3.743, 6.2)
