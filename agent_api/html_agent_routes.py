"""Authenticated Agent adapter for the same Pi job owner."""
from fastapi import APIRouter, Depends
from database import get_db
from html_agent_models import AgentJobRequest, AgentJobRead, AgentJobResult
from html_agent_workflow_models import WorkflowRequest

router = APIRouter()


def call(mode, project_id, slide_id, db, payload=None, job_id=None):
    from agent_api.routes import _html_project_or_404, _html_editor_web_call
    from html_agent_routes import dispatch
    _html_project_or_404(project_id, db)
    return _html_editor_web_call(dispatch, mode, project_id, slide_id, db, payload, job_id)


@router.post("/projects/{project_id}/html-visual/{slide_id}/agent/jobs", response_model=AgentJobResult, status_code=202)
def create(project_id: str, slide_id: str, payload: AgentJobRequest, db=Depends(get_db)):
    return call("create", project_id, slide_id, db, payload)


@router.get("/projects/{project_id}/html-visual/{slide_id}/agent/jobs/{job_id}", response_model=AgentJobResult)
def read(project_id: str, slide_id: str, job_id: str, db=Depends(get_db)):
    return call("read", project_id, slide_id, db, job_id=job_id)


@router.get("/projects/{project_id}/html-visual/{slide_id}/agent/jobs/{job_id}/result", response_model=AgentJobResult)
def result(project_id: str, slide_id: str, job_id: str, db=Depends(get_db)):
    return call("read", project_id, slide_id, db, job_id=job_id)


@router.post("/projects/{project_id}/html-visual/{slide_id}/agent/jobs/{job_id}/cancel", response_model=AgentJobResult)
def cancel(project_id: str, slide_id: str, job_id: str, payload: AgentJobRead, db=Depends(get_db)):
    return call("cancel", project_id, slide_id, db, job_id=job_id)


@router.post("/projects/{project_id}/agent/jobs", response_model=AgentJobResult, status_code=202)
def workflow_create(project_id: str, payload: WorkflowRequest, db=Depends(get_db)):
    return call("workflow_create", project_id, "__project__", db, payload)


@router.get("/projects/{project_id}/agent/jobs/{job_id}", response_model=AgentJobResult)
def workflow_read(project_id: str, job_id: str, db=Depends(get_db)):
    return call("read", project_id, "__project__", db, job_id=job_id)


@router.get("/projects/{project_id}/agent/jobs/{job_id}/result", response_model=AgentJobResult)
def workflow_result(project_id: str, job_id: str, db=Depends(get_db)):
    return call("read", project_id, "__project__", db, job_id=job_id)


@router.post("/projects/{project_id}/agent/jobs/{job_id}/cancel", response_model=AgentJobResult)
def workflow_cancel(project_id: str, job_id: str, payload: AgentJobRead, db=Depends(get_db)):
    return call("cancel", project_id, "__project__", db, job_id=job_id)
