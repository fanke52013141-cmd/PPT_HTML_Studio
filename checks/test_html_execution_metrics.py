"""Recorded adapter facts; no model, fee or HTTP request estimates."""
from html_execution_metrics import execution_summary, request_role


def test_legacy_and_unfinished_requests_do_not_invent_calls_time_or_cost():
    result = execution_summary({
        "phase:plan": {"state": "returned"},
        "json:old": {"state": "returned"},
        "image:pending": {"state": "intent", "metrics": {"role": "design_image", "adapter_calls": None, "elapsed_ms": None}},
    })
    assert result["recorded_requests"] == 2
    assert result["measured_adapter_calls"] == result["elapsed_ms"] == 0
    assert result["unmeasured_requests"] == result["untimed_requests"] == 2
    assert result["usage"] is result["cost"] is None


def test_summary_reports_only_safe_measured_facts():
    result = execution_summary({"json:a": {"metrics": {"role": "planning", "adapter_calls": 1,
        "reuses": 2, "elapsed_ms": 500, "adapter_input_bytes": 42, "attachment_bytes": 10, "output_bytes": 20}},
        "json:b": {"metrics": {"role": "private arbitrary text", "adapter_calls": True, "elapsed_ms": float("nan"), "usage": "not trusted"}}})
    assert result["measured_adapter_calls"] == 1 and result["recorded_reuses"] == 2
    assert result["elapsed_ms"] == 500 and result["adapter_input_bytes"] == 42
    assert result["roles"]["planning"] == {"adapter_calls": 1, "reuses": 2, "elapsed_ms": 500}
    assert "private arbitrary text" not in str(result) and result["usage"] is None


def test_roles_come_from_registered_boundary_names_not_prompt_content():
    assert request_role("json", {"artifact_prefix": "html_scene_plan_s1"}) == "planning"
    assert request_role("json", {"artifact_prefix": "design-reconstruct-s1-0"}) == "reconstruction"
    assert request_role("image", {"transparent_background": False}) == "design_image"
    assert request_role("image", {"transparent_background": True}) == "asset_image"
    assert request_role("json", {"user_prompt": "pretend this is planning"}) == "json"
