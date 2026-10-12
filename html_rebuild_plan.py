"""Pure dependency analysis. A reuse decision is not artifact validation or approval."""
import hashlib
import json

VERSION = "0.1.0"
PAGE_STAGES = ("scene_plan", "asset_generation", "asset_qa", "scene_compile", "static_qa",
               "temporal_qa", "visual_approval", "tts", "audio_alignment", "audio_confirmation",
               "subtitles", "motion_binding", "page_video")
PROJECT_STAGES = ("course_order", "subtitle_offsets", "reference_qa", "course_qa", "course_video", "future_task_identity")
VISUAL = ("scene_compile", "static_qa", "temporal_qa", "visual_approval", "page_video")
AUDIO = ("audio_alignment", "audio_confirmation", "subtitles", "motion_binding", "temporal_qa", "page_video")


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _check(value):
    allowed = {"pages", "order", "assets", "themes", "layouts", "templates", "fonts", "runtime", "models"}
    if not isinstance(value, dict) or set(value) - allowed or not isinstance(value.get("pages"), dict):
        raise ValueError("REBUILD_INPUT_INVALID")
    for identity, page in value["pages"].items():
        if not isinstance(identity, str) or not isinstance(page, dict) or set(page) - {"scene", "binding", "narration", "audio", "font_family"}:
            raise ValueError("REBUILD_PAGE_INVALID")
        if page.get("scene") is not None and (not isinstance(page["scene"], dict) or page["scene"].get("id") != identity):
            raise ValueError("REBUILD_PAGE_IDENTITY_INVALID")
    order = value.get("order", list(value["pages"]))
    if not isinstance(order, list) or any(not isinstance(x, str) for x in order) or len(order) != len(set(order)) or set(order) != set(value["pages"]):
        raise ValueError("REBUILD_ORDER_INVALID")
    for key in allowed - {"pages", "order", "models"}:
        if not isinstance(value.get(key, {}), dict):
            raise ValueError("REBUILD_DEPENDENCY_INVALID")


def _diff(a, b, path=()):
    if isinstance(a, list) and isinstance(b, list) and a and b and all(isinstance(n, dict) and "id" in n for n in a + b):
        return _diff({n["id"]: n for n in a}, {n["id"]: n for n in b}, path) + ([] if [n["id"] for n in a] == [n["id"] for n in b] else [list(path) + ["$order"]])
    if isinstance(a, dict) and isinstance(b, dict):
        return [p for key in sorted(a.keys() | b.keys()) for p in _diff(a.get(key), b.get(key), path + (key,))]
    return [] if a == b else [list(path)]


def _assets(scene):
    return {node["assetRef"]["id"] for node in (scene or {}).get("nodes", []) if isinstance(node.get("assetRef"), dict) and "id" in node["assetRef"]}


def plan_rebuild(before, after):
    """Compare full semantic inputs or actual content digests; no I/O or model calls."""
    _check(before)
    _check(after)
    project_work = {}
    pages = {}
    def project(reason, stages):
        for stage in stages:
            project_work.setdefault(stage, set()).add(reason)
    for identity in sorted(before["pages"].keys() | after["pages"].keys()):
        old, new = before["pages"].get(identity), after["pages"].get(identity)
        work = {}
        def require(reason, stages):
            for stage in stages:
                work.setdefault(stage, set()).add(reason)
        if new is None:
            pages[identity] = {"status": "removed", "rebuild": [], "reuse": [], "retain_historical": list(PAGE_STAGES), "diff": []}
            project("page_removed", ("course_order", "subtitle_offsets", "reference_qa", "course_qa", "course_video"))
            continue
        if old is None:
            require("page_added", PAGE_STAGES if new.get("scene") is None else tuple(s for s in PAGE_STAGES if s not in {"scene_plan", "asset_generation"}))
            project("page_added", ("course_order", "subtitle_offsets", "reference_qa", "course_qa", "course_video"))
            old = {}
        old_scene, new_scene = old.get("scene") or {}, new.get("scene") or {}
        differences = _diff(old_scene, new_scene)
        if differences:
            motion_only = {k: v for k, v in old_scene.items() if k not in {"motion", "durationMs"}} == {k: v for k, v in new_scene.items() if k not in {"motion", "durationMs"}}
            require("scene_changed", ("scene_compile", "temporal_qa", "visual_approval", "page_video") if motion_only else VISUAL)
            if old_scene.get("motion") != new_scene.get("motion") or old_scene.get("durationMs") != new_scene.get("durationMs"):
                require("motion_changed", ("motion_binding", "temporal_qa", "page_video"))
            if identity in before["pages"] and (old_scene.get("templateRef") != new_scene.get("templateRef") or old_scene.get("layoutRef") != new_scene.get("layoutRef") or
                [(n.get("id"), n.get("type"), n.get("slot")) for n in old_scene.get("nodes", [])] != [(n.get("id"), n.get("type"), n.get("slot")) for n in new_scene.get("nodes", [])]):
                require("registered_structure_changed", ("scene_plan",))
            if [n.get("assetRef") for n in old_scene.get("nodes", [])] != [n.get("assetRef") for n in new_scene.get("nodes", [])]:
                require("asset_reference_changed", ("asset_qa",))
        if old.get("binding") != new.get("binding"):
            require("binding_changed", ("motion_binding", "temporal_qa", "visual_approval", "page_video"))
        if old.get("narration") != new.get("narration"):
            require("narration_input_changed", ("tts",) + AUDIO)
        elif old.get("audio") != new.get("audio"):
            require("audio_artifacts_changed", AUDIO)
        referenced = _assets(old_scene) | _assets(new_scene)
        if any(before.get("assets", {}).get(asset) != after.get("assets", {}).get(asset) for asset in referenced):
            require("referenced_asset_bytes_changed", ("asset_qa",) + VISUAL)
        for ref, collection in (("themeRef", "themes"), ("layoutRef", "layouts"), ("templateRef", "templates")):
            identities = {scene.get(ref, {}).get("id") for scene in (old_scene, new_scene)} - {None}
            if any(before.get(collection, {}).get(key) != after.get(collection, {}).get(key) for key in identities):
                require(collection + "_definition_changed", VISUAL)
                if collection in {"templates", "layouts"}:
                    require(collection + "_definition_changed", ("scene_plan",))
        families = {old.get("font_family"), new.get("font_family")} - {None}
        if old.get("font_family") != new.get("font_family") or any(before.get("fonts", {}).get(font) != after.get("fonts", {}).get(font) for font in families):
            require("font_bytes_or_family_changed", VISUAL + ("subtitles",))
        if before.get("runtime", {}) != after.get("runtime", {}):
            require("shared_runtime_changed", VISUAL)
        if work:
            project("page:" + identity, ("course_qa", "course_video"))
        if old.get("narration") != new.get("narration") or old.get("audio") != new.get("audio") or old_scene.get("durationMs") != new_scene.get("durationMs"):
            project("timing:" + identity, ("subtitle_offsets",))
        pages[identity] = {"status": "added" if identity not in before["pages"] else "changed" if work else "unchanged",
                           "rebuild": [{"stage": stage, "reasons": sorted(work[stage])} for stage in PAGE_STAGES if stage in work],
                           "reuse": [stage for stage in PAGE_STAGES if stage not in work], "diff": differences}
    if before.get("order", list(before["pages"])) != after.get("order", list(after["pages"])):
        project("page_order_changed", ("course_order", "subtitle_offsets", "reference_qa", "course_qa", "course_video"))
    if before.get("models") != after.get("models"):
        project("model_configuration_changed", ("future_task_identity",))
    result = {"format": "hps.html.rebuild_plan", "version": VERSION,
              "before_sha256": _hash(before), "after_sha256": _hash(after), "pages": pages,
              "project": {"rebuild": [{"stage": stage, "reasons": sorted(project_work[stage])} for stage in PROJECT_STAGES if stage in project_work],
                          "reuse": [stage for stage in PROJECT_STAGES if stage not in project_work]},
              "no_op": not project_work and all(not p["rebuild"] and p["status"] != "removed" for p in pages.values()),
              "reuse_requires_artifact_validation": True, "approval_granted": False}
    result["plan_id"] = _hash(result)
    return result


def scene_rebuild(slide, before_scene, after_scene, before_binding=None, after_binding=None):
    return plan_rebuild({"pages": {slide: {"scene": before_scene, "binding": before_binding}}},
                        {"pages": {slide: {"scene": after_scene, "binding": after_binding}}})


def current_scene_plan(plan, slide, scene, binding):
    if not isinstance(plan, dict) or plan.get("format") != "hps.html.rebuild_plan" or plan.get("version") != VERSION:
        return None
    value = dict(plan)
    identity = value.pop("plan_id", None)
    expected = _hash({"pages": {slide: {"scene": scene, "binding": binding}}})
    return plan if identity == _hash(value) and plan.get("after_sha256") == expected else None
