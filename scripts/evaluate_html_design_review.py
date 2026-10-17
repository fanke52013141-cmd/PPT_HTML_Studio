"""Replay archived design decisions through the system Agents, without author writes.

This is a diagnostic two-arm replay, not a resumed production task. Fidelity
is evaluated independently even when the new understanding arm stops early.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def report_scene_hash(scene):
    # Static review predates the compact canonical artifact fingerprint.
    return hashlib.sha256(json.dumps(scene, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def freeze_inputs(source_run, design_folder, reconstruction, understanding, out):
    """Verify the original scene and actual image bytes before any model call."""
    from artifact_fingerprint import sha256_file, sha256_json
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    from pipeline_lifecycle import write_json_atomic

    if out.exists():
        raise ValueError("OUTPUT_MUST_BE_NEW: unknown provider outcomes must not be retried")
    candidate = read(design_folder / "candidate.json")
    contracts = read(source_run / "planning/visual_contract.json")
    contract = next(c for c in contracts["slides"] if c["slide_id"] == candidate["slide_id"])
    original, _ = compile_plan(candidate["plan"], contract, load_template_catalog(ROOT))
    old_understanding = read(understanding / "result.json")
    old_fidelity = read(reconstruction / "0/fidelity/result.json")
    final = read(reconstruction / "allocation-capacity-repair.json")["scene"]
    final["nodes"] = json.loads(read(reconstruction / "0/fidelity/request.json")["user_prompt"])["objects"]
    reference, screenshot = design_folder / "design-reference.png", reconstruction / "0/candidate.png"
    if (sha256_json(original) != old_understanding["scene_sha256"]
            or sha256_json(final) != old_fidelity["scene_sha256"]
            or sha256_file(reference) != candidate["image_sha256"]
            or sha256_file(screenshot) != old_fidelity["screenshot_sha256"]):
        raise ValueError("ARCHIVED_EVIDENCE_MISMATCH")
    report = read(reconstruction / "0/strict-review.json")
    if report["scene_sha256"] != report_scene_hash(final):
        raise ValueError("ARCHIVED_REPORT_MISMATCH")
    out.mkdir(parents=True)
    run = out / "isolated-run"
    run.mkdir()
    shutil.copy2(reference, run / "reference.png")
    shutil.copy2(screenshot, run / "candidate.png")
    (run / "planning").mkdir()
    shutil.copy2(source_run / "planning/project_model_binding.json", run / "planning/project_model_binding.json")
    evidence = {"profile": "same-case-design-review/0.1.0", "source_run": str(source_run),
                "slide_id": candidate["slide_id"], "design_sha256": sha256_file(reference),
                "screenshot_sha256": sha256_file(screenshot),
                "understanding_scene_sha256": sha256_json(original), "fidelity_scene_sha256": sha256_json(final),
                "old_understanding": old_understanding, "old_fidelity": old_fidelity,
                "scope": "two independent diagnostic decisions; no resumed task or production acceptance"}
    write_json_atomic(out / "source-evidence.json", evidence)
    write_json_atomic(out / "original-scene.json", original)
    write_json_atomic(out / "candidate-scene.json", final)
    return run, original, final, report, evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", required=True, type=Path)
    parser.add_argument("--design-folder", required=True, type=Path)
    parser.add_argument("--reconstruction", required=True, type=Path)
    parser.add_argument("--understanding", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--reconstruct", action="store_true", help="Run the actual bounded reconstruction pipeline instead of independent review")
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps({"profile": "same-case-design-review/0.1.0", "adapter_decisions": 2,
                          "per_request_timeout_seconds": 600, "new_images": 0, "author_writes": 0}))
        return 0
    out = args.out.resolve()
    if out.exists():
        raise ValueError("OUTPUT_MUST_BE_NEW")
    # Override inherited environment before importing any database consumers.
    os.environ["PPT_STUDIO_DB_PATH"] = str(out / "isolated.db")
    os.environ["PPT_STUDIO_RUNS_DIR"] = str(out / "isolated-runs")
    run, original, final, report, evidence = freeze_inputs(
        args.source_run.resolve(), args.design_folder.resolve(), args.reconstruction.resolve(),
        args.understanding.resolve(), out)
    db = sqlite3.connect((ROOT / "data/projects.db").as_uri() + "?mode=ro", uri=True)
    settings = dict(db.execute("select key,value from settings where key in ('html_visual_connection_id','html_planning_connection_id')"))
    db.close()
    from credential_store import CredentialDependencies, configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies, configure_model_connection_dependencies
    def readonly(*_):
        raise ValueError("Evaluation configuration is read only")
    configure_credential_dependencies(CredentialDependencies(
        read_store=lambda: read(ROOT / "data/credentials.json"), write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(
        read_registry=lambda: read(ROOT / "data/model_connections.json"), write_registry=readonly))
    from types import SimpleNamespace
    from project_model_binding_service import freeze_project_models
    from pipeline_lifecycle import write_json_atomic
    from html_design_agent import understand_design, review_fidelity
    from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
    import json_llm_service as llm

    project = SimpleNamespace(run_dir=str(run), account_id="default", creation_config_package_id=None,
                              creation_config_snapshot_json=None)
    model = freeze_project_models(project, setting=settings.get).text.require_ready()
    write_json_atomic(out / "model.json", model.summary())
    factory = llm.get_openai_client
    calls, decisions = [], []
    def client_factory(**kwargs):
        client = factory(**kwargs)
        create = client.chat.completions.create
        def capture(**request):
            if len(calls) >= (12 if args.reconstruct else 6):
                raise RuntimeError("HTTP_BUDGET_EXHAUSTED")
            item = {"state": "intent", "model": request["model"], "stream": request.get("stream"),
                    "max_tokens": request.get("max_tokens"), "temperature": request.get("temperature"),
                    "reasoning_effort": request.get("reasoning_effort"),
                    "thinking": request.get("extra_body", {}).get("thinking"), "usage": None, "cost": None}
            calls.append(item)
            write_json_atomic(out / "http-attempts.json", calls)
            started = time.monotonic()
            try:
                value = create(**request)
                # For streams this records response opening, not completion.
                item["state"] = "stream_opened" if request.get("stream") else "returned"
                return value
            except Exception as error:
                item.update(state="unknown", error_type=type(error).__name__)
                raise
            finally:
                item["open_elapsed_seconds"] = round(time.monotonic() - started, 3)
                write_json_atomic(out / "http-attempts.json", calls)
        client.chat.completions.create = capture
        return client
    llm.get_openai_client = client_factory

    def generator(**kwargs):
        prefix = kwargs['artifact_prefix']
        stage = ('understanding' if prefix.startswith('design_understanding') else
                 'reconstruction' if prefix.startswith('design-reconstruct') else
                 'layout_repair' if prefix.startswith('layout-agent') else 'fidelity')
        item = {"stage": stage,
                "state": "intent", "request_timeout_seconds": kwargs["request_timeout"],
                "input_bytes": len(kwargs["system_prompt"].encode()) + len(kwargs["user_prompt"].encode()),
                "image_count": len(kwargs.get("image_paths", []))}
        decisions.append(item)
        write_json_atomic(out / "decisions.json", decisions)
        started = time.monotonic()
        try:
            value = llm.generate_json_with_configured_llm(**kwargs, model_binding=model, stream_output=True)
            item["state"] = "returned"
            return value
        except Exception as error:
            item.update(state="unknown", error_type=type(error).__name__)
            raise
        finally:
            item["elapsed_seconds"] = round(time.monotonic() - started, 3)
            write_json_atomic(out / "decisions.json", decisions)

    deps = HtmlReviewDependencies(ROOT, generator)
    events = []
    result = {"profile": evidence["profile"], "author_writes": 0, "new_images": 0,
              "human_approval": False, "full_production_revalidated": False}
    try:
        if args.reconstruct:
            from html_design_reconstruction import reconstruct_design
            from html_production_service import compile_plan
            from html_storyboard_planning import load_template_catalog
            candidate = read(args.design_folder / 'candidate.json')
            contracts = read(args.source_run / 'planning/visual_contract.json')
            contract = next(c for c in contracts['slides'] if c['slide_id'] == candidate['slide_id'])
            shutil.copy2(args.source_run / 'planning/visual_contract.json', run / 'planning/visual_contract.json')
            scene, binding = compile_plan(candidate['plan'], contract, load_template_catalog(ROOT))
            result['scope'] = 'actual bounded system reconstruction; author save and human acceptance excluded'
            result['reconstruction'] = reconstruct_design(scene, binding, run / 'reference.png',
                run_dir=run, deps=deps, beats=contract['narration_beats'], progress=events.append)
            result['state'] = 'returned'
            return_code = 0
            result.update(decisions=decisions, http_attempts=len(calls), events=events)
            write_json_atomic(out / 'summary.json', result)
            print(json.dumps({'state':result['state'], 'decisions':decisions, 'http_attempts':len(calls)},ensure_ascii=False))
            return return_code
        try:
            understood = understand_design(original, run / "reference.png", run_dir=run, deps=deps,
                asset_modes={n["id"]: "generate" for n in original["nodes"] if n["type"] == "image"}, progress=events.append)
            result["understanding"] = understood
        except HtmlReviewError as error:
            if error.code != "DESIGN_ALLOCATION_UNSUPPORTED":
                raise
            path = next((run / "planning/html_visual/candidates").glob("*/design-understanding/*/result.json"))
            result["understanding"] = read(path)
        # Independent diagnostic arm; does not continue production past a stop.
        result["fidelity"] = review_fidelity(final, run / "reference.png", run / "candidate.png", report, None,
            folder=run / "fidelity", run_dir=run, deps=deps)
        result["state"] = "returned"
    except Exception as error:
        result.update(state="stopped", error_code=getattr(error, "code", type(error).__name__))
    result.update(decisions=decisions, http_attempts=len(calls), events=events)
    write_json_atomic(out / "summary.json", result)
    print(json.dumps({"state": result["state"], "decisions": decisions, "http_attempts": len(calls)}, ensure_ascii=False))
    return 0 if result["state"] == "returned" else 1


if __name__ == "__main__":
    raise SystemExit(main())
