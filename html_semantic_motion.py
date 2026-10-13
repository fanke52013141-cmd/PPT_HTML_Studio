"""A03 plan compilation and strict real-audio bindings; no speech generation."""
from __future__ import annotations

import copy
import hashlib
import re

from html_narration_semantics import normalize_semantic_beats
from html_object_decomposition import narration_design


def compile_semantic_motion(plan: dict, contract: dict, nodes: list) -> tuple[dict, dict]:
    from html_visual_review_service import HtmlReviewError

    narration_design(plan)
    from html_scene_plan_models import FrozenSemanticBeat
    frozen = [FrozenSemanticBeat.model_validate(b).model_dump(exclude_none=True) for b in plan["beats"]]
    if normalize_semantic_beats(plan, contract) != frozen:
        raise HtmlReviewError("讲稿映射已变化，须重新规划", code="SEMANTIC_SOURCE_CHANGED")
    if any(not re.fullmatch(r"[a-z][a-z0-9.-]{0,63}", oid) for oid in [plan["slide_id"], *[node["id"] for node in nodes]]):
        raise HtmlReviewError("运行对象ID不符合注册场景身份合同", code="SEMANTIC_RUNTIME_ID")
    duration = max(12000, len(plan["beats"]) * 3500)
    if duration > 120000:
        raise HtmlReviewError("语块过多，请拆页", code="SEMANTIC_CAPACITY")
    states = {obj["objectId"]: {"role": obj["role"], "initialVisible": obj["initialState"]["visible"]}
              for obj in plan["objectSemantics"]}
    motions, links = [], {}
    for index, beat in enumerate(plan["beats"]):
        used = {}
        for action in beat["actions"]:
            oid = action["objectId"]
            offset = used.get(oid, 0)
            motions.append({"actionId": action["actionId"], "targetId": oid, "type": action["type"],
                            "startMs": index * duration // len(plan["beats"]) + offset, "durationMs": 500,
                            **({"offsetX": 0, "offsetY": 0} if action["type"] == "enter" else {})})
            links[action["actionId"]] = {"beatId": beat["id"], "edge": "start", "offsetMs": 0}
            used[oid] = offset + 500
    scene = {"format": "hps.visual.scene", "version": "0.6.0", "id": plan["slide_id"],
             "name": str((plan["slots"].get("header") or {}).get("title") or plan["slide_id"]),
             "themeRef": {"id": "neutral-baseline", "version": "0.2.0"},
             "layoutRef": plan["layoutRef"], "templateRef": plan["templateRef"], "durationMs": duration,
             "nodes": nodes, "nodeStates": states, "motion": motions, "beats": [],
             "source": str(contract.get("source") or "课程讲稿；语义来源保存在规划中。")}
    # Annotation dependencies may need a later author preview time. Formal
    # binding recomputes ordering inside the actual spoken beat window.
    by_id = {node["id"]: node for node in nodes}
    ends = {oid: 0 if state["initialVisible"] else None for oid, state in states.items()}
    for motion in motions:
        node = by_id[motion["targetId"]]
        if node["type"] == "annotation":
            dependency = max(ends.get(node["targetId"]) or 0, ends.get(node["labelId"]) or 0)
            motion["startMs"] = max(motion["startMs"], dependency)
        if motion["type"] == "enter":
            ends[motion["targetId"]] = motion["startMs"] + motion["durationMs"]
    binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_action_ids",
               "actions": links, "narration": [{"id": beat["id"], "spoken_text": beat["spoken_text"],
                                                  "spoken_text_sha256": beat["spoken_text_sha256"]} for beat in plan["beats"]]}
    return scene, binding


def validate_semantic_binding(scene: dict, binding: dict | None, beat_ids: set | None = None) -> dict:
    from html_audio_binder import AudioBindingError

    def fail(code, message):
        raise AudioBindingError(code, message)

    if (scene.get("version") != "0.6.0" or not isinstance(binding, dict)
        or set(binding) != {"format", "version", "mode", "actions", "narration"}
        or binding.get("format") != "hps.html.motion_binding" or binding.get("version") != "0.2.0"
        or binding.get("mode") != "beat_action_ids" or not isinstance(binding.get("actions"), dict)):
        fail("AUDIO_BINDING_INVALID", "新语义场景必须使用完整actionId绑定，不允许旧比例时间")
    motions = scene.get("motion")
    if not isinstance(motions, list) or any(not isinstance(a, dict) or not isinstance(a.get("actionId"), str) for a in motions):
        fail("SCENE_MOTION_INVALID", "动作缺少稳定actionId")
    ids = [a["actionId"] for a in motions]
    if len(set(ids)) != len(ids) or set(binding["actions"]) != set(ids):
        fail("AUDIO_BINDING_INCOMPLETE", "每个动作必须且只能有一个明确语块绑定")
    nodes = scene.get("nodes")
    states = scene.get("nodeStates")
    if (not isinstance(nodes, list) or not isinstance(states, dict)
        or any(not isinstance(n, dict) or not isinstance(n.get("id"), str) for n in nodes)
        or set(states) != {n["id"] for n in nodes} or len(nodes) != len(states)):
        fail("SCENE_STATE_INVALID", "对象状态必须完整且唯一覆盖节点")
    for state in states.values():
        if (not isinstance(state, dict) or set(state) != {"role", "initialVisible"}
            or state["role"] not in ("instructional", "context", "decorative")
            or type(state["initialVisible"]) is not bool
            or state["role"] == "instructional" and state["initialVisible"]):
            fail("SCENE_STATE_INVALID", "对象初始状态不合法")
    entered = {oid for oid, state in states.items() if state["initialVisible"]}
    for motion in motions:
        oid = motion.get("targetId")
        if (not isinstance(oid, str) or oid not in states or motion.get("type") not in ("enter", "emphasize")
            or states[oid]["role"] == "decorative"):
            fail("SCENE_MOTION_INVALID", "动作目标/词汇不合法")
        if motion["type"] == "enter":
            if oid in entered:
                fail("SCENE_STATE_INVALID", "已显示对象不能重复进入")
            entered.add(oid)
        elif oid not in entered:
            fail("SCENE_STATE_INVALID", "隐藏对象不能强调")
    if any(state["role"] == "instructional" and oid not in entered for oid, state in states.items()):
        fail("SCENE_STATE_INVALID", "讲解对象缺少进入动作")
    narration = binding.get("narration")
    if not isinstance(narration, list) or not narration:
        fail("AUDIO_NARRATION_MISSING", "绑定缺少权威旁白")
    seen = set()
    for beat in narration:
        if (not isinstance(beat, dict) or set(beat) != {"id", "spoken_text", "spoken_text_sha256"}
            or not isinstance(beat.get("id"), str) or beat["id"] in seen
            or not isinstance(beat.get("spoken_text"), str) or not beat["spoken_text"].strip()
            or hashlib.sha256(beat["spoken_text"].encode()).hexdigest() != beat["spoken_text_sha256"]):
            fail("AUDIO_NARRATION_INVALID", "权威旁白身份/原句散列不一致")
        seen.add(beat["id"])
    if beat_ids is not None and seen != beat_ids:
        fail("AUDIO_BEAT_MISSING", "音频与权威语块集合不一致")
    for link in binding["actions"].values():
        if (not isinstance(link, dict) or set(link) != {"beatId", "edge", "offsetMs"}
            or link.get("beatId") not in seen or link.get("edge") != "start"
            or type(link.get("offsetMs")) is not int or not 0 <= link["offsetMs"] <= 120000):
            fail("AUDIO_BINDING_INVALID", "新动作只接受明确语块开始边界和非负偏移")
    return binding["actions"]


def bind_semantic_audio(scene: dict, timeline: dict, binding: dict | None) -> dict:
    from html_audio_binder import AudioBindingError, _segments, _audio_duration_sec

    segments = _segments(timeline)
    if any(type(s["start"]) not in (int, float) or type(s["end"]) not in (int, float) for s in segments):
        raise AudioBindingError("AUDIO_TIMESTAMP_INVALID", "真实时间不能使用布尔值")
    duration = round(_audio_duration_sec(timeline) * 1000)
    grouped = {}
    order = []
    for segment in segments:
        bid = segment.get("beat_id") or segment.get("id")
        if not isinstance(bid, str) or not bid:
            raise AudioBindingError("AUDIO_BEAT_ID_MISSING", "音频缺少稳定语块ID")
        if bid not in grouped:
            grouped[bid] = []
            order.append(bid)
        elif order[-1] != bid:
            raise AudioBindingError("AUDIO_BEAT_DUPLICATE", "同一语块音频必须连续")
        grouped[bid].append(segment)
    links = validate_semantic_binding(scene, binding, set(grouped))
    if order != [b["id"] for b in binding["narration"]]:
        raise AudioBindingError("AUDIO_BEAT_ORDER", "音频语块顺序与讲稿不一致")
    windows = {}
    for beat in binding["narration"]:
        parts = grouped[beat["id"]]
        if not _matches_spoken_parts(parts, beat["spoken_text"]):
            raise AudioBindingError("AUDIO_NARRATION_CHANGED", "真实配音原句与规划讲稿不一致")
        start, end = round(parts[0]["start"] * 1000), round(parts[-1]["end"] * 1000)
        if start >= end or end > duration:
            raise AudioBindingError("AUDIO_BEAT_OVERFLOW", "语块时间超出真实音频")
        windows[beat["id"]] = (start, end)
    bound = copy.deepcopy(scene)
    bound["durationMs"] = duration
    bound["beats"] = [{"startMs": round(s["start"] * 1000), "endMs": round(s["end"] * 1000), "text": s["text"]} for s in segments]
    states = scene.get("nodeStates", {})
    ends = {oid: 0 for oid, state in states.items() if state["initialVisible"]}
    last = dict(ends)
    by_id = {node["id"]: node for node in scene["nodes"]}
    for motion in bound["motion"]:
        link = links[motion["actionId"]]
        begin, finish = windows[link["beatId"]]
        oid = motion["targetId"]
        start = max(begin + link["offsetMs"], last.get(oid, 0))
        if motion["type"] == "emphasize":
            if oid not in ends:
                raise AudioBindingError("AUDIO_STATE_CONFLICT", "隐藏对象没有先进入")
            start = max(start, ends[oid])
        node = by_id[oid]
        if node["type"] == "annotation":
            if node["targetId"] not in ends or node["labelId"] not in ends:
                raise AudioBindingError("AUDIO_ANNOTATION_LIFETIME", "标注依赖尚未进入")
            start = max(start, ends[node["targetId"]], ends[node["labelId"]])
        authored = motion.get("durationMs")
        if type(authored) not in (int, float) or not 1 <= authored <= 10000:
            raise AudioBindingError("SCENE_MOTION_INVALID", "动作持续时间不合法")
        available = finish - start
        if available < 1:
            raise AudioBindingError("AUDIO_OFFSET_OVERFLOW", "动作无法在所属语块窗口执行")
        motion["startMs"], motion["durationMs"] = start, min(round(authored), available)
        last[oid] = start + motion["durationMs"]
        if motion["type"] == "enter":
            if oid in ends:
                raise AudioBindingError("AUDIO_STATE_CONFLICT", "已可见对象不能再次进入")
            ends[oid] = last[oid]
    return bound


def _spoken_key(text: str) -> str:
    return re.sub(r"\s+", "", text).rstrip("。.!！?？,，;；:：")


def _matches_spoken_parts(parts: list, text: str) -> bool:
    # Existing subtitles omit punctuation at explicit segment boundaries.
    # Compare each exact chunk before dropping only boundary punctuation.
    remaining = re.sub(r"\s+", "", text)
    for part in parts:
        chunk = _spoken_key(part["text"])
        if not chunk or not remaining.startswith(chunk):
            return False
        remaining = remaining[len(chunk):].lstrip("。.!！?？,，;；:：")
    return remaining == ""
