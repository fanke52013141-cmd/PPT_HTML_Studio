"""Fixed input AB/BA candidate-repair experiment; provider is injected, no server import."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import time

from html_build_snapshot import digest, fresh_hash, json_bytes, safe_file
from html_candidate_agent import repair_candidate
from html_runtime_skills import load_runtime_skill
from html_visual_review_service import HtmlReviewDependencies
from pipeline_lifecycle import write_json_atomic


def fixed_cases(root):
    """Three distinct registered templates; only fixture input construction, no model output edits."""
    cases = []
    for name, node_id, part in (
        ("condensation", "headline", "text"),
        ("water-facts", "stat-1", "text"),
        ("evaporation-process", "header", "title"),
    ):
        scene = json.loads(
            (Path(root) / f"html_engine/visual/scenes/{name}.json").read_text(
                encoding="utf-8"
            )
        )
        scene["version"] = "0.5.0"
        scene["themeRef"] = {"id": "neutral-baseline", "version": "0.2.0"}
        node = next(n for n in scene["nodes"] if n["id"] == node_id)
        node["presentation"] = {"typography": {part: {"fontSizePx": 80}}}
        if part == "title":
            node["title"] = "观察条件变化，理解现象与结果之间的关系"
        cases.append({"id": name, "scene": scene, "binding": None, "manual": None})
    return cases


def evaluate_pairs(
    root, output_dir, generator, *, model_identity, max_rounds=2, cases=None
):
    """Both arms use the same generator/config/budget, immutable initial candidates and images.

    Metrics reported here count adapter invocations, not necessarily HTTP attempts.
    The real provider harness adds actual HTTP counts and usage independently.
    """
    root, output = Path(root).resolve(), Path(output_dir).resolve()
    if output.exists():
        raise ValueError("EVALUATION_DIRECTORY_EXISTS: use a new experiment directory")
    if type(max_rounds) is not int or not 1 <= max_rounds <= 3:
        raise ValueError("EVALUATION_BUDGET_INVALID")
    if set(model_identity) - {"provider", "model", "config_digest"}:
        raise ValueError("EVALUATION_MODEL_IDENTITY_INVALID")
    cases = copy.deepcopy(cases if cases is not None else fixed_cases(root))
    output.mkdir(parents=True)
    selection = load_runtime_skill(root, mode="runtime_skill")
    source_files = [
        "html_candidate_agent.py",
        "html_runtime_skills.py",
        "html_skill_evaluation.py",
        "html_scene_editing.py",
        "html_scene_repair.py",
        "html_visual_review_service.py",
        "html_engine/visual/preview/player.js",
        "html_engine/tools/review-scene.cjs",
        "html_engine/tools/browser-runtime.cjs",
        "html_repair_models.py",
        "json_llm_service.py",
    ]
    closure = [
        {"path": p, "sha256": fresh_hash(root / p)} for p in source_files
    ] + selection.files
    case_source = {
        "cases": cases,
        "budget": max_rounds,
        "model_identity": model_identity,
        "closure": closure,
    }
    experiment = {
        "format": "hps.html.runtime_skill_evaluation",
        "version": "0.1.0",
        "experiment_id": digest(json_bytes(case_source)),
        "model_identity": model_identity,
        "max_decisions_per_arm": max_rounds,
        "closure": closure,
        "case_input_sha256": digest(json_bytes(cases)),
        "arms": [],
        "real_model": "not_tested",
        "visual": "pending_review",
        "export": "not_tested",
    }
    write_json_atomic(output / "input.json", case_source)
    # Preserve the actual implementation; hashes alone cannot reconstruct an uncommitted experiment.
    for record in closure:
        destination = safe_file(output, "source/" + record["path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(safe_file(root, record["path"]), destination)
        if fresh_hash(destination) != record["sha256"]:
            raise ValueError("EVALUATION_SOURCE_CHANGED_DURING_CAPTURE")

    def verify():
        for record in closure:
            if fresh_hash(safe_file(root, record["path"])) != record["sha256"]:
                raise ValueError("EVALUATION_SOURCE_CHANGED")

    try:
        for index, case in enumerate(cases):
            first_inputs = []
            for mode in (
                ["legacy_prompt", "runtime_skill"]
                if index % 2 == 0
                else ["runtime_skill", "legacy_prompt"]
            ):
                verify()
                run = output / case["id"] / mode
                run.mkdir(parents=True)
                write_json_atomic(
                    run / "planning/visual_contract.json",
                    {
                        "slides": [
                            {"slide_id": case["scene"]["id"], "narration_beats": []}
                        ]
                    },
                )
                requests = []

                def model(**kwargs):
                    # Exact shared runtime payload/signature; never drop images for one arm.
                    request = {
                        "system_sha256": digest(kwargs["system_prompt"].encode()),
                        "user_sha256": digest(kwargs["user_prompt"].encode()),
                        "images": [fresh_hash(Path(p)) for p in kwargs["image_paths"]],
                    }
                    requests.append(request)
                    return generator(**kwargs)

                start = time.monotonic()
                result, error = None, None
                try:
                    result = repair_candidate(
                        case["scene"],
                        case.get("binding"),
                        run_dir=run,
                        deps=HtmlReviewDependencies(root, model),
                        manual=case.get("manual"),
                        checkpoint=verify,
                        max_rounds=max_rounds,
                        prompt_mode=mode,
                    )
                except Exception as exc:
                    # Do not serialize provider exceptions/credentials. Preserve failed arm, never reroll.
                    error = {
                        "type": type(exc).__name__,
                        "code": getattr(exc, "code", "EXECUTION_FAILED"),
                    }
                verify()
                arm = {
                    "case_id": case["id"],
                    "mode": mode,
                    "input_sha256": digest(json_bytes(case)),
                    "adapter_calls": len(requests),
                    "requests": requests,
                    "engineering_passed": bool(
                        result and result["report"].get("passed")
                    ),
                    "elapsed_seconds": round(time.monotonic() - start, 3),
                    "manual_scene_edits": 0,
                    "manual_intervention_required": not bool(result),
                    "cost": None,
                    "error": error,
                    "audit": result["summary"]["audit"] if result else None,
                    "runtime_skill": load_runtime_skill(root, mode=mode).identity,
                }
                if result:
                    write_json_atomic(run / "repaired-scene.json", result["scene"])
                    shot = run / result["report"].get("screenshot", "missing")
                    if shot.is_file():
                        shutil.copyfile(shot, run / "final.png")
                if requests:
                    first_inputs.append(
                        {
                            "user_sha256": requests[0]["user_sha256"],
                            "images": requests[0]["images"],
                        }
                    )
                experiment["arms"].append(arm)
                write_json_atomic(output / "results.json", experiment)
            experiment.setdefault("comparability", []).append(
                {
                    "case_id": case["id"],
                    "same_first_model_input": len(first_inputs) == 2
                    and first_inputs[0] == first_inputs[1],
                }
            )
        for mode in ("legacy_prompt", "runtime_skill"):
            rows = [r for r in experiment["arms"] if r["mode"] == mode]
            experiment.setdefault("metrics", {})[mode] = {
                "cases": len(rows),
                "engineering_passed": sum(r["engineering_passed"] for r in rows),
                "adapter_calls": sum(r["adapter_calls"] for r in rows),
                "manual_intervention_required": sum(
                    r["manual_intervention_required"] for r in rows
                ),
                "elapsed_seconds": round(sum(r["elapsed_seconds"] for r in rows), 3),
                "cost": None,
            }
        experiment["status"] = "completed"
        return experiment
    except Exception:
        experiment["status"] = "invalidated"
        raise
    finally:
        write_json_atomic(output / "results.json", experiment)
