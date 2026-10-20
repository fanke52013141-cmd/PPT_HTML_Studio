"""Host-owned Pi tools: sealed materials, original checks, strict result packaging."""
import base64
import io
import json
import zipfile
from pathlib import Path

import html_external_handoff as handoff
from html_handoff_models import ExternalResult
from html_handoff_execution import verification_template
from html_agent_store import digest
from pipeline_lifecycle import project_artifact_lock


class ExecutionError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def text_result(value):
    return [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]


class Execution:
    def __init__(self, run, project, slide, packet, limits, folder):
        self.run, self.project, self.slide = Path(run), project, slide
        self.packet, self.limits, self.folder = packet, limits, Path(folder)
        self.rounds = 0
        self.images = {}
        self.baseline_seen, self.after_seen = set(), set()
        self.epoch = 0
        self.baseline_epoch = self.after_epoch = None
        self.read_materials = set()
        self.last = self.checked = self.preflight = self.final = None
        self.members = {}
        # Server-generated archive is still bounded and path-checked before use.
        with zipfile.ZipFile(handoff.bundle_path(run, project, slide, packet["task_id"])) as archive:
            if sum(item.file_size for item in archive.infolist()) > 256 * 1024 * 1024:
                raise ExecutionError("invalid_input", "任务包过大")
            for member in archive.infolist():
                name = member.filename
                if "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ExecutionError("invalid_input", "任务材料路径不合法")
                self.members[name] = archive.read(name)
        for item in packet["files"]:
            from hashlib import sha256
            data = self.members.get(item["path"], b"")
            if len(data) != item["size"] or sha256(data).hexdigest() != item["sha256"]:
                raise ExecutionError("invalid_input", "任务材料校验失败")
        self.folder.mkdir(parents=True, exist_ok=False)
        for name, data in self.members.items():
            destination = self.folder / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

    def fresh(self):
        with project_artifact_lock(self.run):
            handoff._request(self.run, self.project, self.slide,
                {"task_id": self.packet["task_id"], "status": "needs_input", "message": "current input check", "operations": []})

    def call(self, name, args):
        self.fresh()
        if self.final is not None:
            raise ExecutionError("invalid_result", "任务已交付")
        if name == "read_material":
            filename = args.get("name")
            if filename not in self.members or filename.endswith(".png"):
                raise ExecutionError("invalid_input", "只允许读取包内文字材料")
            raw = self.members[filename]
            if len(raw) > 512 * 1024:
                raise ExecutionError("invalid_input", "材料超过读取限额")
            self.read_materials.add(filename)
            return text_result({"name": filename, "text": raw.decode("utf-8")})
        if name == "view_image":
            filename = args.get("name")
            if filename in self.images:
                raw = self.images[filename]
                self.after_seen.add(filename)
                self.after_epoch = self.epoch
            elif filename in self.members and filename.endswith(".png"):
                raw = self.members[filename]
                if filename not in {shot["file"] for shot in self.packet["context"]["evidence"].get("screenshots", [])}:
                    # References can be viewed but don't count as original slide review.
                    return self._image(filename, raw)
                self.baseline_seen.add(filename)
                self.baseline_epoch = self.epoch
            else:
                raise ExecutionError("invalid_input", "图片不在本任务中")
            return self._image(filename, raw)
        if name not in ("check_candidate", "submit_result"):
            raise ExecutionError("unsupported_capability", "工具未授权")
        proposed = ExternalResult.model_validate(args.get("result"))
        if proposed.task_id != self.packet["task_id"]:
            raise ExecutionError("invalid_result", "结果任务身份错误")
        if name == "submit_result":
            if proposed.status != "proposed":
                raise ExecutionError("constraints_unsatisfied", proposed.message)
            if (not self.last or digest(proposed.model_dump(mode="json")) != digest(self.last.model_dump(mode="json"))
                    or not self.checked.get("passed")):
                raise ExecutionError("verification_failed", "必须先检查当前完整候选并通过")
            if (not self.baseline_seen or not self.after_seen
                    or self.baseline_epoch is None or self.after_epoch is None
                    or self.epoch <= max(self.baseline_epoch, self.after_epoch)
                    or not str(args.get("baseline_notes", "")).strip() or not str(args.get("candidate_notes", "")).strip()):
                raise ExecutionError("verification_failed", "必须实际查看原图和当前候选图并记录观察")
            self.final = self._deliver(proposed, args)
            return text_result({"submitted": True, "saved": False})
        if self.rounds >= self.limits.max_candidate_rounds:
            raise ExecutionError("budget_exceeded", "候选检查轮次已用完")
        if proposed.status != "proposed":
            raise ExecutionError("constraints_unsatisfied", proposed.message)
        if not {"ENTRY.md", "decision-input.json", "constraints.json", "task.json", "content.json"} <= self.read_materials:
            raise ExecutionError("invalid_input", "请先读取本轮任务的入口、条件和权威内容")
        self.rounds += 1
        self.last = proposed
        self.checked = {"passed": False}
        self.images.clear()
        self.after_seen.clear()
        result_path = self.folder / "result.json"
        result_data = proposed.model_dump(mode="json")
        result_data["operations"] = [operation.model_dump(exclude_none=True) for operation in proposed.operations]
        result_path.write_text(json.dumps(result_data, ensure_ascii=False), encoding="utf-8")
        if self.packet["task_type"] == "static_repair":
            from scripts.check_external_task import preflight
            self.preflight = preflight(self.folder / "task.json", result_path)
            if not self.preflight["preflight_passed"]:
                return text_result({"passed": False, "preflight": self.preflight, "round": self.rounds})
        with project_artifact_lock(self.run):
            try:
                self.checked = handoff.preview_result(self.run, self.project, self.slide, proposed)
            except handoff.editor.SceneEditError as error:
                if error.code == "AUDIO_REVISION_CONFLICT": raise
                self.checked = {"passed": False, "validation": {"code": error.code, "message": str(error)}}
        for index, shot in enumerate(self.checked.get("comparison", {}).get("after", [])):
            value = shot.get("image", "")
            if value.startswith("data:image/png;base64,"):
                self.images[f"candidate/{self.rounds}/{index}.png"] = base64.b64decode(value.split(",", 1)[1], validate=True)
        response = {k: v for k, v in self.checked.items() if k != "comparison"}
        return text_result({**response, "round": self.rounds, "candidate_images": list(self.images)})

    @staticmethod
    def _image(name, raw):
        if len(raw) > 16 * 1024 * 1024 or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ExecutionError("invalid_input", "图片类型或大小无效")
        return text_result({"image": name}) + [{"type": "image", "data": base64.b64encode(raw).decode(), "mimeType": "image/png"}]

    def _deliver(self, proposed, args):
        verification = verification_template(self.packet)
        verification["abilities"].update(can_view_images=True, can_run_preflight=True, can_access_original_preview=True)
        # This protocol inspects real audio-bound frames/timing, not sound itself.
        for check in verification["checks"]:
            check.update(status="self_checked", evidence=["original-preview"])
            if check["criterion_id"] == "baseline_visual_review":
                check.update(evidence=sorted(self.baseline_seen), note=args["baseline_notes"][:2000])
            elif check["criterion_id"] == "candidate_visual_review":
                check.update(evidence=sorted(self.after_seen), note=args["candidate_notes"][:2000])
            elif self.packet["task_type"] == "static_repair":
                check["evidence"] = ["preflight.json", "original-preview"]
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("result.json", (self.folder / "result.json").read_bytes())
            archive.writestr("report.md", "# Pi候选执行报告\n\n" + args["baseline_notes"][:2000] + "\n\n" + args["candidate_notes"][:2000]
                             + "\n\n原系统检查通过；模型视觉自检，不代表人工批准。未保存作者。")
            archive.writestr("verification.json", json.dumps(verification, ensure_ascii=False))
            if self.preflight is not None:
                archive.writestr("preflight.json", json.dumps(self.preflight, ensure_ascii=False))
        payload = {"delivery_base64": base64.b64encode(stream.getvalue()).decode()}
        with project_artifact_lock(self.run):
            response = handoff.import_preview(self.run, self.project, self.slide, payload)
        if not response.get("passed"):
            raise ExecutionError("verification_failed", "最终导入复核失败")
        return {"delivery": payload, "preview": response, "saved": False, "human_approval": "not_requested"}
