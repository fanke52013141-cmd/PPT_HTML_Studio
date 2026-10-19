"""Portable page evidence and guarded external proposals over existing repair services."""
from __future__ import annotations

import copy
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import zipfile

from artifact_fingerprint import sha256_file, sha256_json
import html_scene_editing as editor
import html_scene_repair as repair
import html_visual_store as store
from html_handoff_contract import RULES, operation_schema, validate_operations
from html_handoff_models import ExportRequest, ExternalResult, TaskPacket
from pipeline_lifecycle import write_json_atomic


ROOT = Path(__file__).resolve().parent
DIRECTORY = store.SCENE_DIR / "external-handoffs"
MAX_BYTES = 64 * 1024 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024


class HandoffError(ValueError):
    def __init__(self, code, message, status_code=422):
        super().__init__(message)
        self.code, self.status_code = code, status_code


def _file(root, name):
    name = str(name)
    parts = PurePosixPath(name)
    if "\\" in name or ":" in name or parts.is_absolute() or any(p in ("", ".", "..") for p in name.split("/")):
        raise HandoffError("HANDOFF_PATH", "交接材料路径无效")
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise HandoffError("HANDOFF_FILE_MISSING", "交接材料缺失或路径越界")
    return path


def _directory(run, task_id):
    if not re.fullmatch(r"[0-9a-f]{64}", task_id):
        raise HandoffError("HANDOFF_ID", "任务标识无效")
    path = Path(run) / DIRECTORY / task_id
    if not path.resolve().is_relative_to(Path(run).resolve()):
        raise HandoffError("HANDOFF_PATH", "交接任务路径越界")
    return path


def _contract(run, slide):
    value = editor.read_json(Path(run) / "planning/visual_contract.json", {})
    page = next((p for p in value.get("slides", []) if p.get("slide_id") == slide), None)
    if not page or not page.get("narration_beats"):
        raise HandoffError("HANDOFF_CONTENT_REQUIRED", "缺少本页权威内容和讲稿语块，请先完成规划")
    return page


def _definitions():
    paths = [ROOT / name for name in (
        "html_engine/visual/generated/catalog.json", "html_engine/visual/schema.json",
        "html_engine/visual/preview/player.js", "html_engine/visual/preview/data.js", "html_engine/tools/browser-runtime.cjs",
        "html_engine/tools/review-temporal.cjs", "html_engine/tools/temporal-review.cjs",
        "html_engine/visual/qa/overlap-policy.json", "html_handoff_contract.py", "html_handoff_models.py",
        "html_scene_repair.py", "html_scene_editing.py", "html_design_policy.py", "html_external_handoff.py",
        "html_motion_binding.py", "html_audio_binder.py", "html_motion_activity.py",
        "html_handoff_delivery.py",
        "docs/agent/external-agent-execution.md", "docs/agent/external-agent-report-template.md")]
    from html_handoff_execution import definition_files
    paths += [ROOT / name for name in definition_files()]
    identities = {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}
    font_root = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    identities["local_fonts"] = {name: sha256_file(font_root / name) if (font_root / name).is_file() else None
                                 for name in ("msyh.ttc", "msyhbd.ttc", "msyhl.ttc")}
    return identities


def _design(run, slide, key=None):
    from html_design_candidates import candidate_directory, current_design
    base = Path(run) / store.SCENE_DIR / "candidates" / slide
    if key is None:
        key = (editor.read_json(base / "current-design.json", {}) or {}).get("key")
    if not key:
        return None
    current = current_design(run_dir=run, contract=_contract(run, slide), repo_root=ROOT).get("design")
    if not current or current["key"] != key:
        raise HandoffError("HANDOFF_DESIGN_CHANGED", "请选择当前设计参考，不能交接历史候选", 409)
    directory = candidate_directory(run, slide, key)
    record = editor.read_json(_file(run, (directory / "candidate.json").relative_to(run).as_posix()))
    image = _file(run, (directory / "design-reference.png").relative_to(run).as_posix())
    if (sha256_json(record) != key or sha256_file(image) != record["image_sha256"] or record["slide_id"] != slide):
        raise HandoffError("HANDOFF_DESIGN_CHANGED", "设计参考身份或图片字节不匹配", 409)
    return {"key": key, "image_sha256": record["image_sha256"], "_image": image,
            "status": current["status"], "stale": current["stale"],
            "plan": record["plan"], "brief": record["brief"]}


def _identity(run, slide, doc, design):
    return {"content": sha256_json(_contract(run, slide)), "definitions": _definitions(),
            "author": sha256_json({k: doc.get(k) for k in ("scene", "binding", "manual", "resources", "beats")}) if doc else None,
            "asset_bytes": {str(node["id"]): sha256_file(path) for node, _, path in _asset_sources(run, doc)} if doc else {},
            "design": {k: design[k] for k in ("key", "image_sha256", "status", "stale")} if design else None}


def _resolved(catalog, group, reference):
    value = next((item for item in catalog[group] if item["id"] == reference["id"]
                  and item["version"] == reference["version"]), None)
    if value is None:
        raise HandoffError("HANDOFF_DEFINITION_MISSING", "当前主题或布局定义无法解析")
    return copy.deepcopy(value)


class Package:
    def __init__(self):
        self.files, self.data = [], {}

    def add(self, name, data, role, media):
        if name in self.data or len(data) > MAX_FILE_BYTES or sum(map(len, self.data.values())) + len(data) > MAX_BYTES:
            raise HandoffError("HANDOFF_BUDGET", "交接材料超过大小限制或路径重复")
        self.data[name] = data
        self.files.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
                           "role": role, "media_type": media})
        return name

    def json(self, name, value, role):
        return self.add(name, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode(), role, "application/json")

    def image(self, name, path, role, expected=None):
        from PIL import Image
        if path.stat().st_size > MAX_FILE_BYTES:
            raise HandoffError("HANDOFF_BUDGET", "交接图片超过大小限制")
        data = path.read_bytes()
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise HandoffError("HANDOFF_ASSET_CHANGED", "图片字节与登记不符", 409)
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG" or image.width * image.height > 4194304:
                raise HandoffError("HANDOFF_IMAGE_INVALID", "交接图片格式或尺寸无效")
            image.verify()
        return self.add(name, data, role, "image/png")


def _asset_sources(run, doc, catalog=None):
    catalog = catalog or editor.read_json(ROOT / "html_engine/visual/generated/catalog.json")
    assets = {item["id"]: item for item in catalog["assets"] + doc["resources"]["assets"]}
    for node in doc["scene"]["nodes"]:
        if node["type"] == "image":
            asset = copy.deepcopy(assets[node["assetRef"]["id"]])
            # Production's Windows resource manifest may contain native separators.
            # Normalize that validated source path; portable packet paths stay strict.
            path = asset["file"]["path"].replace("\\", "/")
            source = _file(run, path[len("project/"):]) if path.startswith("project/") else _file(ROOT, path)
            yield node, asset, source


def _assets(package, run, doc, catalog):
    result = []
    for node, asset, source in _asset_sources(run, doc, catalog):
        name = f"assets/{asset['file']['sha256']}.png"
        if name not in package.data:
            package.image(name, source, "independent_asset", asset["file"]["sha256"])
        asset["file"]["path"] = name
        result.append({"targetId": node["id"], "asset": asset})
    return result


def _evidence(package, run, report, prefix="evidence"):
    result = copy.deepcopy(report)
    for index, shot in enumerate(result.get("screenshots", [])):
        shot["file"] = package.image(f"{prefix}/frame-{index}.png", _file(run, shot["file"]),
                                     "diagnostic_render" if report.get("diagnosticOnly") else "actual_render")
    result.pop("evidence_dir", None)
    result.pop("measurements_path", None)
    return result


def export_bundle(run, project_id, slide, request):
    """Caller holds the existing project artifact lock. No author/provider writes."""
    request = ExportRequest.model_validate(request)
    slide = store.validate_slide_id(slide)
    run = Path(run).resolve()
    revision = store._read_revision(run)["revision"]
    if request.expected_revision is not None and request.expected_revision != revision:
        raise store.HtmlVisualConflict(request.expected_revision, revision)
    content = _contract(run, slide)
    design = _design(run, slide, request.design_candidate_key)
    doc = None if request.task_type == "design_reference" else editor.load_editor(run, slide)
    audio = editor._check_audio_revision(run, slide, request.expected_audio_revision)
    source = _identity(run, slide, doc, design)
    package = Package()
    for name, source_name, role in (
        ("EXECUTION.md", "external-agent-execution.md", "execution_contract"),
        ("report-template.md", "external-agent-report-template.md", "report_template"),
    ):
        package.add(name, (ROOT / "docs/agent" / source_name).read_bytes(), role, "text/markdown")
    package.json("content.json", content, "authoritative_content")
    context = {"content": "content.json", "design": None, "clock": "not_applicable", "missing_inputs": []}
    catalog = editor.read_json(ROOT / "html_engine/visual/generated/catalog.json")
    if design:
        image = package.image("reference/design.png", design["_image"], "design_reference", design["image_sha256"])
        context["design"] = {key: design[key] for key in ("key", "image_sha256", "status", "stale")}
        context["design"]["file"] = image
    if doc:
        if not set(request.scope) <= {node["id"] for node in doc["scene"]["nodes"]}:
            raise HandoffError("REPAIR_SCOPE", "范围包含不存在的对象")
        preview = editor.preview_editor(run, slide, doc["scene"], doc["binding"], expected_revision=revision,
                                        expected_audio_revision=audio)
        if request.task_type == "animation_repair" and preview["clock"] != "audio_timeline":
            raise HandoffError("REAL_AUDIO_TIMING_REQUIRED", "动画修复需要真实音频时间轴")
        from html_design_agent import component_context
        capabilities = component_context(doc["scene"], ROOT)
        operations = operation_schema(doc, capabilities, request.scope, request.task_type)
        context.update({"scene": doc["scene"], "binding": doc["binding"], "beats": doc["beats"],
                        "bound_scene": preview["scene"], "timing": preview["timing"], "clock": preview["clock"],
                        "protected_paths": editor.manual_protected_paths(doc.get("manual")),
                        "capabilities": capabilities, "assets": _assets(package, run, doc, catalog)})
        theme_ref, layout_ref = doc["scene"]["themeRef"], doc["scene"]["layoutRef"]
        try:
            report = repair.evidence(run, slide, {"expected_revision": revision, "expected_audio_revision": audio,
                                                 "overlap_pairs": request.overlap_pairs, "overlap_policy": request.overlap_policy})
        except editor.SceneEditError as exc:
            if not request.allow_diagnostic_baseline or "CONTENT_CAPACITY_EXCEEDED" not in str(exc):
                raise
            from html_handoff_diagnostics import diagnose
            report = diagnose(run, slide, doc["scene"], doc["binding"], revision, audio)
            report["baseline_failed"] = True
        context["evidence"] = _evidence(package, run, report)
        if not context["evidence"].get("screenshots"):
            raise HandoffError("HANDOFF_EVIDENCE_REQUIRED", "缺少实际播放器截图")
        for file, media in (("voice.mp3", "audio/mpeg"), ("audio_timeline.json", "application/json"),
                            ("subtitles.srt", "application/x-subrip")):
            path = run / "slides" / slide / file
            if path.is_file():
                path = _file(run, path.relative_to(run).as_posix())
                package.add("audio/" + file, path.read_bytes(), "original_audio" if file == "voice.mp3" else "audio_timing", media)
            elif request.task_type == "animation_repair" and file in ("voice.mp3", "audio_timeline.json"):
                raise HandoffError("HANDOFF_AUDIO_REQUIRED", "动画修复缺少原音轨或时间轴")
    else:
        if not design:
            raise HandoffError("HANDOFF_DESIGN_REQUIRED", "请先生成设计参考")
        package.json("planning.json", {"plan": design["plan"], "brief": design["brief"]}, "authoritative_plan")
        # Production plans own structure; the design brief owns the selected theme.
        # Never assume that a planning payload has author-scene themeRef fields.
        theme_ref = design["plan"].get("themeRef")
        if not theme_ref:
            themes = [item for item in catalog["themes"] if item["id"] == design["brief"].get("theme")]
            if len(themes) != 1:
                raise HandoffError("HANDOFF_DEFINITION_MISSING", "设计风格缺失或版本不唯一，请核对原设计定义")
            theme_ref = {key: themes[0][key] for key in ("id", "version")}
        layout_ref = design["plan"]["layoutRef"]
        operations = {"not": {}}
        context["missing_inputs"] = ["registered editable scene and validated independent assets; continue original production before repair"]
    context["style"] = {"theme": _resolved(catalog, "themes", theme_ref),
                        "layout": _resolved(catalog, "layouts", layout_ref),
                        "font_distribution": "Use the named local font; system font files are not redistributed."}
    from html_handoff_execution import create_execution, checker_bytes
    context["execution"] = create_execution(doc, request)
    from html_handoff_models import ExternalVerification
    package.json("constraints.json", context["execution"], "execution_constraints")
    for item in context["execution"].get("capacity_constraints", []):
        for part, fact in item["parts"].items():
            actual = context.get("evidence", {}).get("capacity_measurements", {}).get(item["targetId"] + ":" + part)
            if actual:
                fact["measured"] = actual["measured"]
                fact["measurement_status"] = "original_dom_baseline"
    # Materialize after actual baseline measurements have been attached.
    package.data.pop("constraints.json")
    package.files[:] = [entry for entry in package.files if entry["path"] != "constraints.json"]
    package.json("constraints.json", context["execution"], "execution_constraints")
    package.add("CONTRACT-2.1.md", (ROOT / "docs/contracts/html-presentation/runtime/visual-v1/external-agent-workbench-0.1.0.md").read_bytes(), "execution_extension", "text/markdown")
    package.add("ENTRY.md", (ROOT / "docs/agent/external-agent-entry.md").read_bytes(), "execution_entry", "text/markdown")
    package.json("decision-input.json", {"goal": request.goal, "task_type": request.task_type,
        "scope": request.scope, "authoritative_content": "content.json", "canonical_input": "task.json",
        "verification_required": context["execution"]["verification_required"],
        "required_abilities": context["execution"]["required_abilities"],
        "targets": [node for node in (doc or {}).get("scene", {}).get("nodes", []) if node["id"] in request.scope],
        "readonly_neighbors": [node["id"] for node in (doc or {}).get("scene", {}).get("nodes", []) if node["id"] not in request.scope],
        "font_requirements": context["execution"]["font_requirements"],
        "capacity_constraints": context["execution"].get("capacity_constraints", []),
        "hard_constraints": context["execution"]["hard_constraints"],
        "overlap_coverage": context["execution"].get("overlap_coverage"),
        "protected_paths": context.get("protected_paths", []), "actual_evidence": context.get("evidence"),
        "rules": RULES, "tool_coverage": context["execution"]["portable_checker_scope"]}, "agent_decision_view")
    package.json("verification.schema.json", ExternalVerification.model_json_schema(), "verification_schema")
    package.add("CONTRACT.md", (ROOT / "docs/contracts/html-presentation/runtime/visual-v1/external-agent-execution-2.0.0.md").read_bytes(),
                "execution_definition", "text/markdown")
    package.add("tools/check_task.py", (ROOT / "scripts/check_external_task.py").read_bytes(), "official_preflight", "text/x-python")
    package.add("tools/html_repair_static.py", (ROOT / "html_repair_static.py").read_bytes(), "shared_static_operations", "text/x-python")
    package.add("tools/preflight.cjs", checker_bytes(), "shared_production_compiler", "text/javascript")
    result_schema = ExternalResult.model_json_schema()
    result_schema["$defs"]["RepairOperation"] = operations
    result_schema["allOf"] = [{"if": {"properties": {"status": {"const": "proposed"}}, "required": ["status"]},
                               "then": {"properties": {"operations": {"minItems": 1}}, "required": ["operations"]},
                               "else": {"properties": {"operations": {"maxItems": 0}}}}]
    result_template = {"format": "hps.html.external_result", "version": "0.2.0", "task_id": "",
                       "status": "needs_input", "message": "请填写实际处理结果", "operations": [],
                       "changes": [], "issues": [], "required_inputs": [],
                       "usage": {"calls": None, "elapsed_seconds": None, "tokens": None, "cost": None, "currency": None}}
    # task_id is filled in the template after sealing the task; template is auxiliary,
    # not a hashed input file (avoids a circular task/template identity).
    packet = {"format": "hps.html.external_task", "version": "0.2.0", "project_id": project_id, "slide_id": slide,
              "task_type": request.task_type, "goal": request.goal, "scope": request.scope,
              "contract_hash": _contract_hash(), "expected_revision": revision, "audio_revision": audio,
              "context": context, "rules": copy.deepcopy(RULES), "operation_schema": operations,
              "result_schema": result_schema, "files": package.files, "source_identity": source}
    packet["task_id"] = sha256_json(packet)
    TaskPacket.model_validate(packet)
    result_template["task_id"] = packet["task_id"]
    from html_handoff_execution import verification_template
    verification = verification_template(packet)
    if (revision != store._read_revision(run)["revision"] or audio != editor.audio_revision(run, slide)
            or source != _identity(run, slide, editor.load_editor(run, slide) if doc else None,
                                   _design(run, slide, design["key"]) if design else None)):
        raise HandoffError("HANDOFF_INPUT_CHANGED", "导出期间输入变化，请重新导出", 409)
    directory = _directory(run, packet["task_id"])
    if (directory / "task.json").is_file():
        # A sealed package is immutable, including while FileResponse streams it.
        # Re-export must verify and reuse it rather than truncate the same ZIP.
        previous = load_task(run, project_id, slide, packet["task_id"])
        bundle_path(run, project_id, slide, packet["task_id"])
        return {"task": previous}
    directory.mkdir(parents=True, exist_ok=True)
    archive = io.BytesIO()
    readme = ("# 外部 Agent 任务包\n\n先读 ENTRY.md、decision-input.json，再按引用读 task.json 的 goal、rules、context、operation_schema 和 result_schema。\n"
              "content.json 为权威内容；reference/design.png 是设计参考，evidence 是实际画面。\n"
              "先按constraints.json.required_abilities核对能力；缺任一必需能力返回needs_input/unsupported且operations=[]，proposed或not_run不能豁免。\n"
              "按manifest.json及存在的trial-manifest.json核对SHA256/字节数；它们是本轮材料校验，不是旧答案。原文/人工保护优先于参考图，所有路径相对本包。\n"
              "要求看图的候选须实际审阅原图，baseline_visual_review记录self_checked及实际证据；仅填能力true不足。无原预览接口时原DOM/遮挡/after可not_run，由系统接续。\n"
              "按执行规范诊断、最小修改、自检；修改 result-template.json，另存 result.json，并填写 report.md。\n"
              "严格任务交付delivery.zip：result.json、report.md、verification.json；静态候选再附preflight.json（可选真实证据）；不修改 task.json，不返回 HTML/JS 或整页位图。\n"
              "没有所需资料或能力时返回 needs_input/unsupported。design_reference 不接受操作保存。\n"
              "系统导入后重新检查预览，显式保存后仍须原画面/语义/音频验收。\n")
    payloads = {**package.data, "task.json": json.dumps(packet, ensure_ascii=False, indent=2).encode(),
                "verification-template.json": json.dumps(verification, ensure_ascii=False, indent=2).encode(),
                "README.md": readme.encode(), "result-template.json": json.dumps(result_template, ensure_ascii=False, indent=2).encode()}
    manifest = {"format": "hps.html.external_bundle", "version": "0.2.0", "task_id": packet["task_id"],
                "files": [{"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
                          for name, data in payloads.items()]}
    payloads["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name, data in payloads.items():
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(entry, data)
    bundle = archive.getvalue()
    if len(bundle) > MAX_BYTES:
        raise HandoffError("HANDOFF_BUDGET", "交接包超过大小限制")
    (directory / "bundle.zip").write_bytes(bundle)
    # Store a private exact input copy so the importer can verify every manifest file.
    with zipfile.ZipFile(io.BytesIO(bundle)) as zipped:
        for name in package.data:
            destination = directory / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(zipped.read(name))
    write_json_atomic(directory / "task.json", packet)
    write_json_atomic(directory / "bundle-identity.json", {"sha256": hashlib.sha256(bundle).hexdigest()})
    return {"task": packet}


def _contract_hash():
    from agent_contract.versions import get_contract_hash
    return get_contract_hash()


def load_task(run, project_id, slide, task_id):
    directory = _directory(run, task_id)
    try:
        packet = editor.read_json(_file(directory, "task.json"))
        TaskPacket.model_validate(packet)
        if (packet["task_id"] != task_id or sha256_json({k: v for k, v in packet.items() if k != "task_id"}) != task_id
                or packet["project_id"] != project_id or packet["slide_id"] != slide):
            raise ValueError("identity")
        for entry in packet["files"]:
            path = _file(directory, entry["path"])
            if path.stat().st_size != entry["size"] or sha256_file(path) != entry["sha256"]:
                raise ValueError("file")
        return packet
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HandoffError("HANDOFF_INVALID", "交接任务不存在或身份/材料已变化", 409) from exc


def bundle_path(run, project_id, slide, task_id):
    load_task(run, project_id, slide, task_id)
    directory = _directory(run, task_id)
    path = _file(directory, "bundle.zip")
    if sha256_file(path) != editor.read_json(_file(directory, "bundle-identity.json"))["sha256"]:
        raise HandoffError("HANDOFF_INVALID", "交接包字节已变化", 409)
    return path


def _request(run, project_id, slide, result):
    result = ExternalResult.model_validate(result)
    packet = load_task(run, project_id, slide, result.task_id)
    if packet["contract_hash"] != _contract_hash():
        raise HandoffError("CONTRACT_CHANGED", "接口契约已变化，请重新导出", 409)
    if packet["expected_revision"] != store._read_revision(run)["revision"]:
        raise HandoffError("REVISION_CHANGED", "页面修订已变化，请重新导出", 409)
    editor._check_audio_revision(run, slide, packet["audio_revision"])
    doc = editor.load_editor(run, slide) if packet["task_type"] != "design_reference" else None
    key = (packet["context"].get("design") or {}).get("key")
    if _identity(run, slide, doc, _design(run, slide, key) if key else None) != packet["source_identity"]:
        raise HandoffError("HANDOFF_INPUT_CHANGED", "内容、素材、风格或运行定义已变化，请重新导出", 409)
    operations = [operation.model_dump(exclude_none=True) for operation in result.operations]
    if operations and not all(validate_operations(packet["operation_schema"], operations)):
        raise HandoffError("HANDOFF_OPERATION", "操作不符合本任务的对象、字段、单位、范围或阶段约束")
    body = {"expected_revision": packet["expected_revision"], "expected_audio_revision": packet["audio_revision"],
            "source": "ai", "scope": packet["scope"], "operations": [o.model_dump(exclude_none=True) for o in result.operations]}
    body.update(packet["context"].get("execution", {}).get("temporal_spec", {}))
    return packet, result, body


def preview_result(run, project_id, slide, result):
    packet, result, body = _request(run, project_id, slide, result)
    result_hash = sha256_json(result.model_dump(mode="json"))
    write_json_atomic(_directory(run, result.task_id) / "results" / (result_hash + ".json"), result.model_dump(mode="json"))
    reported = {"usage": result.usage.model_dump(), "usage_source": "external_report_unverified"}
    if result.status != "proposed":
        return {"status": result.status, "message": result.message, "issues": [i.model_dump() for i in result.issues],
                "required_inputs": result.required_inputs, "changes": result.changes, **reported, "saved": False}
    preview = repair.preview_repair(run, slide, body)
    from html_handoff_execution import check_fonts
    acceptance = check_fonts(packet, preview["scene"])
    if any(check["status"] == "failed" for check in acceptance):
        preview["review"]["passed"] = False
        preview["review"].setdefault("issues", []).extend(acceptance)
    receipt = {"task_id": result.task_id, "result_hash": result_hash,
               "candidate_key": preview["candidate_key"], "passed": preview["review"]["passed"]}
    write_json_atomic(_directory(run, result.task_id) / "preview.json", receipt)
    def images(root, report):
        return [{"timeMs": item["timeMs"], "image": "data:image/png;base64," + base64.b64encode(
            _file(root, item["file"]).read_bytes()).decode()} for item in (report or {}).get("screenshots", [])[-2:]]
    return {"status": "candidate", **receipt, "diff": preview["diff"], "review": preview["review"],
            "message": result.message, "changes": result.changes, "issues": [i.model_dump() for i in result.issues], **reported,
            "acceptance": acceptance,
            "comparison": {"before": images(_directory(run, result.task_id), packet["context"].get("evidence")),
                           "after": images(run, preview["review"])}, "saved": False}


def import_preview(run, project_id, slide, payload):
    """Normalize a result or delivery, archive evidence, then reuse original preview."""
    from html_handoff_delivery import DeliveryError, read_delivery
    try:
        result, delivery, files, raw = read_delivery(payload)
    except DeliveryError as exc:
        raise HandoffError("HANDOFF_DELIVERY_INVALID", str(exc)) from exc
    # Reject foreign/stale/invalid operations before retaining external material.
    packet, _, _ = _request(run, project_id, slide, result)
    from html_handoff_execution import validate_verification
    try:
        verification = validate_verification(packet, result, files)
    except ValueError as exc:
        raise HandoffError("HANDOFF_VERIFICATION", str(exc)) from exc
    result_hash = sha256_json(result.model_dump(mode="json"))
    write_json_atomic(_directory(run, result.task_id) / "accepted-results" / (result_hash + ".json"),
                      {"result_hash": result_hash, "verification": verification})
    directory = _directory(run, result.task_id) / "deliveries" / sha256_json(delivery)
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    if delivery["kind"] == "zip":
        (directory / "delivery.zip").write_bytes(raw)
    write_json_atomic(directory / "manifest.json", delivery)
    try:
        response = preview_result(run, project_id, slide, result)
    except editor.SceneEditError as exc:
        if exc.code == "AUDIO_REVISION_CONFLICT":
            raise
        response = {"status": "checks_failed", "passed": False, "saved": False,
                    "task_id": result.task_id, "result_hash": sha256_json(result.model_dump(mode="json")),
                    "message": "原系统检查未通过，候选未保存。", "changes": result.changes,
                    "issues": [issue.model_dump() for issue in result.issues],
                    "validation": {"code": exc.code, "message": str(exc)[:4000], "stage": "original_repair_preview"}}
    diagnostic = None
    if not response.get("passed") and result.status == "proposed" and packet["task_type"] == "static_repair":
        from html_handoff_workbench import _apply
        from html_handoff_diagnostics import diagnose, pictures
        doc = editor.load_editor(run, slide)
        scene = _apply(doc["scene"], [op.model_dump(exclude_none=True) for op in result.operations])
        editor.assert_manual_fields_unmodified(doc, scene, doc["binding"])
        diagnostic = diagnose(run, slide, scene, doc["binding"], packet["expected_revision"], packet["audio_revision"])
        response["diagnostic"] = diagnostic
        response["diagnostic_pictures"] = pictures(run, diagnostic.get("screenshots", []))
    feedback = {"format": "hps.html.external_feedback", "version": "0.1.0", "task_id": result.task_id,
                "result_hash": sha256_json(result.model_dump(mode="json")), "status": response["status"],
                "passed": bool(response.get("passed")), "saved": False, "validation": response.get("validation"),
                "review": response.get("review"), "diff": response.get("diff"), "diagnostic": diagnostic,
                "next_action": "检查通过后人工核对并显式保存；未通过则向同一Agent反馈。身份/版本变化必须重新导出。"}
    write_json_atomic(directory / "feedback.json", feedback)
    if response.get("passed") and verification is not None:
        write_json_atomic(_directory(run, result.task_id) / "adoption-eligibility.json",
                          {"result_hash": feedback["result_hash"], "verification": verification})
    from html_handoff_diagnostics import feedback_bundle
    return {**response, "delivery": delivery, "result": result.model_dump(mode="json"), "feedback": feedback,
            "feedback_bundle_base64": feedback_bundle(run, feedback, diagnostic),
            "external_verification": verification}


def save_result(run, project_id, slide, request):
    from html_handoff_models import SaveRequest
    request = SaveRequest.model_validate(request)
    packet, result, body = _request(run, project_id, slide, request.result)
    if packet["context"].get("execution", {}).get("verification_required"):
        eligibility = editor.read_json(_directory(run, result.task_id) / "adoption-eligibility.json", {})
        if eligibility.get("result_hash") != sha256_json(result.model_dump(mode="json")):
            raise HandoffError("HANDOFF_VERIFICATION", "需要当前结果的完整严格交付与原系统通过预览")
    if (_directory(run, result.task_id) / "saved.json").is_file():
        raise HandoffError("HANDOFF_ALREADY_SAVED", "该交接结果已保存，请读取当前页面后重新导出", 409)
    receipt = editor.read_json(_directory(run, result.task_id) / "preview.json", {})
    expected = {"task_id": result.task_id, "result_hash": sha256_json(result.model_dump(mode="json")),
                "candidate_key": request.candidate_key, "passed": True}
    if result.status != "proposed" or receipt != expected or request.result_hash != expected["result_hash"]:
        raise HandoffError("VALID_PREVIEW_REQUIRED", "需要同一结果的当前通过预览", 409)
    saved = repair.save_repair(run, slide, {**body, "candidate_key": request.candidate_key})
    write_json_atomic(_directory(run, result.task_id) / "saved.json", {"result_hash": request.result_hash,
                                                                      "revision": saved["revision"]})
    return saved


def workbench_read(run, project_id, slide, request):
    """Read-only Agent view; human amendments are intentionally not Agent tools."""
    from html_handoff_workbench import read_work
    return read_work(run, project_id, slide, request)
