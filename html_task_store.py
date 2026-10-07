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

TASK_TYPES = ("html_plan_generate", "html_review", "html_asset_produce")
MAX_ATTEMPTS = 3
ACTIVE_STATUSES = ("queued", "running")


class HtmlTaskError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _job_to_dict(job) -> Dict[str, Any]:
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
    }


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
        payload_json=json_dumps({
            "submission_key": submission_key,
            "attempt": 1,
            "input": payload or {},
        }),
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


def mark_running(db, job_id: str) -> Dict[str, Any]:
    from database import LocalJob

    job = db.query(LocalJob).filter(LocalJob.id == job_id).first()
    if job is None:
        raise HtmlTaskError("任务不存在", status_code=404)
    if job.status not in ACTIVE_STATUSES:
        raise HtmlTaskError(f"任务处于终态 {job.status}，不能再启动")
    job.status = "running"
    job.stage = "running"
    job.started_at = datetime.now()
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


def mark_succeeded(db, job_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    from database import LocalJob

    job = db.query(LocalJob).filter(LocalJob.id == job_id).first()
    if job is None:
        raise HtmlTaskError("任务不存在", status_code=404)
    job.status = "succeeded"
    job.stage = "succeeded"
    job.error = None
    job.result_artifact_id = None
    payload = job.get_payload()
    payload["result"] = result
    job.payload_json = json_dumps(payload)
    job.finished_at = datetime.now()
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


def mark_failed(db, job_id: str, error: str) -> Dict[str, Any]:
    """Record a failure; the job stays retryable until the attempt budget
    runs out, in which case the failure is terminal."""
    from database import LocalJob

    job = db.query(LocalJob).filter(LocalJob.id == job_id).first()
    if job is None:
        raise HtmlTaskError("任务不存在", status_code=404)
    payload = job.get_payload()
    attempt = int(payload.get("attempt", 1))
    job.status = "failed"
    job.stage = "failed"
    job.error = error[:2000]
    job.finished_at = datetime.now()
    db.commit()
    db.refresh(job)
    result = _job_to_dict(job)
    result["retryable"] = attempt < MAX_ATTEMPTS
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
    """Cancel safety: only active tasks can be cancelled; a terminal
    (succeeded/failed) result is never overwritten by a late cancel."""
    from database import LocalJob

    job = db.query(LocalJob).filter(LocalJob.id == job_id).first()
    if job is None:
        raise HtmlTaskError("任务不存在", status_code=404)
    if job.status not in ACTIVE_STATUSES:
        raise HtmlTaskError(
            f"任务已处于终态 {job.status}，取消无效", status_code=409
        )
    job.status = "cancelled"
    job.stage = "cancelled"
    job.finished_at = datetime.now()
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)
