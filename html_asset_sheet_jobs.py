"""Persistent sheet jobs share the existing bounded HTML executor and store."""
import copy
from functools import partial
from pathlib import Path
import threading

from account_context import account_scope, get_current_account_id
from artifact_fingerprint import sha256_json
from html_asset_sheet import HtmlAssetSheetError, PROCESSOR_VERSION
from html_asset_sheet_generation import generate_sheet_candidates, validate_plan, PROMPT_VERSION
import html_task_store as store


class HtmlSheetJobs:
    def __init__(self, session_factory, executor, *, provider=None, freeze_models=None, segmenter=None, assessor=None):
        from html_image_provider import configured_image
        from project_model_binding_service import freeze_project_models
        self.session_factory, self.executor = session_factory, executor
        self.provider = provider or configured_image
        self.freeze = freeze_models or freeze_project_models
        self.segmenter = segmenter
        from html_asset_sheet_assessment import configured_vision
        self.assessor = assessor or configured_vision
        self.submit_lock = threading.Lock()

    def submit(self, db, project, plan):
        plan = copy.deepcopy(plan)
        validate_plan(plan)
        if any(s['method'] == 'mask' for s in plan['slots']) and self.segmenter is None:
            raise HtmlAssetSheetError('SHEET_SEGMENTER_REQUIRED', '准确分割服务尚未配置，请选择透明底或纯色背景处理')
        frozen = self.freeze(project, required=('image',))
        summary = frozen.image.summary()
        account = get_current_account_id()
        key = sha256_json({'plan': plan, 'model': summary, 'prompt_version': PROMPT_VERSION,
                          'processor_version': PROCESSOR_VERSION})
        with self.submit_lock:
            task = store.submit_task(db, project_id=project.id, task_type='html_asset_sheet_generate',
                submission_key=key, payload={'plan': plan, 'model_summary': summary, 'account_id': account})
            if not task['reused'] or task.get('retried'):
                self.executor.submit(self.run, task['id'], project.id, Path(project.run_dir), plan,
                                     account, task['attempt'], frozen.image)
        return task

    def submit_assess(self, db, project, sheet_id, request_key):
        from html_asset_sheet_review import _candidate
        from pipeline_lifecycle import project_artifact_lock
        with project_artifact_lock(project.run_dir):
            _, _, manifest = _candidate(project.run_dir, sheet_id, request_key)
            if not manifest['assets']:
                raise HtmlAssetSheetError('SHEET_EMPTY', '没有可供审阅的有效候选，请重试失败对象')
        frozen = self.freeze(project, required=('text',)).text
        return self._submit_action(db, project, 'assess', {'sheet_id': sheet_id, 'request_key': request_key}, frozen)

    def submit_retry(self, db, project, sheet_id, request_key, asset_id, **options):
        from html_asset_sheet_retry import prepare_retry
        target = {'sheet_id': sheet_id, 'request_key': request_key, 'asset_id': asset_id, **options}
        plan, _ = prepare_retry(project.run_dir, **target)
        if plan['slots'][0]['method'] == 'mask' and self.segmenter is None:
            raise HtmlAssetSheetError('SHEET_SEGMENTER_REQUIRED', '准确分割服务尚未配置')
        frozen = self.freeze(project, required=('image',)).image
        return self._submit_action(db, project, 'retry', target, frozen)

    def _submit_action(self, db, project, action, target, frozen):
        target = copy.deepcopy(target)
        from html_asset_sheet_assessment import PROMPT_VERSION as assess_version
        from html_asset_sheet_retry import PROMPT_VERSION as retry_version
        summary = frozen.summary()
        account = get_current_account_id()
        key = sha256_json({'action': action, 'target': target, 'model': summary,
            'prompt_version': assess_version if action == 'assess' else retry_version,
            'processor_version': PROCESSOR_VERSION, 'generation_prompt_version': PROMPT_VERSION})
        with self.submit_lock:
            task = store.submit_task(db, project_id=project.id, task_type='html_asset_sheet_' + action,
                submission_key=key, payload={'target': target, 'model_summary': summary, 'account_id': account})
            if not task['reused'] or task.get('retried'):
                self.executor.submit(self.run_action, task['id'], project.id, Path(project.run_dir),
                    action, target, account, task['attempt'], frozen)
        return task

    def run_action(self, job_id, project_id, run_dir, action, target, account, attempt, frozen):
        from html_asset_sheet_assessment import assess_candidates, configured_vision
        from html_asset_sheet_retry import prepare_retry, PROMPT_VERSION as retry_prompt_version
        db = self.session_factory()
        try:
            with account_scope(account):
                store.mark_running(db, job_id, expected_attempt=attempt)
                def checkpoint():
                    job = store._job(db, job_id, attempt)
                    if job.project_id != project_id or job.status != 'running':
                        raise store.HtmlTaskError('任务已停止，已有候选保留')
                    from project_path_service import project_or_404
                    project_or_404(db, project_id)
                    if action == 'retry':
                        prepare_retry(run_dir, **target)
                checkpoint()
                if action == 'assess':
                    provider = partial(self.assessor, model_binding=frozen)
                    if self.assessor is configured_vision:
                        provider = partial(provider, checkpoint=checkpoint)
                    advisory = assess_candidates(run_dir, target['sheet_id'], target['request_key'],
                        provider=provider, model_hash=frozen.config_hash,
                        checkpoint=checkpoint)
                    result = {'sheet_id': target['sheet_id'], 'request_key': target['request_key'],
                              'assessment_key': advisory['assessment_key']}
                else:
                    plan, reference = prepare_retry(run_dir, **target)
                    original_provider = partial(self.provider, model_binding=frozen, reference_paths=[str(reference)])
                    def retry_provider(prompt, **kwargs):
                        return original_provider(f'PromptVersion: {retry_prompt_version}。参考图片中只重新生成需求指定的一个主体，保留其身份和画风；排除其他对象和装饰。' + prompt, **kwargs)
                    result = generate_sheet_candidates(plan, run_dir=run_dir, provider=retry_provider,
                        model_config_hash=frozen.config_hash, segmenter=self.segmenter, checkpoint=checkpoint)
                    result['retry_parent'] = target
                checkpoint()
                store.mark_succeeded(db, job_id, result, expected_attempt=attempt)
        except Exception as exc:
            db.rollback()
            from html_visual_store import HtmlVisualConflict
            message = str(exc) if isinstance(exc, (HtmlAssetSheetError, store.HtmlTaskError, HtmlVisualConflict)) else '素材板处理失败，请检查服务连接或重试'
            if frozen.api_key:
                message = message.replace(frozen.api_key, '[REDACTED]')
            store.mark_failed(db, job_id, message, expected_attempt=attempt)
        finally:
            db.close()

    def run(self, job_id, project_id, run_dir, plan, account, attempt, frozen):
        db = self.session_factory()
        try:
            with account_scope(account):
                store.mark_running(db, job_id, expected_attempt=attempt)
                def checkpoint():
                    job = store._job(db, job_id, attempt)
                    if job.project_id != project_id or job.status != 'running':
                        raise store.HtmlTaskError('任务已停止，源图或候选保留')
                    from project_path_service import project_or_404
                    project_or_404(db, project_id)
                result = generate_sheet_candidates(plan, run_dir=run_dir,
                    provider=partial(self.provider, model_binding=frozen), model_config_hash=frozen.config_hash,
                    segmenter=self.segmenter, checkpoint=checkpoint)
                checkpoint()
                store.mark_succeeded(db, job_id, result, expected_attempt=attempt)
        except Exception as exc:
            db.rollback()
            message = str(exc) if isinstance(exc, (HtmlAssetSheetError, store.HtmlTaskError)) else '素材板生成失败，请检查服务连接或重试'
            if frozen.api_key:
                message = message.replace(frozen.api_key, '[REDACTED]')
            store.mark_failed(db, job_id, message, expected_attempt=attempt)
        finally:
            db.close()
