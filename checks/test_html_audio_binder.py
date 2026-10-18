"""D02: audio-timeline binding for HTML scenes (seconds→ms once, at the
boundary; motion rebased; rejects malformed timelines)."""
from __future__ import annotations

import pytest

from html_audio_binder import (
    AudioBindingError,
    bind_scene_to_audio,
    binding_report,
    editor_timing,
)

SCENE = {
    "format": "hps.visual.scene",
    "version": "0.2.0",
    "id": "slide-1",
    "durationMs": 10000,
    "nodes": [{"id": "n1", "slot": "s", "type": "text", "role": "title",
               "runs": [{"text": "标题", "emphasis": False}]}],
    "motion": [
        {"targetId": "n1", "type": "enter", "startMs": 1000,
         "durationMs": 800, "offsetX": 0, "offsetY": 12},
    ],
    "beats": [],
    "source": "测试",
}

TIMELINE = {
    "audio_content_duration_sec": 20.0,
    "segments": [
        {"id": "b1", "start": 0.0, "end": 8.4, "text": "第一句讲解。"},
        {"id": "b2", "start": 8.4, "end": 19.6, "text": "第二句讲解。"},
    ],
}


def test_editor_projection_preserves_author_data_and_explains_clipped_durations():
    import copy
    import hashlib
    scene = copy.deepcopy(SCENE)
    scene.update(version="0.6.0", initialVisibleIds=[])
    scene["motion"] = [
        {"actionId": "a1", "targetId": "n1", "type": "enter", "startMs": 1000, "durationMs": 9000},
        {"actionId": "a2", "targetId": "n1", "type": "emphasize", "startMs": 7000, "durationMs": 4000},
    ]
    binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_ids",
               "sourceBeats": [{"id": s["id"], "spoken_text": s["text"],
                                "spoken_text_sha256": hashlib.sha256(s["text"].encode()).hexdigest()}
                               for s in TIMELINE["segments"]],
               "actions": {"a1": {"beatId": "b1", "edge": "start", "offsetMs": 1000},
                           "a2": {"beatId": "b1", "edge": "start", "offsetMs": 7000}}}
    before = copy.deepcopy((scene, binding))
    bound = bind_scene_to_audio(scene, TIMELINE, binding)
    projection = editor_timing(scene, bound, TIMELINE, binding)
    assert projection["beats"][0] == {"beatId": "b1", "startMs": 0, "endMs": 8400, "text": "第一句讲解。"}
    first, second = projection["actions"]
    assert (first["authorDurationMs"], first["effectiveDurationMs"], first["clippedBy"]) == (9000, 6000, ["next_action"])
    assert (second["authorDurationMs"], second["effectiveDurationMs"], second["clippedBy"]) == (4000, 1400, ["beat_end"])
    assert (scene, binding) == before
    with_tail = dict(TIMELINE, duration_sec=21)
    assert editor_timing(scene, bound, with_tail, binding)["mediaDurationMs"] == 21000
    assert editor_timing(scene, bound, with_tail, binding)["durationMs"] == 20000


def test_seconds_convert_to_ms_exactly_once_and_motion_scales() -> None:
    bound = bind_scene_to_audio(SCENE, TIMELINE)
    assert bound["durationMs"] == 20000
    assert bound["beats"][0] == {"startMs": 0, "endMs": 8400, "text": "第一句讲解。"}
    assert bound["beats"][1]["endMs"] == 19600
    # 1s/10s at scale 2.0 → 2000ms；时长同比例。
    assert bound["motion"][0]["startMs"] == 2000
    assert bound["motion"][0]["durationMs"] == 1600
    # 输入场景不被修改。
    assert SCENE["durationMs"] == 10000 and SCENE["beats"] == []


def test_motion_never_outlives_the_narration() -> None:
    late = dict(SCENE, motion=[
        {"targetId": "n1", "type": "enter", "startMs": 9500,
         "durationMs": 2000, "offsetX": 0, "offsetY": 12},
    ])
    bound = bind_scene_to_audio(late, TIMELINE)
    action = bound["motion"][0]
    assert action["startMs"] + action["durationMs"] <= bound["durationMs"]


def test_malformed_timelines_are_rejected_with_codes() -> None:
    with pytest.raises(AudioBindingError) as missing:
        bind_scene_to_audio(SCENE, {"segments": []})
    assert missing.value.code == "AUDIO_TIMESTAMP_MISSING"
    overlapping = {"audio_content_duration_sec": 10, "segments": [
        {"id": "a", "start": 0.0, "end": 6.0, "text": "一"},
        {"id": "b", "start": 5.0, "end": 9.0, "text": "二"},
    ]}
    with pytest.raises(AudioBindingError) as overlap:
        bind_scene_to_audio(SCENE, overlapping)
    assert overlap.value.code == "AUDIO_TIMESTAMP_OVERLAP"
    empty_text = {"audio_content_duration_sec": 4, "segments": [
        {"id": "a", "start": 0.0, "end": 3.0, "text": "  "},
    ]}
    with pytest.raises(AudioBindingError) as text_missing:
        bind_scene_to_audio(SCENE, empty_text)
    assert text_missing.value.code == "AUDIO_BEAT_TEXT_MISSING"
    with pytest.raises(AudioBindingError) as no_duration:
        bind_scene_to_audio(SCENE, {"segments": TIMELINE["segments"]})
    assert no_duration.value.code == "AUDIO_DURATION_MISSING"


def test_binding_report_and_metadata_stay_out_of_scene() -> None:
    first = bind_scene_to_audio(SCENE, TIMELINE)
    # 场景文档保持严格 Schema：溯源信息不得进入作者输入。
    assert "audioBinding" not in first
    report = binding_report([first])
    assert report == {
        "boundScenes": 1,
        "totalDurationMs": 20000,
        "audioSource": "existing_audio",
    }
    from html_audio_binder import binding_metadata

    assert binding_metadata(SCENE, TIMELINE) == {
        "source": "existing_audio",
        "audioDurationMs": 20000,
        "beatCount": 2,
        "timeScale": 2.0,
    }
