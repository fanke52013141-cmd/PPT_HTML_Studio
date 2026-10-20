"""Attempt-fenced production checkpoints over LocalJob (no second job store)."""
from pathlib import Path
import json
import time
from datetime import datetime, timezone

import html_task_store as store
from html_build_snapshot import digest, json_bytes, safe_file, verify_snapshot, fresh_hash


class ProductionStages:
    MAX_CALLS = 12

    def __init__(self, db, job_id, attempt, run_dir, snapshot_id, repo_root):
        self.db, self.job_id, self.attempt = db, job_id, attempt
        self.run = Path(run_dir)
        self.root = Path(repo_root)
        self.snapshot_id = snapshot_id
        self.folder = safe_file(self.run, "planning/html_visual/builds/" + snapshot_id)

    def checkpoint(self):
        job = store._job(self.db, self.job_id, self.attempt)
        if job.status != "running":
            raise store.HtmlTaskError("任务已停止；拒绝迟到产物", 409)
        self.verify_inputs()
        return job

    def verify_inputs(self, *, check_revision=True):
        """Read-only source verification, also used by task presentation."""
        manifest = verify_snapshot(self.folder)
        if manifest["snapshot_id"] != self.snapshot_id or manifest["kind"] != "generation":
            raise store.HtmlTaskError("生成快照身份不匹配", 409)
        from html_visual_store import _read_revision
        if check_revision and _read_revision(self.run)["revision"] != manifest["source_revision"]:
            raise store.HtmlTaskError("生成快照版本已过期，请重新提交", 409)
        # Execute installed code only when it still matches the frozen closure.
        for entry in manifest["files"]:
            relative = entry["path"]
            target = None
            if relative.startswith("source/") and relative != "source/project-resources.json":
                target = safe_file(self.root, relative.removeprefix("source/"))
            elif relative.startswith("definitions/"):
                target = safe_file(self.root, "html_engine/visual/" + relative.removeprefix("definitions/"))
            elif relative.startswith("references/"):
                target = safe_file(self.root, relative.removeprefix("references/"))
            elif relative.startswith("assets/"):
                path = relative.removeprefix("assets/")
                target = safe_file(self.run, path.removeprefix("project/")) if path.startswith("project/") or path.startswith("planning/") else safe_file(self.root, path)
            if target is not None and (not target.is_file() or fresh_hash(target) != entry["sha256"]):
                raise store.HtmlTaskError("快照依赖已变化，请重新提交", 409)
        return manifest

    def _persist(self, key, record, *, external_outcome=False):
        # Recording the outcome of a submitted request must survive source
        # changes. Author execution still uses the strict checkpoint.
        job = store._job(self.db, self.job_id, self.attempt) if external_outcome else self.checkpoint()
        if job.status != "running":
            raise store.HtmlTaskError("任务已停止；拒绝迟到产物", 409)
        payload = job.get_payload()
        payload.setdefault("production_stages", {})[key] = record
        return store._transition(self.db, job, ("running",), {
            "payload_json": store.json_dumps(payload), "stage": record["stage"],
        })

    def record(self, name, value):
        """Deterministic stage evidence; never bypass final review on recovery."""
        self._save("phase:" + name, value, name, "json")

    def returned_phase(self, name):
        """Read a sealed deterministic result from an earlier attempt."""
        job = self.checkpoint()
        record = job.get_payload().get("production_stages", {}).get("phase:" + name)
        if not record:
            return None
        if record.get("state") != "returned" or record.get("kind") != "json":
            raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID：阶段记录不完整", 409)
        try:
            path = safe_file(self.run, record["file"])
        except (KeyError, TypeError, ValueError) as exc:
            raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID：阶段路径无效", 409) from exc
        if not path.is_file() or fresh_hash(path) != record["sha256"]:
            raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID：阶段产物损坏", 409)
        try:
            value = json.loads(path.read_bytes())
        except (ValueError, UnicodeError) as exc:
            raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID：阶段 JSON 格式错误", 409) from exc
        if not isinstance(value, dict):
            raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID：阶段 JSON 格式错误", 409)
        return value

    def progress(self, value):
        job = self.checkpoint()
        payload = job.get_payload()
        payload["progress"] = {**payload.get("progress", {}), **value}
        store._transition(self.db, job, ("running",), {"payload_json": store.json_dumps(payload)})

    def _save(self, key, value, stage, kind, *, metrics=None):
        external = key.startswith(("json:", "image:"))
        job = store._job(self.db, self.job_id, self.attempt) if external else self.checkpoint()
        if job.status != "running":
            raise store.HtmlTaskError("任务已停止；拒绝迟到产物", 409)
        data = value if kind == "image" else json_bytes(value)
        identity = digest(data)
        relative = f"planning/html_visual/task-stages/{self.job_id}/{identity}.{'png' if kind == 'image' else 'json'}"
        path = safe_file(self.run, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        from html_visual_store import _atomic_write_bytes
        _atomic_write_bytes(path, data)
        job = store._job(self.db, self.job_id, self.attempt) if external else self.checkpoint()
        previous = job.get_payload().get("production_stages", {}).get(key, {})
        record = {**previous, "state": "returned", "stage": stage, "kind": kind,
                  "file": relative, "sha256": identity}
        if metrics is not None:
            record["metrics"] = {**metrics, "output_bytes": len(data)}
        if key.startswith(("json:", "image:")):
            from html_production_recovery import receipt_path, write_receipt
            write_receipt(receipt_path(self.run, self.job_id, digest(key.encode())), {
                "job_id": self.job_id, "snapshot_id": self.snapshot_id, "key": key, "record": record,
            })
        self._persist(key, record, external_outcome=external)
        self.checkpoint()
        return value

    def wrap(self, function, kind):
        def invoke(*args, **kwargs):
            from functools import partial
            original = function
            while isinstance(original, partial):
                original = original.func
            streaming = kind == "json" and getattr(original, "supports_stream_progress", False)
            if streaming:
                kwargs = {**kwargs, "stream_output": True,
                          "request_timeout": kwargs.get("request_timeout") if kwargs.get("request_timeout") is not None else 1800}
            # Hash attachment bytes, not only mutable path strings.
            attachments = kwargs.get("reference_paths", kwargs.get("image_paths", [])) or []
            request = {"args": args, "kwargs": kwargs,
                       "attachments": [fresh_hash(Path(p)) for p in attachments]}
            key = kind + ":" + digest(json_bytes(request))
            job = self.checkpoint()
            payload = job.get_payload()
            records = payload.get("production_stages", {})
            previous = records.get(key)
            if previous and previous.get("state") != "not_submitted":
                if previous["state"] != "returned":
                    if previous["state"] == "output_limit":
                        raise store.HtmlTaskError("MODEL_OUTPUT_LIMIT：规划输出额度耗尽，请调整规划任务后创建新实验", 409)
                    raise store.HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：请求结果不确定，不能自动重复调用", 409)
                path = safe_file(self.run, previous["file"])
                if not path.is_file() or fresh_hash(path) != previous["sha256"]:
                    raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID：已返回产物损坏，不能自动重复调用", 409)
                data = path.read_bytes()
                from html_execution_metrics import request_role
                prior_metrics = previous.get("metrics") or {"role": request_role(kind, kwargs),
                    "adapter_calls": None, "elapsed_ms": None, "usage": None, "cost": None}
                reused = {**previous, "metrics": {**prior_metrics,
                          "reuses": prior_metrics.get("reuses", 0) + 1}}
                self._persist(key, reused)
                self.progress({"reused_stages": sorted(set(payload.get("progress", {}).get("reused_stages", []) + [key]))})
                if kind == "image":
                    from ai_provider_service import open_validated_image
                    open_validated_image(data)
                    return data
                value = json.loads(data)
                if not isinstance(value, dict):
                    raise store.HtmlTaskError("阶段 JSON 必须是对象", 409)
                return value
            if sum(k.startswith(("json:", "image:")) for k in records) >= self.MAX_CALLS:
                self.progress({"next_action": {"stage": "production", "reason": "external_call_budget_exhausted",
                    "routes": ["manual_review"], "automatic_retry": False}})
                raise store.HtmlTaskError("阶段模型调用预算已耗尽", 409)
            if kind == "image" and getattr(self, "image_limit", None) is not None:
                if sum(k.startswith("image:") for k in records) >= self.image_limit:
                    raise store.HtmlTaskError("IMAGE_BUDGET_EXCEEDED：独立素材预算已用完；请显式授权额度", 409)
            getattr(self, "external_guard", lambda: None)()
            request_id = digest(json_bytes({"job": self.job_id, "snapshot": self.snapshot_id,
                                            "key": key, "attempt": self.attempt}))
            lookup_supported = callable(getattr(function, "lookup", None)) and callable(getattr(function, "invoke_with_request_id", None))
            from html_execution_metrics import request_role
            metrics = {"role": request_role(kind, kwargs), "adapter_calls": None, "reuses": 0,
                       "request_timeout_seconds": kwargs.get("request_timeout"),
                       "started_at": datetime.now(timezone.utc).isoformat(), "elapsed_ms": None,
                       "adapter_input_bytes": len(json_bytes({"args": args, "kwargs": kwargs})),
                       "attachment_bytes": sum(Path(p).stat().st_size for p in attachments),
                       "output_bytes": None, "usage": None, "cost": None}
            intent = {"state": "intent", "stage": kind + "_request", "kind": kind,
                      "attempt": self.attempt, "request_id": request_id, "lookup_supported": lookup_supported,
                      "metrics": metrics}
            self._persist(key, intent)
            native_tasks = kind == "image" and getattr(original, "supports_upstream_task", False)
            def stream_progress(value):
                current = store._job(self.db, self.job_id, self.attempt)
                if current.status != "running":
                    raise store.HtmlTaskError("任务已停止；拒绝迟到进度", 409)
                data = current.get_payload()
                data["progress"] = {**data.get("progress", {}), "model_stream": value}
                store._transition(self.db, current, ("running",), {"payload_json": store.json_dumps(data)})
            def submitted(task_id):
                import re
                if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", task_id):
                    raise store.HtmlTaskError("PROVIDER_TASK_ID_INVALID", 409)
                self.checkpoint()
                current = store._job(self.db, self.job_id, self.attempt)
                previous = current.get_payload().get("production_stages", {}).get(key, intent)
                record = {**previous, "upstream_task_id": task_id, "lookup_supported": True}
                from html_production_recovery import receipt_path, write_receipt
                write_receipt(receipt_path(self.run, self.job_id, "upstream-" + digest(key.encode())), {
                    "job_id": self.job_id, "snapshot_id": self.snapshot_id, "key": key, "record": record,
                })
                self._persist(key, record)
            def transport_event(phase):
                if phase not in {"upload", "submit", "poll", "extract"}:
                    raise store.HtmlTaskError("PROVIDER_EVENT_INVALID", 409)
                current = store._job(self.db, self.job_id, self.attempt)
                previous = current.get_payload().get("production_stages", {}).get(key, intent)
                transport = previous.get("transport", {})
                counts = {**transport.get("boundary_entries", {})}
                counts[phase] = counts.get(phase, 0) + 1
                self._persist(key, {**previous, "transport": {
                    "last_phase": phase, "boundary_entries": counts,
                }}, external_outcome=True)
            started = time.monotonic()
            try:
                callbacks = {"on_task_submitted": submitted, "on_transport_event": transport_event} if native_tasks else {}
                if streaming:
                    callbacks["on_stream_progress"] = stream_progress
                value = function.invoke_with_request_id(request_id, *args, **kwargs) if lookup_supported else function(*args, **kwargs, **callbacks)
            except Exception as error:
                previous = store._job(self.db, self.job_id, self.attempt).get_payload().get("production_stages", {}).get(key, intent)
                failed_stream = (store._job(self.db, self.job_id, self.attempt).get_payload()
                                 .get("progress", {}).get("model_stream", {})) if streaming else {}
                output_limit = (failed_stream.get("failure_reason") == "output_limit"
                                and failed_stream.get("finish_reason") == "length")
                from json_llm_transport import _safe_usage
                usage = _safe_usage(failed_stream.get("usage"))
                from html_production_recovery import receipt_path, write_receipt
                record = {**previous, "state": "output_limit" if output_limit else "unknown",
                          "stage": kind + ("_output_limit" if output_limit else "_unknown"),
                          "metrics": {**metrics, "adapter_calls": 1,
                                      "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
                                      "usage": usage, "finish_reason": failed_stream.get("finish_reason")},
                          "error_class": type(error).__name__,
                          "cause_class": type(error.__cause__).__name__ if error.__cause__ else None}
                if kind == "image":
                    from html_image_provider import ImageProviderBoundaryError
                    if isinstance(error, ImageProviderBoundaryError):
                        record["provider_error"] = {"code": error.code, "phase": error.phase}
                write_receipt(receipt_path(self.run, self.job_id,
                                           ("output-limit-" if output_limit else "unknown-") + digest(key.encode())), {
                    "job_id": self.job_id, "snapshot_id": self.snapshot_id, "key": key, "record": record,
                })
                self._persist(key, record, external_outcome=True)
                if streaming:
                    # The stream callback owns sanitized transport evidence;
                    # HTTPException text and model reasoning never enter advice.
                    reason = failed_stream.get("failure_reason")
                    if reason in {"read_timeout", "total_timeout", "incomplete_response", "transport_error", "output_limit"}:
                        current = store._job(self.db, self.job_id, self.attempt)
                        payload = current.get_payload()
                        payload["progress"] = {**payload.get("progress", {}), "next_action": {
                            "stage": metrics["role"], "reason": reason,
                            "routes": ["planning_revision"] if output_limit else ["provider_verification"],
                            "automatic_retry": False}}
                        store._transition(self.db, current, ("running",), {"payload_json": store.json_dumps(payload)})
                if output_limit:
                    raise store.HtmlTaskError("MODEL_OUTPUT_LIMIT：模型已用尽输出额度，场景规划未完成；请优化规划输入后创建新实验", 409) from error
                raise store.HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：供应商结果待核实，禁止自动重复请求", 409) from error
            # Persist raw returned bytes/JSON before validation or downstream work.
            self._save(key, value, kind + "_returned", kind,
                       metrics={**metrics, "adapter_calls": 1, "elapsed_ms": round((time.monotonic() - started) * 1000, 3)})
            if kind == "image":
                from ai_provider_service import open_validated_image
                open_validated_image(value)
            elif not isinstance(value, dict):
                raise store.HtmlTaskError("模型返回必须是 JSON 对象")
            return value
        return invoke
