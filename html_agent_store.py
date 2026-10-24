"""Pi task persistence in existing local_jobs; no startup effects on import."""
import json
import threading
from datetime import datetime
from hashlib import sha256


ACTIVE = ("queued", "running")
LOCK = threading.RLock()
TYPE = "html_pi_agent"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def derive_job_id(project, idempotency_key):
    """Single derivation of the Pi job identity (duplicates previously drifted)."""
    return digest([TYPE, project, idempotency_key])


class JobConflict(ValueError):
    pass


class AgentJobStore:
    def __init__(self, factory):
        self.factory = factory

    def recover(self):
        from database import LocalJob
        with LOCK, self.factory() as db:
            for row in db.query(LocalJob).filter(LocalJob.job_type == TYPE, LocalJob.status.in_(ACTIVE)):
                data = row.get_payload()
                data.update(error={"code": "save_outcome_unknown" if data.get("commit_started") else "interrupted",
                    "message": "进程已退出；请核对保存回执与作者版本，未知请求未重发"})
                row.payload_json = json.dumps(data, ensure_ascii=False)
                row.status = row.stage = "interrupted"
                row.finished_at = datetime.now()
            db.commit()

    def create(self, project, slide, request, model_summary):
        from database import LocalJob
        job_id = derive_job_id(project, request.idempotency_key)
        body = {"slide_id": slide, "request": request.model_dump(mode="json")}
        with LOCK, self.factory() as db:
            row = db.get(LocalJob, job_id)
            if row:
                if row.project_id != project or row.job_type != TYPE or row.get_payload()["input_hash"] != digest(body):
                    raise JobConflict("幂等键已被不同输入使用")
                return self._public(row), False
            row = LocalJob(id=job_id, project_id=project, job_type=TYPE, status="queued", stage="queued", progress=0,
                payload_json=json.dumps({**body, "input_hash": digest(body), "model": model_summary,
                    "result": None, "error": None, "cancel_requested": False,
                    "usage": {"model_calls": 0, "tool_calls": 0, "candidate_rounds": 0, "tokens": None, "cost": None}}, ensure_ascii=False))
            db.add(row)
            db.commit()
            return self._public(row), True

    def read(self, project, slide, job_id, *, private=False):
        from database import LocalJob
        with LOCK, self.factory() as db:
            row = db.get(LocalJob, job_id)
            if not row or row.job_type != TYPE or row.project_id != project or row.get_payload()["slide_id"] != slide:
                raise KeyError("任务不存在")
            return ({**self._public(row), "payload": row.get_payload()} if private else self._public(row))

    def update(self, project, slide, job_id, *, status=None, progress=None, **fields):
        from database import LocalJob
        with LOCK, self.factory() as db:
            row = db.get(LocalJob, job_id)
            if not row or row.job_type != TYPE or row.project_id != project or row.get_payload()["slide_id"] != slide:
                raise KeyError("任务不存在")
            if row.status not in ACTIVE:
                return self._public(row)
            data = row.get_payload()
            if fields.get("cancel_requested") and data.get("commit_started"):
                return self._public(row)
            data.update(fields)
            if status == "succeeded" and data.get("cancel_requested") and not data.get("commit_started"):
                status = "cancelled"
                data.update(result=None, error={"code": "cancelled", "message": "交付前已收到取消请求"})
            if status:
                row.status = row.stage = status
                if status == "running": row.started_at = datetime.now()
                if status not in ACTIVE: row.finished_at = datetime.now()
            if progress is not None: row.progress = progress
            row.error = data.get("error", {}).get("message") if data.get("error") else None
            row.payload_json = json.dumps(data, ensure_ascii=False)
            db.commit()
            return self._public(row)

    def begin_commit(self, project, slide, job_id):
        with LOCK:
            row = self.read(project, slide, job_id, private=True)
            if row["status"] not in ACTIVE or row["payload"].get("cancel_requested"):
                from html_agent_execution import ExecutionError
                raise ExecutionError("cancelled", "保存前已取消，作者未修改")
            return self.update(project, slide, job_id, commit_started=True, progress=95)

    @staticmethod
    def _public(row):
        data = row.get_payload()
        return {"schema_version": "agent-job/1.0", "job_id": row.id, "status": row.status,
                "can_cancel": row.status in ACTIVE and not data.get("commit_started", False),
                "partial_results": data.get("partial_items", []),
                "progress": row.progress, "result": data.get("result") if row.status == "succeeded" else None,
                "error": data.get("error"), "usage": data["usage"]}
