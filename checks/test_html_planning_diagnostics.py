"""Provider-free regressions for natural planning failure classes and retry inputs."""
import copy
import json
from pathlib import Path

import pytest

from html_storyboard_planning import (
    HtmlScenePlanError, load_template_catalog, normalize_html_scene_plan,
)
from html_visual_review_service import generate_scene_plan, HtmlReviewError

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "checks/fixtures/course-structure-plans.json").read_text(encoding="utf-8"))


def stage_case():
    case = copy.deepcopy(CASES[3])
    plan = case["plan"]
    for obj in plan["objects"]:
        if obj["id"] == "stage-1":
            obj["id"] = "obj-stage-1"
    for content in plan["slots"].values():
        for key in ("from", "to"):
            if content.get(key, {}).get("objectId") == "stage-1":
                content[key]["objectId"] = "obj-stage-1"
    for beat in plan["beats"]:
        for key in ("targets", "actions", "expectedState"):
            for item in beat[key]:
                if item["objectId"] == "stage-1":
                    item["objectId"] = "obj-stage-1"
    for ids in plan["visual_coverage"].values():
        ids[:] = ["obj-stage-1" if i == "stage-1" else i for i in ids]
    return case


def normalize(case):
    return normalize_html_scene_plan(case["plan"], load_template_catalog(ROOT), contract_slide=case["contract"])


@pytest.mark.parametrize("actual", ["stage-1", "missing", "relation-2", "annotation"])
def test_endpoint_diagnostic_identifies_slot_and_legal_objects_without_rewriting(actual):
    case = stage_case()
    case["plan"]["slots"]["relation-1"]["from"]["objectId"] = actual
    original = copy.deepcopy(case)
    with pytest.raises(HtmlScenePlanError) as caught:
        normalize(case)
    assert case == original
    assert caught.value.code == "PLAN_RELATION_ENDPOINT"
    facts = json.loads(str(caught.value))
    assert facts["path"] == ["slots", "relation-1", "from", "objectId"]
    assert facts["actual"] == actual
    assert facts["matching_slot_object_ids"] == (["obj-stage-1"] if actual == "stage-1" else [])
    assert "obj-stage-1" in facts["allowed_object_ids"]
    assert not set(facts["allowed_object_ids"]) & {"stage-1", "relation-2", "annotation"}


@pytest.mark.parametrize("manifest_present", [False, True])
def test_no_authored_requirements_allows_omitted_or_empty_coverage_only(manifest_present):
    case = stage_case()
    case["contract"].pop("visual_requirements")
    if manifest_present:
        case["contract"]["visual_requirements"] = []
    case["plan"].pop("visual_coverage")
    normalize(case)
    case["plan"]["visual_coverage"] = {}
    normalize(case)
    case["plan"]["visual_coverage"] = {"visual-group-1": ["obj-stage-1"]}
    with pytest.raises(HtmlScenePlanError) as caught:
        normalize(case)
    assert caught.value.code == "PLAN_VISUAL_COVERAGE"
    facts = json.loads(str(caught.value))
    assert facts["required_ids"] == facts["missing_ids"] == []
    assert facts["unexpected_ids"] == ["visual-group-1"]


def test_coverage_feedback_separates_missing_extra_and_wrong_kind():
    case = stage_case()
    case["plan"]["visual_coverage"]["invented"] = case["plan"]["visual_coverage"].pop("stages")
    with pytest.raises(HtmlScenePlanError) as caught:
        normalize(case)
    facts = json.loads(str(caught.value))
    assert facts["required_ids"] == ["heat", "sequence", "stages"]
    assert facts["missing_ids"] == ["stages"] and facts["unexpected_ids"] == ["invented"]
    case = stage_case()
    case["plan"]["visual_coverage"]["stages"][0] = "header"
    with pytest.raises(HtmlScenePlanError) as caught:
        normalize(case)
    facts = json.loads(str(caught.value))
    assert facts["reason"] == "coverage_object_kind_mismatch"
    assert facts["allowed_object_ids"] == ["obj-stage-1", "stage-2", "stage-3"]


@pytest.mark.parametrize("damage", ["endpoint", "coverage"])
def test_exact_diagnostic_reaches_bounded_retry_and_audit(tmp_path, damage):
    case = stage_case()
    if damage == "coverage":
        case["contract"].pop("visual_requirements")
        case["plan"].pop("visual_coverage")
    good = case["plan"]
    bad = copy.deepcopy(good)
    if damage == "endpoint":
        bad["slots"]["relation-1"]["from"]["objectId"] = "stage-1"
    else:
        bad["visual_coverage"] = {"visual-group-1": ["obj-stage-1"]}
    original = copy.deepcopy(bad)
    requests = []

    def provider(**request):
        requests.append(request)
        return bad if len(requests) == 1 else good

    result = generate_scene_plan(case["contract"], run_dir=tmp_path, repo_root=ROOT,
                                 json_generator=provider, plan_version="0.2.0")
    assert bad == original and len(requests) == 2
    assert result["objects"] == normalize(case)["objects"]
    assert [b["actions"] for b in result["beats"]] == [b["actions"] for b in good["beats"]]
    retry = json.loads(requests[1]["user_prompt"])
    assert retry["invalid_plan"] == bad
    facts = json.loads(retry["diagnostic"]["message"])
    assert facts["path"] == (["visual_coverage"] if damage == "coverage" else ["slots", "relation-1", "from", "objectId"])
    for request in requests:
        assert "html-semantic-plan/0.3.6" in request["system_prompt"]
        assert "objects[].id是对象身份" in request["system_prompt"]
        assert "visual_requirements缺省或为空" in request["schema_hint"]
        assert request["request_timeout"] == 1800 and request["stream_output"]
        assert request["reasoning_effort_override"] == "low"
    sid = case["contract"]["slide_id"]
    record = json.loads((tmp_path / f"planning/html_visual/records/plan-{sid}.json").read_text(encoding="utf-8"))
    assert [a["accepted"] for a in record["attempts"]] == [False, True]
    assert record["attempts"][0]["diagnostic"] == retry["diagnostic"]["message"]


def test_invalid_coverage_twice_still_rejected_without_automatic_cleanup(tmp_path):
    case = stage_case()
    case["contract"]["visual_requirements"] = []
    requests = []

    def provider(**request):
        requests.append(request)
        return copy.deepcopy(case["plan"])

    with pytest.raises(HtmlReviewError) as caught:
        generate_scene_plan(case["contract"], run_dir=tmp_path, repo_root=ROOT,
                            json_generator=provider, plan_version="0.2.0")
    assert caught.value.code == "PLAN_GENERATION_REJECTED" and len(requests) == 2


def test_unknown_planning_transport_is_not_retried(tmp_path):
    requests = []

    def provider(**request):
        requests.append(request)
        raise TimeoutError("unknown provider outcome")

    with pytest.raises(TimeoutError):
        generate_scene_plan(stage_case()["contract"], run_dir=tmp_path, repo_root=ROOT,
                            json_generator=provider, plan_version="0.2.0")
    assert len(requests) == 1
