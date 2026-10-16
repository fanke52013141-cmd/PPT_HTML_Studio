"""Isolated system planning and design-understanding replay from original content.

No image generation, author save or acceptance; never modifies the source run.
"""
from __future__ import annotations

import argparse
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--design-folder", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    out, source, design = args.out.resolve(), args.source_run.resolve(), args.design_folder.resolve()
    if not args.live:
        print(json.dumps({"mode": "dry_run", "planning_max_rounds": 2, "understanding_max_calls": 1,
                          "planning_timeout": 1800, "understanding_timeout": 600, "new_images": 0, "author_writes": 0}))
        return 0
    if out.exists():
        raise ValueError("OUTPUT_MUST_BE_NEW")
    os.environ["PPT_STUDIO_DB_PATH"] = str(out / "isolated.db")
    os.environ["PPT_STUDIO_RUNS_DIR"] = str(out / "isolated-runs")
    from artifact_fingerprint import sha256_file, sha256_json
    candidate = read(design / "candidate.json")
    if sha256_file(design / "design-reference.png") != candidate["image_sha256"]:
        raise ValueError("ORIGINAL_IMAGE_MISMATCH")
    contract = next(s for s in read(source / "planning/visual_contract.json")["slides"] if s["slide_id"] == candidate["slide_id"])
    out.mkdir(parents=True)
    run = out / "isolated-run"
    (run / "planning").mkdir(parents=True)
    shutil.copy2(source / "planning/project_model_binding.json", run / "planning/project_model_binding.json")
    shutil.copy2(design / "design-reference.png", run / "reference.png")
    db = sqlite3.connect((ROOT / "data/projects.db").as_uri() + "?mode=ro", uri=True)
    settings = dict(db.execute("select key,value from settings where key in ('html_visual_connection_id','html_planning_connection_id')"))
    db.close()
    from credential_store import CredentialDependencies, configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies, configure_model_connection_dependencies
    def readonly(*_):
        raise ValueError("Read-only evaluation configuration")
    configure_credential_dependencies(CredentialDependencies(read_store=lambda: read(ROOT / "data/credentials.json"), write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(read_registry=lambda: read(ROOT / "data/model_connections.json"), write_registry=readonly))
    from types import SimpleNamespace
    from project_model_binding_service import freeze_project_models
    from pipeline_lifecycle import write_json_atomic as write
    from html_visual_review_service import generate_scene_plan, HtmlReviewDependencies, HtmlReviewError
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    from html_design_agent import understand_design
    from html_design_candidates import definition_identity
    import json_llm_service as llm

    project = SimpleNamespace(run_dir=str(run), account_id="default", creation_config_package_id=None)
    models = freeze_project_models(project, required=("text", "planning"), setting=settings.get)
    write(out / "models.json", {"planning": models.planning.summary(), "understanding": models.text.summary()})
    identity = definition_identity(ROOT)
    write(out / "source.json", {"contract": contract, "contract_sha256": sha256_json(contract),
        "design_sha256": candidate["image_sha256"], "definitions_sha256": identity,
        "source_run": str(source), "profile": "labeled-plan-diagnostic/0.1.0"})
    calls, http = [], []
    factory = llm.get_openai_client
    def client_factory(**kwargs):
        client = factory(**kwargs)
        create = client.chat.completions.create
        def capture(**request):
            if len(http) >= 6:
                raise RuntimeError("HTTP_BUDGET_EXHAUSTED")
            record = {"model": request["model"], "stream": request.get("stream"),
                      "max_tokens": request.get("max_tokens"), "reasoning_effort": request.get("reasoning_effort"),
                      "temperature": request.get("temperature"), "state": "intent"}
            http.append(record);write(out / "http.json", http)
            try:
                response = create(**request)
                record["state"] = "stream_opened" if request.get("stream") else "returned"
                return response
            except Exception as error:
                record.update(state="unknown", error_type=type(error).__name__)
                raise
            finally:
                write(out / "http.json", http)
        client.chat.completions.create = capture
        return client
    llm.get_openai_client = client_factory
    def generator(model):
        def invoke(**kwargs):
            if definition_identity(ROOT) != identity:
                raise ValueError("DEFINITIONS_CHANGED")
            record = {"stage": "planning" if model is models.planning else "understanding", "state": "intent",
                      "request_timeout_seconds": kwargs["request_timeout"]}
            calls.append(record);write(out / "calls.json", calls)
            started = time.monotonic()
            try:
                value = llm.generate_json_with_configured_llm(**{**kwargs, "model_binding": model, "stream_output": True})
                record["state"] = "returned"
                if definition_identity(ROOT) != identity:
                    raise ValueError("DEFINITIONS_CHANGED")
                return value
            except Exception as error:
                record.update(state="unknown", error_type=type(error).__name__)
                raise
            finally:
                record["elapsed_seconds"] = round(time.monotonic() - started, 3);write(out / "calls.json", calls)
        return invoke

    result = {"profile": "labeled-plan-diagnostic/0.1.0", "new_images": 0, "author_writes": 0,
              "human_approval": False, "full_production_revalidated": False}
    events = []
    try:
        plan = generate_scene_plan(contract, run_dir=run, repo_root=ROOT, json_generator=generator(models.planning), plan_version="0.2.0")
        write(out / "plan.json", plan)
        scene, binding = compile_plan(plan, contract, load_template_catalog(ROOT))
        write(out / "compiled.json", {"scene": scene, "binding": binding})
        result.update(template=plan["templateRef"], layout=plan["layoutRef"],
            code_marker_objects=[o["id"] for o in plan["objects"] if o["slot"].startswith("marker-")],
            code_relation_objects=[o["id"] for o in plan["objects"] if o["slot"].startswith("relation-")])
        try:
            result["understanding"] = understand_design(scene, run / "reference.png", run_dir=run,
                deps=HtmlReviewDependencies(ROOT, generator(models.text)),
                asset_modes={n["id"]: "generate" for n in scene["nodes"] if n["type"] == "image"}, progress=events.append)
        except HtmlReviewError as error:
            if error.code != "DESIGN_ALLOCATION_UNSUPPORTED":
                raise
            result["understanding"] = read(next((run / "planning/html_visual/candidates").glob("*/design-understanding/*/result.json")))
        result["state"] = "returned"
    except Exception as error:
        result.update(state="stopped", error_code=getattr(error, "code", type(error).__name__))
    result.update(calls=calls, http_attempts=len(http), events=events)
    write(out / "summary.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "understanding"}, ensure_ascii=False))
    return 0 if result["state"] == "returned" else 1


if __name__ == "__main__":
    raise SystemExit(main())
