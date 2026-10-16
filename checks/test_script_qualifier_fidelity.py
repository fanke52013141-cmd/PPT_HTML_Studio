"""Conservative source-to-script scope checks, without provider calls."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from storyboard_planning import script_qualifier_risks
from storyboard_prompt_templates import compose_step2_script_system_prompt
import storyboard_service as service

SOURCE = "不存在适用于所有地区和岗位的统一标准。具体要求以公告为准。"


def plan(text):
    return {"title": "test", "slides": [{"slide_id": "slide_001", "slide_title": "test", "narration": text}]}


@pytest.mark.parametrize("text", ["没有统一标准。", "不存在统一标准，直接报考即可。", "并无统一标准。"])
def test_scoped_negative_must_not_become_absolute(text):
    issues = script_qualifier_risks(SOURCE, plan(text))
    assert issues and issues[0]["anchor"] == "统一标准"
    assert issues[0]["source_excerpt"] in SOURCE


@pytest.mark.parametrize("text", [
    "不存在适用于所有地区和岗位的统一标准。",
    "不能说没有统一标准，应查看当地公告。",
    "具体要求以公告为准。", "没有统一教材。",
])
def test_preserved_scope_and_unrelated_claims_do_not_trigger(text):
    assert script_qualifier_risks(SOURCE, plan(text)) == []


def test_risk_is_local_to_sentence_and_slide():
    candidate = plan("所有考生要看公告。没有统一标准。")
    assert script_qualifier_risks(SOURCE, candidate)


def test_actual_generation_stops_before_persistence_without_retry(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(service, "project_or_404", lambda *args: SimpleNamespace(id="isolated", run_dir=str(tmp_path)))
    monkeypatch.setattr(service, "read_project_article_source", lambda *args: {"title": "test", "content": SOURCE})
    monkeypatch.setattr(service, "read_step2_prompts_for_project", lambda *args, **kw: {"script_system": "custom", "script_output_example": "{}"})
    monkeypatch.setattr(service, "run_step2_json_llm", lambda **kw: calls.append(kw) or plan("没有统一标准。"))
    monkeypatch.setattr(service, "_persist_step2_script_plan", lambda *args: pytest.fail("Risky script must not replace saved work"))
    with pytest.raises(HTTPException) as caught:
        service.execute_step2_script_plan.__wrapped__("isolated", None)
    assert caught.value.status_code == 409
    assert caught.value.detail["automatic_retry"] is False
    assert len(calls) == 1
    assert "<FidelityPolicy" in calls[0]["system_prompt"]
    assert calls[0]["system_prompt"] == compose_step2_script_system_prompt("custom", "{}")


def test_manual_edit_cannot_bypass_scope_check(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "project_or_404", lambda *args: SimpleNamespace(run_dir=str(tmp_path)))
    monkeypatch.setattr(service, "read_project_article_source", lambda *args: {"title": "test", "content": SOURCE})
    monkeypatch.setattr(service, "_persist_step2_script_plan", lambda *args: pytest.fail("no write"))
    with pytest.raises(HTTPException):
        service.update_step2_script_plan("isolated", plan("没有统一标准。"), None)


def test_existing_risky_script_stops_visual_before_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "read_project_article_source", lambda *args: {"title": "test", "content": SOURCE})
    monkeypatch.setattr(service, "run_step2_json_llm", lambda **kw: pytest.fail("must stop before paid visual request"))
    with pytest.raises(HTTPException) as caught:
        service._execute_step2_visual_plan(SimpleNamespace(run_dir=str(tmp_path)), plan("没有统一标准。"))
    assert caught.value.detail["code"] == "SCRIPT_QUALIFIER_REVIEW_REQUIRED"
