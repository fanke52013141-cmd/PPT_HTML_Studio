"""Bounded persistent HTML production executor shared by Web and Agent."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import partial
from pathlib import Path
import threading

from account_context import account_scope, get_current_account_id
from artifact_fingerprint import sha256_json
from html_production_service import produce_scene
from html_visual_store import load_scene_with_revision
import html_task_store as store


class HtmlWorkflowJobs:
    def __init__(self, session_factory, deps, provider=None, executor=None, freeze_models=None):
        self.session_factory, self.deps, self.provider = session_factory, deps, provider
        self.executor = executor or ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="html-production"
        )
        self.submit_lock = threading.Lock()
        # Existing injected provider/generator fixtures need no real settings.
        # The production composition root passes this exact configured provider.
        from html_image_provider import configured_image
        from project_model_binding_service import freeze_project_models
        self.freeze_models = freeze_models or (
            freeze_project_models if provider is configured_image else None
        )

    def submit(self, db, project, contract):
        from html_input_manifest import _hash

        root = self.deps.repo_root / "html_engine/visual"
        definition_files = [
            root / "preview/player.js",
            root / "generated/catalog.json",
            root / "effects/registry.json",
        ]
        definition_files += (
            sorted((root / "themes").glob("*.json"))
            + sorted((root / "layouts").glob("*.json"))
            + sorted((root / "templates").glob("*.json"))
        )
        current = load_scene_with_revision(project.run_dir, contract["slide_id"])
        frozen = self.freeze_models(project) if self.freeze_models is not None else None
        model_summary = frozen.summary() if frozen is not None else {"source": "injected"}
        key = sha256_json(
            {
                "contract": contract,
                "model_summary": model_summary,
                "scene_hash": current["sha256"] if current else None,
                "definitions": {
                    str(p.relative_to(root)): _hash(p) for p in definition_files
                },
            }
        )
        with self.submit_lock:
            task = store.submit_task(
                db,
                project_id=project.id,
                task_type="html_plan_generate",
                submission_key=key,
                payload={
                    "slide_id": contract["slide_id"],
                    "account_id": get_current_account_id(),
                    "model_summary": model_summary,
                },
            )
            if not task["reused"] or task.get("retried"):
                self.executor.submit(
                    self.run,
                    task["id"],
                    project.id,
                    Path(project.run_dir),
                    contract,
                    get_current_account_id(),
                    task["attempt"],
                    frozen,
                )
        return task

    def run(self, job_id, project_id, run_dir, contract, account_id, attempt=None, frozen=None):
        db = self.session_factory()
        try:
            with account_scope(account_id):
                store.mark_running(db, job_id, expected_attempt=attempt)

                def checkpoint():
                    from database import LocalJob

                    db.expire_all()
                    job = db.query(LocalJob).filter(LocalJob.id == job_id).first()
                    if (
                        not job
                        or job.status != "running"
                        or (
                            attempt is not None
                            and int(job.get_payload().get("attempt", 1)) != attempt
                        )
                    ):
                        raise store.HtmlTaskError("任务已停止；候选产物保留")

                deps, provider = self.deps, self.provider
                extra = {}
                if frozen is not None:
                    deps = replace(self.deps, json_generator=partial(
                        self.deps.json_generator, model_binding=frozen.text,
                    ))
                    provider = partial(self.provider, model_binding=frozen.image)
                    extra["model_summary"] = frozen.summary()
                result = produce_scene(
                    contract,
                    run_dir=run_dir,
                    deps=deps,
                    provider=provider,
                    checkpoint=checkpoint,
                    **extra,
                )
                checkpoint()
                from project_path_service import project_or_404
                from invalidation_service import html_scene_changed

                project = project_or_404(db, project_id)
                if result["saved"]["changed"]:
                    html_scene_changed(project, [contract["slide_id"]])
                    db.commit()
                store.mark_succeeded(db, job_id, result, expected_attempt=attempt)
        except Exception as exc:
            db.rollback()
            message = str(exc)
            if frozen is not None:
                for model in (frozen.text, frozen.image):
                    if model.api_key:
                        message = message.replace(model.api_key, "[REDACTED]")
                # SDK failures may contain encoded headers or secret fragments.
                if not isinstance(exc, (store.HtmlTaskError, ValueError)):
                    message = "HTML 生成失败，请检查模型连接、服务状态或重试。"
            store.mark_failed(db, job_id, message, expected_attempt=attempt)
        finally:
            db.close()

    def recover(self):
        db = self.session_factory()
        try:
            return store.recover_interrupted(db)
        finally:
            db.close()
