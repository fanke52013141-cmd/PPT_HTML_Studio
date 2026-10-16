"""Bounded image-grounded design understanding, allocation and independent review."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from artifact_fingerprint import sha256_file, sha256_json
from html_runtime_skills import load_runtime_skill
from html_visual_review_service import HtmlReviewError
from pipeline_lifecycle import write_json_atomic
from html_design_policy import Requirement, production_policy, editable_capabilities, resolve_issue

TIMEOUT = 600


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Allocation(Strict):
    targetId: str
    owner: Literal["code", "image"]
    assetMode: Literal["none", "reuse", "generate"]
    variant: str | None
    icon: str | None
    appearance: str = Field(min_length=1, max_length=1200)


class AllocationIssue(Strict):
    targetId: str
    route: Literal["planning", "assets", "capabilities"]
    evidence: str = Field(min_length=1, max_length=1200)
    requirement: Requirement
    variant_id: str | None = None


class Understanding(Strict):
    status: Literal["ready", "unsupported"]
    objects: list[Allocation] = Field(max_length=40)
    issues: list[AllocationIssue] = Field(max_length=20)


class FidelityIssue(Strict):
    targetId: str
    category: Literal["layout", "content", "asset", "capability"]
    severity: Literal["minor", "major"]
    evidence: str = Field(min_length=1, max_length=1200)
    suggestion: str = Field(min_length=1, max_length=1200)
    requirement: Requirement
    variant_id: str | None = None


class Fidelity(Strict):
    status: Literal["pass", "changes_requested", "unsupported"]
    issues: list[FidelityIssue] = Field(max_length=20)


def component_context(scene, repo_root, *, asset_modes=None):
    catalog = json.loads((Path(repo_root)/"html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    from html_storyboard_planning import load_template_catalog
    icons = load_template_catalog(repo_root)["icons"]
    variants = catalog.get("presentationVariants", {}).get("variants", []) if scene["version"] in ("0.6.0", "0.7.0") else []
    return {
        "production_policy": production_policy(scene),
        "objects": scene["nodes"],
        "capabilities": {n["id"]: {
            "owner": "image" if n["type"] == "image" else "code",
            "assetMode": (asset_modes or {}).get(n["id"], "reuse") if n["type"] == "image" else "none",
            "variants": [v for v in variants if n["type"] in v["nodeTypes"]],
            "icons": icons if any(v.get("allowsIcon") and n["type"] in v["nodeTypes"] for v in variants) else [],
            "editable": editable_capabilities(n, [v for v in variants if n["type"] in v["nodeTypes"]]),
        } for n in scene["nodes"]},
    }


def validate_understanding(response, context):
    result = Understanding.model_validate(response)
    nodes = {n["id"]: n for n in context["objects"]}
    if any(i.targetId not in nodes for i in result.issues):
        raise ValueError("Unknown allocation issue target")
    if result.status == "unsupported":
        if result.objects or not result.issues:
            raise ValueError("Unsupported requires issue evidence and no allocations")
        return result.model_dump()
    if result.issues or len(result.objects) != len(nodes) or {o.targetId for o in result.objects} != set(nodes):
        raise ValueError("Each registered object requires exactly one allocation")
    for item in result.objects:
        allowed = context["capabilities"][item.targetId]
        if (item.owner, item.assetMode) != (allowed["owner"], allowed["assetMode"]):
            raise ValueError("Allocation cannot rasterize code or invent image ownership")
        if item.variant is not None and item.variant not in {v["id"] for v in allowed["variants"]}:
            raise ValueError("Variant not applicable")
        if item.icon is not None and (item.icon not in allowed["icons"] or not next((v.get("allowsIcon") for v in allowed["variants"] if v["id"] == item.variant), False)):
            raise ValueError("Icon not applicable")
        if item.owner == "image" and (item.variant is not None or item.icon is not None):
            raise ValueError("Image allocation cannot use code variants")
    return result.model_dump()


def validate_fidelity(response, scene):
    result = Fidelity.model_validate(response)
    if any(i.targetId not in {n["id"] for n in scene["nodes"]} for i in result.issues):
        raise ValueError("Unknown review target")
    if (result.status == "pass") != (not result.issues):
        raise ValueError("Review status contradicts issues")
    return result.model_dump()


def allocation_routes(result, scene, capabilities):
    nodes = {n["id"]: n for n in scene["nodes"]}
    resolved = []
    for issue in result["issues"]:
        target = issue["targetId"]
        route, reason = resolve_issue(issue, nodes[target], capabilities[target])
        resolved.append({"targetId": target, "requested_route": issue["route"],
                         "requirement": issue["requirement"], "route": route, "reason": reason})
    return resolved


def fidelity_routes(result, scene, capabilities):
    """A model category cannot send code-controlled SVG to bitmap generation."""
    nodes = {n["id"]: n for n in scene["nodes"]}
    resolved = []
    for issue in result["issues"]:
        route, reason = resolve_issue(issue, nodes[issue["targetId"]], capabilities[issue["targetId"]])
        resolved.append({"targetId":issue["targetId"],"category":issue["category"],
                         "requirement":issue["requirement"],"route":route,"reason":reason})
    return resolved


def apply_allocations(scene, binding, understanding, *, run_dir, manual=None, beats=None):
    """Execute model-selected registered variants through the original guarded editor."""
    from html_scene_editing import resources
    from html_scene_repair import candidate_from_document
    import copy
    nodes = {n["id"]: n for n in scene["nodes"]}
    items = understanding["result"]["objects"]
    if len(items) != len(nodes) or {o["targetId"] for o in items} != set(nodes):
        raise HtmlReviewError("设计分工对象与当前场景不一致", code="DESIGN_ALLOCATION_STALE")
    operations = []
    for item in items:
        node = nodes[item["targetId"]]
        if item["owner"] != ("image" if node["type"] == "image" else "code"):
            raise HtmlReviewError("设计分工归属不一致",code="DESIGN_ALLOCATION_STALE")
        if item["owner"] == "code" and item["variant"] is not None:
            values = {"variant":item["variant"]}
            if item["icon"] is not None:
                values["icon"] = item["icon"]
            p = node.get("presentation", {})
            if p.get("variant") == item["variant"] and p.get("icon") == item["icon"]:
                continue
            operations.append({"targetId":item["targetId"],"kind":"set_variant","values":values})
    current = copy.deepcopy(scene)
    project = resources(run_dir)
    for start in range(0,len(operations),20):
        doc = {"scene":current,"binding":binding,"manual":manual,"resources":project,"beats":beats}
        try:
            candidate = candidate_from_document(run_dir,scene["id"],{"expected_revision":0,"source":"ai","operations":operations[start:start+20]},doc)
        except ValueError as exc:
            raise HtmlReviewError("组件选择与当前作者保护或注册能力冲突，停止",code="DESIGN_ALLOCATION_CONFLICT") from exc
        current = candidate["scene"]
    return current, operations


def decision(stage, payload, images, *, folder, run_dir, deps, checkpoint=lambda: None):
    checkpoint()
    skill = load_runtime_skill(deps.repo_root, stage=stage, mode="runtime_skill")
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    paths = [Path(p).resolve() for p in images]
    if any(not p.is_relative_to(Path(run_dir).resolve()) or not p.is_file() for p in paths):
        raise HtmlReviewError("Agent图片路径无效", code="DESIGN_AGENT_IMAGE_INVALID")
    hashes = [sha256_file(p) for p in paths]
    schema = Understanding if stage == "design_understanding" else Fidelity
    prompts = {"system_prompt":skill.fragment,"user_prompt":json.dumps(payload,ensure_ascii=False),
               "schema_hint":json.dumps(schema.model_json_schema(),ensure_ascii=False)}
    write_json_atomic(folder/"request.json",{**prompts,"runtime_skill":skill.identity,"image_sha256":hashes,
                                            "request_timeout_seconds":TIMEOUT,"thinking_policy":"preserve_provider_configuration"})
    response = deps.json_generator(**prompts,run_dir=str(run_dir),artifact_prefix=f"{stage}-{folder.name}",
                                  image_paths=[str(p) for p in paths],request_timeout=TIMEOUT)
    write_json_atomic(folder/"response.json",response)
    checkpoint(); skill.verify()
    if hashes != [sha256_file(p) for p in paths]:
        raise HtmlReviewError("Agent执行时图片发生变化",code="DESIGN_STALE")
    return response, skill.identity


def understand_design(scene, reference, *, run_dir, deps, asset_modes=None, checkpoint=lambda: None, progress=lambda value: None):
    context = component_context(scene,deps.repo_root,asset_modes=asset_modes)
    reference = Path(reference).resolve()
    if not reference.is_relative_to(Path(run_dir).resolve()) or not reference.is_file():
        raise HtmlReviewError("设计图路径无效",code="DESIGN_AGENT_IMAGE_INVALID")
    identity = sha256_json({"context":context,"image":sha256_file(reference),"version":"0.1.0",
                           "skill":load_runtime_skill(deps.repo_root,stage="design_understanding",mode="runtime_skill").identity})
    folder = Path(run_dir)/"planning/html_visual/candidates"/scene["id"]/"design-understanding"/identity
    response, skill = decision("design_understanding",context,[reference],folder=folder,run_dir=run_dir,deps=deps,checkpoint=checkpoint)
    try:
        result = validate_understanding(response,context)
    except ValueError as exc:
        write_json_atomic(folder/"diagnostic.json",{"code":"DESIGN_UNDERSTANDING_INVALID","message":str(exc)[:1200]})
        raise HtmlReviewError("设计理解未通过对象与分工校验",code="DESIGN_UNDERSTANDING_INVALID") from exc
    record = {"result":result,"runtime_skill":skill,"audit":str(folder.relative_to(Path(run_dir))),
              "design_sha256":sha256_file(reference),"scene_sha256":sha256_json(scene)}
    if result["status"] == "unsupported":
        record["routed_issues"] = allocation_routes(result, scene, context["capabilities"])
        record["repair_routes"] = sorted({issue["route"] for issue in record["routed_issues"]})
    write_json_atomic(folder/"result.json",record)
    if result["status"] != "ready":
        progress({"next_action": {"stage": "design_understanding", "reason": "unsupported",
                  "routes": record["repair_routes"], "automatic_retry": False}})
        raise HtmlReviewError("设计要求需规划、素材或组件返工，已保留问题证据",code="DESIGN_ALLOCATION_UNSUPPORTED")
    return record


def review_fidelity(scene, reference, screenshot, report, understanding, *, folder, run_dir, deps, manual=None, checkpoint=lambda: None):
    from html_scene_editing import manual_protected_paths
    payload = {**component_context(scene,deps.repo_root),"measurements":report.get("measurements"),
               "geometry":report.get("geometry"),"manual_protected_paths":manual_protected_paths(manual)}
    response, skill = decision("design_fidelity_review",payload,[reference,screenshot],folder=folder,
                              run_dir=run_dir,deps=deps,checkpoint=checkpoint)
    try:
        result = validate_fidelity(response,scene)
    except ValueError as exc:
        write_json_atomic(Path(folder)/"diagnostic.json",{"code":"DESIGN_REVIEW_INVALID","message":str(exc)[:1200]})
        raise HtmlReviewError("还原审核响应无效，未签发通过",code="DESIGN_REVIEW_INVALID") from exc
    routed = fidelity_routes(result,scene,payload["capabilities"])
    record = {"result":result,"runtime_skill":skill,"scene_sha256":sha256_json(scene),
              "design_sha256":sha256_file(reference),"screenshot_sha256":sha256_file(screenshot),
              "repair_routes":sorted({i["route"] for i in routed}),"routed_issues":routed,"human_approval":"pending"}
    write_json_atomic(Path(folder)/"result.json",record)
    return record
