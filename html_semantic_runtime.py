"""A03 pure plan-to-motion mapping. Audio resolution is owned by the binder."""
from __future__ import annotations

import copy

from html_semantic_design import build_semantic_design


def compile_semantic_motion(plan: dict) -> tuple[list, dict, list, int]:
    design = build_semantic_design(plan)
    duration = max(12000, len(plan["beats"]) * 3500)
    if duration > 120000:
        raise ValueError("Too many narration beats; split the slide")
    motion, links = [], {}
    objects = {o["id"]: o for o in plan["objects"]}
    for index, beat in enumerate(plan["beats"]):
        per_target = {}
        for action in beat["actions"]:
            target = action["objectId"]
            offset = per_target.get(target, 0) * 500
            per_target[target] = per_target.get(target, 0) + 1
            item = {"actionId": action["actionId"], "targetId": target,
                    "type": action["type"], "startMs": index * duration // len(plan["beats"]) + offset,
                    "durationMs": 500}
            if action["type"] == "enter":
                item.update(offsetX=0, offsetY=0 if objects[target]["kind"] == "annotation" else 12)
            motion.append(item)
            links[action["actionId"]] = {"beatId": beat["id"], "edge": "start", "offsetMs": offset}
    binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_ids",
               "actions": links, "sourceBeats": [{k: copy.deepcopy(b[k]) for k in
                    ("id", "spoken_text", "spoken_text_sha256")} for b in plan["beats"]]}
    return motion, binding, design["initialVisibleObjectIds"], duration
