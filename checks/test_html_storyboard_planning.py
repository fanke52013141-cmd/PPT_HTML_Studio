"""C01: semantic storyboard adaptation for the HTML backend (AC07).

Covers registered-capability gating (template/version/slot-kind/icon),
beat→node/action mapping completeness, transitional-object retention,
asset render ownership, and the AC07 evidence block. The real built
engine catalog is used as the registration source.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from html_storyboard_planning import (
    HtmlScenePlanError,
    beat_action_map,
    dedupe_plan_beats,
    load_template_catalog,
    plan_evidence,
    transitional_objects,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def catalog() -> dict:
    return load_template_catalog(REPO_ROOT)


CONTRACT_SLIDE = {
    "slide_id": "slide_001",
    "narration_beats": [
        {"id": "slide_001_beat_001", "spoken_text": "看见的是水滴，关键在空气中的水蒸气。"},
        {"id": "slide_001_beat_002", "spoken_text": "空气中有水蒸气，通常看不见。"},
        {"id": "slide_001_beat_003", "spoken_text": "水蒸气遇到较冷的杯壁。"},
        {"id": "slide_001_beat_004", "spoken_text": "水蒸气冷却凝结成小水滴。"},
        {"id": "slide_001_beat_005", "spoken_text": "所以杯外的水滴来自空气中的水蒸气。"},
    ],
}


def valid_plan() -> dict:
    return {
        "slide_id": "slide_001",
        "templateRef": {"id": "explanation-cards-v1", "version": "0.1.0"},
        "slots": {
            "header": {"kind": "header", "number": "01", "title": "冷杯外的水滴，从哪里来？"},
            "headline": {"kind": "text", "runs": [{"text": "看见的是水滴，关键在空气中的水蒸气。", "emphasis": False}]},
            "intro": {"kind": "text", "runs": [{"text": "从空气到杯壁，观察水的状态如何发生变化。", "emphasis": False}]},
            "card-1": {"kind": "card", "tone": "pink", "icon": "air", "title": "空气中有水蒸气", "body": "通常看不见，却一直在我们身边。"},
            "card-2": {"kind": "card", "tone": "green", "icon": "thermometer", "title": "遇到较冷的杯壁", "body": "水蒸气冷却，凝结成小水滴。"},
            "card-3": {"kind": "card", "tone": "blue", "icon": "droplet", "title": "杯外水滴来自空气", "body": "并不是杯里的水漏了出来。"},
            "figure": {"kind": "figure", "tag": {"icon": "eye", "text": "观察冷杯表面"}, "note": {"icon": "droplet", "text": "水滴来自空气中的水蒸气"}},
            "subject": {"kind": "image", "assetRef": {"id": "condensation", "version": "0.1.0"}, "anchorId": "focus"},
            "anchor-label": {"kind": "text", "runs": [{"text": "杯壁上的小水滴", "emphasis": False}]},
            "summary": {"kind": "summary", "from": {"text": "气态", "tone": "blue"}, "to": {"text": "液态", "tone": "green"}, "term": "凝结", "takeaway": "不是杯里的水漏出来"},
            "annotation": {"kind": "annotation", "targetId": "subject", "anchorId": "focus", "radius": 21, "labelId": "anchor-label"},
        },
        "objects": [
            {"id": "header", "slot": "header", "kind": "header"},
            {"id": "headline", "slot": "headline", "kind": "text"},
            {"id": "intro", "slot": "intro", "kind": "text"},
            {"id": "card-1", "slot": "card-1", "kind": "card", "icon": "air"},
            {"id": "card-2", "slot": "card-2", "kind": "card", "icon": "thermometer"},
            {"id": "card-3", "slot": "card-3", "kind": "card", "icon": "droplet"},
            {"id": "figure", "slot": "figure", "kind": "figure"},
            {"id": "subject", "slot": "subject", "kind": "image"},
            {"id": "summary", "slot": "summary", "kind": "summary"},
            {"id": "anchor-label", "slot": "anchor-label", "kind": "text"},
            {"id": "annotation", "slot": "annotation", "kind": "annotation"},
        ],
        "beats": [
            {"id": "slide_001_beat_001", "target": {"objectId": "headline", "action": "emphasize"}},
            {"id": "slide_001_beat_002", "target": {"objectId": "card-1", "action": "enter"}},
            {"id": "slide_001_beat_003", "target": {"objectId": "card-2", "action": "enter"}},
            {"id": "slide_001_beat_004", "target": {"objectId": "annotation", "action": "enter"}},
            {"id": "slide_001_beat_005", "target": {"objectId": "summary", "action": "enter"}},
        ],
        "assets": [
            {"id": "cold-cup", "role": "主视觉：冷杯表面凝结", "render_owner": "image_asset", "need": "同系列科学插画，表达杯壁水滴", "slot": "subject"},
            {"id": "cards-copy", "role": "知识卡文字与图标", "render_owner": "code"},
        ],
    }


def test_catalog_loads_from_real_built_bundle(catalog) -> None:
    assert set(catalog["templates"]) >= {
        "explanation-cards-v1",
        "data-relation-v1",
        "process-stage-v1",
    }
    assert len(catalog["sha256"]) == 64
    assert "droplet" in catalog["icons"]
    # Registration source is the single gate: nothing invented here.
    assert "rocket" not in catalog["icons"]


def test_valid_plan_normalizes_with_full_beat_map(catalog) -> None:
    plan = __import__("html_storyboard_planning").normalize_html_scene_plan(
        valid_plan(), catalog, contract_slide=CONTRACT_SLIDE
    )
    assert plan["structure"] == "explanation-cards"
    assert plan["layoutRef"]["id"] == "science-explanation-v1"
    mapping = beat_action_map(plan)
    assert set(mapping) == {b["id"] for b in CONTRACT_SLIDE["narration_beats"]}
    assert mapping["slide_001_beat_002"] == {"objectId": "card-1", "action": "enter"}
    evidence = plan_evidence(plan)
    assert evidence["beat_map"] == mapping
    assert evidence["asset_table"][0]["render_owner"] == "image_asset"
    assert evidence["catalog_sha256"] == catalog["sha256"]


def test_transitional_object_stays_in_the_table(catalog) -> None:
    plan = valid_plan()
    # A vapor fragment appears mid-explanation and leaves before the end:
    # it must remain an explicit object even though the final frame is
    # identical without it (AC07 / OSS-04).
    plan["objects"].append(
        {"id": "vapor-fragment", "slot": "intro", "kind": "text",
         "exit": True, "transitional": True}
    )
    normalized = __import__("html_storyboard_planning").normalize_html_scene_plan(
        plan, catalog
    )
    assert "vapor-fragment" in [obj["id"] for obj in normalized["objects"]]
    assert transitional_objects(normalized) == [
        {"id": "vapor-fragment", "slot": "intro", "kind": "text",
         "exit": True, "transitional": True}
    ]


def test_unregistered_template_and_version_rejected(catalog) -> None:
    plan = valid_plan()
    plan["templateRef"] = {"id": "three-column-juice", "version": "0.1.0"}
    with pytest.raises(HtmlScenePlanError) as unregistered:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert unregistered.value.code == "TEMPLATE_UNREGISTERED"

    plan = valid_plan()
    plan["templateRef"] = {"id": "explanation-cards-v1", "version": "9.0.0"}
    with pytest.raises(HtmlScenePlanError) as version:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert version.value.code == "TEMPLATE_VERSION_MISMATCH"


def test_slot_rules_are_enforced(catalog) -> None:
    plan = valid_plan()
    plan["slots"]["extra"] = {"kind": "text", "runs": []}
    with pytest.raises(HtmlScenePlanError) as undeclared:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert undeclared.value.code == "PLAN_SLOT_UNDECLARED"

    plan = valid_plan()
    plan["slots"]["card-1"] = {"kind": "text", "runs": []}
    with pytest.raises(HtmlScenePlanError) as kind:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert kind.value.code == "PLAN_SLOT_KIND"

    plan = valid_plan()
    del plan["slots"]["summary"]
    with pytest.raises(HtmlScenePlanError) as required:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert required.value.code == "PLAN_SLOT_REQUIRED"


def test_unknown_icon_rejected(catalog) -> None:
    plan = valid_plan()
    plan["objects"][3]["icon"] = "rocket"
    with pytest.raises(HtmlScenePlanError) as icon:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert icon.value.code == "ICON_UNREGISTERED"


def test_beat_coverage_gaps_are_rejected(catalog) -> None:
    plan = valid_plan()
    plan["beats"] = plan["beats"][:4]
    with pytest.raises(HtmlScenePlanError) as missing:
        __import__("html_storyboard_planning").normalize_html_scene_plan(
            plan, catalog, contract_slide=CONTRACT_SLIDE
        )
    assert missing.value.code == "PLAN_BEAT_MISSING"

    plan = valid_plan()
    plan["beats"].append({"id": "slide_001_beat_999", "narration_only": True})
    with pytest.raises(HtmlScenePlanError) as unknown:
        __import__("html_storyboard_planning").normalize_html_scene_plan(
            plan, catalog, contract_slide=CONTRACT_SLIDE
        )
    assert unknown.value.code == "PLAN_BEAT_UNKNOWN"

    plan = valid_plan()
    plan["beats"][1]["target"] = {"objectId": "not-declared", "action": "enter"}
    with pytest.raises(HtmlScenePlanError) as target:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert target.value.code == "PLAN_BEAT_TARGET_UNKNOWN"

    plan = valid_plan()
    plan["beats"][1]["target"] = {"objectId": "card-1", "action": "explode"}
    with pytest.raises(HtmlScenePlanError) as action:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert action.value.code == "PLAN_BEAT_ACTION_INVALID"

    plan = valid_plan()
    plan["beats"][1] = dict(plan["beats"][1])
    plan["beats"][1]["narration_only"] = False
    del plan["beats"][1]["target"]
    with pytest.raises(HtmlScenePlanError) as target_missing:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert target_missing.value.code == "PLAN_BEAT_TARGET_MISSING"


def test_slide_mismatch_and_asset_owner_rejected(catalog) -> None:
    plan = valid_plan()
    plan["slide_id"] = "slide_002"
    with pytest.raises(HtmlScenePlanError) as mismatch:
        __import__("html_storyboard_planning").normalize_html_scene_plan(
            plan, catalog, contract_slide=CONTRACT_SLIDE
        )
    assert mismatch.value.code == "PLAN_SLIDE_MISMATCH"

    plan = valid_plan()
    plan["assets"][0]["render_owner"] = "model_css"
    with pytest.raises(HtmlScenePlanError) as owner:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert owner.value.code == "PLAN_ASSET_OWNER_INVALID"

    plan = valid_plan()
    del plan["assets"][0]["need"]
    with pytest.raises(HtmlScenePlanError) as need:
        __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert need.value.code == "PLAN_FIELD_TOO_LONG" or need.value.code == "PLAN_FIELD_MISSING"


def test_plan_input_is_not_mutated(catalog) -> None:
    plan = valid_plan()
    frozen = copy.deepcopy(plan)
    __import__("html_storyboard_planning").normalize_html_scene_plan(plan, catalog)
    assert plan == frozen


def test_spoken_sentence_dedupe_is_reused() -> None:
    beats = [
        {"text": "水蒸气冷却，凝结成小水滴。"},
        {"text": "水蒸气冷却，凝结成小水滴。"},  # 同句去重
        {"text": "并不是杯里的水漏了出来。"},
    ]
    kept = dedupe_plan_beats(beats)
    assert len(kept) == 2
