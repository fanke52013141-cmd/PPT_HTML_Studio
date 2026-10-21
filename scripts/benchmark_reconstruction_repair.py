"""End-to-end page-level benchmark: injected capacity defect -> deterministic repair.

Each versioned course plan is compiled by the real compiler, then a card body is
lengthened (the documented page-3 failure class) and the page is reviewed by the
real browser QA. The deterministic capacity repair runs with no model calls.
Original QA remains the validator; nothing is saved or approved.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import html_capacity_repair as capacity  # noqa: E402
from html_production_service import compile_plan  # noqa: E402
from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan  # noqa: E402
from html_visual_review_service import HtmlReviewDependencies, review_scene  # noqa: E402

FIXTURES = ROOT / "checks/fixtures/course-structure-plans.json"
DEPS = HtmlReviewDependencies(ROOT, lambda **kw: {})


def _run_dir(folder, contract):
    run = Path(folder)
    (run / "planning").mkdir(parents=True, exist_ok=True)
    (run / "planning/visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": contract["slide_id"], "narration_beats": []}]}),
        encoding="utf-8")
    return run


def _inject(scene):
    cards = [node for node in scene["nodes"] if node["type"] == "card"]
    if not cards:
        return None
    card = cards[0]
    card["body"] = (card.get("body") or "内容") * 3
    card.setdefault("presentation", {}).setdefault("typography", {})["body"] = {
        "fontSizePx": 28}
    return card["id"]


def build_cases():
    catalog = load_template_catalog(ROOT)
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    built = []
    for case in cases:
        plan = normalize_html_scene_plan(case["plan"], catalog, contract_slide=case["contract"])
        scene, binding = compile_plan(plan, case["contract"], catalog)
        scene = copy.deepcopy(scene)
        target = _inject(scene)
        if target:
            built.append({"case": case, "scene": scene, "binding": binding, "target": target})
    return built


def run():
    started = time.perf_counter()
    records = []
    with tempfile.TemporaryDirectory() as folder:
        for index, item in enumerate(build_cases()):
            contract, scene = item["case"]["contract"], item["scene"]
            run_dir = _run_dir(Path(folder) / f"case-{index}", contract)
            baseline = review_scene(scene, run_dir=run_dir, deps=DEPS)
            record = {"slide_id": contract["slide_id"], "injected": True,
                      "target": item["target"], "baseline_passed": bool(baseline.get("passed")),
                      "baseline_message": (baseline.get("message") or "")[:160]}
            if not baseline.get("passed"):
                trial = capacity.repair_capacity(
                    run_dir, contract["slide_id"],
                    {"expected_revision": 0, "scope": [item["target"]]},
                    scene=scene, binding=item["binding"])
                record.update(status=trial["status"], reason=trial.get("reason"),
                              repaired=trial["status"] == "candidate",
                              attempts=len(trial.get("attempts", [])),
                              provider_calls=trial["provider_calls"],
                              author_unchanged=trial["author_unchanged"])
            else:
                record.update(status="not_injected", repaired=False, attempts=0,
                              provider_calls=0, author_unchanged=True)
            records.append(record)
    return {
        "mode": "injected_capacity_end_to_end",
        "pages": len(records),
        "baseline_failed": sum(not record["baseline_passed"] for record in records),
        "deterministically_repaired": sum(record["repaired"] for record in records),
        "explicit_no_fit": sum(record["status"] == "needs_revision" for record in records),
        "model_calls": 0, "provider_calls": 0, "author_writes": 0,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "records": records,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print("RECONSTRUCTION_BENCHMARK:" + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
