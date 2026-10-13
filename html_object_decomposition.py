"""Pure A02 object ownership, whole-asset control, budget and state validation."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from artifact_fingerprint import sha256_json

from html_narration_semantics import NarrationSemanticError
from html_scene_plan_models import FrozenSemanticBeat, ObjectSemantics


def resolve_existing_resources(plan: dict, run_dir: Path, *, contract: dict) -> dict | None:
    """Resolve selected project resources through the byte-verifying shared loader."""
    from html_storyboard_planning import HtmlScenePlanError

    if not isinstance(plan.get("objects"), list) or not isinstance(plan.get("slots"), dict):
        return None  # The normalizer owns the structural diagnostic.
    objects = {obj.get("id"): obj for obj in plan["objects"] if isinstance(obj, dict) and isinstance(obj.get("id"), str)}
    refs = []
    for item in plan.get("objectSemantics", []) if isinstance(plan.get("objectSemantics"), list) else []:
        if isinstance(item, dict) and item.get("sourceMode") == "existing":
            obj = objects.get(item.get("objectId")) if isinstance(item.get("objectId"), str) else None
            content = plan["slots"].get(obj["slot"], {}) if obj and isinstance(obj.get("slot"), str) else {}
            ref = content.get("assetRef") if isinstance(content, dict) else None
            if isinstance(ref, dict) and isinstance(ref.get("id"), str) and isinstance(ref.get("version"), str):
                refs.append(ref)
    if not refs:
        return None
    offered = {(ref.get("id"), ref.get("version"))
               for group in contract.get("visual_groups", []) if isinstance(group, dict)
               for asset in group.get("available_assets", []) if isinstance(asset, dict)
               for ref in [asset.get("assetRef", {})] if isinstance(ref, dict)}
    if any((ref["id"], ref["version"]) not in offered for ref in refs):
        raise HtmlScenePlanError("DECOMPOSITION_RESOURCE_NOT_OFFERED", "不能引用本次输入未提供的已有素材")
    from html_scene_editing import SceneEditError, resources

    try:
        return resources(run_dir, asset_refs=refs)
    except SceneEditError as exc:
        raise HtmlScenePlanError("DECOMPOSITION_RESOURCE_INVALID", "已有素材实际字节或资源清单未通过验证") from exc


def _reject(code: str, message: str):
    raise NarrationSemanticError(code, message)


def normalize_decomposition(plan: dict, *, asset_budget: int = 1, resources: dict | None = None) -> dict:
    if type(asset_budget) is not int or not 0 <= asset_budget <= 2:
        _reject("BRIEF_BUDGET_INVALID", "独立主体预算必须是 0—2 的整数")
    raw = plan.get("objectSemantics")
    if not isinstance(raw, list) or not raw or len(raw) > 64:
        _reject("DECOMPOSITION_MISSING", "所有实际对象必须声明语义分工（1—64项）")
    objects = {obj["id"]: obj for obj in plan["objects"]}
    definitions = {}
    image_count = 0
    anchors = {}
    needs = [asset for asset in plan["assets"] if asset["render_owner"] == "image_asset"]
    if len({asset["id"] for asset in plan["assets"]}) != len(plan["assets"]):
        _reject("DECOMPOSITION_ASSET_DUPLICATE", "素材身份不能重复")
    if any(asset.get("slot") not in plan["slots"] or plan["slots"][asset["slot"]]["kind"] != "image" for asset in needs):
        _reject("DECOMPOSITION_ASSET_SLOT", "图片资产必须引用实际图片槽位")
    for item in raw:
        try:
            definition = ObjectSemantics.model_validate(item)
        except ValidationError as exc:
            _reject("DECOMPOSITION_INVALID", "对象分工字段不合法：" + str(exc.errors()[0]["loc"]))
        oid = definition.objectId
        if oid not in objects or oid in definitions:
            _reject("DECOMPOSITION_OBJECT_ID", "对象分工身份未知或重复：" + oid)
        obj = objects[oid]
        content = plan["slots"][obj["slot"]]
        if obj.get("exit") or obj.get("transitional"):
            _reject("DECOMPOSITION_CONTROL_UNSUPPORTED", "当前动作词汇不能表达隐式退出，请显式扩展能力")
        if definition.initialState.visible:
            if definition.role == "instructional" or not definition.initiallyVisibleReason:
                _reject("DECOMPOSITION_INITIAL_VISIBILITY", "初始可见只用于明确说明理由的背景/装饰")
        elif definition.initiallyVisibleReason is not None:
            _reject("DECOMPOSITION_INITIAL_VISIBILITY", "初始隐藏对象不能附带初始可见理由")
        if obj["kind"] == "image":
            image_count += 1
            if definition.representation != "independent_asset" or definition.semanticType != "subject" or not definition.sourceMode:
                _reject("DECOMPOSITION_IMAGE_OWNERSHIP", "图片只能承担独立主体，不承载文字、数据或关系")
            matching = [asset for asset in needs if asset.get("slot") == obj["slot"]]
            ref = content.get("assetRef", {})
            if len(matching) != 1 or matching[0]["id"] != ref.get("id") or not ref.get("version"):
                _reject("DECOMPOSITION_ASSET_IDENTITY", "图片槽位必须对应唯一素材身份/版本")
            required = definition.requiredAnchors
            if len(set(required)) != len(required) or any(anchor.lower() in {"focus", "center"} for anchor in required):
                _reject("DECOMPOSITION_ANCHOR_GENERIC", "不能用通用中心 focus 代替具体语义定位")
            if required and content.get("anchorId") not in required:
                _reject("DECOMPOSITION_ANCHOR_REFERENCE", "图片必须引用声明的具体锚点")
            anchors[oid] = _anchor_status(ref, required, definition.sourceMode, resources)
        elif definition.representation != "code" or definition.sourceMode is not None or definition.requiredAnchors:
            _reject("DECOMPOSITION_CODE_OWNERSHIP", "文字、关系、数据和图标必须由代码承担")
        definitions[oid] = definition.model_dump(exclude_none=True)
    if set(definitions) != set(objects):
        _reject("DECOMPOSITION_COVERAGE", "对象分工必须完整覆盖实际对象")
    if image_count > asset_budget:
        _reject("BRIEF_BUDGET_EXCEEDED", f"独立主体 {image_count} 个超出预算 {asset_budget}；先拆页或改用代码")
    sequence = _sequence(plan, definitions)
    result = {"objectSemantics": [definitions[oid] for oid in objects], "visualSequence": sequence,
              "assetPolicy": {"budget": asset_budget, "subjects": image_count, "control": "whole_asset"},
              "anchorChecks": anchors}
    result["decomposition_sha256"] = _decomposition_hash(plan, result)
    return result


def _decomposition_hash(plan: dict, decomposition: dict) -> str:
    source = {key: plan[key] for key in ("slide_id", "slots", "objects", "assets")}
    source["beats"] = [FrozenSemanticBeat.model_validate(beat).model_dump(exclude_none=True) for beat in plan["beats"]]
    state = {key: decomposition[key] for key in ("visualSequence", "assetPolicy", "anchorChecks")}
    state["objectSemantics"] = [ObjectSemantics.model_validate(obj).model_dump(exclude_none=True)
                               for obj in decomposition["objectSemantics"]]
    return sha256_json({"plan": source, "decomposition": state})


def narration_design(plan: dict) -> dict:
    """Bound design input; hashes are reproducibility evidence, never approval."""
    if _decomposition_hash(plan, plan) != plan.get("decomposition_sha256"):
        _reject("DECOMPOSITION_CHANGED", "对象/讲稿/状态已变化，须重新校验再构建设计输入")
    return {"objects": [ObjectSemantics.model_validate(obj).model_dump(exclude_none=True) for obj in plan["objectSemantics"]],
            "sequence": plan["visualSequence"],
            "asset_policy": plan["assetPolicy"], "anchor_checks": plan["anchorChecks"],
            "source_sha256": plan["decomposition_sha256"]}


def _anchor_status(ref: dict, required: list[str], mode: str, resources: dict | None) -> dict:
    if mode == "generate":
        return {"status": "pending_asset", "required": required, "assetRef": ref}
    entries = [asset for asset in (resources or {}).get("assets", [])
               if asset["id"] == ref["id"] and asset["version"] == ref["version"]]
    if len(entries) != 1:
        _reject("DECOMPOSITION_RESOURCE_MISSING", "已有素材必须经实际资源加载器验证身份、版本和字节")
    asset = entries[0]
    registered = {anchor["id"]: anchor for anchor in asset.get("anchors", [])}
    if len(registered) != len(asset.get("anchors", [])) or set(required) - set(registered):
        _reject("DECOMPOSITION_ANCHOR_MISSING", "已有素材缺少唯一具体锚点")
    for aid in required:
        if any(type(registered[aid].get(axis)) not in (float, int)
               or not math.isfinite(registered[aid][axis]) or not 0 <= registered[aid][axis] < 1 for axis in ("x", "y")):
            _reject("DECOMPOSITION_ANCHOR_INVALID", "实际源图锚点坐标不合法")
    return {"status": "resource_verified" if required else "whole_asset_verified",
            "required": required, "assetRef": ref, "file_sha256": asset["file"]["sha256"],
            "intrinsic": asset["intrinsic"],
            "anchors": {aid: {axis: registered[aid][axis] for axis in ("x", "y")} for aid in required}}


def _sequence(plan: dict, definitions: dict) -> list[dict[str, Any]]:
    visible = {oid: definition["initialState"]["visible"] for oid, definition in definitions.items()}
    sequence = [{"stage": "start", "visible": dict(visible)}]
    _annotation_dependencies(plan, definitions, visible)
    driven = set()
    for beat in plan["beats"]:
        for target in beat["targets"]:
            if target["role"] != definitions[target["objectId"]]["role"]:
                _reject("DECOMPOSITION_ROLE_CONFLICT", "语块目标角色与对象分工不一致")
        before = dict(visible)
        for action in beat["actions"]:
            oid = action["objectId"]
            if action["type"] == "enter":
                if visible[oid]:
                    _reject("DECOMPOSITION_STATE_CONFLICT", "对象已可见，不能用再次进入代替强调")
                visible[oid] = True
            elif not visible[oid]:
                _reject("DECOMPOSITION_STATE_CONFLICT", "隐藏对象不能强调；须先有独立进入动作")
            driven.add(oid)
        _annotation_dependencies(plan, definitions, visible)
        sequence.append({"stage": "beat", "beatId": beat["id"], "spoken_text": beat["spoken_text"],
                         "visualIntent": beat["visualIntent"], "before": before, "after": dict(visible),
                         "actions": beat["actions"], "narration_only": beat["narration_only"],
                         **({"narration_only_reason": beat["narration_only_reason"]} if beat["narration_only"] else {})})
    for oid, definition in definitions.items():
        if definition["role"] == "instructional" and oid not in driven:
            _reject("DECOMPOSITION_UNDRIVEN", "讲解对象缺少语块驱动：" + oid)
        if definition["endState"]["visible"] != visible[oid]:
            _reject("DECOMPOSITION_END_STATE", "结束状态与语块动作不一致：" + oid)
    sequence.append({"stage": "end", "visible": dict(visible)})
    return sequence


def _annotation_dependencies(plan: dict, definitions: dict, visible: dict):
    by_slot = {obj["slot"]: obj["id"] for obj in plan["objects"]}
    for slot, content in plan["slots"].items():
        if content["kind"] != "annotation":
            continue
        target, label = content.get("targetId"), content.get("labelId")
        image = next((obj for obj in plan["objects"] if obj["id"] == target and obj["kind"] == "image"), None)
        label_object = next((obj for obj in plan["objects"] if obj["id"] == label and obj["kind"] == "text"), None)
        if (not image or not label_object or content.get("anchorId") not in definitions[target]["requiredAnchors"]
                or plan["slots"][image["slot"]].get("anchorId") != content.get("anchorId")):
            _reject("DECOMPOSITION_ANNOTATION_REFERENCE", "标注必须引用明确图片对象、标签和已声明具体锚点")
        if visible[by_slot[slot]] and (not visible[target] or not visible[label]):
            _reject("DECOMPOSITION_ANNOTATION_LIFETIME", "标注不能先于图片或标签出现")
