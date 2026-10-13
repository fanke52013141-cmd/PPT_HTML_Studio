"""A01 contract regression: exact authority, multi-actions and no downgrade."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from html_scene_plan_models import HtmlPlanGenerationRequest
from html_storyboard_planning import (
    HtmlScenePlanError, load_template_catalog, normalize_html_scene_plan, plan_evidence,
)
from html_visual_review_service import HtmlReviewError, generate_scene_plan
from test_html_visual_review import CONTRACT_SLIDE, model_plan

ROOT = Path(__file__).resolve().parents[1]
CATALOG = load_template_catalog(ROOT)


def semantic_plan():
    plan = model_plan()
    plan["version"] = "0.2.0"
    plan["beats"] = [
        {
            "id": beat["id"], "visualIntent": intent,
            "targets": [{"objectId": target, "role": "instructional", "meaning": intent}],
            "actions": [{"actionKey": key, "objectId": target, "type": "enter",
                         "expectedState": {"visible": True, "meaning": intent}}],
        }
        for beat, target, key, intent in zip(
            CONTRACT_SLIDE["narration_beats"], ["stat-1", "summary"], ["freezing-point", "freezing-process"],
            ["显示标准大气压下的冰点为 0°C", "显示液态水放热凝固为冰的关系"], strict=True
        )
    ]
    return plan


def normalize(plan, source=None):
    return normalize_html_scene_plan(plan, CATALOG, contract_slide=source or CONTRACT_SLIDE,
                                     expected_version="0.2.0")


def test_multi_target_and_repeat_emphasis_have_stable_independent_identity():
    plan = semantic_plan()
    first = plan["beats"][0]
    first["targets"].append({"objectId": "summary", "role": "instructional", "meaning": "液态→固态"})
    first["actions"].append({"actionKey": "relation-enter", "objectId": "summary", "type": "enter",
                              "expectedState": {"visible": True, "meaning": "显示液态→固态关系"}})
    first["actions"].append({"actionKey": "temperature-first-focus", "objectId": "stat-1", "type": "emphasize",
                              "expectedState": {"visible": True, "meaning": "强调冰点"}})
    second = plan["beats"][1]
    second["targets"].append(copy.deepcopy(first["targets"][0]))
    second["actions"].append({**copy.deepcopy(first["actions"][-1]), "actionKey": "temperature-second-focus"})
    frozen = normalize(plan)
    actions = [action for beat in frozen["beats"] for action in beat["actions"]]
    assert len({action["actionId"] for action in actions}) == 5
    reordered = copy.deepcopy(plan)
    reordered["beats"].reverse()
    reordered["beats"][1]["actions"].reverse()
    assert {a["actionKey"]: a["actionId"] for b in normalize(reordered)["beats"] for a in b["actions"]} == {
        a["actionKey"]: a["actionId"] for a in actions
    }
    assert [b["id"] for b in normalize(reordered)["beats"]] == [b["id"] for b in CONTRACT_SLIDE["narration_beats"]]


def test_authority_frozen_byte_exact_and_idempotent():
    source = copy.deepcopy(CONTRACT_SLIDE)
    source["narration_beats"][0]["spoken_text"] = "  标准大气压下，水在0摄氏度结冰。\n"
    frozen = normalize(semantic_plan(), source)
    text = source["narration_beats"][0]["spoken_text"]
    assert frozen["beats"][0]["spoken_text"] == text
    assert frozen["beats"][0]["spoken_text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert normalize(frozen, source) == frozen
    source["narration_beats"][0]["spoken_text"] = "改过的讲稿"
    with pytest.raises(HtmlScenePlanError, match="权威原句") as rejected:
        normalize(frozen, source)
    assert rejected.value.code == "SEMANTIC_SOURCE_CHANGED"


@pytest.mark.parametrize("change,code", [
    (lambda p: p["beats"][0].pop("visualIntent"), "SEMANTIC_BEAT_INVALID"),
    (lambda p: p["beats"][0].update(visualIntent="  "), "SEMANTIC_BEAT_INVALID"),
    (lambda p: p["beats"][0].update(target={"objectId": "stat-1", "action": "enter"}), "SEMANTIC_BEAT_INVALID"),
    (lambda p: p["beats"][0]["targets"][0].update(objectId="gone"), "PLAN_BEAT_TARGET_UNKNOWN"),
    (lambda p: p["beats"][0]["actions"][0].update(objectId="summary"), "SEMANTIC_ACTION_TARGET"),
    (lambda p: p["beats"][0]["actions"][0].update(type="spin"), "SEMANTIC_BEAT_INVALID"),
    (lambda p: p["beats"][1]["actions"][0].update(actionKey="freezing-point"), "SEMANTIC_ACTION_DUPLICATE"),
    (lambda p: p["beats"][0]["actions"][0].update(expectedState={"visible": True, "meaning": ""}), "SEMANTIC_BEAT_INVALID"),
    (lambda p: p["beats"][0]["actions"][0].update(expectedState={"visible": 1, "meaning": "冰点"}), "SEMANTIC_BEAT_INVALID"),
    (lambda p: p["beats"][0].update(actions=[]), "SEMANTIC_EXPRESSION_MISSING"),
    (lambda p: p["beats"][0]["targets"][0].update(role="decorative"), "SEMANTIC_DECORATION_ACTION"),
    (lambda p: p["beats"][0]["targets"][0].update(role="context"), "SEMANTIC_INSTRUCTION_MISSING"),
    (lambda p: p["beats"][0].update(id="unknown"), "PLAN_BEAT_UNKNOWN"),
    (lambda p: p["beats"].pop(), "PLAN_BEAT_MISSING"),
    (lambda p: p["beats"].append(copy.deepcopy(p["beats"][0])), "PLAN_BEAT_DUPLICATE"),
    (lambda p: p["objects"].pop(), "OBJECT_SLOT_MISMATCH"),
    (lambda p: p.update(version="0.1.0"), "PLAN_VERSION_MISMATCH"),
])
def test_invalid_or_downgraded_expression_rejected(change, code):
    plan = semantic_plan()
    change(plan)
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(plan)
    assert rejected.value.code == code


def test_narration_only_needs_explicit_reason_and_no_claimed_visuals():
    plan = semantic_plan()
    plan["beats"][0].update(narration_only=True, targets=[], actions=[])
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(plan)
    assert rejected.value.code == "SEMANTIC_NARRATION_REASON"
    plan["beats"][0]["narration_only_reason"] = "本句引出问题，下一句才解释具体状态"
    assert normalize(plan)["beats"][0]["narration_only"] is True
    plan["beats"][0]["targets"] = copy.deepcopy(semantic_plan()["beats"][0]["targets"])
    with pytest.raises(HtmlScenePlanError):
        normalize(plan)


def test_source_validation_precedes_any_model_request(tmp_path):
    calls = []
    with pytest.raises(HtmlReviewError) as rejected:
        generate_scene_plan({"slide_id": "slide_001", "narration_beats": []}, run_dir=tmp_path,
                            repo_root=ROOT, json_generator=lambda **kw: calls.append(kw), plan_version="0.2.0")
    assert rejected.value.code == "SEMANTIC_SOURCE_MISSING"
    assert calls == []


@pytest.mark.parametrize("beats", [None, 1, "bad", []])
def test_invalid_legacy_beats_keep_diagnostic_instead_of_type_error(beats):
    plan = model_plan()
    plan["beats"] = beats
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize_html_scene_plan(plan, CATALOG, contract_slide=CONTRACT_SLIDE)
    assert rejected.value.code == "PLAN_BEATS_MISSING"


def test_frozen_action_identity_and_narration_are_not_model_overrides():
    frozen = normalize(semantic_plan())
    frozen["beats"][0]["actions"][0]["actionId"] = "act-forged"
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(frozen)
    assert rejected.value.code == "SEMANTIC_ACTION_ID_CHANGED"
    frozen = normalize(semantic_plan())
    frozen["beats"][0]["spoken_text"] = "模型改写原句"
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(frozen)
    assert rejected.value.code == "SEMANTIC_SOURCE_CHANGED"


@pytest.mark.parametrize("source", [
    {"slide_id": "bad/slide", "narration_beats": CONTRACT_SLIDE["narration_beats"]},
    {"slide_id": "slide_001", "narration_beats": [CONTRACT_SLIDE["narration_beats"][0]] * 2},
    {"slide_id": "slide_001", "narration_beats": [{"id": "bad/beat", "spoken_text": "text"}]},
    {"slide_id": "slide_001", "narration_beats": [{"id": "b1", "text": "旧别名不能猜测为原句"}]},
])
def test_invalid_authority_rejected_before_paid_calls(tmp_path, source):
    calls = []
    with pytest.raises(HtmlReviewError):
        generate_scene_plan(source, run_dir=tmp_path, repo_root=ROOT,
                            json_generator=lambda **kw: calls.append(kw), plan_version="0.2.0")
    assert not calls


def test_generation_repairs_structural_failure_without_legacy_downgrade(tmp_path):
    responses = [model_plan(), semantic_plan()]
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    plan = generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT,
                               json_generator=generate, plan_version="0.2.0")
    assert plan["version"] == "0.2.0"
    assert len(calls) == 2
    user = json.loads(calls[0]["user_prompt"])
    assert user["slide"]["narration_beats"] == CONTRACT_SLIDE["narration_beats"]
    assert "spoken_text_sha256" not in calls[0]["user_prompt"]
    assert "PromptVersion:html-plan-0.5.0" in calls[0]["system_prompt"]
    assert "beats映射单一" not in calls[0]["system_prompt"]
    evidence = plan_evidence(plan)
    assert evidence["validation"] == {"structure": "passed", "semantic": "not_run", "audio": "not_run", "human": "pending_review"}
    assert evidence["beat_map"][plan["beats"][0]["id"]]["actions"][0]["actionId"]
    record = json.loads((tmp_path / "planning/html_visual/records/plan-slide_001-v0.2.0.json").read_text(encoding="utf-8"))
    assert record["attempts"][0]["diagnostic_code"] == "PLAN_VERSION_MISMATCH"
    with pytest.raises(HtmlReviewError):
        generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT,
                            json_generator=lambda **_: model_plan(), plan_version="0.2.0")


def test_shared_web_agent_request_and_response_schema():
    import html_visual_review_routes as web
    from agent_contract.models import HtmlPlanGenerationRequest as agent_request, HtmlPlanGenerationResult
    from agent_contract.capabilities import CAPABILITIES
    assert web.PlanGenerateRequest is agent_request is HtmlPlanGenerationRequest
    assert agent_request().plan_version == "0.1.0"
    assert agent_request(plan_version="0.2.0").plan_version == "0.2.0"
    assert agent_request(plan_version="0.1.0").plan_version == "0.1.0"
    with pytest.raises(ValidationError):
        agent_request(plan_version="unknown")
    cap = next(c for c in CAPABILITIES if c.id == "html_review.plan_generate")
    assert cap.request_model is agent_request
    assert cap.version == "1.2"
    frozen = normalize(semantic_plan())
    response = HtmlPlanGenerationResult(project_id="project", slide_id="slide_001", plan=frozen,
                                       evidence=plan_evidence(frozen))
    assert response.model_dump()["plan"]["beats"][0]["actions"][0]["actionId"]
    definitions = response.model_json_schema()["$defs"]
    assert "visualIntent" in definitions["FrozenSemanticBeat"]["properties"]


def test_new_plan_cannot_be_compiled_as_legacy_scene():
    from html_production_service import compile_plan
    with pytest.raises(HtmlReviewError) as rejected:
        compile_plan(normalize(semantic_plan()), CONTRACT_SLIDE, CATALOG)
    assert rejected.value.code == "SEMANTIC_COMPILER_PENDING"


def test_all_twenty_s08_beats_are_preserved_and_old_mappings_rejected():
    audit = json.loads((ROOT / "docs/plans/html-backend-development/evidence/s08-narration-audit-2026-10-13.json").read_text(encoding="utf-8"))
    count = 0
    for page in audit["pages"]:
        source = {"slide_id": "slide_001", "narration_beats": [
            {"id": beat["beat_id"], "spoken_text": beat["spoken_text"]} for beat in page["beats"]
        ]}
        plan = semantic_plan()
        plan["beats"] = []
        for index, beat in enumerate(source["narration_beats"]):
            expression = copy.deepcopy(semantic_plan()["beats"][0])
            expression["id"] = beat["id"]
            # Contract fixture only: no claim that this is a correct course design.
            expression["visualIntent"] = "合同追踪测试；实际画面含义仍待独立 QA"
            expression["actions"][0]["actionKey"] = f"contract-trace-{index}"
            plan["beats"].append(expression)
        frozen = normalize(plan, source)
        assert [b["spoken_text"] for b in frozen["beats"]] == [b["spoken_text"] for b in source["narration_beats"]]
        assert plan_evidence(frozen)["validation"]["semantic"] == "not_run"
        legacy = copy.deepcopy(plan)
        legacy["beats"] = [{"id": b["id"], "target": {"objectId": "stat-1", "action": "emphasize"}} for b in source["narration_beats"]]
        with pytest.raises(HtmlScenePlanError) as rejected:
            normalize(legacy, source)
        assert rejected.value.code == "SEMANTIC_BEAT_INVALID"
        count += len(source["narration_beats"])
    assert count == 20
