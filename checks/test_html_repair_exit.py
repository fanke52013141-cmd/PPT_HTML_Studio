"""Explicit stop semantics over measured failures, no model or author writes."""
import pytest
from html_repair_progress import repair_exit_reason


@pytest.mark.parametrize("report,rounds,stopped,reason,expected", [
    ({"passed": True}, 2, False, None, None),
    ({"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED"}, 3, False, None, "budget_exhausted"),
    ({"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED"}, 1, True, None, "model_stop"),
    ({"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED"}, 1, False, None, "missing_diagnostic_evidence"),
    ({"passed": False, "message": "RESOURCE_INVALID"}, 0, False, None, "non_capacity_failure"),
    ({"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED"}, 3, True, "repeated_patch", "repeated_patch"),
])
def test_repair_exit_distinguishes_success_budget_capability_and_no_progress(report, rounds, stopped, reason, expected):
    assert repair_exit_reason(report, rounds=rounds, max_rounds=3, stopped=stopped, reason=reason) == expected
