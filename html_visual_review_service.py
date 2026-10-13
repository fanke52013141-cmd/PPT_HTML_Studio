"""Compile & static review service for the HTML backend (C04).

Wires the C01–C03 pure layers into one application-facing service:

- plan generation through the shared configured LLM (injected callable so
  daily tests use stubs) with ONE bounded repair round; structure
  failures save diagnostics and never widen the validators
- brief assembly via ``html_design_brief`` (registry-gated effects)
- static review: schema/resource validation plus real browser
  measurement and screenshot through the shared preview bundle
  (``html_engine/tools/review-scene.cjs``); text overflow, missing
  resources, and prepare failures return object-level diagnostics
- approval records bound to scene/theme/template/layout/runtime hashes;
  any related change invalidates the previous approval (AC04 gate for
  the html backend)

Storage layout under ``planning/html_visual/``: ``records/`` (model
generation evidence: request-context hashes + response hashes, AC06/AC07),
``review/`` (reports + screenshots), ``approval-<slide>.json``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from html_design_brief import load_effect_registry
from html_storyboard_planning import (
    HtmlScenePlanError,
    load_template_catalog,
    normalize_html_scene_plan,
    plan_evidence,
)

REVIEW_DIR = Path("planning") / "html_visual" / "review"
RECORDS_DIR = Path("planning") / "html_visual" / "records"
APPROVAL_PREFIX = "planning/html_visual/approval-"
REVIEW_SCRIPT = Path("html_engine") / "tools" / "review-scene.cjs"
BUNDLE_PATH = Path("html_engine") / "visual" / "preview" / "player.js"
MAX_REVIEW_PIXELS = 4_000_000


class HtmlReviewError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "HTML_REVIEW_ERROR",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class HtmlReviewDependencies:
    """json_generator(**kwargs) -> dict; the real binding wraps
    ``json_llm_service.generate_json_with_configured_llm`` (configured in
    server.py). Tests inject a stub."""

    repo_root: Path
    json_generator: Callable[..., Dict[str, Any]]
    run_subprocess_bounded: Callable[..., subprocess.CompletedProcess] = __import__(
        "runtime_support"
    ).run_subprocess_killable
    node_bin: str = "node"
    review_script: Path = REVIEW_SCRIPT
    stage_timeout_sec: float = 240.0


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _registered_capabilities(repo_root: Path) -> Dict[str, Any]:
    catalog = load_template_catalog(repo_root)
    effects = load_effect_registry(repo_root)
    schema = json.loads(
        (repo_root / "html_engine/visual/schema.json").read_text(encoding="utf-8")
    )
    def resolved(value):
        if isinstance(value, dict):
            if "$ref" in value:
                return resolved(schema["$defs"][value["$ref"].split("/")[-1]])
            return {k: resolved(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolved(v) for v in value]
        return value
    available_kinds = {kind for template in catalog["templates"].values() for rule in template["slots"].values() for kind in rule["kinds"]}
    node_contracts = {
        item["properties"]["type"]["const"]: {
            "required": [
                k for k in item["required"] if k not in ("id", "slot", "type")
            ],
            "properties": {
                k: v
                for k, v in item["properties"].items()
                if k not in ("id", "slot", "type", "presentation")
            },
        }
        for item in schema["$defs"]["node"]["oneOf"]
        if item["properties"]["type"]["const"] in available_kinds
    }
    node_contracts = resolved(node_contracts)
    return {"catalog": catalog, "effects": effects, "node_contracts": node_contracts}


def _plan_schema_hint(plan_version: str = "0.1.0") -> str:
    if plan_version == "0.2.0":
        return (
            '输出 JSON：{version:"0.2.0",slide_id,templateRef:{id,version},'
            'slots:{槽位名:{kind,...内容}},objects:[{id,slot,kind,icon?,exit?,transitional?}],'
            'beats:[{id,visualIntent,targets:[{objectId,role:instructional|context|decorative,meaning}],'
            'actions:[{actionKey,objectId,type:enter|emphasize,expectedState:{visible:true,meaning}}],'
            'narration_only?:false,narration_only_reason?}],'
            'assets:[{id,role,render_owner:code|image_asset,need?,slot?}]}。'
        )
    return (
        "输出 JSON 对象：{slide_id, templateRef:{id,version}, slots:{槽位名:"
        "{kind,...内容}}, objects:[{id,slot,kind,icon?,exit?,transitional?}], "
        "beats:[{id, target:{objectId,action enter|emphasize} | narration_only:true}], "
        "assets:[{id,role,render_owner code|image_asset,need?,slot?}]}。"
        "只能使用列出的模板 id、槽位与图标；每个讲稿语块必须有一条映射。"
    )


def build_plan_generation_prompts(
    contract_slide: Dict[str, Any],
    capabilities: Dict[str, Any],
    brief: Optional[Dict[str, Any]] = None,
    *,
    plan_version: str = "0.1.0",
) -> Dict[str, str]:
    """AC06: the model request context lists registered capabilities only."""
    templates = capabilities["catalog"]["templates"]
    template_lines = []
    for template_id in sorted(templates):
        template = templates[template_id]
        slots = ", ".join(
            f"{name}[{'/'.join(rule.get('kinds') or [])}"
            f"{'*' if rule.get('required') else ''}]"
            for name, rule in sorted((template.get("slots") or {}).items())
        )
        template_lines.append(
            f"- {template_id}@{template.get('version')} "
            f"结构 {template.get('structure')}：{slots}"
        )
    system = (
        "你是课程场景规划器。只输出一个 JSON 对象，把讲稿语块映射到受约束模板的"
        "槽位与对象上；不得输出 HTML/CSS/JS，不得使用未列出的模板、槽位、图标或"
        "动作。语块映射必须覆盖全部讲稿语块。\n已注册模板与槽位：\n"
        + "\n".join(template_lines)
        + "\n已注册图标："
        + ", ".join(capabilities["catalog"]["icons"])
        + "\n已注册效果："
        + ", ".join(sorted(capabilities["effects"]["effects"]))
        + "\nPromptVersion:html-plan-0.4.0。每个内容槽位必须在 objects 中有一个同 kind 对象，"
        "beats.target.objectId 只能引用本次对象；同一动作只绑定一个语块。"
        "图片 assetRef 可引用用户给出的已有资产；需新资产时在 assets 声明 image_asset 和 need，"
        "只生成独立主体，不生成整页。text 的 runs 每项为{text,emphasis}。"
        + "\n必须输出的顶层结构：" + _plan_schema_hint()
        + '\n格式示例片段："templateRef":{"id":"已选模板ID","version":"0.1.0"}, '
          '"slots":{"槽位ID":{"kind":"text","role":"callout","runs":[{"text":"本页原文","emphasis":false}]}}, '
          '"objects":[{"id":"稳定对象ID","slot":"槽位ID","kind":"text"}], '
          '"beats":[{"id":"输入语块ID","target":{"objectId":"稳定对象ID","action":"enter"}}]。'
          '这只是字段示例，替换示例ID并补齐全部必需槽位。不要输出template/content/actions等替代字段；'
          'slots存内容，objects只存身份/槽位/kind，beats映射单一已注册动作。'
        + "\n槽位内容字段契约（kind 对应 type，不输出 id/slot/type）："
        + json.dumps(capabilities.get("node_contracts", {}), ensure_ascii=False)
    )
    if plan_version == "0.2.0":
        system = (
            "PromptVersion:html-plan-0.5.0。你是讲稿驱动的课程视觉规划器，只输出一个 JSON 对象。"
            "spoken_text 是不可改写的语义真值；视觉说明、设计参考不得覆盖原句。"
            "不得输出 HTML/CSS/JS、猜测像素/音频时长，或使用未列出的模板、槽位、图标、动作。"
            "按讲稿逐语块表达含义，而不只是覆盖 ID。visualIntent 说明要解释的具体关系/状态；"
            "targets 逐个说明对象表达什么及其角色，instructional 为讲解对象、context 为背景、"
            "decorative 为装饰。每个非纯旁白语块至少有一个 instructional 目标和自身动作。"
            "动作可一对多，同对象可跨语块重复强调；每次动作给出整页唯一、可复用的 actionKey，"
            "只允许 enter/emphasize，objectId 必须属于本语块 targets。expectedState 声明动作后"
            "对象可见和具体表达含义，不能仅写‘强调图片’。装饰不得承担讲解动作。"
            "无法用注册能力表达时不得虚构图内可独立运动对象。纯旁白须明确 narration_only:true、"
            "narration_only_reason，并将 targets/actions 设为空；不得把能力不足默认改成纯旁白。"
            "不要输出 spoken_text、散列或 actionId，宿主从权威讲稿与 actionKey 确定性生成。"
            "每个内容槽位必须在 objects 中有一个同 kind 对象。图片只生成独立主体；"
            "已有资源引用保持身份/版本，新图片需求声明 image_asset 和 need。"
            "这些是计划声明，不能自称语义 QA 或用户批准已通过。\n已注册模板与槽位：\n"
            + "\n".join(template_lines)
            + "\n已注册图标：" + ", ".join(capabilities["catalog"]["icons"])
            + "\n必须输出的顶层结构：" + _plan_schema_hint(plan_version)
            + '\n语块示例：{"id":"输入语块ID","visualIntent":"说明液态水放热变为冰",'
              '"targets":[{"objectId":"本页对象ID","role":"instructional","meaning":"液态到固态关系"}],'
              '"actions":[{"actionKey":"freezing-relation-enter","objectId":"本页对象ID","type":"enter",'
              '"expectedState":{"visible":true,"meaning":"显示液态水→固态冰及放热说明"}}]}。'
              '示例只说明字段，ID必须引用本次输入或本页声明。slots存内容，objects存身份；'
              'beats存意图、目标和动作。'
            + "\n槽位内容字段契约（kind 对应 type，不输出 id/slot/type）："
            + json.dumps(capabilities.get("node_contracts", {}), ensure_ascii=False)
        )
    user = json.dumps(
        {
            "slide": {
                "slide_id": contract_slide.get("slide_id"),
                "visual_groups": contract_slide.get("visual_groups") or [],
                "narration_beats": (
                    [{"id": b.get("id"), "spoken_text": b.get("spoken_text")}
                     for b in contract_slide.get("narration_beats") or [] if isinstance(b, dict)]
                    if plan_version == "0.2.0" else contract_slide.get("narration_beats") or []
                ),
            },
            "design_brief": brief,
        },
        ensure_ascii=False,
    )
    return {
        "system_prompt": system,
        "user_prompt": user,
        "schema_hint": _plan_schema_hint(plan_version),
    }


def generate_scene_plan(
    contract_slide: Dict[str, Any],
    *,
    run_dir: str | Path,
    repo_root: Path,
    json_generator: Callable[..., Dict[str, Any]],
    brief: Optional[Dict[str, Any]] = None,
    artifact_prefix: Optional[str] = None,
    plan_version: str = "0.1.0",
) -> Dict[str, Any]:
    """Model → validated scene plan, with one bounded repair round.

    Evidence (AC06/AC07) is written before the verdict: the request
    context hashes (catalog/registry/brief) and the response hash land in
    ``planning/html_visual/records/plan-<slide>.json`` together with the
    final diagnostics. A model output that fails normalization twice is
    an error — validators never bend toward the model.
    """
    if plan_version not in ("0.1.0", "0.2.0"):
        raise HtmlReviewError("未知规划版本", code="PLAN_VERSION_MISMATCH", status_code=422)
    if plan_version == "0.2.0":
        # Fail before a paid request when authority is absent or malformed.
        from html_narration_semantics import NarrationSemanticError, validate_narration_source

        try:
            validate_narration_source(contract_slide)
        except NarrationSemanticError as exc:
            raise HtmlReviewError(str(exc), code=exc.code, status_code=422) from exc
    capabilities = _registered_capabilities(Path(repo_root))
    prompts = build_plan_generation_prompts(contract_slide, capabilities, brief, plan_version=plan_version)
    version_suffix = "_v0_2_0" if plan_version == "0.2.0" else ""
    prefix = artifact_prefix or f"html_scene_plan_{contract_slide.get('slide_id')}{version_suffix}"
    attempts: list[Dict[str, Any]] = []
    plan = None
    previous_response = None
    last_failure: Optional[HtmlScenePlanError] = None
    for round_index in (1, 2):
        repair_note = ""
        if attempts:
            repair_note = (
                f"上一次输出未通过校验：{last_failure.code} {last_failure}。"
                "请严格按已注册模板/槽位/图标重新输出完整 JSON。"
            )
            if plan_version == "0.2.0":
                # The dynamic diagnostic and rejected plan are already in user input.
                repair_note = ""
        response = json_generator(
            system_prompt=prompts["system_prompt"] + repair_note,
            user_prompt=(prompts["user_prompt"] if previous_response is None else json.dumps({"task":json.loads(prompts["user_prompt"]),"invalid_plan":previous_response,"diagnostic":{"code":last_failure.code,"message":str(last_failure)}},ensure_ascii=False)),
            run_dir=str(run_dir),
            artifact_prefix=prefix,
            schema_hint=prompts["schema_hint"],
        )
        previous_response = response
        _write_json(Path(run_dir) / REVIEW_DIR / f"{prefix}-round-{round_index}.json", {"prompts": prompts, "response": response})
        response_sha256 = _sha256_bytes(
            json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        try:
            plan = normalize_html_scene_plan(
                response,
                capabilities["catalog"],
                contract_slide=contract_slide,
                expected_version=plan_version,
            )
            attempts.append(
                {
                    "round": round_index,
                    "response_sha256": response_sha256,
                    "accepted": True,
                }
            )
            break
        except HtmlScenePlanError as exc:
            last_failure = exc
            attempts.append(
                {
                    "round": round_index,
                    "response_sha256": response_sha256,
                    "accepted": False,
                    "diagnostic_code": exc.code,
                    "diagnostic": str(exc),
                }
            )
    record = {
        "format": "hps.html.plan_generation",
        "version": "0.1.0",
        "slide_id": contract_slide.get("slide_id"),
        "artifact_prefix": prefix,
        "request_context": {
            "plan_version": plan_version,
            "catalog_sha256": capabilities["catalog"]["sha256"],
            "effect_registry_sha256": capabilities["effects"]["sha256"],
            "brief_sha256": (brief or {}).get("sha256"),
            "registered_templates": sorted(capabilities["catalog"]["templates"]),
            "registered_icons": capabilities["catalog"]["icons"],
        },
        "attempts": attempts,
        "accepted": plan is not None,
        "plan_evidence": plan_evidence(plan) if plan else None,
    }
    records_dir = Path(run_dir) / RECORDS_DIR
    record_suffix = "-v0.2.0" if plan_version == "0.2.0" else ""
    _write_json(records_dir / f"plan-{contract_slide.get('slide_id')}{record_suffix}.json", record)
    if plan is None:
        raise HtmlReviewError(
            "模型输出两次未通过注册能力校验；诊断已保存，请调整后重试："
            f"{last_failure.code} {last_failure}",
            status_code=422,
            code="PLAN_GENERATION_REJECTED",
        )
    return plan


# ------------------------------------------------------------- static review


def resource_environment(run_dir):
    import os

    env = dict(os.environ)
    resources = Path(run_dir) / "planning/html_visual/resources.json"
    env.pop("HPS_HTML_RESOURCES", None)
    if resources.is_file():
        env["HPS_HTML_RESOURCES"] = str(resources.resolve())
    return env


def review_scene(
    scene: Dict[str, Any],
    *,
    run_dir: str | Path,
    deps: HtmlReviewDependencies,
    diagnostic: bool = False,
) -> Dict[str, Any]:
    """Compile + measure + screenshot one scene via the shared bundle."""
    from html_visual_store import validate_slide_id, HtmlVisualError

    try:
        validate_slide_id(scene.get("id"))
    except HtmlVisualError as exc:
        raise HtmlReviewError(str(exc), status_code=400) from exc
    run_dir = Path(run_dir)
    review_dir = run_dir / REVIEW_DIR
    review_dir.mkdir(parents=True, exist_ok=True)
    scene_tmp = review_dir / f"scene-{scene.get('id')}.under-review.json"
    report_path = review_dir / f"report-{scene.get('id')}.json"
    screenshot_path = review_dir / f"review-{scene.get('id')}.png"
    screenshot_path.unlink(missing_ok=True)  # Never reuse a previous passing screenshot.
    scene_tmp.write_text(
        json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    result = deps.run_subprocess_bounded(
        [
            deps.node_bin,
            str(deps.repo_root / deps.review_script),
            str(scene_tmp),
            str(report_path),
            str(screenshot_path),
        ],
        cwd=str(deps.repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout_sec=deps.stage_timeout_sec,
        env={**resource_environment(run_dir), "HPS_CANDIDATE_DIAGNOSTIC": "1"}
        if diagnostic else {k: v for k, v in resource_environment(run_dir).items()
                            if k != "HPS_CANDIDATE_DIAGNOSTIC"},
    )
    if result.returncode != 0:
        raise HtmlReviewError(
            "静态审阅脚本失败：" + (result.stderr or "")[-400:],
            status_code=500,
            code="REVIEW_SCRIPT_FAILED",
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["screenshot"] = str(screenshot_path.relative_to(run_dir))
    report["scene_sha256"] = _sha256_bytes(
        json.dumps(scene, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    _write_json(report_path, report)
    scene_tmp.unlink(missing_ok=True)
    return report


# ----------------------------------------------------------------- approval


def _runtime_fingerprint(deps: HtmlReviewDependencies) -> Dict[str, Any]:
    bundle = deps.repo_root / BUNDLE_PATH
    payload = bundle.read_bytes() if bundle.is_file() else b""
    return {
        "bundle_sha256": _sha256_bytes(payload),
        "font": "Microsoft YaHei",
    }


def approve_scene(
    scene: Dict[str, Any],
    *,
    run_dir: str | Path,
    deps: HtmlReviewDependencies,
    reviewer: str = "user",
) -> Dict[str, Any]:
    """Freeze an approval bound to every hash a later change could touch."""
    report = review_scene(scene, run_dir=run_dir, deps=deps)
    if not report.get("passed"):
        raise HtmlReviewError(
            "静态审阅未通过，不能批准："
            + str(report.get("code") or report.get("pageErrors") or "unknown"),
            status_code=409,
            code="APPROVAL_REVIEW_FAILED",
        )
    approval = {
        "format": "hps.html.scene_approval",
        "version": "0.1.0",
        "slide_id": scene.get("id"),
        "scene_sha256": report["scene_sha256"],
        "theme": scene.get("themeRef"),
        "layout": scene.get("layoutRef"),
        "template": scene.get("templateRef"),
        "assets": sorted(
            {
                json.dumps(node["assetRef"], ensure_ascii=False, sort_keys=True)
                for node in scene.get("nodes", [])
                if node.get("type") == "image"
            }
        ),
        "runtime": _runtime_fingerprint(deps),
        "review_sha256": _sha256_bytes(
            json.dumps(report, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ),
        "reviewer": reviewer,
    }
    from html_input_manifest import resolved_scene_inputs

    approval["resolved_input_digest"] = resolved_scene_inputs(
        scene, run_dir, deps.repo_root
    )["digest"]
    approval["sha256"] = _sha256_bytes(
        json.dumps(approval, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    path = Path(run_dir) / f"{APPROVAL_PREFIX}{scene.get('id')}.json"
    _write_json(path, approval)
    return approval


def approval_status(
    scene: Optional[Dict[str, Any]],
    *,
    run_dir: str | Path,
    deps: HtmlReviewDependencies,
    slide_id: str,
) -> Dict[str, Any]:
    """Recompute approval validity; any related change invalidates it."""
    from html_visual_store import validate_slide_id

    slide_id = validate_slide_id(slide_id)
    path = Path(run_dir) / f"{APPROVAL_PREFIX}{slide_id}.json"
    if not path.is_file():
        return {"valid": False, "reason": "no_approval"}
    approval = json.loads(path.read_text(encoding="utf-8"))
    if scene is None:
        return {"valid": False, "approval": approval, "reason": "scene_missing"}
    # Most specific reason first: a theme swap also changes the whole-scene
    # hash, but naming the real cause is what the user needs.
    if scene.get("themeRef") != approval.get("theme"):
        return {"valid": False, "reason": "theme_changed", "approval": approval}
    if scene.get("layoutRef") != approval.get("layout"):
        return {"valid": False, "reason": "layout_changed", "approval": approval}
    if scene.get("templateRef") != approval.get("template"):
        return {"valid": False, "reason": "template_changed", "approval": approval}
    assets = sorted(
        {
            json.dumps(node["assetRef"], ensure_ascii=False, sort_keys=True)
            for node in scene.get("nodes", [])
            if node.get("type") == "image"
        }
    )
    if assets != approval.get("assets"):
        return {"valid": False, "reason": "assets_changed", "approval": approval}
    if _runtime_fingerprint(deps) != approval.get("runtime"):
        return {"valid": False, "reason": "runtime_changed", "approval": approval}
    scene_sha256 = _sha256_bytes(
        json.dumps(scene, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    if scene_sha256 != approval.get("scene_sha256"):
        return {"valid": False, "reason": "scene_changed", "approval": approval}
    from html_input_manifest import resolved_scene_inputs

    if resolved_scene_inputs(scene, run_dir, deps.repo_root)["digest"] != approval.get(
        "resolved_input_digest"
    ):
        return {
            "valid": False,
            "reason": "resolved_inputs_changed",
            "approval": approval,
        }
    return {"valid": True, "approval": approval}


def approve_stored_scene(run_dir, slide_id, candidate, *, deps):
    """Both transports approve the current stored document under the same lock."""
    from html_visual_store import load_scene_with_revision
    from pipeline_lifecycle import project_artifact_lock

    with project_artifact_lock(run_dir):
        document = load_scene_with_revision(run_dir, slide_id)
        if document is None or (
            candidate is not None and candidate != document["scene"]
        ):
            raise HtmlReviewError(
                "批准必须对应已保存的当前场景，请先保存并审阅", status_code=409
            )
        return approve_scene(document["scene"], run_dir=run_dir, deps=deps)
