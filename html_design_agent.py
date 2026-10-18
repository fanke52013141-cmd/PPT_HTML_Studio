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
from html_design_policy import (Requirement, ReferenceDetail, production_policy, editable_capabilities,
                               resolve_issue, presentation_facts, allowed_reference_details, reference_observation)

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
    required_features: list[Literal["label_value_stacked", "term_overlay_on_arrow", "takeaway_below_flow"]] = Field(default_factory=list, max_length=3)


class AllocationIssue(Strict):
    targetId: str
    route: Literal["planning", "assets", "capabilities"]
    evidence: str = Field(min_length=1, max_length=1200)
    requirement: Requirement
    variant_id: str | None = None
    reference_detail: ReferenceDetail | None = None


class Understanding(Strict):
    status: Literal["ready", "unsupported"]
    objects: list[Allocation] = Field(max_length=40)
    issues: list[AllocationIssue] = Field(max_length=20)


class FidelityIssue(Strict):
    targetId: str
    category: Literal["layout", "content", "asset", "capability"] = 'layout'
    severity: Literal["minor", "major"]
    evidence: str = Field(min_length=1, max_length=1200)
    suggestion: str = Field(min_length=1, max_length=1200)
    requirement: Requirement
    variant_id: str | None = None
    reference_detail: ReferenceDetail | None = None
    # Compatibility only: typed duplicate evidence must agree with coverage.
    reference_alignment: Literal['left','center','right','uncertain'] | None = None


class CoverageCheck(Strict):
    targetId: str
    dimension: Literal['geometry','content','typography','structure','semantic_relation','asset_identity','asset_rendering']
    status: Literal['pass','issue','uncertain']
    evidence: str = Field(min_length=1, max_length=300)
    issue_indices: list[int] = Field(default_factory=list, max_length=20)
    reference_alignment: Literal['left','center','right','uncertain'] | None = None


class Fidelity(Strict):
    status: Literal["pass", "changes_requested", "unsupported"]
    issues: list[FidelityIssue] = Field(max_length=20)
    coverage: list[CoverageCheck] = Field(default_factory=list, max_length=280)


def review_checklist(scene):
    result = []
    for node in scene['nodes']:
        dimensions = ['geometry']
        if node['type'] in ('text','header','card','summary','label','badge','figure','chart'):
            dimensions += ['content','typography']
        if node['type'] not in ('image','shape'):
            dimensions += ['structure']
        if node['type'] in ('summary','arrow','annotation','chart'):
            dimensions += ['semantic_relation']
        if node['type'] == 'image':
            dimensions += ['asset_identity','asset_rendering']
        result += [{'targetId':node['id'],'dimension':d} for d in dimensions]
    return result


def validate_coverage(result, scene, alignment=None):
    expected = {(v['targetId'],v['dimension']) for v in review_checklist(scene)}
    actual = [(v.targetId,v.dimension) for v in result.coverage]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('REVIEW_COVERAGE_INCOMPLETE: missing, duplicate or unknown checks')
    for item in result.coverage:
        if item.status == 'uncertain':
            raise ValueError('REVIEW_COVERAGE_INCOMPLETE: uncertain check')
        indices = [i for i,issue in enumerate(result.issues)
                   if (issue.targetId,issue_dimension(issue.requirement)) == (item.targetId,item.dimension)]
        nodes = {n['id']:n for n in scene['nodes']}
        blocking = [i for i in indices if not reference_observation(result.issues[i].model_dump(),nodes[item.targetId])]
        if (blocking and item.status != 'issue') or (item.status == 'issue' and not indices):
            raise ValueError('REVIEW_COVERAGE_INCOMPLETE: issue/check status mismatch')
        # Legacy explicit indices must be accurate; new models omit this bookkeeping.
        if item.issue_indices and set(item.issue_indices) != set(indices):
            raise ValueError('REVIEW_COVERAGE_INCOMPLETE: issue dimension or target mismatch')
        item.issue_indices = indices
        if item.dimension == 'typography' and item.targetId in (alignment or {}):
            if item.reference_alignment in (None,'uncertain'):
                raise ValueError('REVIEW_COVERAGE_INCOMPLETE: missing reference text alignment')
            if item.reference_alignment != alignment[item.targetId]['align'] and not blocking:
                raise ValueError('REVIEW_COVERAGE_INCOMPLETE: text alignment mismatch without issue')
    if any((i.targetId,issue_dimension(i.requirement)) not in expected for i in result.issues):
        raise ValueError('REVIEW_COVERAGE_INCOMPLETE: unreviewed issues')


def issue_dimension(requirement):
    return {'semantic_text':'content','theme_conflict':'structure','registered_variant':'structure',
            'unsupported_presentation':'structure'}.get(requirement,requirement)


def text_alignment_contract(scene, repo_root):
    catalog = json.loads((Path(repo_root)/'html_engine/visual/generated/catalog.json').read_text(encoding='utf-8'))
    layout = next((v for v in catalog['layouts'] if {'id':v['id'],'version':v['version']} == scene.get('layoutRef')), None)
    if not layout:return {}
    return {n['id']:{'align':n.get('presentation',{}).get('typography',{}).get('text',{}).get('align',layout['slots'][n['slot']]['align']),
                    'source':'registered_layout_and_presentation'} for n in scene['nodes'] if n['type']=='text'}


def _applicable_variants(node, variants):
    """Mirror registered compiler preconditions before asking for allocation."""
    if node["type"] == "arrow" and node.get("from"):
        return []  # Bound relation geometry has no independent variants.
    relationship = {"summary-relationship-panel", "summary-relationship-compact",
                    "summary-relationship-columns"}
    result = []
    for variant in variants:
        if node["type"] not in variant["nodeTypes"]:
            continue
        if variant.get("headingAllowed") is False and node.get("heading"):
            continue
        if variant["id"] in relationship and not node.get("heading"):
            continue
        delimiters = variant.get("labelDelimiter")
        if delimiters:
            text = "".join(run.get("text", "") for run in node.get("runs", []))
            first = next((index for index, character in enumerate(text) if character in delimiters), -1)
            if first <= 0 or first >= len(text) - 1:
                continue
        result.append(variant)
    return result


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
            "currentRender": ({"icon": n["icon"], "source": "scene_card"} if n["type"] == "card" else
                              {part: {"icon": n[part]["icon"], "source": "scene_figure_" + part}
                               for part in ("tag", "note") if n.get(part)} if n["type"] == "figure" else {}),
            "variants": (applicable := _applicable_variants(n, variants)),
            "currentPresentation": presentation_facts(n),
            "allowed_reference_details": allowed_reference_details(n),
            "variantFacts": {v["id"]: presentation_facts(n, v["id"]) for v in applicable},
            "icons": icons if any(v.get("allowsIcon") for v in applicable) else [],
            "editable": editable_capabilities(n, applicable),
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
        data = result.model_dump()
        observations = [i for i in data['issues'] if reference_observation(i, nodes[i['targetId']])]
        if len(observations) == len(result.issues):
            raise ValueError('Only allowed reference decorations differ; return complete ready allocations, do not invent missing capabilities')
        data['issues'] = [i for i in data['issues'] if not reference_observation(i, nodes[i['targetId']])]
        data['reference_observations'] = observations
        return data
    observations = [i.model_dump() for i in result.issues if reference_observation(i.model_dump(), nodes[i.targetId])]
    if len(observations) != len(result.issues) or len(result.objects) != len(nodes) or {o.targetId for o in result.objects} != set(nodes):
        raise ValueError("Each registered object requires exactly one allocation")
    for item in result.objects:
        allowed = context["capabilities"][item.targetId]
        if (item.owner, item.assetMode) != (allowed["owner"], allowed["assetMode"]):
            raise ValueError("Allocation cannot rasterize code or invent image ownership")
        if item.variant is not None and item.variant not in {v["id"] for v in allowed["variants"]}:
            raise ValueError("Variant not applicable")
        if item.variant is not None and next(v for v in allowed["variants"] if v["id"] == item.variant).get("requiresIcon") and item.icon is None:
            raise ValueError("Variant requires an icon")
        if item.icon is not None and (item.icon not in allowed["icons"] or not next((v.get("allowsIcon") for v in allowed["variants"] if v["id"] == item.variant), False)):
            raise ValueError("Icon not applicable")
        if item.owner == "image" and (item.variant is not None or item.icon is not None):
            raise ValueError("Image allocation cannot use code variants")
    missing = []
    for item in result.objects:
        facts = presentation_facts(nodes[item.targetId], item.variant)
        for feature in item.required_features:
            if not facts.get(feature):
                missing.append({"targetId": item.targetId, "route": "capabilities",
                                "requirement": "unsupported_presentation", "variant_id": None,
                                "evidence": "Required reference feature is not implemented: " + feature})
    if missing:
        return {"status": "unsupported", "objects": [], "issues": missing[:20]}
    data = result.model_dump()
    data['issues'] = []
    data['reference_observations'] = observations
    return data


def validate_fidelity(response, scene, *, require_coverage=False, alignment=None, require_facts=False):
    original_facts, fact_sources = None, None
    if require_facts or (isinstance(response,dict) and 'facts' in response):
        from html_review_facts import project_facts
        original_facts = response.get('facts') if isinstance(response,dict) else None
        response, fact_sources = project_facts(response,scene,review_checklist(scene),alignment)
        require_coverage = True
    result = Fidelity.model_validate(response)
    for issue in result.issues:
        if issue.reference_alignment is not None:
            checks = [c for c in result.coverage if c.targetId == issue.targetId and c.dimension == 'typography']
            if (issue.requirement != 'typography' or issue.reference_alignment == 'uncertain'
                    or len(checks) != 1 or checks[0].reference_alignment != issue.reference_alignment):
                raise ValueError('REVIEW_COVERAGE_INCOMPLETE: duplicated reference alignment conflicts with coverage')
    if any(i.targetId not in {n["id"] for n in scene["nodes"]} for i in result.issues):
        raise ValueError("Unknown review target")
    nodes = {n['id']:n for n in scene['nodes']}
    blocking = [i for i in result.issues if not reference_observation(i.model_dump(),nodes[i.targetId])]
    if (result.status == 'pass' and blocking) or (result.status != 'pass' and not result.issues):
        raise ValueError("Review status contradicts issues")
    if require_coverage:
        validate_coverage(result, scene, alignment)
    data = result.model_dump()
    for issue in data['issues']:
        issue['category'] = ('layout' if issue['requirement'] in ('geometry','typography') else
                             'content' if issue['requirement'] in ('semantic_text','semantic_relation') else
                             'asset' if issue['requirement'] in ('asset_identity','asset_rendering') else 'capability')
    nodes = {n['id']:n for n in scene['nodes']}
    data['reference_observations'] = [i for i in data['issues'] if reference_observation(i,nodes[i['targetId']])]
    data['issues'] = [i for i in data['issues'] if not reference_observation(i,nodes[i['targetId']])]
    if not data['issues']:
        data['status'] = 'pass'
    if original_facts is not None:
        data['facts'] = original_facts
        data['fact_projection'] = {'contract':'design-review-facts/0.1.0','issue_sources':fact_sources,
                                   'issue_indices_refer_to':'unfiltered_projection'}
    return data


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
                         "requirement":issue["requirement"],"route":route,"reason":reason,
                         "fact_conflict": reason == "requested_variant_already_active_requires_fact_review",
                         "current_variant": nodes[issue["targetId"]].get("presentation", {}).get("variant", "plain"),
                         "requested_variant": issue.get("variant_id")})
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


def decision(stage, payload, images, *, folder, run_dir, deps, checkpoint=lambda: None, skill_stage=None):
    checkpoint()
    skill = load_runtime_skill(deps.repo_root, stage=skill_stage or stage, mode="runtime_skill")
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    paths = [Path(p).resolve() for p in images]
    if any(not p.is_relative_to(Path(run_dir).resolve()) or not p.is_file() for p in paths):
        raise HtmlReviewError("Agent图片路径无效", code="DESIGN_AGENT_IMAGE_INVALID")
    hashes = [sha256_file(p) for p in paths]
    from html_review_facts import ReviewFacts
    from html_reference_localization import MappedLocations
    schema = (MappedLocations if stage == 'design_reference_localization' else Understanding if stage == 'design_understanding' else ReviewFacts
              if payload.get('review_output_contract') == 'design-review-facts/0.1.0' else Fidelity)
    schema_hint = schema.model_json_schema()
    if stage == 'design_fidelity_review' and schema is Fidelity:
        for definition, field in (('FidelityIssue','category'),('FidelityIssue','reference_alignment'),('CoverageCheck','issue_indices')):
            schema_hint['$defs'][definition]['properties'].pop(field,None)
    # Keep thinking enabled with low GLM effort for both design decisions.
    # Binding, output allowance, deadline and structural checks stay unchanged.
    effort_override = "low"
    prompts = {"system_prompt":skill.fragment,"user_prompt":json.dumps(payload,ensure_ascii=False),
               "schema_hint":json.dumps(schema_hint,ensure_ascii=False)}
    write_json_atomic(folder/"request.json",{**prompts,"runtime_skill":skill.identity,"image_sha256":hashes,
                                            "request_timeout_seconds":TIMEOUT,
                                            "reasoning_effort_override":effort_override,
                                            "thinking_policy":"enabled_low_for_glm" if effort_override else "preserve_provider_configuration"})
    response = deps.json_generator(**prompts,run_dir=str(run_dir),artifact_prefix=f"{stage}-{folder.name}",
                                  image_paths=[str(p) for p in paths],request_timeout=TIMEOUT,
                                  **({"reasoning_effort_override": effort_override} if effort_override else {}))
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
        diagnostic = {"code":"DESIGN_UNDERSTANDING_INVALID","message":str(exc)[:1200]}
        write_json_atomic(folder/"diagnostic.json",diagnostic)
        # A complete returned JSON with invalid allocations may receive one
        # model repair. Transport-unknown outcomes never reach this branch.
        repair_input = {**context, "repair_feedback": {
            "diagnostic": diagnostic, "invalid_response": response,
            "instruction": "重新返回完整JSON对象；ready的objects须逐一覆盖输入对象且issues=[]，不得输出占位符或省略字段。",
        }}
        repaired, skill = decision("design_understanding", repair_input, [reference],
                                   folder=folder/"repair", run_dir=run_dir, deps=deps, checkpoint=checkpoint)
        try:
            result = validate_understanding(repaired, context)
        except ValueError as repair_error:
            write_json_atomic(folder/"repair-diagnostic.json",{
                "code":"DESIGN_UNDERSTANDING_INVALID","message":str(repair_error)[:1200]})
            raise HtmlReviewError("设计理解两次未通过对象与分工校验",code="DESIGN_UNDERSTANDING_INVALID") from repair_error
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


def review_target_evidence(scene, screenshot, report):
    """Persist comparable final-frame object evidence; never infer a fix from edited fields."""
    import math
    from PIL import Image
    from artifact_fingerprint import sha256_bytes
    result = {}
    with Image.open(screenshot) as source:
        image = source.convert('RGB')
        for node in scene['nodes']:
            box = report.get('geometry', {}).get(node['id'], {}).get('box')
            region = None
            if box and all(isinstance(box.get(k),(float,int)) for k in ('x','y','width','height')):
                rect = (math.floor(box['x']*image.width/1600), math.floor(box['y']*image.height/900),
                        math.ceil((box['x']+box['width'])*image.width/1600),
                        math.ceil((box['y']+box['height'])*image.height/900))
                if 0 <= rect[0] < rect[2] <= image.width and 0 <= rect[1] < rect[3] <= image.height:
                    region = sha256_bytes(image.crop(rect).tobytes())
            result[node['id']] = {'node_sha256':sha256_json(node), 'box':box,
                                  'region_sha256':region, 'image_size':list(image.size)}
    return result


def retain_unchanged_issues(result, previous, current):
    retained = []
    for issue in (previous or {}).get('result', {}).get('issues', []):
        target = issue['targetId']
        before = previous.get('target_evidence', {}).get(target, {})
        after = current.get(target, {})
        same_pixels = (before.get('region_sha256') and before.get('region_sha256') == after.get('region_sha256')
                       and before.get('box') == after.get('box') and before.get('image_size') == after.get('image_size'))
        no_pixel_proof = not before.get('region_sha256') or not after.get('region_sha256')
        same_node = before.get('node_sha256') and before.get('node_sha256') == after.get('node_sha256')
        if same_pixels or (no_pixel_proof and same_node):
            if issue not in result['issues']:
                result['issues'].append(issue)
            retained.append({'targetId':target,'issue_id':sha256_json(issue),
                             'reason':'unchanged_rendered_region' if same_pixels else 'unchanged_node_without_comparable_region'})
    if result['issues'] and result['status'] == 'pass':
        result['status'] = 'changes_requested'
    return retained


def review_fidelity(scene, reference, screenshot, report, understanding, *, folder, run_dir, deps, manual=None, checkpoint=lambda: None, previous=None, local_comparisons=False):
    from html_scene_editing import manual_protected_paths
    from html_review_evidence import comparison_evidence
    run = Path(run_dir).resolve()
    if any(not Path(p).resolve().is_relative_to(run) for p in (reference, screenshot, folder)):
        raise HtmlReviewError('审核证据路径无效',code='DESIGN_AGENT_IMAGE_INVALID')
    payload = {**component_context(scene,deps.repo_root),"measurements":report.get("measurements"),
               "geometry":report.get("geometry"),"manual_protected_paths":manual_protected_paths(manual)}
    payload['review_checklist'] = review_checklist(scene)
    payload['text_alignment_contract'] = text_alignment_contract(scene,deps.repo_root)
    if not local_comparisons:
        payload['review_output_contract'] = 'design-review-facts/0.1.0'
    evidence = review_target_evidence(scene, screenshot, report)
    if previous:
        if previous.get('design_sha256') != sha256_file(reference):
            raise HtmlReviewError('前轮审核原图不匹配',code='DESIGN_REVIEW_PREVIOUS_STALE')
        payload['prior_open_issues'] = previous['result']['issues']
        payload['current_target_evidence'] = {i['targetId']:evidence.get(i['targetId']) for i in previous['result']['issues']}
        payload['previous_target_evidence'] = {i['targetId']:previous.get('target_evidence', {}).get(i['targetId']) for i in previous['result']['issues']}
    local_evidence, sheets = None, []
    if local_comparisons:
        checkpoint()
        local_evidence, sheets = comparison_evidence(scene, reference, screenshot, report, folder=Path(folder)/'local-evidence')
        payload['local_comparisons'] = local_evidence
    response, skill = decision("design_fidelity_review",payload,[reference,screenshot,*sheets],folder=folder,
                              run_dir=run_dir,deps=deps,checkpoint=checkpoint,
                              skill_stage='design_fidelity_review_local' if local_comparisons else None)
    if local_evidence and (local_evidence['reference_sha256'] != sha256_file(reference)
                           or local_evidence['screenshot_sha256'] != sha256_file(screenshot)
                           or local_evidence['scene_sha256'] != sha256_json(scene)):
        raise HtmlReviewError('局部审核证据来源发生变化',code='DESIGN_STALE')
    try:
        result = validate_fidelity(response,scene,require_coverage=True,alignment=payload['text_alignment_contract'],
                                   require_facts=not local_comparisons)
    except ValueError as exc:
        code = 'DESIGN_REVIEW_COVERAGE_INCOMPLETE' if 'REVIEW_COVERAGE_INCOMPLETE' in str(exc) else 'DESIGN_REVIEW_INVALID'
        write_json_atomic(Path(folder)/"diagnostic.json",{"code":code,"message":str(exc)[:1200]})
        raise HtmlReviewError("还原审核不完整或响应无效，未签发通过",code=code) from exc
    retained = retain_unchanged_issues(result, previous, evidence)
    routed = fidelity_routes(result,scene,payload["capabilities"])
    record = {"result":result,"runtime_skill":skill,"scene_sha256":sha256_json(scene),
              "design_sha256":sha256_file(reference),"screenshot_sha256":sha256_file(screenshot),
              "target_evidence":evidence,"continuity":{"retained":retained},
              "local_evidence":local_evidence,
              "coverage_check":{"status":"complete","expected":len(payload['review_checklist']),"reported":len(result['coverage'])},
              "fact_checks": {"conflicts": sum(i["fact_conflict"] for i in routed),
                              "policy": "preserve_issue_and_block_noop_variant_retry"},
              "repair_routes":sorted({i["route"] for i in routed}),"routed_issues":routed,"human_approval":"pending"}
    write_json_atomic(Path(folder)/"result.json",record)
    return record
