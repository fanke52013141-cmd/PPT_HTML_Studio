"""Immutable, hash-verified local HTML input snapshots; no database/providers."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import tempfile

from pipeline_lifecycle import project_artifact_lock
from html_visual_store import _read_revision, validate_slide_id

VERSION = "0.1.0"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024


class SnapshotError(ValueError):
    pass


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def fresh_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(256 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_file(root, relative):
    if not isinstance(relative, str) or "\\" in relative:
        raise SnapshotError("INVALID_SNAPSHOT_PATH")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or not rel.parts or any(p in (".", "..") or ":" in p for p in rel.parts):
        raise SnapshotError("INVALID_SNAPSHOT_PATH")
    root = Path(root).resolve()
    candidate = root.joinpath(*rel.parts)
    if not candidate.resolve().is_relative_to(root):
        raise SnapshotError("SNAPSHOT_PATH_ESCAPE")
    if candidate.is_symlink():
        raise SnapshotError("SNAPSHOT_SYMLINK")
    return candidate


def _no_secrets(value):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized.endswith("apikey") or normalized in {"authorization", "password", "cookie", "secret", "token", "accesstoken", "bearertoken", "credentialref"}:
                raise SnapshotError("SECRET_FIELD_NOT_ALLOWED")
            _no_secrets(child)
    elif isinstance(value, list):
        for child in value:
            _no_secrets(child)
    elif isinstance(value, str) and re.search(r"sk-[A-Za-z0-9]{20,}", value):
        raise SnapshotError("SECRET_VALUE_NOT_ALLOWED")


class _Capture:
    def __init__(self):
        self.files = {}
        self.sources = {}

    def add(self, relative, data):
        safe_file(Path(tempfile.gettempdir()), relative)
        if len(data) > MAX_FILE_BYTES or sum(len(v) for k, v in self.files.items() if k != relative) + len(data) > MAX_TOTAL_BYTES:
            raise SnapshotError("SNAPSHOT_FILE_BUDGET")
        self.files[relative] = data

    def read(self, source, relative):
        source = Path(source).resolve()
        if not source.is_file() or source.stat().st_size > MAX_FILE_BYTES:
            raise SnapshotError("SNAPSHOT_SOURCE_MISSING_OR_TOO_LARGE")
        data = source.read_bytes()
        if source in self.sources and self.sources[source] != digest(data):
            raise SnapshotError("SNAPSHOT_SOURCE_CHANGED")
        self.sources[source] = digest(data)
        self.add(relative, data)
        return data

    def unchanged(self):
        return all(p.is_file() and fresh_hash(p) == sha for p, sha in self.sources.items())


def _commit(run, capture, metadata, revision):
    if not capture.unchanged() or _read_revision(run)["revision"] != revision:
        raise SnapshotError("SNAPSHOT_SOURCE_CHANGED")
    manifest = {"format": "hps.html.input_snapshot", "version": VERSION,
                **metadata, "source_revision": revision,
                "files": [{"path": p, "sha256": digest(data), "bytes": len(data)}
                          for p, data in sorted(capture.files.items())]}
    snapshot_id = digest(json_bytes(manifest))
    manifest["snapshot_id"] = snapshot_id
    base = safe_file(run, "planning/html_visual/builds")
    base.mkdir(parents=True, exist_ok=True)
    final = base / snapshot_id
    if final.exists():
        verify_snapshot(final)
        return {"snapshot_id": snapshot_id, "path": str(final), "reused": True}
    stage = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=base))
    try:
        for relative, data in capture.files.items():
            target = safe_file(stage, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (stage / "manifest.json").write_bytes(json_bytes(manifest))
        verify_snapshot(stage)
        if not capture.unchanged() or _read_revision(run)["revision"] != revision:
            raise SnapshotError("SNAPSHOT_SOURCE_CHANGED")
        os.rename(stage, final)
    finally:
        if stage.exists():
            # Only remove the staging directory allocated above, inside this run.
            assert stage.resolve().parent == base.resolve()
            shutil.rmtree(stage)
    return {"snapshot_id": snapshot_id, "path": str(final), "reused": False}


def verify_snapshot(folder):
    folder = Path(folder).resolve()
    try:
        path = folder / "manifest.json"
        if path.stat().st_size > 1024 * 1024:
            raise SnapshotError("SNAPSHOT_MANIFEST_BUDGET")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        original = dict(manifest)
        identity = original.pop("snapshot_id")
        if manifest.get("format") != "hps.html.input_snapshot" or manifest.get("version") != VERSION:
            raise SnapshotError("SNAPSHOT_VERSION_UNSUPPORTED")
        if digest(json_bytes(original)) != identity:
            raise SnapshotError("SNAPSHOT_MANIFEST_HASH_MISMATCH")
        files = manifest["files"]
        if not files or len(files) > 512 or any(type(x["bytes"]) is not int or not 0 <= x["bytes"] <= MAX_FILE_BYTES for x in files) or len({x["path"] for x in files}) != len(files) or sum(x["bytes"] for x in files) > MAX_TOTAL_BYTES:
            raise SnapshotError("SNAPSHOT_FILE_LIST_INVALID")
        for entry in files:
            p = safe_file(folder, entry["path"])
            if not p.is_file() or p.stat().st_size != entry["bytes"] or fresh_hash(p) != entry["sha256"]:
                raise SnapshotError("SNAPSHOT_FILE_HASH_MISMATCH")
        if manifest["kind"] not in {"generation", "render"}:
            raise SnapshotError("SNAPSHOT_KIND_INVALID")
        return manifest
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SnapshotError("SNAPSHOT_INVALID") from exc


def create_generation_snapshot(run_dir, contract, *, repo_root=None, expected_revision=None,
                               options=None, model_identity=None):
    """No future image/audio is fabricated; model identity is deliberately minimal."""
    from html_production_models import HtmlProduceRequest
    root = Path(repo_root or Path(__file__).parent).resolve()
    run = Path(run_dir).resolve()
    contract = copy.deepcopy(contract)
    validate_slide_id(contract.get("slide_id"))
    options = HtmlProduceRequest.model_validate(options or {}).model_dump()
    identities = copy.deepcopy(model_identity or {})
    if set(identities) - {"text", "image"} or any(not isinstance(v, dict) or set(v) - {"provider", "model", "config_digest"} for v in identities.values()):
        raise SnapshotError("MODEL_IDENTITY_FIELDS_INVALID")
    _no_secrets([contract, options, identities])
    with project_artifact_lock(run):
        revision = _read_revision(run)["revision"]
        if expected_revision is not None and expected_revision != revision:
            raise SnapshotError("SNAPSHOT_REVISION_CONFLICT")
        capture = _Capture()
        capture.add("input/contract.json", json_bytes(contract))
        capture.add("input/options.json", json_bytes(options))
        capture.add("input/model-identity.json", json_bytes(identities))
        # Pin the actual planner/runtime definitions; not just their IDs.
        for name in ["html_storyboard_planning.py", "html_semantic_plan.py", "html_semantic_design.py", "html_semantic_runtime.py", "html_motion_binding.py", "html_audio_binder.py", "html_design_reconstruction.py", "html_design_agent.py", "html_planning_context.py", "html_visual_review_service.py", "html_reference_package.py",
                     "html_production_service.py", "html_design_brief.py", "html_image_provider.py",
                     "html_production_models.py", "html_candidate_agent.py", "html_runtime_skills.py", "html_scene_repair.py", "html_engine/visual/presentation-variants.json",
                     "json_llm_service.py", "ai_provider_service.py", "html_workflow_jobs.py", "html_production_stages.py", "html_production_recovery.py",
                     "html_rebuild_plan.py", "html_scene_editing.py", "html_input_manifest.py", "invalidation_service.py", "project_impact_service.py",
                     "html_task_store.py", "html_repair_progress.py", "html_engine/tools/temporal-review.cjs", "html_engine/tools/review-temporal.cjs", "html_engine/visual/qa/overlap-policy.json", "html_engine/tools/catalog-lib.cjs", "html_engine/tools/catalog-assemble.cjs"]:
            capture.read(root / name, "source/" + name)
        from html_runtime_skills import runtime_source_files
        for record in runtime_source_files(root):
            if digest(capture.read(safe_file(root, record["path"]), "source/" + record["path"])) != record["sha256"]:
                raise SnapshotError("SNAPSHOT_SKILL_SOURCE_CHANGED")
        for directory in ("themes", "layouts", "templates"):
            for p in sorted((root / "html_engine/visual" / directory).glob("*.json")):
                capture.read(p, "definitions/" + directory + "/" + p.name)
        for name in ("generated/catalog.json", "schema.json", "effects/registry.json", "catalog/catalog.json"):
            capture.read(root / "html_engine/visual" / name, "definitions/" + name)
        # Available assets and reference attachments must remain recoverable.
        catalog = json.loads(capture.files["definitions/catalog/catalog.json"])
        for page in catalog.get("referencePages", []):
            relative = page["screenshot"]["path"]
            data = capture.read(safe_file(root, relative), "references/" + relative)
            if digest(data) != page["screenshot"]["sha256"]:
                raise SnapshotError("REFERENCE_HASH_MISMATCH")
        offered = {a["assetRef"]["id"] for g in contract.get("visual_groups", []) for a in g.get("available_assets", [])}
        assets, _ = _capture_assets(root, run, capture, offered)
        versions = {a["id"]: a["version"] for a in assets}
        for g in contract.get("visual_groups", []):
            for a in g.get("available_assets", []):
                if versions.get(a["assetRef"]["id"]) != a["assetRef"]["version"]:
                    raise SnapshotError("SNAPSHOT_ASSET_VERSION_MISMATCH")
        return _commit(run, capture, {"kind": "generation", "slide_id": contract["slide_id"],
                                      "target": "planning", "provider_called": False}, revision)


def _capture_assets(root, run, capture, used):
    from html_scene_editing import resources
    resource_file = run / "planning/html_visual/resources.json"
    if resource_file.is_file():
        _no_secrets(json.loads(capture.read(resource_file, "source/project-resources.json")))
    project = resources(run)
    runtime = json.loads((root / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    builtin = {a["id"]: a for a in runtime["assets"]}
    project_assets = {a["id"]: a for a in project["assets"]}
    selected = []
    pack = {}
    for identity in sorted(used):
        record = project_assets.get(identity) or builtin.get(identity)
        if record is None:
            raise SnapshotError("SNAPSHOT_ASSET_MISSING")
        relative = record["file"]["path"]
        # Legacy Windows resource references may contain backslashes. Keep the
        # renderer's lookup key, normalize only the audited filesystem path.
        filesystem_relative = relative.replace("\\", "/")
        source = safe_file(run, filesystem_relative.removeprefix("project/")) if identity in project_assets else safe_file(root, filesystem_relative)
        data = capture.read(source, "assets/" + filesystem_relative)
        if digest(data) != record["file"]["sha256"]:
            raise SnapshotError("SNAPSHOT_ASSET_HASH_MISMATCH")
        selected.append(record)
        pack[relative] = base64.b64encode(data).decode("ascii")
    return selected, pack


def create_render_snapshot(run_dir, slide_id, *, repo_root=None, expected_revision=None, target="html_preview"):
    """Freeze one saved page. Formal video requires existing authoritative gates."""
    root = Path(repo_root or Path(__file__).parent).resolve()
    run = Path(run_dir).resolve()
    slide_id = validate_slide_id(slide_id)
    if target not in {"html_preview", "video", "pptx"}:
        raise SnapshotError("SNAPSHOT_TARGET_UNSUPPORTED")
    with project_artifact_lock(run):
        revision = _read_revision(run)["revision"]
        if expected_revision is not None and revision != expected_revision:
            raise SnapshotError("SNAPSHOT_REVISION_CONFLICT")
        capture = _Capture()
        scene = json.loads(capture.read(run / f"planning/html_visual/scene-{slide_id}.json", "input/scene.json"))
        if scene.get("id") != slide_id:
            raise SnapshotError("SNAPSHOT_SCENE_ID_MISMATCH")
        _no_secrets(scene)
        if target == "pptx":
            from html_input_manifest import html_readiness
            if not html_readiness(run, root, [slide_id])["ready"]:
                raise SnapshotError("SNAPSHOT_PPTX_GATES_REQUIRED")
            capture.add("input/author-scene.json", json_bytes(scene))
            scene = {**scene, "beats": []}
            capture.add("input/scene.json", json_bytes(scene))
        if target == "video":
            from html_input_manifest import html_readiness
            from tts_artifacts import confirmation_status, artifact_paths, CONFIRMATION_HASH_KEYS, confirmation_path
            from html_creation_workflow import _validate_slide_binding
            contract = json.loads(capture.read(run / "planning/visual_contract.json", "input/contract.json"))
            ids = [s["slide_id"] for s in contract["slides"]]
            if slide_id not in ids or not html_readiness(run, root, [slide_id])["ready"] or not confirmation_status(run, ids).get("confirmed") or _validate_slide_binding(run, slide_id):
                raise SnapshotError("SNAPSHOT_VIDEO_GATES_REQUIRED")
            for key in CONFIRMATION_HASH_KEYS:
                p = artifact_paths(run, slide_id)[key]
                data = capture.read(p, "audio/" + p.name)
                if p.suffix == ".json":
                    _no_secrets(json.loads(data))
            capture.read(confirmation_path(run), "source/audio_confirmed.json")
        for filename in (f"binding-{slide_id}.json", f"edits-{slide_id}.json", f"production-provenance-{slide_id}.json", f"approval-{slide_id}.json"):
            p = run / "planning/html_visual" / filename
            if p.is_file():
                data = capture.read(p, "source/" + filename)
                _no_secrets(json.loads(data))
        visual = root / "html_engine/visual"
        catalog = json.loads(capture.read(visual / "generated/catalog.json", "source/catalog.json"))
        for key, directory, ref in (("themes", "themes", "themeRef"), ("layouts", "layouts", "layoutRef"), ("templates", "templates", "templateRef")):
            reference = scene[ref]
            catalog[key] = [x for x in catalog[key] if x["id"] == reference["id"] and x["version"] == reference["version"]]
            if len(catalog[key]) != 1:
                raise SnapshotError("SNAPSHOT_DEFINITION_MISSING")
            source_definition = capture.read(safe_file(visual, f"{directory}/{reference['id']}.json"), "source/" + directory + "/" + reference["id"] + ".json")
            if json_bytes(json.loads(source_definition)) != json_bytes(catalog[key][0]):
                raise SnapshotError("SNAPSHOT_DEFINITION_STALE")
        used = {n["assetRef"]["id"] for n in scene["nodes"] if "assetRef" in n}
        catalog["assets"], pack = _capture_assets(root, run, capture, used)
        from html_scene_editing import _node
        if target == "video":
            from html_audio_binder import bind_scene_to_audio
            capture.add("input/author-scene.json", json_bytes(scene))
            timeline = json.loads(capture.files["audio/audio_timeline.json"])
            binding = json.loads(capture.files[f"source/binding-{slide_id}.json"])
            scene = bind_scene_to_audio(scene, timeline, binding)
            capture.add("input/scene.json", json_bytes(scene))
        _node("const fs=require('fs');const p=JSON.parse(fs.readFileSync(0,'utf8'));require('./html_engine/visual/compiler.cjs').compile(p.scene,p.catalog);console.log('{}');", {"scene": scene, "catalog": catalog})
        capture.read(visual / "schema.json", "source/schema.json")
        capture.read(visual / "effects/registry.json", "source/effects.json")
        capture.read(visual / "qa/overlap-policy.json", "source/qa-policy.json")
        capture.read(visual / "preview/player.js", "preview/player.js")
        theme = catalog["themes"][0]
        if theme["font"]["family"] != "Microsoft YaHei":
            raise SnapshotError("SNAPSHOT_FONT_UNSUPPORTED")
        font_root = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        styles = []
        for name, weight in (("msyh.ttc", 400), ("msyhbd.ttc", 700), ("msyhl.ttc", 300)):
            capture.read(font_root / name, "preview/fonts/" + name)
            styles.append(f'@font-face{{font-family:"Microsoft YaHei";src:url("fonts/{name}");font-weight:{weight};font-style:normal;}}')
        capture.add("preview/fonts.css", "\n".join(styles).encode("utf-8"))
        html = capture.read(visual / "preview/index.html", "source/preview-index.html").decode("utf-8")
        html = html.replace('<meta charset="utf-8" />', '<meta charset="utf-8" /><link rel="stylesheet" href="fonts.css" />')
        html = html.replace("共享视觉定义 · 工程验证稿", "固定输入预览 · 审美待确认")
        html = html.replace("此页的简化视觉未通过用户审阅。请查看", "当前页面冻结了场景、素材与字体。此处展示")
        html = html.replace("两个实例共用组件，引用两种布局；没有逐页 HTML。", "单页固定输入；网页内修改仅为临时预览，原作品请通过编辑器保存。")
        html = re.sub(r'<a href="../style-review/index.html">.*?</a\s*>', '<span>当前快照输入</span>', html, flags=re.S)
        # Snapshot files stay immutable; editing in the page is only an unsaved preview.
        bootstrap = '''<script>
        (async()=>{
          try {
            await Promise.all([...document.fonts].map(f=>f.load()));
            const player=document.createElement('script');player.src='player.js';
            player.onload=()=>{if(new URLSearchParams(location.search).has('export'))return;const timer=setInterval(()=>{if(window.visualPlayer?.ready){window.visualPlayer.seek(window.visualPlayer.scene.durationMs);clearInterval(timer);}},50);};
            document.body.append(player);
          } catch { document.getElementById('status').textContent='未应用：SNAPSHOT_FONT_LOAD_FAILED'; }
        })();
        </script>'''
        html = html.replace('<script src="player.js"></script>', bootstrap)
        capture.add("preview/index.html", html.encode("utf-8"))
        capture.add("preview/data.js", b"window.VisualData=" + json_bytes({"catalog": catalog, "scenes": [scene], "pack": pack}).replace(b"<", b"\\u003c") + b";")
        return _commit(run, capture, {"kind": "render", "slide_id": slide_id, "target": target,
            "clock": "confirmed_audio_inputs" if target == "video" else "author",
            "scene_digest": digest(json_bytes(scene)), "font_scope": "local_only", "approval_granted": False}, revision)
