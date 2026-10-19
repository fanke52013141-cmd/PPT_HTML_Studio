"""Derive task-specific operations from registered production capabilities."""
import copy

from html_motion_binding import motion_identity
from html_scene_repair import KINDS, PARTS


def operation_schema(doc, context, scope, task_type):
    schema = doc["capabilities"]["schema"]
    definitions = schema["$defs"]

    def expand(value):
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            if "$ref" in value:
                return expand(definitions[value["$ref"].split("/")[-1]])
            return {key: expand(child) for key, child in value.items()}
        return value

    variants = []

    def add(node, kind, values, **fields):
        variants.append({"type": "object", "additionalProperties": False,
                         "required": ["targetId", "kind", "values", *fields],
                         "properties": {"targetId": {"const": node["id"]}, "kind": {"const": kind},
                                        "values": {"type": "object", "additionalProperties": False,
                                                   "minProperties": 1, "properties": expand(values)},
                                        **{key: {"const": value} for key, value in fields.items()}}})

    presentation = definitions["presentation"]["properties"]
    style = definitions["instanceTextStyle"]["properties"]
    for node in doc["scene"]["nodes"]:
        if node["id"] not in scope:
            continue
        capability = context["capabilities"][node["id"]]
        editable = capability["editable"]
        if "set_presentation" in editable:
            add(node, "set_presentation", {key: presentation[key] for key in KINDS["set_presentation"]})
        if "set_text_style" in editable:
            for part in PARTS.get(node["type"], []):
                if part in ("tag", "note", "heading") and not node.get(part):
                    continue
                add(node, "set_text_style", {key: style[key] for key in KINDS["set_text_style"]}, part=part)
        if editable.get("set_variant"):
            for variant in capability["variants"]:
                if variant["id"] not in editable["set_variant"]:
                    continue
                values = {"variant": {"const": variant["id"]}}
                if variant.get("allowsIcon") and capability["icons"]:
                    values["icon"] = {"enum": capability["icons"]}
                add(node, "set_variant", values)
                variants[-1]["properties"]["values"]["required"] = ["variant"]
        if task_type != "animation_repair":
            continue
        for action in doc["scene"]["motion"]:
            if action["targetId"] != node["id"]:
                continue
            motion_spec = next(item["properties"] for item in definitions["motion"]["oneOf"]
                               if item["properties"]["type"]["const"] == action["type"])
            values = {key: copy.deepcopy(motion_spec[key]) for key in KINDS["set_motion"] if key in motion_spec}
            identity = {"action": action["type"]}
            if action.get("actionId"):
                identity["actionId"] = action["actionId"]
            links = (doc["binding"] or {}).get("actions", {})
            if motion_identity(action) in links:
                values.pop("startMs", None)
            add(node, "set_motion", values, **identity)
            beat_ids = [beat["id"] for beat in doc["beats"]]
            if beat_ids:
                add(node, "set_binding", {"beatId": {"enum": beat_ids}, "edge": {"enum": ["start", "end"]},
                                          "offsetMs": {"type": "integer", "minimum": -120000, "maximum": 120000}},
                    **identity)
                if motion_identity(action) not in links:
                    variants[-1]["properties"]["values"]["required"] = KINDS["set_binding"]
    return {"oneOf": variants} if variants else {"not": {}}


RULES = {
    "authority": ["authoritative_content_and_manual_protection", "resolved_theme_and_layout", "design_reference", "examples"],
    "must_preserve": ["exact_text_numbers_relations", "object_action_beat_identity", "manual_protected_paths",
                      "source_image_bytes", "existing_narration_and_audio"],
    "forbidden": ["arbitrary_html_js_css", "whole_slide_bitmap_body", "new_objects_or_relations",
                  "provider_or_tts_requests", "approval_writes", "scope_expansion"],
    "coordinates": "layout canvas logical pixels; offsets relative to registered slots; time in milliseconds; anchors normalized",
    "style": "Resolved theme and per-node presentation are authoritative. Application chrome is not slide style.",
    "checks": ["registered_schema_and_capabilities", "strict_capacity", "sampled_geometry_and_temporal_review",
               "independent_semantic_review_when_required", "current_human_visual_decision"],
    "sampling_limit": "Finite sampled geometry is not proof of all-time collision safety or aesthetic approval.",
    "budget": {"image_requests": 0, "tts_requests": 0, "external_inference_budget": None, "unreported_cost": None},
    "save": "Explicit preview then save; source=ai. Export/import never approves or regenerates audio.",
}


def validate_operations(schema, operations):
    """Use the engine's locked AJV rather than a second validator dependency."""
    from html_scene_editing import _node
    return _node("""
const fs=require('fs'), Ajv=require('./html_engine/node_modules/ajv');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const validate=new Ajv({strict:false,allErrors:true}).compile(input.schema);
console.log(JSON.stringify(input.operations.map(operation=>Boolean(validate(operation)))));
""", {"schema": schema, "operations": operations})
