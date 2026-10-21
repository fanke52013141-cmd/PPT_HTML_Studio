"""Frozen overflow and arrow-crossing detection benchmark.

Cases replay frozen measurements through the production capacity predicate and
the production vector-overlap core. No browser, provider, author write or
approval: this measures detection policy on frozen facts, not rendering quality
or real-course acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "checks/fixtures/overflow-crossing/probe.cjs"

KINDS = ("text_overflow", "arrow_text_crossing")
PROVENANCE = ("documented_real_observation", "controlled_frame")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows):
    scored = [r for r in rows if r["expected"] is not None]
    tp = sum(r["expected"] is True and r["predicted"] is True for r in scored)
    fn = sum(r["expected"] is True and r["predicted"] is False for r in scored)
    tn = sum(r["expected"] is False and r["predicted"] is False for r in scored)
    fp = sum(r["expected"] is False and r["predicted"] is True for r in scored)
    positives = sum(r["expected"] is True for r in scored)
    negatives = len(scored) - positives
    unresolved_positive = sum(r["expected"] is True and r["predicted"] is None for r in scored)
    unresolved_negative = sum(r["expected"] is False and r["predicted"] is None for r in scored)
    ratio = lambda a, b: a / b if b else None
    return {
        "labeled_cases": len(scored),
        "excluded_ambiguous": len(rows) - len(scored),
        "positives": positives,
        "negatives": negatives,
        "tp": tp, "fn": fn, "tn": tn, "fp": fp,
        "unresolved_positive": unresolved_positive,
        "unresolved_negative": unresolved_negative,
        "detector_undetermined": sum(r["predicted"] is None for r in rows),
        "false_negative_rate_on_decisive": ratio(fn, tp + fn),
        "false_positive_rate_on_decisive": ratio(fp, tn + fp),
        "miss_or_unresolved_over_all_positives": ratio(fn + unresolved_positive, positives),
        "decision_coverage": ratio(tp + fn + tn + fp, len(scored)),
        "elapsed_seconds": round(sum(r["elapsed_ms"] for r in rows) / 1000, 6),
    }


def validate(dataset):
    if (dataset.get("format") != "hps.overflow_crossing_dataset"
            or dataset.get("version") != "0.1.0"):
        raise ValueError("INVALID_DATASET_VERSION")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 40:
        raise ValueError("INVALID_CASES")
    ids = set()
    for case in cases:
        identity = case.get("id")
        if (not isinstance(identity, str) or not identity or identity in ids
                or len(identity) > 80):
            raise ValueError("INVALID_CASE_ID")
        ids.add(identity)
        if case.get("kind") not in KINDS or case.get("provenance") not in PROVENANCE:
            raise ValueError("INVALID_CASE_KIND")
        if type(case.get("expected")) not in (bool, type(None)):
            raise ValueError("INVALID_EXPECTATION")
        if not case.get("note"):
            raise ValueError("CASE_NOTE_REQUIRED")
        if case["kind"] == "text_overflow":
            if not isinstance(case.get("measured"), dict) or not isinstance(case.get("limits"), dict):
                raise ValueError("INVALID_MEASUREMENT")
        else:
            if (not isinstance(case.get("nodes"), list) or not case["nodes"]
                    or not isinstance(case.get("pairs"), list) or not case["pairs"]
                    or not isinstance(case.get("frame"), dict)):
                raise ValueError("INVALID_FRAME")
    return cases


def evaluate(dataset_path, output):
    dataset_path, output = Path(dataset_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("OUTPUT_MUST_BE_NEW")
    dataset_hash = digest(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = validate(dataset)
    started = time.perf_counter()
    probe_output = subprocess.run(
        ["node", str(PROBE), str(dataset_path)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    if probe_output.returncode != 0:
        raise ValueError("PROBE_FAILED: " + (probe_output.stderr or "")[-800:])
    probe = json.loads(probe_output.stdout)
    by_id = {result["id"]: result for result in probe["results"]}
    if set(by_id) != {case["id"] for case in cases}:
        raise ValueError("PROBE_CASE_MISMATCH")
    rows = []
    for case in cases:
        verdict = by_id[case["id"]]["verdict"]
        if case["kind"] == "text_overflow":
            predicted = bool(verdict["flagged"])
        else:
            predicted = None if verdict["undetermined"] else bool(verdict["flagged"])
        rows.append({
            "id": case["id"], "kind": case["kind"], "provenance": case["provenance"],
            "note": case["note"], "expected": case["expected"], "predicted": predicted,
            "elapsed_ms": round(by_id[case["id"]]["elapsed_ms"], 6),
            "evidence": verdict,
        })
    kinds = sorted({row["kind"] for row in rows})
    provenances = sorted({row["provenance"] for row in rows})
    summary = {
        "dataset_sha256": dataset_hash,
        "detector_version": probe["version"],
        "provider_calls": 0, "browser_calls": 0, "author_writes": 0,
        "cases": len(cases),
        "by_kind": {kind: metrics([r for r in rows if r["kind"] == kind]) for kind in kinds},
        "by_provenance": {p: metrics([r for r in rows if r["provenance"] == p]) for p in provenances},
        "wall_seconds": round(time.perf_counter() - started, 6),
        "rows": rows,
        "boundary": "Frozen detection-policy replay: capacity predicate and linear vector core only. "
                    "No rendering, screenshot, model, author save or approval. Documented real "
                    "measurements are replayed values, not re-captured pages; real crossing pairs "
                    "from another machine require hash-sealed transfer. Ambiguous expectations "
                    "stay excluded from decisive denominators.",
    }
    if digest(dataset_path) != dataset_hash:
        raise ValueError("INPUT_CHANGED_DURING_EVALUATION")
    output.mkdir(parents=True)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    summary = evaluate(args.dataset, args.output)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
