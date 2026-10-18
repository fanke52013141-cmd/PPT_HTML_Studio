"""Production authority and executable repair ownership, shared by visual agents."""
from typing import Literal

Requirement = Literal[
    "geometry", "typography", "registered_variant", "semantic_text", "semantic_relation",
    "asset_identity", "asset_rendering", "theme_conflict", "unsupported_presentation",
]

ReferenceDetail = Literal['decorative_icon', 'surface_chrome']


def allowed_reference_details(node):
    if node['type'] == 'text' and ''.join(r.get('text','') for r in node.get('runs',[])).strip():
        return ['decorative_icon', 'surface_chrome']
    if node['type'] == 'header' and node.get('title'):
        return ['decorative_icon', 'surface_chrome']
    if node['type'] == 'summary' and all(node.get(k) for k in ('from','to','term','takeaway')):
        return ['decorative_icon', 'surface_chrome']
    return []


def reference_observation(issue, node):
    """Only explicit reference-only decoration can be nonblocking; minor alone never suffices."""
    return (issue.get('reference_detail') in allowed_reference_details(node)
            and issue.get('requirement') == 'unsupported_presentation'
            and issue.get('severity') != 'major')


def presentation_facts(node, variant=None):
    """Renderer-owned facts; reference names never imply unimplemented features."""
    variant = variant if variant is not None else node.get("presentation", {}).get("variant", "plain")
    stacked = node['type'] == 'text' and variant == 'text-card-stacked'
    overlay = node['type'] == 'summary' and variant == 'summary-arrow-overlay'
    facts = {"variant": variant, "label_value_stacked": node["type"] == "card" or stacked,
             "term_overlay_on_arrow": overlay, "takeaway_below_flow": overlay}
    if node["type"] == "text":
        facts["text_layout"] = "stacked_label_body" if stacked else "inline_runs"
        facts["label_split"] = "block_after_first_colon" if stacked else "inline_emphasized_prefix" if variant == "text-card-label" else "none"
    if node["type"] == "summary":
        facts.update(term_position="on_connector" if overlay else "below_connector" if variant == "summary-panel" else "registered_layout",
                     takeaway_position="below_flow" if overlay else "side_column")
        facts["term_prefix"] = "" if variant in {
            "summary-arrow-overlay", "summary-panel", "summary-relationship-panel",
            "summary-relationship-compact", "summary-relationship-columns", "summary-strip-divided",
        } else "这个过程叫"
        facts["section_dividers"] = 2 if variant in {
            "summary-relationship-panel", "summary-relationship-compact", "summary-relationship-columns", "summary-strip-divided",
        } else 0
    if node["type"] == "card":
        facts.update(container_frame=variant == "card-outline", icon_container="circle", surface="background" if variant == "card-outline" else "theme_default")
    if node["type"] == "arrow":
        facts.update(explicit_endpoints=bool(node.get("from")), head=node.get("head",True), line_style=node.get("lineStyle","solid"))
    if node["type"] == "chart":
        facts.update(code_owned=True, plateau=node.get("plateau"), data_editable_by_local_repair=False)
    if node["type"] == "figure":
        facts.update(frame_stroke="dashed" if variant == "figure-frame-dashed" else "solid", container_frame=variant in {"figure-frame-top","figure-frame-dashed"},
                     tag_treatment="inset_top_caption" if variant in {"figure-frame-top","figure-frame-dashed"} else "outlined_pill" if variant == "figure-caption-top" else "floating_tag")
    if node["type"] == "annotation":
        facts.update(anchor_stroke="dashed" if variant in {"annotation-dashed", "annotation-ring-dashed", "annotation-dashed-no-arrow"} else "solid",
                     leader_stroke="dashed" if variant in {"annotation-dashed", "annotation-line-dashed", "annotation-dashed-no-arrow"} else "solid",
                     leader_arrow=variant == "annotation-dashed",
                     leader_geometry="anchor_to_label_edge", static_style_editable="variant_only")
    return facts


def production_policy(scene):
    return {
        "version": "0.2.0",
        "theme": scene.get("themeRef"),
        "palette": "grayscale" if (scene.get("themeRef") or {}).get("id") == "neutral-baseline" else "registered_theme",
        "text_owner": "code_including_labels_inside_illustrations",
        "relation_owner": "code",
        "reference_role": "composition_reference_below_authoritative_content_and_theme",
        "asset_scope": "nonsemantic_illustration_only_no_text_labels_or_semantic_relations",
        "reference_adaptation": {
            "allowed_details": ['decorative_icon','surface_chrome'],
            "missing_decorative_icon": 'omit_rather_than_invent_or_use_unrelated_icon',
            "required": ['authoritative_text','semantic_relations','explicit_structure','readability','asset_identity','manual_protection'],
            "minor_alone_is_not_exemption": True,
        },
    }


def editable_capabilities(node, variants):
    from html_scene_repair import PARTS, STYLE_KEYS
    if node["type"] == "arrow" and node.get("from"):
        return {}  # Geometry is derived from semantic endpoints; replan to change them.
    if node["type"] == "annotation":
        return {"set_variant": [v["id"] for v in variants]} if variants else {}
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
        if issue["variant_id"] == node.get("presentation", {}).get("variant", "plain"):
            return "capabilities", "requested_variant_already_active_requires_fact_review"
        return "reconstruction", "explicit_applicable_registered_variant"
    return "capabilities", "required_presentation_not_executable_by_registered_static_tools"
