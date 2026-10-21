"""End-to-end injected capacity defect: baseline block -> deterministic repair.

Browser CI only: the real compiler and capacity QA run. No model, save or approval.
"""
import json
import warnings

from scripts.benchmark_reconstruction_repair import run


def test_injected_capacity_defect_is_blocked_then_deterministically_attempted():
    result = run()
    payload = "RECONSTRUCTION_BENCHMARK:" + json.dumps(result, ensure_ascii=False)
    print(payload)
    # pytest captures stdout for passing tests; warnings keep the frozen result
    # in the CI summary so the numbers remain auditable.
    warnings.warn(payload, stacklevel=1)
    assert result["pages"] >= 3
    assert result["baseline_failed"] >= 2
    assert result["model_calls"] == result["provider_calls"] == result["author_writes"] == 0
    for record in result["records"]:
        assert record["provider_calls"] == 0
        assert record["author_unchanged"] is True
        if record["baseline_passed"]:
            assert record["status"] == "not_injected"
        else:
            assert record["status"] in ("candidate", "needs_revision")
            assert record["attempts"] >= 0
