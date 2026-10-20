"""Thin account-scoped Web endpoints for the portable external exchange."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from html_handoff_models import ExportRequest, ImportRequest, SaveRequest, WorkReadRequest, WorkRequest


router = APIRouter()


def _db():
    from html_visual_routes import _get_db
    yield from _get_db()


def dispatch(mode, project_id, slide_id, payload, db, task_id=None):
    import html_external_handoff as handoff
    from html_visual_routes import _html_project
    from html_scene_editing import SceneEditError
    from html_visual_store import HtmlVisualConflict, HtmlVisualError
    from pipeline_lifecycle import project_artifact_lock
    from project_path_service import project_run_dir_or_500

    project = _html_project(project_id, db)
    run = project_run_dir_or_500(project)
    try:
        with project_artifact_lock(run):
            if mode == "export":
                result = handoff.export_bundle(run, project_id, slide_id, payload)
                result["download_url"] = (f"/api/projects/{project_id}/html-visual/{slide_id}"
                                          f"/handoff/{result['task']['task_id']}/bundle")
            elif mode == "bundle":
                return FileResponse(handoff.bundle_path(run, project_id, slide_id, task_id),
                                    media_type="application/zip", filename=f"external-agent-{slide_id}.zip",
                                    headers={"Cache-Control": "no-store"})
            elif mode == "preview":
                result = handoff.import_preview(run, project_id, slide_id, payload)
            elif mode.startswith("work_"):
                import html_handoff_workbench as workbench
                functions = {"work_open": workbench.open_work, "work_read": workbench.read_work,
                    "work_propose": workbench.preview_proposal, "work_update": workbench.update_work, "work_check": workbench.check_work, "work_save": workbench.save_work}
                result = functions[mode](run, project_id, slide_id, payload)
                if mode == "work_save" and result["changed"]:
                    from invalidation_service import html_scene_changed
                    html_scene_changed(project, [slide_id], rebuild_plan=result.get("rebuild_plan"))
                    db.commit()
            else:
                result = handoff.save_result(run, project_id, slide_id, payload)
                if result["changed"]:
                    from invalidation_service import html_scene_changed
                    html_scene_changed(project, [slide_id], rebuild_plan=result.get("rebuild_plan"))
                    db.commit()
        return {"success": True, **result}
    except handoff.HandoffError as exc:
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    except HtmlVisualConflict as exc:
        raise HTTPException(409, detail={"code": "REVISION_CONFLICT", "message": str(exc)}) from exc
    except SceneEditError as exc:
        raise HTTPException(409 if exc.code == "AUDIO_REVISION_CONFLICT" else 422,
                            detail={"code": exc.code, "message": str(exc)}) from exc
    except HtmlVisualError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except (ValueError, KeyError, OSError) as exc:
        from html_visual_review_service import HtmlReviewError
        if isinstance(exc, HtmlReviewError):
            raise HTTPException(exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
        raise HTTPException(422, detail={"code": "HANDOFF_MATERIAL_INVALID", "message": "交接材料缺失或不合法，请检查当前页输入"}) from exc


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/export")
def export(project_id: str, slide_id: str, payload: ExportRequest, db: Any = Depends(_db)):
    return dispatch("export", project_id, slide_id, payload, db)


@router.get("/api/projects/{project_id}/html-visual/{slide_id}/handoff/{task_id}/bundle")
def bundle(project_id: str, slide_id: str, task_id: str, db: Any = Depends(_db)):
    return dispatch("bundle", project_id, slide_id, None, db, task_id)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/preview")
def preview(project_id: str, slide_id: str, payload: ImportRequest, db: Any = Depends(_db)):
    return dispatch("preview", project_id, slide_id, payload, db)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/save")
def save(project_id: str, slide_id: str, payload: SaveRequest, db: Any = Depends(_db)):
    return dispatch("save", project_id, slide_id, payload, db)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/work/open")
def work_open(project_id: str, slide_id: str, payload: WorkReadRequest, db: Any = Depends(_db)):
    return dispatch("work_open", project_id, slide_id, payload, db)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/work/read")
def work_read(project_id: str, slide_id: str, payload: WorkReadRequest, db: Any = Depends(_db)):
    return dispatch("work_read", project_id, slide_id, payload, db)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/work/update")
def work_update(project_id: str, slide_id: str, payload: WorkRequest, db: Any = Depends(_db)):
    return dispatch("work_update", project_id, slide_id, payload, db)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/work/check")
def work_check(project_id: str, slide_id: str, payload: WorkRequest, db: Any = Depends(_db)):
    return dispatch("work_check", project_id, slide_id, payload, db)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/work/save")
def work_save(project_id: str, slide_id: str, payload: WorkRequest, db: Any = Depends(_db)):
    return dispatch("work_save", project_id, slide_id, payload, db)


@router.post("/api/projects/{project_id}/html-visual/{slide_id}/handoff/work/propose")
def work_propose(project_id: str, slide_id: str, payload: WorkRequest, db: Any = Depends(_db)):
    return dispatch("work_propose", project_id, slide_id, payload, db)
