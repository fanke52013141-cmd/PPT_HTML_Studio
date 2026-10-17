"""Real incident categories must respect authority and executable ownership."""
import pytest

from html_design_policy import production_policy, resolve_issue, editable_capabilities
from html_design_agent import validate_fidelity, validate_understanding


@pytest.mark.parametrize("need,kind,expected", [
    ("semantic_text", "image", "planning"), ("semantic_relation", "image", "planning"),
    ("asset_identity", "image", "assets"), ("asset_rendering", "card", "capabilities"),
    ("unsupported_presentation", "summary", "capabilities"), ("theme_conflict", "image", "design_review"),
    ("geometry", "annotation", "capabilities"), ("geometry", "card", "reconstruction"),
    ("typography", "image", "capabilities"), ("typography", "card", "reconstruction"),
])
def test_requirement_overrides_misleading_asset_or_layout_category(need, kind, expected):
    node = {"id": "target", "type": kind}
    capability = {"editable": editable_capabilities(node, [])}
    route, reason = resolve_issue({"requirement": need, "category": "asset"}, node, capability)
    assert route == expected and reason


def test_variant_requires_an_explicit_applicable_id():
    node = {"id": "n", "type": "text"}
    capability = {"editable": editable_capabilities(node, [{"id": "plain"}])}
    issue = {"requirement": "registered_variant"}
    assert resolve_issue(issue, node, capability)[0] == "capabilities"
    assert resolve_issue({**issue, "variant_id": "invented"}, node, capability)[0] == "capabilities"
    assert resolve_issue({**issue, "variant_id": "plain"}, node, capability) == (
        "capabilities", "requested_variant_already_active_requires_fact_review")
    node['presentation'] = {'variant': 'text-card-label'}
    assert resolve_issue({**issue, "variant_id": "plain"}, node, capability)[0] == "reconstruction"


def test_reference_authority_and_missing_discriminant_fail_closed():
    policy = production_policy({"themeRef": {"id": "neutral-baseline", "version": "0.2.0"}})
    assert policy["palette"] == "grayscale" and policy["text_owner"].startswith("code")
    assert production_policy({"themeRef": {"id": "other"}})["palette"] == "registered_theme"
    with pytest.raises(ValueError):
        validate_fidelity({"status": "changes_requested", "issues": [{"targetId": "s", "category": "asset",
            "severity": "major", "evidence": "missing labels", "suggestion": "paint text"}]}, {"nodes": [{"id": "s"}]})
    with pytest.raises(ValueError):
        validate_understanding({"status": "unsupported", "objects": [], "issues": [
            {"targetId": "s", "route": "assets", "evidence": "missing labels"}]}, {"objects": [{"id": "s"}]})
