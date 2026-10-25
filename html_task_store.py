"""Persistent task store for html design/asset tasks (F02).

Own task type + persistence over the shared ``LocalJob`` table — html
tasks never disguise themselves as video jobs (plan: "HTML 设计/资产任务
应有自己的类型/store"). Reuses generation_control's cooperative cancel
checkpoints at the boundaries the caller declares; restart recovery
marks in-flight tasks ``interrupted``; retries are bounded by an attempt
counter carried in the payload; idempotency is the exact
``submission_key`` (an active or succeeded job with the same key is
reused, never duplicated).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

TASK_TYPES = ("html_plan_generate", "html_review", "html_asset_produce", "html_asset_sheet_generate", "html_asset_sheet_assess", "html_asset_sheet_retry", "html_semantic_review", "html_course_produce", "html_reference_review", "html_paired_experiment")
MAX_ATTEMPTS = 3
ACTIVE_STATUSES = ("queued", "running")


class HtmlTaskError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _job_to_dict(job) -> Dict[str, Any]:
    from html_execution_metrics import execution_summary
    payload = job.get_payload()
    return {
        "id": job.id,
        "project_id": job.project_id,
        "type": job.job_type,
        "status": job.status,
        "attempt": int(payload.get("attempt", 1)),
        "submission_key": payload.get("submission_key"),
        "error": job.error,
        "result": payload.get("result"),
        "snapshot_id": payload.get("input", {}).get("snapshot_id"),
        "stages": payload.get("production_stages", {}),
        "execution": execution_summary(payload.get("production_stages", {})),
        "reconciliation": payload.get("reconciliation"),
        "slide_id": payload.get("input", {}).get("slide_id"),
        "stage": job.stage,
        "source_revision": payload.get("input", {}).get("source_revision"),
        "progress": payload.get("progress", {}),
        "recovery": recovery_action(job),
    }


def recovery_action(job):
    """Display advice only; resubmission still enforces all recovery gates."""
    payload = job.get_payload()
    unknown = any(r.get("state") in {"intent", "unknown"}
                  for r in payload.get("production_stages", {}).values())
    output_limit = any(r.get("state") == "output_limit"
                       for r in payload.get("production_stages", {}).values())
    blocked = unknown or "RECONCILIATION_BLOCKED" in (job.error or "")
    resumable = (job.job_type in ("html_plan_generate","html_semantic_review")
                 and job.status in {"failed", "interrupted"}
                 and int(payload.get("attempt", 1)) < MAX_ATTEMPTS
                 and bool(payload.get("input", {}).get("snapshot_id") or (job.job_type=="html_semantic_review" and payload.get("input", {}).get("input_digest")))
                 and not blocked and not output_limit)
    return {"can_resume": resumable, "requires_verification": blocked,
            "reason": "external_outcome_unknown" if blocked else
                      "model_output_limit" if output_limit else
                      "resume_original_request" if resumable else "not_resumable"}


def task_view(job, run_dir, *, verify_dependencies=True):
    import json
    from pathlib import Path
    from artifact_fingerprint import sha256_json
    from html_visual_store import _read_revision

    value = _job_to_dict(job)
    result = value.get("result") or {}
    expected = (result.get("saved") or {}).get("revision", value.get("source_revision"))
    if verify_dependencies and job.job_type == "html_plan_generate" and value.get("snapshot_id"):
        from html_production_stages import ProductionStages
        try:
            verifier = ProductionStages(None, job.id, None, run_dir, value["snapshot_id"], Path(__file__).resolve().parent)
            manifest = verifier.verify_inputs(check_revision=False)
            expected = manifest["source_revision"] if expected is None else expected
            frozen_contract = json.loads((verifier.folder / "input/contract.json").read_text(encoding="utf-8"))
        except (ValueError, OSError, KeyError):
            value["input_state"] = "stale"
            value["recovery"] = {**value["recovery"], "can_resume": False, "reason": "dependencies_changed"}
            return value
    else:
        frozen_contract = None
    current = _read_revision(run_dir)["revision"]
    value["input_state"] = "unknown" if expected is None else "current" if expected == current else "stale"
    if value["input_state"] == "current" and job.job_type == "html_plan_generate":
        identity = job.get_payload().get("input", {}).get("contract_sha256") or (sha256_json(frozen_contract) if frozen_contract else None)
        try:
            slides = json.loads((Path(run_dir) / "planning/visual_contract.json").read_text(encoding="utf-8")).get("slides", [])
            contract = next((s for s in slides if s.get("slide_id") == value["slide_id"]), None)
            value["input_state"] = "unknown" if not identity else "current" if contract and sha256_json(contract) == identity else "stale"
        except (OSError, ValueError, TypeError):
            value["input_state"] = "unknown"
    if value["input_state"]=="current" and job.job_type=="html_semantic_review":
        from html_semantic_review_service import source
        try:
            if source(run_dir,value["slide_id"])["input_digest"]!=job.get_payload()["input"].get("input_digest"):
                value["input_state"]="stale"
        except (ValueError,OSError,KeyError,StopIteration):
            value["input_state"]="stale"
    if value["input_state"] != "current":
        value["recovery"] = {**value["recovery"], "can_resume": False, "reason": "input_changed"}
    return value


def recent_task_summaries(db, project_id: str, *, limit: int = 20, run_dir=None) -> list[Dict[str, Any]]:
    """Return safe, project-scoped task facts for workflow status reads.

    Inputs, result payloads, and idempotency keys stay on the task endpoints;
    the status projection exposes only lifecycle facts needed for recovery.
    """
    from database import LocalJob

    safe_limit = max(1, min(int(limit), 100))
    jobs = (
        db.query(LocalJob)
        .filter(
            LocalJob.project_id == project_id,
            LocalJob.job_type.in_(TASK_TYPES),
        )
        .order_by(LocalJob.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    summaries = []
    for job in jobs:
        value = task_view(job, run_dir, verify_dependencies=False) if run_dir else _job_to_dict(job)
        summaries.append({
            "id": job.id,
            "type": job.job_type,
            "status": job.status,
            "stage": job.stage,
            "attempt": int(job.get_payload().get("attempt", 1)),
            "error": job.error,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "slide_id": job.get_payload().get("input", {}).get("slide_id"),
            "snapshot_id": job.get_payload().get("input", {}).get("snapshot_id"),
            "source_revision": job.get_payload().get("input", {}).get("source_revision"),
            "progress": job.get_payload().get("progress", {}),
            "recovery": value["recovery"],
            "input_state": value.get("input_state", "unknown"),
        })
    return summaries


def current_slide_task(db, project_id, slide_id, run_dir):
    from database import LocalJob
    from sqlalchemy import func
    job = db.query(LocalJob).filter(
        LocalJob.project_id == project_id, LocalJob.job_type == "html_plan_generate",
        func.json_extract(LocalJob.payload_json, "$.input.slide_id") == slide_id,
    ).order_by(LocalJob.created_at.desc(), LocalJob.id.desc()).first()
    return task_view(job, run_dir) if job else None


def submit_task(
    db,
    *,
    project_id: str,
    task_type: str,
    submission_key: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Idempotent submission: reuse an active/succeeded job with the same
    key; a failed job with the same key is retried within the attempt
    budget, otherwise refused with the last error."""
    from database import LocalJob

    if task_type not in TASK_TYPES:
        raise HtmlTaskError(f"未知 HTML 任务类型：{task_type}")
    existing = (
        db.query(LocalJob)
        .filter(
            LocalJob.project_id == project_id,
            LocalJob.job_type == task_type,
        )
        .order_by(LocalJob.created_at.desc())
        .limit(20)
        .all()
    )
    for job in existing:
        job_payload = job.get_payload()
        if job_payload.get("submission_key") != submission_key:
            continue
        if job.status in ACTIVE_STATUSES or job.status == "succeeded":
            return {**_job_to_dict(job), "reused": True}
        if job.status == "cancelled" and (job_payload.get("input", {}).get("snapshot_id") or job.job_type=="html_semantic_review"):
            raise HtmlTaskError("已取消的快照任务不会恢复；请更改输入后创建新任务", 409)
        if any(record.get("state") in {"intent", "unknown"} for record in job_payload.get("production_stages", {}).values()):
            raise HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：外部请求结果不确定，需核实后处理，禁止盲目重试", 409)
        if any(record.get("state") == "output_limit" for record in job_payload.get("production_stages", {}).values()):
            raise HtmlTaskError("MODEL_OUTPUT_LIMIT：原请求输出额度耗尽，请调整规划输入后创建新实验", 409)
        attempt = int(job_payload.get("attempt", 1))
        if attempt >= MAX_ATTEMPTS:
            raise HtmlTaskError(
                f"任务已达最大重试次数（{MAX_ATTEMPTS}）：{job.error or '未知错误'}",
                status_code=409,
            )
        # Retry in place: same row, next attempt.
        job.status = "queued"
        job.error = None
        job_payload["attempt"] = attempt + 1
        job_payload.pop("result", None)
        job.started_at = None
        job.finished_at = None
        job.payload_json = json_dumps(job_payload)
        job.updated_at = datetime.now()
        db.commit()
        db.refresh(job)
        return {**_job_to_dict(job), "reused": True, "retried": True}

    job = LocalJob(
        id=f"html_{uuid.uuid4().hex[:20]}",
        project_id=project_id,
        job_type=task_type,
        status="queued",
        stage="queued",
        payload_json=json_dumps(
            {
                "submission_key": submission_key,
                "attempt": 1,
                "input": payload or {},
            }
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {**_job_to_dict(job), "reused": False}


def json_dumps(value: Any) -> str:
    return json_module().dumps(value, ensure_ascii=False)


def json_module():
    import json

    return json


def _job(db, job_id, expected_attempt=None):
    from database import LocalJob

    db.expire_all()
    job = db.query(LocalJob).filter(LocalJob.id == job_id).first()
    if job is None:
        raise HtmlTaskError("任务不存在", status_code=404)
    if (
        expected_attempt is not None
        and int(job.get_payload().get("attempt", 1)) != expected_attempt
    ):
        raise HtmlTaskError("旧任务尝试已被重试替代", status_code=409)
    return job


def _transition(db, job, allowed, fields):
    from database import LocalJob

    changed = (
        db.query(LocalJob)
        .filter(
            LocalJob.id == job.id,
            LocalJob.status.in_(allowed),
            LocalJob.payload_json == job.payload_json,
        )
        .update(fields, synchronize_session=False)
    )
    if changed != 1:
        db.rollback()
        db.refresh(job)
        raise HtmlTaskError("任务状态已变化，拒绝迟到的状态更新", status_code=409)
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


def mark_running(db, job_id: str, expected_attempt=None) -> Dict[str, Any]:
    job = _job(db, job_id, expected_attempt)
    payload = job.get_payload()
    for key in ("next_action", "repair_status", "stop_reason"):
        payload.get("progress", {}).pop(key, None)
    return _transition(
        db,
        job,
        ("queued",),
        {"status": "running", "stage": "running", "started_at": datetime.now(), "payload_json": json_dumps(payload)},
    )


def mark_succeeded(
    db, job_id: str, result: Dict[str, Any], expected_attempt=None
) -> Dict[str, Any]:
    job = _job(db, job_id, expected_attempt)
    payload = job.get_payload()
    payload["result"] = result
    for key in ("next_action", "repair_status", "stop_reason"):
        payload.get("progress", {}).pop(key, None)
    return _transition(
        db,
        job,
        ("running",),
        {
            "status": "succeeded",
            "stage": result.get("stage", "succeeded"),
            "error": None,
            "result_artifact_id": None,
            "payload_json": json_dumps(payload),
            "finished_at": datetime.now(),
        },
    )


def mark_failed(db, job_id: str, error: str, expected_attempt=None) -> Dict[str, Any]:
    job = _job(db, job_id)
    if job.status not in ACTIVE_STATUSES or (
        expected_attempt is not None
        and int(job.get_payload().get("attempt", 1)) != expected_attempt
    ):
        return _job_to_dict(job)
    try:
        result = _transition(
            db,
            job,
            ACTIVE_STATUSES,
            {
                "status": "failed",
                "stage": "failed",
                "error": error[:2000],
                "finished_at": datetime.now(),
            },
        )
    except HtmlTaskError as exc:
        if exc.status_code != 409:
            raise
        return _job_to_dict(job)
    result["retryable"] = int(job.get_payload().get("attempt", 1)) < MAX_ATTEMPTS
    return result


def recover_interrupted(db) -> int:
    """Startup recovery: tasks left ``running``/``queued`` by an exited
    process become ``interrupted`` (retryable, never silently re-run)."""
    from database import LocalJob

    jobs = (
        db.query(LocalJob)
        .filter(
            LocalJob.job_type.in_(TASK_TYPES),
            LocalJob.status.in_(ACTIVE_STATUSES),
        )
        .all()
    )
    for job in jobs:
        job.status = "interrupted"
        job.stage = "interrupted"
        job.error = "进程退出导致任务中断；可重新提交以继续"
        job.updated_at = datetime.now()
    db.commit()
    return len(jobs)


def cancel_task(db, job_id: str) -> Dict[str, Any]:
    """Atomic cancellation cannot overwrite a success registered concurrently."""
    return _transition(
        db,
        _job(db, job_id),
        ACTIVE_STATUSES,
        {"status": "cancelled", "stage": "cancelled", "finished_at": datetime.now()},
    )


def record_progress(db,job_id,progress,expected_attempt=None):
    """Attempt-fenced progress over the existing persistent job payload."""
    job=_job(db,job_id,expected_attempt)
    payload=job.get_payload()
    payload["progress"]={**payload.get("progress",{}),**progress}
    return _transition(db,job,("running",),{"payload_json":json_dumps(payload),"stage":"semantic_review"})
