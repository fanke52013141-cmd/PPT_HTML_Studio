"""HTTP contract for the HTML visual backend scene documents (B02).

Routes only: parsing, project/backend guards, and error translation.
Storage lives in ``html_visual_store``; the service boundaries are the
frozen dependency record configured once by ``server.py``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import html_visual_store as store
from project_path_service import project_run_dir_or_500

router = APIRouter()


class HtmlVisualDependencies:
    """Narrow dependency record; never the application module."""

    def __init__(
        self,
        artifact_lock: Any = None,
    ) -> None:
        self.artifact_lock = artifact_lock


_dependencies = HtmlVisualDependencies()


def configure_html_visual_service(dependencies: HtmlVisualDependencies) -> None:
    global _dependencies
    _dependencies = dependencies


def _get_db():
    from database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _html_project(project_id: str, db: Any):
    from database import Project

    project = (
        db.query(Project).filter(Project.id == project_id).first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    if (project.visual_backend or "image") != "html":
        raise HTTPException(
            status_code=400,
            detail="该项目使用图片管线；HTML 场景接口仅适用于 HTML 后端项目",
        )
    return project


class SceneSaveRequest(BaseModel):
    scene: dict[str, Any]
    expected_revision: int


@router.get("/api/projects/{project_id}/html-visual/status")
def html_visual_status(project_id: str, db: Any = Depends(_get_db)):
    project = _html_project(project_id, db)
    from project_path_service import read_current_slide_ids_or_404

    run_dir = project_run_dir_or_500(project)
    slide_ids = read_current_slide_ids_or_404(project)
    return {"success": True, **store.read_status(run_dir, slide_ids)}


@router.get("/api/projects/{project_id}/html-visual/{slide_id}")
def html_visual_get(project_id: str, slide_id: str, db: Any = Depends(_get_db)):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    try:
        document = store.load_scene_with_revision(run_dir, slide_id)
    except store.HtmlVisualError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if document is None:
        raise HTTPException(status_code=404, detail="该页尚未保存 HTML 场景")
    return {"success": True, "slide_id": slide_id, **document}


@router.put("/api/projects/{project_id}/html-visual/{slide_id}")
def html_visual_put(
    project_id: str,
    slide_id: str,
    payload: SceneSaveRequest,
    db: Any = Depends(_get_db),
):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    try:
        result = store.save_scene(
            run_dir,
            slide_id,
            payload.scene,
            payload.expected_revision,
            lock=_dependencies.artifact_lock,
            write_json_atomic=_dependencies.write_json_atomic,
        )
    except store.HtmlVisualConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )
    except store.HtmlVisualError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    response = {"success": True, "slide_id": slide_id, **result}
    if result["changed"]:
        # Invalidation updates files and project state but never commits;
        # this route owns the single database commit (project rule).
        from invalidation_service import html_scene_changed

        html_scene_changed(project, [slide_id])
        db.commit()
    return response
