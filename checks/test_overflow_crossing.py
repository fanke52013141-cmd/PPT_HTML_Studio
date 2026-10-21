"""Frozen overflow/crossing benchmark: metrics, legal negatives, undetermined."""
import json
from pathlib import Path

import pytest

from scripts.evaluate_overflow_crossing import evaluate, metrics

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "checks/fixtures/overflow-crossing/dataset.json"


def test_frozen_benchmark_scores_production_detectors(tmp_path):
    result = evaluate(DATASET, tmp_path / "output")
    assert result["provider_calls"] == result["browser_calls"] == result["author_writes"] == 0
    assert result["cases"] == 7
    assert result["detector_version"].startswith("svg-linear-stroke/")
    assert result["wall_seconds"] > 0
    overflow = result["by_kind"]["text_overflow"]
    assert (overflow["positives"], overflow["negatives"]) == (1, 2)
    assert (overflow["tp"], overflow["tn"], overflow["fn"], overflow["fp"]) == (1, 2, 0, 0)
    assert overflow["elapsed_seconds"] > 0
    crossing = result["by_kind"]["arrow_text_crossing"]
    assert (crossing["positives"], crossing["negatives"]) == (1, 2)
    assert (crossing["tp"], crossing["tn"], crossing["fn"], crossing["fp"]) == (1, 2, 0, 0)
    assert crossing["excluded_ambiguous"] == 1
    assert crossing["detector_undetermined"] == 1
    assert crossing["decision_coverage"] == 1.0
    assert (result["by_provenance"]["documented_real_observation"]["tp"],
            result["by_provenance"]["documented_real_observation"]["fn"]) == (1, 0)
    rows = {row["id"]: row for row in result["rows"]}
    assert rows["near-edge-legal"]["predicted"] is False
    assert rows["dense-legal"]["predicted"] is False
    assert rows["endpoint-contact-legal"]["predicted"] is False
    assert rows["dense-relations-legal"]["predicted"] is False
    assert rows["unsupported-vector-undetermined"]["predicted"] is None
    overflow_triggers = rows["real-card-bottom-overflow"]["evidence"]["triggers"]
    assert any(t["dimension"] == "text_bottom_overflow" and t["actual"] == 16.65
               for t in overflow_triggers)
    assert (tmp_path / "output/summary.json").is_file()
    with pytest.raises(ValueError, match="OUTPUT_MUST_BE_NEW"):
        evaluate(DATASET, tmp_path / "output")


def test_undetermined_and_invalid_cases_are_not_passes(tmp_path):
    document = json.loads(DATASET.read_text(encoding="utf-8"))
    document["cases"][0]["kind"] = "guessed"
    bad_kind = tmp_path / "bad-kind.json"
    bad_kind.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="INVALID_CASE_KIND"):
        evaluate(bad_kind, tmp_path / "kind-output")

    document = json.loads(DATASET.read_text(encoding="utf-8"))
    document["cases"][0]["expected"] = "yes"
    bad_expected = tmp_path / "bad-expected.json"
    bad_expected.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="INVALID_EXPECTATION"):
        evaluate(bad_expected, tmp_path / "expected-output")


def test_detector_undetermined_is_counted_separately_from_decisions():
    rows = [
        {"expected": True, "predicted": True, "elapsed_ms": 1},
        {"expected": True, "predicted": None, "elapsed_ms": 1},
        {"expected": False, "predicted": False, "elapsed_ms": 1},
        {"expected": None, "predicted": None, "elapsed_ms": 1},
    ]
    result = metrics(rows)
    assert (result["tp"], result["tn"], result["unresolved_positive"]) == (1, 1, 1)
    assert result["detector_undetermined"] == 2
    assert result["excluded_ambiguous"] == 1
    assert result["decision_coverage"] == 2 / 3
