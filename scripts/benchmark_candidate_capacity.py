"""Original-browser cumulative unsaved capacity acceptance, without providers.

Controlled fixtures, not real-course or visual approval. Preserves all evidence
under a new output directory; never writes a saved author scene.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from html_capacity_repair import solve_capacity_candidate  # noqa: E402
from html_visual_review_service import HtmlReviewDependencies  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = json.loads((ROOT / "checks/fixtures/capacity-baseline/ordinary.json").read_text(encoding="utf-8"))
    records = []
    for name in ("normal", "two-cards", "budget", "protected"):
        folder = output / name
        (folder / "planning").mkdir(parents=True)
        scene = copy.deepcopy(base)
        if name != "normal":
            for node in scene["nodes"]:
                if node["id"] in ("card-1", "card-2"):
                    node["presentation"] = {"height": 80}
        manual = {"protected_paths": [["scene", "nodes", target, "presentation"]
                                      for target in ("card-1", "card-2")]} if name == "protected" else None
        write_json_atomic(folder / "planning/visual_contract.json",
                          {"slides": [{"slide_id": scene["id"], "narration_beats": []}]})
        write_json_atomic(folder / "input-scene.json", scene)

        def no_provider(**kwargs):
            raise AssertionError("Deterministic capacity acceptance must not call a provider")

        original = copy.deepcopy(scene)
        result = solve_capacity_candidate(scene, None, run_dir=folder,
            deps=HtmlReviewDependencies(ROOT, no_provider), manual=manual,
            **({"max_states": 1} if name == "budget" else {}))
        status = result["summary"]["status"]
        expected = {"normal": "unchanged", "two-cards": "candidate",
                    "budget": "budget_exhausted", "protected": "needs_revision"}[name]
        valid = status == expected and scene == original
        if name in ("normal", "two-cards"):
            preflight = (result["report"] or {}).get("geometry_preflight", {})
            valid = valid and preflight.get("passed") is True and preflight.get("coverage", {}).get("frame_complete") is True
        if name == "two-cards":
            changed = {n["id"] for n, old in zip(result["scene"]["nodes"], original["nodes"]) if n != old}
            valid = valid and changed == {"card-1", "card-2"}
        if name == "protected":
            valid = valid and result["scene"] == original
            valid = valid and any(a.get("code") == "MANUAL_FIELD_PROTECTED" for a in result["summary"]["attempts"])
        record = {"case": name, "expected_status": expected, "actual_status": status,
                  "passed": bool(valid), "input_unchanged": scene == original,
                  "saved_author_exists": (folder / f"planning/html_visual/scene-{scene['id']}.json").exists(),
                  "summary": result["summary"]}
        record["passed"] = record["passed"] and not record["saved_author_exists"]
        records.append(record)
        write_json_atomic(folder / "acceptance.json", record)
    summary = {"format": "hps.candidate_capacity_acceptance/0.1.0", "provenance": "controlled_fixture",
               "passed": all(r["passed"] for r in records), "cases": records,
               "provider_calls": 0, "production_author_writes": 0, "approvals": 0,
               "boundary": "Real browser checks on controlled fixtures; no real-course or model-fidelity claim."}
    write_json_atomic(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory; existing paths are rejected")
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"passed": result["passed"], "cases": [{"case": c["case"], "status": c["actual_status"],
                      "passed": c["passed"]} for c in result["cases"]]}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
