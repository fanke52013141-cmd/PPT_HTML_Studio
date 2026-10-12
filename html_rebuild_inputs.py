"""Read-only capture of actual inputs for S03; the planner remains filesystem-free."""
import json
from pathlib import Path
import os

from html_build_snapshot import safe_file, fresh_hash
from html_visual_store import validate_slide_id, scene_path
from pipeline_lifecycle import project_artifact_lock


def capture_inputs(run_dir, *, repo_root=None):
    run = Path(run_dir).resolve()
    root = Path(repo_root or Path(__file__).parent).resolve()
    observed = {}
    def read(path, default=None):
        if not path.is_file():
            observed[path] = None
            return default
        data = path.read_bytes()
        from html_build_snapshot import digest
        actual = digest(data)
        if path in observed and observed[path] != actual:
            raise ValueError("REBUILD_INPUT_CHANGED")
        observed[path] = actual
        return json.loads(data.decode("utf-8-sig"))
    def content_hash(path):
        if path not in observed:
            observed[path] = fresh_hash(path) if path.is_file() else None
        return observed[path]
    with project_artifact_lock(run):
        contract = read(run / "planning/visual_contract.json", {"slides": []})
        rows = contract["slides"]
        narration = read(run / "planning/narration_beats.json", {"slides": []})
        spoken = {page["slide_id"]: page for page in narration["slides"]}
        result = {"pages": {}, "order": [], "assets": {}, "themes": {}, "layouts": {}, "templates": {}, "fonts": {}}
        result["runtime"] = {name: content_hash(root / "html_engine/visual" / name) for name in (
            "preview/player.js", "generated/catalog.json", "assets.json", "preview/data.js", "icons.cjs", "effects/registry.json", "schema.json",
        )}
        manifest = read(run / "planning/html_visual/resources.json", {"assets": []})
        project_assets = {a["id"]: a for a in manifest["assets"]}
        runtime = read(root / "html_engine/visual/generated/catalog.json", {"assets": []})
        builtin = {a["id"]: a for a in runtime["assets"]}
        for row in rows:
            slide = validate_slide_id(row["slide_id"])
            if slide in result["pages"]:
                raise ValueError("REBUILD_DUPLICATE_PAGE")
            scene = read(scene_path(run, slide))
            from tts_artifacts import artifact_paths, REQUIRED_OUTPUT_KEYS
            paths = artifact_paths(run, slide)
            beats = row.get("narration_beats", [])
            spoken_beats = spoken.get(slide, {}).get("beats", beats)
            page = {"scene": scene,
                    "binding": {"author": read(run / f"planning/html_visual/binding-{slide}.json"), "beat_ids": [b.get("id") for b in beats]},
                    "narration": {"speech": row.get("narration", ""), "beat_texts": [b.get("tts_text", b.get("spoken_text", b.get("text", ""))) for b in spoken_beats], "tts_text_sha256": content_hash(paths["text"])},
                    "audio": {key: content_hash(paths[key]) for key in REQUIRED_OUTPUT_KEYS}}
            result["pages"][slide] = page
            result["order"].append(slide)
            for key, directory in (("themeRef", "themes"), ("layoutRef", "layouts"), ("templateRef", "templates")):
                ref = (scene or {}).get(key)
                if not ref:
                    continue
                definition = safe_file(root, f"html_engine/visual/{directory}/{ref['id']}.json")
                result[directory][ref["id"]] = content_hash(definition)
                if key == "themeRef":
                    family = read(definition, {}).get("font", {}).get("family")
                    page["font_family"] = family
                    if family == "Microsoft YaHei":
                        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
                        result["fonts"][family] = {name: content_hash(fonts / name) for name in ("msyh.ttc", "msyhbd.ttc", "msyhl.ttc")}
            for node in (scene or {}).get("nodes", []):
                asset_id = node.get("assetRef", {}).get("id")
                if not asset_id:
                    continue
                asset = project_assets.get(asset_id) or builtin.get(asset_id)
                if asset is None:
                    result["assets"][asset_id] = None
                    continue
                reference = asset["file"]
                relative = reference if isinstance(reference, str) else reference["path"]
                file = safe_file(run if asset_id in project_assets else root, relative.replace("\\", "/").removeprefix("project/"))
                result["assets"][asset_id] = {"record": asset, "actual_sha256": content_hash(file)}
        if any((fresh_hash(path) if path.is_file() else None) != expected for path, expected in observed.items()):
            raise ValueError("REBUILD_INPUT_CHANGED")
        return result
