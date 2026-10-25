"""Explicit reference re-review using the existing persistent worker and task store."""
from dataclasses import replace
from functools import partial
from pathlib import Path

from account_context import account_scope, get_current_account_id
from artifact_fingerprint import sha256_json
from artifact_fingerprint import sha256_file
import json
from html_reference_service import inspect_session, validate_correction
from html_reference_workbench import resume_review
from pipeline_lifecycle import write_json_atomic
import html_task_store as store


class ReferenceReviewJobs:
    def __init__(self, owner):
        self.owner=owner

    def submit(self, db, project, slide, original, correction):
        from database import LocalJob
        owner=self.owner
        packet=inspect_session(original,project.run_dir,slide,owner.deps.repo_root)
        correction=validate_correction(packet,correction)
        frozen=owner.freeze_models(project,required=('text',)) if owner.freeze_models else None
        identity=frozen.text.summary() if frozen else {'source':'injected'}
        key=sha256_json({'original':original.id,'correction':correction,'model':identity})
        with owner.submit_lock:
            # No automatic retries for any prior dispatch with this exact identity.
            jobs=db.query(LocalJob).filter(LocalJob.project_id==project.id,
                LocalJob.job_type=='html_reference_review').all()
            for job in jobs:
                if job.get_payload().get('submission_key')==key:
                    if job.status in ('failed','interrupted'):
                        replay_identity={'correction_sha256':sha256_json(correction),'execution_mode':'configured_transport',
                                         'execution_identity':sha256_json(identity)}
                        folder=packet['folder']/'replays'/sha256_json(replay_identity)
                        try:
                            receipt=json.loads((folder/'attempt.json').read_text(encoding='utf-8'))
                            result_path=folder/'completed.json'
                            if (receipt.get('state')=='completed' and receipt.get('identity')==replay_identity
                                and receipt.get('key')==sha256_json(replay_identity)
                                and sha256_file(result_path)==receipt.get('result_sha256')):
                                result=json.loads(result_path.read_text(encoding='utf-8'))
                                from html_reference_publication import publish
                                review_key=publish(packet,result,project.run_dir) if result['result']['status']=='pass' else None
                                store._transition(db,job,('failed','interrupted'),{'status':'running'})
                                return {**store.mark_succeeded(db,job.id,{'stage':'reference_review','review':result,
                                    'original_task_id':original.id,'reference_review_key':review_key,
                                    'author_saved':False,'human_approval':'pending'}),'reused':True}
                        except (ValueError,OSError):pass
                    return {**store._job_to_dict(job),'reused':True}
                previous=job.get_payload().get('input',{})
                if (previous.get('original_task_id')==original.id and previous.get('correction_sha256')==sha256_json(correction)
                    and job.status!='succeeded'):
                    raise store.HtmlTaskError('同一修正的旧请求尚未确认，不能换模型重发',409)
            path=packet['folder']/'submissions'/f'{key}.json'
            write_json_atomic(path,correction)
            task=store.submit_task(db,project_id=project.id,task_type='html_reference_review',submission_key=key,
                payload={'slide_id':slide,'original_task_id':original.id,'session_key':packet['key'],
                         'correction_file':path.relative_to(Path(project.run_dir).resolve()).as_posix(),
                         'source_revision':original.get_payload()['input']['source_revision'],'model_summary':identity,
                         'correction_sha256':sha256_json(correction)})
            owner.executor.submit(self.run,task['id'],project.id,project.run_dir,slide,original.id,path,
                                  get_current_account_id(),task['attempt'],frozen)
            return task

    def run(self, job_id, project_id, run, slide, original_id, path, account, attempt, frozen):
        db=self.owner.session_factory()
        try:
            with account_scope(account):
                store.mark_running(db,job_id,expected_attempt=attempt)
                def checkpoint():
                    db.expire_all()
                    job=store._job(db,job_id,attempt)
                    if job.status!='running':raise store.HtmlTaskError('复核任务已停止',409)
                    original=store._job(db,original_id)
                    inspect_session(original,run,slide,self.owner.deps.repo_root)
                checkpoint()
                deps=self.owner.deps
                if frozen:
                    deps=replace(deps,json_generator=partial(deps.json_generator,model_binding=frozen.text))
                job=store._job(db,job_id,attempt)
                identity=sha256_json(job.get_payload()['input']['model_summary'])
                packet=inspect_session(store._job(db,original_id),run,slide,deps.repo_root)
                store.record_progress(db,job_id,{'next_action':{'reason':'reference_review','routes':['evidence_review']}},attempt)
                result=resume_review(packet['folder'],path,run_dir=run,deps=deps,checkpoint=checkpoint,
                                     execution_identity=identity)
                checkpoint()
                from html_reference_publication import publish
                review_key=publish(packet,result,run) if result['result']['status']=='pass' else None
                store.mark_succeeded(db,job_id,{'stage':'reference_review','review':result,
                    'reference_review_key':review_key,'original_task_id':original_id,
                    'author_saved':False,'human_approval':'pending'},expected_attempt=attempt)
        except Exception as error:
            db.rollback()
            message=str(error)
            if frozen and frozen.text.api_key:message=message.replace(frozen.text.api_key,'[REDACTED]')
            if not isinstance(error,ValueError):message='复核未完成；请核对原请求及回执，不自动重发。'
            store.mark_failed(db,job_id,message,expected_attempt=attempt)
        finally:db.close()
