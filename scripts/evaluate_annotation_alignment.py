"""Evaluate measured predictions against independently labelled audio starts.

Input: JSON rows with sample_id, category, truth_start_sec, predicted_start_sec,
reliable, truth_source ('human'), audio_sha256, truth_audio_sha256.
Missing truth is reported as unlabelled, never counted as passing.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def evaluate(rows):
    ids = [row["sample_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate sample_id")
    measured, missing, unavailable = [], [], []
    for row in rows:
        truth = row.get("truth_start_sec")
        if truth is None:
            missing.append(row["sample_id"])
            continue
        if row.get("truth_source") != "human":
            raise ValueError("truth must be independently human-labelled")
        if not row.get("audio_sha256") or row.get("truth_audio_sha256") != row["audio_sha256"]:
            raise ValueError("truth audio hash mismatch")
        if isinstance(truth, bool) or not isinstance(truth, (int, float)) or not math.isfinite(truth) or truth < 0:
            raise ValueError("invalid truth time")
        duration = row.get('duration_sec')
        if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float))
                                     or not math.isfinite(duration) or duration <= 0 or truth >= duration):
            raise ValueError('truth time outside audio duration')
        predicted = row.get("predicted_start_sec")
        if not row.get("reliable") or predicted is None:
            unavailable.append(row["sample_id"])
            continue
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
               for v in (truth, predicted)):
            raise ValueError("invalid time")
        measured.append({"sample_id": row["sample_id"], "category": row["category"],
                         "absolute_error_ms": abs(truth - predicted) * 1000})
    errors = sorted(row["absolute_error_ms"] for row in measured)
    def percentile(p):
        return errors[max(0, math.ceil(len(errors) * p) - 1)] if errors else None
    coverage = len(measured) / len(rows) if rows else 0
    p95 = percentile(.95)
    severe = [row["sample_id"] for row in measured if row["absolute_error_ms"] > 300]
    categories = {}
    for row in rows:
        categories[row["category"]] = categories.get(row["category"], 0) + 1
    return {"total": len(rows), "category_counts": categories,
            "unlabelled": missing, "manual_required": unavailable,
            "automatic_coverage": coverage, "p50_ms": percentile(.5), "p95_ms": p95,
            "max_ms": max(errors) if errors else None, "severe_false_accepts": severe,
            "measurements": measured,
            "passed": bool(len(rows) >= 100 and not missing and coverage >= .9
                           and p95 is not None and p95 <= 150 and not severe)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("total", "automatic_coverage", "p95_ms", "passed")}))


if __name__ == "__main__":
    main()
