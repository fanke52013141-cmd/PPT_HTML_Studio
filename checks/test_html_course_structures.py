"""Offline authored fixtures exercise original normalize/A02/compile/render boundaries."""

import copy
import json
from pathlib import Path
import subprocess

import pytest

from html_storyboard_planning import (
    normalize_html_scene_plan,
    load_template_catalog,
    HtmlScenePlanError,
)
from html_semantic_design import build_semantic_design
from html_production_service import compile_plan

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "checks/fixtures/course-structure-plans.json").read_text(encoding="utf-8")
)


def compile_cases(directory):
    catalog = load_template_catalog(ROOT)
    for case in CASES:
        plan = normalize_html_scene_plan(
            case["plan"], catalog, contract_slide=case["contract"]
        )
        build_semantic_design(plan)
        scene, binding = compile_plan(plan, case["contract"], catalog)
        assert len(scene["motion"]) == len(plan["objects"])
        assert len(binding["actions"]) == len(scene["motion"])
        (directory / (scene["id"] + ".json")).write_text(
            json.dumps(scene, ensure_ascii=False), encoding="utf-8"
        )


@pytest.mark.parametrize("backend", ["software", "default"])
def test_four_page_shared_browser_and_deterministic_geometry(tmp_path, backend):
    compile_cases(tmp_path)
    result = subprocess.run(
        ["node", "checks/test_html_course_structures.cjs", str(tmp_path), backend],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "browser-report.json").read_text())
    assert len(report["results"]) == 16 and report["structurePassed"]
    if backend == "software":
        assert report["pixelExact"], (
            "Software capture must be strictly pixel deterministic"
        )
    else:
        assert all(r["pixelExact"] for r in report["results"] if r["width"] == 1600)
    # Fractional-width DPR2 pixel equality is reported independently, not promoted to acceptance.


@pytest.mark.parametrize(
    "damage",
    [
        "endpoint",
        "out_of_range",
        "missing_requirement",
        "wrong_type",
        "missing_stage",
        "false_plateau",
        "unordered_x",
        "nan",
        "range",
    ],
)
def test_missing_or_invalid_course_structure_is_rejected_before_design(damage):
    index = (
        2
        if damage in ("false_plateau", "unordered_x", "nan", "range")
        else 3
        if damage == "missing_stage"
        else 0
    )
    case = copy.deepcopy(CASES[index])
    plan = case["plan"]
    slots = plan["slots"]
    if damage == "endpoint":
        del slots["relation-1"]["to"]
    elif damage == "out_of_range":
        slots["relation-1"]["from"]["point"]["x"] = 2
    elif damage == "missing_requirement":
        plan["visual_coverage"].clear()
    elif damage == "wrong_type":
        plan["visual_coverage"]["outward-heat"][0] = "header"
    elif damage == "missing_stage":
        plan["visual_coverage"]["stages"].pop()
    elif damage == "false_plateau":
        slots["chart"]["points"][2]["y"] = 0.8
    elif damage == "unordered_x":
        slots["chart"]["points"][2]["x"] = 0.1
    elif damage == "nan":
        slots["chart"]["min"] = float("nan")
    elif damage == "range":
        slots["chart"]["max"] = slots["chart"]["min"]
    with pytest.raises(HtmlScenePlanError):
        normalize_html_scene_plan(
            plan, load_template_catalog(ROOT), contract_slide=case["contract"]
        )


def test_new_structure_guard_does_not_claim_natural_language_understanding():
    case = copy.deepcopy(CASES[0])
    case["contract"].pop("visual_requirements")
    case["plan"].pop("visual_coverage")
    plan = normalize_html_scene_plan(
        case["plan"], load_template_catalog(ROOT), contract_slide=case["contract"]
    )
    assert "visual_coverage" not in plan


@pytest.mark.parametrize(
    "damage",
    ["head_type", "line_style", "endpoint_type", "presentation", "endpoint_recursive"],
)
def test_relations_reject_invalid_schema_before_design(damage):
    case = copy.deepcopy(CASES[0])
    r = case["plan"]["slots"]["relation-1"]
    if damage == "head_type":
        r["head"] = "yes"
    elif damage == "line_style":
        r["lineStyle"] = "arbitrary-css"
    elif damage == "endpoint_type":
        r["from"] = None
    elif damage == "presentation":
        r["presentation"] = {"offsetX": 2}
    else:
        r["from"]["objectId"] = "relation-2"
    with pytest.raises(HtmlScenePlanError):
        normalize_html_scene_plan(
            case["plan"], load_template_catalog(ROOT), contract_slide=case["contract"]
        )


def test_explicit_relation_cannot_bypass_preflight_in_a02():
    case = copy.deepcopy(CASES[0])
    p = normalize_html_scene_plan(
        case["plan"], load_template_catalog(ROOT), contract_slide=case["contract"]
    )
    p["slots"]["relation-1"].pop("from")
    p["slots"]["relation-1"].pop("to")
    from html_semantic_plan import SemanticPlanError

    with pytest.raises(SemanticPlanError):
        build_semantic_design(p)


@pytest.mark.parametrize("key", ["x", "y"])
def test_nonfinite_chart_point_is_rejected(key):
    case = copy.deepcopy(CASES[2])
    case["plan"]["slots"]["chart"]["points"][0][key] = float("nan")
    with pytest.raises(HtmlScenePlanError):
        normalize_html_scene_plan(
            case["plan"], load_template_catalog(ROOT), contract_slide=case["contract"]
        )


def test_chart_review_requires_text_data_and_semantic_coverage():
    from html_design_agent import review_checklist, component_context

    case = CASES[2]
    plan = normalize_html_scene_plan(
        case["plan"], load_template_catalog(ROOT), contract_slide=case["contract"]
    )
    scene, _ = compile_plan(plan, case["contract"], load_template_catalog(ROOT))
    assert {
        r["dimension"] for r in review_checklist(scene) if r["targetId"] == "chart"
    } == {"geometry", "content", "typography", "structure", "semantic_relation"}
    context = component_context(scene, ROOT)
    assert context["capabilities"]["relation-1"]["editable"] == {}
    assert context["capabilities"]["relation-1"]["variants"] == []


def test_relation_action_outside_current_channel_is_rejected_before_design():
    case = copy.deepcopy(CASES[0])
    beat = case["plan"]["beats"][-1]
    beat["actions"].append(
        {
            "objectId": "relation-1",
            "actionId": "relation-highlight",
            "type": "emphasize",
        }
    )
    with pytest.raises(HtmlScenePlanError, match="relation-1"):
        normalize_html_scene_plan(
            case["plan"], load_template_catalog(ROOT), contract_slide=case["contract"]
        )
