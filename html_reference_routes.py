"""Thin account/project/page adapters for explicit reference correction."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from html_reference_models import ReferenceCorrection
from html_reference_service import inspect_session
from project_path_service import project_run_dir_or_500

router=APIRouter()


def _get_db():
    from html_visual_review_routes import _get_db as original
    yield from original()


@router.get('/api/projects/{project_id}/html-review/{slide_id}/reusable-assets')
def reusable_assets(project_id:str,slide_id:str,db:Any=Depends(_get_db)):
    from html_visual_review_routes import _html_project, _contract_slide
    from html_asset_reuse import available
    project=_html_project(project_id,db)
    run=project_run_dir_or_500(project)
    _contract_slide(run,slide_id)
    return {'success':True,'assets':available(run)}


def packet(project_id,slide_id,job_id,db):
    from html_visual_review_routes import _html_project, _task, _service_deps, _contract_slide
    project=_html_project(project_id,db)
    run=project_run_dir_or_500(project)
    _contract_slide(run,slide_id)
    try:return project,inspect_session(_task(project_id,job_id,db),run,slide_id,_service_deps().repo_root)
    except ValueError as error:raise HTTPException(getattr(error,'status_code',409),str(error)) from None


@router.get('/api/projects/{project_id}/html-review/{slide_id}/reference/{job_id}')
def reference_read(project_id:str,slide_id:str,job_id:str,db:Any=Depends(_get_db)):
    project,value=packet(project_id,slide_id,job_id,db)
    from database import LocalJob
    tasks=db.query(LocalJob).filter(LocalJob.project_id==project_id,LocalJob.job_type=='html_reference_review').order_by(LocalJob.created_at.desc()).all()
    from html_task_store import _job_to_dict
    latest=next((j for j in tasks if j.get_payload().get('input',{}).get('original_task_id')==job_id),None)
    design_key=None
    from html_visual_review_routes import _task
    snapshot=_task(project_id,job_id,db).get_payload().get('input',{}).get('snapshot_id')
    if snapshot:
        from html_build_snapshot import safe_file,verify_snapshot
        import json
        try:
            folder=safe_file(project.run_dir,'planning/html_visual/builds/'+snapshot)
            verify_snapshot(folder)
            design_key=json.loads((folder/'input/options.json').read_text(encoding='utf-8')).get('design_candidate_key')
        except (ValueError,OSError,KeyError):pass
    base=f'/api/projects/{project_id}/html-review/{slide_id}/reference/{job_id}'
    return {'success':True,'reference':{'key':value['key'],'correction':value['correction'],
        'unresolved_targets':[r['targetId'] for r in value['correction']['mapping']['targets'] if r['status']!='located'],
        'workbench_url':base+'/workbench','task':_job_to_dict(latest) if latest else None,
        'continuation_design_key':design_key,
        'author_saved':False,'human_approval':'pending'}}


@router.get('/api/projects/{project_id}/html-review/{slide_id}/reference/{job_id}/workbench')
def reference_workbench(project_id:str,slide_id:str,job_id:str,db:Any=Depends(_get_db)):
    _,value=packet(project_id,slide_id,job_id,db)
    return FileResponse(value['folder']/'index.html',media_type='text/html',headers={
        'Cache-Control':'no-store','Content-Security-Policy':"sandbox allow-scripts allow-downloads; default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})


@router.post('/api/projects/{project_id}/html-review/{slide_id}/reference/{job_id}/resume')
def reference_resume(project_id:str,slide_id:str,job_id:str,payload:ReferenceCorrection,db:Any=Depends(_get_db)):
    project,_=packet(project_id,slide_id,job_id,db)
    from html_visual_review_routes import _jobs, _task
    if _jobs is None:raise HTTPException(503,'生产任务服务未配置')
    try:
        task=_jobs.reference_reviews.submit(db,project,slide_id,_task(project_id,job_id,db),payload.model_dump())
        return {'success':True,'task':task}
    except ValueError as error:raise HTTPException(getattr(error,'status_code',409),str(error)) from None
