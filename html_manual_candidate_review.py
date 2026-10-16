"""Audited human review of an unsaved HTML candidate after an unknown model outcome.

This does not reconcile, retry, or mark the original production task successful.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

from artifact_fingerprint import sha256_file, sha256_json
from html_build_snapshot import safe_file
from html_task_store import task_view
from html_visual_store import _read_revision
from pipeline_lifecycle import project_artifact_lock, write_json_atomic


class ManualCandidateError(ValueError):
    def __init__(self, code: str, status_code: int = 409):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _stage_json(run: Path, task: dict, stage: str):
    record = task["stages"].get(stage)
    if not record or record.get("state") != "returned" or record.get("kind") != "json":
        raise ManualCandidateError("CANDIDATE_STAGE_NOT_RETURNED")
    path = safe_file(run, record["file"].replace("\\", "/"))
    if not path.is_file() or sha256_file(path) != record["sha256"]:
        raise ManualCandidateError("CANDIDATE_STAGE_CHANGED")
    return _json(path)


def inspect_candidate(job, run_dir: str | Path, slide_id: str, repo_root: str | Path):
    """Bind one preview to the original failed task and its returned stages."""
    run = Path(run_dir)
    view = task_view(job, run)
    if (job.job_type != "html_plan_generate" or view["slide_id"] != slide_id
            or job.status not in {"failed", "interrupted"} or view.get("input_state") != "current"):
        raise ManualCandidateError("CANDIDATE_TASK_NOT_CURRENT")
    unknown = [(key, value) for key, value in view["stages"].items()
               if value.get("state") in {"intent", "unknown"} and value.get("kind") == "json"
               and value.get("lookup_supported") is False]
    unresolved = [value for value in view["stages"].values() if value.get("state") in {"intent", "unknown"}]
    if len(unknown) != 1 or len(unresolved) != 1 or not view["recovery"]["requires_verification"]:
        raise ManualCandidateError("CANDIDATE_OUTCOME_NOT_UNKNOWN")
    if view["source_revision"] != _read_revision(run)["revision"]:
        raise ManualCandidateError("CANDIDATE_REVISION_CHANGED")
    compile_record = _stage_json(run, view, "phase:compile")
    understanding = _stage_json(run, view, "phase:design_understanding")
    if compile_record["scene"]["id"] != slide_id:
        raise ManualCandidateError("CANDIDATE_SCENE_MISMATCH")
    asset_stages = [key for key in view["stages"] if key.startswith("phase:asset:")]
    assets = [_stage_json(run, view, key) for key in asset_stages]
    for asset in assets:
        path = safe_file(run, asset["file"].replace("\\", "/"))
        if not path.is_file() or sha256_file(path) != asset["sha256"]:
            raise ManualCandidateError("CANDIDATE_ASSET_CHANGED")

    base = safe_file(run, f"planning/html_visual/candidates/{slide_id}")
    matching = []
    for folder in (base / "layout-agent").glob("*"):
        summary_path = folder / "result.json"
        summary = _json(summary_path) if summary_path.is_file() else None
        index = len(summary.get("rounds", [])) if summary else 1
        if summary and (summary.get("passed") is not True or not 0 <= index <= 3):
            continue
        initial, final, strict = folder / "0/scene.json", folder / f"{index}/scene.json", folder / f"{index}/strict-review.json"
        if not all(p.is_file() for p in (initial, final, strict)):
            continue
        if _json(initial) != compile_record["scene"]:
            continue
        candidate, report = _json(final), _json(strict)
        review_hash = hashlib.sha256(json.dumps(candidate, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        if report.get("passed") is True and report.get("scene_sha256") == review_hash:
            matching.append((folder, candidate, report))
    if len(matching) != 1:
        raise ManualCandidateError("CANDIDATE_LAYOUT_AMBIGUOUS")
    layout_folder, layout_scene, layout_report = matching[0]

    from html_design_reconstruction import PROMPT_VERSION
    from html_runtime_skills import load_runtime_skill
    from html_scene_editing import edit_path
    if edit_path(run, slide_id).exists():
        raise ManualCandidateError("CANDIDATE_MANUAL_EDIT_PRESENT")
    skill = load_runtime_skill(Path(repo_root), stage="design_reconstruction", mode="runtime_skill")
    options = _json(safe_file(run, f"planning/html_visual/builds/{view['snapshot_id']}/input/options.json"))
    design_key = options.get("design_candidate_key")
    if not design_key:
        raise ManualCandidateError("CANDIDATE_DESIGN_MISSING")
    design_dir = safe_file(run, f"planning/html_visual/candidates/{slide_id}/designs/{design_key}")
    design_record = _json(design_dir / "candidate.json")
    design_image = design_dir / "design-reference.png"
    if sha256_json(design_record) != design_key or sha256_file(design_image) != design_record["image_sha256"]:
        raise ManualCandidateError("CANDIDATE_DESIGN_CHANGED")
    if understanding["design_sha256"] != design_record["image_sha256"]:
        raise ManualCandidateError("CANDIDATE_UNDERSTANDING_MISMATCH")
    identity = sha256_json({"scene": layout_scene, "binding": compile_record["binding"],
                            "design": sha256_file(design_image), "manual": None,
                            "prompt": PROMPT_VERSION, "runtime_skill": skill.identity,
                            "understanding": understanding})
    audit = base / "design-reconstruction" / identity
    record = _json(audit / "allocation-applied.json")
    preview = audit / "0/current.png"
    if record.get("source") != "validated_model_understanding" or not preview.is_file():
        raise ManualCandidateError("CANDIDATE_PREVIEW_MISSING")
    # Apply the returned, validated design allocation again using the same
    # registered editor; the audit file alone is never an author source.
    # Resources are supplied explicitly in the returned image stage.
    from html_design_agent import apply_allocations
    from html_scene_editing import resources as current_resources
    resource_path = run / "planning/html_visual/resources.json"
    beats = _json(safe_file(run, f"planning/html_visual/builds/{view['snapshot_id']}/input/contract.json"))["narration_beats"]
    from html_visual_review_service import HtmlReviewDependencies, review_scene, REVIEW_DIR
    from html_visual_store import _atomic_write_bytes
    review_paths = [run / REVIEW_DIR / f"review-{slide_id}.png",
                    run / REVIEW_DIR / f"report-{slide_id}.json"]
    with project_artifact_lock(run):
        before = resource_path.read_bytes() if resource_path.is_file() else None
        before_review = {path: path.read_bytes() if path.is_file() else None for path in review_paths}
        try:
            resource_doc = _json(resource_path) if resource_path.is_file() else {"assets": []}
            existing = {asset["id"]: asset for asset in resource_doc.get("assets", [])}
            for asset in assets:
                if asset["id"] in existing and existing[asset["id"]] != asset:
                    raise ManualCandidateError("CANDIDATE_ASSET_CONFLICT")
                existing[asset["id"]] = asset
            resource_doc["assets"] = list(existing.values())
            write_json_atomic(resource_path, resource_doc)
            candidate, operations = apply_allocations(layout_scene, compile_record["binding"], understanding,
                run_dir=run, manual=None, beats=beats)
            if candidate != record["scene"] or operations != record["operations"]:
                raise ManualCandidateError("CANDIDATE_ALLOCATION_CHANGED")
            capacity_path = audit / "allocation-capacity-repair.json"
            if capacity_path.is_file():
                from html_scene_repair import candidate_from_document
                capacity = _json(capacity_path)
                rounds = capacity.get("summary", {}).get("rounds", [])
                if capacity.get("report", {}).get("passed") is not True or len(rounds) > 3:
                    raise ManualCandidateError("CANDIDATE_CAPACITY_REPAIR_INVALID")
                for turn in rounds:
                    response = turn.get("response", {})
                    if response.get("action") != "patch" or not isinstance(response.get("operations"), list):
                        raise ManualCandidateError("CANDIDATE_CAPACITY_REPAIR_INVALID")
                    if any(op.get("kind") not in {"set_presentation", "set_text_style"} for op in response["operations"]):
                        raise ManualCandidateError("CANDIDATE_CAPACITY_REPAIR_INVALID")
                    document = {"scene": candidate, "binding": compile_record["binding"], "manual": None,
                                "resources": current_resources(run), "beats": beats}
                    candidate = candidate_from_document(run, slide_id, {"expected_revision": 0,
                        "source": "ai", "operations": response["operations"]}, document)["scene"]
                if candidate != capacity.get("scene") or capacity.get("binding") != compile_record["binding"]:
                    raise ManualCandidateError("CANDIDATE_CAPACITY_REPAIR_CHANGED")
            report = review_scene(candidate, run_dir=run,
                deps=HtmlReviewDependencies(repo_root=Path(repo_root), json_generator=lambda **_kwargs: {}),
                diagnostic=True)
            rendered = safe_file(run, report["screenshot"].replace("\\", "/"))
            if sha256_file(rendered) != sha256_file(preview):
                raise ManualCandidateError("CANDIDATE_PREVIEW_CHANGED")
        finally:
            if before is None:
                resource_path.unlink(missing_ok=True)
            else:
                _atomic_write_bytes(resource_path, before)
            for path, payload in before_review.items():
                if payload is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write_bytes(path, payload)
    key = sha256_json({"job": job.id, "snapshot": view["snapshot_id"],
                       "unknown_stage": unknown[0][0], "scene": sha256_json(candidate),
                       "design": sha256_file(design_image), "preview": sha256_file(preview),
                       "assets": [(a["id"], a["sha256"]) for a in assets]})
    decision_path = base / "manual-reviews" / f"{key}.json"
    decision = _json(decision_path) if decision_path.is_file() else None
    return {"key": key, "job_id": job.id, "slide_id": slide_id,
            "source_revision": view["source_revision"], "scene_sha256": sha256_json(candidate),
            "design_sha256": sha256_file(design_image), "preview_sha256": sha256_file(preview),
            "design_candidate_key": design_key, "layout_review": layout_report,
            "engineering": "passed" if report.get("passed") else "failed",
            "engineering_issues": report.get("capacityIssues") or [],
            "model_fidelity": "unknown", "decision": decision,
            "_scene": candidate, "_binding": compile_record["binding"], "_plan": _stage_json(run, view, "phase:plan"),
            "_assets": assets, "_preview": preview, "_design": design_image,
            "_decision_path": decision_path, "_layout_audit": layout_folder}


def public_candidate(packet: dict):
    return {key: value for key, value in packet.items() if not key.startswith("_")}


def decide_candidate(job, run_dir, slide_id, repo_root, *, key: str, decision: str, note: str,
                     actor_id: str | None = None):
    if decision not in ("accept", "reject") or not isinstance(note, str) or len(note.strip()) < 8:
        raise ManualCandidateError("CANDIDATE_DECISION_INVALID", 400)
    with project_artifact_lock(Path(run_dir)):
        packet = inspect_candidate(job, run_dir, slide_id, repo_root)
        if packet["key"] != key:
            raise ManualCandidateError("CANDIDATE_KEY_CHANGED")
        if packet["decision"]:
            if packet["decision"]["decision"] == decision and packet["decision"]["note"] == note.strip():
                return public_candidate(packet)
            raise ManualCandidateError("CANDIDATE_ALREADY_DECIDED")
        if decision == "accept" and packet["engineering"] != "passed":
            raise ManualCandidateError("CANDIDATE_ENGINEERING_FAILED")
        from datetime import datetime, timezone
        record = {"format": "hps.html.manual_candidate_review", "version": "0.1.0",
                  "key": key, "job_id": job.id, "slide_id": slide_id,
                  "source_revision": packet["source_revision"],
                  "scene_sha256": packet["scene_sha256"],
                  "design_sha256": packet["design_sha256"],
                  "preview_sha256": packet["preview_sha256"],
                  "engineering": packet["engineering"],
                  "decision": decision, "note": note.strip(),
                  "actor_id": actor_id,
                  "model_fidelity": "unknown", "author_saved": False,
                  "decided_at": datetime.now(timezone.utc).isoformat()}
        write_json_atomic(packet["_decision_path"], record)
        packet["decision"] = record
        return public_candidate(packet)
