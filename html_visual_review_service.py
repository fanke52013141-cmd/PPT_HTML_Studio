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
    run_subprocess_bounded: Callable[..., subprocess.CompletedProcess] = (
        __import__("runtime_support").run_subprocess_killable
    )
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
    return {"catalog": catalog, "effects": effects}


def _plan_schema_hint() -> str:
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
        + "\n已注册图标：" + ", ".join(capabilities["catalog"]["icons"])
        + "\n已注册效果：" + ", ".join(sorted(capabilities["effects"]["effects"]))
    )
    user = json.dumps(
        {
            "slide": {
                "slide_id": contract_slide.get("slide_id"),
                "visual_groups": contract_slide.get("visual_groups") or [],
                "narration_beats": contract_slide.get("narration_beats") or [],
            },
            "design_brief": brief,
        },
        ensure_ascii=False,
    )
    return {
        "system_prompt": system,
        "user_prompt": user,
        "schema_hint": _plan_schema_hint(),
    }


def generate_scene_plan(
    contract_slide: Dict[str, Any],
    *,
    run_dir: str | Path,
    repo_root: Path,
    json_generator: Callable[..., Dict[str, Any]],
    brief: Optional[Dict[str, Any]] = None,
    artifact_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """Model → validated scene plan, with one bounded repair round.

    Evidence (AC06/AC07) is written before the verdict: the request
    context hashes (catalog/registry/brief) and the response hash land in
    ``planning/html_visual/records/plan-<slide>.json`` together with the
    final diagnostics. A model output that fails normalization twice is
    an error — validators never bend toward the model.
    """
    capabilities = _registered_capabilities(Path(repo_root))
    prompts = build_plan_generation_prompts(contract_slide, capabilities, brief)
    prefix = artifact_prefix or f"html_scene_plan_{contract_slide.get('slide_id')}"
    attempts: List[Dict[str, Any]] = []
    plan = None
    last_failure: Optional[HtmlScenePlanError] = None
    for round_index in (1, 2):
        repair_note = ""
        if attempts:
            repair_note = (
                f"上一次输出未通过校验：{last_failure.code} {last_failure}。"
                "请严格按已注册模板/槽位/图标重新输出完整 JSON。"
            )
        response = json_generator(
            system_prompt=prompts["system_prompt"] + repair_note,
            user_prompt=prompts["user_prompt"],
            run_dir=str(run_dir),
            artifact_prefix=prefix,
            schema_hint=prompts["schema_hint"],
        )
        response_sha256 = _sha256_bytes(
            json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        try:
            plan = normalize_html_scene_plan(
                response,
                capabilities["catalog"],
                contract_slide=contract_slide,
            )
            attempts.append({
                "round": round_index,
                "response_sha256": response_sha256,
                "accepted": True,
            })
            break
        except HtmlScenePlanError as exc:
            last_failure = exc
            attempts.append({
                "round": round_index,
                "response_sha256": response_sha256,
                "accepted": False,
                "diagnostic_code": exc.code,
                "diagnostic": str(exc),
            })
    record = {
        "format": "hps.html.plan_generation",
        "version": "0.1.0",
        "slide_id": contract_slide.get("slide_id"),
        "artifact_prefix": prefix,
        "request_context": {
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
    _write_json(records_dir / f"plan-{contract_slide.get('slide_id')}.json", record)
    if plan is None:
        raise HtmlReviewError(
            "模型输出两次未通过注册能力校验；诊断已保存，请调整后重试："
            f"{last_failure.code} {last_failure}",
            status_code=422,
            code="PLAN_GENERATION_REJECTED",
        )
    return plan


# ------------------------------------------------------------- static review


def review_scene(
    scene: Dict[str, Any],
    *,
    run_dir: str | Path,
    deps: HtmlReviewDependencies,
) -> Dict[str, Any]:
    """Compile + measure + screenshot one scene via the shared bundle."""
    run_dir = Path(run_dir)
    review_dir = run_dir / REVIEW_DIR
    review_dir.mkdir(parents=True, exist_ok=True)
    scene_tmp = review_dir / f"scene-{scene.get('id')}.under-review.json"
    report_path = review_dir / f"report-{scene.get('id')}.json"
    screenshot_path = review_dir / f"review-{scene.get('id')}.png"
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
    )
    if result.returncode != 0:
        raise HtmlReviewError(
            "静态审阅脚本失败：" + (result.stderr or "")[-400:],
            status_code=500,
            code="REVIEW_SCRIPT_FAILED",
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["screenshot"] = str(
        screenshot_path.relative_to(run_dir)
    )
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
    path = Path(run_dir) / f"{APPROVAL_PREFIX}{slide_id}.json"
    if not path.is_file():
        return {"valid": False, "reason": "no_approval"}
    approval = json.loads(path.read_text(encoding="utf-8"))
    if scene is None:
        return {"valid": True, "approval": approval, "reason": "scene_not_supplied"}
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
    return {"valid": True, "approval": approval}
