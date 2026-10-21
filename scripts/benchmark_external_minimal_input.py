"""Benchmark the compact external-Agent task input against the full packet.

Builds a representative packet from a versioned course plan (real scene compile,
real capability facts and execution constraints) plus frozen evidence fields,
then measures the full `task.json` view against `task-minimal.json`. Provider-free
and read-only; this is an input-size comparison, not a live Agent run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from artifact_fingerprint import sha256_json  # noqa: E402
from html_design_agent import component_context  # noqa: E402
from html_external_handoff import _minimal_task  # noqa: E402
from html_handoff_contract import RULES, operation_schema  # noqa: E402
from html_handoff_execution import create_execution  # noqa: E402
from html_handoff_models import ExportRequest  # noqa: E402
import html_scene_editing as editor  # noqa: E402
from html_production_service import compile_plan  # noqa: E402
from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan  # noqa: E402

FIXTURES = ROOT / "checks/fixtures/course-structure-plans.json"


def build_packet():
    catalog = load_template_catalog(ROOT)
    case = json.loads(FIXTURES.read_text(encoding="utf-8"))[0]
    plan = normalize_html_scene_plan(case["plan"], catalog, contract_slide=case["contract"])
    scene, binding = compile_plan(plan, case["contract"], catalog)
    scope = [node["id"] for node in scene["nodes"]
             if node["type"] in ("arrow", "text", "card")][:4]
    request = ExportRequest(task_type="static_repair", goal="修复关系箭头穿过文字并保持原文",
                            scope=scope, expected_revision=1)
    doc = {"scene": scene, "binding": binding, "beats": [], "manual": None,
           "capabilities": editor.capabilities(),
           "resources": {"assets": []}}
    capabilities = component_context(scene, ROOT)
    arrow = next(node["id"] for node in scene["nodes"] if node["type"] == "arrow")
    text = next(node["id"] for node in scene["nodes"] if node["type"] == "text")
    context = {
        "content": "content.json", "design": {"key": "0" * 64, "image_sha256": "0" * 64,
                                              "status": "candidate", "stale": False,
                                              "file": "reference/design.png"},
        "clock": "audio_timeline", "missing_inputs": [],
        "scene": scene, "binding": binding, "beats": [],
        "bound_scene": scene, "timing": {"durationMs": scene["durationMs"]},
        "protected_paths": [["card-1", "presentation", "offsetX"]],
        "capabilities": capabilities,
        "assets": [{"id": "condensation", "file": "assets/condensation.png", "role": "image_asset"}],
        "evidence": {
            "issues": [{"code": "TEMPORAL_OVERLAP", "timeMs": 540, "targets": [arrow, text],
                        "measured": {"reason": "stroke_crosses_text"},
                        "allowed_repairs": ["layout_or_motion"]}],
            "capacityIssues": [{"target": "card-1", "triggers": [
                {"dimension": "text_bottom_overflow", "actual": 16.65, "limit": 0,
                 "tolerance": 1, "unit": "css_px"}]}],
            "screenshots": [{"timeMs": 0, "file": "evidence/frame-0.png"}],
            "frames": [], "passed": False,
        },
        "style": {"theme": {"id": "neutral-baseline", "version": "0.2.0"},
                  "layout": scene["layoutRef"]},
        "execution": create_execution(doc, request),
    }
    packet = {
        "format": "hps.html.external_task", "version": "0.2.0",
        "project_id": "fixture", "slide_id": scene["id"], "task_type": request.task_type,
        "goal": request.goal, "scope": scope, "contract_hash": "0" * 16,
        "expected_revision": 1, "audio_revision": "0" * 64,
        "context": context, "rules": RULES,
        "operation_schema": operation_schema(doc, capabilities, scope, request.task_type),
        "result_schema": {"format": "hps.html.external_result", "version": "0.2.0"},
        "files": [{"path": "reference/design.png", "sha256": "0" * 64, "size": 1,
                   "role": "design_reference"},
                  {"path": "evidence/frame-0.png", "sha256": "0" * 64, "size": 1,
                   "role": "actual_render"},
                  {"path": "voice.mp3", "sha256": "0" * 64, "size": 1, "role": "original_audio"},
                  {"path": "EXECUTION.md", "sha256": "0" * 64, "size": 1, "role": "execution_contract"}],
        "source_identity": {"revision": 1},
    }
    packet["task_id"] = sha256_json(packet)
    return packet


def measure(packet, candidates=None):
    full = json.dumps(packet, ensure_ascii=False, indent=2).encode()
    minimal = _minimal_task(packet, candidates)
    minimal_bytes = json.dumps(minimal, ensure_ascii=False, indent=2).encode()
    return {
        "full_bytes": len(full),
        "minimal_bytes": len(minimal_bytes),
        "reduction_ratio": round(1 - len(minimal_bytes) / len(full), 4),
        "full_top_level": sorted(packet),
        "minimal_top_level": sorted(minimal),
        "targets": len(minimal["targets"]),
        "defects": len(minimal["defects"]),
        "files": len(minimal["files"]),
        "operation_kinds": len(minimal["operation_kinds"]),
        "candidates": len(minimal["candidates"]),
        "model_calls": 0, "provider_calls": 0, "author_writes": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    packet = build_packet()
    result = measure(packet)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
