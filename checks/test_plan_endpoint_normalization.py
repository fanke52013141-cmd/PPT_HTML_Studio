"""Deterministic relation-endpoint normalization for model slot-name references."""
import copy
import json
from pathlib import Path

import pytest

from html_production_service import compile_plan
from html_storyboard_planning import (
    HtmlScenePlanError,
    _resolve_relation_endpoints,
    load_template_catalog,
    normalize_html_scene_plan,
)
from scripts.benchmark_plan_endpoint_normalization import (
    FIXTURES,
    arrow_endpoints,
    metrics,
    rewrite,
    run_case,
    transform,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(FIXTURES.read_text(encoding="utf-8"))
CATALOG = load_template_catalog(ROOT)


def compiled(plan, contract):
    normalized = normalize_html_scene_plan(plan, CATALOG, contract_slide=contract)
    scene, binding = compile_plan(normalized, contract, CATALOG)
    return normalized, scene, binding


def first_slot_variant(case):
    plan = transform(case["plan"])
    arrow, key, slot_name = next(arrow_endpoints(plan))
    return plan, arrow, key, slot_name


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["contract"]["slide_id"])
def test_slot_name_endpoint_is_normalized_to_the_same_scene(case):
    plan, arrow, key, slot_name = first_slot_variant(case)
    _, canonical_scene, canonical_binding = compiled(copy.deepcopy(plan), case["contract"])
    normalized, scene, binding = compiled(
        rewrite(plan, arrow, key, slot_name), case["contract"]
    )
    assert (scene, binding) == (canonical_scene, canonical_binding)
    receipts = normalized["registered"]["endpoint_resolutions"]
    assert receipts[0]["requested"] == slot_name
    assert receipts[0]["resolved"] == canonical_recipient(plan, arrow, key)
    assert receipts[0]["basis"].startswith("unique slot identity")


def canonical_recipient(plan, arrow, key):
    content = plan["slots"][arrow["slot"]][key]
    return content["objectId"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["contract"]["slide_id"])
def test_unknown_and_kind_mismatch_references_stay_rejected(case):
    plan, arrow, key, _ = first_slot_variant(case)
    for requested in ("missing-object", arrow["slot"]):
        with pytest.raises(HtmlScenePlanError) as caught:
            compiled(rewrite(plan, arrow, key, requested), case["contract"])
        assert caught.value.code == "PLAN_RELATION_ENDPOINT"
    asset_id = next(
        (asset["id"] for asset in plan.get("assets", []) if asset.get("id")), None
    )
    if asset_id:
        with pytest.raises(HtmlScenePlanError) as caught:
            compiled(rewrite(plan, arrow, key, asset_id), case["contract"])
        assert caught.value.code == "PLAN_RELATION_ENDPOINT"


def _synthetic_plan():
    return {
        "objects": [
            {"id": "text-a", "slot": "shared", "kind": "text"},
            {"id": "text-b", "slot": "shared", "kind": "text"},
            {"id": "photo", "slot": "photo-slot", "kind": "image"},
            {"id": "relation-1", "slot": "relation-1", "kind": "arrow"},
        ],
        "slots": {
            "photo-slot": {"kind": "image", "anchorId": "focus"},
            "relation-1": {
                "kind": "arrow",
                "from": {"objectId": "shared", "point": {"x": 0.5, "y": 0.5}},
                "to": {"objectId": "photo-slot", "anchorId": "focus"},
            },
        },
        "assets": [],
        "registered": {},
    }


def test_ambiguous_slot_asset_and_anchor_mismatch_are_never_rewritten():
    ambiguous = _synthetic_plan()
    receipts = _resolve_relation_endpoints(ambiguous)
    assert [r["endpoint"] for r in receipts] == ["to"]
    assert ambiguous["slots"]["relation-1"]["from"]["objectId"] == "shared"
    assert ambiguous["slots"]["relation-1"]["to"]["objectId"] == "photo"

    with_asset = _synthetic_plan()
    with_asset["assets"] = [{"id": "shared"}]
    receipts = _resolve_relation_endpoints(with_asset)
    assert [r["endpoint"] for r in receipts] == ["to"]

    unique = _synthetic_plan()
    unique["objects"] = [obj for obj in unique["objects"] if obj["id"] != "text-b"]
    receipts = _resolve_relation_endpoints(unique)
    assert {r["endpoint"] for r in receipts} == {"from", "to"}
    assert unique["slots"]["relation-1"]["from"]["objectId"] == "text-a"
    assert unique["slots"]["relation-1"]["to"]["objectId"] == "photo"
    assert {r["resolved"] for r in receipts} == {"text-a", "photo"}

    mismatch = _synthetic_plan()
    mismatch["objects"] = [obj for obj in mismatch["objects"] if obj["id"] != "text-b"]
    mismatch["slots"]["relation-1"]["to"]["anchorId"] = "wrong"
    receipts = _resolve_relation_endpoints(mismatch)
    assert [r["endpoint"] for r in receipts] == ["from"]
    assert mismatch["slots"]["relation-1"]["to"]["objectId"] == "photo-slot"


def test_benchmark_reports_full_recovery_without_weakening_rejection():
    result = metrics([run_case(case, CATALOG) for case in CASES])
    assert result["pages"] == 4
    assert result["slot_name_variants"] >= 8
    assert result["slot_name_acceptance_rate"] == 1.0
    assert result["scene_identity_matches"] == result["slot_name_variants"]
    assert result["endpoint_resolution_receipts"] == result["slot_name_variants"]
    assert result["unknown_rejected"] == result["unknown_variants"]
    assert result["kind_mismatch_rejected"] == result["kind_mismatch_variants"]
    assert result["provider_calls"] == result["author_writes"] == 0
