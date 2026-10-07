"""Bounded persistent HTML production executor shared by Web and Agent."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

from account_context import account_scope, get_current_account_id
from artifact_fingerprint import sha256_json
from html_production_service import produce_scene
from html_visual_store import load_scene_with_revision
import html_task_store as store


class HtmlWorkflowJobs:
    def __init__(self, session_factory, deps, provider=None, executor=None):
        self.session_factory, self.deps, self.provider = session_factory, deps, provider
        self.executor = executor or ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="html-production"
        )
        self.submit_lock = threading.Lock()

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
        key = sha256_json(
            {
                "contract": contract,
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
                )
        return task

    def run(self, job_id, project_id, run_dir, contract, account_id, attempt=None):
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

                result = produce_scene(
                    contract,
                    run_dir=run_dir,
                    deps=self.deps,
                    provider=self.provider,
                    checkpoint=checkpoint,
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
            store.mark_failed(db, job_id, str(exc), expected_attempt=attempt)
        finally:
            db.close()

    def recover(self):
        db = self.session_factory()
        try:
            return store.recover_interrupted(db)
        finally:
            db.close()
