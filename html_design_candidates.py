"""Immutable design checkpoint; accepting a design never approves HTML."""
from __future__ import annotations

import json
from pathlib import Path

from artifact_fingerprint import sha256_json, sha256_file
from pipeline_lifecycle import write_json_atomic, project_artifact_lock
from html_visual_store import validate_slide_id, _read_revision, HtmlVisualConflict, load_scene_with_revision
from html_visual_review_service import HtmlReviewError
from html_reference_package import verify_package


def definition_identity(repo_root):
    repo = Path(repo_root)
    visual = repo / "html_engine/visual"
    paths = [visual / "preview/player.js", visual / "generated/catalog.json", visual / "effects/registry.json",
             repo / "html_engine/tools/catalog-lib.cjs", repo / "html_engine/tools/catalog-assemble.cjs"]
    paths += [repo / name for name in ("html_production_service.py", "html_reference_package.py",
                                      "html_design_candidates.py", "html_image_provider.py", "html_design_brief.py",
                                      "html_candidate_agent.py", "html_scene_repair.py", "html_scene_editing.py",
                                      "html_visual_review_service.py", "html_engine/tools/review-scene.cjs")]
    for folder in ("themes", "layouts", "templates"):
        paths += sorted((visual / folder).glob("*.json"))
    catalog_path = visual / "catalog/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    paths += [repo / entry["path"] for entry in catalog["sourceManifest"]]
    return sha256_json({str(p.relative_to(repo)): sha256_file(p) for p in paths})


def candidate_directory(run_dir, slide_id, key):
    import re
    if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
        raise HtmlReviewError("设计候选标识无效", code="DESIGN_KEY_INVALID")
    return Path(run_dir) / "planning/html_visual/candidates" / validate_slide_id(slide_id) / "designs" / key


def save_design(*, run_dir, contract, revision, definitions, model_summary, plan, brief, candidate, package, design_path):
    record = {
        "format": "hps.html.design_candidate", "version": "0.1.0",
        "slide_id": contract["slide_id"], "revision": revision,
        "contract_sha256": sha256_json(contract), "definitions_sha256": definitions,
        "model_summary": model_summary, "plan": plan, "brief": brief, "candidate": candidate,
        "reference_package": package["directory"],
        "reference_manifest_sha256": package["manifest"]["manifestSha256"],
        "image_sha256": sha256_file(design_path),
        "base_scene_sha256": (load_scene_with_revision(run_dir, contract["slide_id"]) or {}).get("sha256"),
    }
    key = sha256_json(record)
    directory = candidate_directory(run_dir, contract["slide_id"], key)
    with project_artifact_lock(run_dir):
        current = _read_revision(run_dir)["revision"]
        if current != revision:
            raise HtmlVisualConflict(revision, current)
        directory.mkdir(parents=True, exist_ok=True)
        image = directory / "design-reference.png"
        if not image.exists():
            image.write_bytes(Path(design_path).read_bytes())
        if sha256_file(image) != record["image_sha256"]:
            raise HtmlReviewError("设计候选图片已损坏", code="DESIGN_CANDIDATE_INVALID")
        write_json_atomic(directory / "candidate.json", record)
        write_json_atomic(directory.parent.parent / "current-design.json", {"key": key})
    return {"stage": "design_review", "saved": {"changed": False},
            "design": {"key": key, "file": str(image.relative_to(run_dir)),
                       "sha256": record["image_sha256"], "reference_package_key": package["manifest"]["cacheKey"],
                       "approval_status": "not_recorded"},
            "message": "设计参考已生成；请审阅并携带 design_candidate_key 确认后继续，尚未生成素材或替换场景。"}


def _revision_matches(run_dir, record, key, revision):
    scene = load_scene_with_revision(run_dir, record["slide_id"]) or {}
    if record["revision"] == revision and scene.get("sha256") == record["base_scene_sha256"]:
        return True
    receipt = candidate_directory(run_dir, record["slide_id"], key).parent.parent / "design-acceptance.json"
    if not receipt.is_file():
        return False
    accepted = json.loads(receipt.read_text(encoding="utf-8"))
    return (accepted.get("design_candidate_key") == key
            and accepted.get("saved_revision") == revision
            and accepted.get("scene_sha256") == scene.get("sha256")
            and accepted.get("provenance_sha256") == sha256_file(Path(run_dir) / "planning/html_visual" / f"production-provenance-{record['slide_id']}.json"))


def load_design(*, run_dir, contract, key, revision, definitions, model_summary):
    directory = candidate_directory(run_dir, contract["slide_id"], key)
    try:
        record = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
        if (record["format"] != "hps.html.design_candidate" or record["version"] != "0.1.0"
                or sha256_json(record) != key or sha256_file(directory / "design-reference.png") != record["image_sha256"]):
            raise ValueError("hash")
        if (record["slide_id"] != contract["slide_id"] or not _revision_matches(run_dir, record, key, revision)
                or record["contract_sha256"] != sha256_json(contract)
                or record["definitions_sha256"] != definitions or record["model_summary"] != model_summary):
            raise HtmlReviewError("内容、修订、定义或模型已变化，请重新生成设计参考", status_code=409, code="DESIGN_STALE")
        root = Path(run_dir).resolve()
        package_dir = (root / record["reference_package"]).resolve()
        if not package_dir.is_relative_to(root):
            raise ValueError("path")
        package = verify_package(package_dir)
        if package["manifest"]["manifestSha256"] != record["reference_manifest_sha256"]:
            raise ValueError("manifest")
        return record, package, directory / "design-reference.png"
    except HtmlReviewError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HtmlReviewError("设计候选不存在或字节已损坏", code="DESIGN_CANDIDATE_INVALID") from exc


def current_design(*, run_dir, contract, repo_root):
    slide_id = validate_slide_id(contract["slide_id"])
    root = Path(run_dir) / "planning/html_visual/candidates" / slide_id
    pointer = root / "current-design.json"
    if not pointer.exists():
        return {"design": None}
    try:
        key = json.loads(pointer.read_text(encoding="utf-8"))["key"]
        directory = candidate_directory(run_dir, slide_id, key)
        record = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
        if sha256_json(record) != key or sha256_file(directory / "design-reference.png") != record["image_sha256"]:
            raise ValueError("hash")
        package_dir = (Path(run_dir) / record["reference_package"]).resolve()
        if not package_dir.is_relative_to(Path(run_dir).resolve()):
            raise ValueError("path")
        if verify_package(package_dir)["manifest"]["manifestSha256"] != record["reference_manifest_sha256"]:
            raise ValueError("manifest")
        accepted = root / "design-acceptance.json"
        acceptance = json.loads(accepted.read_text(encoding="utf-8")) if accepted.exists() else {}
        state = "accepted_for_reconstruction" if acceptance.get("design_candidate_key") == key else "needs_review"
        stale = (not _revision_matches(run_dir, record, key, _read_revision(run_dir)["revision"])
                 or record["contract_sha256"] != sha256_json(contract)
                 or record["definitions_sha256"] != definition_identity(repo_root))
        return {"design": {"key": key, "status": state, "stale": stale,
                           "sha256": record["image_sha256"]}}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HtmlReviewError("当前设计候选无法验证", code="DESIGN_CANDIDATE_INVALID") from exc
