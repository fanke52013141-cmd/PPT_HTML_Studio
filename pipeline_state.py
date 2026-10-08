"""Pure state transitions in visible workflow order with historical stage IDs."""

from __future__ import annotations

from typing import Any, Mapping


MIN_INTERNAL_STEP = 1
MAX_INTERNAL_STEP = 10
INTERNAL_STEP_ORDER = (1, 2, 3, 4, 5, 6, 7, 10, 9, 8)
VALID_STEP_STATES = frozenset({"pending", "in_progress", "completed", "pending_reconfirmation"})

# Eight stable visible steps; digital human remains optional.
USER_TO_INTERNAL_STEPS: dict[int, tuple[int, ...]] = {
    1: (1,),
    2: (2,),
    3: (3, 4),
    4: (5,),
    5: (6, 7),
    6: (10,),
    7: (9,),
    8: (8,),
}
INTERNAL_TO_USER_STEP: dict[int, int] = {
    internal: user for user, internal_steps in USER_TO_INTERNAL_STEPS.items() for internal in internal_steps
}


def validate_step(step: int) -> int:
    if isinstance(step, bool) or not isinstance(step, int) or not MIN_INTERNAL_STEP <= step <= MAX_INTERNAL_STEP:
        raise ValueError(f"internal pipeline step must be an integer from 1 to 10, got {step!r}")
    return step


def validate_statuses(statuses: Mapping[str, Any]) -> None:
    for key, value in statuses.items():
        try:
            step = int(key)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid pipeline step key: {key!r}") from exc
        validate_step(step)
        if value not in VALID_STEP_STATES:
            raise ValueError(f"invalid state for internal step {step}: {value!r}")


def _copy(statuses: Mapping[str, Any]) -> dict[str, str]:
    validate_statuses(statuses)
    return {str(key): str(value) for key, value in statuses.items()}


def begin_step(statuses: Mapping[str, Any], target_step: int) -> dict[str, str]:
    target_step = validate_step(target_step)
    result = _copy(statuses)
    for step in INTERNAL_STEP_ORDER[INTERNAL_STEP_ORDER.index(target_step) + 1:]:
        key = str(step)
        if result.get(key) == "completed":
            result[key] = "pending_reconfirmation"
        elif result.get(key) == "in_progress":
            result[key] = "pending"
    result[str(target_step)] = "in_progress"
    return result


def complete_step(statuses: Mapping[str, Any], target_step: int) -> dict[str, str]:
    target_step = validate_step(target_step)
    result = _copy(statuses)
    for step in INTERNAL_STEP_ORDER[INTERNAL_STEP_ORDER.index(target_step) + 1:]:
        key = str(step)
        if result.get(key) == "completed":
            result[key] = "pending_reconfirmation"
        elif result.get(key) in {"in_progress", "pending_reconfirmation"}:
            result[key] = "pending"
    result[str(target_step)] = "completed"
    return result


def mark_retry_needed(statuses: Mapping[str, Any], target_step: int) -> dict[str, str]:
    target_step = validate_step(target_step)
    result = _copy(statuses)
    result[str(target_step)] = "pending_reconfirmation"
    for step in INTERNAL_STEP_ORDER[INTERNAL_STEP_ORDER.index(target_step) + 1:]:
        key = str(step)
        if result.get(key) in {"completed", "in_progress", "pending_reconfirmation"}:
            result[key] = "pending"
    return result


def current_step_after_completion(current_step: int | None, target_step: int) -> int:
    target_step = validate_step(target_step)
    if current_step is None:
        return target_step
    validate_step(current_step)
    return max((current_step, target_step), key=INTERNAL_STEP_ORDER.index)
