"""Image-grounded instance reconstruction using existing constrained editor tools."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

from artifact_fingerprint import sha256_file, sha256_json
from html_scene_repair import candidate_from_document
from html_scene_editing import resources, manual_protected_paths, SceneEditError
from html_visual_review_service import HtmlReviewError, review_scene
from html_storyboard_planning import load_template_catalog
from html_design_agent import (understand_design, review_fidelity, apply_allocations, component_context,
                               validate_understanding, allocation_routes)
from html_runtime_skills import load_runtime_skill
from pipeline_lifecycle import write_json_atomic
from html_page_budget import page_budgeted

PROMPT_VERSION = "html-design-reconstruct/0.6.2"
REQUEST_TIMEOUT_SECONDS = 600


@page_budgeted
def reconstruct_design(scene, binding, design_path, *, run_dir, deps, manual=None,
                       beats=None, understanding=None, checkpoint=lambda: None, progress=lambda value: None,
                       reference_review_key=None):
    run = Path(run_dir)
    design_path = Path(design_path).resolve()
    if not design_path.is_relative_to(run.resolve()) or not design_path.is_file():
        raise HtmlReviewError("设计参考路径无效", code="RECONSTRUCTION_REFERENCE_INVALID")
    source_hash = sha256_file(design_path)
    skill = load_runtime_skill(deps.repo_root,stage="design_reconstruction",mode="runtime_skill")
    identity = sha256_json({"scene":scene,"binding":binding,"design":source_hash,
                            "manual":manual,"prompt":PROMPT_VERSION,"runtime_skill":skill.identity,
                            "understanding":understanding})
    audit = run/"planning/html_visual/candidates"/scene["id"]/"design-reconstruction"/identity
    audit.mkdir(parents=True,exist_ok=True)
    def stop(reason, routes, code, message, **evidence):
        action = {"stage": "reconstruction", "reason": reason, "routes": routes, "automatic_retry": False}
        write_json_atomic(audit/"result.json", {"status": "rejected", "stop_reason": reason,
            "next_action": action, "design_sha256": source_hash, "visual_fidelity": "not_accepted", **evidence})
        progress({"next_action": action})
        raise HtmlReviewError(message, code=code)
    # PNG is the existing multimodal transport format; keep original source/hash.
    reference = audit/"reference.png"
    with Image.open(design_path) as image:
        image.load()
        if image.width*image.height > 4_000_000:
            raise HtmlReviewError("设计参考超过视觉输入预算",code="RECONSTRUCTION_REFERENCE_INVALID")
        image.save(reference,format="PNG")
    if reference_review_key:
        from html_reference_publication import restore
        try:
            proposed,report,fidelity=restore(scene,binding,reference_review_key,reference,run_dir=run,
                deps=deps,manual=manual,beats=beats,audit=audit)
        except ValueError as error:
            raise HtmlReviewError(str(error),code='REFERENCE_CONTINUATION_REJECTED',status_code=409) from error
        checkpoint();skill.verify()
        return _result(proposed,binding,report,audit,run,[{'source':'reference_review','key':reference_review_key}],
                       source_hash,proposed!=scene,understanding,fidelity,skill.identity)
    understanding = understanding or understand_design(scene,reference,run_dir=run,deps=deps,checkpoint=checkpoint,progress=progress)
    if understanding["design_sha256"] != source_hash:
        # PNG transport may transcode; compare against the actual original design.
        if understanding["design_sha256"] != sha256_file(reference):
            raise HtmlReviewError("设计理解与当前设计不一致",code="DESIGN_STALE")
    catalog = json.loads((deps.repo_root/"html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    layout = next(v for v in catalog["layouts"] if v["id"]==scene["layoutRef"]["id"] and v["version"]==scene["layoutRef"]["version"])
    current, allocation_operations = apply_allocations(scene,binding,understanding,run_dir=run,manual=manual,beats=beats)
    write_json_atomic(audit/"allocation-applied.json",{"operations":allocation_operations,"scene":current,
                                                     "source":"validated_model_understanding","human_approval":"pending"})
    # A variant can invalidate a layout that passed before allocation. Repair
    # the actual selected components before spending a reconstruction request.
    allocation_report = review_scene(current, run_dir=run, deps=deps)
    write_json_atomic(audit / "allocation-strict-review.json", allocation_report)
    if not allocation_report.get("passed"):
        if "CONTENT_CAPACITY_EXCEEDED" not in str(allocation_report.get("message", "")):
            raise HtmlReviewError("组件选择后的工程检查失败：" + str(allocation_report.get("message")),
                                  code="CANDIDATE_REJECTED", status_code=422)
        from html_candidate_agent import repair_candidate
        repaired = repair_candidate(current, binding, run_dir=run, deps=deps,
                                    manual=manual, checkpoint=checkpoint, progress=progress,
                                    deterministic_first=True, beats=beats)
        current, binding = repaired["scene"], repaired["binding"]
        shutil.copytree(run / repaired["summary"]["audit"], audit / "allocation-layout-agent",
                        dirs_exist_ok=True)
        allocation_report = review_scene(current, run_dir=run, deps=deps)
        write_json_atomic(audit / "allocation-capacity-repair.json", {
            "scene": current, "binding": binding, "summary": repaired["summary"],
            "report": allocation_report,
        })
        if not allocation_report.get("passed"):
            raise HtmlReviewError("组件容量修复后的工程检查仍失败", code="CANDIDATE_REJECTED", status_code=422)
    history = []
    diagnostic = None
    seen = set()
    fidelity = None
    for index in range(2):
        checkpoint()
        skill.verify()
        if sha256_file(design_path) != source_hash:
            raise HtmlReviewError("设计图在还原过程中变化",code="DESIGN_STALE")
        folder = audit/str(index);folder.mkdir(exist_ok=True)
        report = review_scene(current,run_dir=run,deps=deps,diagnostic=True,
                              preflight_dir=folder/"preflight-current")
        write_json_atomic(folder/"current-review.json", report)
        shot = run/report.get("screenshot","missing")
        if not shot.is_file() or not report.get("geometry"):
            raise HtmlReviewError("缺少实际代码截图，不能还原",code="RECONSTRUCTION_RENDER_FAILED")
        current_image = folder/"current.png"
        current_image.write_bytes(shot.read_bytes())
        context = component_context(current, deps.repo_root)
        user = {"canvas":layout["canvas"],"objects":current["nodes"],
                "base_slots":{n["slot"]:layout["slots"][n["slot"]] for n in current["nodes"]},
                "production_policy": context["production_policy"],
                "capabilities": context["capabilities"],
                "manual_protected_paths":manual_protected_paths(manual),
                "actual_geometry":report["geometry"],"actual_measurements":report.get("measurements"),
                "capacity_issues":report.get("capacityIssues", []),
                "geometry_preflight":report.get("geometry_preflight"),
                "diagnostic":diagnostic,
                "content_safe_rect":{"x":0,"y":0,"width":1600,"height":800},
                "motion_extents":{n["id"]:{
                    "minX":min([0]+[a.get("offsetX",0) for a in current["motion"] if a["targetId"]==n["id"]]),
                    "maxX":max([0]+[a.get("offsetX",0) for a in current["motion"] if a["targetId"]==n["id"]]),
                    "minY":min([0]+[a.get("offsetY",0) for a in current["motion"] if a["targetId"]==n["id"]]),
                    "maxY":max([0]+[a.get("offsetY",0) for a in current["motion"] if a["targetId"]==n["id"]])
                } for n in current["nodes"]}}
        user["geometry_limits"] = {}
        for node in current["nodes"]:
            box = layout["slots"][node["slot"]]["box"]
            p = node.get("presentation", {})
            extent = user["motion_extents"][node["id"]]
            x, y = box["x"] + p.get("offsetX", 0), box["y"] + p.get("offsetY", 0)
            user["geometry_limits"][node["id"]] = {
                "current_base_x":x,"current_base_y":y,
                "max_width_at_current_x":1600-x-extent["maxX"],
                "max_height_at_current_y":800-y-extent["maxY"],
                "max_offsetY_at_current_height":800-box["y"]-p.get("height",box["height"])-extent["maxY"],
            }
        user["registered_icons"] = sorted(load_template_catalog(deps.repo_root)["icons"])
        prompts = {"system_prompt":skill.fragment,"user_prompt":json.dumps(user,ensure_ascii=False),
                   "schema_hint":"{status:candidate,operations:[{targetId,kind,part?,values}]} or {status:unchanged,message} or {status:unsupported,message,issues:[{targetId,route,requirement,variant_id?,evidence}]}"}
        # The current render is evidence for the first decision too, including
        # an unchanged response. Keep this order identical in every round.
        images = [str(reference.resolve()), str(current_image.resolve())]
        write_json_atomic(folder/"request.json",{**prompts,"prompt_version":PROMPT_VERSION,
                         "request_timeout_seconds":REQUEST_TIMEOUT_SECONDS,
                         "thinking_policy":"enabled_low_for_glm",
                         "reasoning_effort_override":"low",
                         "runtime_skill":skill.identity,
                         "source_design_sha256":source_hash,
                         "image_roles":["design_reference", "current_html_render"],
                         "image_sha256":[sha256_file(Path(p)) for p in images]})
        progress({"design_reconstruction_round":index+1,"design_reconstruction_max_rounds":2})
        # A transport exception is not structural: let persistent stages handle unknown.
        response = deps.json_generator(**prompts,run_dir=str(run),artifact_prefix=f"design-reconstruct-{scene['id']}-{index}",image_paths=images,
                                      request_timeout=REQUEST_TIMEOUT_SECONDS,reasoning_effort_override="low")
        write_json_atomic(folder/"response.json",response)
        history.append({"round":index+1,"response":response})
        checkpoint(); skill.verify()
        try:
            if not isinstance(response,dict):
                raise ValueError("Response must be an object")
            if response.get("status") in ("unsupported","unchanged"):
                expected = {"status", "message", "issues"} if response["status"] == "unsupported" else {"status", "message"}
                if set(response)!=expected or not isinstance(response["message"],str) or not response["message"].strip():
                    raise ValueError("Stop requires a message")
                if response["status"]=="unsupported":
                    checked = validate_understanding({"status": "unsupported", "objects": [], "issues": response["issues"]}, context)
                    routed = allocation_routes(checked, current, context["capabilities"])
                    stop("unsupported", sorted({i["route"] for i in routed}), "RECONSTRUCTION_UNSUPPORTED",
                         response["message"], history=history, routed_issues=routed)
                final = review_scene(current,run_dir=run,deps=deps,
                                     preflight_dir=folder/"preflight-final")
                proposed = current
            elif set(response)!={"status","operations"} or response["status"]!="candidate" or not isinstance(response["operations"],list):
                raise ValueError("Expected registered operations")
            elif any(not isinstance(o,dict) or o.get("kind") not in ("set_presentation","set_text_style","set_variant") for o in response["operations"]):
                raise ValueError("Only static instance operations are permitted")
            else:
                doc={"scene":current,"binding":binding,"manual":manual,"resources":resources(run),"beats":beats}
                candidate=candidate_from_document(run,scene["id"],{"expected_revision":0,"source":"ai","operations":response["operations"]},doc)
                proposed = candidate["scene"]
                final=review_scene(proposed,run_dir=run,deps=deps,
                                   preflight_dir=folder/"preflight-final")
            if not final.get("passed") and ((final.get("geometry_preflight", {}).get("issues")
                    and final.get("geometry_preflight", {}).get("raw_report_sha256"))
                    or "CONTENT_CAPACITY_EXCEEDED" in str(final.get("message", ""))):
                from html_linked_layout import solve_production_layout
                deterministic = solve_production_layout(proposed, binding, run_dir=run, deps=deps,
                    manual=manual, beats=beats, checkpoint=checkpoint, progress=progress)
                write_json_atomic(folder/"deterministic-layout.json", deterministic["summary"])
                if deterministic["summary"]["status"] in ("candidate", "unchanged"):
                    proposed, final = deterministic["scene"], deterministic["report"]
            write_json_atomic(folder/"strict-review.json",final)
            if not final.get("passed"):
                diagnostic={"code":final.get("code"),"message":final.get("message"),
                            "capacityIssues":final.get("capacityIssues"),
                            "geometry_preflight":final.get("geometry_preflight")}
                current=proposed
                continue
            identity = sha256_json(proposed)
            if identity in seen:
                stop("repeated_candidate", ["manual_review"], "DESIGN_RECONSTRUCTION_NO_PROGRESS", "还原候选重复且未改善，停止", history=history)
            seen.add(identity)
            screenshot = run/final.get("screenshot","missing")
            if not screenshot.is_file():
                raise HtmlReviewError("还原审核缺少实际截图",code="DESIGN_REVIEW_IMAGE_MISSING")
            archived_shot = folder/"candidate.png"
            archived_shot.write_bytes(screenshot.read_bytes())
            progress({"design_review_round":index+1,"design_review_max_rounds":2})
            fidelity = review_fidelity(proposed,reference,archived_shot,final,understanding,folder=folder/"fidelity",
                                       run_dir=run,deps=deps,manual=manual,checkpoint=checkpoint,previous=fidelity,
                                       localized_reference=True, progress=progress)
            if fidelity["result"]["status"] == "pass":
                return _result(proposed,binding,final,audit,run,history,source_hash,proposed!=scene,understanding,fidelity,skill.identity)
            if fidelity["result"]["status"] == "unsupported" or set(fidelity["repair_routes"]) - {"reconstruction"}:
                stop("upstream_revision_required", fidelity["repair_routes"], "DESIGN_REVIEW_ROUTED",
                     "还原审核要求回到内容、素材或组件能力阶段，已保留证据", history=history, fidelity=fidelity)
            current = proposed
            diagnostic = {"code":"DESIGN_FIDELITY_CHANGES_REQUESTED","issues":fidelity["result"]["issues"]}
        except HtmlReviewError:
            raise
        except (ValueError,SceneEditError,KeyError,TypeError) as error:
            diagnostic={"code":getattr(error,"code","RECONSTRUCTION_RESPONSE_INVALID"),"message":str(error)[:1500]}
            write_json_atomic(folder/"diagnostic.json",diagnostic)
    stop("budget_exhausted", ["manual_review"], "RECONSTRUCTION_REJECTED",
         "设计还原预算已耗尽，已保留候选，请检查失败证据后决定后续处理。",
         history=history, diagnostic=diagnostic, fidelity=fidelity)


def _result(scene,binding,report,audit,run,history,source_hash,changed,understanding,fidelity,skill):
    summary={"prompt_version":PROMPT_VERSION,"rounds":len(history),"changed":changed,
             "design_sha256":source_hash,"audit":str(audit.relative_to(run)),
             "engineering":"passed","visual_fidelity":"model_pass_pending_user_review",
             "materialized_assets":[{"targetId":n["id"],"assetRef":n["assetRef"]} for n in scene["nodes"] if n["type"] == "image"],
             "understanding":understanding,"fidelity_review":fidelity,"runtime_skill":skill}
    write_json_atomic(audit/"result.json",{"scene":scene,"binding":binding,"summary":summary})
    return {"scene":scene,"binding":binding,"report":report,"summary":summary}
