from __future__ import annotations

from pathlib import Path
import sys
import json
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from storyboard_planning import (
    build_step2_visual_repair_user_prompt,
    compose_visual_contract_from_plans,
    normalize_slide_visual_plan,
)
from visual_contract_service import normalize_visual_contract


SCRIPT_PLAN = {
    "title": "测试主题",
    "slides": [{
        "slide_id": "slide_001",
        "slide_title": "三个阶段",
        "narration": "先看三个阶段。它们在这一段说明中同时展示。",
    }],
}


def test_old_visual_plan_defaults_to_sequential_reveal() -> None:
    plan = normalize_slide_visual_plan({
        "slides": [{
            "slide_id": "slide_001",
            "visual_elements": [
                {"element_id": "el_001", "role": "title", "visual_type": "text", "visual_description": "三个阶段", "narration": "先看三个阶段。"},
                {"element_id": "el_002", "role": "body", "visual_type": "picture", "visual_description": "三个独立卡片横向排列", "narration": "它们在这一段说明中同时展示。"},
            ],
        }],
    }, SCRIPT_PLAN)
    assert plan["slides"][0]["visual_elements"][1]["reveal_mode"] == "sequential"


def test_reordering_script_pages_keeps_existing_visuals(monkeypatch, tmp_path: Path) -> None:
    import storyboard_service as service

    old = {"title": "主题", "slides": [
        {"slide_id": "slide_001", "slide_title": "一", "narration": "第一段"},
        {"slide_id": "slide_002", "slide_title": "二", "narration": "第二段"},
    ]}
    reordered = {"title": "主题", "slides": list(reversed(old["slides"]))}
    visual_path = tmp_path / "slide_visual_plan.json"
    visual_path.write_text(json.dumps({"slides": [
        {"slide_id": "slide_001", "visual_elements": [{"element_id": "one"}]},
        {"slide_id": "slide_002", "visual_elements": [{"element_id": "two"}]},
    ]}), encoding="utf-8")
    monkeypatch.setattr(service, "step2_visual_plan_path", lambda _project: str(visual_path))

    assert service._sync_visual_plan_for_script_reorder(SimpleNamespace(), old, reordered)
    saved = json.loads(visual_path.read_text(encoding="utf-8"))
    assert [slide["slide_id"] for slide in saved["slides"]] == ["slide_002", "slide_001"]
    assert saved["source_script_hash"] == service._step2_script_plan_fingerprint(reordered)
    assert service._step2_visual_plan_status(SimpleNamespace(), reordered) == (True, False)

    changed = json.loads(json.dumps(reordered))
    changed["slides"][0]["narration"] = "改过的第二段"
    assert not service._sync_visual_plan_for_script_reorder(SimpleNamespace(), reordered, changed)


def test_together_intent_is_preserved_in_the_contract_and_manual_normalization() -> None:
    visual_plan = normalize_slide_visual_plan({
        "slides": [{
            "slide_id": "slide_001",
            "visual_elements": [
                {"element_id": "el_001", "role": "title", "visual_type": "text", "visual_description": "三个阶段", "narration": "先看三个阶段。", "reveal_mode": "sequential"},
                {"element_id": "el_002", "role": "body", "visual_type": "picture", "visual_description": "三个独立卡片横向排列", "narration": "它们在这一段说明中同时展示。", "reveal_mode": "together"},
            ],
        }],
    }, SCRIPT_PLAN)
    contract = compose_visual_contract_from_plans(SCRIPT_PLAN, visual_plan, "test", "测试主题")
    assert contract["slides"][0]["visual_groups"][1]["reveal_mode"] == "together"
    old_contract = {"slides": [{"visual_groups": [{"id": "old", "role": "content_body"}]}]}
    assert normalize_visual_contract(old_contract)["slides"][0]["visual_groups"][0]["reveal_mode"] == "sequential"


def test_atomicity_repair_prompt_requires_a_full_plan_without_animation_choice() -> None:
    prompt = build_step2_visual_repair_user_prompt(
        SCRIPT_PLAN,
        {"slides": []},
        "Visual group slide_001_el_002 in slide_001 describes multiple independent visual islands",
    )
    assert "重新输出全部 slides" in prompt
    assert "不输出 reveal_mode" in prompt


def test_compose_retries_atomicity_failure_once_with_the_repaired_plan(monkeypatch, tmp_path: Path) -> None:
    """The quality gate gets one specific repair attempt before pausing Step 2."""
    import server  # Configure storyboard dependencies as the app does.
    import storyboard_service as service

    del server
    planning = tmp_path / "planning"
    planning.mkdir()
    initial_plan = normalize_slide_visual_plan({
        "slides": [{
            "slide_id": "slide_001",
            "visual_elements": [
                {"element_id": "el_001", "role": "title", "visual_type": "text", "visual_description": "三个阶段", "narration": "先看三个阶段。"},
                {"element_id": "el_002", "role": "body", "visual_type": "picture", "visual_description": "三个独立卡片横向排列", "narration": "它们在这一段说明中同时展示。"},
            ],
        }],
    }, SCRIPT_PLAN)
    repaired_plan = json.loads(json.dumps(initial_plan, ensure_ascii=False))
    repaired_plan["slides"][0]["visual_elements"][1]["reveal_mode"] = "together"
    (planning / "slide_script_plan.json").write_text(json.dumps(SCRIPT_PLAN, ensure_ascii=False), encoding="utf-8")
    (planning / "slide_visual_plan.json").write_text(json.dumps(initial_plan, ensure_ascii=False), encoding="utf-8")

    # 项目桩必须覆盖 compose_step2_visual_contract 真正读取的列。
    # target_duration_sec 是真实数据库列（database.py + 迁移 0015），
    # 漏掉它会让这里报 AttributeError，而不是被测的修复重试逻辑。
    project = SimpleNamespace(
        id="project-reveal",
        run_dir=str(tmp_path),
        mask_enabled=1,
        target_duration_sec=None,
    )
    validation_results = iter([
        {"valid": False, "stderr": "Visual group slide_001_el_002 in slide_001 describes multiple independent visual islands", "stdout": "", "returncode": 1},
        {"valid": True, "stderr": "", "stdout": "ok", "returncode": 0},
    ])
    repair_calls: list[dict] = []
    monkeypatch.setattr(service, "project_or_404", lambda _db, _id: project)
    monkeypatch.setattr(service, "read_project_article_source", lambda _project: {"title": "测试主题", "summary": ""})
    monkeypatch.setattr(service, "read_project_pipeline_profile", lambda _project: {})
    monkeypatch.setattr(service, "write_project_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "handle_step_navigation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service.invalidation_service, "storyboard_contract_changed", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "validate_visual_contract_file", lambda *_args, **_kwargs: next(validation_results))

    def fake_repair(_project, _script_plan, **kwargs):
        repair_calls.append(kwargs)
        return {"success": True, "visual_plan": repaired_plan}

    monkeypatch.setattr(service, "_execute_step2_visual_plan", fake_repair)
    result = service.compose_step2_visual_contract("project-reveal", object())

    assert result["success"] is True
    assert len(repair_calls) == 1
    assert "multiple independent visual islands" in repair_calls[0]["repair_validation_error"]
    assert result["contract"]["slides"][0]["visual_groups"][1]["reveal_mode"] == "sequential"


def test_project_mask_setting_owns_reveal_mode() -> None:
    import storyboard_service as service

    plan = {"slides": [{"visual_elements": [{"reveal_mode": "sequential"}, {"reveal_mode": "together"}]}]}
    without_mask = service._apply_project_reveal_mode(
        json.loads(json.dumps(plan)), SimpleNamespace(mask_enabled=0)
    )
    with_mask = service._apply_project_reveal_mode(
        json.loads(json.dumps(plan)), SimpleNamespace(mask_enabled=1)
    )
    assert {item["reveal_mode"] for item in without_mask["slides"][0]["visual_elements"]} == {"together"}
    assert {item["reveal_mode"] for item in with_mask["slides"][0]["visual_elements"]} == {"sequential"}


def test_visual_retry_names_missing_body_instead_of_missing_slide(monkeypatch, tmp_path: Path) -> None:
    import server  # Configure service dependencies under the isolated test runtime.
    import storyboard_service as service

    del server
    prompts = []
    responses = iter([
        {"slides": [{"slide_id": "slide_001", "visual_elements": [
            {"role": "title", "visual_type": "text", "visual_description": "三个阶段", "narration": SCRIPT_PLAN["slides"][0]["narration"]},
        ]}]},
        {"slides": [{"slide_id": "slide_001", "visual_elements": [
            {"role": "title", "visual_type": "text", "visual_description": "三个阶段", "narration": "先看三个阶段。"},
            {"role": "body", "visual_type": "picture", "visual_description": "三个阶段并排展示", "narration": "它们在这一段说明中同时展示。"},
        ]}]},
    ])
    monkeypatch.setattr(service, "read_step2_prompts_for_project", lambda *_args, **_kwargs: {
        "visual_system": "test", "visual_output_example": "{}",
    })
    monkeypatch.setattr(service, "step2_visual_prompt_uses_legacy_contract", lambda _prompt: False)
    monkeypatch.setattr(service, "run_step2_json_llm", lambda **kwargs: (prompts.append(kwargs["user_prompt"]), next(responses))[1])
    monkeypatch.setattr(service, "step2_visual_plan_path", lambda _project: str(tmp_path / "visual.json"))
    monkeypatch.setattr(service, "write_project_log", lambda *_args, **_kwargs: None)

    result = service._execute_step2_visual_plan(
        SimpleNamespace(mask_enabled=1), SCRIPT_PLAN,
    )

    assert result["success"] is True
    assert len(prompts) == 2
    assert "slide_001 至少需要一个 body 视觉元素" in prompts[1]
    assert "role 为 body" in prompts[1]
