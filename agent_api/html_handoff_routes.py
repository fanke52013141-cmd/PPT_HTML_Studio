"""Authenticated Agent adapter for the same Web exchange owner."""
from fastapi import APIRouter, Depends

from database import get_db
from html_handoff_models import ExportRequest, ImportRequest, SaveRequest, HandoffResult, WorkReadRequest


router = APIRouter()  # /api/agent/v1 is protected by the existing auth middleware.


def _call(mode, project_id, slide_id, payload, db, task_id=None):
    from agent_api.routes import _html_editor_web_call, _html_project_or_404
    from html_handoff_routes import dispatch
    _html_project_or_404(project_id, db)
    result = _html_editor_web_call(dispatch, mode, project_id, slide_id, payload, db, task_id)
    if mode == "export":
        result["download_url"] = (f"/api/agent/v1/projects/{project_id}/html-visual/{slide_id}"
                                  f"/handoff/{result['task']['task_id']}/bundle")
    return result


@router.post("/projects/{project_id}/html-visual/{slide_id}/handoff/export", response_model=HandoffResult)
def export(project_id: str, slide_id: str, payload: ExportRequest, db=Depends(get_db)):
    return _call("export", project_id, slide_id, payload, db)


@router.get("/projects/{project_id}/html-visual/{slide_id}/handoff/{task_id}/bundle")
def bundle(project_id: str, slide_id: str, task_id: str, db=Depends(get_db)):
    return _call("bundle", project_id, slide_id, None, db, task_id)


@router.post("/projects/{project_id}/html-visual/{slide_id}/handoff/preview", response_model=HandoffResult)
def preview(project_id: str, slide_id: str, payload: ImportRequest, db=Depends(get_db)):
    return _call("preview", project_id, slide_id, payload, db)


@router.post("/projects/{project_id}/html-visual/{slide_id}/handoff/save", response_model=HandoffResult)
def save(project_id: str, slide_id: str, payload: SaveRequest, db=Depends(get_db)):
    return _call("save", project_id, slide_id, payload, db)


@router.post("/projects/{project_id}/html-visual/{slide_id}/handoff/work/read", response_model=HandoffResult)
def work_read(project_id: str, slide_id: str, payload: WorkReadRequest, db=Depends(get_db)):
    return _call("work_read", project_id, slide_id, payload, db)
