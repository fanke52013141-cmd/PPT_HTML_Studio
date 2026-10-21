"""Pure static repair mutation shared by production and the portable checker."""
import math

PARTS = {
    "text": ["text"], "label": ["text"], "badge": ["text"], "header": ["title"],
    "card": ["title", "body"], "figure": ["tag", "note"],
    "summary": ["heading", "from", "to", "term", "takeaway"],
}

ENDPOINT_KIND = "set_endpoint_point"


class StaticRepairError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _point(value):
    if not isinstance(value, dict) or set(value) != {"x", "y"}:
        raise StaticRepairError("REPAIR_FIELDS", "端点必须是 {x,y}")
    for coordinate in value.values():
        if type(coordinate) not in (int, float) or not math.isfinite(coordinate) or not 0 <= coordinate <= 1:
            raise StaticRepairError("REPAIR_FIELDS", "端点坐标必须是 0–1 的有限数")
    return {"x": float(value["x"]), "y": float(value["y"])}


def _apply_endpoint_point(node, values):
    """Move declared relation attachment points only; object identity is fixed."""
    if node["type"] != "arrow" or not node.get("from") or not node.get("to"):
        raise StaticRepairError("ENDPOINT_POINT_REQUIRED", "只有带显式端点的关系可调整附着点")
    if not values or set(values) - {"from", "to"}:
        raise StaticRepairError("REPAIR_FIELDS", "set_endpoint_point 只接受 from/to")
    resolved = {}
    for side in ("from", "to"):
        if side not in values:
            continue
        endpoint = node[side]
        if endpoint.get("anchorId"):
            raise StaticRepairError("ENDPOINT_ANCHOR_FIXED", "图片锚点端点不可改为自由附着点")
        if set(endpoint) != {"objectId", "point"}:
            raise StaticRepairError("REPAIR_FIELDS", "端点必须已声明 objectId 与 point")
        resolved[side] = _point(values[side])
    if not resolved:
        raise StaticRepairError("REPAIR_FIELDS", "set_endpoint_point 至少修改一端")
    merged_from = resolved.get("from", node["from"]["point"])
    merged_to = resolved.get("to", node["to"]["point"])
    if merged_from == merged_to:
        raise StaticRepairError("ENDPOINT_ZERO_LENGTH", "端点不能重合为零长度关系")
    for side, point in resolved.items():
        node[side]["point"] = point
    return "endpoint_point"


def apply_static(scene, node, operation):
    kind, values = operation["kind"], operation["values"]
    if kind == ENDPOINT_KIND:
        _apply_endpoint_point(node, values)
        return
    if kind not in ("set_presentation", "set_text_style", "set_variant"):
        raise StaticRepairError("STATIC_OPERATION_REQUIRED", "便携预检仅执行注册静态操作")
    if node["type"] == "arrow" and node.get("from"):
        raise StaticRepairError("RELATION_GEOMETRY_OWNED", "Change endpoint objects or replan")
    if node["type"] == "annotation" and kind != "set_variant":
        raise StaticRepairError("REPAIR_FIELDS", "圈注空间不能单独覆盖")
    if operation.get("action") is not None or operation.get("actionId") is not None:
        raise StaticRepairError("REPAIR_FIELDS", "基础样式不接受action")
    presentation = node.setdefault("presentation", {})
    part = operation.get("part")
    if kind == "set_variant":
        if scene["version"] not in ("0.6.0", "0.7.0") or part is not None or "variant" not in values:
            raise StaticRepairError("VARIANT_VERSION", "注册呈现变体需语义场景，且指定variant")
        presentation["variant"] = values["variant"]
        presentation.pop("icon", None)
        if "icon" in values:
            presentation["icon"] = values["icon"]
        scene["version"] = "0.7.0"
    elif kind == "set_text_style":
        if part not in PARTS.get(node["type"], []) or (part in ("tag", "note", "heading") and not node.get(part)):
            raise StaticRepairError("UNSUPPORTED_TEXT_PART", "不存在该公开文字部位")
        presentation.setdefault("typography", {}).setdefault(part, {}).update(values)
    else:
        if part is not None:
            raise StaticRepairError("REPAIR_FIELDS", "布局操作不接受part")
        presentation.update(values)
    if scene["version"] not in ("0.6.0", "0.7.0"):
        scene["version"] = "0.5.0"
