"""Account-scoped HTML sheet routes; no model calls on request thread."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from html_asset_sheet import HtmlAssetSheetError
from html_asset_sheet_models import (HtmlSheetGenerateRequest, HtmlSheetReviewRequest, HtmlSheetAcceptRequest,
                                    HtmlSheetReadRequest, HtmlSheetRetryRequest)
from html_asset_sheet_review import _candidate, _read, review_candidate, accept_candidate
from html_visual_routes import _get_db, _html_project
from html_visual_store import SCENE_DIR, HtmlVisualConflict
from pipeline_lifecycle import project_artifact_lock
from project_path_service import project_run_dir_or_500
import html_task_store as store

router = APIRouter()
_jobs = None


def configure_sheet_jobs(jobs):
    global _jobs
    _jobs = jobs


def _error(exc):
    if isinstance(exc, HtmlVisualConflict):
        return HTTPException(409, {'code': 'CONFLICT', 'message': str(exc), 'current_revision': exc.current})
    return HTTPException(getattr(exc, 'status_code', 400), {'code': getattr(exc, 'code', 'SHEET_ERROR'), 'message': str(exc)})


@router.post('/api/projects/{project_id}/html-asset-sheets/generate')
def sheet_generate(project_id: str, body: HtmlSheetGenerateRequest, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    if _jobs is None:
        raise HTTPException(503, '素材板任务服务尚未配置')
    try:
        task = _jobs.submit(db, project, body.plan)
    except (HtmlAssetSheetError, store.HtmlTaskError, ValueError) as exc:
        raise _error(exc) from exc
    return {'success': True, 'project_id': project_id, 'data': {'task': task}}


@router.get('/api/projects/{project_id}/html-asset-sheets')
def sheet_list(project_id: str, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    root = Path(project_run_dir_or_500(project)).resolve()
    candidates = []
    with project_artifact_lock(root):
        paths = list((root / SCENE_DIR / 'asset-sheets').glob('*/*/candidate.json'))
        for path in sorted(paths, key=lambda p: p.stat().st_mtime_ns)[-100:]:
            if not path.resolve().is_relative_to(root):
                continue
            try:
                seal = json.loads(path.read_text(encoding='utf-8'))
                candidates.append({'sheet_id': path.parent.parent.name, 'request_key': path.parent.name,
                                   'sealed': seal.get('request_key') == path.parent.name})
            except (OSError, ValueError):
                continue
    from database import LocalJob
    tasks = db.query(LocalJob).filter(LocalJob.project_id == project_id,
        LocalJob.job_type.in_(('html_asset_sheet_generate', 'html_asset_sheet_assess', 'html_asset_sheet_retry'))).order_by(LocalJob.updated_at.desc()).limit(20).all()
    task = next((j for j in tasks if j.status in store.ACTIVE_STATUSES), tasks[0] if tasks else None)
    return {'success': True, 'project_id': project_id,
            'data': {'candidates': candidates, 'task': store._job_to_dict(task) if task else None}}


@router.get('/api/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}')
def sheet_read(project_id: str, sheet_id: str, request_key: str, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    try:
        with project_artifact_lock(project.run_dir):
            _, directory, manifest = _candidate(project_run_dir_or_500(project), sheet_id, request_key)
            reviews = _read(directory / 'reviews.json', {'revision': 0, 'decisions': {}})
            accepted = _read(directory / 'accepted.json', {})
            from html_asset_sheet_assessment import read_advisory
            advisory = read_advisory(directory, manifest)
    except (HtmlAssetSheetError, ValueError) as exc:
        raise _error(exc) from exc
    return {'success': True, 'project_id': project_id, 'data': {**reviews, 'manifest': manifest, 'accepted': accepted, 'advisory': advisory}}


@router.post('/api/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/assess')
def sheet_assess(project_id: str, sheet_id: str, request_key: str,
                 body: HtmlSheetReadRequest, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    if _jobs is None:
        raise HTTPException(503, '素材板任务服务尚未配置')
    try:
        task = _jobs.submit_assess(db, project, sheet_id, request_key)
    except (HtmlAssetSheetError, store.HtmlTaskError, ValueError) as exc:
        raise _error(exc) from exc
    return {'success': True, 'project_id': project_id, 'data': {'task': task}}


@router.post('/api/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/{asset_id}/retry')
def sheet_retry(project_id: str, sheet_id: str, request_key: str, asset_id: str,
                body: HtmlSheetRetryRequest, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    if _jobs is None:
        raise HTTPException(503, '素材板任务服务尚未配置')
    try:
        task = _jobs.submit_retry(db, project, sheet_id, request_key, asset_id, **body.model_dump())
    except (HtmlAssetSheetError, HtmlVisualConflict, store.HtmlTaskError, ValueError) as exc:
        raise _error(exc) from exc
    return {'success': True, 'project_id': project_id, 'data': {'task': task}}


@router.put('/api/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/{asset_id}/review')
def sheet_review(project_id: str, sheet_id: str, request_key: str, asset_id: str,
                 body: HtmlSheetReviewRequest, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    try:
        result = review_candidate(project_run_dir_or_500(project), sheet_id, request_key, asset_id, **body.model_dump())
    except (HtmlAssetSheetError, HtmlVisualConflict, ValueError) as exc:
        raise _error(exc) from exc
    return {'success': True, 'project_id': project_id, 'data': result}


@router.post('/api/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/{asset_id}/accept')
def sheet_accept(project_id: str, sheet_id: str, request_key: str, asset_id: str,
                 body: HtmlSheetAcceptRequest, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    try:
        result = accept_candidate(project_run_dir_or_500(project), sheet_id, request_key, asset_id, **body.model_dump())
    except (HtmlAssetSheetError, HtmlVisualConflict, ValueError) as exc:
        raise _error(exc) from exc
    return {'success': True, 'project_id': project_id, 'data': result}


@router.get('/api/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/{asset_id}/image')
def sheet_image(project_id: str, sheet_id: str, request_key: str, asset_id: str, db=Depends(_get_db)):
    project = _html_project(project_id, db)
    try:
        with project_artifact_lock(project.run_dir):
            _, directory, manifest = _candidate(project_run_dir_or_500(project), sheet_id, request_key)
            if not any(a['id'] == asset_id for a in manifest['assets']):
                raise HTTPException(404, '素材候选不存在')
            path = directory / f'asset-{asset_id}.png'
    except HtmlAssetSheetError as exc:
        raise _error(exc) from exc
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store'})
