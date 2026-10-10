"""C-line regressions for deterministic motion and explicit audio bindings."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from html_action_editing import ActionEditError, normalize_object_actions
from html_audio_binder import AudioBindingError, bind_scene_to_audio
from html_scene_editing import merge_manual_edits


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "neutral-actions.json").read_text(
        encoding="utf-8"
    )
)
AUDIO = {
    "audio_content_duration_sec": 10.0,
    "segments": [
        {"id": "beat-intro", "start": 1.0, "end": 2.0, "text": "引入。"},
        {"id": "beat-focus", "start": 6.0, "end": 7.5, "text": "强调。"},
        {"id": "beat-wrap", "start": 8.0, "end": 9.0, "text": "收尾。"},
    ],
}


def binding(actions: dict) -> dict:
    return {
        "format": "hps.html.motion_binding",
        "version": "0.1.0",
        "mode": "beat_ids",
        "actions": actions,
    }


def test_manual_offsets_bind_the_named_action_and_preserve_unbound_time():
    source = copy.deepcopy(FIXTURE)
    original = copy.deepcopy(source)
    links = binding(
        {
            "headline:emphasize": {
                "beatId": "beat-focus",
                "edge": "start",
                "offsetMs": 125,
            },
            "headline:exit": {
                "beatId": "beat-wrap",
                "edge": "end",
                "offsetMs": -300,
            },
        }
    )

    result = bind_scene_to_audio(source, AUDIO, links)
    actions = {
        action["targetId"] + ":" + action["type"]: action
        for action in result["motion"]
    }
    assert result["durationMs"] == 10000
    assert actions["headline:emphasize"]["startMs"] == 6125
    assert actions["headline:exit"]["startMs"] == 8700
    # A supplied binding document keeps intentionally unbound decorative
    # actions on their authored times; only explicitly linked actions move.
    assert actions["title-rule:enter"]["startMs"] == 337
    assert actions["title-rule:enter"]["durationMs"] == 777
    assert source == original
    assert AUDIO["segments"][1]["start"] == 6.0


@pytest.mark.parametrize(
    ("link", "expected_code"),
    [
        ({}, "AUDIO_BINDING_INVALID"),
        (
            {"beatId": "beat-focus", "edge": "middle", "offsetMs": 0},
            "AUDIO_BINDING_INVALID",
        ),
        (
            {"beatId": "beat-focus", "edge": "start", "offsetMs": 12.5},
            "AUDIO_BINDING_INVALID",
        ),
        (
            {"beatId": "beat-focus", "edge": "start", "offsetMs": True},
            "AUDIO_BINDING_INVALID",
        ),
        (
            {"beatId": "removed-beat", "edge": "start", "offsetMs": 0},
            "AUDIO_BEAT_MISSING",
        ),
    ],
)
def test_malformed_explicit_links_fail_closed(link, expected_code):
    with pytest.raises(AudioBindingError) as exc:
        bind_scene_to_audio(
            FIXTURE, AUDIO, binding({"headline:emphasize": link})
        )
    assert exc.value.code == expected_code


def test_orphaned_binding_does_not_silently_fall_back_to_absolute_time():
    with pytest.raises(AudioBindingError) as exc:
        bind_scene_to_audio(
            FIXTURE,
            AUDIO,
            binding(
                {
                    "deleted-object:emphasize": {
                        "beatId": "beat-focus",
                        "edge": "start",
                        "offsetMs": 0,
                    }
                }
            ),
        )
    assert exc.value.code == "AUDIO_BINDING_TARGET_GONE"


def test_single_action_slot_and_exit_lifecycle_guard_remain_explicit():
    actions = [
        {"type": "enter", "startMs": 0, "durationMs": 500},
        {"type": "emphasize", "startMs": 700, "durationMs": 500},
        {"type": "emphasize", "startMs": 1400, "durationMs": 500},
    ]
    with pytest.raises(ActionEditError) as duplicate:
        normalize_object_actions(
            "headline", actions, scene_duration_ms=4000
        )
    assert duplicate.value.code == "ACTION_CHANNEL_CONFLICT"

    with pytest.raises(ActionEditError) as transient:
        normalize_object_actions(
            "headline",
            [
                {"type": "enter", "startMs": 0, "durationMs": 500},
                {"type": "exit", "startMs": 700, "durationMs": 400},
            ],
            scene_duration_ms=4000,
            is_exit_object=False,
        )
    assert transient.value.code == "ACTION_EXIT_NOT_TRANSITIONAL"


def test_replan_keeps_manual_edit_or_reports_target_identity_conflict():
    base = {
        "nodes": [{"id": "target", "type": "text", "title": "原始标题"}],
        "motion": [],
    }
    edited = {
        "nodes": [{"id": "target", "type": "text", "title": "人工标题"}],
        "motion": [],
    }
    manual = {
        "base_scene": base,
        "scene": edited,
        "base_binding": None,
        "binding": None,
    }

    unchanged_identity = {
        "nodes": [{"id": "target", "type": "text", "title": "新计划标题"}],
        "motion": [],
    }
    merged = merge_manual_edits(unchanged_identity, None, manual)
    assert merged["scene"]["nodes"][0]["title"] == "人工标题"
    assert merged["conflicts"] == []

    changed_identity = {
        "nodes": [{"id": "target", "type": "shape", "title": "新计划形状"}],
        "motion": [],
    }
    conflicted = merge_manual_edits(changed_identity, None, manual)
    assert conflicted["conflicts"][0]["code"] == "MANUAL_TARGET_CONFLICT"
    assert conflicted["scene"]["nodes"][0]["type"] == "shape"
