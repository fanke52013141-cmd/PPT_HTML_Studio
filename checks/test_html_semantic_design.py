"""A02 allocation, minimal context and Agent contract regressions."""
import copy
import json
from pathlib import Path

import pytest

from checks.test_html_semantic_plan import semantic_plan, normalize, CONTRACT_SLIDE
from html_semantic_design import build_semantic_design
from html_semantic_plan import SemanticPlanError, preserve_action_identity
from html_design_brief import build_design_brief, load_effect_registry, required_keyframes
from html_reference_package import design_content, design_prompt, assemble_reference
from html_visual_review_service import build_plan_generation_prompts, _registered_capabilities, generate_scene_plan, HtmlReviewError
from html_planning_context import planning_context

ROOT = Path(__file__).resolve().parents[1]


def brief_for(plan):
    return build_design_brief(plan, theme="neutral-baseline", asset_budget=1, effect_registry=load_effect_registry(ROOT))


def test_allocation_and_ordered_state_reach_actual_reference_package(tmp_path):
    from runtime_support import run_subprocess_killable
    plan = normalize(semantic_plan())
    brief = brief_for(plan)
    assert brief["version"] == "0.2.0" and brief["effects"] == []
    design = brief["semantic_design"]
    assert design["semantic_review"] == "pending_review"
    assert "card-1" not in design["initialVisibleObjectIds"]
    assert "card-1" in design["steps"][0]["visibleObjectIds"]
    assert next(o for o in design["allocations"] if o["id"] == "subject")["control"] == "whole_asset_only"
    assert next(o for o in design["allocations"] if o["id"] == "card-1")["render_owner"] == "code"
    package = assemble_reference(plan, brief, repo_root=ROOT, directory=tmp_path / "package", runner=run_subprocess_killable)
    prompt = design_prompt(package)
    assert "html-design-reference/0.4.0" in prompt and "semanticDesign" in prompt
    assert "instructional" in prompt and "whole_asset_only" in prompt
    assert "plan_sha256" not in prompt and "spoken_text_sha256" not in prompt
    assert "actionId" not in json.dumps(package["content"]["semanticDesign"])
    assert package["references"] and all(Path(p).is_file() for p in package["references"])
    assert [f["stage"] for f in required_keyframes(plan)] == ["start"] + ["relation_change"] * 5 + ["end"]


@pytest.mark.parametrize("change,code", [
    (lambda p: p["assets"][0].update(id="wrong"), "SEMANTIC_ASSET_IDENTITY"),
    (lambda p: p["assets"].clear(), "SEMANTIC_ASSET_OWNERSHIP"),
    (lambda p: p["assets"].append(copy.deepcopy(p["assets"][0])), "SEMANTIC_ASSET_DUPLICATE"),
    (lambda p: p["objects"][0].update(transitional=True), "SEMANTIC_STATE_UNSUPPORTED"),
    (lambda p: p["objects"][0].update(initialVisible=False, initialVisibleReason=None), "SEMANTIC_OBJECT_NEVER_VISIBLE"),
    (lambda p: p["objects"][0].update(kind="text"), "SEMANTIC_SLOT_KIND"),
])
def test_unsupported_allocation_is_blocked(change, code):
    plan = normalize(semantic_plan())
    change(plan)
    with pytest.raises(SemanticPlanError) as caught:
        build_semantic_design(plan)
    assert caught.value.code == code


@pytest.mark.parametrize("field,value,code", [
    ("targetId", "focus", "SEMANTIC_ANNOTATION_TARGET"),
    ("anchorId", "wrong-focus", "SEMANTIC_ANNOTATION_ANCHOR"),
    ("labelId", "missing-label", "SEMANTIC_ANNOTATION_LABEL"),
])
def test_annotation_references_fail_before_image_generation(field, value, code):
    plan = normalize(semantic_plan())
    plan["slots"]["annotation"][field] = value
    with pytest.raises(SemanticPlanError) as caught:
        build_semantic_design(plan)
    assert caught.value.code == code


@pytest.mark.parametrize("target", ["subject", "condensation"])
def test_annotation_accepts_explicit_image_identity(target):
    plan = normalize(semantic_plan())
    plan["slots"]["annotation"]["targetId"] = target
    assert build_semantic_design(plan)["semantic_review"] == "pending_review"


def test_planning_repairs_bad_annotation_before_design_image(tmp_path):
    bad = semantic_plan()
    bad["slots"]["annotation"]["targetId"] = "focus"
    good = semantic_plan()
    responses = [bad, good]
    plan = generate_scene_plan(
        CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT,
        json_generator=lambda **kw: responses.pop(0), plan_version="0.2.0",
    )
    assert plan["slots"]["annotation"]["targetId"] == "subject"
    record = json.loads((tmp_path / "planning/html_visual/records/plan-slide_001.json").read_text(encoding="utf-8"))
    assert [item["accepted"] for item in record["attempts"]] == [False, True]
    assert record["attempts"][0]["diagnostic_code"] == "SEMANTIC_ANNOTATION_TARGET"


def test_annotation_identity_rules_reach_both_provider_rounds(tmp_path):
    bad, good = semantic_plan(), semantic_plan()
    bad["slots"]["annotation"]["targetId"] = "anchor-label"
    requests = []

    def provider(**request):
        requests.append(request)
        return bad if len(requests) == 1 else good

    generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT,
                        json_generator=provider, plan_version="0.2.0")
    assert len(requests) == 2
    for request in requests:
        prompt = request["system_prompt"]
        assert "html-semantic-plan/0.3.3" in prompt
        assert "targetId 引用图片对象ID、图片槽位ID或该图片的素材ID" in prompt
        assert "annotation.anchorId 必须等于所指图片槽位的 anchorId" in prompt
        assert "labelId 单独引用 kind=text" in prompt
        assert request["reasoning_effort_override"] == "low"
    retry = json.loads(requests[1]["user_prompt"])
    assert retry["invalid_plan"] == bad
    assert retry["diagnostic"]["code"] == "SEMANTIC_ANNOTATION_TARGET"


def test_image_internal_state_change_is_not_assumed_possible():
    plan = normalize(semantic_plan())
    for i, expression in enumerate(("完整未分词文本", "分离后的Token块")):
        plan["beats"][i]["targets"].append({"objectId": "subject", "purpose": "试图改变图片内部内容"})
        plan["beats"][i]["actions"].append({"actionId": f"image-{i}", "objectId": "subject", "type": "emphasize"})
        plan["beats"][i]["expectedState"].append({"objectId": "subject", "visible": True, "expression": expression})
    with pytest.raises(SemanticPlanError) as caught:
        build_semantic_design(plan)
    assert caught.value.code == "SEMANTIC_IMAGE_STATE_CHANGE"


def test_emphasis_cannot_precede_enter_even_if_enter_exists_later():
    plan = normalize(semantic_plan())
    plan["beats"][0]["actions"][0]["type"] = "emphasize"
    plan["beats"][1]["actions"][0]["type"] = "enter"
    with pytest.raises(SemanticPlanError) as caught:
        build_semantic_design(plan)
    assert caught.value.code == "SEMANTIC_ACTION_BEFORE_ENTER"


def test_changed_plan_cannot_reuse_semantic_brief():
    plan = normalize(semantic_plan())
    brief = brief_for(plan)
    plan["beats"][0]["visualIntent"] = "新的设计意图"
    with pytest.raises(HtmlReviewError, match="不一致"):
        design_content(plan, brief)


def test_context_removes_metadata_but_preserves_distinct_copy_and_asset_identity():
    contract = copy.deepcopy(CONTRACT_SLIDE)
    contract["narration_beats"][0].update(audio_path="private.wav", debug="unused")
    original = "".join(b["spoken_text"] for b in contract["narration_beats"])
    contract["visual_groups"] = [
        {"id": "g1", "content": original, "description": "必须保留的视觉约束", "sha256": "unused"},
        {"id": "g2", "content": "独立屏幕措辞", "available_assets": [{"assetRef": {"id": "asset", "version": "1", "private": "unused"}, "description": "真实主体说明", "path": "private.png"}]},
    ]
    brief = {"theme": "neutral-baseline", "asset_budget": 1, "effects": ["unused"], "sha256": "unused"}
    context = planning_context(contract, brief)
    wire = json.dumps(context, ensure_ascii=False)
    assert all(word not in wire for word in ("private", "unused", "sha256", "effects"))
    assert "content" not in context["slide"]["visual_groups"][0]
    assert "独立屏幕措辞" in wire and "真实主体说明" in wire and "必须保留的视觉约束" in wire
    assert context["slide"]["narration_beats"][0]["spoken_text"] == CONTRACT_SLIDE["narration_beats"][0]["spoken_text"]


def test_prompt_adds_true_capacity_not_all_effects():
    caps = _registered_capabilities(ROOT)
    prompts = build_plan_generation_prompts(CONTRACT_SLIDE, caps, plan_version="0.2.0")
    assert "maxLines" in prompts["system_prompt"] and "contentBottom" in prompts["system_prompt"]
    assert "已注册效果" not in prompts["system_prompt"]
    assert "仅是资料" in prompts["system_prompt"]


def test_normal_storyboard_contract_preserves_title_display_and_visual_anchor():
    contract = copy.deepcopy(CONTRACT_SLIDE)
    contract.pop("title", None)
    contract["main_title"] = "正常入口标题"
    contract["visual_groups"] = [{"id": "g1", "display_text": "屏幕文字", "visible_text": "屏幕文字",
                                  "visual_anchor": "分词器连接到独立编号对象", "mask_target": "unused"}]
    before = copy.deepcopy(contract)
    payload = planning_context(contract, None)["slide"]
    assert payload["title"] == "正常入口标题"
    assert payload["visual_groups"] == [{"id": "g1", "content": "屏幕文字",
                                         "description": "分词器连接到独立编号对象"}]
    assert payload["narration_beats"][0]["spoken_text"] == contract["narration_beats"][0]["spoken_text"]
    assert contract == before


def test_bad_authority_is_rejected_before_provider(tmp_path):
    contract = copy.deepcopy(CONTRACT_SLIDE)
    contract["narration_beats"][1]["id"] = contract["narration_beats"][0]["id"]
    def provider(**kwargs):
        pytest.fail("Invalid source must not consume a provider request")
    with pytest.raises(HtmlReviewError) as caught:
        generate_scene_plan(contract, run_dir=tmp_path, repo_root=ROOT, json_generator=provider, plan_version="0.2.0")
    assert caught.value.code == "PLAN_CONTEXT_INVALID"


def test_structural_retry_preserves_valid_action_identity():
    previous = semantic_plan()
    current = copy.deepcopy(previous)
    current["beats"][0]["actions"][0]["actionId"] = "renamed"
    with pytest.raises(SemanticPlanError) as caught:
        preserve_action_identity(previous, current)
    assert caught.value.code == "SEMANTIC_ACTION_ID_CHANGED"
    # Duplicate, invalid old identity must be repairable.
    previous["beats"][1]["actions"][0]["actionId"] = previous["beats"][0]["actions"][0]["actionId"]
    preserve_action_identity(previous, current)


def test_retry_identity_guard_is_on_model_execution_path(tmp_path):
    previous, current = semantic_plan(), semantic_plan()
    previous["beats"][0].pop("visualIntent")
    current["beats"][0]["actions"][0]["actionId"] = "renamed"
    responses = [previous, current]
    with pytest.raises(HtmlReviewError, match="SEMANTIC_ACTION_ID_CHANGED"):
        generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT, json_generator=lambda **kw: responses.pop(0), plan_version="0.2.0")
    record = json.loads((tmp_path / "planning/html_visual/records/plan-slide_001.json").read_text(encoding="utf-8"))
    assert record["accepted"] is False


def test_agent_resolves_exact_registered_version():
    from html_candidate_agent import _registered_reference
    rows = [{"id": "layout", "version": "1", "box": "old"}, {"id": "layout", "version": "2", "box": "current"}]
    assert _registered_reference(rows, {"id": "layout", "version": "2"})["box"] == "current"
    with pytest.raises(HtmlReviewError) as caught:
        _registered_reference(rows, {"id": "layout", "version": "3"})
    assert caught.value.code == "REPAIR_REFERENCE_VERSION"


def test_generic_figure_claim_does_not_gain_semantic_approval():
    plan = normalize(semantic_plan())
    plan["beats"][-1].update(visualIntent="为回复预留空间/检查实际用量", targets=[{"objectId": "figure", "purpose": "泛化容器"}], actions=[{"actionId": "generic", "objectId": "figure", "type": "emphasize"}], expectedState=[{"objectId": "figure", "visible": True, "expression": "容器可见"}])
    assert build_semantic_design(plan)["semantic_review"] == "pending_review"
