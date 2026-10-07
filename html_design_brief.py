"""Design brief, keyframe list, and freeze record for HTML scenes (C02).

Pure layer between a normalized scene plan (``html_storyboard_planning``)
and later visual/asset production:

- the brief states what a design reference must cover: registered theme,
  template, effect IDs with backend (from the engine effect registry),
  asset budget, subtitle reserve, and content — the model-side prompt
  assembly (C04 service) consumes this; it never invents effects
- candidates separate code-rendered parts (CSS/SVG/Canvas2D) from
  independent image parts, so generation ownership stays explicit
- keyframes follow OSS-04: a static scene needs one final-frame
  reference; a process scene (transitional objects) must cover start,
  relation change, and end
- freezing records the chosen candidate with input/output hashes and
  explicit diff notes — no claim of automatic pixel-exact reproduction
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_EFFECT_REGISTRY = (
    Path("html_engine") / "visual" / "effects" / "registry.json"
)
_BACKENDS = {"CSS", "SVG", "Canvas2D", "image_asset"}


class DesignBriefError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def load_effect_registry(
    repo_root: str | Path = ".",
    registry_path: str | Path | None = None,
) -> Dict[str, Any]:
    path = (
        Path(registry_path)
        if registry_path
        else Path(repo_root) / DEFAULT_EFFECT_REGISTRY
    )
    if not path.is_file():
        raise DesignBriefError(
            "EFFECT_REGISTRY_MISSING", "效果注册表不存在，请先构建引擎"
        )
    raw = path.read_bytes()
    try:
        registry = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise DesignBriefError("EFFECT_REGISTRY_CORRUPT", "效果注册表无法解析") from exc
    effects = registry.get("effects")
    if not isinstance(effects, list) or not effects:
        raise DesignBriefError("EFFECT_REGISTRY_CORRUPT", "效果注册表为空")
    registered = {}
    for effect in effects:
        if isinstance(effect, dict) and effect.get("id"):
            backend = str(effect.get("backend") or "")
            if backend not in _BACKENDS:
                raise DesignBriefError(
                    "EFFECT_REGISTRY_CORRUPT",
                    f"效果 {effect.get('id')} backend 不合法：{backend}",
                )
            registered[str(effect["id"])] = {
                "backend": backend,
                "purpose": str(effect.get("purpose") or ""),
            }
    return {
        "effects": registered,
        "sha256": _sha256_bytes(raw),
    }


def build_design_brief(
    plan: Dict[str, Any],
    *,
    theme: str,
    asset_budget: int,
    subtitle_reserve: bool = True,
    effect_registry: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble the design brief for one planned slide.

    The brief only references registered capabilities: template from the
    plan, theme id, effect ids resolved against the registry, and the
    image-asset needs (code parts never consume generation budget).
    """
    template_ref = plan.get("templateRef")
    if not isinstance(template_ref, dict) or not template_ref.get("id"):
        raise DesignBriefError(
            "BRIEF_PLAN_INVALID", "brief 需要一个已规范化的场景计划"
        )
    theme_id = str(theme or "").strip()
    if not theme_id:
        raise DesignBriefError("BRIEF_THEME_MISSING", "缺少主题")
    if not isinstance(asset_budget, int) or asset_budget < 0 or asset_budget > 2:
        raise DesignBriefError(
            "BRIEF_BUDGET_INVALID", "每场景生图预算为 0—2（双对象模板上限 2）"
        )
    image_needs = [
        asset
        for asset in plan.get("assets", [])
        if asset.get("render_owner") == "image_asset"
    ]
    if len(image_needs) > asset_budget:
        raise DesignBriefError(
            "BRIEF_BUDGET_EXCEEDED",
            f"计划需要 {len(image_needs)} 个独立图片资产，超出预算 {asset_budget}",
        )
    used_effects = sorted(effect_registry["effects"])
    brief = {
        "format": "hps.html.design_brief",
        "version": "0.1.0",
        "slide_id": plan.get("slide_id"),
        "templateRef": dict(template_ref),
        "structure": plan.get("structure"),
        "theme": theme_id,
        "effects": [
            {
                "id": effect_id,
                "backend": effect_registry["effects"][effect_id]["backend"],
                "purpose": effect_registry["effects"][effect_id]["purpose"],
            }
            for effect_id in used_effects
        ],
        "asset_needs": [
            {
                "id": asset["id"],
                "role": asset.get("role"),
                "need": asset.get("need"),
                "slot": asset.get("slot"),
            }
            for asset in image_needs
        ],
        "asset_budget": asset_budget,
        "subtitle_reserve": bool(subtitle_reserve),
        "registry_sha256": effect_registry["sha256"],
        "catalog_sha256": (plan.get("registered") or {}).get("catalog_sha256"),
    }
    brief["sha256"] = _sha256_bytes(_canonical(brief))
    return brief


def normalize_design_candidate(candidate: Any) -> Dict[str, Any]:
    """Validate one candidate design reference.

    Every part declares its backend; image parts describe the generated
    appearance, code parts describe the CSS/SVG/Canvas structure that
    the shared renderer will reproduce.
    """
    if not isinstance(candidate, dict):
        raise DesignBriefError("CANDIDATE_INVALID", "设计参考必须是对象")
    name = str(candidate.get("name") or "").strip()
    if not name:
        raise DesignBriefError("CANDIDATE_NAME_MISSING", "设计参考缺少名称")
    parts = candidate.get("parts")
    if not isinstance(parts, list) or not parts:
        raise DesignBriefError("CANDIDATE_PARTS_MISSING", "设计参考缺少分工说明")
    normalized_parts: List[Dict[str, Any]] = []
    for index, part in enumerate(parts, start=1):
        if not isinstance(part, dict):
            raise DesignBriefError("CANDIDATE_PART_INVALID", f"分工 #{index} 不是对象")
        backend = str(part.get("backend") or "").strip()
        if backend not in _BACKENDS:
            raise DesignBriefError(
                "CANDIDATE_BACKEND_INVALID",
                f"分工 #{index} backend 必须是 {'/'.join(sorted(_BACKENDS))}",
            )
        description = str(part.get("description") or "").strip()
        if not description:
            raise DesignBriefError(
                "CANDIDATE_DESCRIPTION_MISSING", f"分工 #{index} 缺少描述"
            )
        normalized_parts.append({"backend": backend, "description": description})
    normalized = {
        "name": name,
        "parts": normalized_parts,
        "keyframes": normalize_keyframes(candidate.get("keyframes")),
        "notes": str(candidate.get("notes") or "").strip(),
    }
    normalized["sha256"] = _sha256_bytes(_canonical(normalized))
    return normalized


def normalize_keyframes(keyframes: Any) -> List[Dict[str, Any]]:
    """Keyframe list: what each reference frame must show."""
    if keyframes is None:
        return []
    if not isinstance(keyframes, list):
        raise DesignBriefError("KEYFRAMES_INVALID", "keyframes 必须是数组")
    result: List[Dict[str, Any]] = []
    for index, frame in enumerate(keyframes, start=1):
        if not isinstance(frame, dict):
            raise DesignBriefError("KEYFRAME_INVALID", f"关键帧 #{index} 不是对象")
        stage = str(frame.get("stage") or "").strip()
        if stage not in {"start", "relation_change", "end", "static"}:
            raise DesignBriefError(
                "KEYFRAME_STAGE_INVALID",
                f"关键帧 #{index} stage 必须是 start/relation_change/end/static",
            )
        shows = str(frame.get("shows") or "").strip()
        if not shows:
            raise DesignBriefError(
                "KEYFRAME_SHOWS_MISSING", f"关键帧 #{index} 缺少画面说明"
            )
        result.append({"stage": stage, "shows": shows})
    return result


def required_keyframes(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """OSS-04: static scenes need one reference; process scenes must cover
    start, relation change, and end. Transitional objects force process
    keyframes even when the plan structure would suggest a static page."""
    has_transitional = any(
        obj.get("exit") or obj.get("transitional")
        for obj in plan.get("objects", [])
    )
    is_process = plan.get("structure") == "process-stage" or has_transitional
    if not is_process:
        return [{"stage": "static", "shows": "最终讲解状态（终帧）"}]
    return [
        {"stage": "start", "shows": "初始状态：主体在位，过程未开始"},
        {"stage": "relation_change", "shows": "关系/过程变化：过渡对象在场，方向或数量可见"},
        {"stage": "end", "shows": "终态：过渡对象已离场，只保留长期对象与结论"},
    ]


def freeze_design(
    brief: Dict[str, Any],
    candidate: Dict[str, Any],
    *,
    diff_notes: str,
) -> Dict[str, Any]:
    """The AC07 freeze record: chosen candidate bound to the brief by hash.

    ``diff_notes`` must state where the executable target differs from the
    reference; freezing never claims automatic pixel-exact reproduction.
    """
    notes = str(diff_notes or "").strip()
    if not notes:
        raise DesignBriefError(
            "FREEZE_DIFF_MISSING", "冻结必须记录与设计参考的差异说明"
        )
    record = {
        "format": "hps.html.design_freeze",
        "version": "0.1.0",
        "slide_id": brief.get("slide_id"),
        "templateRef": brief.get("templateRef"),
        "brief_sha256": brief.get("sha256"),
        "candidate_name": candidate.get("name"),
        "candidate_sha256": candidate.get("sha256"),
        "keyframes": candidate.get("keyframes", []),
        "diff_notes": notes,
    }
    record["sha256"] = _sha256_bytes(_canonical(record))
    return record
