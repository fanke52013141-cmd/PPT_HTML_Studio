"""Aggregate offline before/after metrics for the restoration optimizations.

Runs the frozen, provider-free benchmarks (planning endpoint normalization,
relation attachment routing, capacity candidates, external minimal input) and
prints one comparable table. Browser-only end-to-end numbers are reported by
checks/test_reconstruction_repair_benchmark.py in CI, not here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import benchmark_capacity_repair as capacity_bench  # noqa: E402
from scripts import benchmark_external_minimal_input as minimal_bench  # noqa: E402
from scripts import benchmark_geometry_endpoint_routing as routing_bench  # noqa: E402
from scripts import benchmark_plan_endpoint_normalization as plan_bench  # noqa: E402


def summarize():
    plan_before = plan_bench_metrics(baseline=True)
    plan_after = plan_bench_metrics(baseline=False)
    routing_before = routing_bench.run(baseline=True)
    routing_after = routing_bench.run(baseline=False)
    capacity_before = capacity_bench.run(baseline=True)
    capacity_after = capacity_bench.run(baseline=False)
    packet = minimal_bench.build_packet()
    minimal = minimal_bench.measure(packet)
    return {
        "format": "hps.restoration_optimization_summary/0.1.0",
        "planning_endpoint_normalization": {
            "before": {"plans_accepted": plan_before["slot_name_accepted"],
                       "variants": plan_before["slot_name_variants"],
                       "scene_identity": plan_before["scene_identity_matches"]},
            "after": {"plans_accepted": plan_after["slot_name_accepted"],
                      "variants": plan_after["slot_name_variants"],
                      "scene_identity": plan_after["scene_identity_matches"],
                      "receipts": plan_after["endpoint_resolution_receipts"]},
            "invalid_rejected": {"before": plan_before["unknown_rejected"] + plan_before["kind_mismatch_rejected"],
                                 "after": plan_after["unknown_rejected"] + plan_after["kind_mismatch_rejected"]},
        },
        "relation_attachment_routing": {
            "before": {"routes_solved": routing_before["routes_solved"],
                       "route_cases": routing_before["route_cases"],
                       "non_route_correctly_skipped": routing_before["non_route_correctly_skipped"]},
            "after": {"routes_solved": routing_after["routes_solved"],
                      "route_cases": routing_after["route_cases"],
                      "non_route_correctly_skipped": routing_after["non_route_correctly_skipped"],
                      "false_candidates": routing_after["false_candidates"]},
        },
        "capacity_candidates": {
            "before": {"candidates": capacity_before["candidates_total"]},
            "after": {"candidates": capacity_after["candidates_total"],
                      "cases": {record["case"]: record["candidates"] for record in capacity_after["cases"]}},
        },
        "external_agent_minimal_input": {
            "full_bytes": minimal["full_bytes"],
            "minimal_bytes": minimal["minimal_bytes"],
            "reduction_ratio": minimal["reduction_ratio"],
            "targets": minimal["targets"],
            "defects": minimal["defects"],
            "candidates_supported": "deterministic endpoint routing forwarded with requires_original_qa",
        },
        "global_zero_boundaries": {"model_calls": 0, "provider_calls": 0,
                                    "author_writes": 0, "approvals": 0},
        "boundary": "Frozen offline fixtures only. Real course pages, live model quality and browser QA "
                    "on the other machine remain separate; no approval is implied.",
    }


def plan_bench_metrics(*, baseline):
    if baseline:
        import html_storyboard_planning

        original = html_storyboard_planning._resolve_relation_endpoints
        html_storyboard_planning._resolve_relation_endpoints = lambda plan: []
        try:
            return plan_bench.metrics([plan_bench.run_case(case, plan_bench.load_template_catalog(ROOT))
                                       for case in json.loads(plan_bench.FIXTURES.read_text(encoding="utf-8"))])
        finally:
            html_storyboard_planning._resolve_relation_endpoints = original
    return plan_bench.metrics([plan_bench.run_case(case, plan_bench.load_template_catalog(ROOT))
                               for case in json.loads(plan_bench.FIXTURES.read_text(encoding="utf-8"))])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = summarize()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
