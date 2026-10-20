"""Read-only repair advice and conservative dependency groups, never approval.

Geometry below is derived author geometry for explanations/search only. All
suggestions and all partial combinations must pass the original compiler/player.
"""
import copy
import math

from artifact_fingerprint import sha256_json
import html_scene_editing as editor


def geometry(packet, scene):
    layout = packet["context"]["style"]["layout"]
    boxes = {}
    for node in scene["nodes"]:
        box = copy.deepcopy(layout["slots"][node["slot"]]["box"])
        p = node.get("presentation", {})
        box.update(x=box["x"] + p.get("offsetX", 0), y=box["y"] + p.get("offsetY", 0),
                   width=p.get("width", box["width"]), height=p.get("height", box["height"]))
        boxes[node["id"]] = box
    return boxes


def _extent(scene, node_id, box):
    offsets = [(0, 0)] + [(a.get("offsetX", 0), a.get("offsetY", 0))
                         for a in scene["motion"] if a["targetId"] == node_id and a["type"] == "enter"]
    pad = 8 if any(a["targetId"] == node_id and a["type"] == "emphasize" for a in scene["motion"]) else 0
    return {"left": box["x"] + min(x for x, _ in offsets) - pad,
            "top": box["y"] + min(y for _, y in offsets) - pad,
            "right": box["x"] + box["width"] + max(x for x, _ in offsets) + pad,
            "bottom": box["y"] + box["height"] + max(y for _, y in offsets) + pad}


def operation_groups(packet, baseline, agent, operations):
    targets = sorted({op["targetId"] for op in operations})
    parent = {target: target for target in targets}
    def root(target):
        while parent[target] != target:
            target = parent[target]
        return target
    reasons = []
    def join(a, b, reason):
        if a in parent and b in parent and a != b:
            parent[root(b)] = root(a)
            reasons.append((a, b, reason))
    # Explicit relation objects can connect two edited targets through an unchanged annotation.
    for node in baseline["nodes"]:
        ids = [value for key, value in node.items() if key in ("id", "targetId", "labelId", "parentId") and isinstance(value, str) and value in parent]
        for a in ids:
            for b in ids:
                join(a, b, "显式对象引用")
    for a, b in packet["context"]["execution"].get("temporal_spec", {}).get("overlap_pairs", []):
        join(a, b, "指定遮挡验收对")
    envelopes = {}
    for scene in (baseline, agent):
        for target, box in geometry(packet, scene).items():
            if target not in parent:
                continue
            value = _extent(scene, target, box)
            previous = envelopes.get(target, value)
            envelopes[target] = {k: (min(previous[k], value[k]) if k in ("left", "top") else max(previous[k], value[k])) for k in value}
    for i, a in enumerate(targets):
        for b in targets[i+1:]:
            x, y = envelopes[a], envelopes[b]
            if x["left"] < y["right"] and y["left"] < x["right"] and x["top"] < y["bottom"] and y["top"] < x["bottom"]:
                join(a, b, "原页/候选及保留动作包络相交")
    groups = {}
    for index, op in enumerate(operations):
        groups.setdefault(root(op["targetId"]), []).append(index)
    return [{"id": sha256_json({"indices": indices, "operations": [operations[i] for i in indices]}),
             "operation_indices": indices, "targets": sorted({operations[i]["targetId"] for i in indices}),
             "operations": [operations[i] for i in indices],
             "reasons": sorted({why for a, b, why in reasons if root(a) == key and root(b) == key}) or ["同一对象的字号、尺寸和位置整体采用"],
             "requires_full_check": True} for key, indices in groups.items()]


def selected_operations(groups, operations, selected):
    known = {g["id"] for g in groups}
    if selected is not None and (len(selected) != len(set(selected)) or not set(selected) <= known):
        raise ValueError("关联组已变化或包含未知组，请重新读取工作草稿")
    indices = {i for g in groups if selected is None or g["id"] in selected for i in g["operation_indices"]}
    return [op for i, op in enumerate(operations) if i in indices]


def _capacity(packet, scene, width_delta=0, height_delta=0):
    # Same production relationship capacity owner; derived boxes are not validation.
    return editor._node("""
const fs=require('fs'),p=JSON.parse(fs.readFileSync(0,'utf8'));
const layout=structuredClone(p.layout);
for(const n of p.scene.nodes){const b=layout.slots[n.slot].box,pres=n.presentation||{};
 layout.slots[n.slot].box={...b,x:b.x+(pres.offsetX||0),y:b.y+(pres.offsetY||0),
 width:(pres.width??b.width)+p.dw,height:(pres.height??b.height)+p.dh};}
console.log(JSON.stringify(require('./html_engine/visual/relationship-capacity.cjs').constraints(
 p.scene,layout,require('./html_engine/visual/presentation-variants.json').variants)));
""", {"scene": scene, "layout": packet["context"]["style"]["layout"], "dw": width_delta, "dh": height_delta})


def advice(packet, scene, checked, working_hash):
    boxes = geometry(packet, scene)
    baseline_boxes = geometry(packet, packet["context"].get("scene", scene))
    names = {n["id"]: {"summary": "底栏", "headline": "重点文字", "header": "页面标题", "card": "内容卡片", "figure": "插图"}.get(n["type"], n["id"]) for n in scene["nodes"]}
    parts = {"from": "左侧标签", "to": "右侧标签", "heading": "标题", "term": "术语", "takeaway": "结论"}
    canvas = packet["context"]["style"]["layout"]["canvas"]
    limit_x, limit_y = canvas["width"], canvas["contentBottom"]
    measurements = (checked or {}).get("diagnostic", {}) or {}
    measurements = measurements.get("capacity_measurements", {}) or ((checked or {}).get("review", {}) or {}).get("capacity_measurements", {})
    current = _capacity(packet, scene)
    wider = {v["targetId"]: v for v in _capacity(packet, scene, width_delta=1)}
    taller = {v["targetId"]: v for v in _capacity(packet, scene, height_delta=1)}
    messages, proposed, blocked = [], {}, []
    for item in current:
        target = item["targetId"]
        if target not in packet["scope"]:
            continue
        for part, fact in item["parts"].items():
            measured = measurements.get(target + ":" + part, {})
            if measured.get("units") != "logical_canvas_px":
                continue
            for dimension, axis, next_facts in (("height", "高度", taller), ("width", "宽度", wider)):
                actual = measured.get("measured", {}).get(dimension)
                budget = fact["effective_limits"][dimension]
                if not isinstance(actual, (float, int)) or not math.isfinite(actual):
                    continue
                tolerance = fact.get("tolerance", {}).get(dimension, 1)
                deficit = actual - budget
                if deficit <= tolerance:
                    continue
                slope = next_facts[target]["parts"][part]["effective_limits"][dimension] - budget
                text = f"{names[target]}的{parts.get(part, part)}实测{axis} {actual:.2f}px，当前预算 {budget:.2f}px，超出 {deficit:.2f}px（容差 {tolerance}px）。"
                messages.append({"code": "CAPACITY_DEFICIT", "targetId": target, "part": part, "dimension": dimension,
                                 "actual": actual, "limit": budget, "deficit": deficit, "tolerance": tolerance,
                                 "source": "current_original_dom_and_production_capacity", "message": text})
                if slope > 0:
                    proposed.setdefault(target, {})[dimension] = max(proposed.get(target, {}).get(dimension, boxes[target][dimension]),
                                                                    boxes[target][dimension] + math.ceil(deficit/slope) + 2)
                else:
                    blocked.append(f"{target}/{part} 的{axis}无法仅调整父框解决，请人工检查换行或合法变体。")
    for node in scene["nodes"]:
        target = node["id"]
        if target not in packet["scope"] or node["type"] == "annotation":
            continue
        original = boxes[target]
        box = {**original, **proposed.get(target, {})}
        extent = _extent(scene, target, box)
        dx_min, dx_max = -extent["left"], limit_x - extent["right"]
        dy_min, dy_max = -extent["top"], limit_y - extent["bottom"]
        if dx_min > dx_max or dy_min > dy_max:
            proposed.pop(target, None)
            blocked.append(f"{target} 扩框后连同原动作无法放进内容区，不能自动联动；请人工选择合法方案。")
            continue
        dx, dy = max(dx_min, min(0, dx_max)), max(dy_min, min(0, dy_max))
        if dx or dy:
            # A bad offset should not move a headline above its title merely
            # because y=0 is legal. Prefer the original author/template location
            # on violated axes if the resized box and retained actions still fit.
            preferred = {**box, "x": baseline_boxes[target]["x"] if dx else box["x"],
                         "y": baseline_boxes[target]["y"] if dy else box["y"]}
            bounds = _extent(scene, target, preferred)
            if bounds["left"] >= 0 and bounds["top"] >= 0 and bounds["right"] <= limit_x and bounds["bottom"] <= limit_y:
                dx, dy = preferred["x"]-box["x"], preferred["y"]-box["y"]
        if dx or dy:
            values = proposed.setdefault(target, {})
            p = node.get("presentation", {})
            if dx:
                values["offsetX"] = p.get("offsetX", 0) + dx
            if dy:
                values["offsetY"] = p.get("offsetY", 0) + dy
            overflow = {"左侧": max(0, -extent["left"]), "上方": max(0, -extent["top"]),
                        "右侧": max(0, extent["right"]-limit_x), "底部": max(0, extent["bottom"]-limit_y)}
            edges = "、".join(f"{edge}超出 {amount:.2f}px" for edge, amount in overflow.items() if amount)
            messages.append({"code": "RETAINED_MOTION_MARGIN", "targetId": target, "source": "registered_layout_and_retained_actions",
                             "message": f"{names[target]}连同原入场/强调范围{edges}；建议水平移动 {dx:.2f}px、垂直移动 {dy:.2f}px，保留全部动作参数。",
                             "dx": dx, "dy": dy, "content_right": limit_x, "content_bottom": limit_y})
    validation = ((checked or {}).get("review", {}) or {}).get("validation")
    if validation:
        messages.append({"code": validation.get("code", "ORIGINAL_CHECK"), "message": "原系统检查：" + validation.get("message", "未通过，请检查原始诊断")})
    for target, values in proposed.items():
        for key, text in (("height", "增高"), ("width", "加宽")):
            if key in values:
                messages.append({"code": "PARENT_BOX_ESTIMATE", "targetId": target,
                                 "message": f"建议将{names[target]}{text} {values[key]-boxes[target][key]:.2f}px，再联动位置避开原动作边界；需实际预览确认。",
                                 "source": "production_capacity_sensitivity_estimate", "dimension": key,
                                 "before": boxes[target][key], "proposed": values[key]})
    operations = [{"targetId": target, "kind": "set_presentation", "values": values} for target, values in sorted(proposed.items())]
    proposal = {"title": "联动调整父框与位置（保留字号和动作）", "operations": operations,
                "base_work_hash": working_hash, "preview_required": True, "automatic": False}
    proposal["id"] = sha256_json(proposal)
    return {"base_work_hash": working_hash, "messages": messages, "blocked": blocked,
            "proposals": [proposal] if operations else [], "boundary": "估算仅用于提出方案；原检查通过预览并确认后才写工作草稿，不是视觉批准。"}


def merge_operations(existing, additions):
    result = copy.deepcopy(existing)
    for op in additions:
        previous = next((v for v in result if (v["targetId"], v["kind"], v.get("part")) == (op["targetId"], op["kind"], op.get("part"))), None)
        if previous is None:
            result.append(copy.deepcopy(op))
        else:
            previous["values"].update(op["values"])
    return result
