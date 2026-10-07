"""Semantic storyboard adaptation for the HTML backend (C01).

Pure planning layer between the existing Step 2 visual contract and the
constrained html-visual scene definitions. Ownership mirrors
``storyboard_planning.py``: normalization/validation only — no FastAPI,
no database, no model calls. Orchestration stays in storyboard_service;
the registered capability catalog comes from the built engine bundle
(``html_engine/visual/generated/catalog.json``), so a model or a human
can only ever reference templates, slot kinds, and icons that are
actually registered. Free HTML is not an output of this layer.

AC07 evidence produced here: the beat→node/action map, the object table
including transitional (exiting) objects, and the asset table with an
explicit render owner for every image need.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from visual_contract_service import narration_dedupe_key

DEFAULT_CATALOG_PATH = (
    Path("html_engine") / "visual" / "generated" / "catalog.json"
)
_ALLOWED_ACTIONS = {"enter", "emphasize"}
_ALLOWED_RENDER_OWNERS = {"code", "image_asset"}


class HtmlScenePlanError(ValueError):
    """Plan rejection with a stable diagnostic code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- catalog


def load_template_catalog(
    repo_root: str | Path = ".",
    catalog_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Load the registered capability catalog from the built engine bundle.

    The generated catalog is the single registration source; a missing or
    stale bundle is a hard error — planning never widens capabilities.
    """
    path = (
        Path(catalog_path)
        if catalog_path
        else Path(repo_root) / DEFAULT_CATALOG_PATH
    )
    if not path.is_file():
        raise HtmlScenePlanError(
            "CATALOG_MISSING",
            "引擎能力目录不存在，请先在 html_engine 执行构建（node visual/build.cjs）",
        )
    raw = path.read_bytes()
    try:
        catalog = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HtmlScenePlanError("CATALOG_CORRUPT", "引擎能力目录无法解析") from exc
    templates = catalog.get("templates")
    if not isinstance(templates, list) or not templates:
        raise HtmlScenePlanError("CATALOG_CORRUPT", "能力目录缺少模板注册")
    registered: Dict[str, Dict[str, Any]] = {}
    for template in templates:
        if not isinstance(template, dict):
            continue
        template_id = str(template.get("id") or "")
        if template_id:
            registered[template_id] = template
    icons = _registered_icons(repo_root)
    return {
        "templates": registered,
        "icons": icons,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _registered_icons(repo_root: str | Path) -> List[str]:
    """Registered icon ids from the shared icon registry source."""
    icons_path = (
        Path(repo_root) / "html_engine" / "visual" / "icons.cjs"
    )
    if not icons_path.is_file():
        raise HtmlScenePlanError("ICON_REGISTRY_MISSING", "共享图标注册表不存在")
    ids: List[str] = []
    in_paths = False
    for line in icons_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("const paths = {"):
            in_paths = True
            continue
        if in_paths:
            if stripped.startswith("};"):
                break
            if stripped.startswith("//") or not stripped:
                continue
            name = stripped.split(":", 1)[0].strip()
            if name.startswith("[") or name.startswith('"'):
                try:
                    name = json.loads(name)
                except Exception:
                    pass
            if isinstance(name, str) and name:
                ids.append(name)
    if not ids:
        raise HtmlScenePlanError("ICON_REGISTRY_CORRUPT", "共享图标注册表为空")
    return sorted(ids)


# ---------------------------------------------------------------- planning


def _clean_text(value: Any, *, max_length: int, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise HtmlScenePlanError("PLAN_FIELD_MISSING", f"{label} 不能为空")
    if len(text) > max_length:
        raise HtmlScenePlanError(
            "PLAN_FIELD_TOO_LONG",
            f"{label} 超出 {max_length} 字符上限（当前 {len(text)}）",
        )
    return text


def normalize_html_scene_plan(
    plan_input: Dict[str, Any],
    catalog: Dict[str, Any],
    *,
    contract_slide: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate and freeze one slide's HTML scene plan.

    ``plan_input`` fields:
      - ``slide_id``: must match the contract slide when provided
      - ``templateRef``: {id, version} — must be a registered template
      - ``slots``: {slotName: {kind, ...content}} — content shape is kept
        verbatim; kind must be allowed by the template rule
      - ``objects``: [{id, slot, kind, action?, exit?}] — the full object
        table; transitional objects stay listed with ``exit: true`` even
        though they are absent from the final frame (AC07)
      - ``beats``: [{id, target?: {objectId, action}, narration_only?}]
        — one entry per contract narration beat, in order
      - ``assets``: [{id, role, render_owner, need?, slot?}]
    """
    if not isinstance(plan_input, dict):
        raise HtmlScenePlanError("PLAN_INVALID", "场景计划必须是 JSON 对象")
    slide_id = _clean_text(
        plan_input.get("slide_id"), max_length=80, label="slide_id"
    )
    if isinstance(contract_slide, list):
        # Convenience form: a bare narration-beat list for this slide.
        contract_slide = {"narration_beats": contract_slide}
    if contract_slide is not None:
        contract_id = str(contract_slide.get("slide_id") or "").strip()
        if contract_id and contract_id != slide_id:
            raise HtmlScenePlanError(
                "PLAN_SLIDE_MISMATCH",
                f"计划 slide_id={slide_id} 与契约 {contract_id} 不一致",
            )

    template_ref = plan_input.get("templateRef")
    if not isinstance(template_ref, dict):
        raise HtmlScenePlanError("PLAN_TEMPLATE_MISSING", "缺少 templateRef")
    template_id = str(template_ref.get("id") or "")
    template = catalog["templates"].get(template_id)
    if template is None:
        raise HtmlScenePlanError(
            "TEMPLATE_UNREGISTERED",
            f"模板 {template_id} 未注册；可用：{', '.join(sorted(catalog['templates']))}",
        )
    template_version = str(template_ref.get("version") or "")
    if template_version != str(template.get("version")):
        raise HtmlScenePlanError(
            "TEMPLATE_VERSION_MISMATCH",
            f"模板 {template_id} 版本 {template_version or '(空)'} 未注册",
        )

    slot_rules = template.get("slots") or {}
    slots_input = plan_input.get("slots")
    if not isinstance(slots_input, dict) or not slots_input:
        raise HtmlScenePlanError("PLAN_SLOTS_MISSING", "缺少槽位内容")
    normalized_slots: Dict[str, Any] = {}
    for slot_name, content in slots_input.items():
        rule = slot_rules.get(str(slot_name))
        if rule is None:
            raise HtmlScenePlanError(
                "PLAN_SLOT_UNDECLARED",
                f"槽位 {slot_name} 不在模板 {template_id} 的声明中",
            )
        kind = str(content.get("kind") or "") if isinstance(content, dict) else ""
        if kind not in (rule.get("kinds") or []):
            raise HtmlScenePlanError(
                "PLAN_SLOT_KIND",
                f"槽位 {slot_name} 不允许 {kind or '(空)'}（允许：{', '.join(rule.get('kinds') or [])}）",
            )
        normalized_slots[str(slot_name)] = content
    for slot_name, rule in slot_rules.items():
        if rule.get("required") and slot_name not in normalized_slots:
            raise HtmlScenePlanError(
                "PLAN_SLOT_REQUIRED",
                f"模板 {template_id} 必填槽位 {slot_name} 缺失",
            )

    objects = _normalize_objects(plan_input, slot_rules, catalog["icons"])

    beats = _normalize_beats(plan_input, contract_slide)

    assets = _normalize_assets(plan_input)

    plan = {
        "format": "hps.html.scene_plan",
        "version": "0.1.0",
        "slide_id": slide_id,
        "templateRef": {"id": template_id, "version": template_version},
        "structure": str(template.get("structure")),
        "layoutRef": dict(template.get("layoutRef") or {}),
        "slots": normalized_slots,
        "objects": objects,
        "beats": beats,
        "assets": assets,
        "registered": {
            "catalog_sha256": catalog["sha256"],
            "icons": catalog["icons"],
        },
    }
    if contract_slide is not None:
        plan["contract"] = {
            "slide_id": contract_id,
            "narration_beats": len(
                contract_slide.get("narration_beats") or []
            ),
        }
    return plan


def _normalize_objects(
    plan_input: Dict[str, Any],
    slot_rules: Dict[str, Any],
    registered_icons: List[str],
) -> List[Dict[str, Any]]:
    objects_input = plan_input.get("objects")
    if not isinstance(objects_input, list) or not objects_input:
        raise HtmlScenePlanError("PLAN_OBJECTS_MISSING", "缺少对象表")
    seen: set[str] = set()
    objects: List[Dict[str, Any]] = []
    for index, item in enumerate(objects_input, start=1):
        if not isinstance(item, dict):
            raise HtmlScenePlanError("PLAN_OBJECT_INVALID", f"对象 #{index} 不是对象")
        object_id = _clean_text(
            item.get("id"), max_length=64, label=f"对象 #{index} id"
        )
        if object_id in seen:
            raise HtmlScenePlanError(
                "PLAN_OBJECT_DUPLICATE", f"对象 id 重复：{object_id}"
            )
        seen.add(object_id)
        slot = _clean_text(
            item.get("slot"), max_length=64, label=f"对象 {object_id} slot"
        )
        rule = slot_rules.get(slot)
        if rule is None:
            raise HtmlScenePlanError(
                "PLAN_SLOT_UNDECLARED",
                f"对象 {object_id} 的槽位 {slot} 未在模板中声明",
            )
        kind = _clean_text(
            item.get("kind"), max_length=32, label=f"对象 {object_id} kind"
        )
        if kind not in (rule.get("kinds") or []):
            raise HtmlScenePlanError(
                "PLAN_SLOT_KIND",
                f"对象 {object_id}：槽位 {slot} 不允许 {kind}",
            )
        entry: Dict[str, Any] = {
            "id": object_id,
            "slot": slot,
            "kind": kind,
            "exit": bool(item.get("exit")),
        }
        if item.get("icon") is not None:
            icon = str(item.get("icon"))
            if icon not in registered_icons:
                raise HtmlScenePlanError(
                    "ICON_UNREGISTERED",
                    f"对象 {object_id} 图标 {icon} 未注册；可用：{', '.join(registered_icons)}",
                )
            entry["icon"] = icon
        if item.get("transitional") is not None:
            entry["transitional"] = bool(item.get("transitional"))
        objects.append(entry)
    return objects


def _normalize_beats(
    plan_input: Dict[str, Any], contract_slide: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    beats_input = plan_input.get("beats")
    if not isinstance(beats_input, list) or not beats_input:
        raise HtmlScenePlanError("PLAN_BEATS_MISSING", "缺少讲稿语块映射")
    contract_beats = (
        (contract_slide or {}).get("narration_beats") or []
        if contract_slide
        else []
    )
    contract_ids = [
        str(beat.get("id") or "")
        for beat in contract_beats
        if isinstance(beat, dict)
    ]
    if contract_ids:
        plan_ids = [str(beat.get("id") or "") for beat in beats_input if isinstance(beat, dict)]
        missing = [b for b in contract_ids if b not in plan_ids]
        if missing:
            raise HtmlScenePlanError(
                "PLAN_BEAT_MISSING",
                "讲稿语块缺少映射：" + ", ".join(missing),
            )
        extra = [b for b in plan_ids if b and b not in contract_ids]
        if extra:
            raise HtmlScenePlanError(
                "PLAN_BEAT_UNKNOWN",
                "映射引用了契约中不存在的语块：" + ", ".join(extra),
            )
    seen: set[str] = set()
    beats: List[Dict[str, Any]] = []
    for index, beat in enumerate(beats_input, start=1):
        if not isinstance(beat, dict):
            raise HtmlScenePlanError("PLAN_BEAT_INVALID", f"语块 #{index} 不是对象")
        beat_id = _clean_text(
            beat.get("id"), max_length=80, label=f"语块 #{index} id"
        )
        if beat_id in seen:
            raise HtmlScenePlanError(
                "PLAN_BEAT_DUPLICATE", f"语块重复映射：{beat_id}"
            )
        seen.add(beat_id)
        entry: Dict[str, Any] = {"id": beat_id}
        if beat.get("narration_only") is True:
            entry["narration_only"] = True
        else:
            target = beat.get("target")
            if not isinstance(target, dict):
                raise HtmlScenePlanError(
                    "PLAN_BEAT_TARGET_MISSING",
                    f"语块 {beat_id} 既非 narration_only 也缺少 target",
                )
            object_id = _clean_text(
                target.get("objectId"), max_length=64, label=f"语块 {beat_id} target"
            )
            action = str(target.get("action") or "").strip().lower()
            if action not in _ALLOWED_ACTIONS:
                raise HtmlScenePlanError(
                    "PLAN_BEAT_ACTION_INVALID",
                    f"语块 {beat_id} 动作 {action or '(空)'} 不在注册动作内",
                )
            known = any(obj["id"] == object_id for obj in plan_input.get("objects") or [])
            if not known:
                raise HtmlScenePlanError(
                    "PLAN_BEAT_TARGET_UNKNOWN",
                    f"语块 {beat_id} 指向未声明对象 {object_id}",
                )
            entry["target"] = {"objectId": object_id, "action": action}
        beats.append(entry)
    return beats


def _normalize_assets(plan_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    assets_input = plan_input.get("assets") or []
    if not isinstance(assets_input, list):
        raise HtmlScenePlanError("PLAN_ASSETS_INVALID", "assets 必须是数组")
    assets: List[Dict[str, Any]] = []
    for index, item in enumerate(assets_input, start=1):
        if not isinstance(item, dict):
            raise HtmlScenePlanError("PLAN_ASSET_INVALID", f"资产 #{index} 不是对象")
        asset_id = _clean_text(
            item.get("id"), max_length=64, label=f"资产 #{index} id"
        )
        role = _clean_text(
            item.get("role"), max_length=64, label=f"资产 {asset_id} role"
        )
        owner = str(item.get("render_owner") or "").strip().lower()
        if owner not in _ALLOWED_RENDER_OWNERS:
            raise HtmlScenePlanError(
                "PLAN_ASSET_OWNER_INVALID",
                f"资产 {asset_id} 渲染归属必须是 code 或 image_asset",
            )
        entry: Dict[str, Any] = {
            "id": asset_id,
            "role": role,
            "render_owner": owner,
        }
        if owner == "image_asset":
            need = _clean_text(
                item.get("need"), max_length=400, label=f"资产 {asset_id} need"
            )
            entry["need"] = need
            if item.get("slot"):
                entry["slot"] = str(item["slot"])
        assets.append(entry)
    return assets


# ------------------------------------------------------------- AC07 evidence


def beat_action_map(plan: Dict[str, Any]) -> Dict[str, Any]:
    """AC07 evidence: every narration beat → its on-screen target."""
    mapping: Dict[str, Any] = {}
    for beat in plan.get("beats", []):
        if beat.get("narration_only"):
            mapping[beat["id"]] = {"narration_only": True}
        else:
            mapping[beat["id"]] = {
                "objectId": beat["target"]["objectId"],
                "action": beat["target"]["action"],
            }
    return mapping


def transitional_objects(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """AC07: objects that appear and later leave — they must stay in the
    object table even though the final frame no longer shows them."""
    return [
        obj
        for obj in plan.get("objects", [])
        if obj.get("exit") or obj.get("transitional")
    ]


def plan_evidence(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Compact AC07 evidence block for acceptance manifests."""
    return {
        "slide_id": plan.get("slide_id"),
        "templateRef": plan.get("templateRef"),
        "structure": plan.get("structure"),
        "beat_map": beat_action_map(plan),
        "objects_total": len(plan.get("objects", [])),
        "transitional_objects": [
            obj["id"] for obj in transitional_objects(plan)
        ],
        "asset_table": [
            {
                "id": asset["id"],
                "render_owner": asset["render_owner"],
                "need": asset.get("need"),
            }
            for asset in plan.get("assets", [])
        ],
        "catalog_sha256": (plan.get("registered") or {}).get("catalog_sha256"),
    }


def dedupe_plan_beats(beats: Any) -> List[Dict[str, Any]]:
    """Reuse the shared spoken-sentence dedupe on raw plan beats."""
    seen: set[str] = set()
    result: List[Dict[str, Any]] = []
    for beat in beats if isinstance(beats, list) else []:
        if not isinstance(beat, dict):
            continue
        text = str(beat.get("text") or beat.get("spoken_text") or "")
        key = narration_dedupe_key(text)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        result.append(beat)
    return result
