"""Persistent human static amendments to an immutable, verified external delivery.

Caller holds project_artifact_lock. Work artifacts never confer author/approval
state; final persistence uses the existing editor and its invalidation owner.
"""
import copy

from artifact_fingerprint import sha256_json
import html_external_handoff as exchange
import html_scene_editing as editor
import html_scene_repair as repair
import html_visual_store as store
from html_handoff_contract import validate_operations
from html_handoff_models import ExternalResult, WorkReadRequest, WorkRequest
from html_handoff_execution import check_fonts
from html_repair_static import apply_static
from pipeline_lifecycle import write_json_atomic


def _file(run, ref):
    return exchange._directory(run, ref.task_id) / "human-work" / (ref.result_hash + ".json")


def _source(run, project_id, slide, ref):
    directory = exchange._directory(run, ref.task_id)
    accepted = editor.read_json(directory / "accepted-results" / (ref.result_hash + ".json"), {})
    if accepted.get("result_hash") != ref.result_hash:
        raise exchange.HandoffError("WORK_DELIVERY_REQUIRED", "请先导入完整交付；普通预览不授予人工接手资格")
    result = ExternalResult.model_validate(editor.read_json(directory / "results" / (ref.result_hash + ".json")))
    if sha256_json(result.model_dump(mode="json")) != ref.result_hash:
        raise exchange.HandoffError("WORK_RESULT_CHANGED", "原交付已变化")
    packet, result, body = exchange._request(run, project_id, slide, result)
    if packet["task_type"] != "static_repair" or result.status != "proposed":
        raise exchange.HandoffError("WORK_STATIC_ONLY", "人工工作区当前只接手合法静态候选")
    doc = editor.load_editor(run, slide)
    ai_scene = _apply(doc["scene"], body["operations"])
    editor.assert_manual_fields_unmodified(doc, ai_scene, doc["binding"])
    return packet, doc, ai_scene, body


def _apply(scene, operations):
    value = copy.deepcopy(scene)
    nodes = {node["id"]: node for node in value["nodes"]}
    for operation in operations:
        if operation["kind"] not in ("set_presentation", "set_text_style", "set_variant"):
            raise exchange.HandoffError("WORK_STATIC_ONLY", "人工接手不修改动作、绑定、原文或对象结构")
        apply_static(value, nodes[operation["targetId"]], operation)
    return value


def _load(run, ref):
    path = _file(run, ref)
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise exchange.HandoffError("WORK_MISSING", "尚无可恢复工作草稿")
    value = editor.read_json(path)
    if value.get("task_id") != ref.task_id or value.get("result_hash") != ref.result_hash:
        raise exchange.HandoffError("WORK_IDENTITY", "工作记录身份不匹配")
    return value


def _hash(work):
    return sha256_json({key: work[key] for key in ("task_id", "result_hash", "work_revision", "operations")})


def _version(work, request):
    if work["work_revision"] != request.work_revision:
        raise exchange.HandoffError("WORK_CONFLICT", "工作草稿已变化，请读取最新版本；本地修改保留", 409)
    if work.get("saved_revision") is not None:
        raise exchange.HandoffError("WORK_ALREADY_SAVED", "本工作草稿已保存，请从当前页面重新导出", 409)


def _candidate(run, project_id, slide, ref, work):
    packet, doc, ai_scene, body = _source(run, project_id, slide, ref)
    if not all(validate_operations(packet["operation_schema"], work["operations"])):
        raise exchange.HandoffError("WORK_SCOPE", "人工操作超出原任务scope、注册部位或字段范围")
    scene = _apply(ai_scene, work["operations"])
    return packet, doc, ai_scene, body, scene


def open_work(run, project_id, slide, payload):
    ref = WorkReadRequest.model_validate(payload)
    _source(run, project_id, slide, ref)
    if not _file(run, ref).exists():
        write_json_atomic(_file(run, ref), {"task_id": ref.task_id, "result_hash": ref.result_hash,
            "work_revision": 0, "operations": [], "check": None, "saved_revision": None})
    return read_work(run, project_id, slide, ref)


def read_work(run, project_id, slide, payload):
    ref = WorkReadRequest.model_validate(payload)
    # Enforce ownership even when returning a stale work record.
    exchange.load_task(run, project_id, slide, ref.task_id)
    work = _load(run, ref)
    if work.get("saved_revision") is not None:
        return {"work": work, "saved": True, "stale": False, "editable": False}
    try:
        packet, doc, _, _, scene = _candidate(run, project_id, slide, ref, work)
    except (exchange.HandoffError, editor.SceneEditError, store.HtmlVisualConflict) as exc:
        intent = work.get("save_intent")
        current = editor.load_editor(run, slide)
        saved = bool(intent and current["revision"] == intent["revision"] and sha256_json(current["scene"]) == intent["scene_hash"])
        return {"work": work, "stale": not saved, "saved": saved, "message": str(exc), "editable": False}
    return {"work": work, "working_hash": _hash(work), "stale": False, "saved": False, "editable": True,
            "scope": packet["scope"], "scene": scene, "baseline_revision": doc["revision"],
            "font_requirements": packet["context"]["execution"].get("font_requirements", []),
            "operation_schema": packet["operation_schema"]}


def update_work(run, project_id, slide, payload):
    request = WorkRequest.model_validate(payload)
    work = _load(run, request)
    _version(work, request)
    next_work = {**work, "operations": [op.model_dump(exclude_none=True) for op in request.operations],
                 "work_revision": work["work_revision"] + 1, "check": None, "save_intent": None}
    _candidate(run, project_id, slide, request, next_work)
    # Invalid geometry/capacity may be retained as a bounded draft; no author write.
    write_json_atomic(_file(run, request), next_work)
    return read_work(run, project_id, slide, request)


def check_work(run, project_id, slide, payload):
    request = WorkRequest.model_validate(payload)
    work = _load(run, request)
    _version(work, request)
    packet, doc, _, body, scene = _candidate(run, project_id, slide, request, work)
    if [op.model_dump(exclude_none=True) for op in request.operations] != work["operations"]:
        raise exchange.HandoffError("WORK_CONFLICT", "请先保存当前操作到工作草稿，再运行检查", 409)
    acceptance = check_fonts(packet, scene)
    diagnostic, images = None, []
    try:
        preview = editor.preview_editor(run, slide, scene, doc["binding"], expected_revision=doc["revision"], expected_audio_revision=body["expected_audio_revision"])
        review = repair.evidence(run, slide, body, preview)
        passed = review["passed"] and not any(item["status"] == "failed" for item in acceptance)
    except editor.SceneEditError as exc:
        review = {"passed": False, "validation": {"code": exc.code, "message": str(exc), "stage": "original_work_preview"}}
        passed = False
    from html_handoff_diagnostics import diagnose, pictures
    if not passed:
        diagnostic = diagnose(run, slide, scene, doc["binding"], doc["revision"], body["expected_audio_revision"])
        images = pictures(run, diagnostic.get("screenshots", []))
    else:
        images = pictures(run, review.get("screenshots", []))
    checked = {"working_hash": _hash(work), "passed": bool(passed), "acceptance": acceptance,
               "review": review, "diagnostic": diagnostic}
    work["check"] = checked
    write_json_atomic(_file(run, request), work)
    return {**read_work(run, project_id, slide, request), "pictures": images}


def save_work(run, project_id, slide, payload):
    request = WorkRequest.model_validate(payload)
    work = _load(run, request)
    _version(work, request)
    if not (work.get("check") or {}).get("passed") or work["check"]["working_hash"] != _hash(work):
        raise exchange.HandoffError("WORK_VALID_CHECK_REQUIRED", "需要当前工作草稿完整通过检查后才能保存")
    # Recheck the unchanged work and all current dependencies, using original player.
    response = check_work(run, project_id, slide, request)
    if not response["work"]["check"]["passed"]:
        raise exchange.HandoffError("WORK_VALID_CHECK_REQUIRED", "当前工作草稿复核未通过；修改保留")
    _, doc, ai_scene, body, scene = _candidate(run, project_id, slide, request, work)
    work = _load(run, request)
    work["save_intent"] = {"revision": doc["revision"] + 1, "scene_hash": sha256_json(scene)}
    write_json_atomic(_file(run, request), work)
    # AI has already passed the unchanged original protection guard. Only human
    # differences relative to ai_scene become new protected leaves in this path.
    saved = editor.save_editor(run, slide, scene, doc["binding"], doc["revision"], origin="human",
                               expected_audio_revision=body["expected_audio_revision"], _human_base_scene=ai_scene)
    work["saved_revision"] = saved["revision"]
    work["save_result"] = saved
    write_json_atomic(_file(run, request), work)
    return {**saved, "saved": True, "work": work}
