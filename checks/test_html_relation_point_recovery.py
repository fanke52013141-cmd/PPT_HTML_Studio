import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from html_relation_point_recovery import repair_relation_points
from html_storyboard_planning import normalize_html_scene_plan, load_template_catalog
from html_visual_review_service import HtmlReviewError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case(tmp_path):
    original = json.loads((ROOT / "checks/fixtures/course-structure-plans.json").read_text(encoding="utf-8"))[0]
    plan = normalize_html_scene_plan(original["plan"], load_template_catalog(ROOT), contract_slide=original["contract"])
    image = tmp_path / "original.png"
    Image.new("RGB", (64, 36), "white").save(image)
    changes = [{"objectId": obj["id"], "fromPoint": {"x": .5, "y": .5},
                "toPoint": {"x": .9, "y": .5}} for obj in plan["objects"] if obj["kind"] == "arrow"]
    return plan, original["contract"], image, changes


def invoke(case, tmp_path, response, **kwargs):
    plan, contract, image, _ = case
    def generator(**request):
        assert request["image_paths"] == [str(image)]
        assert request["request_timeout"] == 600
        return response
    return repair_relation_points(plan, image, "按原图修正向外端点", contract=contract,
                                  repo_root=ROOT, run_dir=tmp_path, generator=generator, **kwargs)


def test_only_point_coordinates_change_and_author_image_stay_untouched(case, tmp_path):
    plan, _, image, changes = case
    original, pixels = copy.deepcopy(plan), image.read_bytes()
    updated, evidence = invoke(case, tmp_path, {"changes": changes})
    restored = copy.deepcopy(updated)
    for slot, content in original["slots"].items():
        if content["kind"] == "arrow":
            for key in ("from", "to"):
                restored["slots"][slot][key]["point"] = content[key]["point"]
    assert restored == original and plan == original
    assert image.read_bytes() == pixels and evidence["approval"] == "not_recorded"
    assert not list(tmp_path.rglob("scene-*.json"))


@pytest.mark.parametrize("damage", ["extra", "id", "duplicate", "missing", "range", "nan", "rebind"])
def test_bad_repairs_reject_without_writing_plan_or_author(case, tmp_path, damage):
    changes = copy.deepcopy(case[3])
    response = {"changes": changes}
    if damage == "extra": response["scene"] = {}
    elif damage == "id": changes[0]["objectId"] = "invented"
    elif damage == "duplicate": changes[1] = copy.deepcopy(changes[0])
    elif damage == "missing": changes.pop()
    elif damage == "range": changes[0]["fromPoint"]["x"] = 1.1
    elif damage == "nan": changes[0]["fromPoint"]["x"] = float("nan")
    elif damage == "rebind": changes[0]["fromPoint"]["objectId"] = "other"
    with pytest.raises(HtmlReviewError, match="未通过验证"):
        invoke(case, tmp_path, response)
    assert not list(tmp_path.rglob("validated-plan.json"))
    assert not list(tmp_path.rglob("scene-*.json"))


def test_image_change_after_request_blocks_acceptance(case, tmp_path):
    plan, contract, image, changes = case
    def generator(**request):
        image.write_bytes(b"changed")
        return {"changes": changes}
    with pytest.raises(HtmlReviewError) as caught:
        repair_relation_points(plan, image, "修正", contract=contract, repo_root=ROOT,
                               run_dir=tmp_path, generator=generator)
    assert caught.value.code == "DESIGN_STALE"


def test_initial_request_contains_output_schema_without_repair_fallback(case, tmp_path):
    plan, contract, image, changes = case
    calls = []
    def generator(**request):
        calls.append(request)
        # schema_hint is only used by the shared adapter after JSON syntax failure.
        system = request["system_prompt"]
        schema = json.loads(system.split("\n输出Schema：", 1)[1])
        assert schema["required"] == ["changes"]
        assert schema["additionalProperties"] is False
        assert set(schema["$defs"]["PointChange"]["required"]) == {"objectId", "fromPoint", "toPoint"}
        assert request["reasoning_effort_override"] == "low"
        return {"changes": changes}
    repair_relation_points(plan, image, "修正", contract=contract, repo_root=ROOT,
                           run_dir=tmp_path, generator=generator)
    assert len(calls) == 1


def test_relation_keyed_response_is_not_silently_converted(case, tmp_path):
    response = {c["objectId"]: {"from": {"point": c["fromPoint"]},
                                "to": {"point": c["toPoint"]}} for c in case[3]}
    with pytest.raises(HtmlReviewError) as caught:
        invoke(case, tmp_path, response)
    assert caught.value.code == "RELATION_POINT_REPAIR_REJECTED"
    assert not list(tmp_path.rglob("validated-plan.json"))
