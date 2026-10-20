"""One bounded real-model Pi repair trial on a fresh isolated source copy."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True, help="AgentJobRequest JSON; no credentials")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    from html_agent_models import AgentJobRequest
    request = AgentJobRequest.model_validate_json(args.request.read_bytes())
    if not args.live:
        print("Request valid; add --live for one bounded paid model trial. No provider called.")
        return
    source, out = args.source_run.resolve(), args.output.resolve()
    if out.exists() or source == out or source in out.parents or out in source.parents:
        raise ValueError("Fresh output outside source required; existing attempts are never retried")
    from artifact_fingerprint import sha256_file
    excluded = {"builds", "external-handoffs", "editor-history", "repair-evidence", "handoff-diagnostics", "pi-jobs", "__pycache__"}
    files, total = [], 0
    for directory in ("inputs", "planning", "slides"):
        for path in (source / directory).rglob("*"):
            if any(part in excluded for part in path.relative_to(source).parts): continue
            if path.is_symlink(): raise ValueError("Source symlinks not accepted")
            if path.is_file():
                total += path.stat().st_size
                if path.stat().st_size > 128*1024*1024 or total > 1024*1024*1024: raise ValueError("Copy budget exceeded")
                files.append((path, sha256_file(path)))
    out.mkdir(parents=True)
    run = out / "isolated-run"
    for path, hash_value in files:
        destination = run / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        if sha256_file(destination) != hash_value: raise ValueError("Source changed while copying")
    os.environ["PPT_STUDIO_DB_PATH"] = str(out / "jobs.db")
    os.environ["PPT_STUDIO_RUNS_DIR"] = str(out / "runs")
    from credential_store import CredentialDependencies, configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies, configure_model_connection_dependencies
    def read(path): return json.loads(path.read_text(encoding="utf-8"))
    def readonly(*_): raise ValueError("Read only configuration")
    configure_credential_dependencies(CredentialDependencies(read_store=lambda: read(ROOT / "data/credentials.json"), write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(read_registry=lambda: read(ROOT / "data/model_connections.json"), write_registry=readonly))
    with sqlite3.connect((ROOT / "data/projects.db").as_uri() + "?mode=ro", uri=True) as db:
        settings = dict(db.execute("select key,value from settings where key in ('html_visual_connection_id','html_planning_connection_id')"))
    from project_model_binding_service import freeze_project_models
    from database import init_db, SessionLocal
    from html_agent_store import AgentJobStore
    from html_agent_jobs import submit, _work
    from pipeline_lifecycle import write_json_atomic
    project = SimpleNamespace(run_dir=str(run), account_id="default", creation_config_package_id=None, creation_config_snapshot_json=None)
    model = freeze_project_models(project, setting=settings.get).text.require_ready()
    init_db()
    store = AgentJobStore(SessionLocal)
    write_json_atomic(out / "attempt.json", {"state": "intent", "model": model.summary(), "automatic_retry": False,
        "source": str(source), "source_files": len(files), "request": request.model_dump(mode="json")})
    slide = read(run / "planning/visual_contract.json")["slides"]
    scope = set(request.task.scope)
    import html_visual_store as visual
    candidates = []
    for item in slide:
        slide_id = item.get("slide_id") or item.get("id")
        path = visual.scene_path(run, slide_id)
        if path.is_file() and scope <= {node["id"] for node in read(path)["nodes"]}: candidates.append(slide_id)
    if len(candidates) != 1: raise ValueError("Scope must identify exactly one saved slide")
    slide_id = candidates[0]
    job = submit(run, "pi-live-trial", slide_id, request, model, store=store, launch=False)
    _work(store, run, "pi-live-trial", slide_id, request, model, job["job_id"])
    result = store.read("pi-live-trial", slide_id, job["job_id"])
    effective = store.read("pi-live-trial", slide_id, job["job_id"], private=True)["payload"]["model"]
    unchanged = all(sha256_file(path) == value for path, value in files)
    write_json_atomic(out / "result.json", result)
    write_json_atomic(out / "summary.json", {"status": result["status"], "error": result["error"], "usage": result["usage"],
        "source_unchanged": unchanged, "model": model.summary(), "execution": effective,
        "saved": False, "human_approval": "not_requested"})
    print(json.dumps({"status": result["status"], "error": result["error"], "usage": result["usage"], "source_unchanged": unchanged}, ensure_ascii=False))
    if not unchanged: raise ValueError("Source changed during trial")
    if result["status"] != "succeeded": raise SystemExit(1)


if __name__ == "__main__": main()
