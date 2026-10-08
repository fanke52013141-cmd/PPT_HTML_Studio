"""N02 author editing; strict production compiler remains the validator.

No database or provider calls. Callers hold the project lock and invalidate only
when changed. Anchor variants are private immutable resources, never edits of a
shared resource. Ordinary write failures roll back; crash recovery is separate.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import re
import subprocess
from pathlib import Path

from PIL import Image

import html_visual_store as store

ROOT = Path(__file__).resolve().parent
ID = re.compile(r"^[a-z][a-z0-9.-]{0,63}$")


class SceneEditError(store.HtmlVisualError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def edit_path(run, slide):
    return Path(run) / store.SCENE_DIR / f"edits-{store.validate_slide_id(slide)}.json"


def binding_path(run, slide):
    return (
        Path(run) / store.SCENE_DIR / f"binding-{store.validate_slide_id(slide)}.json"
    )


def _digest(value):
    return hashlib.sha256(store._document_bytes(value)).hexdigest()


def _node(script, payload):
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(payload),
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if result.returncode:
        raise SceneEditError("SCENE_INVALID", result.stderr[-5000:])
    return json.loads(result.stdout)


def capabilities():
    schema = read_json(ROOT / "html_engine/visual/schema.json")
    return {
        "schema": schema,
        "actions": [
            s["properties"]["type"]["const"] for s in schema["$defs"]["motion"]["oneOf"]
        ],
    }


def resources(run):
    """Validate real resource bytes with the existing production resource loader."""
    path = Path(run) / store.SCENE_DIR / "resources.json"
    return _node(
        """
const fs=require('fs'); const p=JSON.parse(fs.readFileSync(0,'utf8'));
delete process.env.HPS_HTML_RESOURCES;
if(p.path) process.env.HPS_HTML_RESOURCES=p.path;
console.log(JSON.stringify(require('./html_engine/tools/project-resources.cjs').loadProjectResources()||{assets:[],pack:{}}));
""",
        {"path": str(path.resolve()) if path.is_file() else None},
    )


def beats_for(run, slide):
    contract = read_json(Path(run) / "planning/visual_contract.json", {})
    page = next(
        (s for s in contract.get("slides", []) if s.get("slide_id") == slide), {}
    )
    return page.get("narration_beats", [])


def load_editor(run, slide):
    doc = store.load_scene_with_revision(run, slide)
    if doc is None:
        raise SceneEditError("SCENE_MISSING", "请先生成此页场景")
    return {
        **doc,
        "binding": read_json(binding_path(run, slide)),
        "anchor_overrides": {},
        "beats": beats_for(run, slide),
        "resources": resources(run),
        "capabilities": capabilities(),
        "manual": read_json(edit_path(run, slide)),
        "preview_clock": "author",
        "audio_status": "作者时钟；输出使用已确认音频的语块绑定",
    }


def _validate_binding(binding, scene, beats):
    if binding is None:
        return
    if set(binding) != {"format", "version", "mode", "actions"} or (
        binding.get("format"),
        binding.get("version"),
        binding.get("mode"),
    ) != ("hps.html.motion_binding", "0.1.0", "beat_ids"):
        raise SceneEditError("BINDING_INVALID", "动作语块绑定格式不合法")
    valid = {f"{a['targetId']}:{a['type']}" for a in scene["motion"]}
    beat_ids = {b.get("beat_id") or b.get("id") for b in beats}
    if not isinstance(binding["actions"], dict):
        raise SceneEditError("BINDING_INVALID", "actions 必须为对象")
    for key, value in binding["actions"].items():
        if key not in valid:
            raise SceneEditError("BINDING_TARGET_GONE", f"动作已删除：{key}")
        if not isinstance(value, dict) or set(value) != {"beatId", "edge", "offsetMs"}:
            raise SceneEditError("BINDING_INVALID", f"绑定字段错误：{key}")
        if value["beatId"] not in beat_ids:
            raise SceneEditError("BEAT_GONE", f"讲稿语块已删除：{value['beatId']}")
        if (
            value["edge"] not in ("start", "end")
            or type(value["offsetMs"]) is not int
            or abs(value["offsetMs"]) > 120000
        ):
            raise SceneEditError("BINDING_INVALID", f"边界或偏移错误：{key}")


def _anchor_variants(run, scene, overrides, project_resources):
    catalog = read_json(ROOT / "html_engine/visual/generated/catalog.json")
    assets = {a["id"]: a for a in catalog["assets"] + project_resources["assets"]}
    manifest = read_json(Path(run) / store.SCENE_DIR / "resources.json", {"assets": []})
    additions, files = [], {}
    for node_id, anchors in overrides.items():
        node = next((n for n in scene["nodes"] if n["id"] == node_id), None)
        if not node or node["type"] != "image":
            raise SceneEditError("TARGET_NODE_GONE", f"图片对象不存在：{node_id}")
        asset = assets.get(node["assetRef"]["id"])
        if not asset or asset["version"] != node["assetRef"]["version"]:
            raise SceneEditError("ASSET_GONE", "图片资源版本不存在")
        if not isinstance(anchors, list) or not 1 <= len(anchors) <= 16:
            raise SceneEditError("ANCHOR_INVALID", "锚点数量必须为1–16")
        ids = set()
        for a in anchors:
            if (
                not isinstance(a, dict)
                or set(a) != {"id", "x", "y"}
                or not isinstance(a["id"], str)
                or not ID.fullmatch(a["id"])
                or a["id"] in ids
            ):
                raise SceneEditError("ANCHOR_INVALID", "锚点名称重复或不合法")
            ids.add(a["id"])
            if any(
                type(a[k]) not in (float, int)
                or not math.isfinite(a[k])
                or not 0 <= a[k] < 1
                for k in ("x", "y")
            ):
                raise SceneEditError("ANCHOR_BOUNDS", "锚点必须在原图内部")
        if anchors == asset["anchors"]:
            continue
        record = next((a for a in manifest["assets"] if a["id"] == asset["id"]), None)
        if record:
            original = (Path(run) / record["file"]).resolve()
            if not original.is_relative_to(Path(run).resolve()):
                raise SceneEditError("ASSET_PATH_ESCAPE", "资源越界")
        else:
            original = (ROOT / asset["file"]["path"]).resolve()
            if not original.is_relative_to(ROOT):
                raise SceneEditError("ASSET_PATH_ESCAPE", "资源越界")
        data = original.read_bytes()
        if hashlib.sha256(data).hexdigest() != asset["file"]["sha256"]:
            raise SceneEditError("ASSET_HASH_MISMATCH", "资源字节已变化")
        with Image.open(io.BytesIO(data)) as image:
            image = image.convert("RGBA")
            w, h = image.size
            pixels = [
                {
                    "id": a["id"],
                    "x": min(w - 1, round(a["x"] * w)),
                    "y": min(h - 1, round(a["y"] * h)),
                }
                for a in anchors
            ]
            if any(image.getpixel((a["x"], a["y"]))[3] == 0 for a in pixels):
                raise SceneEditError("ANCHOR_EMPTY", "锚点落在透明区域，请选择主体内部")
            bbox = list(image.getbbox())
        variant_id = (
            "edit-"
            + _digest(
                {
                    "slide": scene["id"],
                    "node": node_id,
                    "sha": asset["file"]["sha256"],
                    "anchors": pixels,
                }
            )[:32]
        )
        relative = str(store.SCENE_DIR / "editor-assets" / f"{variant_id}.png").replace(
            "\\", "/"
        )
        variant = {
            "id": variant_id,
            "version": "0.1.0",
            "file": relative,
            "sha256": asset["file"]["sha256"],
            "size": [w, h],
            "alpha_bbox": bbox,
            "anchors": pixels,
            "source": {
                "kind": "manual_anchor_variant",
                "asset_id": asset["id"],
                "provenance": (record or {}).get("source"),
            },
        }
        additions.append(variant)
        files[Path(run) / relative] = data
        node["assetRef"] = {"id": variant_id, "version": "0.1.0"}
        runtime = copy.deepcopy(asset)
        runtime["id"] = variant_id
        runtime["anchors"] = [
            {"id": a["id"], "x": a["x"] / w, "y": a["y"] / h} for a in pixels
        ]
        assets[variant_id] = runtime
    for item in additions:
        manifest["assets"] = [
            a for a in manifest["assets"] if a["id"] != item["id"]
        ] + [item]
    return list(assets.values()), manifest, files


def _compile(scene, assets):
    return _node(
        """
const fs=require('fs'),p=JSON.parse(fs.readFileSync(0,'utf8'));
const c=require('./html_engine/visual/generated/catalog.json');c.assets=p.assets;
try{const r=require('./html_engine/visual/compiler.cjs').compile(p.scene,c);console.log(JSON.stringify(r.source));}
catch(e){process.stderr.write(e.message);process.exitCode=1;}
""",
        {"scene": scene, "assets": assets},
    )


def preview_editor(run, slide, scene, binding, anchor_overrides=None):
    """Resolve timing through the existing binder; no writes or TTS."""
    scene = copy.deepcopy(scene)
    project = resources(run)
    assets, _, _ = _anchor_variants(run, scene, anchor_overrides or {}, project)
    # Variants use the original pixel pack in previews; save materializes them.
    runtime_assets = [
        a
        for a in assets
        if a["id"]
        not in {
            b["id"]
            for b in read_json(ROOT / "html_engine/visual/generated/catalog.json")[
                "assets"
            ]
        }
    ]
    _validate_binding(binding, scene, beats_for(run, slide))
    timeline = read_json(
        Path(run) / "slides" / store.validate_slide_id(slide) / "audio_timeline.json"
    )
    clock = "author"
    if timeline is not None:
        from html_audio_binder import bind_scene_to_audio, AudioBindingError

        try:
            scene = bind_scene_to_audio(scene, timeline, binding)
        except AudioBindingError as exc:
            raise SceneEditError(exc.code, str(exc)) from exc
        clock = "audio_timeline"
    _compile(scene, assets)
    return {
        "scene": scene,
        "resources": {"assets": runtime_assets, "pack": project["pack"]},
        "clock": clock,
        "audio_status": "现有音频时间轴（输出仍检查确认状态）"
        if timeline
        else "作者时钟；尚无音频时间轴，beat 绑定在输出时解析",
    }


def merge_manual_edits(candidate, binding, manual):
    """Reapply changed fields by stable IDs; return conflicts without hiding them."""
    result, links = copy.deepcopy(candidate), copy.deepcopy(binding)
    conflicts = []
    if not manual:
        return {"scene": result, "binding": links, "conflicts": conflicts}
    base, edited = manual["base_scene"], manual["scene"]
    for collection, identity in (
        ("nodes", lambda n: n["id"]),
        ("motion", lambda a: f"{a['targetId']}:{a['type']}"),
    ):
        before = {identity(n): n for n in base[collection]}
        after = {identity(n): n for n in edited[collection]}
        current = {identity(n): n for n in result[collection]}
        for key in before.keys() | after.keys():
            if before.get(key) == after.get(key):
                continue
            old, new, target = before.get(key), after.get(key), current.get(key)
            if new is None:
                current.pop(key, None)
            elif (
                target is None
                and collection == "motion"
                and new["targetId"] in {n["id"] for n in result["nodes"]}
            ):
                current[key] = copy.deepcopy(new)
            elif target is None or (old and target.get("type") != old.get("type")):
                conflicts.append(
                    {"target": key, "code": "MANUAL_TARGET_CONFLICT", "override": new}
                )
            else:
                for field in (old or {}).keys() | new.keys():
                    if (old or {}).get(field) != new.get(field):
                        if field in new:
                            target[field] = copy.deepcopy(new[field])
                        else:
                            target.pop(field, None)
        result[collection] = list(current.values())
    if manual.get("base_binding") != manual.get("binding"):
        original = (manual.get("base_binding") or {}).get("actions", {})
        changed = (manual.get("binding") or {}).get("actions", {})
        links = links or {
            "format": "hps.html.motion_binding",
            "version": "0.1.0",
            "mode": "beat_ids",
            "actions": {},
        }
        for key in original.keys() | changed.keys():
            if original.get(key) != changed.get(key):
                if key in changed:
                    links["actions"][key] = copy.deepcopy(changed[key])
                else:
                    links["actions"].pop(key, None)
    return {"scene": result, "binding": links, "conflicts": conflicts}


def save_editor(run, slide, scene, binding, expected_revision, anchor_overrides=None):
    """Caller must hold project_artifact_lock across this operation."""
    document = store.load_scene_with_revision(run, slide)
    if not document:
        raise SceneEditError("SCENE_MISSING", "场景不存在")
    if type(expected_revision) is not int or expected_revision < 0:
        raise SceneEditError("REVISION_INVALID", "expected_revision 必须是非负整数")
    if document["revision"] != expected_revision:
        raise store.HtmlVisualConflict(expected_revision, document["revision"])
    scene = copy.deepcopy(scene)
    _node(
        """
const fs=require('fs'),p=JSON.parse(fs.readFileSync(0,'utf8'));
if(['0.1.0','0.2.0'].includes(p.version)){p.version='0.3.0';p.themeRef.version='0.2.0';p.layoutRef.version='0.2.0';}
try{require('./html_engine/visual/compiler.cjs').validate('scene',p);console.log('{}');}
catch(e){process.stderr.write(e.message);process.exitCode=1;}
""",
        scene,
    )
    if scene.get("id") != slide:
        raise SceneEditError("SCENE_ID_INVALID", "页面 ID 不一致")
    # Editing is deliberately narrower than raw authoring: stable structure.
    for key in set(scene) | set(document["scene"]):
        if key not in ("nodes", "motion") and scene.get(key) != document["scene"].get(
            key
        ):
            raise SceneEditError("STRUCTURE_LOCKED", f"本编辑器不修改 {key}")
    if [(n["id"], n["type"], n["slot"]) for n in scene["nodes"]] != [
        (n["id"], n["type"], n["slot"]) for n in document["scene"]["nodes"]
    ]:
        raise SceneEditError("STRUCTURE_LOCKED", "对象身份/类型/槽位不可更改")
    existing_binding = read_json(binding_path(run, slide))
    _validate_binding(binding, scene, beats_for(run, slide))
    project_resources = resources(run)
    assets, manifest, files = _anchor_variants(
        run, scene, anchor_overrides or {}, project_resources
    )
    _compile(scene, assets)  # Validate without silently migrating stored source.
    timeline = read_json(Path(run) / "slides" / slide / "audio_timeline.json")
    if timeline is not None:
        from html_audio_binder import bind_scene_to_audio, AudioBindingError

        try:
            _compile(bind_scene_to_audio(scene, timeline, binding), assets)
        except AudioBindingError as exc:
            raise SceneEditError(exc.code, str(exc)) from exc
    changed = scene != document["scene"] or binding != existing_binding
    if not changed:
        return {
            "revision": expected_revision,
            "changed": False,
            "sha256": document["sha256"],
        }
    previous = read_json(edit_path(run, slide))
    manual = {
        "format": "hps.html.scene_edits",
        "version": "0.1.0",
        "slide_id": slide,
        "base_revision": (previous or {}).get("base_revision", expected_revision),
        "base_scene": (previous or {}).get("base_scene", document["scene"]),
        "base_binding": (previous or {}).get("base_binding", existing_binding),
        "scene": scene,
        "binding": binding,
    }
    directory = Path(run) / store.SCENE_DIR
    files.update(
        {
            store.scene_path(run, slide): store._document_bytes(scene),
            edit_path(run, slide): store._document_bytes(manual),
            binding_path(run, slide): store._document_bytes(binding)
            if binding is not None
            else None,
            store.revision_path(run): store._document_bytes(
                {"revision": expected_revision + 1}
            ),
        }
    )
    if anchor_overrides:
        files[directory / "resources.json"] = store._document_bytes(manifest)
    backups = {p: p.read_bytes() if p.exists() else None for p in files}
    try:
        for path, data in files.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                store._atomic_write_bytes(path, data)
    except Exception:
        for path, data in backups.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                store._atomic_write_bytes(path, data)
        raise
    return {
        "revision": expected_revision + 1,
        "changed": True,
        "sha256": _digest(scene),
    }
