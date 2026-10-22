"""End-to-end page-level benchmark: injected capacity defect -> deterministic repair.

Uses the versioned capacity-baseline scenes (0.5.0, no semantic binding), injects
the documented page-3 failure class, and runs the real browser QA plus the
deterministic capacity repair with zero model calls. Nothing is saved or approved.
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
import html_visual_store as store  # noqa: E402
from html_visual_review_service import HtmlReviewDependencies, review_scene  # noqa: E402

FIXTURES = ROOT / "checks/fixtures/capacity-baseline"
SCENES = ("ordinary", "dense")
DEPS = HtmlReviewDependencies(ROOT, lambda **kw: {})


def _run_dir(folder, slide_id):
    run = Path(folder)
    (run / "planning").mkdir(parents=True, exist_ok=True)
    (run / "planning/visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": slide_id, "narration_beats": []}]}),
        encoding="utf-8")
    return run


def _inject(scene, profile):
    cards = [node for node in scene["nodes"] if node["type"] == "card"]
    if not cards:
        return None
    card = cards[0]
    if profile == "mild":
        card.setdefault("presentation", {}).setdefault("typography", {})["body"] = {
            "fontSizePx": 30}
    else:
        card["body"] = (card.get("body") or "内容") * 3
        card.setdefault("presentation", {}).setdefault("typography", {})["body"] = {
            "fontSizePx": 28}
    return card["id"]


def build_cases():
    built = []
    for name in SCENES:
        scene = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        for profile in ("mild", "severe"):
            injected = copy.deepcopy(scene)
            target = _inject(injected, profile)
            if target:
                built.append({"name": name, "profile": profile, "scene": injected,
                              "slide_id": injected["id"], "target": target})
    return built


def run():
    started = time.perf_counter()
    records = []
    with tempfile.TemporaryDirectory() as folder:
        for index, item in enumerate(build_cases()):
            scene, slide_id = item["scene"], item["slide_id"]
            run_dir = _run_dir(Path(folder) / f"case-{index}", slide_id)
            store.save_scene(run_dir, slide_id, scene, 0)
            baseline = review_scene(scene, run_dir=run_dir, deps=DEPS)
            record = {"slide_id": slide_id, "profile": item["profile"],
                      "target": item["target"], "baseline_passed": bool(baseline.get("passed")),
                      "baseline_message": (baseline.get("message") or "")[:160]}
            if not baseline.get("passed"):
                trial = capacity.repair_capacity(
                    run_dir, slide_id,
                    {"expected_revision": 1, "scope": [item["target"]]})
                record.update(status=trial["status"], reason=trial.get("reason"),
                              repaired=trial["status"] == "candidate",
                              attempts=len(trial.get("attempts", [])),
                              attempts_detail=[{key: attempt.get(key) for key in
                                                ("passed", "code", "message")}
                                               for attempt in trial.get("attempts", [])],
                              provider_calls=trial["provider_calls"],
                              author_unchanged=trial["author_unchanged"])
            else:
                record.update(status="not_injected", repaired=False, attempts=0,
                              provider_calls=0, author_unchanged=True)
            records.append(record)
    mild = [record for record in records if record["profile"] == "mild"]
    severe = [record for record in records if record["profile"] == "severe"]
    return {
        "mode": "injected_capacity_end_to_end",
        "pages": len({record["slide_id"] for record in records}),
        "cases": len(records),
        "mild_cases": len(mild),
        "mild_baseline_failed": sum(not record["baseline_passed"] for record in mild),
        "mild_deterministically_repaired": sum(record["repaired"] for record in mild),
        "severe_cases": len(severe),
        "severe_baseline_failed": sum(not record["baseline_passed"] for record in severe),
        "severe_explicit_no_fit": sum(record["status"] == "needs_revision" for record in severe),
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
