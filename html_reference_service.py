"""Project/page/task-bound reference sessions; no directory guessing or author writes."""
import json
from pathlib import Path
from artifact_fingerprint import sha256_file, sha256_json
from html_build_snapshot import safe_file
from html_reference_workbench import _source
from html_reference_localization import mapped_reference_targets, validate_mapped_locations
from html_visual_review_service import HtmlReviewError


def inspect_session(job, run_dir, slide, repo):
    run=Path(run_dir).resolve()
    payload=job.get_payload()
    if (job.job_type!='html_plan_generate' or job.status not in ('failed','interrupted')
        or payload.get('input',{}).get('slide_id')!=slide):
        raise HtmlReviewError('原任务或页面不匹配',code='REFERENCE_TASK_UNAVAILABLE',status_code=409)
    if any(r.get('state') in ('intent','unknown') for r in payload.get('production_stages',{}).values()):
        raise HtmlReviewError('原供应商请求结果待核实',code='REFERENCE_PROVIDER_UNVERIFIED',status_code=409)
    ref=payload.get('progress',{}).get('reference_workbench')
    if not ref:
        raise HtmlReviewError('该任务没有定位复核资料',code='REFERENCE_NOT_FOUND',status_code=404)
    try:
        contract=json.loads((run/'planning/visual_contract.json').read_text(encoding='utf-8'))
        page_contract=next((s for s in contract.get('slides',[]) if s.get('slide_id')==slide),None)
        if not page_contract or sha256_json(page_contract)!=payload.get('input',{}).get('contract_sha256'):
            raise ValueError('contract')
        page=safe_file(run,ref['path'].replace('\\','/'))
        if page.name!='index.html':raise ValueError('path')
        folder=page.parent
        session=json.loads((folder/'session.json').read_text(encoding='utf-8'))
        if sha256_json(session)!=ref['session_sha256'] or session['scene']['id']!=slide:
            raise ValueError('identity')
        if _source(session['scene'],run,repo,session.get('resource_snapshot'))!=session['source']:
            raise ValueError('source')
        for path,digest in ((folder/'reference.png',session['reference_sha256']),
                            (folder/'current.png',session['screenshot_sha256']),
                            (safe_file(run,session['original_reference'].replace('\\','/')),session['reference_sha256'])):
            if sha256_file(path)!=digest:raise ValueError('image')
    except (KeyError,ValueError,OSError) as exc:
        raise HtmlReviewError('定位复核来源已变化',code='REFERENCE_SOURCE_STALE',status_code=409) from exc
    keys=('targetId','status','container_presence','container_box','identity_evidence','part_regions')
    correction={'session_sha256':ref['session_sha256'],'mapping':{'targets':[
        {k:row[k] for k in keys} for row in session['localization']['result']['targets']]}}
    return {'folder':folder,'session':session,'correction':correction,'key':ref['session_sha256']}


def validate_correction(packet, correction):
    from html_reference_models import ReferenceCorrection
    value=ReferenceCorrection.model_validate(correction).model_dump()
    if value['session_sha256']!=packet['key']:
        raise HtmlReviewError('修正文件属于其他会话',code='REFERENCE_SESSION_MISMATCH',status_code=409)
    session=packet['session']
    ids={row['targetId'] for row in session['localization']['result']['targets']}
    targets=[t for t in mapped_reference_targets(session['scene']) if t['targetId'] in ids]
    validate_mapped_locations(value['mapping'],targets,session['localization']['image_size'])
    return value
