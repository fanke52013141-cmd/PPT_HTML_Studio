"""A01 contracts and real boundary signatures; fixtures are not model evidence."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from html_semantic_plan import HtmlPlanGenerateRequest
from html_storyboard_planning import HtmlScenePlanError, load_template_catalog, normalize_html_scene_plan, plan_evidence
from html_visual_review_service import generate_scene_plan, HtmlReviewError
from checks.test_html_storyboard_planning import valid_plan, CONTRACT_SLIDE

ROOT = Path(__file__).resolve().parents[1]


def semantic_plan(contract=CONTRACT_SLIDE):
    plan = valid_plan()
    plan["version"] = "0.2.0"
    plan["slide_id"] = contract["slide_id"]
    plan["assets"][0]["id"] = plan["slots"]["subject"]["assetRef"]["id"]
    for obj in plan["objects"]:
        instructional = obj["id"] in ("card-1", "card-2")
        obj.update(role="instructional" if instructional else "context", initialVisible=not instructional)
        if not instructional:
            obj["initialVisibleReason"] = "上下文结构在开始时帮助定位页面"
    plan["beats"] = []
    for i, beat in enumerate(contract["narration_beats"]):
        ids = ["card-1", "card-2"]
        plan["beats"].append({
            "id": beat["id"], "visualIntent": "测试视觉表达声明，不代表真实画面语义已验收",
            "targets": [{"objectId": target, "purpose": "展示本句的具体说明"} for target in ids],
            "actions": [{"actionId": f"{beat['id']}-{target}", "objectId": target, "type": "enter" if i == 0 else "emphasize"} for target in ids],
            "expectedState": [{"objectId": target, "visible": True, "expression": "能看到声明的解释内容"} for target in ids],
        })
    return plan


def normalize(plan, contract=CONTRACT_SLIDE):
    return normalize_html_scene_plan(plan, load_template_catalog(ROOT), contract_slide=contract)


def test_many_targets_repeated_emphasis_preserves_source_and_identity():
    plan = normalize(semantic_plan())
    assert len(plan["beats"][0]["actions"]) == 2
    assert plan["beats"][1]["actions"][0]["type"] == "emphasize"
    assert normalize(plan) == plan
    for beat, source in zip(plan["beats"], CONTRACT_SLIDE["narration_beats"]):
        assert beat["spoken_text"] == source["spoken_text"]
        assert beat["spoken_text_sha256"] == hashlib.sha256(source["spoken_text"].encode()).hexdigest()
    evidence = plan_evidence(plan)
    assert evidence["semantic"]["meaning"] == "pending_review"
    assert evidence["semantic"]["runtime"] == "not_implemented"


@pytest.mark.parametrize("mutation,code", [
    (lambda p: p["beats"].pop(), "SEMANTIC_BEAT_COVERAGE"),
    (lambda p: p["beats"].reverse(), "SEMANTIC_BEAT_COVERAGE"),
    (lambda p: p["beats"][0].update(id="unknown"), "SEMANTIC_BEAT_COVERAGE"),
    (lambda p: p["beats"][0].update(spoken_text="重写后的讲稿"), "SEMANTIC_SPOKEN_MISMATCH"),
    (lambda p: p["beats"][0].update(spoken_text_sha256="f" * 64), "SEMANTIC_SPOKEN_MISMATCH"),
    (lambda p: p["beats"][0]["targets"][0].update(objectId="unknown"), "SEMANTIC_TARGET_UNKNOWN"),
    (lambda p: p["beats"][0]["actions"][0].update(objectId="header"), "SEMANTIC_ACTION_TARGET"),
    (lambda p: p["beats"][1]["actions"][0].update(actionId=p["beats"][0]["actions"][0]["actionId"]), "SEMANTIC_ACTION_DUPLICATE"),
    (lambda p: p["beats"][1]["actions"][0].update(type="enter"), "SEMANTIC_ENTER_DUPLICATE"),
    (lambda p: p["beats"][0]["actions"][0].update(type="invent"), "SEMANTIC_SCHEMA_INVALID"),
    (lambda p: p["beats"][0].update(target={"objectId": "figure", "action": "emphasize"}), "SEMANTIC_SCHEMA_INVALID"),
    (lambda p: p["beats"][0].pop("visualIntent"), "SEMANTIC_SCHEMA_INVALID"),
    (lambda p: p["beats"][0]["targets"][0].pop("purpose"), "SEMANTIC_SCHEMA_INVALID"),
    (lambda p: p["beats"][0].update(expectedState=[]), "SEMANTIC_VISUAL_EXPRESSION_MISSING"),
    (lambda p: p["beats"][0]["expectedState"][0].update(visible=False), "SEMANTIC_STATE_UNSUPPORTED"),
    (lambda p: p["beats"][0].update(narration_only=True), "SEMANTIC_NARRATION_ONLY_INVALID"),
    (lambda p: p["objects"][0].pop("initialVisibleReason"), "SEMANTIC_INITIAL_VISIBILITY"),
    (lambda p: p["objects"][3].update(initialVisible=True, initialVisibleReason="逃逸"), "SEMANTIC_INITIAL_VISIBILITY"),
    (lambda p: p.update(version="0.3.0"), "PLAN_VERSION_UNSUPPORTED"),
    (lambda p: p.pop("version"), "PLAN_VERSION_REQUIRED"),
])
def test_invalid_claims_fail_closed(mutation, code):
    plan = semantic_plan()
    mutation(plan)
    with pytest.raises(HtmlScenePlanError) as caught:
        normalize(plan)
    assert caught.value.code == code


def test_explicit_narration_only_and_instructional_not_zero_time():
    plan = semantic_plan()
    plan["beats"][-1].update(targets=[], actions=[], expectedState=[], narration_only=True, narrationOnlyReason="收尾转场，无新增知识点")
    assert normalize(plan)["beats"][-1]["narrationOnlyReason"]
    for beat in plan["beats"][:-1]:
        beat["actions"] = [a for a in beat["actions"] if a["objectId"] != "card-2"]
    with pytest.raises(HtmlScenePlanError, match="instructional"):
        normalize(plan)


def test_twenty_existing_token_beats_have_exact_authoritative_trace():
    course = json.loads((ROOT / "checks/fixtures/html/token-five-page.json").read_text(encoding="utf-8"))
    count = 0
    for slide in course["slides"]:
        normalized = normalize(semantic_plan(slide), slide)
        assert [b["id"] for b in normalized["beats"]] == [b["id"] for b in slide["narration_beats"]]
        count += len(normalized["beats"])
    assert count == 20


def test_source_bytes_and_missing_source():
    contract = copy.deepcopy(CONTRACT_SLIDE)
    contract["narration_beats"][0]["spoken_text"] = "  原文\n"
    assert normalize(semantic_plan(contract), contract)["beats"][0]["spoken_text"] == "  原文\n"
    with pytest.raises(HtmlScenePlanError) as caught:
        normalize(semantic_plan(), {})
    assert caught.value.code == "SEMANTIC_SOURCE_REQUIRED"


def test_new_plan_uses_explicit_semantic_runtime():
    from html_production_service import compile_plan
    scene, binding = compile_plan(normalize(semantic_plan()), CONTRACT_SLIDE, load_template_catalog(ROOT))
    assert scene["version"] == "0.6.0" and binding["version"] == "0.2.0"


def test_generator_repairs_downgrade_once_and_records_actual_version(tmp_path):
    responses, calls = [valid_plan(), semantic_plan()], []
    def generator(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)
    result = generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT, json_generator=generator, plan_version="0.2.0")
    assert result["version"] == "0.2.0" and len(calls) == 2
    assert all(call["request_timeout"] == 1800 and call["stream_output"] for call in calls)
    assert "单一已注册动作" not in calls[0]["system_prompt"]
    assert "为回复预留空间" in calls[0]["system_prompt"]
    record = json.loads((tmp_path / "planning/html_visual/records/plan-slide_001.json").read_text(encoding="utf-8"))
    assert record["attempts"][0]["diagnostic_code"] == "PLAN_VERSION_MISMATCH"
    assert record["request_context"]["plan_version"] == "0.2.0"
    request = json.loads((tmp_path / "planning/html_visual/review/html_scene_plan_slide_001-round-2-request.json").read_text(encoding="utf-8"))
    assert request["system_prompt"] == calls[1]["system_prompt"]
    assert request["user_prompt"] == calls[1]["user_prompt"]
    assert request["request_timeout_seconds"] == calls[1]["request_timeout"]


def test_schema_same_for_web_agent_mcp_cli():
    from html_visual_review_routes import PlanGenerateRequest
    from agent_contract.capabilities import CAPABILITIES
    cap = next(c for c in CAPABILITIES if c.id == "html_review.plan_generate")
    assert cap.request_model is PlanGenerateRequest is HtmlPlanGenerateRequest
    assert cap.request_model(plan_version="0.2.0").plan_version == "0.2.0"
    for payload in ({"plan_version": "bad"}, {"unexpected": True}):
        with pytest.raises(ValidationError):
            HtmlPlanGenerateRequest(**payload)


def test_actual_client_mcp_cli_forward_version(monkeypatch):
    from agent_client.client import AgentClient
    from mcp_server.tools import _dispatch
    from cli.pptctl import build_parser
    client, captured = AgentClient(), []
    def transport(method, path, *, body=None):
        captured.append((method, path, body))
        return {"plan": {"version": body.get("plan_version", "0.1.0")}}
    monkeypatch.setattr(client, "_request", transport)
    assert _dispatch("html_review.plan_generate", {"project_id": "p", "slide_id": "s", "plan_version": "0.2.0"}, client)["plan"]["version"] == "0.2.0"
    assert captured[0] == ("POST", "/projects/p/html-review/s/plan/generate", {"plan_version": "0.2.0"})
    assert client.post_html_plan_generate("p", "s")["plan"]["version"] == "0.1.0"
    args = build_parser().parse_args(["html", "plan-generate", "--project", "p", "--slide", "s", "--file", "request.json"])
    assert args.file == "request.json"


def test_web_and_agent_forward_to_same_generator(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import html_visual_review_routes as web
    import agent_api.routes as agent
    calls = []
    def generate(contract, *, run_dir, repo_root, json_generator, brief, plan_version):
        calls.append(plan_version)
        return normalize(semantic_plan())
    monkeypatch.setattr(web.review, "generate_scene_plan", generate)
    monkeypatch.setattr(web, "_html_project", lambda *a: object())
    monkeypatch.setattr(web, "project_run_dir_or_500", lambda *a: tmp_path)
    monkeypatch.setattr(web, "_contract_slide", lambda *a: CONTRACT_SLIDE)
    monkeypatch.setattr(web, "_dependencies", SimpleNamespace(repo_root=ROOT, json_generator=lambda: None))
    payload = HtmlPlanGenerateRequest(plan_version="0.2.0")
    assert web.generate_plan("p", "slide_001", payload, db=None)["plan"]["version"] == "0.2.0"
    monkeypatch.setattr(agent, "_html_project_or_404", lambda *a: object())
    monkeypatch.setattr(agent, "_contract_slide_or_404", lambda *a: CONTRACT_SLIDE)
    monkeypatch.setattr(agent, "_agent_review_deps", lambda: web._dependencies)
    import project_path_service
    monkeypatch.setattr(project_path_service, "project_run_dir_or_500", lambda *a: tmp_path)
    assert agent.agent_html_plan_generate("p", "slide_001", payload=payload, db=None).plan["version"] == "0.2.0"
    assert calls == ["0.2.0", "0.2.0"]


def test_downgrade_never_falls_back_after_two_failures(tmp_path):
    calls = []
    def generator(**kwargs):
        calls.append(kwargs)
        return valid_plan()
    with pytest.raises(HtmlReviewError):
        generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT, json_generator=generator, plan_version="0.2.0")
    assert len(calls) == 2


def test_request_evidence_survives_provider_exception(tmp_path):
    calls = []
    def generator(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("not a provider success")
    with pytest.raises(TimeoutError):
        generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT, json_generator=generator, plan_version="0.2.0")
    request = json.loads((tmp_path / "planning/html_visual/review/html_scene_plan_slide_001-round-1-request.json").read_text(encoding="utf-8"))
    assert request["plan_version"] == "0.2.0"
    assert len(calls) == 1 and calls[0]["request_timeout"] == 1800
    assert request["request_timeout_seconds"] == 1800 and request["stream_output"]
    assert request["system_prompt_sha256"] == hashlib.sha256(request["system_prompt"].encode()).hexdigest()


def test_new_slot_object_declarations_cannot_duplicate():
    plan = semantic_plan()
    extra = copy.deepcopy(plan["objects"][0])
    extra["id"] = "duplicated-header"
    plan["objects"].append(extra)
    with pytest.raises(HtmlScenePlanError) as caught:
        normalize(plan)
    assert caught.value.code == "SEMANTIC_SLOT_OBJECTS"
