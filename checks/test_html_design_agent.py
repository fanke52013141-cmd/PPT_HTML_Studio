"""Actual design Agent boundaries, allocation evidence and bounded visual feedback."""
import copy
import json
from pathlib import Path

import pytest

from checks.test_html_design_reconstruction import case as case
from checks.html_design_agent_fixture import response_for
from html_design_agent import component_context, validate_understanding, validate_fidelity, apply_allocations, fidelity_routes
from html_design_reconstruction import reconstruct_design
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from html_runtime_skills import load_runtime_skill, runtime_source_files

ROOT = Path(__file__).resolve().parents[1]


def ready(context):
    return response_for({"artifact_prefix":"design_understanding-case","user_prompt":json.dumps(context)})


def test_three_real_registered_skills_and_source_closure():
    for stage in ("design_understanding","design_reconstruction","design_fidelity_review"):
        selected = load_runtime_skill(ROOT,stage=stage,mode="runtime_skill")
        assert selected.fragment and selected.identity["stage"] == stage
        selected.verify()
    files = runtime_source_files(ROOT)
    assert len({f["path"] for f in files}) == len(files)
    assert any("design-fidelity-review" in f["path"] for f in files)


def test_review_receives_authority_and_tools_without_previous_agent_verdict(case):
    from html_design_agent import review_fidelity
    run, scene, _, reference, _ = case
    calls = []
    def generator(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        calls.append(payload)
        assert payload["production_policy"]["palette"] == "grayscale"
        assert "understanding" not in payload
        for item in payload["capabilities"].values():
            if "set_text_style" in item["editable"]:
                assert item["editable"]["set_text_style"]["scope"] == "whole_part_only"
        return {"status": "pass", "issues": []}
    result = review_fidelity(scene, reference, reference, {}, {"result": "not independent evidence"},
        folder=run/"fidelity", run_dir=run, deps=HtmlReviewDependencies(ROOT, generator))
    assert len(calls) == 1 and result["human_approval"] == "pending"


@pytest.mark.parametrize("damage",["missing","duplicate","rasterize","variant","icon"])
def test_allocation_rejects_missing_duplicate_rasterized_and_unregistered_objects(case,damage):
    _,scene,_,_,_=case
    context=component_context(scene,ROOT);result=ready(context)
    if damage=="missing":result["objects"].pop()
    if damage=="duplicate":result["objects"][-1]=copy.deepcopy(result["objects"][0])
    if damage=="rasterize":result["objects"][0].update(owner="image",assetMode="generate")
    if damage=="variant":result["objects"][0]["variant"]="text-card-soft"
    if damage=="icon":result["objects"][0]["icon"]="speech"
    with pytest.raises(ValueError):validate_understanding(result,context)


def test_generated_and_reused_images_require_exact_authoritative_owner():
    scene={"version":"0.6.0","nodes":[{"id":"subject","slot":"image","type":"image","assetRef":{"id":"planned","version":"0.1.0"}}]}
    for mode in ("generate","reuse"):
        context=component_context(scene,ROOT,asset_modes={"subject":mode});result=ready(context)
        assert validate_understanding(result,context)["objects"][0]["assetMode"]==mode
        result["objects"][0]["assetMode"]="reuse" if mode=="generate" else "generate"
        with pytest.raises(ValueError):validate_understanding(result,context)


def test_svg_issue_cannot_route_code_to_bitmap_generation():
    result={"issues":[{"targetId":"summary","category":"asset","requirement":"asset_identity"},{"targetId":"subject","category":"asset","requirement":"asset_identity"}]}
    scene={"nodes":[{"id":"summary","type":"summary"},{"id":"subject","type":"image"}]}
    routed=fidelity_routes(result,scene,{"summary":{},"subject":{}})
    assert [i["route"] for i in routed]==["capabilities","assets"]


def test_unsupported_allocation_routes_code_back_to_capabilities_without_more_calls(case):
    from html_design_agent import understand_design
    run, scene, _, reference, _ = case
    before = copy.deepcopy(scene)
    calls, events = [], []
    target = next(n["id"] for n in scene["nodes"] if n["type"] != "image")
    def generator(**kw):
        calls.append(kw)
        return {"status": "unsupported", "objects": [], "issues": [
            {"targetId": target, "route": "assets", "requirement": "unsupported_presentation", "evidence": "fixture code-controlled component unavailable"}]}
    with pytest.raises(HtmlReviewError) as caught:
        understand_design(scene, reference, run_dir=run, deps=HtmlReviewDependencies(ROOT, generator), progress=events.append)
    assert caught.value.code == "DESIGN_ALLOCATION_UNSUPPORTED" and len(calls) == 1
    assert events[-1]["next_action"]["routes"] == ["capabilities"]
    assert events[-1]["next_action"]["automatic_retry"] is False and scene == before
    record = json.loads(next((run / "planning/html_visual/candidates").glob("*/design-understanding/*/result.json")).read_text(encoding="utf-8"))
    assert record["result"]["issues"][0]["route"] == "assets"
    assert record["routed_issues"][0]["route"] == "capabilities"


def test_component_choices_are_executed_before_layout_without_changing_text_or_actions(case):
    run,scene,binding,_,contract=case
    decision=ready(component_context(scene,ROOT))
    decision["objects"][0].update(variant="header-badge")
    decision["objects"][1].update(variant="text-card-outline",icon="speech")
    changed,operations=apply_allocations(scene,binding,{"result":decision},run_dir=run,beats=contract["narration_beats"])
    assert len(operations)==2 and changed["version"]=="0.7.0"
    assert changed["nodes"][0]["presentation"]["variant"]=="header-badge"
    assert changed["nodes"][1]["presentation"]["icon"]=="speech"
    assert changed["motion"]==scene["motion"]
    assert [{k:v for k,v in n.items() if k!="presentation"} for n in changed["nodes"]]==scene["nodes"]


@pytest.mark.parametrize("response",[
    {"status":"pass","issues":[{"targetId":"header","category":"layout","requirement":"geometry","severity":"major","evidence":"visible difference","suggestion":"adjust spacing"}]},
    {"status":"changes_requested","issues":[]},
    {"status":"pass","issues":[],"approval":True},
    {"status":"changes_requested","issues":[{"targetId":"invented","category":"layout","requirement":"geometry","severity":"major","evidence":"difference","suggestion":"adjust"}]},
])
def test_review_never_accepts_contradictions_approval_or_unknown_targets(case,response):
    with pytest.raises(ValueError):validate_fidelity(response,case[1])


def test_visual_feedback_is_consumed_by_next_real_static_decision(case):
    run,scene,binding,reference,contract=case;calls=[];reviews=[]
    def generator(**kw):
        calls.append(kw)
        assert kw["request_timeout"]==600 and "thinking" not in kw
        fixture=response_for(kw)
        if kw["artifact_prefix"].startswith("design_fidelity_review-"):
            assert len(kw["image_paths"])==2 and all(Path(p).is_file() for p in kw["image_paths"])
            reviews.append(kw)
            if len(reviews)==1:
                return {"status":"changes_requested","issues":[{"targetId":"header","category":"layout","requirement":"geometry","severity":"minor","evidence":"header sits above reference baseline","suggestion":"move down"}]}
            return fixture
        if fixture is not None:return fixture
        payload=json.loads(kw["user_prompt"])
        if len(reviews)==0:return {"status":"unchanged","message":"fixture initial"}
        assert payload["diagnostic"]["issues"][0]["targetId"]=="header"
        return {"status":"candidate","operations":[{"targetId":"header","kind":"set_presentation","values":{"offsetY":8}}]}
    result=reconstruct_design(scene,binding,reference,run_dir=run,deps=HtmlReviewDependencies(ROOT,generator),beats=contract["narration_beats"])
    assert len(calls)==5 and len(reviews)==2
    assert result["summary"]["fidelity_review"]["human_approval"]=="pending"
    assert result["scene"]["motion"]==scene["motion"]


def test_asset_problem_stops_static_loop_and_preserves_author(case):
    run,scene,binding,reference,contract=case;before=copy.deepcopy(scene);calls=[];events=[]
    def generator(**kw):
        calls.append(kw)
        if kw["artifact_prefix"].startswith("design_fidelity_review-"):
            return {"status":"changes_requested","issues":[{"targetId":"header","category":"capability","requirement":"unsupported_presentation","severity":"major","evidence":"unsupported header shape","suggestion":"add registered variant"}]}
        return response_for(kw) or {"status":"unchanged","message":"fixture"}
    with pytest.raises(HtmlReviewError) as caught:
        reconstruct_design(scene,binding,reference,run_dir=run,deps=HtmlReviewDependencies(ROOT,generator),beats=contract["narration_beats"],progress=events.append)
    assert caught.value.code=="DESIGN_REVIEW_ROUTED" and len(calls)==3 and scene==before
    assert not (run/"planning/html_visual/scene-token-03.json").exists()
    assert events[-1]["next_action"]["routes"] == ["capabilities"]
    assert events[-1]["next_action"]["reason"] == "upstream_revision_required"


def test_reconstruction_discovers_missing_semantic_labels_and_stops_at_planning(case):
    run,scene,binding,reference,contract=case
    calls, events = [], []
    def generator(**kw):
        fixture = response_for(kw)
        if fixture is not None:
            return fixture
        calls.append(kw)
        return {"status": "unsupported", "message": "missing semantic label objects", "issues": [
            {"targetId": scene["nodes"][0]["id"], "route": "assets", "requirement": "semantic_text",
             "evidence": "reference labels are absent from the code object table"}]}
    with pytest.raises(HtmlReviewError) as caught:
        reconstruct_design(scene,binding,reference,run_dir=run,deps=HtmlReviewDependencies(ROOT,generator),
                           beats=contract["narration_beats"],progress=events.append)
    assert caught.value.code == "RECONSTRUCTION_UNSUPPORTED" and len(calls) == 1
    assert events[-1]["next_action"]["routes"] == ["planning"]
    assert not list((run/"planning/html_visual").glob("scene-*.json"))


def test_new_component_choices_apply_before_layout_without_guessing_geometry(tmp_path):
    from html_design_agent import component_context, validate_understanding, apply_allocations
    from html_visual_review_service import HtmlReviewDependencies, review_scene
    root=Path(__file__).resolve().parents[1]
    folder=root/"html_engine/visual/fixtures/presentation-details"
    scene=json.loads((folder/"source-scene.json").read_text(encoding="utf-8"))
    binding=json.loads((folder/"binding.json").read_text(encoding="utf-8"))
    contract=json.loads((folder/"contract.json").read_text(encoding="utf-8"))
    context=component_context(scene,root)
    objects=[]
    for n in scene["nodes"]:
        variant="text-card-label" if n["id"].startswith("stat-") else "summary-relationship-panel" if n["type"]=="summary" else "plain"
        icon={"stat-input":"speech","stat-output":"document","stat-pricing":"coins","billing-summary":"check-plain"}.get(n["id"])
        objects.append({"targetId":n["id"],"owner":"code","assetMode":"none","variant":variant,"icon":icon,"appearance":"registered engineering fixture"})
    result=validate_understanding({"status":"ready","objects":objects,"issues":[]},context)
    updated,operations=apply_allocations(scene,binding,{"result":result},run_dir=tmp_path,beats=contract["narration_beats"])
    assert updated["motion"]==scene["motion"]
    assert all(set(n.get("presentation",{})) <= {"variant","icon"} for n in updated["nodes"])
    assert len(operations)==len(scene["nodes"])
    report=review_scene(updated,run_dir=tmp_path,deps=HtmlReviewDependencies(root,lambda **kw:None),diagnostic=True)
    assert not report["passed"] and report.get("geometry")
    assert any("registered variant requires" in issue.get("message","") for issue in report.get("capacityIssues",[]))


@pytest.mark.parametrize("stop", [False, True])
def test_allocated_capacity_is_repaired_before_reconstruction_or_stops(tmp_path, stop):
    from PIL import Image
    folder = ROOT / "html_engine/visual/fixtures/presentation-details"
    scene = json.loads((folder / "source-scene.json").read_text(encoding="utf-8"))
    binding = json.loads((folder / "binding.json").read_text(encoding="utf-8"))
    contract = json.loads((folder / "contract.json").read_text(encoding="utf-8"))
    from pipeline_lifecycle import write_json_atomic
    write_json_atomic(tmp_path / "planning/visual_contract.json", {"slides": [contract]})
    reference = tmp_path / "reference.png"
    Image.new("RGB", (1280, 720), "white").save(reference)
    context = component_context(scene, ROOT)
    allocation = ready(context)
    icons = {"stat-input": "speech", "stat-output": "document", "stat-pricing": "coins",
             "billing-summary": "check-plain"}
    for item in allocation["objects"]:
        if item["targetId"] in icons:
            item.update(variant="summary-relationship-panel" if item["targetId"] == "billing-summary"
                        else "text-card-label", icon=icons[item["targetId"]])
    operations = json.loads((folder / "operations.json").read_text(encoding="utf-8"))
    operations = [op for op in operations if op["kind"] != "set_variant"]
    calls = []

    def generator(**kw):
        prefix = kw["artifact_prefix"]
        calls.append(prefix)
        if prefix.startswith("design_understanding-"):
            return allocation
        if prefix.startswith("layout-agent-"):
            payload = json.loads(kw["user_prompt"])
            assert payload["diagnostic"]["capacityIssues"]
            assert any(n.get("presentation", {}).get("variant") == "summary-relationship-panel"
                       for n in payload["nodes"])
            return {"action": "stop", "message": "fixture protected capacity"} if stop else {
                "action": "patch", "operations": operations}
        if prefix.startswith("design-reconstruct-"):
            payload = json.loads(kw["user_prompt"])
            summary = next(n for n in payload["objects"] if n["id"] == "billing-summary")
            assert summary["presentation"]["height"] == 160
            return {"status": "unchanged", "message": "fixture layout repaired"}
        return response_for(kw)

    kwargs = dict(run_dir=tmp_path, deps=HtmlReviewDependencies(ROOT, generator),
                  beats=contract["narration_beats"])
    before = copy.deepcopy(scene)
    if stop:
        with pytest.raises(HtmlReviewError) as caught:
            reconstruct_design(scene, binding, reference, **kwargs)
        assert caught.value.code == "CANDIDATE_AGENT_REJECTED"
        assert not any(p.startswith(("design-reconstruct-", "design_fidelity_review-")) for p in calls)
    else:
        result = reconstruct_design(scene, binding, reference, **kwargs)
        assert result["report"]["passed"] and result["binding"] == binding
        assert result["scene"]["motion"] == scene["motion"]
        assert result["summary"]["fidelity_review"]["human_approval"] == "pending"
        audit = tmp_path / result["summary"]["audit"]
        assert (audit / "allocation-layout-agent/0/diagnostic.png").is_file()
        assert not json.loads((audit / "allocation-strict-review.json").read_text(encoding="utf-8"))["passed"]
    assert scene == before
    assert not (tmp_path / "planning/html_visual/scene-token-03.json").exists()
