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


def compile_plan(plan: dict, contract: dict, catalog: dict) -> tuple[dict, dict]:
    """Content fills registered slots; IDs and time are resolved by code."""
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
        "themeRef": {"id": "soft-science", "version": "0.2.0"},
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
) -> dict:
    from html_storyboard_planning import load_template_catalog

    slide_id = validate_slide_id(contract["slide_id"])
    with project_artifact_lock(run_dir):
        from html_visual_store import _read_revision

        revision = _read_revision(run_dir)["revision"]
    checkpoint()
    plan = generate_scene_plan(
        contract,
        run_dir=run_dir,
        repo_root=deps.repo_root,
        json_generator=deps.json_generator,
    )
    brief = build_design_brief(
        plan,
        theme="soft-science",
        asset_budget=1,
        effect_registry=load_effect_registry(deps.repo_root),
    )
    checkpoint()
    # Registered templates provide a reusable visual target; this is not a
    # fabricated image-model design. New generated assets are independently gated.
    candidate = {
        "name": "registered:" + plan["templateRef"]["id"],
        "sha256": plan["registered"]["catalog_sha256"],
        "keyframes": required_keyframes(plan),
    }
    references = []
    if brief["asset_needs"] and provider is not None:
        from runtime_support import run_subprocess_killable

        atlas_result = run_subprocess_killable(
            ["node", str(deps.repo_root / "html_engine/visual/tools/effect-cache.cjs")],
            cwd=str(deps.repo_root / "html_engine"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout_sec=120,
        )
        if atlas_result.returncode:
            raise HtmlReviewError("效果参考图构建失败")
        atlas = json.loads(atlas_result.stdout)
        references = [
            str(deps.repo_root / "html_engine/visual/effects/cache" / atlas["file"])
        ]
        design_path = (
            run_dir
            / "planning/html_visual/candidates"
            / slide_id
            / "design-reference.png"
        )
        design_path.parent.mkdir(parents=True, exist_ok=True)
        design_input = {
            "templateRef": plan["templateRef"],
            "layoutRef": plan["layoutRef"],
            "slots": plan["slots"],
            "asset_needs": brief["asset_needs"],
            "effects": [
                {"id": e["id"], "backend": e["backend"]} for e in brief["effects"]
            ],
        }
        design_prompt = (
            "PromptVersion: html-design-reference/0.1.0。科普画面设计参考。遵守附件效果库，文字/关系线/图标/卡片只能使用"
            "附件标注的 CSS/SVG/Canvas 效果；独立主体插画为图片资产。"
            "16:9，底部1/9留白给字幕。不要额外栏目、品牌和来源页脚。"
            "最终结构由下面的注册槽位计划确定："
            + json.dumps(design_input, ensure_ascii=False)
        )
        request = {
            "prompt": design_prompt,
            "reference_paths": references,
            "brief_sha256": brief["sha256"],
        }
        request["reference_sha256"] = [
            hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in references
        ]
        key = sha256_json(request)
        key_path = design_path.with_suffix(".request.json")
        if (
            not design_path.is_file()
            or not key_path.is_file()
            or json.loads(key_path.read_text(encoding="utf-8")).get("key") != key
        ):
            image = provider(
                design_prompt,
                size="1536x1024",
                reference_paths=references,
                transparent_background=False,
            )
            from ai_provider_service import open_validated_image

            open_validated_image(image)
            design_path.write_bytes(image)
            write_json_atomic(
                key_path,
                {
                    "key": key,
                    "reference_sha256": [
                        hashlib.sha256(Path(p).read_bytes()).hexdigest()
                        for p in references
                    ],
                },
            )
        references.append(str(design_path))
        candidate = {
            **candidate,
            "name": "generated-reference",
            "sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
        }
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
    for need in brief["asset_needs"]:
        if provider is None:
            raise HtmlReviewError(
                "独立资产需要配置图片服务", code="IMAGE_PROVIDER_MISSING"
            )
        entry = produce_asset(
            {
                "id": need["id"],
                "role": need["role"],
                "need": need["need"],
                "prompt": need["need"] + "。独立主体，透明底，无文字标签，完整边界。",
                "transparent_background": True,
                "size": "1024x1024",
                "reference_sha256": [
                    hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in references
                ],
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
    scene, binding = compile_plan(plan, contract, load_template_catalog(deps.repo_root))
    checkpoint()
    directory = run_dir / "planning/html_visual"
    # Candidate resources/definitions stay separate until review succeeds; a
    # failed candidate must not overwrite the old approved resource manifest.
    candidate_dir = directory / "candidates" / slide_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(candidate_dir / "plan.json", plan)
    write_json_atomic(candidate_dir / "brief.json", brief)
    write_json_atomic(candidate_dir / "freeze.json", freeze)
    # Review uses a temporary project resource root, retaining file locations.
    with project_artifact_lock(run_dir):
        checkpoint()
        rollback_paths = [
            resources_path,
            scene_path(run_dir, slide_id),
            revision_path(run_dir),
            directory / f"binding-{slide_id}.json",
            directory / f"plan-{slide_id}.json",
        ]
        previous = {p: p.read_bytes() if p.is_file() else None for p in rollback_paths}
        committed = False
        try:
            if resources.get("assets"):
                write_json_atomic(resources_path, resources)
            report = review_scene(scene, run_dir=run_dir, deps=deps)
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
            from html_visual_store import _read_revision, HtmlVisualConflict

            current_revision = _read_revision(run_dir)["revision"]
            if current_revision != revision:
                raise HtmlVisualConflict(revision, current_revision)
            result = save_scene(
                run_dir, slide_id, scene, revision, lock=project_artifact_lock
            )
            write_json_atomic(directory / f"binding-{slide_id}.json", binding)
            write_json_atomic(directory / f"plan-{slide_id}.json", plan)
            committed = True
        finally:
            if not committed:
                for path, payload in previous.items():
                    if payload is None:
                        path.unlink(missing_ok=True)
                    else:
                        _atomic_write_bytes(path, payload)
    return {
        "scene": scene,
        "plan": plan,
        "review": report,
        "saved": result,
        "message": "已生成实际场景；请查看截图后批准。",
    }
