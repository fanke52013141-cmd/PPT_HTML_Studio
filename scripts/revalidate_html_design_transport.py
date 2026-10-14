"""Revalidate one design after audited subject-size and anchor fixes; no model calls or approvals."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from html_build_snapshot import fresh_hash, safe_file, verify_snapshot
from html_design_candidates import candidate_directory, definition_identity, load_design, save_design
from html_visual_store import _read_revision

BEFORE = "1548918bd06f2049563efb6255984a733fc87e0316330402eb098bb29687133d"
AFTER = "3b34181a1dcdcb19cd4600265f93f09f89caba19c2e089a739d6455355ae7a78"
SCENE_BEFORE = "72321ba16fb41fbcf4d586e84012e06febf1da5b63450d64d294cf4e5084bd35"
SCENE_AFTER = "185a26c4447cf2ca6a5d29076b032df7039b1c9f71ac0e07b3d33725c0ef82f7"


def verify_transport_change(manifest, *, repo, run):
    changed = []
    for entry in manifest["files"]:
        path = entry["path"]
        target = None
        if path.startswith("source/") and path != "source/project-resources.json":
            target = safe_file(repo, path.removeprefix("source/"))
        elif path.startswith("definitions/"):
            target = safe_file(repo, "html_engine/visual/" + path.removeprefix("definitions/"))
        elif path.startswith("references/"):
            target = safe_file(repo, path.removeprefix("references/"))
        elif path.startswith("assets/"):
            relative = path.removeprefix("assets/")
            target = safe_file(run, relative.removeprefix("project/")) if relative.startswith(("project/", "planning/")) else safe_file(repo, relative)
        if target is not None and (not target.is_file() or fresh_hash(target) != entry["sha256"]):
            changed.append((path, entry["sha256"], fresh_hash(target) if target.is_file() else None))
    expected = [
        ("source/html_image_provider.py", BEFORE, AFTER),
        ("source/html_production_service.py", SCENE_BEFORE, SCENE_AFTER),
    ]
    if changed != expected:
        raise ValueError("TRANSPORT_MIGRATION_DEPENDENCIES_CHANGED")


def main():
    import httpx
    from artifact_fingerprint import sha256_json
    from pipeline_lifecycle import project_artifact_lock, write_json_atomic
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8010")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    run = safe_file(repo, "runs/" + args.project)
    with httpx.Client(base_url=args.base, timeout=30) as client:
        response = client.get(f"/api/projects/{args.project}/html-review/tasks/{args.job}")
        response.raise_for_status()
        task = response.json()["task"]
        if task["status"] != "succeeded" or task["stage"] != "design_review" or any(v.get("state") != "returned" for v in task["stages"].values()):
            raise ValueError("MIGRATION_REQUIRES_RETURNED_DESIGN")
        response = client.get(f"/api/projects/{args.project}/model-binding")
        response.raise_for_status()
        summary = response.json()["effective"]
    folder = safe_file(run, "planning/html_visual/builds/" + task["snapshot_id"])
    manifest = verify_snapshot(folder)
    if manifest["snapshot_id"] != task["snapshot_id"] or manifest["kind"] != "generation":
        raise ValueError("MIGRATION_SNAPSHOT_INVALID")
    verify_transport_change(manifest, repo=repo, run=run)
    contract = json.loads((folder / "input/contract.json").read_text(encoding="utf-8"))
    current = json.loads((run / "planning/visual_contract.json").read_text(encoding="utf-8"))
    if next(s for s in current["slides"] if s["slide_id"] == contract["slide_id"]) != contract:
        raise ValueError("MIGRATION_CONTENT_CHANGED")
    key = task["result"]["design"]["key"]
    directory = candidate_directory(run, contract["slide_id"], key)
    record = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
    if sha256_json(record) != key:
        raise ValueError("MIGRATION_DESIGN_INVALID")
    with project_artifact_lock(run):
        revision = _read_revision(run)["revision"]
        record, package, image = load_design(run_dir=run, contract=contract, key=key,
            revision=revision, definitions=record["definitions_sha256"], model_summary=summary)
        # verify_package validates all actual reference bytes before creating a
        # new immutable identity. No older approval is copied.
        package["directory"] = record["reference_package"]
        candidate = {**record["candidate"], "transport_migration": {
            "version": "subject-explicit-pixels-and-anchor/0.2.0", "from_key": key,
            "from_job": task["id"], "from_snapshot": task["snapshot_id"],
            "before": BEFORE, "after": AFTER,
            "scene_before": SCENE_BEFORE, "scene_after": SCENE_AFTER}}
        result = save_design(run_dir=run, contract=contract, revision=revision,
            definitions=definition_identity(repo), model_summary=summary,
            plan=record["plan"], brief=record["brief"], candidate=candidate,
            package=package, design_path=image)
        write_json_atomic(directory.parent.parent / "transport-migration.json", {
            "from_key": key, "to_key": result["design"]["key"],
            "image_sha256": record["image_sha256"], "from_job": task["id"],
            "author_changed": False, "approval_copied": False})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
