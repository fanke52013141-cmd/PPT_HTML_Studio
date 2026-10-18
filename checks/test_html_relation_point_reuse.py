import copy
import json

import pytest
from pydantic import ValidationError

from checks.test_html_e_production import case as case
from html_production_models import HtmlProduceRequest
from html_production_service import produce_scene
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from html_design_candidates import candidate_directory


@pytest.mark.parametrize("options", [
    {"repair_relation_points": "修正"},
    {"reuse_design_candidate_key": "a" * 64, "repair_relation_points": " "},
    {"reuse_design_candidate_key": "a" * 64, "repair_relation_points": "修正", "design_candidate_key": "b" * 64},
])
def test_relation_repair_requires_explicit_reuse_and_rejects_mixed_work(options):
    with pytest.raises(ValidationError):
        HtmlProduceRequest.model_validate(options)


def setup_design(case):
    root = case.deps.repo_root
    original = json.loads((root / "checks/fixtures/course-structure-plans.json").read_text(encoding="utf-8"))[0]
    case.contract = original["contract"]
    deps = HtmlReviewDependencies(root, lambda **kw: copy.deepcopy(original["plan"]))
    result = produce_scene(case.contract, run_dir=case.run, deps=deps, provider=case.provider,
                           options={"plan_version": "0.2.0"})
    key = result["design"]["key"]
    directory = candidate_directory(case.run, case.contract["slide_id"], key)
    record = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
    return key, directory, record


def test_original_production_path_repairs_only_points_and_reuses_image(case):
    key, directory, original = setup_design(case)
    before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    calls = []
    def generator(**kw):
        calls.append(kw)
        payload = json.loads(kw["user_prompt"])
        return {"changes": [{"objectId": id, "fromPoint": {"x": .5, "y": .5},
                             "toPoint": {"x": .9, "y": .5}} for id in payload["relations"]]}
    result = produce_scene(case.contract, run_dir=case.run,
                           deps=HtmlReviewDependencies(case.deps.repo_root, generator),
                           options={"plan_version": "0.2.0", "reuse_design_candidate_key": key,
                                    "repair_relation_points": "按原图修复坐标"})
    assert len(calls) == 1 and len(case.requests) == 1
    assert result["relation_points_repaired"] and result["reference_reused"]
    assert result["design"]["approval_status"] == "not_recorded" and not result["saved"]["changed"]
    new_dir = candidate_directory(case.run, case.contract["slide_id"], result["design"]["key"])
    new = json.loads((new_dir / "candidate.json").read_text(encoding="utf-8"))
    assert new["plan"]["beats"] == original["plan"]["beats"]
    assert new["plan"]["objects"] == original["plan"]["objects"]
    assert (new_dir / "design-reference.png").read_bytes() == before["design-reference.png"]
    assert all((directory / name).read_bytes() == data for name, data in before.items())
    assert not list(case.run.rglob("scene-*.json"))


def test_manual_editor_overlay_blocks_model_point_repair(case):
    key, _, _ = setup_design(case)
    from html_scene_editing import edit_path
    path = edit_path(case.run, case.contract["slide_id"])
    path.write_text("{}")
    def forbidden(**kw):
        pytest.fail("Manual overlay must block before model request")
    with pytest.raises(HtmlReviewError) as caught:
        produce_scene(case.contract, run_dir=case.run,
                       deps=HtmlReviewDependencies(case.deps.repo_root, forbidden),
                       options={"plan_version": "0.2.0", "reuse_design_candidate_key": key,
                                "repair_relation_points": "按原图修复"})
    assert caught.value.code == "MANUAL_EDIT_CONFLICT"


def test_mcp_forwards_declared_production_fields_without_dropping_reuse_or_repair():
    from mcp_server.tools import _dispatch
    captured = []
    class Client:
        def produce_html_scene(self, project_id, slide_id, **options):
            captured.append((project_id, slide_id, options))
            return {}
    body = {"plan_version": "0.2.0", "reuse_design_candidate_key": "a" * 64,
            "repair_relation_points": "修复坐标"}
    _dispatch("html_review.produce", {"project_id": "p", "slide_id": "s", **body}, Client())
    assert captured == [("p", "s", body)]
