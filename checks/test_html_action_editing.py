"""D01: object & action editing contract (registered actions, channel
conflicts, manual-override priority, AC11 evidence)."""
from __future__ import annotations

import pytest

from html_action_editing import (
    REGISTERED_ACTIONS,
    action_evidence,
    apply_action_edits,
    normalize_object_actions,
    ActionEditError,
)


def actions(**overrides) -> list:
    base = [
        {"type": "enter", "startMs": 0, "durationMs": 800, "offsetY": 12},
        {"type": "exit", "startMs": 8000, "durationMs": 600},
    ]
    base.extend(overrides.pop("extra", []))
    for key, value in overrides.items():
        for action in base:
            if action["type"] == key:
                action.update(value)
    return base


def test_registered_vocabulary_covers_three_explanatory_actions() -> None:
    # AC11: at least three explanation-bearing action types (plus enter).
    assert {"enter", "exit", "emphasize", "relation_draw"} <= set(REGISTERED_ACTIONS)


def test_normalizes_and_orders_windows(tmp_None=None) -> None:
    normalized = normalize_object_actions(
        "vapor",
        actions(extra=[{"type": "emphasize", "startMs": 3000, "durationMs": 900}]),
        scene_duration_ms=15000,
        is_exit_object=True,
    )
    assert [a["type"] for a in normalized] == ["enter", "emphasize", "exit"]
    assert normalized[0]["offsetY"] == 12


def test_unregistered_and_channel_conflicts_rejected() -> None:
    with pytest.raises(ActionEditError) as unregistered:
        normalize_object_actions(
            "vapor",
            [{"type": "explode", "startMs": 0, "durationMs": 500}],
            scene_duration_ms=15000,
            is_exit_object=True,
        )
    assert unregistered.value.code == "ACTION_UNREGISTERED"

    duplicated = actions(
        extra=[{"type": "emphasize", "startMs": 3000, "durationMs": 900},
               {"type": "emphasize", "startMs": 5000, "durationMs": 900}]
    )
    with pytest.raises(ActionEditError) as conflict:
        normalize_object_actions(
            "vapor", duplicated, scene_duration_ms=15000, is_exit_object=True
        )
    assert conflict.value.code == "ACTION_CHANNEL_CONFLICT"

    overlap = actions(
        extra=[{"type": "emphasize", "startMs": 500, "durationMs": 900}]
    )
    with pytest.raises(ActionEditError) as overlap_error:
        normalize_object_actions(
            "vapor", overlap, scene_duration_ms=15000, is_exit_object=True
        )
    assert overlap_error.value.code == "ACTION_WINDOW_OVERLAP"


def test_exit_requires_transitional_and_relation_requires_annotation() -> None:
    with pytest.raises(ActionEditError) as exit_denied:
        normalize_object_actions(
            "card-1", actions(), scene_duration_ms=15000, is_exit_object=False
        )
    assert exit_denied.value.code == "ACTION_EXIT_NOT_TRANSITIONAL"

    with pytest.raises(ActionEditError) as relation_denied:
        normalize_object_actions(
            "card-1",
            actions(extra=[{"type": "relation_draw", "startMs": 4000, "durationMs": 600}]),
            scene_duration_ms=15000,
            is_exit_object=True,
        )
    assert relation_denied.value.code == "ACTION_RELATION_NOT_ANNOTATION"


def test_enter_is_mandatory_and_bounds_enforced() -> None:
    with pytest.raises(ActionEditError) as missing:
        normalize_object_actions(
            "vapor",
            [{"type": "exit", "startMs": 8000, "durationMs": 600}],
            scene_duration_ms=15000,
            is_exit_object=True,
        )
    assert missing.value.code == "ACTION_ENTER_MISSING"

    with pytest.raises(ActionEditError) as overflow:
        normalize_object_actions(
            "vapor",
            [{"type": "enter", "startMs": 14900, "durationMs": 800}],
            scene_duration_ms=15000,
            is_exit_object=True,
        )
    assert overflow.value.code == "ACTION_TIME_OVERFLOW"


def test_manual_overrides_win_and_conflicts_are_explicit() -> None:
    planned = {"vapor": actions(), "card-1": [{"type": "enter", "startMs": 0, "durationMs": 800}]}
    manual = {
        "vapor": [
            {"type": "enter", "startMs": 1000, "durationMs": 800, "offsetY": 0},
            {"type": "exit", "startMs": 9000, "durationMs": 600},
        ],
        "removed-object": [{"type": "enter", "startMs": 0, "durationMs": 500}],
    }
    result = apply_action_edits(
        planned,
        scene_duration_ms=15000,
        manual_overrides=manual,
        exit_objects={"vapor"},
    )
    # Manual edit keeps priority over the replanned defaults.
    assert result["actions"]["vapor"][0]["startMs"] == 1000
    assert result["actions"]["card-1"][0]["startMs"] == 0
    # The override for an object the replan dropped is an explicit conflict.
    assert result["conflicts"] == [
        {
            "object_id": "removed-object",
            "reason": "object_removed_by_replan",
            "override": manual["removed-object"],
        }
    ]


def test_action_evidence_includes_beat_map() -> None:
    evidence = action_evidence(
        {
            "vapor": normalize_object_actions(
                "vapor", actions(), scene_duration_ms=15000, is_exit_object=True
            )
        },
        beat_map={"beat_001": {"objectId": "vapor", "action": "enter"}},
    )
    assert evidence["beat_map"]["beat_001"]["objectId"] == "vapor"
    assert evidence["objects"]["vapor"][0]["type"] == "enter"
    assert "relation_draw" in evidence["registered_actions"]
