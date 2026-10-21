"""Frozen three-case browser baseline and offline repair replay. No provider calls."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from artifact_fingerprint import sha256_file, sha256_json  # noqa: E402
from html_candidate_agent import repair_candidate  # noqa: E402
from html_visual_review_service import HtmlReviewDependencies, review_scene  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402

FIXTURES = ROOT / "checks/fixtures/capacity-baseline"


def source_identity():
    """Pin working bytes as well as HEAD: uncommitted fixes are part of the experiment."""
    tracked = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    files = {name: sha256_file(ROOT / name) for name in tracked if name and (ROOT / name).is_file()}
    # Include this new tool and fixtures before the first commit too.
    for path in [Path(__file__).resolve(), *FIXTURES.glob("*.json")]:
        files[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    return {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
            "files": files, "working_tree_sha256": sha256_json(files)}


def semantic_state(scene):
    value = copy.deepcopy(scene)
    # Presentation is the sole change permitted by these offline fixture decisions.
    for node in value["nodes"]:
        node.pop("presentation", None)
    return value


def run_course_baseline(source_run, output, slides, temporal_mode=None):
    """Freeze local course evidence without touching its authors, approvals or providers."""
    source_run, output = Path(source_run).resolve(), Path(output).resolve()
    if temporal_mode not in (None, "sampled", "output_frames"):
        raise ValueError("Unsupported temporal mode")
    if output.exists() or source_run == output or source_run in output.parents or output in source_run.parents:
        raise ValueError("Use a new output outside the source run")
    if not slides or len(slides) > 5 or len(set(slides)) != len(slides):
        raise ValueError("Select one to five distinct slides")
    for slide in slides:
        if not slide or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in slide):
            raise ValueError("Invalid slide identity")
    # Freeze only course inputs and resource bytes. Exclude approvals, caches,
    # historical jobs and credentials from the isolated run. Revision and
    # manual protection are author inputs, not disposable evaluation caches.
    selected = [source_run / "planning/visual_contract.json"]
    visual = source_run / "planning/html_visual"
    selected += [visual / f"{prefix}-{slide}.json" for slide in slides for prefix in ("scene", "binding", "edits")]
    selected += [visual / "resources.json", visual / "revision.json"]
    for directory in (visual / "assets", visual / "editor-assets", source_run / "inputs", source_run / "slides"):
        if directory.is_dir():
            selected += [p for p in directory.rglob("*") if p.is_file()]
    files = {}
    total = 0
    for path in sorted(set(selected)):
        if not path.exists():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(source_run):
            raise ValueError("Course resource must stay inside source run")
        total += path.stat().st_size
        if path.stat().st_size > 128 * 1024 * 1024 or total > 1024 * 1024 * 1024:
            raise ValueError("Course exceeds isolated copy budget")
        files[path.relative_to(source_run).as_posix()] = sha256_file(path)
    for slide in slides:
        if f"planning/html_visual/scene-{slide}.json" not in files:
            raise ValueError("Missing source scene: " + slide)
    output.mkdir(parents=True)
    source = source_identity()
    write_json_atomic(output / "source-manifest.json", source)
    write_json_atomic(output / "course-manifest.json", {"source_run": str(source_run), "files": files,
                      "slides": slides, "input_sha256": sha256_json(files)})
    isolated = output / "isolated-run"
    for relative, expected in files.items():
        destination = isolated / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_run / relative, destination)
        if sha256_file(destination) != expected:
            raise ValueError("Source changed while copying")
    records = []
    for slide in slides:
        scene = json.loads((isolated / f"planning/html_visual/scene-{slide}.json").read_text(encoding="utf-8"))
        binding_path = isolated / f"planning/html_visual/binding-{slide}.json"
        binding = json.loads(binding_path.read_text(encoding="utf-8")) if binding_path.exists() else None
        calls = []

        def capture_only(**kwargs):
            calls.append({"user_bytes": len(kwargs["user_prompt"].encode("utf-8")),
                          "request_timeout_seconds": kwargs["request_timeout"]})
            return {"action": "stop", "message": "Diagnostic capture only; no real model called"}

        deps = HtmlReviewDependencies(ROOT, capture_only)
        started = time.perf_counter()
        strict = review_scene(scene, run_dir=isolated, deps=deps)
        diagnostic = review_scene(scene, run_dir=isolated, deps=deps, diagnostic=True)
        write_json_atomic(output / slide / "strict-review.json", strict)
        write_json_atomic(output / slide / "diagnostic.json", diagnostic)
        error = None
        if not strict.get("passed"):
            try:
                repair_candidate(scene, binding, run_dir=isolated, deps=deps, max_rounds=1, prompt_mode="runtime_skill")
            except Exception as exc:
                error = {"code": getattr(exc, "code", type(exc).__name__), "message": str(exc)}
        temporal = {"status": "not_run"}
        if temporal_mode:
            if not strict.get("passed"):
                temporal = {"status": "blocked", "reason": "static_review_failed"}
            else:
                from html_scene_repair import evidence
                try:
                    from html_visual_store import load_scene_with_revision
                    revision = load_scene_with_revision(isolated, slide)["revision"]
                    report = evidence(isolated, slide, {"expected_revision": revision,
                        "sampling_mode": temporal_mode, "fps": 30, "step_ms": 250,
                        "overlap_policy": "registered"})
                    write_json_atomic(output / slide / "temporal-review.json", report)
                    temporal = {"status": "passed" if report.get("passed") else "failed",
                                "clock": report.get("clock"), "frame_count": report.get("frame_count"),
                                "coverage": report.get("coverage"), "issue_count": len(report.get("issues", [])),
                                "evidence_dir": report.get("evidence_dir")}
                except Exception as exc:
                    temporal = {"status": "blocked", "code": getattr(exc, "code", type(exc).__name__),
                                "message": str(exc)}
        records.append({"slide_id": slide, "strict_passed": bool(strict.get("passed")),
                        "capacity_issues": diagnostic.get("capacityIssues", []), "error": error,
                        "captured_requests": calls, "elapsed_seconds": round(time.perf_counter() - started, 3),
                        "provider_calls": 0, "model": None, "usage": None, "cost": None,
                        "temporal": temporal,
                        "real_model_acceptance": "not_run", "human_visual_acceptance": "pending_review"})
        write_json_atomic(output / "progress.json", {"cases": records})
    unchanged = all((source_run / p).is_file() and sha256_file(source_run / p) == digest for p, digest in files.items())
    result = {"mode": "local_course_diagnostic", "source_unchanged": unchanged,
              "code_unchanged": source["working_tree_sha256"] == source_identity()["working_tree_sha256"],
              "input_sha256": sha256_json(files), "cases": records,
              "boundary": "Real local content, isolated original browser diagnostics; no model decisions, author saves, approvals or original Token incident reproduction."}
    write_json_atomic(output / "summary.json", result)
    return result


def run_baseline(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Use a new output directory; previous evidence must not be overwritten")
    output.mkdir(parents=True)
    specification = json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))
    source = source_identity()
    write_json_atomic(output / "source-manifest.json", source)
    write_json_atomic(output / "frozen-cases.json", specification)
    records = []
    for case in specification["cases"]:
        run = output / case["id"]
        run.mkdir()
        path = FIXTURES / case["scene"]
        if sha256_file(path) != case["scene_sha256"]:
            raise ValueError("Frozen fixture hash mismatch: " + case["id"])
        scene = json.loads(path.read_text(encoding="utf-8"))
        write_json_atomic(run / "input-scene.json", scene)
        write_json_atomic(run / "planning/visual_contract.json", {
            "slides": [{"slide_id": scene["id"], "narration_beats": case.get("narration_beats", [])}]})
        binding = case.get("binding")
        calls = []

        def offline_decision(**kwargs):
            payload = json.loads(kwargs["user_prompt"])
            calls.append({"user_bytes": len(kwargs["user_prompt"].encode("utf-8")),
                          "system_bytes": len(kwargs["system_prompt"].encode("utf-8")),
                          "screenshot_sha256": [sha256_file(Path(p)) for p in kwargs["image_paths"]],
                          "request_timeout_seconds": kwargs["request_timeout"],
                          "issues": payload["diagnostic"].get("capacityIssues", [])})
            # Explicit fixture oracle, never represented as autonomous AI output.
            return {"action": "patch", "operations": copy.deepcopy(case["offline_operations"])}

        deps = HtmlReviewDependencies(ROOT, offline_decision)
        started = time.perf_counter()
        initial = review_scene(scene, run_dir=run, deps=deps)
        write_json_atomic(run / "initial-review.json", initial)
        diagnosis = review_scene(scene, run_dir=run, deps=deps, diagnostic=True)
        write_json_atomic(run / "initial-diagnostic.json", diagnosis)
        initial_shot = run / diagnosis.get("screenshot", "missing")
        if initial_shot.is_file():
            shutil.copyfile(initial_shot, run / "initial.png")
        error = None
        result = None
        try:
            result = repair_candidate(scene, binding, run_dir=run, deps=deps,
                                      max_rounds=specification["max_rounds"], prompt_mode="runtime_skill")
            write_json_atomic(run / "offline-result.json", result)
            final_shot = run / result["report"].get("screenshot", "missing")
            if final_shot.is_file():
                shutil.copyfile(final_shot, run / "offline-final.png")
        except Exception as exc:
            error = {"code": getattr(exc, "code", type(exc).__name__), "message": str(exc)}
        preserved = bool(result and semantic_state(result["scene"]) == semantic_state(scene)
                         and result["binding"] == binding)
        record = {"id": case["id"], "input_sha256": case["scene_sha256"],
                  "initial_passed": bool(initial.get("passed")),
                  "initial_expectation_met": bool(initial.get("passed")) == case["expected_initial_pass"],
                  "capacity_issues": diagnosis.get("capacityIssues", []),
                  "offline_engineering_passed": bool(result and result["report"].get("passed")),
                  "semantic_motion_preserved": preserved, "offline_decisions": calls,
                  "elapsed_seconds": round(time.perf_counter() - started, 3), "error": error,
                  "provider_calls": 0, "model": None, "usage": None, "cost": None,
                  "real_model_acceptance": "not_run", "human_visual_acceptance": "pending_review"}
        records.append(record)
        write_json_atomic(output / "progress.json", {"cases": records})
    current_source = source_identity()
    unchanged = source["working_tree_sha256"] == current_source["working_tree_sha256"]
    summary = {"format": "hps.capacity.baseline_result", "version": "0.1.0", "mode": "offline_replay",
               "source_sha256": source["working_tree_sha256"], "source_unchanged": unchanged,
               "cases": records, "passed": unchanged and all(c["initial_expectation_met"] and
                   c["offline_engineering_passed"] and c["semantic_motion_preserved"] for c in records),
               "boundary": "Synthetic versioned fixtures plus explicit oracle decisions; real browser checks, no autonomous model result or original Token incident reproduction."}
    write_json_atomic(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, help="Freeze a real local course instead of synthetic fixtures")
    parser.add_argument("--slides", nargs="+", help="One to five source slide IDs")
    parser.add_argument("--temporal", choices=("sampled", "output_frames"), help="Original temporal checker; output_frames uses 30fps")
    args = parser.parse_args()
    if args.source_run:
        result = run_course_baseline(args.source_run, args.output, args.slides, args.temporal)
        success = result["source_unchanged"] and result["code_unchanged"]
    else:
        if args.slides or args.temporal:
            parser.error("--slides/--temporal requires --source-run")
        result = run_baseline(args.output)
        success = result["passed"]
    print(json.dumps({"completed": success, "cases": len(result["cases"]),
                      "mode": result["mode"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
