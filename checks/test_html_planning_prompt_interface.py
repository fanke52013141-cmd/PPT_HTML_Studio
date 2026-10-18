"""The schema hint and actual task must describe the same production interface."""
import json
from pathlib import Path

from html_visual_review_service import build_plan_generation_prompts, _registered_capabilities

ROOT = Path(__file__).resolve().parents[1]


def test_required_coverage_is_present_in_actual_output_hint():
    contract = {
        "slide_id": "s1",
        "narration_beats": [{"id": "b1", "spoken_text": "水向外界散热。"}],
        "visual_requirements": [{"id": "outward-heat", "kind": "relation", "minCount": 8}],
    }
    prompts = build_plan_generation_prompts(contract, _registered_capabilities(ROOT), plan_version="0.2.0")
    task = json.loads(prompts["user_prompt"])
    assert task["slide"]["visual_requirements"] == contract["visual_requirements"]
    assert "visual_coverage" in prompts["schema_hint"]
    assert "minCount" in prompts["schema_hint"]
    assert "自身box内" in prompts["system_prompt"]
    assert "box.x+box.width*point.x" in prompts["system_prompt"]


def test_legacy_plan_hint_does_not_require_new_coverage():
    contract = {"slide_id": "s1", "narration_beats": [{"id": "b1", "spoken_text": "观察水。"}]}
    prompts = build_plan_generation_prompts(contract, _registered_capabilities(ROOT), plan_version="0.1.0")
    assert "visual_coverage" not in prompts["schema_hint"]
