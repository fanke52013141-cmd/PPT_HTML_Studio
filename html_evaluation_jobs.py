"""Paired experiment jobs reuse the production executor/store, never author save."""
from pathlib import Path
from account_context import account_scope,get_current_account_id
from artifact_fingerprint import sha256_json
from html_evaluation_execution import freeze,execute,completed_result
from html_annotation_store import read,sealed_dataset
from html_paired_evaluation import checked
from html_reference_localization import mapped_reference_targets
from html_acceptance_criteria import safe
import html_task_store as store


class EvaluationJobs:
    def __init__(self,owner):self.owner=owner

    def submit(self,db,project,command):
        from database import LocalJob
        owner=self.owner
        frozen=owner.freeze_models(project,required=('text','planning')) if owner.freeze_models else None
        models={arm:(getattr(frozen,command[arm]['model_role']) or frozen.text) if frozen else None for arm in ('before','after')}
        for model in models.values():
            if model:
                model.require_ready()
                if model.supports_images is not True:raise ValueError('EXPERIMENT_VISUAL_MODEL_REQUIRED')
        with owner.submit_lock:
            key,folder,identity=freeze(project.run_dir,command,owner.deps.repo_root,models)
            expected_data=identity['dataset']
            if not (folder/'frozen.json').exists():raise ValueError('EXPERIMENT_SNAPSHOT_MISSING')
            if sealed_dataset(project.run_dir,command['dataset_id'])[1]!=expected_data:raise ValueError('EXPERIMENT_DATASET_CHANGED')
            def requests(data,root):
                return {case['id']:sha256_json({'reference':case['reference']['sha256'],
                    'targets':mapped_reference_targets(read(checked(root,case['scene'])))}) for case in data['cases']}
            current_requests=set(requests(identity['dataset'],folder/'dataset').values())
            total=len(identity['dataset']['cases'])*2*command['repetitions']
            if total>command['max_model_calls']:raise ValueError('EXPERIMENT_PAIR_BUDGET_TOO_SMALL')
            jobs=db.query(LocalJob).filter(LocalJob.project_id==project.id,LocalJob.job_type=='html_paired_experiment').order_by(LocalJob.created_at.desc()).all()
            for job in jobs:
                payload=job.get_payload();old=payload.get('input',{})
                if payload.get('submission_key')==key:
                    receipt=folder/'result-receipt.json'
                    if job.status in ('failed','interrupted') and receipt.is_file():
                        result=completed_result(folder,identity,owner.deps.repo_root)
                        if not result['stopped']:
                            store._transition(db,job,('failed','interrupted'),{'status':'running'})
                            return {**store.mark_succeeded(db,job.id,{'stage':'paired_evaluation','experiment_key':key,**result}),'reused':True}
                    return {**store._job_to_dict(job),'reused':True}
                previous=safe(project.run_dir,old['experiment_path'])
                http=read(previous/'http.json') if (previous/'http.json').exists() else []
                unknown=[r for r in http if r['state'] in ('intent','unknown')]
                if unknown:
                    previous_identity=read(previous/'frozen.json');previous_requests=requests(previous_identity['dataset'],previous/'dataset')
                    previous_trials=read(previous/'trials.json')['trials']
                    if any(previous_requests[previous_trials[r['trial']]['case_id']] in current_requests for r in unknown):
                        raise ValueError('EXPERIMENT_PRIOR_OUTCOME_UNKNOWN')
            task=store.submit_task(db,project_id=project.id,task_type='html_paired_experiment',submission_key=key,
                payload={'dataset_id':command['dataset_id'],'dataset_sha256':sha256_json(identity['dataset']),
                    'experiment_key':key,'experiment_path':folder.relative_to(Path(project.run_dir).resolve()).as_posix(),
                    'model_summary':identity['models']})
            owner.executor.submit(self.run,task['id'],project.id,project.run_dir,key,folder,identity,models,get_current_account_id(),task['attempt'])
            return task

    def run(self,job_id,project_id,run,key,folder,identity,models,account,attempt):
        db=self.owner.session_factory()
        try:
            with account_scope(account):
                store.mark_running(db,job_id,expected_attempt=attempt)
                def checkpoint():
                    db.expire_all();job=store._job(db,job_id,attempt)
                    if job.status!='running':raise store.HtmlTaskError('实验任务已停止',409)
                    _,current=sealed_dataset(run,identity['options']['dataset_id'])
                    if current!=identity['dataset']:raise ValueError('EXPERIMENT_DATASET_CHANGED')
                checkpoint()
                result=execute(folder,identity,repo=self.owner.deps.repo_root,generator=self.owner.deps.json_generator,
                    models=models,checkpoint=checkpoint,
                    progress=lambda value:store.record_progress(db,job_id,{'experiment':value},attempt))
                checkpoint()
                if result['stopped']:
                    store.record_progress(db,job_id,{'comparison':result['comparison'],'experiment_key':key,
                        'next_action':{'reason':'paired_experiment_stopped','routes':['provider_verification'],'automatic_retry':False}},attempt)
                    store.mark_failed(db,job_id,'实验未完整结束；结果和未执行分母已保留，不自动重发。',expected_attempt=attempt)
                else:store.mark_succeeded(db,job_id,{'stage':'paired_evaluation','experiment_key':key,**result},expected_attempt=attempt)
        except Exception:
            db.rollback();store.mark_failed(db,job_id,'实验停止；请核对来源、预算与原请求回执，不自动重发。',expected_attempt=attempt)
        finally:db.close()
