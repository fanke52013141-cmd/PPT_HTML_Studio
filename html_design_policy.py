"""Production authority and executable repair ownership, shared by visual agents."""
from typing import Literal

Requirement = Literal[
    "geometry", "typography", "registered_variant", "semantic_text", "semantic_relation",
    "asset_identity", "asset_rendering", "theme_conflict", "unsupported_presentation",
]


def production_policy(scene):
    return {
        "version": "0.1.0",
        "theme": scene.get("themeRef"),
        "palette": "grayscale" if (scene.get("themeRef") or {}).get("id") == "neutral-baseline" else "registered_theme",
        "text_owner": "code_including_labels_inside_illustrations",
        "relation_owner": "code",
        "reference_role": "composition_reference_below_authoritative_content_and_theme",
        "asset_scope": "nonsemantic_illustration_only_no_text_labels_or_semantic_relations",
    }


def editable_capabilities(node, variants):
    from html_scene_repair import PARTS, STYLE_KEYS
    if node["type"] == "annotation":
        return {}
    result = {"set_presentation": ["offsetX", "offsetY", "width", "height"]}
    if PARTS.get(node["type"]):
        result["set_text_style"] = {"parts": PARTS[node["type"]], "fields": sorted(STYLE_KEYS), "scope": "whole_part_only"}
    if variants:
        result["set_variant"] = [v["id"] for v in variants]
    return result


def resolve_issue(issue, node, capability):
    """Use explicit need and registered tools, never parse free prose for routing."""
    need = issue["requirement"]
    if need in {"semantic_text", "semantic_relation"}:
        return "planning", "semantic_content_remains_code_owned_even_inside_an_image"
    if need == "theme_conflict":
        return "design_review", "reference_conflicts_with_authoritative_theme_requires_review"
    if need in {"asset_identity", "asset_rendering"}:
        if node["type"] == "image":
            return "assets", "nonsemantic_image_repair"
        return "capabilities", "code_controlled_object_cannot_be_replaced_by_bitmap_asset"
    operations = capability.get("editable", {})
    if need == "geometry" and "set_presentation" in operations:
        return "reconstruction", "registered_geometry_operation"
    if need == "typography" and "set_text_style" in operations:
        return "reconstruction", "registered_whole_part_typography_operation"
    if need == "registered_variant" and issue.get("variant_id") in operations.get("set_variant", []):
        return "reconstruction", "explicit_applicable_registered_variant"
    return "capabilities", "required_presentation_not_executable_by_registered_static_tools"
