"""Reconcile durable responses and author commits; never resubmit a provider call."""
import json
from pathlib import Path

import html_task_store as store
from html_build_snapshot import digest, json_bytes, safe_file, fresh_hash, verify_snapshot
from html_visual_store import _atomic_write_bytes, _read_revision


def receipt_path(run, job_id, name):
    return safe_file(run, f"planning/html_visual/task-stages/{job_id}/{name}.receipt.json")


def write_receipt(path, value):
    envelope = {"value": value, "sha256": digest(json_bytes(value))}
    _atomic_write_bytes(path, json_bytes(envelope))


def read_receipt(path):
    if path.stat().st_size > 64 * 1024 * 1024:
        raise store.HtmlTaskError("RECOVERY_RECEIPT_INVALID", 409)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if digest(json_bytes(envelope["value"])) != envelope["sha256"]:
        raise store.HtmlTaskError("RECOVERY_RECEIPT_INVALID", 409)
    return envelope["value"]


def validate_response(run, record):
    path = safe_file(run, record["file"])
    if not path.is_file() or fresh_hash(path) != record["sha256"]:
        raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID", 409)
    data = path.read_bytes()
    if record["kind"] == "image":
        from ai_provider_service import open_validated_image
        open_validated_image(data)
        return data
    if record["kind"] != "json":
        raise store.HtmlTaskError("RECOVERY_KIND_INVALID", 409)
    result = json.loads(data)
    if not isinstance(result, dict):
        raise store.HtmlTaskError("RECOVERY_RESPONSE_INVALID", 409)
    return result


def reconcile_responses(db, job_id, run, *, lookups=None):
    """Recover returned-but-unregistered output, or query an explicitly capable adapter."""
    job = store._job(db, job_id)
    if job.status not in {"failed", "interrupted"}:
        return 0
    payload = job.get_payload()
    snapshot_id = payload.get("input", {}).get("snapshot_id")
    if not snapshot_id:
        return 0
    snapshot = verify_snapshot(safe_file(run, "planning/html_visual/builds/" + snapshot_id))
    if snapshot["snapshot_id"] != snapshot_id or snapshot["kind"] != "generation":
        raise store.HtmlTaskError("RECOVERY_SNAPSHOT_INVALID", 409)
    count = 0
    for key, record in payload.get("production_stages", {}).items():
        if record.get("state") not in {"intent", "unknown"} or not key.startswith(("json:", "image:")):
            continue
        path = receipt_path(run, job_id, digest(key.encode()))
        if not path.is_file():
            upstream_path = receipt_path(run, job_id, "upstream-" + digest(key.encode()))
            if upstream_path.is_file():
                upstream = read_receipt(upstream_path)
                attached = upstream["record"]
                if (upstream["job_id"] != job_id or upstream["snapshot_id"] != snapshot_id or upstream["key"] != key
                        or attached["attempt"] != record.get("attempt") or attached["request_id"] != record.get("request_id")):
                    raise store.HtmlTaskError("PROVIDER_RESULT_IDENTITY_MISMATCH", 409)
                record.update({"upstream_task_id": attached["upstream_task_id"], "lookup_supported": True})
            lookup = (lookups or {}).get("toapis" if record.get("upstream_task_id") else record["kind"])
            # Only adapters that submitted this identity may query it. No guessed URL.
            if not lookup or not record.get("lookup_supported"):
                continue
            if int(record.get("lookup_attempts", 0)) >= 3:
                continue
            record["lookup_attempts"] = int(record.get("lookup_attempts", 0)) + 1
            store._transition(db, job, ("failed", "interrupted"), {"payload_json": store.json_dumps(payload)})
            response = lookup(record if record.get("upstream_task_id") else record["request_id"])
            if not isinstance(response, dict) or response.get("request_id") != record["request_id"]:
                raise store.HtmlTaskError("PROVIDER_RESULT_IDENTITY_MISMATCH", 409)
            if response.get("state") != "succeeded":
                continue
            data = response["result"] if record["kind"] == "image" else json_bytes(response["result"])
            output = safe_file(run, f"planning/html_visual/task-stages/{job_id}/{digest(data)}.{'png' if record['kind'] == 'image' else 'json'}")
            _atomic_write_bytes(output, data)
            returned = {**record, "state": "returned", "stage": record["kind"] + "_reconciled",
                        "file": output.relative_to(Path(run).resolve()).as_posix(), "sha256": digest(data)}
            validate_response(run, returned)
            write_receipt(path, {"job_id": job_id, "snapshot_id": snapshot_id, "key": key, "record": returned})
        receipt = read_receipt(path)
        returned = receipt["record"]
        if (receipt["job_id"] != job_id or receipt["snapshot_id"] != snapshot_id or receipt["key"] != key
                or returned.get("attempt") != record.get("attempt")
                or returned.get("request_id") != record.get("request_id")
                or returned.get("kind") != record["kind"] or returned.get("state") != "returned"):
            raise store.HtmlTaskError("PROVIDER_RESULT_IDENTITY_MISMATCH", 409)
        validate_response(run, returned)
        payload["production_stages"][key] = returned
        count += 1
    if count:
        store._transition(db, job, ("failed", "interrupted"), {"payload_json": store.json_dumps(payload)})
    return count


def seal_author_commit(db, job_id, attempt, run, snapshot_id, result, paths, *, expected=None):
    """Last operation inside the author transaction; output files precede this seal."""
    job = store._job(db, job_id, attempt)
    if job.status != "running":
        raise store.HtmlTaskError("任务已停止，不能封存作者提交", 409)
    value = {"job_id": job_id, "attempt": attempt, "snapshot_id": snapshot_id,
             "state": "prepared" if expected is not None else "sealed",
             "result": result, "files": []}
    for path in paths:
        relative = Path(path).resolve().relative_to(Path(run).resolve()).as_posix()
        if expected is not None and Path(path) in expected:
            data = expected[Path(path)]
            identity = digest(data) if data is not None else None
        else:
            identity = fresh_hash(safe_file(run, relative)) if Path(path).is_file() else None
        value["files"].append({"path": relative, "sha256": identity})
    write_receipt(receipt_path(run, job_id, f"author-{attempt}"), value)


def reconcile_author_commit(db, job_id, project):
    """Restore terminal state only for an exact, complete, still-current author commit."""
    from pipeline_lifecycle import project_artifact_lock
    from invalidation_service import html_scene_changed
    with project_artifact_lock(project.run_dir):
        job = store._job(db, job_id)
        if job.status not in {"failed", "interrupted", "succeeded"} or job.project_id != project.id:
            return None
        payload = job.get_payload()
        attempt = int(payload.get("attempt", 1))
        path = receipt_path(project.run_dir, job_id, f"author-{attempt}")
        if not path.is_file():
            return None
        receipt = read_receipt(path)
        if (receipt["job_id"] != job_id or receipt["attempt"] != attempt
                or receipt.get("state") not in {"prepared", "sealed"}
                or receipt["snapshot_id"] != payload.get("input", {}).get("snapshot_id")):
            raise store.HtmlTaskError("AUTHOR_COMMIT_IDENTITY_MISMATCH", 409)
        snapshot = verify_snapshot(safe_file(project.run_dir, "planning/html_visual/builds/" + receipt["snapshot_id"]))
        result = receipt["result"]
        slide = snapshot["slide_id"]
        if (snapshot["snapshot_id"] != receipt["snapshot_id"] or snapshot["kind"] != "generation"
                or result.get("scene", {}).get("id") != slide or not result.get("review", {}).get("passed")
                or _read_revision(project.run_dir)["revision"] != result["saved"]["revision"]):
            raise store.HtmlTaskError("AUTHOR_COMMIT_STALE", 409)
        if not receipt["files"]:
            raise store.HtmlTaskError("AUTHOR_COMMIT_INCOMPLETE", 409)
        from html_visual_store import scene_path, revision_path, _document_bytes
        required = {scene_path(project.run_dir, slide).relative_to(Path(project.run_dir)).as_posix(),
                    revision_path(project.run_dir).relative_to(Path(project.run_dir)).as_posix(),
                    f"planning/html_visual/binding-{slide}.json", f"planning/html_visual/plan-{slide}.json",
                    f"planning/html_visual/production-provenance-{slide}.json"}
        if not required.issubset({entry["path"] for entry in receipt["files"]}):
            raise store.HtmlTaskError("AUTHOR_COMMIT_INCOMPLETE", 409)
        if fresh_hash(scene_path(project.run_dir, slide)) != result["saved"]["sha256"] or digest(_document_bytes(result["scene"])) != result["saved"]["sha256"]:
            raise store.HtmlTaskError("AUTHOR_COMMIT_IDENTITY_MISMATCH", 409)
        for entry in receipt["files"]:
            output = safe_file(project.run_dir, entry["path"])
            if (entry["sha256"] is None and output.exists()) or (entry["sha256"] is not None and (not output.is_file() or fresh_hash(output) != entry["sha256"])):
                raise store.HtmlTaskError("AUTHOR_COMMIT_INCOMPLETE", 409)
        if job.status == "succeeded":
            return store._job_to_dict(job)
        if result["saved"]["changed"]:
            html_scene_changed(project, [slide])
        payload["result"] = result
        payload["reconciliation"] = {"kind": "author_commit", "attempt": attempt}
        # Commit invalidation's DB change and task terminal state together.
        return store._transition(db, job, ("failed", "interrupted"), {
            "payload_json": store.json_dumps(payload), "status": "succeeded", "stage": "succeeded",
            "error": None, "finished_at": store.datetime.now(),
        })
