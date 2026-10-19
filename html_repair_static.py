"""Pure static repair mutation shared by production and the portable checker."""
PARTS = {
    "text": ["text"], "label": ["text"], "badge": ["text"], "header": ["title"],
    "card": ["title", "body"], "figure": ["tag", "note"],
    "summary": ["heading", "from", "to", "term", "takeaway"],
}


class StaticRepairError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def apply_static(scene, node, operation):
    kind, values = operation["kind"], operation["values"]
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
