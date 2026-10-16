"""Registered multi-label content survives semantic planning and protected editing."""
import copy
from pathlib import Path

import pytest

from checks.test_html_semantic_plan import semantic_plan
from checks.test_html_storyboard_planning import CONTRACT_SLIDE
from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan, HtmlScenePlanError
from html_production_service import compile_plan
from html_scene_repair import candidate_from_document
from html_visual_review_service import _registered_capabilities, build_plan_generation_prompts

ROOT = Path(__file__).resolve().parents[1]


def labeled_plan():
    plan = semantic_plan()
    plan["templateRef"] = {"id": "explanation-labeled-v1", "version": "0.1.0"}
    for i in range(1, 7):
        slot = f"marker-{i}"
        plan["slots"][slot] = {"kind": "text", "role": "caption", "runs": [{"text": f"代码标签{i}", "emphasis": False}]}
        plan["objects"].append({"id": slot, "slot": slot, "kind": "text", "role": "instructional", "initialVisible": False})
        beat = plan["beats"][0]
        beat["targets"].append({"objectId": slot, "purpose": "可编辑名称"})
        beat["actions"].append({"actionId": f"{slot}-enter", "objectId": slot, "type": "enter"})
        beat["expectedState"].append({"objectId": slot, "visible": True, "expression": f"能看见代码标签{i}"})
    return plan


def test_labels_are_real_semantic_objects_with_source_and_binding():
    catalog = load_template_catalog(ROOT)
    plan = normalize_html_scene_plan(labeled_plan(), catalog, contract_slide=CONTRACT_SLIDE)
    scene, binding = compile_plan(plan, CONTRACT_SLIDE, catalog)
    assert scene["layoutRef"] == {"id": "science-explanation-v1", "version": "0.3.0"}
    for i in range(1, 7):
        target = f"marker-{i}"
        assert next(n for n in scene["nodes"] if n["id"] == target)["type"] == "text"
        assert any(a["targetId"] == target and a["type"] == "enter" for a in scene["motion"])
    assert binding and [b["spoken_text"] for b in plan["beats"]] == [b["spoken_text"] for b in CONTRACT_SLIDE["narration_beats"]]


@pytest.mark.parametrize("damage", ["seventh", "legacy_template", "unbound"])
def test_extra_unregistered_or_unbound_labels_cannot_pass(damage):
    plan = labeled_plan()
    if damage == "seventh":
        plan["slots"]["marker-7"] = plan["slots"]["marker-6"]
    elif damage == "legacy_template":
        plan["templateRef"]["id"] = "explanation-cards-v1"
    else:
        plan["beats"][0]["actions"] = [a for a in plan["beats"][0]["actions"] if a["objectId"] != "marker-1"]
    with pytest.raises(HtmlScenePlanError):
        normalize_html_scene_plan(plan, load_template_catalog(ROOT), contract_slide=CONTRACT_SLIDE)


def test_registered_variants_use_existing_protected_editor_without_content_changes(tmp_path):
    catalog = load_template_catalog(ROOT)
    plan = normalize_html_scene_plan(labeled_plan(), catalog, contract_slide=CONTRACT_SLIDE)
    scene, binding = compile_plan(plan, CONTRACT_SLIDE, catalog)
    before = copy.deepcopy(scene)
    ops = [{"targetId": "intro", "kind": "set_variant", "values": {"variant": "text-emphasis-bold"}},
           {"targetId": "figure", "kind": "set_variant", "values": {"variant": "figure-caption-top"}}]
    value = candidate_from_document(tmp_path, scene["id"], {"expected_revision": 0, "source": "ai", "operations": ops},
                                    {"scene": scene, "binding": binding, "manual": None, "resources": {}, "beats": CONTRACT_SLIDE["narration_beats"]})
    assert value["scene"]["version"] == "0.7.0" and scene == before
    assert value["scene"]["motion"] == scene["motion"]
    for old, new in zip(scene["nodes"], value["scene"]["nodes"]):
        assert old == {k: v for k, v in new.items() if k != "presentation"}


def test_normal_planning_prompt_has_exact_registered_label_budget():
    capabilities = _registered_capabilities(ROOT)
    prompts = build_plan_generation_prompts(CONTRACT_SLIDE, capabilities, plan_version="0.2.0")
    assert "html-semantic-plan/0.3.0" in prompts["system_prompt"]
    template = capabilities["catalog"]["templates"]["explanation-labeled-v1"]
    assert [s for s in template["slots"] if s.startswith("marker-")] == [f"marker-{i}" for i in range(1, 7)]
    assert "marker-6" in prompts["system_prompt"] and "图片需求" in prompts["system_prompt"]


def test_live_planning_replay_rejects_existing_output_before_configuration(tmp_path):
    from scripts.evaluate_html_labeled_planning import main
    with pytest.raises(ValueError, match="OUTPUT_MUST_BE_NEW"):
        main(["--source-run", "absent", "--design-folder", "absent", "--out", str(tmp_path), "--live"])
