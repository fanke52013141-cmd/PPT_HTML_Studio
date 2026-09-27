# -*- coding: utf-8 -*-
"""勾画标注模块的持久任务存储(W3)。

复用 ``local_jobs`` 表,job_type 独立命名(annotation_detect / annotation_plan /
annotation_align / annotation_preview),不复用写死 video_render 的
``VideoJobStore``。状态枚举与既有 paused 约定对齐;成功必须清错
(progress=100 且 error=NULL);重启把遗留活动任务标 interrupted。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from database import LocalJob

__all__ = [
    "ANNOTATION_JOB_TYPES",
    "AnnotationJobPersistenceError",
    "AnnotationJobStore",
]

ANNOTATION_JOB_TYPES = ("annotation_detect", "annotation_plan", "annotation_align", "annotation_preview")

_RETRY_DELAYS_SEC = (0.1, 0.2, 0.4)


class AnnotationJobPersistenceError(RuntimeError):
    def __init__(self, category: str, **details: Any):
        super().__init__(f"annotation job persistence failure: {category}")
        self.category = category
        self.details = details


class AnnotationJobStore:
    """annotation_* 任务在 local_jobs 上的窄操作面。"""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.session_factory = session_factory
        self._sleep = sleep

    # ------------------------------------------------------------ 基础

    def create(
        self,
        project_id: str,
        *,
        job_type: str,
        payload: Dict[str, Any],
        request_key: Optional[str] = None,
    ) -> LocalJob:
        if job_type not in ANNOTATION_JOB_TYPES:
            raise ValueError(f"unknown annotation job type: {job_type}")
        last_error: Optional[Exception] = None
        for attempt in range(len(_RETRY_DELAYS_SEC) + 1):
            try:
                db = self.session_factory()
            except Exception as exc:
                last_error = exc
                self._sleep(_RETRY_DELAYS_SEC[min(attempt, len(_RETRY_DELAYS_SEC) - 1)])
                continue
            try:
                # 幂等:相同 project/type/request_key 的活跃或成功任务直接复用
                if request_key:
                    existing = self.find_by_request_key(project_id, job_type, request_key, db=db)
                    if existing is not None:
                        return existing
                job = LocalJob(
                    id=f"annojob_{uuid.uuid4().hex[:20]}",
                    project_id=project_id,
                    job_type=job_type,
                    status="queued",
                    progress=0,
                    stage="queued",
                    error=None,
                    payload_json=_dump_payload({**payload, "request_key": request_key}),
                )
                db.add(job)
                db.commit()
                # commit 会使属性过期;返回前重新加载并脱离会话,
                # 让调用方在会话关闭后仍能安全读取字段。
                db.refresh(job)
                db.expunge(job)
                return job
            except Exception as exc:
                last_error = exc
                try:
                    db.rollback()
                except Exception:
                    pass
                self._sleep(_RETRY_DELAYS_SEC[min(attempt, len(_RETRY_DELAYS_SEC) - 1)])
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        raise AnnotationJobPersistenceError("create_failed", exception_type=type(last_error).__name__ if last_error else None)

    def get(self, job_id: str) -> Optional[LocalJob]:
        db = self.session_factory()
        try:
            return db.get(LocalJob, job_id)
        finally:
            db.close()

    def find_by_request_key(
        self,
        project_id: str,
        job_type: str,
        request_key: str,
        *,
        db: Optional[Session] = None,
    ) -> Optional[LocalJob]:
        owned_session = db is None
        session = db or self.session_factory()
        try:
            rows = (
                session.query(LocalJob)
                .filter(
                    LocalJob.project_id == project_id,
                    LocalJob.job_type == job_type,
                )
                .order_by(LocalJob.created_at.desc())
                .limit(50)
                .all()
            )
            for row in rows:
                payload = row.get_payload()
                if payload.get("request_key") == request_key and row.status in ("queued", "running", "succeeded"):
                    return row
            return None
        finally:
            if owned_session:
                session.close()

    def latest_active(self, project_id: str, job_type: Optional[str] = None) -> Optional[LocalJob]:
        db = self.session_factory()
        try:
            query = db.query(LocalJob).filter(
                LocalJob.project_id == project_id,
                LocalJob.status.in_(("queued", "running")),
            )
            if job_type:
                query = query.filter(LocalJob.job_type == job_type)
            return query.order_by(LocalJob.created_at.desc()).first()
        finally:
            db.close()

    # ------------------------------------------------------------ 状态迁移

    def mark_running(self, job_id: str, stage: str) -> None:
        self._update(job_id, {"status": "running", "stage": stage, "progress": 5, "error": None})

    def update_progress(self, job_id: str, progress: int, stage: Optional[str] = None) -> None:
        fields: Dict[str, Any] = {"progress": max(0, min(100, int(progress)))}
        if stage:
            fields["stage"] = stage
        self._update(job_id, fields)

    def mark_succeeded(self, job_id: str, stage: str, result: Dict[str, Any]) -> None:
        # 成功必须清错:持久终态 progress=100 / error=NULL
        self._update(
            job_id,
            {
                "status": "succeeded",
                "stage": stage,
                "progress": 100,
                "error": None,
                "payload_json": _dump_payload({**self._payload_of(job_id), "result": result}),
            },
        )

    def mark_failed(self, job_id: str, message: str, *, retryable: bool = False) -> None:
        self._update(
            job_id,
            {
                "status": "failed",
                "error": _sanitize_error(message),
                "payload_json": _dump_payload({**self._payload_of(job_id), "retryable": retryable}),
            },
        )

    def mark_cancelled(self, job_id: str) -> None:
        self._update(job_id, {"status": "cancelled", "error": None})

    def interrupt_orphaned(self, project_id: Optional[str] = None) -> int:
        """把上一进程遗留的 queued/running 任务标 interrupted。"""
        db = self.session_factory()
        count = 0
        try:
            query = db.query(LocalJob).filter(
                LocalJob.job_type.in_(ANNOTATION_JOB_TYPES),
                LocalJob.status.in_(("queued", "running")),
            )
            if project_id:
                query = query.filter(LocalJob.project_id == project_id)
            for job in query.all():
                job.status = "interrupted"
                job.error = "进程重启导致任务中断,可重新发起"
                count += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return count

    # ------------------------------------------------------------ 内部

    def _payload_of(self, job_id: str) -> Dict[str, Any]:
        job = self.get(job_id)
        return job.get_payload() if job else {}

    def _update(self, job_id: str, fields: Dict[str, Any]) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(len(_RETRY_DELAYS_SEC) + 1):
            db = self.session_factory()
            try:
                job = db.get(LocalJob, job_id)
                if job is None:
                    return
                for key, value in fields.items():
                    setattr(job, key, value)
                db.commit()
                return
            except Exception as exc:
                last_error = exc
                try:
                    db.rollback()
                except Exception:
                    pass
                self._sleep(_RETRY_DELAYS_SEC[min(attempt, len(_RETRY_DELAYS_SEC) - 1)])
            finally:
                db.close()
        raise AnnotationJobPersistenceError("update_failed", exception_type=type(last_error).__name__ if last_error else None)


def _dump_payload(payload: Dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, default=str)


def _sanitize_error(message: Any) -> str:
    """错误文本不得携带密钥;超长截断。"""
    text = str(message or "unknown error")
    lowered = text.lower()
    for marker in ("api_key", "apikey", "authorization", "bearer", "secret"):
        if marker in lowered:
            return "上游引擎请求失败(错误详情已脱敏)"
    return text[:800]
