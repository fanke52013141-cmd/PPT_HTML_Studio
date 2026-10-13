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

    def submit(self, db, project, contract, options=None, *, expected_snapshot=None,
               expected_model_summary=None):
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
        if expected_model_summary is not None and model_summary != expected_model_summary:
            raise store.HtmlTaskError("项目生成模型已变化；课程任务不能混用模型版本", 409)
        # Reconcile before building a new revision-dependent submission key.
        # Otherwise an already-saved page would be generated again as a new job.
        recovered = self.reconcile_project(db, project, contract, options, model_summary)
        if recovered is not None:
            return {**recovered, "reused": True, "reconciled": True}
        from html_build_snapshot import create_generation_snapshot
        snapshot = create_generation_snapshot(
            project.run_dir, contract, repo_root=self.deps.repo_root,
            expected_revision=_read_revision(project.run_dir)["revision"], options=options,
            model_identity={name: {"provider": part.get("provider"), "model": part.get("model"),
                                  "config_digest": part.get("config_hash")}
                            for name in ("text", "image") if (part := model_summary.get(name))},
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

    def submit_semantic_review(self, db, project, slide_id, *,
                               expected_snapshot=None, expected_model_summary=None):
        """Queue the A04 review as a durable stage task using the same LocalJob pool."""
        import json
        from html_visual_store import load_scene_with_revision, _read_revision, validate_slide_id
        from html_build_snapshot import create_generation_snapshot
        from html_input_manifest import resolved_scene_inputs

        slide_id = validate_slide_id(slide_id)
        run_dir = Path(project.run_dir)
        document = load_scene_with_revision(run_dir, slide_id)
        if document is None or document["scene"].get("version") != "0.6.0":
            raise store.HtmlTaskError("语义审阅只接受已保存的 scene0.6.0", 409)
        try:
            contract = json.loads((run_dir / "planning/visual_contract.json").read_text(encoding="utf-8"))
            page = next(item for item in contract.get("slides", []) if item.get("slide_id") == slide_id)
        except (OSError, ValueError, StopIteration) as exc:
            raise store.HtmlTaskError("当前分镜不存在，不能启动语义审阅", 409) from exc
        input_digest = resolved_scene_inputs(document["scene"], run_dir, self.deps.repo_root)["digest"]
        frozen = self.freeze_models(project) if self.freeze_models is not None else None
        model_summary = frozen.summary() if frozen is not None else {"source": "injected"}
        if expected_model_summary is not None and model_summary != expected_model_summary:
            raise store.HtmlTaskError("项目生成模型已变化；课程任务不能混用模型版本", 409)
        model_identity = {
            name: {"provider": part.get("provider"), "model": part.get("model"),
                  "config_digest": part.get("config_hash")}
            for name in ("text", "image") if (part := model_summary.get(name))
        }
        snapshot = create_generation_snapshot(
            run_dir, page, repo_root=self.deps.repo_root,
            expected_revision=_read_revision(run_dir)["revision"],
            model_identity=model_identity,
        )
        if expected_snapshot is not None and snapshot["snapshot_id"] != expected_snapshot:
            raise store.HtmlTaskError("语义审阅快照已变化，不能作为原请求继续", 409)
        scene_sha256 = document["sha256"]
        key = sha256_json({
            "kind": "html_semantic_review", "slide_id": slide_id,
            "snapshot_id": snapshot["snapshot_id"], "source_revision": _read_revision(run_dir)["revision"],
            "scene_sha256": scene_sha256, "semantic_input_digest": input_digest,
            "model_summary": model_summary,
        })
        # Resolve a previous uncertain provider request before allowing the
        # course to create a new review task for this page.
        self.reconcile_project(db, project, job_types=("html_review",), slide_id=slide_id)
        from database import LocalJob
        unresolved = db.query(LocalJob).filter(
            LocalJob.project_id == project.id, LocalJob.job_type == "html_review",
            LocalJob.status.in_(("failed", "interrupted")),
        ).order_by(LocalJob.created_at.desc()).all()
        for job in unresolved:
            payload = job.get_payload()
            source = payload.get("input", {})
            records = payload.get("production_stages", {})
            if source.get("slide_id") == slide_id and any(
                value.get("state") in {"intent", "unknown"} for value in records.values()
            ):
                raise store.HtmlTaskError(
                    "EXTERNAL_OUTCOME_UNKNOWN：本页原语义审阅请求仍待对账，禁止发起新请求", 409
                )
        with self.submit_lock:
            task = store.submit_task(
                db, project_id=project.id, task_type="html_review", submission_key=key,
                payload={
                    "slide_id": slide_id, "account_id": get_current_account_id(),
                    "snapshot_id": snapshot["snapshot_id"],
                    "source_revision": _read_revision(run_dir)["revision"],
                    "contract_sha256": sha256_json(page),
                    "scene_sha256": scene_sha256,
                    "semantic_input_digest": input_digest,
                    "model_summary": model_summary,
                },
            )
            if not task["reused"] or task.get("retried"):
                self.executor.submit(
                    self.run_semantic_review, task["id"], project.id,
                    run_dir, slide_id, get_current_account_id(), task["attempt"], frozen,
                )
        return task

    def resume(self, db, project, job):
        """Explicit retry of the frozen request, through the original submit path."""
        import json
        from html_build_snapshot import safe_file, verify_snapshot
        from html_visual_store import _read_revision

        if job.job_type == "html_review":
            if job.status in store.ACTIVE_STATUSES or job.status == "succeeded":
                return {**store._job_to_dict(job), "reused": True}
            if not store.recovery_action(job)["can_resume"]:
                raise store.HtmlTaskError("原语义审阅请求结果未知或不能继续；禁止重新调用供应商", 409)
            payload = job.get_payload().get("input", {})
            try:
                folder = safe_file(project.run_dir, "planning/html_visual/builds/" + payload["snapshot_id"])
                manifest = verify_snapshot(folder)
                contract = json.loads((folder / "input/contract.json").read_text(encoding="utf-8"))
                current = next((s for s in json.loads((Path(project.run_dir) / "planning/visual_contract.json").read_text(encoding="utf-8")).get("slides", []) if s.get("slide_id") == payload["slide_id"]), None)
                from html_visual_store import load_scene_with_revision
                document = load_scene_with_revision(project.run_dir, payload["slide_id"])
                from html_input_manifest import resolved_scene_inputs
                input_digest = resolved_scene_inputs(document["scene"], project.run_dir, self.deps.repo_root)["digest"] if document else None
                if (current != contract or _read_revision(project.run_dir)["revision"] != manifest["source_revision"]
                        or not document or document["sha256"] != payload.get("scene_sha256")
                        or input_digest != payload.get("semantic_input_digest")):
                    raise ValueError("semantic input changed")
            except (ValueError, OSError, KeyError, TypeError) as exc:
                raise store.HtmlTaskError("原语义审阅输入或版本已变化；请核实后重新审阅", 409) from exc
            return self.submit_semantic_review(
                db, project, payload["slide_id"],
                expected_snapshot=manifest["snapshot_id"],
                expected_model_summary=payload.get("model_summary"),
            )
        if job.job_type != "html_plan_generate":
            raise store.HtmlTaskError("此入口仅用于 HTML 场景生产或语义审阅任务", 409)
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
        return self.submit(db, project, contract, options=options, expected_snapshot=manifest["snapshot_id"],
                           expected_model_summary=job.get_payload().get("input", {}).get("model_summary"))

    def run_semantic_review(self, job_id, project_id, run_dir, slide_id, account_id,
                            attempt=None, frozen=None):
        import json
        db = self.session_factory()
        try:
            with account_scope(account_id):
                store.mark_running(db, job_id, expected_attempt=attempt)

                def checkpoint():
                    from database import LocalJob
                    db.expire_all()
                    job = db.query(LocalJob).filter(LocalJob.id == job_id).first()
                    if (not job or job.status != "running" or
                            (attempt is not None and int(job.get_payload().get("attempt", 1)) != attempt)):
                        raise store.HtmlTaskError("任务已停止；语义审阅结果保留")

                from database import LocalJob
                from html_production_stages import ProductionStages
                from html_visual_store import load_scene_with_revision, _read_revision
                from html_input_manifest import resolved_scene_inputs
                from html_semantic_review import review_semantic_scene
                job = store._job(db, job_id, attempt)
                source = job.get_payload().get("input", {})
                snapshot_id = source.get("snapshot_id")
                if not snapshot_id:
                    raise store.HtmlTaskError("语义审阅任务没有冻结输入快照", 409)
                stages = ProductionStages(db, job_id, attempt, run_dir, snapshot_id, self.deps.repo_root)
                stages.checkpoint()
                frozen_contract = json.loads((stages.folder / "input/contract.json").read_text(encoding="utf-8"))
                current_contract = json.loads((Path(run_dir) / "planning/visual_contract.json").read_text(encoding="utf-8"))
                page = next((s for s in current_contract.get("slides", []) if s.get("slide_id") == slide_id), None)
                document = load_scene_with_revision(run_dir, slide_id)
                if (page != frozen_contract or not document or document["sha256"] != source.get("scene_sha256")
                        or _read_revision(run_dir)["revision"] != source.get("source_revision")
                        or resolved_scene_inputs(document["scene"], run_dir, self.deps.repo_root)["digest"] != source.get("semantic_input_digest")):
                    raise store.HtmlTaskError("语义审阅输入已变化，原任务不能继续", 409)
                deps = self.deps
                if frozen is not None:
                    deps = replace(self.deps, json_generator=partial(
                        self.deps.json_generator, model_binding=frozen.text,
                        temperature=0, max_tokens_limit=2048, request_timeout=90,
                        strict_response=True,
                    ), semantic_model_identity=frozen.text.summary())
                deps = replace(deps, json_generator=stages.wrap(deps.json_generator, "json"))
                evidence_dir = f"planning/html_visual/semantic-review/tasks/{job_id}"
                report = review_semantic_scene(
                    document["scene"], run_dir=run_dir, deps=deps,
                    evidence_dir=evidence_dir, review_id=job_id,
                )
                checkpoint()
                store.mark_succeeded(db, job_id, {
                    "stage": "semantic_review", "slide_id": slide_id,
                    "snapshot_id": snapshot_id, "scene_sha256": source["scene_sha256"],
                    "semantic_input_digest": source["semantic_input_digest"],
                    "report": report, "passed": bool(report.get("passed")),
                }, expected_attempt=attempt)
        except Exception as exc:
            db.rollback()
            message = str(exc)
            if frozen is not None:
                for model in (frozen.text, frozen.image):
                    if model.api_key:
                        message = message.replace(model.api_key, "[REDACTED]")
                if not isinstance(exc, (store.HtmlTaskError, ValueError)):
                    message = "语义审阅失败，请检查模型连接、服务状态或核实原请求。"
            store.mark_failed(db, job_id, message, expected_attempt=attempt)
        finally:
            db.close()

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
                    ))
                    provider = partial(self.provider, model_binding=frozen.image)
                    extra["model_summary"] = frozen.summary()
                deps = replace(deps, json_generator=stages.wrap(deps.json_generator, "json"))
                if provider is not None:
                    provider = stages.wrap(provider, "image")
                extra["stage_record"] = stages.record
                extra["progress_record"] = stages.progress
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
                LocalJob.job_type.in_(("html_plan_generate", "html_review")), LocalJob.status.in_(("failed", "interrupted")),
            ).distinct().all()
            for project in projects:
                with account_scope(project.account_id):
                    self.reconcile_project(db, project)
            return count
        finally:
            db.close()

    def reconcile_project(self, db, project, contract=None, options=None, model_summary=None,
                          *, job_types=("html_plan_generate", "html_review"), slide_id=None):
        from database import LocalJob
        from html_production_recovery import reconcile_responses, reconcile_author_commit
        from html_build_snapshot import safe_file, verify_snapshot
        import json
        lookups = {}
        for kind, function in (("json", self.deps.json_generator), ("image", self.provider)):
            if callable(getattr(function, "lookup", None)):
                lookups[kind] = function.lookup
        query = db.query(LocalJob).filter(LocalJob.project_id == project.id,
            LocalJob.job_type.in_(job_types), LocalJob.status.in_(("failed", "interrupted", "succeeded")),
        ).order_by(LocalJob.created_at.desc()).all()
        jobs = query
        if slide_id is not None:
            jobs = [job for job in jobs if job.get_payload().get("input", {}).get("slide_id") == slide_id]
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
                result = reconcile_author_commit(db, job.id, project) if job.job_type == "html_plan_generate" else None
                if result is not None:
                    if contract is not None:
                        return result
                    recovered = recovered or result
                else:
                    job_lookups = dict(lookups)
                    from html_image_provider import configured_image, lookup_toapis_result
                    if self.provider is configured_image and self.freeze_models is not None:
                        def native_lookup(record):
                            bound = self.freeze_models(project)
                            expected = job.get_payload().get("input", {}).get("model_summary", {}).get("image", {})
                            if bound.image.config_hash != expected.get("config_hash"):
                                raise store.HtmlTaskError("PROVIDER_CONNECTION_CHANGED", 409)
                            return lookup_toapis_result(record, model_binding=bound.image)
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
