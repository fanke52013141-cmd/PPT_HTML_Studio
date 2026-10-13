"""Pure A02 allocation and beat-state projection, without model calls or clocks."""
from __future__ import annotations

from artifact_fingerprint import sha256_json
from html_semantic_plan import normalize_semantics, SemanticPlanError


def build_semantic_design(plan: dict, *, asset_budget: int = 1) -> dict:
    """Consume normalized A01; unsupported content changes fail before generation.

    State descriptions are author/model claims, not observations or semantic QA.
    A single raster asset cannot change its internal content per beat.
    """
    def fail(code, message):
        raise SemanticPlanError(code, message)

    if plan.get("version") != "0.2.0":
        fail("SEMANTIC_DESIGN_VERSION", "语义设计只接收 0.2.0 计划")
    if type(asset_budget) is not int or not 0 <= asset_budget <= 1:
        fail("SEMANTIC_DESIGN_BUDGET", "当前语义生产最多一个独立主体；多素材须先扩展生产适配")
    # Revalidate shape and source hashes at the consumer; these fields were
    # bound to the authority upstream. This does not establish new authority.
    source = {"narration_beats": [{"id": b.get("id"), "spoken_text": b.get("spoken_text")} for b in plan.get("beats", [])]}
    objects, beats = normalize_semantics(plan, plan["objects"], source)
    assets = plan.get("assets", [])
    asset_ids = [a["id"] for a in assets]
    if len(asset_ids) != len(set(asset_ids)):
        fail("SEMANTIC_ASSET_DUPLICATE", "素材身份重复")
    image_needs = [a for a in assets if a["render_owner"] == "image_asset"]
    if len(image_needs) > asset_budget:
        fail("SEMANTIC_DESIGN_BUDGET", "独立主体超过预算，需重新分配表达")
    images = {o["slot"]: o for o in objects if o["kind"] == "image"}
    if set(images) != {a.get("slot") for a in image_needs} or len(image_needs) != len(images):
        fail("SEMANTIC_ASSET_OWNERSHIP", "每个图片对象必须与一个显式 image_asset 需求一一对应")
    by_slot = {a["slot"]: a for a in image_needs}
    allocations = []
    for obj in objects:
        content = plan["slots"][obj["slot"]]
        if obj["kind"] != content.get("kind"):
            fail("SEMANTIC_SLOT_KIND", "对象类型必须与对应内容槽位一致")
        if obj.get("exit") or obj.get("transitional"):
            fail("SEMANTIC_STATE_UNSUPPORTED", "当前语义动作未定义 exit；不能承诺过渡对象消失")
        row = {k: obj[k] for k in ("id", "slot", "kind", "role", "initialVisible")}
        if obj.get("initialVisibleReason"):
            row["initialVisibleReason"] = obj["initialVisibleReason"]
        row["render_owner"] = "image_asset" if obj["kind"] == "image" else "code"
        if obj["kind"] == "image":
            asset = by_slot[obj["slot"]]
            ref = content.get("assetRef", {})
            if ref.get("id") != asset["id"] or not isinstance(ref.get("version"), str) or not ref["version"].strip():
                fail("SEMANTIC_ASSET_IDENTITY", "主体需求与图片槽位 assetRef 的身份/版本不一致")
            row["assetRef"] = dict(ref)
            row["control"] = "whole_asset_only"
        else:
            row["control"] = "registered_code_object"
        allocations.append(row)
    visible = {o["id"] for o in objects if o["initialVisible"]}
    initial = sorted(visible)
    image_ids = {o["id"] for o in objects if o["kind"] == "image"}
    image_expressions = {}
    steps = []
    for beat in beats:
        for action in beat["actions"]:
            if action["type"] == "enter":
                visible.add(action["objectId"])
            elif action["objectId"] not in visible:
                fail("SEMANTIC_ACTION_BEFORE_ENTER", "对象强调前须已进入；不能依赖 0ms 隐式显示")
        for state in beat["expectedState"]:
            if state["objectId"] not in visible:
                fail("SEMANTIC_EXPECTED_INVISIBLE", "声明的预期可见对象尚未进入")
            if state["objectId"] in image_ids:
                prior = image_expressions.setdefault(state["objectId"], state["expression"])
                if prior != state["expression"]:
                    fail("SEMANTIC_IMAGE_STATE_CHANGE", "同一静态主体不得声明不同内部状态；拆成代码对象/独立素材后重规划")
        step = {k: beat[k] for k in ("id", "visualIntent", "targets", "actions", "expectedState", "narration_only")}
        # Source text is needed once to check design relevance. Hash stays in
        # the plan/evidence, not in the image prompt.
        step["spoken_text"] = beat["spoken_text"]
        if beat.get("narrationOnlyReason"):
            step["narrationOnlyReason"] = beat["narrationOnlyReason"]
        step["visibleObjectIds"] = sorted(visible)
        steps.append(step)
    hidden = {o["id"] for o in objects} - visible
    if hidden:
        fail("SEMANTIC_OBJECT_NEVER_VISIBLE", "非初始对象缺少显式进入：" + ", ".join(sorted(hidden)))
    result = {
        "format": "hps.html.semantic_design", "version": "0.1.0",
        "slide_id": plan["slide_id"], "allocations": allocations,
        "initialVisibleObjectIds": initial, "steps": steps,
        "finalVisibleObjectIds": sorted(visible),
        "plan_sha256": sha256_json(plan), "semantic_review": "pending_review",
    }
    result["sha256"] = sha256_json(result)
    return result


def semantic_design_context(design: dict) -> dict:
    """Only image-design decisions; retain full source and state evidence on disk."""
    return {
        "objects": design["allocations"],
        "initialVisibleObjectIds": design["initialVisibleObjectIds"],
        "beats": [{k: v for k, v in s.items() if k not in ("actions", "visibleObjectIds")} for s in design["steps"]],
        "finalVisibleObjectIds": design["finalVisibleObjectIds"],
    }
