"""Account/project adapters for dataset annotation and original persistent jobs."""
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import HTMLResponse
from html_evaluation_models import EvaluationCommand
from html_annotation_store import directory,case_view,save_labels,review_labels,create_dataset,read
from project_path_service import project_run_dir_or_500
from html_acceptance_criteria import safe

router=APIRouter()

def _db():
    from html_visual_review_routes import _get_db
    yield from _get_db()

def project_packet(project_id,db):
    from html_visual_review_routes import _html_project,_service_deps
    project=_html_project(project_id,db)
    return project,project_run_dir_or_500(project),_service_deps()


def overview(project_id,db):
    project,run,deps=project_packet(project_id,db)
    base=Path(run)/'planning/html_visual/evaluation/datasets'
    datasets=[]
    for file in sorted(base.glob('*/dataset.json'))[:200]:
        try:
            folder=directory(run,file.parent.name);data=read(safe(folder,'dataset.json'))
            datasets.append({'id':file.parent.name,'cases':[{'id':c['id'],'course_id':c['course_id'],'split':c['split']} for c in data['cases']]})
        except (ValueError,OSError,KeyError):continue
    from html_visual_store import scene_path
    contract=read(Path(run)/'planning/visual_contract.json')
    pages=[{'slide_id':p['slide_id'],'title':p.get('title',p['slide_id'])} for p in contract.get('slides',[]) if scene_path(run,p['slide_id']).is_file()]
    from database import LocalJob
    from html_task_store import _job_to_dict
    tasks=db.query(LocalJob).filter(LocalJob.project_id==project_id,LocalJob.job_type=='html_paired_experiment').order_by(LocalJob.created_at.desc()).limit(10).all()
    return {'datasets':datasets,'pages':pages,'protocols':['0.5.0','0.5.1'],'tasks':[_job_to_dict(j) for j in tasks]}


def command(project_id,payload,db):
    project,run,deps=project_packet(project_id,db);body=payload.command.model_dump(mode='json');action=body['action']
    try:
        if action=='create_dataset':return {'dataset':create_dataset(run,body,deps.repo_root)}
        if action=='save_labels':return {'annotation':save_labels(run,body)}
        if action=='review_labels':return {'annotation':review_labels(run,body)}
        if action=='read_case':
            packet=case_view(run,body['dataset_id'],body['case_id'])
            versions=packet['annotation_dir']/'annotation-versions'
            history=[]
            for file in sorted((p for p in versions.glob('*.json') if p.stem.isdigit()),key=lambda p:int(p.stem))[-200:]:
                state=read(safe(packet['folder'],file.relative_to(packet['folder']).as_posix()));history.append({k:state.get(k) for k in ('revision','status','annotator','review')})
            return {'annotation':packet['state'],'case':packet['case'],'history':history,
                'workbench_url':f'/api/projects/{project_id}/html-evaluation/{body["dataset_id"]}/{body["case_id"]}/workbench'}
        if action=='start_experiment':
            from html_visual_review_routes import _jobs
            if _jobs is None:raise HTTPException(503,'实验执行器未配置')
            return {'task':_jobs.evaluations.submit(db,project,body)}
    except (ValueError,OSError,KeyError) as error:
        messages={'ANNOTATION_REVISION_OR_SOURCE_CONFLICT':'标注版本或原图已变化，请重新打开样本。',
            'ANNOTATION_UNRESOLVED':'请补齐尚不确定的对象或容器，再提交复核。',
            'ANNOTATION_TEXT_INCOMPLETE':'请补齐全部文字部件及身份依据，再提交复核。',
            'INDEPENDENT_REVIEWER_REQUIRED':'复核者须与标注者不同，请填写独立复核者。',
            'DATASET_HAS_UNREVIEWED_DRAFTS':'请先独立复核数据集中的全部样本。',
            'EXPERIMENT_PRIOR_OUTCOME_UNKNOWN':'旧实验有请求结果待核实，不能换配置重复提交。',
            'EXPERIMENT_VISUAL_MODEL_REQUIRED':'实验所选项目模型必须明确支持图像。',
            'CURRENT_DESIGN_REQUIRED':'请先确认当前设计；旧设计过期时可沿原图复用入口刷新。',
            'EXPERIMENT_PAIR_BUDGET_TOO_SMALL':'调用额度不足以覆盖完整配对，请增加额度或减少样本/重复次数。'}
        raise HTTPException(409,messages.get(str(error),'评测操作未完成：'+(str(error) if isinstance(error,ValueError) else type(error).__name__))) from None
    raise HTTPException(400,'不支持的评测操作')


@router.get('/api/projects/{project_id}/html-evaluation')
def evaluation_read(project_id:str,db=Depends(_db)):
    return {'success':True,'evaluation':overview(project_id,db)}

@router.post('/api/projects/{project_id}/html-evaluation/action')
def evaluation_action(project_id:str,payload:EvaluationCommand,db=Depends(_db)):
    return {'success':True,'evaluation':command(project_id,payload,db)}

@router.get('/api/projects/{project_id}/html-evaluation/{dataset_id}/{case_id}/workbench')
def workbench(project_id:str,dataset_id:str,case_id:str,db=Depends(_db)):
    _,run,_=project_packet(project_id,db)
    try:packet=case_view(run,dataset_id,case_id)
    except (ValueError,OSError,KeyError):raise HTTPException(409,'标注来源或版本不可用') from None
    from html_reference_workbench_ui import render_workbench
    body=render_workbench(packet['reference'],packet['reference'],{'session_sha256':packet['state']['source_sha256'],
        'mapping':packet['state']['mapping']},packet['image_size'],packet['targets'],annotation_mode=True)
    return HTMLResponse(body,headers={'Cache-Control':'no-store','Content-Security-Policy':
        "sandbox allow-scripts allow-downloads; default-src 'none'; img-src data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})
