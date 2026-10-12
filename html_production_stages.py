"""Attempt-fenced production checkpoints over LocalJob (no second job store)."""
from pathlib import Path
import json

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
        manifest = verify_snapshot(self.folder)
        if manifest["snapshot_id"] != self.snapshot_id or manifest["kind"] != "generation":
            raise store.HtmlTaskError("生成快照身份不匹配", 409)
        from html_visual_store import _read_revision
        if _read_revision(self.run)["revision"] != manifest["source_revision"]:
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
        return job

    def _persist(self, key, record):
        job = self.checkpoint()
        payload = job.get_payload()
        payload.setdefault("production_stages", {})[key] = record
        return store._transition(self.db, job, ("running",), {
            "payload_json": store.json_dumps(payload), "stage": record["stage"],
        })

    def record(self, name, value):
        """Deterministic stage evidence; never bypass final review on recovery."""
        self._save("phase:" + name, value, name, "json")

    def _save(self, key, value, stage, kind):
        self.checkpoint()
        data = value if kind == "image" else json_bytes(value)
        identity = digest(data)
        relative = f"planning/html_visual/task-stages/{self.job_id}/{identity}.{'png' if kind == 'image' else 'json'}"
        path = safe_file(self.run, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        from html_visual_store import _atomic_write_bytes
        _atomic_write_bytes(path, data)
        self._persist(key, {"state": "returned", "stage": stage, "kind": kind,
                            "file": relative, "sha256": identity})
        return value

    def wrap(self, function, kind):
        def invoke(*args, **kwargs):
            # Hash attachment bytes, not only mutable path strings.
            attachments = kwargs.get("reference_paths", kwargs.get("image_paths", [])) or []
            request = {"args": args, "kwargs": kwargs,
                       "attachments": [fresh_hash(Path(p)) for p in attachments]}
            key = kind + ":" + digest(json_bytes(request))
            job = self.checkpoint()
            payload = job.get_payload()
            records = payload.get("production_stages", {})
            previous = records.get(key)
            if previous:
                if previous["state"] != "returned":
                    raise store.HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：请求结果不确定，不能自动重复调用", 409)
                path = safe_file(self.run, previous["file"])
                if not path.is_file() or fresh_hash(path) != previous["sha256"]:
                    raise store.HtmlTaskError("STAGE_ARTIFACT_INVALID：已返回产物损坏，不能自动重复调用", 409)
                data = path.read_bytes()
                if kind == "image":
                    from ai_provider_service import open_validated_image
                    open_validated_image(data)
                    return data
                value = json.loads(data)
                if not isinstance(value, dict):
                    raise store.HtmlTaskError("阶段 JSON 必须是对象", 409)
                return value
            if sum(k.startswith(("json:", "image:")) for k in records) >= self.MAX_CALLS:
                raise store.HtmlTaskError("阶段模型调用预算已耗尽", 409)
            self._persist(key, {"state": "intent", "stage": kind + "_request", "kind": kind})
            try:
                value = function(*args, **kwargs)
            except Exception:
                self._persist(key, {"state": "unknown", "stage": kind + "_unknown", "kind": kind})
                raise store.HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：供应商结果待核实，禁止自动重复请求", 409) from None
            # Persist raw returned bytes/JSON before validation or downstream work.
            self._save(key, value, kind + "_returned", kind)
            if kind == "image":
                from ai_provider_service import open_validated_image
                open_validated_image(value)
            elif not isinstance(value, dict):
                raise store.HtmlTaskError("模型返回必须是 JSON 对象")
            return value
        return invoke
