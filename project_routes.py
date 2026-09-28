"""Explicit FastAPI routes for project lifecycle."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from project_path_service import project_or_404
from project_impact_service import list_impacts, set_decision
from project_impact_service import resolve_impacts
from impact_source_version import impact_source_version
from artifact_fingerprint import sha256_file
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
    items = list_impacts(project.run_dir)
    from project_storage import slide_dir

    for item in items:
        if item.get("reason") == "storyboard_visual_changed" and "images" in item.get("affected", ()):
            slide_id = str(item.get("scope_id") or "")
            item["image_sha256"] = sha256_file(slide_dir(project.run_dir, slide_id) / "visual_draft.png")
    return {"success": True, "items": items}


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


@router.put("/api/projects/{project_id}/impacts/reuse-image")
def confirm_storyboard_image_reuse(
    project_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Confirm one existing image against the current storyboard visual input."""
    project = project_or_404(db, project_id)
    slide_id = str(payload.get("slide_id") or "").strip()
    version = str(payload.get("source_version") or "").strip()
    image_hash = str(payload.get("image_sha256") or "").strip()
    if not slide_id or not version or not image_hash:
        raise HTTPException(status_code=400, detail="缺少页面、分镜版本或图片版本")
    from project_storage import slide_dir
    from pipeline_lifecycle import project_artifact_lock

    with project_artifact_lock(project.run_dir):
        current = next((item for item in list_impacts(project.run_dir)
                        if item.get("id") == f"storyboard_visual_changed:{slide_id}"), None)
        image = slide_dir(project.run_dir, slide_id) / "visual_draft.png"
        if (current is None or "images" not in current.get("affected", ())
                or current.get("source_version") != version
                or impact_source_version(project.run_dir, "storyboard_visual_changed", slide_id) != version
                or sha256_file(image) != image_hash):
            raise HTTPException(status_code=409, detail="分镜或图片已变化，请刷新后重新核对")
        settled = resolve_impacts(
            project.run_dir, affected=("images",), slide_ids=(slide_id,), source_version=version,
        )
    return {"success": True, "resolved": bool(settled)}


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
