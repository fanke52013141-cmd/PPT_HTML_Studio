"""Benchmark deterministic capacity candidates on frozen capacity measurements.

No browser, provider or author write: candidate generation only, reusing the
production size hint/geometry constraints and the registered layout. Original
capacity QA remains the validator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import html_capacity_repair as capacity  # noqa: E402


def scene_and_layout():
    scene = json.loads((ROOT / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    scene["themeRef"]["id"] = "neutral-baseline"
    scene["version"] = "0.5.0"
    headline = next(node for node in scene["nodes"] if node["id"] == "headline")
    headline["presentation"] = {"typography": {"text": {"fontSizePx": 80}}}
    card = next(node for node in scene["nodes"] if node["id"] == "card-1")
    card["presentation"] = {"typography": {"body": {"fontSizePx": 32}}}
    catalog = json.loads((ROOT / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    layout = capacity._layout_for(scene, catalog)
    return scene, layout, catalog


def diagnostics():
    return {
        "font_case": {"capacityIssues": [{
            "target": "headline", "triggers": [
                {"dimension": "line_count", "actual": 4, "limit": 2, "tolerance": 0, "unit": "lines"}],
            "effectiveLimits": {"width": 800, "height": 120, "maxLines": 2}}]},
        "box_case": {"capacityIssues": [{
            "target": "card-1", "triggers": [
                {"dimension": "box_height", "actual": 316.65, "limit": 300, "tolerance": 1, "unit": "canvas_px"}],
            "effectiveLimits": {"width": 520, "height": 300, "maxLines": 6}}]},
    }


def run(baseline=False):
    scene, layout, catalog = scene_and_layout()
    scope = ["headline", "card-1"]
    records = []
    started = time.perf_counter()
    for name, diagnostic in diagnostics().items():
        if baseline:
            candidates = []
        else:
            candidates = capacity.capacity_candidates(scene, layout, diagnostic, catalog, scope)
        kinds = sorted({operation["kind"] for operations in candidates for operation in operations})
        fonts = [operation["values"]["fontSizePx"] for operations in candidates
                 for operation in operations if operation["kind"] == "set_text_style"]
        sizes = [operation["values"] for operations in candidates
                 for operation in operations if operation["kind"] == "set_presentation"]
        records.append({"case": name, "candidates": len(candidates), "kinds": kinds,
                        "font_min": min(fonts) if fonts else None,
                        "font_max": max(fonts) if fonts else None,
                        "size_candidates": len(sizes)})
    return {
        "mode": "baseline" if baseline else "deterministic_capacity",
        "version": capacity.VERSION,
        "cases": records,
        "candidates_total": sum(record["candidates"] for record in records),
        "model_calls": 0, "provider_calls": 0, "author_writes": 0,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
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
