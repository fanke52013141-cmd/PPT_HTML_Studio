"""A01 pure semantic planning contract. No rendering, clocks or approval."""
from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError


class SemanticPlanError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class VisualTarget(StrictRecord):
    objectId: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=1, max_length=400)


class PlannedAction(StrictRecord):
    actionId: str = Field(min_length=1, max_length=80)
    objectId: str = Field(min_length=1, max_length=64)
    type: Literal["enter", "emphasize"]


class ExpectedState(StrictRecord):
    objectId: str = Field(min_length=1, max_length=64)
    visible: StrictBool
    expression: str = Field(min_length=1, max_length=400)


class SemanticBeat(StrictRecord):
    id: str = Field(min_length=1, max_length=80)
    visualIntent: str = Field(min_length=1, max_length=600)
    targets: list[VisualTarget] = Field(max_length=64)
    actions: list[PlannedAction] = Field(max_length=128)
    expectedState: list[ExpectedState] = Field(max_length=64)
    narration_only: StrictBool = False
    narrationOnlyReason: str | None = Field(default=None, min_length=1, max_length=400)
    spoken_text: str | None = None
    spoken_text_sha256: str | None = None


class SemanticObject(StrictRecord):
    role: Literal["instructional", "context", "decorative"]
    initialVisible: StrictBool
    initialVisibleReason: str | None = Field(default=None, min_length=1, max_length=400)


class HtmlPlanGenerateRequest(StrictRecord):
    brief: dict | None = None
    plan_version: Literal["0.1.0", "0.2.0"] = "0.1.0"


def normalize_semantics(plan_input, objects, contract_slide):
    """Bind model declarations to exact authoritative spoken bytes and IDs.

    Meaning is still a claim for A04 QA, never a semantic approval here.
    """
    def fail(code, message):
        raise SemanticPlanError(code, message)

    contract_beats = (contract_slide or {}).get("narration_beats")
    if not isinstance(contract_beats, list) or not contract_beats:
        fail("SEMANTIC_SOURCE_REQUIRED", "新版计划必须有权威讲稿语块")
    sources = {}
    for beat in contract_beats:
        if not isinstance(beat, dict) or not isinstance(beat.get("id"), str) or not beat["id"].strip():
            fail("SEMANTIC_SOURCE_INVALID", "讲稿缺少稳定语块 ID")
        text = beat.get("spoken_text")
        if text is None:
            text = beat.get("text")
        if not isinstance(text, str) or not text.strip() or beat["id"] in sources:
            fail("SEMANTIC_SOURCE_INVALID", "讲稿文本为空或语块 ID 重复")
        sources[beat["id"]] = text
    raw_beats = plan_input.get("beats")
    if not isinstance(raw_beats, list) or [b.get("id") if isinstance(b, dict) else None for b in raw_beats] != list(sources):
        fail("SEMANTIC_BEAT_COVERAGE", "语块必须按权威讲稿顺序完整映射，不可新增、删除、重复或换序")
    raw_objects = {o["id"]: o for o in plan_input["objects"]}
    slots = [o["slot"] for o in objects]
    if len(set(slots)) != len(slots) or set(slots) != set(plan_input["slots"]):
        fail("SEMANTIC_SLOT_OBJECTS", "新版计划每个内容槽位必须恰好有一个对象")
    normalized_objects = []
    try:
        for obj in objects:
            raw = raw_objects[obj["id"]]
            role = SemanticObject.model_validate({k: raw[k] for k in ("role", "initialVisible", "initialVisibleReason") if k in raw})
            if role.initialVisible:
                if role.role == "instructional" or not role.initialVisibleReason:
                    fail("SEMANTIC_INITIAL_VISIBILITY", "初始可见只允许有明确理由的 context/decorative")
            elif role.initialVisibleReason is not None:
                fail("SEMANTIC_INITIAL_VISIBILITY", "非初始可见对象不能声明初始可见理由")
            normalized_objects.append({**obj, **role.model_dump(exclude_none=True)})
        beats = [SemanticBeat.model_validate(b) for b in raw_beats]
    except ValidationError as exc:
        import json
        errors = exc.errors(include_input=False, include_url=False)
        fail("SEMANTIC_SCHEMA_INVALID", json.dumps({"errors": errors[:8], "remaining": max(0, len(errors) - 8)}, ensure_ascii=False))
    known = {o["id"]: o for o in normalized_objects}
    action_ids, covered, entered = set(), set(), set()
    result = []
    for beat in beats:
        text = sources[beat.id]
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # str_strip_whitespace applies to model text, not the source. Compare
        # the original supplied value to preserve every source byte.
        raw = raw_beats[len(result)]
        if (beat.spoken_text is not None and raw["spoken_text"] != text) or (beat.spoken_text_sha256 is not None and beat.spoken_text_sha256 != digest):
            fail("SEMANTIC_SPOKEN_MISMATCH", f"{beat.id} 不可替换原讲稿或散列")
        target_ids = [t.objectId for t in beat.targets]
        state_ids = [s.objectId for s in beat.expectedState]
        if len(set(target_ids)) != len(target_ids) or len(set(state_ids)) != len(state_ids):
            fail("SEMANTIC_TARGET_DUPLICATE", f"{beat.id} 对象/状态重复")
        if set(target_ids) - set(known):
            fail("SEMANTIC_TARGET_UNKNOWN", f"{beat.id} 引用了未知对象")
        if beat.narration_only:
            if not beat.narrationOnlyReason or beat.targets or beat.actions or beat.expectedState:
                fail("SEMANTIC_NARRATION_ONLY_INVALID", "纯旁白必须有理由且不能同时声明视觉动作/目标/状态")
        elif beat.narrationOnlyReason or not beat.targets or not beat.actions or set(state_ids) != set(target_ids):
            fail("SEMANTIC_VISUAL_EXPRESSION_MISSING", "视觉语块须有目标、动作及每个目标的可检查状态，不可混用纯旁白理由")
        for state in beat.expectedState:
            if not state.visible:
                fail("SEMANTIC_STATE_UNSUPPORTED", "当前动作只支持 enter/emphasize，不能声明不可见终态")
        for action in beat.actions:
            if action.actionId in action_ids:
                fail("SEMANTIC_ACTION_DUPLICATE", "actionId 在本页必须唯一；重复强调需独立 ID")
            if action.objectId not in target_ids:
                fail("SEMANTIC_ACTION_TARGET", "动作只能指向本语块声明目标")
            if action.type == "enter":
                if action.objectId in entered or known[action.objectId]["initialVisible"]:
                    fail("SEMANTIC_ENTER_DUPLICATE", "同一对象只能进入一次，初始可见对象不能再次进入")
                entered.add(action.objectId)
            action_ids.add(action.actionId)
        covered.update(target_ids)
        result.append({**beat.model_dump(exclude_none=True), "spoken_text": text, "spoken_text_sha256": digest})
    instructional = {o["id"] for o in normalized_objects if o["role"] == "instructional"}
    if instructional - covered or instructional - entered:
        fail("SEMANTIC_INSTRUCTIONAL_UNBOUND", "每个 instructional 对象须由语块明确表达并进入，不得默认 0ms 显示")
    return normalized_objects, result


def preserve_action_identity(previous: dict, current: dict) -> None:
    """Keep unambiguous valid identities on structural retry; invalid IDs may change."""
    if not isinstance(previous, dict) or previous.get("version") != "0.2.0":
        return
    def entries(plan):
        found = []
        for beat in plan.get("beats", []) if isinstance(plan.get("beats"), list) else []:
            if not isinstance(beat, dict) or not isinstance(beat.get("actions"), list):
                continue
            occurrence = {}
            for action in beat["actions"]:
                if not isinstance(action, dict) or not all(isinstance(v, str) and v.strip() for v in (beat.get("id"), action.get("objectId"), action.get("type"), action.get("actionId"))):
                    continue
                pair = (beat["id"], action["objectId"], action["type"])
                ordinal = occurrence.get(pair, 0)
                occurrence[pair] = ordinal + 1
                found.append(((*pair, ordinal), action["actionId"]))
        return found
    old = entries(previous)
    counts = {}
    for _, identity in old:
        counts[identity] = counts.get(identity, 0) + 1
    stable = {key: identity for key, identity in old if counts[identity] == 1 and len(identity) <= 80 and identity == identity.strip()}
    for key, identity in entries(current):
        if key in stable and stable[key] != identity:
            raise SemanticPlanError("SEMANTIC_ACTION_ID_CHANGED", "结构修复不可重命名已有明确动作；保留原 actionId")
