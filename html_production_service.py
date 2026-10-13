"""Plan-to-scene production. Registered components, project assets, explicit beats.

The returned candidate is never automatically approved. File replacement and
revision checks use the same project lock as manual edits.
"""

from __future__ import annotations

import copy
import json
import hashlib
from artifact_fingerprint import sha256_json
from pathlib import Path
from typing import Callable

from html_visual_store import (
    scene_path,
    revision_path,
    save_scene,
    validate_slide_id,
    _atomic_write_bytes,
)
from pipeline_lifecycle import project_artifact_lock, write_json_atomic
from html_visual_review_service import (
    generate_scene_plan,
    review_scene,
    HtmlReviewError,
)
from html_design_brief import (
    build_design_brief,
    freeze_design,
    load_effect_registry,
    required_keyframes,
)
from html_asset_service import HtmlAssetDependencies, produce_asset


def supplied_asset_ids(plan, contract, run_dir, repo_root):
    """Only explicitly supplied, matching, validated resources bypass generation."""
    offered = {}
    for group in contract.get("visual_groups", []):
        for item in group.get("available_assets", []):
            ref = item.get("assetRef", {})
            if not ref.get("id") or not ref.get("version"):
                raise HtmlReviewError("提供的素材缺少身份或版本", code="SUPPLIED_ASSET_INVALID")
            offered[ref["id"]] = ref["version"]
    used = [need for need in plan["assets"] if need["render_owner"] == "image_asset" and need["id"] in offered]
    if not used:
        return set()
    from html_scene_editing import resources as validated_resources

    project = validated_resources(run_dir)
    catalog = json.loads((repo_root / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    available = {a["id"]: a for a in catalog["assets"] + project["assets"]}
    reused = set()
    for need in used:
        asset = available.get(need["id"])
        content = plan["slots"].get(need.get("slot"), {})
        expected = {"id": need["id"], "version": offered[need["id"]]}
        if not asset or asset["version"] != expected["version"] or content.get("assetRef") != expected:
            raise HtmlReviewError("提供素材的身份、版本或图片引用不一致", code="SUPPLIED_ASSET_INVALID")
        reused.add(need["id"])
    return reused


def compile_plan(
    plan: dict,
    contract: dict,
    catalog: dict,
    relation_resolutions: list[dict] | None = None,
) -> tuple[dict, dict]:
    """Content fills registered slots; IDs and time are resolved by code."""
    if plan.get("version", "0.1.0") != "0.1.0":
        raise HtmlReviewError(
            "语义规划尚需对应版本的动作编译接入，不得按旧单目标模式执行",
            code="SEMANTIC_COMPILER_PENDING",
        )
    if plan["templateRef"]["id"] not in catalog["templates"]:
        raise HtmlReviewError("模板未注册")
    slide_id = validate_slide_id(plan["slide_id"])
    objects = {obj["slot"]: obj for obj in plan["objects"]}
    if len(objects) != len(plan["objects"]) or set(objects) != set(plan["slots"]):
        raise HtmlReviewError(
            "对象表与内容槽位必须一一对应", code="OBJECT_SLOT_MISMATCH"
        )
    nodes = []
    for slot, content in plan["slots"].items():
        obj = objects[slot]
        if content["kind"] != obj["kind"]:
            raise HtmlReviewError("对象类型与内容类型不一致")
        node = {k: copy.deepcopy(v) for k, v in content.items() if k != "kind"}
        node.update(id=obj["id"], slot=slot, type=content["kind"])
        if node["type"] == "text":
            node.setdefault(
                "role",
                {
                    "headline": "headline",
                    "intro": "intro",
                    "caption": "caption",
                    "anchor-label": "caption",
                }.get(slot, "callout"),
            )
        if node["type"] == "image":
            need = next(
                (
                    a
                    for a in plan["assets"]
                    if a.get("slot") == slot and a.get("render_owner") == "image_asset"
                ),
                None,
            )
            if need:
                node["assetRef"] = {"id": need["id"], "version": "0.1.0"}
            node.setdefault("anchorId", "focus")
        nodes.append(node)

    # Resolve explicit asset/slot identities to node IDs. A unique image or
    # label alone does not prove that an unknown model reference means it.
    nodes_by_id = {node["id"]: node for node in nodes}
    objects_by_slot = {obj["slot"]: obj for obj in plan["objects"]}
    asset_slot_by_id = {
        asset["id"]: asset.get("slot")
        for asset in plan["assets"]
        if asset.get("render_owner") == "image_asset" and asset.get("slot")
    }
    for annotation in (node for node in nodes if node["type"] == "annotation"):
        original_target_id = annotation["targetId"]
        target = nodes_by_id.get(original_target_id)
        if target is None:
            target_slot = asset_slot_by_id.get(original_target_id)
            slot_object = objects_by_slot.get(target_slot or original_target_id)
            if slot_object and slot_object["kind"] == "image":
                target = nodes_by_id.get(slot_object["id"])
        if not target or target["type"] != "image":
            raise HtmlReviewError(
                f"标注 {annotation['id']} 未能唯一对应到图片对象",
                code="ANNOTATION_TARGET_UNRESOLVED",
            )
        if target.get("anchorId") != annotation["anchorId"]:
            raise HtmlReviewError(
                f"标注 {annotation['id']} 与图片焦点不一致",
                code="ANNOTATION_ANCHOR_MISMATCH",
            )

        original_label_id = annotation["labelId"]
        label = nodes_by_id.get(original_label_id)
        if label is None:
            label_slot = objects_by_slot.get(original_label_id)
            if label_slot and label_slot["kind"] == "text":
                label = nodes_by_id.get(label_slot["id"])
        if not label or label["type"] != "text":
            raise HtmlReviewError(
                f"标注 {annotation['id']} 未能唯一对应到文字标签",
                code="ANNOTATION_LABEL_UNRESOLVED",
            )
        if original_target_id != target["id"] or original_label_id != label["id"]:
            if relation_resolutions is not None:
                relation_resolutions.append({
                    "annotation_id": annotation["id"],
                    "target": {"requested": original_target_id, "resolved": target["id"]},
                    "label": {"requested": original_label_id, "resolved": label["id"]},
                    "basis": "explicit asset/slot identity with matching image anchor",
                })
            annotation["targetId"] = target["id"]
            annotation["labelId"] = label["id"]

    duration = max(12000, len(plan["beats"]) * 3500)
    if duration > 120000:
        raise HtmlReviewError("语块过多，请拆页")
    beat_positions = {
        b["id"]: i * duration // len(plan["beats"]) for i, b in enumerate(plan["beats"])
    }
    targets = {o["id"] for o in plan["objects"]}
    mapping = {}
    for beat in plan["beats"]:
        if beat.get("narration_only"):
            continue
        target = beat["target"]
        if target["objectId"] not in targets:
            raise HtmlReviewError("讲稿引用了不存在的对象", code="BEAT_TARGET_MISSING")
        key = f"{target['objectId']}:{target['action']}"
        if key in mapping:
            raise HtmlReviewError(
                "同一动作重复绑定，请使用明确的动作或旁白", code="BEAT_ACTION_DUPLICATE"
            )
        mapping[key] = {"beatId": beat["id"], "edge": "start", "offsetMs": 0}
    motion = []
    for i, obj in enumerate(plan["objects"]):
        key = f"{obj['id']}:enter"
        start = beat_positions[mapping[key]["beatId"]] if key in mapping else 0
        motion.append(
            {
                "targetId": obj["id"],
                "type": "enter",
                "startMs": start,
                "durationMs": 500,
                "offsetX": 0,
                "offsetY": 0 if obj["kind"] == "annotation" else 12,
            }
        )
        emphasize = f"{obj['id']}:emphasize"
        if emphasize in mapping:
            when = max(start + 500, beat_positions[mapping[emphasize]["beatId"]])
            mapping[emphasize]["offsetMs"] = (
                when - beat_positions[mapping[emphasize]["beatId"]]
            )
            motion.append(
                {
                    "targetId": obj["id"],
                    "type": "emphasize",
                    "startMs": when,
                    "durationMs": 500,
                }
            )
        if obj.get("exit"):
            motion.append(
                {
                    "targetId": obj["id"],
                    "type": "exit",
                    "startMs": duration - 1000,
                    "durationMs": 500,
                }
            )
    name = str((plan["slots"].get("header") or {}).get("title") or slide_id)
    scene = {
        "format": "hps.visual.scene",
        "version": "0.3.0",
        "id": slide_id,
        "name": name,
        "themeRef": {"id": "neutral-baseline", "version": "0.2.0"},
        "layoutRef": plan["layoutRef"],
        "templateRef": plan["templateRef"],
        "durationMs": duration,
        "nodes": nodes,
        "motion": motion,
        "beats": [],
        "source": str(contract.get("source") or "课程内容；语义来源保存在分镜契约中。"),
    }
    return scene, {
        "format": "hps.html.motion_binding",
        "version": "0.1.0",
        "mode": "beat_ids",
        "actions": mapping,
    }


def produce_scene(
    contract: dict,
    *,
    run_dir: Path,
    deps,
    provider: Callable | None = None,
    checkpoint: Callable = lambda: None,
    model_summary: dict | None = None,
    options: dict | None = None,
    stage_record: Callable = lambda name, value: None,
    progress_record: Callable = lambda value: None,
    commit_record: Callable = lambda result, paths, **kwargs: None,
) -> dict:
    from html_storyboard_planning import load_template_catalog

    slide_id = validate_slide_id(contract["slide_id"])
    with project_artifact_lock(run_dir):
        from html_visual_store import _read_revision

        revision = _read_revision(run_dir)["revision"]
        from html_visual_store import load_scene
        from pipeline_lifecycle import read_json_file
        original_scene = load_scene(run_dir, slide_id)
        original_binding = read_json_file(run_dir / f"planning/html_visual/binding-{slide_id}.json")
    checkpoint()
    model_summary = copy.deepcopy(model_summary or {})
    # Preserve legacy GPT Image standard-size support. Current Flare/native
    # custom-size models use the shared 1K widescreen request.
    image_model = str(model_summary.get("image", {}).get("model", "")).lower()
    design_size = "1536x1024" if image_model.startswith("gpt-image-1") else "1280x720"
    design_dimensions = tuple(int(value) for value in design_size.split("x"))
    from html_production_models import HtmlProduceRequest
    from html_design_candidates import definition_identity, load_design, save_design
    from html_reference_package import assemble_reference, design_prompt, verify_package, PROMPT_VERSION
    from runtime_support import run_subprocess_killable

    selection = HtmlProduceRequest.model_validate(options or {})
    definitions = definition_identity(deps.repo_root)
    resumed = None
    if selection.design_candidate_key:
        resumed, package, accepted_image = load_design(
            run_dir=run_dir, contract=contract, key=selection.design_candidate_key,
            revision=revision, definitions=definitions, model_summary=model_summary,
        )
    plan = copy.deepcopy(resumed["plan"]) if resumed else generate_scene_plan(
        contract,
        run_dir=run_dir,
        repo_root=deps.repo_root,
        json_generator=deps.json_generator,
    )
    brief = copy.deepcopy(resumed["brief"]) if resumed else build_design_brief(
        plan,
        theme="neutral-baseline",
        asset_budget=1,
        effect_registry=load_effect_registry(deps.repo_root),
    )
    reused_assets = supplied_asset_ids(plan, contract, run_dir, deps.repo_root) if not selection.asset_instruction else set()
    new_asset_needs = [need for need in brief["asset_needs"] if need["id"] not in reused_assets]
    stage_record("plan", plan)
    stage_record("brief", brief)
    checkpoint()
    # Registered templates provide a reusable visual target; this is not a
    # fabricated image-model design. New generated assets are independently gated.
    candidate = {
        "name": "registered:" + plan["templateRef"]["id"],
        "sha256": plan["registered"]["catalog_sha256"],
        "keyframes": required_keyframes(plan),
    }
    references = []
    if resumed:
        candidate = copy.deepcopy(resumed["candidate"])
        references = package["references"] + [str(accepted_image)]
    elif new_asset_needs and provider is not None:
        package_path = run_dir / "planning/html_visual/reference-packages" / sha256_json(
            {"plan": plan, "brief": brief, "definitions": definitions})
        package = assemble_reference(plan, brief, repo_root=deps.repo_root,
                                     directory=package_path, runner=run_subprocess_killable)
        package["directory"] = str(package_path.relative_to(run_dir))
        references = package["references"]
        design_path = (
            run_dir
            / "planning/html_visual/candidates"
            / slide_id
            / "design-reference.png"
        )
        design_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = design_prompt(package, instruction=selection.design_instruction)
        request = {
            "prompt": prompt,
            "reference_paths": references,
            "brief_sha256": brief["sha256"],
            "model_config_hash": model_summary.get("image", {}).get("config_hash"),
            "reference_package_key": package["manifest"]["cacheKey"],
            "image_policy": {"quality": "low", "resolution_hint": "1K", "size": design_size, "transparent_background": False},
        }
        request["reference_sha256"] = [
            hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in references
        ]
        key = sha256_json(request)
        design_path = design_path.with_name("design-" + key + ".png")
        key_path = design_path.with_suffix(".request.json")
        if (
            not design_path.is_file()
            or not key_path.is_file()
            or json.loads(key_path.read_text(encoding="utf-8")).get("key") != key
            or json.loads(key_path.read_text(encoding="utf-8")).get("response_sha256") != hashlib.sha256(design_path.read_bytes()).hexdigest()
        ):
            image = provider(
                prompt,
                size=design_size,
                reference_paths=references,
                transparent_background=False,
            )
            from ai_provider_service import open_validated_image

            measured_image = open_validated_image(image)
            design_path.write_bytes(image)
            write_json_atomic(
                key_path,
                {
                    "key": key,
                    "prompt_version": PROMPT_VERSION,
                    "reference_package_key": package["manifest"]["cacheKey"],
                    "response_sha256": hashlib.sha256(image).hexdigest(),
                    "transparent_background": False,
                    "provider_boundary_called": True,
                    "requested_size": design_size,
                    "actual_size": list(measured_image.size),
                    "size_verified": measured_image.size == design_dimensions,
                    "reference_sha256": [
                        hashlib.sha256(Path(p).read_bytes()).hexdigest()
                        for p in references
                    ],
                },
            )
        candidate = {
            **candidate,
            "name": "generated-reference",
            "request_key": key,
            "sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
        }
        checkpoint()
        refreshed = verify_package(package_path)
        if refreshed["manifest"]["manifestSha256"] != package["manifest"]["manifestSha256"]:
            raise HtmlReviewError("请求期间参考包已变化", code="REFERENCE_PACKAGE_INVALID")
        if definition_identity(deps.repo_root) != definitions:
            raise HtmlReviewError("生成期间定义已变化，请重新提交", code="DESIGN_STALE", status_code=409)
        stage_record("design", candidate)
        return save_design(run_dir=run_dir, contract=contract, revision=revision,
                           definitions=definitions, model_summary=model_summary,
                           plan=plan, brief=brief, candidate=candidate,
                           package=package, design_path=design_path)
    elif selection.design_instruction:
        raise HtmlReviewError("纯代码页面无需图片设计修改", code="DESIGN_NOT_REQUIRED")
    freeze = freeze_design(
        brief,
        candidate,
        diff_notes="代码槽位为几何真值；生成参考只指导风格和独立主体，最终以静态截图审阅。",
    )
    resources_path = run_dir / "planning/html_visual/resources.json"
    resources = (
        json.loads(resources_path.read_text(encoding="utf-8"))
        if resources_path.is_file()
        else {"assets": []}
    )
    if selection.asset_instruction:
        from html_scene_editing import edit_path
        if edit_path(run_dir, slide_id).exists():
            raise HtmlReviewError("此页有人工作品覆盖，请先检查对象编辑；素材返工不会自动替换人工资源", code="MANUAL_EDIT_CONFLICT", status_code=409)
    for need in new_asset_needs:
        if provider is None:
            raise HtmlReviewError(
                "独立资产需要配置图片服务", code="IMAGE_PROVIDER_MISSING"
            )
        entry = produce_asset(
            {
                "id": need["id"],
                "role": need["role"],
                "need": need["need"],
                "prompt": need["need"] + "。只用黑灰白，匹配设计参考的材质和光照。独立主体，透明底，无文字标签，完整边界。" + ("本轮主体修改方向：" + selection.asset_instruction if selection.asset_instruction else ""),
                "transparent_background": True,
                "size": "1024x1024",
                "reference_sha256": [
                    hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in references
                ],
                "model_config_hash": model_summary.get("image", {}).get("config_hash"),
                "generation_parameters": {"quality": "low", "resolution_hint": "1K"},
            },
            HtmlAssetDependencies(
                lambda prompt, **kw: provider(
                    prompt,
                    **kw,
                    reference_paths=references,
                    transparent_background=True,
                ),
                run_dir / "planning/html_visual/assets",
            ),
        )
        entry["id"] = (
            "project-"
            + hashlib.sha256(f"{slide_id}:{entry['id']}".encode()).hexdigest()[:32]
        )
        entry.pop("cache", None)  # Transport cache telemetry is not author input.
        original_id = need["id"]
        for asset in plan["assets"]:
            if asset["id"] == original_id:
                asset["id"] = entry["id"]
        entry["file"] = "planning/html_visual/assets/" + entry["file"]
        # This default is a generic subject center, never a scientific feature.
        if not entry["anchors"]:
            # A generic subject center, not a guessed scientific detail. Users
            # inspect this target in the actual preview before approval.
            x, y, right, bottom = entry["alpha_bbox"]
            px, py = (x + right) // 2, (y + bottom) // 2
            entry["anchors"] = [
                {
                    "id": "focus",
                    "x": px,
                    "y": py,
                    "nx": px / entry["size"]["width"],
                    "ny": py / entry["size"]["height"],
                }
            ]
            entry["anchor_semantics"] = "derived_subject_center; requires visual review"
        resources["assets"] = [
            a for a in resources["assets"] if a["id"] != entry["id"]
        ] + [entry]
        stage_record("asset:" + original_id, entry)
    relation_resolutions: list[dict] = []
    scene, binding = compile_plan(
        plan, contract, load_template_catalog(deps.repo_root), relation_resolutions,
    )
    stage_record("compile", {"scene": scene, "binding": binding,
                             "relation_resolutions": relation_resolutions})
    checkpoint()
    directory = run_dir / "planning/html_visual"
    # Candidate resources/definitions stay separate until review succeeds; a
    # failed candidate must not overwrite the old approved resource manifest.
    candidate_dir = directory / "candidates" / slide_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(candidate_dir / "plan.json", plan)
    write_json_atomic(candidate_dir / "brief.json", brief)
    write_json_atomic(candidate_dir / "freeze.json", freeze)
    write_json_atomic(candidate_dir / "models.json", model_summary)
    # Review uses a temporary project resource root, retaining file locations.
    with project_artifact_lock(run_dir):
        checkpoint()
        from html_visual_store import _read_revision, HtmlVisualConflict
        from html_scene_editing import edit_path, read_json, merge_manual_edits, _validate_binding

        current_revision = _read_revision(run_dir)["revision"]
        if current_revision != revision:
            raise HtmlVisualConflict(revision, current_revision)
        if definition_identity(deps.repo_root) != definitions:
            raise HtmlReviewError("生成期间定义已变化，请重新提交", code="DESIGN_STALE", status_code=409)
        if resumed:
            load_design(run_dir=run_dir, contract=contract, key=selection.design_candidate_key,
                        revision=revision, definitions=definitions, model_summary=model_summary)
        # Reapply only explicit manual deltas to stable IDs, before reviewing.
        # Missing/changed targets keep the candidate and fail without touching
        # the current scene, private resources, binding, or approval.
        manual = read_json(edit_path(run_dir, slide_id))
        merged = merge_manual_edits(scene, binding, manual)
        if merged["conflicts"]:
            write_json_atomic(candidate_dir / "manual-conflicts.json", merged["conflicts"])
            raise HtmlReviewError(
                "重新规划与人工修改冲突，请检查保留的候选。",
                status_code=409,
                code="MANUAL_EDIT_CONFLICT",
            )
        scene, binding = merged["scene"], merged["binding"]
        _validate_binding(binding, scene, contract.get("narration_beats", []))
        # Assets added while generation was in flight must never disappear.
        current_resources = read_json(resources_path, {"assets": []})
        generated_ids = {a["id"] for a in resources.get("assets", [])}
        resources["assets"] += [
            a for a in current_resources.get("assets", []) if a["id"] not in generated_ids
        ]
        rollback_paths = [
            resources_path,
            scene_path(run_dir, slide_id),
            revision_path(run_dir),
            directory / f"binding-{slide_id}.json",
            directory / f"plan-{slide_id}.json",
            directory / f"production-provenance-{slide_id}.json",
            candidate_dir / "design-acceptance.json",
        ]
        previous = {p: p.read_bytes() if p.is_file() else None for p in rollback_paths}
        committed = False
        try:
            if resources.get("assets"):
                write_json_atomic(resources_path, resources)
            report = review_scene(scene, run_dir=run_dir, deps=deps)
            layout_agent = None
            if not report.get("passed") and "CONTENT_CAPACITY_EXCEEDED" in str(report.get("message", "")):
                from html_candidate_agent import repair_candidate

                repaired = repair_candidate(scene, binding, run_dir=run_dir, deps=deps,
                                            manual=manual, checkpoint=checkpoint, progress=progress_record)
                scene, binding, report = repaired["scene"], repaired["binding"], repaired["report"]
                layout_agent = repaired["summary"]
            if not report.get("passed"):
                raise HtmlReviewError(
                    "候选场景静态审阅未通过："
                    + str(report.get("message") or report.get("code")),
                    status_code=422,
                    code="CANDIDATE_REJECTED",
                )
            if len(candidate["keyframes"]) > 1:
                from html_pptx_snapshot import (
                    HtmlSnapshotDependencies,
                    render_snapshots,
                )

                times = [0, scene["durationMs"] // 2, scene["durationMs"]]
                frame_paths = render_snapshots(
                    scene,
                    times,
                    candidate_dir / "keyframes",
                    deps=HtmlSnapshotDependencies(
                        repo_root=deps.repo_root,
                        run_dir=run_dir,
                        run_subprocess_bounded=deps.run_subprocess_bounded,
                    ),
                )
                candidate["keyframes"] = [
                    {
                        **frame,
                        "timeMs": t,
                        "file": str(p.relative_to(run_dir)),
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    }
                    for frame, t, p in zip(candidate["keyframes"], times, frame_paths)
                ]
                freeze = freeze_design(
                    brief,
                    candidate,
                    diff_notes="实际关键帧由共享播放器生成；参考图只指导外观，槽位为几何真值。",
                )
                write_json_atomic(candidate_dir / "freeze.json", freeze)
            checkpoint()
            stage_record("review", report)
            from html_rebuild_plan import scene_rebuild
            rebuild_plan = scene_rebuild(slide_id, original_scene, scene, original_binding, binding)
            stage_record("rebuild", rebuild_plan)
            from html_visual_store import _read_revision, HtmlVisualConflict

            current_revision = _read_revision(run_dir)["revision"]
            if current_revision != revision:
                raise HtmlVisualConflict(revision, current_revision)
            if definition_identity(deps.repo_root) != definitions:
                raise HtmlReviewError("修复期间定义已变化，请重新提交", code="DESIGN_STALE", status_code=409)
            provenance = {"format": "hps.html.production_provenance", "version": "0.1.0",
                          "model_summary": model_summary, "themeRef": scene["themeRef"],
                          "design_candidate_key": selection.design_candidate_key,
                          "files": [], "supplied_asset_ids": sorted(reused_assets),
                          "layout_agent": layout_agent,
                          "plan_relation_resolutions": relation_resolutions}
            if resumed:
                pack_root = run_dir / resumed["reference_package"]
                paths = [pack_root / "manifest.json", accepted_image]
                paths += [pack_root / f["path"] for f in package["manifest"]["files"]]
                provenance["reference_package_key"] = package["manifest"]["cacheKey"]
                provenance["files"] = [{"path": str(p.relative_to(run_dir)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
            from html_visual_store import _document_bytes
            def metadata_bytes(value):
                return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            pending = {
                scene_path(run_dir, slide_id): _document_bytes(scene),
                directory / f"binding-{slide_id}.json": metadata_bytes(binding),
                directory / f"plan-{slide_id}.json": metadata_bytes(plan),
                directory / f"production-provenance-{slide_id}.json": metadata_bytes(provenance),
                resources_path: resources_path.read_bytes() if resources_path.exists() else None,
            }
            material_paths = [resources_path, directory / f"binding-{slide_id}.json",
                              directory / f"plan-{slide_id}.json",
                              directory / f"production-provenance-{slide_id}.json"]
            scene_changed = pending[scene_path(run_dir, slide_id)] != previous[scene_path(run_dir, slide_id)]
            changed = scene_changed or any(pending[p] != previous[p] for p in material_paths)
            result = {"revision": revision + int(changed), "changed": changed,
                      "sha256": hashlib.sha256(pending[scene_path(run_dir, slide_id)]).hexdigest()}
            revision_state = {"revision": result["revision"], "last_sha256": result["sha256"]}
            pending[revision_path(run_dir)] = (
                json.dumps(revision_state, ensure_ascii=False, indent=2).encode("utf-8") if scene_changed
                else metadata_bytes(revision_state) if changed else previous[revision_path(run_dir)]
            )
            if resumed:
                pending[candidate_dir / "design-acceptance.json"] = metadata_bytes({
                    "format": "hps.html.design_acceptance", "version": "0.1.0",
                    "design_candidate_key": selection.design_candidate_key,
                    "scope": "design reference only; actual HTML visual approval remains required",
                    "saved_revision": result["revision"], "scene_sha256": result["sha256"],
                    "provenance_sha256": hashlib.sha256(pending[directory / f"production-provenance-{slide_id}.json"]).hexdigest(),
                })
            else:
                pending[candidate_dir / "design-acceptance.json"] = previous[candidate_dir / "design-acceptance.json"]
            output = {
                "design_candidate_key": selection.design_candidate_key,
                "scene": scene, "plan": plan, "review": report,
                "layout_agent": layout_agent, "saved": result,
                "rebuild_plan": rebuild_plan,
                "message": "已生成实际场景；请查看截图后批准。",
            }
            # Receipt seals all author files while the author lock is held.
            commit_paths = list(rollback_paths)
            if report.get("screenshot"):
                from html_build_snapshot import safe_file
                commit_paths.append(safe_file(run_dir, report["screenshot"].replace("\\", "/")))
            for asset in resources.get("assets", []):
                asset_file = asset.get("file")
                relative = asset_file if isinstance(asset_file, str) else (asset_file or {}).get("path")
                if relative and relative.replace("\\", "/").startswith(("planning/", "project/")):
                    from html_build_snapshot import safe_file
                    commit_paths.append(safe_file(run_dir, relative.replace("\\", "/").removeprefix("project/")))
            from html_build_snapshot import safe_file
            commit_paths.extend(safe_file(run_dir, item["path"].replace("\\", "/")) for item in provenance["files"])
            # Write-ahead expected hashes cover the gap before the final seal.
            commit_record(output, commit_paths, expected=pending)
            saved_scene = save_scene(run_dir, slide_id, scene, revision, lock=project_artifact_lock,
                                     allow_manual_replace=bool(manual))
            for path in material_paths[1:]:
                _atomic_write_bytes(path, pending[path])
            if changed and not saved_scene["changed"]:
                _atomic_write_bytes(revision_path(run_dir), pending[revision_path(run_dir)])
            if resumed:
                _atomic_write_bytes(candidate_dir / "design-acceptance.json", pending[candidate_dir / "design-acceptance.json"])
            commit_record(output, commit_paths)
            committed = True
        finally:
            if not committed:
                for path, payload in previous.items():
                    if payload is None:
                        path.unlink(missing_ok=True)
                    else:
                        _atomic_write_bytes(path, payload)
    return output
