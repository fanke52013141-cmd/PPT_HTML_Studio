"""Deterministic capacity candidate bounds and strategy contract."""
import copy
import json

import pytest

import html_capacity_repair as capacity
import html_capacity_repair as repair_module
from html_repair_orchestration import CAPACITY_INSTRUCTION, OVERLAP_INSTRUCTION, generate_repair
from html_repair_models import RepairGenerateRequest
from scripts.benchmark_capacity_repair import diagnostics, run, scene_and_layout


def test_size_and_font_candidates_stay_bounded_and_readable():
    scene, layout, catalog = scene_and_layout()
    scope = ["headline", "card-1"]
    for diagnostic in diagnostics().values():
        candidates = capacity.capacity_candidates(scene, layout, diagnostic, catalog, scope)
        assert candidates
        for operations in candidates:
            for operation in operations:
                assert operation["targetId"] in scope
                assert operation["kind"] in ("set_presentation", "set_text_style")
                if operation["kind"] == "set_text_style":
                    assert operation["values"]["fontSizePx"] >= capacity.MIN_READABLE_PX
                else:
                    values = operation["values"]
                    assert set(values) <= {"width", "height", "offsetX", "offsetY"}
                    if "width" in values:
                        assert 20 <= values["width"] <= 1600
                    if "height" in values:
                        assert 20 <= values["height"] <= 800
        assert candidates == capacity.capacity_candidates(scene, layout, diagnostic, catalog, scope)


def test_candidates_do_not_touch_text_identity_or_unscoped_targets():
    scene, layout, catalog = scene_and_layout()
    original = copy.deepcopy(scene)
    diagnostic = diagnostics()["box_case"]
    candidates = capacity.capacity_candidates(scene, layout, diagnostic, catalog, ["card-1"])
    assert all(operations[0]["targetId"] == "card-1" for operations in candidates)
    assert capacity.capacity_candidates(scene, layout, diagnostic, catalog, ["headline"]) == []
    assert scene == original


def test_benchmark_reports_candidates_without_model_calls():
    result = run()
    assert result["candidates_total"] > 0
    assert result["model_calls"] == result["provider_calls"] == result["author_writes"] == 0
    font_case = next(case for case in result["cases"] if case["case"] == "font_case")
    assert "set_text_style" in font_case["kinds"]
    assert font_case["font_min"] >= capacity.MIN_READABLE_PX
    box_case = next(case for case in result["cases"] if case["case"] == "box_case")
    assert "set_presentation" in box_case["kinds"] and box_case["size_candidates"] > 0
    baseline = run(baseline=True)
    assert baseline["candidates_total"] == 0


def test_capacity_first_requires_its_fixed_instruction(tmp_path):
    request = {"expected_revision": 0, "scope": ["headline"], "strategy": "capacity_first",
               "instruction": OVERLAP_INSTRUCTION}
    with pytest.raises(Exception) as caught:
        generate_repair(tmp_path, "slide_001", request, lambda: pytest.fail("no model"))
    assert getattr(caught.value, "code", "") == "REPAIR_CAPACITY_GOAL"
    assert CAPACITY_INSTRUCTION != OVERLAP_INSTRUCTION
    model = RepairGenerateRequest.model_validate(
        {"expected_revision": 0, "scope": ["headline"], "strategy": "capacity_first",
         "instruction": CAPACITY_INSTRUCTION})
    assert model.strategy == "capacity_first"


def test_annotation_and_missing_targets_are_skipped():
    scene, layout, catalog = scene_and_layout()
    annotation = next(node for node in scene["nodes"] if node["type"] == "annotation")
    diagnostic = {"capacityIssues": [{"target": annotation["id"], "triggers": []},
                                     {"target": "missing", "triggers": []}]}
    assert capacity.capacity_candidates(scene, layout, diagnostic, catalog,
                                        [annotation["id"], "missing"]) == []
    assert repair_module.MAX_CANDIDATES >= 1
    assert json.dumps(diagnostics(), sort_keys=True)
