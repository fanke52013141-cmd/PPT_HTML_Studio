"""Explicit FastAPI routes for project lifecycle."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from project_path_service import project_or_404
from project_impact_service import list_impacts, set_decision
from project_service import (
    AiModeUpdate,
    ProjectCreate,
    ProjectService,
    ProjectUpdate,
    get_project_service,
)


router = APIRouter()


@router.get("/api/projects/{project_id}/impacts")
def get_project_impacts(project_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    project = project_or_404(db, project_id)
    return {"success": True, "items": list_impacts(project.run_dir)}


@router.put("/api/projects/{project_id}/impacts/decision")
def update_project_impact_decision(
    project_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    project = project_or_404(db, project_id)
    try:
        item = set_decision(
            project.run_dir,
            str(payload.get("impact_id") or ""),
            str(payload.get("decision") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="待处理影响不存在")
    return {"success": True, "item": item}


@router.post("/api/projects")
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    return service.create(payload, db)


@router.get("/api/projects")
def list_projects(
    db: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> list[dict[str, Any]]:
    return service.list(db)


@router.get("/api/projects/{project_id}")
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    return service.get(project_id, db)


@router.get("/api/projects/{project_id}/ai-mode")
def get_project_ai_mode(
    project_id: str,
    db: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, str]:
    return service.get_ai_mode(project_id, db)


@router.put("/api/projects/{project_id}/ai-mode")
def update_project_ai_mode(
    project_id: str,
    payload: AiModeUpdate,
    db: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    return service.update_ai_mode(project_id, payload, db)


@router.put("/api/projects/{project_id}")
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    return service.update(project_id, payload, db)


@router.delete("/api/projects/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    return service.delete(project_id, db)
