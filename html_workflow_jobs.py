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

# Historical candidate identity from before the explicit unknown-result
# experiment path. The source bytes are pinned by Git; this hash is used only
# when the complete candidate definition digest also matches.
LEGACY_DESIGN_CANDIDATES_SHA256 = "05ee4141c548bf5839da44ba16fa7b1a683bf4653d4042cfba2d533ceaf9fc1f"


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

    def submit(self, db, project, contract, options=None, *, expected_snapshot=None):
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
        from html_visual_store import _read_revision
        from html_production_models import HtmlProduceRequest
        from html_design_candidates import definition_identity
        options = HtmlProduceRequest.model_validate(options or {}).model_dump()
        frozen = self.freeze_models(project) if self.freeze_models is not None else None
        model_summary = frozen.summary() if frozen is not None else {"source": "injected"}
        definition_override = None
        if options.get("prior_unknown_task_id"):
            definition_override = self._verify_prior_unknown(db, project, contract, options, model_summary)
        # Reconcile before building a new revision-dependent submission key.
        # Otherwise an already-saved page would be generated again as a new job.
        recovered = self.reconcile_project(db, project, contract, options, model_summary)
        if recovered is not None:
            return {**recovered, "reused": True, "reconciled": True}
        if frozen is not None:
            frozen.text.require_ready()
            (frozen.planning or frozen.text).require_ready()
            if not options.get("reuse_design_candidate_key") and (not options.get("design_candidate_key") or options.get("design_instruction", "").strip()):
                frozen.image.require_ready()  # Every new page requires a full design reference.
        from html_build_snapshot import create_generation_snapshot
        snapshot = create_generation_snapshot(
            project.run_dir, contract, repo_root=self.deps.repo_root,
            expected_revision=_read_revision(project.run_dir)["revision"], options=options,
            model_identity={name: {"provider": part.get("provider"), "model": part.get("model"),
                                  "config_digest": part.get("config_hash")}
                            for name in ("text", "image", "planning") if (part := model_summary.get(name))},
        )
        if expected_snapshot is not None and snapshot["snapshot_id"] != expected_snapshot:
            raise store.HtmlTaskError("原任务代码、模型或依赖已变化；不能作为原请求继续", 409)
        key = sha256_json(
            {
                "contract": contract,
                "snapshot_id": snapshot["snapshot_id"],
                "options": options,
                "visual_reference_definitions": definition_identity(self.deps.repo_root),
                "model_summary": model_summary,
                "scene_hash": current["sha256"] if current else None,
                "project_revision": _read_revision(project.run_dir)["revision"],
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
                    "snapshot_id": snapshot["snapshot_id"],
                    "source_revision": _read_revision(project.run_dir)["revision"],
                    "contract_sha256": sha256_json(contract),
                    "definition_hash_override": definition_override,
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
                    options,
                )
        return task

    def _verify_prior_unknown(self, db, project, contract, options, model_summary):
        """Allow a separately keyed experiment only after checking local evidence.

        This never resolves the provider outcome or changes the original job.
        """
        import json
        from database import LocalJob
        from html_build_snapshot import safe_file, verify_snapshot
        from html_production_recovery import reconcile_responses, receipt_path
        from html_visual_store import _read_revision
        from artifact_fingerprint import sha256_file, sha256_json
        from html_design_candidates import definition_identity, candidate_directory

        job = db.query(LocalJob).filter(
            LocalJob.id == options["prior_unknown_task_id"],
            LocalJob.project_id == project.id,
            LocalJob.job_type == "html_plan_generate",
        ).first()
        if job is None or job.status not in {"failed", "interrupted"}:
            raise store.HtmlTaskError("PRIOR_UNKNOWN_TASK_INVALID：原任务不存在或不在失败状态", 409)
        payload = job.get_payload()
        snapshot_id = payload.get("input", {}).get("snapshot_id")
        if not snapshot_id:
            raise store.HtmlTaskError("PRIOR_UNKNOWN_TASK_INVALID：原任务缺少输入快照", 409)
        folder = safe_file(project.run_dir, "planning/html_visual/builds/" + snapshot_id)
        manifest = verify_snapshot(folder)
        original_options = {k: v for k, v in json.loads((folder / "input/options.json").read_text(encoding="utf-8")).items()
                            if k != "prior_unknown_task_id"}
        repeated_options = {k: v for k, v in options.items() if k != "prior_unknown_task_id"}
        if (manifest["kind"] != "generation"
                or json.loads((folder / "input/contract.json").read_text(encoding="utf-8")) != contract
                or original_options != repeated_options
                or payload.get("input", {}).get("model_summary") != model_summary
                or manifest["source_revision"] != _read_revision(project.run_dir)["revision"]):
            raise store.HtmlTaskError("PRIOR_UNKNOWN_TASK_MISMATCH：新实验必须使用原讲稿、设计和模型绑定", 409)
        # A returned response receipt takes precedence over a new paid call.
        reconcile_responses(db, job.id, project.run_dir)
        records = store._job(db, job.id).get_payload().get("production_stages", {})
        pending = [r for r in records.values() if r.get("state") in {"intent", "unknown"}]
        if (len(pending) != 1 or pending[0].get("kind") != "json"
                or pending[0].get("lookup_supported") is not False
                or receipt_path(project.run_dir, job.id, f"author-{payload.get('attempt', 1)}").exists()):
            raise store.HtmlTaskError("PRIOR_UNKNOWN_TASK_UNVERIFIED：先核实原任务产物或供应商回执", 409)
        override = {name: sha256_file(folder / "source" / name) for name in (
            "html_design_agent.py", "html_production_service.py")}
        candidate_key = options["design_candidate_key"]
        candidate_file = candidate_directory(project.run_dir, contract["slide_id"], candidate_key) / "candidate.json"
        candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
        if (sha256_json(candidate) != candidate_key
                or sha256_file(candidate_file.parent / "design-reference.png") != candidate.get("image_sha256")):
            raise store.HtmlTaskError("PRIOR_UNKNOWN_DESIGN_INVALID：原设计候选字节或身份已变化", 409)
        candidate_source_hashes = (sha256_file(self.deps.repo_root / "html_design_candidates.py"),
                                   LEGACY_DESIGN_CANDIDATES_SHA256)
        matched = None
        for source_hash in candidate_source_hashes:
            trial = {**override, "html_design_candidates.py": source_hash}
            if candidate.get("definitions_sha256") == definition_identity(
                    self.deps.repo_root, source_hash_overrides=trial):
                matched = trial
                break
        if matched is None or candidate.get("image_sha256") is None:
            raise store.HtmlTaskError("PRIOR_UNKNOWN_DEFINITION_MISMATCH：设计定义差异超过允许的运行策略", 409)
        return matched

    def resume(self, db, project, job):
        """Explicit retry of the frozen request, through the original submit path."""
        import json
        from html_build_snapshot import safe_file, verify_snapshot
        from html_visual_store import _read_revision

        if job.job_type != "html_plan_generate":
            raise store.HtmlTaskError("此入口仅用于场景生产任务", 409)
        if job.status in store.ACTIVE_STATUSES or job.status == "succeeded":
            return {**store._job_to_dict(job), "reused": True}
        if not store.recovery_action(job)["can_resume"]:
            raise store.HtmlTaskError("该任务不能直接继续；请先核实原请求或已有作品", 409)
        try:
            folder = safe_file(project.run_dir, "planning/html_visual/builds/" + job.get_payload()["input"]["snapshot_id"])
            manifest = verify_snapshot(folder)
            contract = json.loads((folder / "input/contract.json").read_text(encoding="utf-8"))
            options = json.loads((folder / "input/options.json").read_text(encoding="utf-8"))
            current = next((s for s in json.loads((Path(project.run_dir) / "planning/visual_contract.json").read_text(encoding="utf-8")).get("slides", []) if s.get("slide_id") == contract["slide_id"]), None)
            if current != contract or _read_revision(project.run_dir)["revision"] != manifest["source_revision"]:
                raise ValueError("revision changed")
        except (ValueError, OSError, KeyError) as exc:
            raise store.HtmlTaskError("原任务输入或版本已变化；请重新读取当前页面", 409) from exc
        if (self.freeze_models is not None
                and self.freeze_models(project).summary() != job.get_payload().get("input", {}).get("model_summary")):
            raise store.HtmlTaskError("原任务代码、模型或依赖已变化；不能作为原请求继续", 409)
        return self.submit(db, project, contract, options=options, expected_snapshot=manifest["snapshot_id"])

    def run(self, job_id, project_id, run_dir, contract, account_id, attempt=None, frozen=None, options=None):
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
                from html_production_stages import ProductionStages
                job = store._job(db, job_id, attempt)
                snapshot_id = job.get_payload().get("input", {}).get("snapshot_id")
                if not snapshot_id:
                    raise store.HtmlTaskError("旧任务没有输入快照，请重新提交", 409)
                stages = ProductionStages(db, job_id, attempt, run_dir, snapshot_id, self.deps.repo_root)
                stages.checkpoint()
                import json
                # The executor consumes the frozen inputs, never the mutable caller object.
                contract = json.loads((stages.folder / "input/contract.json").read_text(encoding="utf-8"))
                options = json.loads((stages.folder / "input/options.json").read_text(encoding="utf-8"))
                extra = {}
                if options:
                    extra["options"] = options
                if frozen is not None:
                    deps = replace(self.deps, json_generator=partial(
                        self.deps.json_generator, model_binding=frozen.text,
                    ), planning_generator=partial(
                        self.deps.json_generator, model_binding=frozen.planning or frozen.text,
                    ))
                    provider = partial(self.provider, model_binding=frozen.image)
                    extra["model_summary"] = frozen.summary()
                deps = replace(deps, json_generator=stages.wrap(deps.json_generator, "json"))
                if deps.planning_generator is not None:
                    deps = replace(deps, planning_generator=stages.wrap(deps.planning_generator, "json"))
                if provider is not None:
                    provider = stages.wrap(provider, "image")
                extra["stage_record"] = stages.record
                extra["progress_record"] = stages.progress
                extra["plan_override"] = stages.returned_phase("plan")
                if job.get_payload().get("input", {}).get("definition_hash_override"):
                    extra["definition_hash_override"] = job.get_payload()["input"]["definition_hash_override"]
                from html_production_recovery import seal_author_commit
                extra["commit_record"] = partial(seal_author_commit, db, job_id, attempt, run_dir, snapshot_id)
                result = produce_scene(
                    contract,
                    run_dir=run_dir,
                    deps=deps,
                    provider=provider,
                    checkpoint=stages.checkpoint,
                    **extra,
                )
                checkpoint()
                from project_path_service import project_or_404
                from invalidation_service import html_scene_changed

                project = project_or_404(db, project_id)
                if result["saved"]["changed"]:
                    html_scene_changed(project, [contract["slide_id"]], rebuild_plan=result.get("rebuild_plan"))
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
            count = store.recover_interrupted(db)
            from database import Project, LocalJob
            projects = db.query(Project).join(LocalJob, LocalJob.project_id == Project.id).filter(
                LocalJob.job_type == "html_plan_generate", LocalJob.status.in_(("failed", "interrupted")),
            ).distinct().all()
            for project in projects:
                with account_scope(project.account_id):
                    self.reconcile_project(db, project)
            return count
        finally:
            db.close()

    def reconcile_project(self, db, project, contract=None, options=None, model_summary=None):
        from database import LocalJob
        from html_production_recovery import reconcile_responses, reconcile_author_commit
        from html_build_snapshot import safe_file, verify_snapshot
        import json
        lookups = {}
        for kind, function in (("json", self.deps.json_generator), ("image", self.provider)):
            if callable(getattr(function, "lookup", None)):
                lookups[kind] = function.lookup
        jobs = db.query(LocalJob).filter(LocalJob.project_id == project.id,
            LocalJob.job_type == "html_plan_generate", LocalJob.status.in_(("failed", "interrupted", "succeeded")),
        ).order_by(LocalJob.created_at.desc()).all()
        recovered = None
        for job in jobs:
            snapshot_id = job.get_payload().get("input", {}).get("snapshot_id")
            if not snapshot_id:
                continue
            try:
                folder = safe_file(project.run_dir, "planning/html_visual/builds/" + snapshot_id)
                verify_snapshot(folder)
                if contract is not None and (
                    json.loads((folder / "input/contract.json").read_text(encoding="utf-8")) != contract
                    or json.loads((folder / "input/options.json").read_text(encoding="utf-8")) != options
                    or job.get_payload().get("input", {}).get("model_summary") != model_summary
                ):
                    continue
                result = reconcile_author_commit(db, job.id, project)
                if result is not None:
                    if contract is not None:
                        return result
                    recovered = recovered or result
                else:
                    job_lookups = dict(lookups)
                    from html_image_provider import configured_image, lookup_toapis_result
                    if self.provider is configured_image and self.freeze_models is not None:
                        def native_lookup(record, *, on_transport_event=None):
                            bound = self.freeze_models(project)
                            expected = job.get_payload().get("input", {}).get("model_summary", {}).get("image", {})
                            if bound.image.config_hash != expected.get("config_hash"):
                                raise store.HtmlTaskError("PROVIDER_CONNECTION_CHANGED", 409)
                            return lookup_toapis_result(record, model_binding=bound.image,
                                                        on_transport_event=on_transport_event)
                        job_lookups["toapis"] = native_lookup
                    reconcile_responses(db, job.id, project.run_dir, lookups=job_lookups)
                    if contract is not None:
                        pending = store._job(db, job.id).get_payload().get("production_stages", {})
                        if any(record.get("state") in {"intent", "unknown"} for record in pending.values()):
                            # A newer code/definition snapshot must not bypass an
                            # unresolved paid request for the same semantic input.
                            raise store.HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：先核实原请求，禁止用新快照重复生成", 409)
            except Exception:
                # No blind retry and no startup-wide failure on one broken receipt.
                db.rollback()
                current = store._job(db, job.id)
                if current.status in {"failed", "interrupted"}:
                    store._transition(db, current, ("failed", "interrupted"), {
                        "error": "RECOVERY_RECONCILIATION_BLOCKED：回执、版本或供应商结果需核实",
                    })
                    if contract is not None:
                        raise store.HtmlTaskError("RECOVERY_RECONCILIATION_BLOCKED：请先核实已有作品或供应商回执", 409) from None
        return recovered
