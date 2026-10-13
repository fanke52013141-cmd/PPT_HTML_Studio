"""Pure 0.2.0 beat validation; no model calls or semantic approval."""
from __future__ import annotations

import hashlib
from typing import Any

from pydantic import TypeAdapter, ValidationError

from html_scene_plan_models import PlanIdentity, SemanticBeat

_IDENTITY = TypeAdapter(PlanIdentity)


def _action_id(slide_id: str, key: str) -> str:
    return "act-" + hashlib.sha256((slide_id + "\0" + key).encode("utf-8")).hexdigest()[:32]


class NarrationSemanticError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def validate_narration_source(contract: dict[str, Any] | None) -> dict[str, str]:
    """Return exact source text; reject invalid authority before model calls."""
    if contract and contract.get("slide_id"):
        try:
            _IDENTITY.validate_python(contract["slide_id"], strict=True)
        except ValidationError as exc:
            raise NarrationSemanticError("SEMANTIC_SOURCE_INVALID", "权威页面 ID 格式不合法") from exc
    source = (contract or {}).get("narration_beats")
    if not isinstance(source, list) or not source:
        raise NarrationSemanticError("SEMANTIC_SOURCE_MISSING", "新规划必须读取权威讲稿语块")
    source_by_id = {}
    for beat in source:
        if not isinstance(beat, dict) or not isinstance(beat.get("id"), str) or not beat["id"]:
            raise NarrationSemanticError("SEMANTIC_SOURCE_INVALID", "权威语块缺少稳定 ID")
        try:
            _IDENTITY.validate_python(beat["id"], strict=True)
        except ValidationError as exc:
            raise NarrationSemanticError("SEMANTIC_SOURCE_INVALID", "权威语块 ID 格式不合法") from exc
        text = beat.get("spoken_text")
        if not isinstance(text, str) or not text.strip():
            raise NarrationSemanticError("SEMANTIC_SOURCE_INVALID", "权威语块缺少 spoken_text")
        if beat["id"] in source_by_id:
            raise NarrationSemanticError("SEMANTIC_SOURCE_DUPLICATE", "权威语块 ID 重复")
        source_by_id[beat["id"]] = text
    if len(source_by_id) > 128:
        raise NarrationSemanticError("SEMANTIC_SOURCE_INVALID", "权威语块超过 128 项，请拆页")
    return source_by_id


def normalize_semantic_beats(
    plan: dict[str, Any], contract: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Freeze source-order beats and independent, deterministic action identities."""
    source_by_id = validate_narration_source(contract)
    try:
        _IDENTITY.validate_python(plan["slide_id"], strict=True)
    except ValidationError as exc:
        raise NarrationSemanticError("SEMANTIC_PLAN_ID_INVALID", "语义规划页面 ID 格式不合法") from exc
    raw_beats = plan.get("beats")
    if not isinstance(raw_beats, list) or not raw_beats or len(raw_beats) > 128:
        raise NarrationSemanticError("PLAN_BEATS_MISSING", "语块映射应为 1–128 项")
    objects = {obj["id"] for obj in plan["objects"]}
    roles: dict[str, str] = {}
    seen_beats: dict[str, dict[str, Any]] = {}
    action_keys: set[str] = set()
    for raw in raw_beats:
        raw = _validate_host_fields(raw, source_by_id, plan["slide_id"])
        try:
            beat = SemanticBeat.model_validate(raw)
        except ValidationError as exc:
            location = ".".join(str(part) for part in exc.errors()[0]["loc"])
            raise NarrationSemanticError(
                "SEMANTIC_BEAT_INVALID", f"语义映射字段不合法：{location}"
            ) from exc
        if beat.id not in source_by_id:
            raise NarrationSemanticError("PLAN_BEAT_UNKNOWN", f"未知语块：{beat.id}")
        if beat.id in seen_beats:
            raise NarrationSemanticError("PLAN_BEAT_DUPLICATE", f"重复语块：{beat.id}")
        if beat.narration_only:
            if not beat.narration_only_reason or beat.targets or beat.actions:
                raise NarrationSemanticError(
                    "SEMANTIC_NARRATION_REASON", "纯旁白必须说明理由，且不携带目标或动作"
                )
        elif beat.narration_only_reason is not None or not beat.targets or not beat.actions:
            raise NarrationSemanticError(
                "SEMANTIC_EXPRESSION_MISSING", "讲解语块必须有视觉目标和动作，不能用纯旁白理由代替"
            )
        targets = {}
        for target in beat.targets:
            if target.objectId not in objects:
                raise NarrationSemanticError("PLAN_BEAT_TARGET_UNKNOWN", f"未知目标：{target.objectId}")
            if target.objectId in targets:
                raise NarrationSemanticError("SEMANTIC_TARGET_DUPLICATE", f"重复目标：{target.objectId}")
            if target.objectId in roles and roles[target.objectId] != target.role:
                raise NarrationSemanticError("SEMANTIC_ROLE_CONFLICT", f"目标角色冲突：{target.objectId}")
            roles[target.objectId] = target.role
            targets[target.objectId] = target
        actions = []
        for action in beat.actions:
            if action.objectId not in targets:
                raise NarrationSemanticError("SEMANTIC_ACTION_TARGET", "动作必须引用本语块已声明目标")
            if targets[action.objectId].role == "decorative":
                raise NarrationSemanticError("SEMANTIC_DECORATION_ACTION", "装饰不能承担讲解动作")
            if action.actionKey in action_keys:
                raise NarrationSemanticError("SEMANTIC_ACTION_DUPLICATE", f"动作 key 重复：{action.actionKey}")
            action_keys.add(action.actionKey)
            actions.append({**action.model_dump(), "actionId": _action_id(plan["slide_id"], action.actionKey)})
        driven = {action["objectId"] for action in actions}
        if any(target.role == "instructional" and target.objectId not in driven for target in beat.targets):
            raise NarrationSemanticError("SEMANTIC_TARGET_UNDRIVEN", "讲解目标缺少自身动作")
        if not beat.narration_only and not any(target.role == "instructional" for target in beat.targets):
            raise NarrationSemanticError("SEMANTIC_INSTRUCTION_MISSING", "视觉表达不能只有背景或装饰")
        text = source_by_id[beat.id]
        seen_beats[beat.id] = {
            **beat.model_dump(exclude_none=True),
            "spoken_text": text,
            "spoken_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "actions": actions,
        }
    missing = set(source_by_id) - set(seen_beats)
    if missing:
        raise NarrationSemanticError("PLAN_BEAT_MISSING", "语块缺少映射：" + ", ".join(sorted(missing)))
    return [seen_beats[beat_id] for beat_id in source_by_id]


def _validate_host_fields(raw: Any, source: dict[str, str], slide_id: str) -> Any:
    """Allow revalidation of frozen plans without trusting model/source rewrites."""
    if not isinstance(raw, dict):
        return raw
    raw = dict(raw)
    beat_id = raw.get("id")
    text = source.get(beat_id) if isinstance(beat_id, str) else None
    if "spoken_text" in raw or "spoken_text_sha256" in raw:
        expected_hash = hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None
        if raw.get("spoken_text") != text or raw.get("spoken_text_sha256") != expected_hash:
            raise NarrationSemanticError("SEMANTIC_SOURCE_CHANGED", "规划讲稿与当前权威原句不一致")
        raw.pop("spoken_text", None)
        raw.pop("spoken_text_sha256", None)
    if isinstance(raw.get("actions"), list):
        actions = []
        for action in raw["actions"]:
            if isinstance(action, dict) and "actionId" in action:
                action = dict(action)
                key = action.get("actionKey")
                expected = (
                    _action_id(slide_id, key)
                    if isinstance(key, str) else None
                )
                if action.pop("actionId") != expected:
                    raise NarrationSemanticError("SEMANTIC_ACTION_ID_CHANGED", "动作身份与稳定 key 不一致")
            actions.append(action)
        raw["actions"] = actions
    return raw
