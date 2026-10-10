"""HTTP contract for the HTML visual backend scene documents (B02).

Routes only: parsing, project/backend guards, and error translation.
Storage lives in ``html_visual_store``; the service boundaries are the
frozen dependency record configured once by ``server.py``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt

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
    from project_path_service import project_or_404

    project = project_or_404(db, project_id)
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
    from visual_contract_service import read_contract_slide_ids

    run_dir = project_run_dir_or_500(project)
    slide_ids = read_contract_slide_ids(run_dir)
    from pathlib import Path
    from html_creation_workflow import project_status

    return {
        "success": True,
        "project_id": project_id,
        **project_status(
            project,
            run_dir=run_dir,
            repo_root=Path(__file__).resolve().parent,
            slide_ids=slide_ids,
            db=db,
        ),
    }


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


class SceneEditorSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene: dict[str, Any]
    binding: dict[str, Any] | None
    expected_revision: StrictInt = Field(ge=0)
    anchor_overrides: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


@router.get("/api/projects/{project_id}/html-visual/{slide_id}/editor")
def html_scene_editor_get(project_id: str, slide_id: str, db: Any = Depends(_get_db)):
    from html_scene_editing import load_editor, SceneEditError
    from pipeline_lifecycle import project_artifact_lock

    run_dir = project_run_dir_or_500(_html_project(project_id, db))
    try:
        with project_artifact_lock(run_dir):
            return {"success": True, **load_editor(run_dir, slide_id)}
    except SceneEditError as exc:
        raise HTTPException(
            404 if exc.code == "SCENE_MISSING" else 422,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except store.HtmlVisualError as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@router.put("/api/projects/{project_id}/html-visual/{slide_id}/editor")
def html_scene_editor_put(
    project_id: str,
    slide_id: str,
    payload: SceneEditorSaveRequest,
    db: Any = Depends(_get_db),
):
    from html_scene_editing import save_editor, SceneEditError
    from pipeline_lifecycle import project_artifact_lock

    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    try:
        with project_artifact_lock(run_dir):
            result = save_editor(run_dir, slide_id, **payload.model_dump())
            if result["changed"]:
                from invalidation_service import html_scene_changed

                html_scene_changed(project, [slide_id])
                db.commit()
        return {"success": True, "slide_id": slide_id, **result}
    except store.HtmlVisualConflict as exc:
        raise HTTPException(
            409,
            detail={
                "code": "REVISION_CONFLICT",
                "message": str(exc),
                "expected_revision": exc.expected,
                "current_revision": exc.current,
            },
        ) from exc
    except SceneEditError as exc:
        raise HTTPException(
            422, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    except store.HtmlVisualError as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@router.get("/api/html-scene-editor/runtime/{name}")
def html_scene_editor_runtime(name: str):
    """Only fixed shared bundles; no project data or arbitrary file paths."""
    from pathlib import Path
    from fastapi.responses import FileResponse

    if name not in ("data.js", "player.js"):
        raise HTTPException(404, detail="Unknown runtime file")
    return FileResponse(
        Path(__file__).resolve().parent / "html_engine/visual/preview" / name,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/editor/preview")
def html_scene_editor_preview(
    project_id: str,
    slide_id: str,
    payload: SceneEditorSaveRequest,
    db: Any = Depends(_get_db),
):
    from html_scene_editing import preview_editor, SceneEditError
    from pipeline_lifecycle import project_artifact_lock

    run_dir = project_run_dir_or_500(_html_project(project_id, db))
    try:
        with project_artifact_lock(run_dir):
            return {
                "success": True,
                **preview_editor(
                    run_dir,
                    slide_id,
                    payload.scene,
                    payload.binding,
                    payload.anchor_overrides,
                ),
            }
    except SceneEditError as exc:
        raise HTTPException(
            422, detail={"code": exc.code, "message": str(exc)}
        ) from exc
