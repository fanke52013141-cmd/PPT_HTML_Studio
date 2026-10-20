"""Thin account-scoped Web and Agent adapters for unattended candidate jobs."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from html_agent_models import AgentJobRequest, AgentJobRead, AgentJobResult
from html_agent_workflow_models import WorkflowRequest

router = APIRouter()


def _db():
    from html_visual_routes import _get_db
    yield from _get_db()


def dispatch(mode, project_id, slide_id, db, payload=None, job_id=None):
    from html_visual_routes import _html_project
    from project_path_service import project_run_dir_or_500
    from html_agent_execution import ExecutionError
    from html_agent_store import JobConflict
    import html_agent_jobs as jobs
    project = _html_project(project_id, db)
    run = project_run_dir_or_500(project)
    store = jobs.configure()
    try:
        if mode in {"create", "workflow_create"}:
            from project_model_binding_service import freeze_project_models
            from html_agent_store import digest
            existing_id = digest(["html_pi_agent", project_id, payload.idempotency_key])
            try:
                store.read(project_id, slide_id, existing_id)
            except KeyError:
                frozen = freeze_project_models(project)
                pure_planning = (mode == "workflow_create"
                    and payload.task.task_type in {"article.generate", "storyboard.plan"})
                model = (getattr(frozen, "planning", None) or frozen.text) if pure_planning else frozen.text
            else:
                model = None
            if mode == "workflow_create":
                from html_agent_workflows import submit
                return submit(project, payload, model, store=store)
            return jobs.submit(run, project_id, slide_id, payload, model, store=store)
        if mode == "cancel":
            return store.update(project_id, slide_id, job_id, cancel_requested=True)
        return store.read(project_id, slide_id, job_id)
    except KeyError as error:
        raise HTTPException(404, detail={"code": "job_not_found", "message": "任务不存在"}) from error
    except JobConflict as error:
        raise HTTPException(409, detail={"code": "idempotency_conflict", "message": str(error)}) from error
    except ExecutionError as error:
        raise HTTPException(409 if error.code == "stale_input" else 422, detail={"code": error.code, "message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(422, detail={"code": "invalid_input", "message": "模型配置或任务输入不完整，请检查项目模型设置"}) from error


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/agent/jobs", response_model=AgentJobResult, status_code=202)
def create(project_id: str, slide_id: str, payload: AgentJobRequest, db: Any = Depends(_db)):
    return dispatch("create", project_id, slide_id, db, payload)


@router.get("/api/projects/{project_id}/html-visual/{slide_id}/agent/jobs/{job_id}", response_model=AgentJobResult)
def read(project_id: str, slide_id: str, job_id: str, db: Any = Depends(_db)):
    return dispatch("read", project_id, slide_id, db, job_id=job_id)


@router.get("/api/projects/{project_id}/html-visual/{slide_id}/agent/jobs/{job_id}/result", response_model=AgentJobResult)
def result(project_id: str, slide_id: str, job_id: str, db: Any = Depends(_db)):
    return dispatch("read", project_id, slide_id, db, job_id=job_id)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/agent/jobs/{job_id}/cancel", response_model=AgentJobResult)
def cancel(project_id: str, slide_id: str, job_id: str, payload: AgentJobRead, db: Any = Depends(_db)):
    return dispatch("cancel", project_id, slide_id, db, job_id=job_id)


@router.post("/api/projects/{project_id}/agent/jobs", response_model=AgentJobResult, status_code=202)
def workflow_create(project_id: str, payload: WorkflowRequest, db: Any = Depends(_db)):
    return dispatch("workflow_create", project_id, "__project__", db, payload)


@router.get("/api/projects/{project_id}/agent/jobs/{job_id}", response_model=AgentJobResult)
def workflow_read(project_id: str, job_id: str, db: Any = Depends(_db)):
    return dispatch("read", project_id, "__project__", db, job_id=job_id)


@router.get("/api/projects/{project_id}/agent/jobs/{job_id}/result", response_model=AgentJobResult)
def workflow_result(project_id: str, job_id: str, db: Any = Depends(_db)):
    return dispatch("read", project_id, "__project__", db, job_id=job_id)


@router.post("/api/projects/{project_id}/agent/jobs/{job_id}/cancel", response_model=AgentJobResult)
def workflow_cancel(project_id: str, job_id: str, payload: AgentJobRead, db: Any = Depends(_db)):
    return dispatch("cancel", project_id, "__project__", db, job_id=job_id)
