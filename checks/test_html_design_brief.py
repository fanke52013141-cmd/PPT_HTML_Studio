"""C02 (pure core): design brief, keyframe list, and freeze records.

The model-call side joins in the C04 service; here the brief, candidate,
keyframe, and freeze contracts are covered, including the AC06 boundary
(effects only from the registry) and the AC07 freeze record.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from html_design_brief import (
    DesignBriefError,
    build_design_brief,
    freeze_design,
    load_effect_registry,
    normalize_design_candidate,
    normalize_keyframes,
    required_keyframes,
)
from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def catalog():
    return load_template_catalog(REPO_ROOT)


@pytest.fixture(scope="module")
def effects():
    return load_effect_registry(REPO_ROOT)


@pytest.fixture(scope="module")
def explain_plan(catalog):
    """Reuse the C01 test plan (explanation-cards, one image asset)."""
    sys_path = Path(__file__).parent
    import sys

    sys.path.insert(0, str(sys_path))
    from test_html_storyboard_planning import CONTRACT_SLIDE, valid_plan

    plan = valid_plan()
    return normalize_html_scene_plan(
        plan, catalog, contract_slide={
            "slide_id": plan["slide_id"],
            "narration_beats": CONTRACT_SLIDE["narration_beats"],
        }
    )


def test_effect_registry_loads_from_engine_source(effects) -> None:
    assert "leader-line-draw" in effects["effects"]
    assert effects["effects"]["leader-line-draw"]["backend"] == "SVG"
    assert len(effects["sha256"]) == 64


def test_brief_only_references_registered_effects(explain_plan, effects) -> None:
    brief = build_design_brief(
        explain_plan,
        theme="soft-science",
        asset_budget=1,
        effect_registry=effects,
    )
    assert brief["templateRef"]["id"] == "explanation-cards-v1"
    assert all(e["backend"] in {"CSS", "SVG", "Canvas2D"} for e in brief["effects"])
    assert len(brief["asset_needs"]) == 1
    assert brief["asset_needs"][0]["need"]
    assert len(brief["sha256"]) == 64


def test_budget_is_enforced(explain_plan, effects) -> None:
    with pytest.raises(DesignBriefError) as zero_budget:
        build_design_brief(
            explain_plan, theme="soft-science", asset_budget=0,
            effect_registry=effects,
        )
    assert zero_budget.value.code == "BRIEF_BUDGET_EXCEEDED"
    with pytest.raises(DesignBriefError) as invalid:
        build_design_brief(
            explain_plan, theme="soft-science", asset_budget=3,
            effect_registry=effects,
        )
    assert invalid.value.code == "BRIEF_BUDGET_INVALID"


def test_candidate_separates_code_from_image_parts(explain_plan, effects) -> None:
    brief = build_design_brief(
        explain_plan, theme="soft-science", asset_budget=1,
        effect_registry=effects,
    )
    candidate = normalize_design_candidate({
        "name": "冷杯浅色卡组",
        "parts": [
            {"backend": "CSS", "description": "三张知识卡，渐变图标气泡"},
            {"backend": "SVG", "description": "圈注与引线，随讲解描绘"},
            {"backend": "image_asset", "description": "冷杯表面水滴插画"},
        ],
        "keyframes": [{"stage": "static", "shows": "终帧完整讲解状态"}],
        "notes": "插画沿用已认可资产",
    })
    assert [p["backend"] for p in candidate["parts"]] == [
        "CSS", "SVG", "image_asset",
    ]
    assert len(candidate["sha256"]) == 64
    # Unknown backends are rejected before any generation happens.
    with pytest.raises(DesignBriefError) as backend:
        normalize_design_candidate({
            "name": "x",
            "parts": [{"backend": "WebGL", "description": "3D 效果"}],
        })
    assert backend.value.code == "CANDIDATE_BACKEND_INVALID"
    with pytest.raises(DesignBriefError) as stage:
        normalize_keyframes([{"stage": "mid", "shows": "x"}])
    assert stage.value.code == "KEYFRAME_STAGE_INVALID"
    # The brief stays unchanged by candidate work.
    assert len(brief["sha256"]) == 64


def test_process_keyframes_cover_start_change_end(catalog) -> None:
    sys_path = Path(__file__).parent
    import sys

    sys.path.insert(0, str(sys_path))
    from test_html_storyboard_planning import valid_plan

    plan = valid_plan()
    plan["objects"].append(
        {"id": "vapor-fragment", "slot": "intro", "kind": "text",
         "exit": True, "transitional": True}
    )
    normalized = normalize_html_scene_plan(plan, catalog)
    keyframes = required_keyframes(normalized)
    assert [k["stage"] for k in keyframes] == ["start", "relation_change", "end"]
    # Static scene: single final-frame reference suffices.
    assert [k["stage"] for k in required_keyframes(
        normalize_html_scene_plan(valid_plan(), catalog)
    )] == ["static"]


def test_freeze_requires_diff_notes_and_hashes(explain_plan, effects) -> None:
    brief = build_design_brief(
        explain_plan, theme="soft-science", asset_budget=1,
        effect_registry=effects,
    )
    candidate = normalize_design_candidate({
        "name": "冷杯浅色卡组",
        "parts": [{"backend": "CSS", "description": "三张知识卡"}],
        "keyframes": [{"stage": "static", "shows": "终帧"}],
    })
    with pytest.raises(DesignBriefError) as missing_notes:
        freeze_design(brief, candidate, diff_notes="  ")
    assert missing_notes.value.code == "FREEZE_DIFF_MISSING"
    record = freeze_design(
        brief,
        candidate,
        diff_notes="知识卡标题行高按实际测量放宽；插画复用已认可资产，非像素级复刻参考图。",
    )
    assert record["brief_sha256"] == brief["sha256"]
    assert record["candidate_sha256"] == candidate["sha256"]
    assert len(record["sha256"]) == 64
    assert "像素级" in record["diff_notes"]
