"""A02 contracts, real resource/package bytes, and independent Token expressions."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from html_design_brief import build_design_brief, load_effect_registry
from html_storyboard_planning import HtmlScenePlanError, normalize_html_scene_plan, plan_evidence
from html_visual_review_service import HtmlReviewError, generate_scene_plan
from html_reference_package import assemble_reference, design_content, design_prompt, verify_package
from runtime_support import run_subprocess_killable
from test_html_narration_semantics import CATALOG, CONTRACT_SLIDE, ROOT, semantic_plan


def decomposition_plan():
    plan = semantic_plan()
    plan["version"] = "0.3.0"
    add_definitions(plan)
    return plan


def add_definitions(plan):
    targets = {target["objectId"] for beat in plan["beats"] for target in beat["targets"]}
    plan["objectSemantics"] = []
    for obj in plan["objects"]:
        instructional = obj["id"] in targets
        definition = {"objectId": obj["id"], "role": "instructional" if instructional else "context",
                      "meaning": f"注册内容对象 {obj['id']}", "semanticType": "relation" if obj["kind"] == "summary" else "text",
                      "representation": "code", "initialState": {"visible": not instructional},
                      "endState": {"visible": True}}
        if not instructional:
            definition["initiallyVisibleReason"] = "固定背景说明，不作为本句新知识默认出现"
        plan["objectSemantics"].append(definition)


def normalize(plan, source=None, budget=1, resources=None):
    return normalize_html_scene_plan(plan, CATALOG, contract_slide=source or CONTRACT_SLIDE,
                                     expected_version="0.3.0", asset_budget=budget, resolved_resources=resources)


def brief(plan):
    return build_design_brief(plan, theme="neutral-baseline", asset_budget=plan["assetPolicy"]["budget"],
                              effect_registry=load_effect_registry(ROOT))


@pytest.mark.parametrize("labels", [("输入文本", "分词器", "Token 单元"), ("输入占用", "输出预留", "共享上下文窗口")])
def test_token_concepts_have_independent_code_states_without_invented_numbers(labels):
    plan = decomposition_plan()
    beats = []
    source = {"slide_id": "slide_001", "narration_beats": []}
    for index, label in enumerate(labels, 1):
        oid = f"stat-{index}"
        plan["slots"][oid]["runs"][0]["text"] = label
        b = copy.deepcopy(plan["beats"][0])
        b["id"] = f"token-b{index}"
        b["visualIntent"] = "分别说明" + label
        b["targets"] = [{"objectId": oid, "role": "instructional", "meaning": label}]
        b["actions"] = [{"actionKey": f"reveal-{index}", "objectId": oid, "type": "enter",
                         "expectedState": {"visible": True, "meaning": label}}]
        beats.append(b)
        source["narration_beats"].append({"id": b["id"], "spoken_text": label + "承担本阶段的表达。"})
    plan["slots"]["header"]["title"] = "逐步解释"
    plan["slots"]["summary"] = {"kind": "summary", "from": {"text": labels[0], "tone": "blue"},
                                  "to": {"text": labels[-1], "tone": "green"}, "term": "关系", "takeaway": "各部分需要共同理解"}
    plan["beats"] = beats
    add_definitions(plan)
    frozen = normalize(plan, source, budget=0)
    frames = frozen["visualSequence"]
    assert all(frames[0]["visible"][f"stat-{i}"] is False for i in (1, 2, 3))
    assert frames[1]["after"]["stat-1"] and not frames[1]["after"]["stat-2"]
    assert frames[2]["after"]["stat-2"] and not frames[2]["after"]["stat-3"]
    assert frames[3]["after"]["stat-3"]
    assert frozen["assetPolicy"]["subjects"] == 0
    design = design_content(frozen, brief(frozen))
    for label in labels:
        assert label in design["exactText"]
    assert plan_evidence(frozen)["validation"]["semantic"] == "not_run"


@pytest.mark.parametrize("change,code", [
    (lambda p: p.pop("objectSemantics"), "DECOMPOSITION_MISSING"),
    (lambda p: p["objectSemantics"].pop(), "DECOMPOSITION_COVERAGE"),
    (lambda p: p["objectSemantics"][1].update(initialState={"visible": True}), "DECOMPOSITION_INITIAL_VISIBILITY"),
    (lambda p: p["objectSemantics"][0].pop("initiallyVisibleReason"), "DECOMPOSITION_INITIAL_VISIBILITY"),
    (lambda p: p["objectSemantics"][1].update(endState={"visible": False}), "DECOMPOSITION_END_STATE"),
    (lambda p: p["objectSemantics"][1].update(representation="independent_asset"), "DECOMPOSITION_CODE_OWNERSHIP"),
    (lambda p: p["beats"][0]["actions"][0].update(type="emphasize"), "DECOMPOSITION_STATE_CONFLICT"),
    (lambda p: p["objects"][1].update(exit=True), "DECOMPOSITION_CONTROL_UNSUPPORTED"),
    (lambda p: p["objectSemantics"][1].update(role="context", initiallyVisibleReason=None), "DECOMPOSITION_ROLE_CONFLICT"),
    (lambda p: p["objectSemantics"][1].update(control="image_region"), "DECOMPOSITION_INVALID"),
])
def test_unsupported_or_inconsistent_expression_blocks(change, code):
    plan = decomposition_plan()
    change(plan)
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(plan)
    assert rejected.value.code == code


def image_plan(mode="generate"):
    from test_html_storyboard_planning import CONTRACT_SLIDE as source, valid_plan
    plan = valid_plan()
    plan["version"] = "0.3.0"
    plan["slots"]["subject"]["assetRef"] = {"id": "cold-cup", "version": "0.1.0"}
    plan["slots"]["subject"]["anchorId"] = "droplet-tip"
    plan["slots"]["annotation"]["anchorId"] = "droplet-tip"
    plan["beats"] = [{"id": beat["id"], "visualIntent": source["narration_beats"][i]["spoken_text"],
                      "targets": [{"objectId": beat["target"]["objectId"], "role": "instructional", "meaning": "具体讲解目标"}],
                      "actions": [{"actionKey": f"reveal-{i}", "objectId": beat["target"]["objectId"], "type": "enter",
                                   "expectedState": {"visible": True, "meaning": "显示对应正文/具体定位"}}]}
                     for i, beat in enumerate(plan["beats"])]
    add_definitions(plan)
    image = next(item for item in plan["objectSemantics"] if item["objectId"] == "subject")
    image.update(semanticType="subject", representation="independent_asset", sourceMode=mode,
                 requiredAnchors=["droplet-tip"], meaning="冷杯主体与表面的独立水滴部位")
    source = copy.deepcopy(source)
    source["visual_groups"] = [{"id": "cup", "available_assets": [{"assetRef": {"id": "cold-cup", "version": "0.1.0"}}]}]
    return plan, source


def write_resource(run):
    file = run / "assets/cup.png"
    file.parent.mkdir(parents=True)
    Image.new("RGBA", (32, 32), (120, 120, 120, 255)).save(file)
    data = file.read_bytes()
    manifest = {"assets": [{"id": "cold-cup", "version": "0.1.0", "file": "assets/cup.png",
                            "sha256": hashlib.sha256(data).hexdigest(), "alpha_bbox": [0, 0, 32, 32],
                            "anchors": [{"id": "droplet-tip", "x": 24, "y": 12}]},
                           {"id": "unrelated", "version": "0.1.0", "file": "not-present.png"}]}
    target = run / "planning/html_visual/resources.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(manifest), encoding="utf-8")
    return file


def test_generated_subject_requests_have_states_but_do_not_claim_anchors_verified():
    plan, source = image_plan()
    frozen = normalize(plan, source)
    assert frozen["anchorChecks"]["subject"]["status"] == "pending_asset"
    need = brief(frozen)["asset_needs"][0]
    request = need["generation_request"]
    assert request["status"] == "prepared_not_called"
    assert request["size"] == "1024x1024" and request["quality"] == "low"
    assert "droplet-tip" in request["prompt"] and '"initialState"' in request["prompt"]
    assert request["transparent_background"] is True
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(plan, source, budget=0)
    assert rejected.value.code == "BRIEF_BUDGET_EXCEEDED"
    definition = next(item for item in plan["objectSemantics"] if item["objectId"] == "subject")
    definition["requiredAnchors"] = ["focus"]
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(plan, source)
    assert rejected.value.code == "DECOMPOSITION_ANCHOR_GENERIC"


def test_existing_png_verified_selected_only_and_corrupt_bytes_block(tmp_path):
    plan, source = image_plan("existing")
    file = write_resource(tmp_path)
    kwargs = dict(run_dir=tmp_path, repo_root=ROOT, json_generator=lambda **_: copy.deepcopy(plan), plan_version="0.3.0")
    frozen = generate_scene_plan(source, **kwargs)
    assert frozen["anchorChecks"]["subject"]["status"] == "resource_verified"
    assert frozen["anchorChecks"]["subject"]["anchors"]["droplet-tip"] == {"x": 0.75, "y": 0.375}
    assert frozen["anchorChecks"]["subject"]["file_sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()
    assert frozen["design_brief"]["asset_needs"][0]["generation_request"]["status"] == "reuse_only"
    package = assemble_reference(frozen, frozen["design_brief"], repo_root=ROOT, directory=tmp_path / "package",
                                 runner=run_subprocess_killable, run_dir=tmp_path)
    attached = [entry for entry in package["manifest"]["attachments"] if entry.get("type") == "subject-reference"]
    assert len(attached) == 1
    assert (tmp_path / "package" / attached[0]["path"]).read_bytes() == file.read_bytes()
    assert attached[0]["assetRef"] == {"id": "cold-cup", "version": "0.1.0"}
    assert "subjectAttachments" in design_prompt(package)
    assert normalize(frozen, source, resources=__import__("html_scene_editing").resources(tmp_path, [{"id": "cold-cup", "version": "0.1.0"}]))["visualSequence"] == frozen["visualSequence"]
    file.write_bytes(file.read_bytes() + b"changed")
    with pytest.raises(HtmlReviewError) as rejected:
        generate_scene_plan(source, **kwargs)
    assert "DECOMPOSITION_RESOURCE_INVALID" in str(rejected.value)


def test_real_package_hashes_narration_states_and_minimal_prompt(tmp_path):
    frozen = normalize(decomposition_plan())
    design = brief(frozen)
    package = assemble_reference(frozen, design, repo_root=ROOT, directory=tmp_path / "package", runner=run_subprocess_killable)
    assert package["content"]["narrationDesign"]["sequence"] == frozen["visualSequence"]
    assert package["references"] and all(Path(path).is_file() for path in package["references"])
    prompt = design_prompt(package)
    assert "html-design-reference/0.4.0" in prompt
    assert CONTRACT_SLIDE["narration_beats"][0]["spoken_text"] in prompt
    assert "source_sha256" not in prompt and "anchor_checks" not in prompt
    content_file = tmp_path / "package" / package["manifest"]["exactContent"]["path"]
    content_file.write_bytes(content_file.read_bytes() + b" ")
    with pytest.raises(HtmlReviewError):
        verify_package(tmp_path / "package")
    frozen["objectSemantics"][0]["meaning"] = "changed"
    with pytest.raises(ValueError, match="重新校验"):
        design_content(frozen, design)


def test_shared_request_version_and_new_schema():
    from html_scene_plan_models import HtmlPlanGenerationRequest
    from agent_contract.models import HtmlPlanGenerationResult
    from pydantic import ValidationError
    assert HtmlPlanGenerationRequest(plan_version="0.3.0", asset_budget=0).asset_budget == 0
    with pytest.raises(ValidationError):
        HtmlPlanGenerationRequest(plan_version="0.3.0", asset_budget=True)
    frozen = normalize(decomposition_plan())
    result = HtmlPlanGenerationResult(project_id="test", slide_id="slide_001", plan=frozen, evidence=plan_evidence(frozen))
    assert result.model_dump()["plan"]["objectSemantics"]


@pytest.mark.parametrize("change,code", [
    (lambda p: next(item for item in p["objectSemantics"] if item["objectId"] == "subject").update(semanticType="data"), "DECOMPOSITION_IMAGE_OWNERSHIP"),
    (lambda p: p["slots"]["subject"]["assetRef"].update(id="unknown"), "DECOMPOSITION_ASSET_IDENTITY"),
    (lambda p: p["assets"].append(copy.deepcopy(p["assets"][0])), "DECOMPOSITION_ASSET_DUPLICATE"),
    (lambda p: p["slots"]["annotation"].update(targetId="figure"), "DECOMPOSITION_ANNOTATION_REFERENCE"),
    (lambda p: next(item for item in p["objectSemantics"] if item["objectId"] == "subject").update(initialState={"visible": False}, endState={"visible": False}, initiallyVisibleReason=None), "DECOMPOSITION_ANNOTATION_LIFETIME"),
])
def test_image_ownership_identity_and_annotation_dependencies(change, code):
    plan, source = image_plan()
    change(plan)
    with pytest.raises(HtmlScenePlanError) as rejected:
        normalize(plan, source)
    assert rejected.value.code == code


def test_selected_existing_anchor_must_actually_exist(tmp_path):
    plan, source = image_plan("existing")
    write_resource(tmp_path)
    path = tmp_path / "planning/html_visual/resources.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["assets"][0]["anchors"][0]["id"] = "different-part"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(HtmlReviewError, match="DECOMPOSITION_ANCHOR_MISSING"):
        generate_scene_plan(source, run_dir=tmp_path, repo_root=ROOT, json_generator=lambda **_: plan,
                            plan_version="0.3.0")


def test_anchor_metadata_changes_after_plan_block_reference_assembly(tmp_path):
    plan, source = image_plan("existing")
    write_resource(tmp_path)
    frozen = generate_scene_plan(source, run_dir=tmp_path, repo_root=ROOT, json_generator=lambda **_: plan, plan_version="0.3.0")
    path = tmp_path / "planning/html_visual/resources.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["assets"][0]["anchors"][0]["x"] = 10
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(HtmlReviewError, match="须重新规划"):
        assemble_reference(frozen, frozen["design_brief"], repo_root=ROOT, directory=tmp_path / "package",
                           runner=run_subprocess_killable, run_dir=tmp_path)
    assert not (tmp_path / "package").exists()


@pytest.mark.parametrize("bad_objects", [None, 7, "not-a-list"])
def test_malformed_model_object_table_gets_bounded_repair_diagnostic(tmp_path, bad_objects):
    plan = decomposition_plan()
    plan["objects"] = bad_objects
    calls = []

    def generator(**kwargs):
        calls.append(kwargs)
        return plan

    with pytest.raises(HtmlReviewError, match="PLAN_OBJECTS_MISSING"):
        generate_scene_plan(CONTRACT_SLIDE, run_dir=tmp_path, repo_root=ROOT, json_generator=generator,
                            plan_version="0.3.0")
    assert len(calls) == 2
    assert "html-plan-0.6.0" in calls[0]["system_prompt"]
    assert json.loads(calls[0]["user_prompt"])["asset_budget"] == 1
