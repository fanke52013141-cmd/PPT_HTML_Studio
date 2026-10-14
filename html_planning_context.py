"""Decision-only planning inputs. Audit metadata remains outside model context."""
from __future__ import annotations


def planning_context(contract: dict, brief: dict | None) -> dict:
    if not isinstance(contract, dict) or not isinstance(contract.get("narration_beats"), list) or not contract["narration_beats"]:
        raise ValueError("需要当前页完整权威讲稿")
    if brief is not None and not isinstance(brief, dict):
        raise ValueError("brief必须是对象")
    budget = (brief or {}).get("asset_budget", 1)
    if type(budget) is not int or not 0 <= budget <= 1:
        raise ValueError("当前语义设计的独立主体预算必须是0或1")
    beats = []
    seen = set()
    for beat in contract.get("narration_beats") or []:
        if not isinstance(beat, dict) or not isinstance(beat.get("id"), str) or not beat["id"].strip() or beat["id"] in seen:
            raise ValueError("讲稿语块ID必须唯一且非空")
        text = beat.get("spoken_text")
        if text is None:
            text = beat.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("讲稿原句必须非空")
        seen.add(beat["id"])
        beats.append({"id": beat.get("id"), "spoken_text": text})
    joined = "".join(str(b["spoken_text"] or "") for b in beats)
    title = contract.get("title") if contract.get("title") is not None else contract.get("main_title")
    if title is not None and not isinstance(title, str):
        raise ValueError("标题必须是文字")
    duplicates = {joined}
    if isinstance(title, str):
        duplicates.update({title + joined, title + "。" + joined})
    groups = []
    raw_groups = contract.get("visual_groups") or []
    if not isinstance(raw_groups, list):
        raise ValueError("视觉组必须是列表")
    for group in raw_groups:
        if not isinstance(group, dict):
            raise ValueError("视觉组必须是对象")
        if any(group.get(k) is not None and not isinstance(group[k], str) for k in
               ("id", "description", "content", "visible_text", "display_text", "visual_anchor")):
            raise ValueError("视觉组标识、描述和屏幕文字必须是字符串")
        row = {"id": group["id"]} if group.get("id") else {}
        description = group.get("description") or group.get("visual_anchor")
        if description:
            row["description"] = description
        # Only exact textual duplication is removed. Differing display copy
        # can be important; never summarize or guess semantic equivalence.
        content = group.get("content") or group.get("display_text") or group.get("visible_text")
        if content and content not in duplicates:
            row["content"] = content
        if group.get("available_assets"):
            if not isinstance(group["available_assets"], list) or any(not isinstance(item, dict) for item in group["available_assets"]):
                raise ValueError("已有素材声明必须是对象列表")
            row["available_assets"] = []
            for item in group["available_assets"]:
                ref = item.get("assetRef")
                if not isinstance(ref, dict) or any(not isinstance(ref.get(k), str) or not ref[k].strip() for k in ("id", "version")):
                    raise ValueError("已有素材必须有明确id/version")
                row["available_assets"].append({"assetRef": {k: ref[k] for k in ("id", "version")}, **({"description": item["description"]} if isinstance(item.get("description"), str) else {})})
        if row:
            groups.append(row)
    slide = {"slide_id": contract.get("slide_id"), "narration_beats": beats, "visual_groups": groups}
    if title:
        slide["title"] = title
    design = {k: brief[k] for k in ("templateRef", "theme", "asset_budget", "subtitle_reserve", "asset_needs") if brief and k in brief}
    if "asset_needs" in design:
        if not isinstance(design["asset_needs"], list) or any(not isinstance(a, dict) for a in design["asset_needs"]):
            raise ValueError("asset_needs必须是对象列表")
        design["asset_needs"] = [{k: a[k] for k in ("id", "role", "need", "slot") if k in a} for a in design["asset_needs"]]
    return {"slide": slide, "design_brief": design or None}
