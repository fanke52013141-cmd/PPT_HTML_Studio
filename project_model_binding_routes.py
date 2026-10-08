"""Account-scoped HTML model configuration; shared service for Web and Agent."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from project_path_service import project_or_404
from project_model_binding_models import ProjectModelBindingUpdate
from project_model_binding_service import (
    ModelBindingError, ModelBindingConflict, get_project_model_binding,
    save_project_model_binding,
)

router = APIRouter()


def _project(db, project_id):
    project = project_or_404(db, project_id)
    if project.visual_backend != "html":
        raise HTTPException(400, "项目独立模型配置仅适用于 HTML 项目")
    return project


@router.get("/api/projects/{project_id}/model-binding")
def read_binding(project_id: str, db: Session = Depends(get_db)):
    project = _project(db, project_id)
    try:
        return get_project_model_binding(project)
    except ModelBindingError as exc:
        raise HTTPException(400, str(exc)) from None


@router.put("/api/projects/{project_id}/model-binding")
def update_binding(project_id: str, payload: ProjectModelBindingUpdate, db: Session = Depends(get_db)):
    project = _project(db, project_id)
    try:
        return save_project_model_binding(project, payload)
    except ModelBindingConflict as exc:
        raise HTTPException(409, str(exc)) from None
    except ModelBindingError as exc:
        raise HTTPException(400, str(exc)) from None
