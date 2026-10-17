"""Adapter-boundary measurements only; never infer usage, cost or approval."""
from math import isfinite


def request_role(kind, kwargs):
    prefix = str(kwargs.get("artifact_prefix", ""))
    for marker, role in (("html_scene_plan_", "planning"),
                         ("design_understanding-", "design_understanding"),
                         ("layout-agent-", "layout_repair"),
                         ("design-reconstruct-", "reconstruction"),
                         ("design_fidelity_review-", "fidelity_review")):
        if prefix.startswith(marker):
            return role
    if kind == "image" and kwargs.get("transparent_background") is not None:
        return "asset_image" if kwargs["transparent_background"] else "design_image"
    return kind


def execution_summary(stages):
    records = [record for key, record in stages.items() if key.startswith(("json:", "image:"))]
    roles = {}
    summary = {"version": "0.1.0", "recorded_requests": len(records), "measured_adapter_calls": 0,
               "recorded_reuses": 0, "unmeasured_requests": 0, "elapsed_ms": 0,
               "untimed_requests": 0, "adapter_input_bytes": 0, "attachment_bytes": 0,
               "output_bytes": 0, "usage": None, "usage_complete": bool(records),
               "cost": None, "roles": roles}
    for record in records:
        metrics = record.get("metrics")
        if not isinstance(metrics, dict):
            summary["unmeasured_requests"] += 1
            summary["untimed_requests"] += 1
            summary["usage_complete"] = False
            continue
        usage = metrics.get("usage")
        if isinstance(usage, dict):
            if any(type(usage.get(field)) is not int or usage[field] < 0
                   for field in ("prompt_tokens", "completion_tokens", "total_tokens")):
                summary["usage_complete"] = False
            if summary["usage"] is None:
                summary["usage"] = {"prompt_tokens": 0, "completion_tokens": 0,
                                    "total_tokens": 0, "completion_tokens_details": {"reasoning_tokens": 0}}
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                count = usage.get(field)
                if type(count) is int and count >= 0:
                    summary["usage"][field] += count
            reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
            if type(reasoning) is int and reasoning >= 0:
                summary["usage"]["completion_tokens_details"]["reasoning_tokens"] += reasoning
        else:
            summary["usage_complete"] = False
        if type(metrics.get("adapter_calls")) is not int:
            summary["unmeasured_requests"] += 1
        role = metrics.get("role")
        if role not in {"planning", "design_understanding", "layout_repair", "reconstruction",
                        "fidelity_review", "asset_image", "design_image", "json", "image"}:
            role = "unknown"
        aggregate = roles.setdefault(role, {"adapter_calls": 0, "reuses": 0, "elapsed_ms": 0})
        for source, target in (("adapter_calls", "measured_adapter_calls"), ("reuses", "recorded_reuses"),
                               ("adapter_input_bytes", "adapter_input_bytes"), ("attachment_bytes", "attachment_bytes"),
                               ("output_bytes", "output_bytes")):
            value = metrics.get(source, 0)
            if type(value) is int and value >= 0:
                summary[target] += value
                if source in aggregate:
                    aggregate[source] += value
        elapsed = metrics.get("elapsed_ms")
        if type(elapsed) in (int, float) and isfinite(elapsed) and elapsed >= 0:
            summary["elapsed_ms"] += elapsed
            aggregate["elapsed_ms"] += elapsed
        else:
            summary["untimed_requests"] += 1
    return summary
