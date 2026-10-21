"""Benchmark deterministic relation attachment-point routing.

Cases replay frozen DOM frames through the production line-hit predicate and the
bounded endpoint solver. No browser, provider, author write or approval: the
original compiler and 30fps/registered QA remain the validator.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import html_geometry_repair as geometry  # noqa: E402

DATASET = ROOT / "checks/fixtures/geometry-endpoint-routing/dataset.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(case):
    arrow = next(node for node in case["nodes"] if node.get("from") or node["type"] == "arrow")
    text = next(node for node in case["nodes"] if node["type"] == "text")
    return {
        "passed": False,
        "issues": [{"code": "TEMPORAL_OVERLAP", "targets": [arrow["id"], text["id"]],
                    "measured": {"reason": "stroke_crosses_text"}, "timeMs": 0}],
        "frames": case["frames"],
    }


def endpoint_operations(proposals):
    return [
        operation
        for proposal in proposals
        for operation in proposal.get("operations", [])
        if operation.get("kind") == "set_endpoint_point"
    ]


def verify(case, operation):
    """Recompute hits for the proposed attachment points on every frozen frame."""
    nodes = {node["id"]: node for node in case["nodes"]}
    arrow = nodes[operation["targetId"]]
    candidate = copy.deepcopy(arrow)
    for side, point in operation["values"].items():
        candidate[side]["point"] = point
    points = geometry._endpoint_points(candidate)
    text_ids = {node["id"] for node in case["nodes"] if node["type"] == "text"}
    return sum(
        geometry._endpoint_route_hits(candidate, points, frame, text_ids) or 0
        for frame in case["frames"]
    )


def run(baseline=False):
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    if baseline:
        original = geometry.propose_endpoint_routes
        geometry.propose_endpoint_routes = lambda *args, **kwargs: []
        try:
            return _run(dataset, baseline=True)
        finally:
            geometry.propose_endpoint_routes = original
    return _run(dataset, baseline=False)


def _run(dataset, *, baseline):
    records = []
    started = time.perf_counter()
    for case in dataset["cases"]:
        doc = {"scene": {"nodes": copy.deepcopy(case["nodes"])}}
        report = build_report(case)
        proposals = geometry.propose(doc, case["scope"], report, copy.deepcopy(case["frames"]))
        operations = endpoint_operations(proposals)
        if case["expected"] == "route_found":
            clean = [operation for operation in operations if verify(case, operation) == 0]
            records.append({"id": case["id"], "expected": case["expected"],
                            "solved": bool(clean), "candidates": len(clean),
                            "total_proposals": len(operations)})
        else:
            records.append({"id": case["id"], "expected": case["expected"],
                            "solved": not operations, "candidates": 0,
                            "total_proposals": len(operations)})
    positives = [record for record in records if record["expected"] == "route_found"]
    others = [record for record in records if record["expected"] != "route_found"]
    return {
        "dataset_sha256": digest(DATASET),
        "mode": "baseline" if baseline else "endpoint_routing",
        "detector_version": geometry.VERSION,
        "cases": len(records),
        "route_cases": len(positives),
        "routes_solved": sum(record["solved"] for record in positives),
        "route_success_rate": (sum(record["solved"] for record in positives) / len(positives))
        if positives else None,
        "non_route_cases": len(others),
        "non_route_correctly_skipped": sum(record["solved"] for record in others),
        "false_candidates": sum(record["total_proposals"] for record in others),
        "model_calls": 0, "provider_calls": 0, "author_writes": 0,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "records": records,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run(baseline=args.baseline)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
