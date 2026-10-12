"""S05: pin ordered formal export inputs before any browser/encoder work."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile

from html_build_snapshot import (
    SnapshotError,
    create_render_snapshot,
    digest,
    fresh_hash,
    json_bytes,
    safe_file,
    verify_snapshot,
    _read_revision,
    _no_secrets,
)
from pipeline_lifecycle import project_artifact_lock

TOOLS = ("export-slide-video.cjs", "export-snapshots.cjs", "browser-runtime.cjs")


def freeze_course(run_dir, repo_root, *, target, fingerprint_factory):
    """A course references verified immutable pages; order never comes from live files later.

    Media is copied, never hard-linked. No providers, DB state or credentials are read.
    Digital-human media has an explicit 1 GiB local export budget.
    """
    run, root = Path(run_dir).resolve(), Path(repo_root).resolve()
    if target not in {"pptx", "video"}:
        raise SnapshotError("EXPORT_TARGET_INVALID")
    base = run / "planning/html_visual/export-builds"
    base.mkdir(parents=True, exist_ok=True)
    with project_artifact_lock(run):
        fingerprint = fingerprint_factory()
        _no_secrets(fingerprint)
        revision = _read_revision(run)["revision"]
        contract = json.loads(
            (run / "planning/visual_contract.json").read_text(encoding="utf-8")
        )
        ids = [s["slide_id"] for s in contract["slides"]]
        if not ids or len(ids) != len(set(ids)):
            raise SnapshotError("EXPORT_ORDER_INVALID")
        pages = []
        for identity in ids:
            page = create_render_snapshot(
                run, identity, repo_root=root, expected_revision=revision, target=target
            )
            pages.append({"slide_id": identity, "snapshot_id": page["snapshot_id"]})
        stage = Path(tempfile.mkdtemp(prefix=".export-", dir=base))
        try:
            files = []
            sources = {}

            def copy(source, relative):
                source = Path(source)
                before = fresh_hash(source)
                destination = safe_file(stage, relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                if fresh_hash(destination) != before or fresh_hash(source) != before:
                    raise SnapshotError("EXPORT_SOURCE_CHANGED")
                sources[source] = before
                files.append(
                    {
                        "path": relative,
                        "sha256": before,
                        "bytes": destination.stat().st_size,
                    }
                )

            for name in TOOLS:
                copy(root / "html_engine/tools" / name, "tools/" + name)
            if target == "video":
                cfg_file = run / "planning/digital_human.json"
                from distribution_profile import features

                allow_presenter = features()["digital_human"]
                cfg_bytes = (
                    cfg_file.read_bytes()
                    if allow_presenter and cfg_file.is_file()
                    else None
                )
                cfg = (
                    json.loads(cfg_bytes.decode("utf-8-sig"))
                    if cfg_bytes is not None
                    else {"enabled": False}
                )
                if not isinstance(cfg, dict):
                    raise SnapshotError("EXPORT_DIGITAL_HUMAN_CONFIG_INVALID")
                _no_secrets(cfg)
                cfg_out = stage / "frozen-run/planning/digital_human.json"
                cfg_out.parent.mkdir(parents=True, exist_ok=True)
                cfg_out.write_bytes(json_bytes(cfg))
                files.append(
                    {
                        "path": "frozen-run/planning/digital_human.json",
                        "sha256": fresh_hash(cfg_out),
                        "bytes": cfg_out.stat().st_size,
                    }
                )
                if cfg_bytes is not None:
                    sources[cfg_file] = digest(cfg_bytes)
                if cfg.get("enabled"):
                    name = (
                        "digi_upload.mp4"
                        if str(cfg.get("mode") or "upload").strip().lower() == "upload"
                        else "digi_full.mp4"
                    )
                    media = run / "planning/digital_human" / name
                    if not media.is_file() or media.stat().st_size > 1024**3:
                        raise SnapshotError("EXPORT_DIGITAL_HUMAN_MISSING_OR_TOO_LARGE")
                    copy(media, "frozen-run/planning/digital_human/" + name)
            manifest = {
                "format": "hps.html.course_export",
                "version": "0.1.0",
                "target": target,
                "source_revision": revision,
                "fingerprint": fingerprint,
                "pages": pages,
                "files": files,
            }
            manifest["snapshot_id"] = digest(json_bytes(manifest))
            (stage / "manifest.json").write_bytes(json_bytes(manifest))
            if (
                fingerprint_factory() != fingerprint
                or _read_revision(run)["revision"] != revision
                or any(fresh_hash(p) != h for p, h in sources.items())
            ):
                raise SnapshotError("EXPORT_SOURCE_CHANGED")
            final = base / manifest["snapshot_id"]
            if final.exists():
                verify_course(final)
            else:
                os.rename(stage, final)
            verify_course(final)
            return final
        finally:
            if stage.exists():
                assert stage.resolve().parent == base.resolve()
                shutil.rmtree(stage)


def verify_course(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    original = dict(manifest)
    identity = original.pop("snapshot_id")
    if (
        manifest.get("format") != "hps.html.course_export"
        or manifest.get("version") != "0.1.0"
        or digest(json_bytes(original)) != identity
    ):
        raise SnapshotError("EXPORT_MANIFEST_INVALID")
    for entry in manifest["files"]:
        path = safe_file(folder, entry["path"])
        if path.stat().st_size != entry["bytes"] or fresh_hash(path) != entry["sha256"]:
            raise SnapshotError("EXPORT_FILE_CHANGED")
    builds = folder.parent.parent / "builds"
    for page in manifest["pages"]:
        snap = verify_snapshot(safe_file(builds, page["snapshot_id"]))
        if (
            snap["snapshot_id"] != page["snapshot_id"]
            or snap["slide_id"] != page["slide_id"]
            or snap["target"] != manifest["target"]
        ):
            raise SnapshotError("EXPORT_PAGE_INVALID")
    return manifest


def page_folder(course, page):
    return safe_file(Path(course).parent.parent / "builds", page["snapshot_id"])


def export_env(root, snapshot, extra=None):
    env = dict(os.environ)
    env.pop("HPS_HTML_RESOURCES", None)
    env.pop("HPS_HTML_SNAPSHOT", None)
    env.update(extra or {})
    env["HPS_HTML_SNAPSHOT"] = str(Path(snapshot).resolve())
    env["NODE_PATH"] = os.pathsep.join(
        [str(Path(root) / "html_engine/node_modules"), str(Path(root) / "node_modules")]
    )
    return env


def runtime_identity(root, course, execute, *, node_bin="node", timeout=60):
    """Pin actual browser and Playwright identity, not an assumed product name."""
    code = "const p=require('playwright');const r=require(process.argv[1]);console.log(JSON.stringify({browser:r.resolveBrowser(p.chromium),playwright:require('playwright/package.json').version,node:process.version,node_path:process.execPath}));"
    result = execute(
        [node_bin, "-e", code, str(Path(course) / "tools/browser-runtime.cjs")],
        cwd=str(root),
        env=export_env(root, course),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout_sec=timeout,
    )
    if result.returncode:
        raise SnapshotError(
            "EXPORT_BROWSER_PREFLIGHT_FAILED: " + (result.stderr or "")[-300:]
        )
    identity = json.loads(result.stdout)
    identity["browser_sha256"] = fresh_hash(identity["browser"])
    identity["node_sha256"] = fresh_hash(identity["node_path"])
    return identity


def verify_runtime_identity(identity):
    for name, hash_key, path_key in (
        ("browser", "browser_sha256", "browser"),
        ("node", "node_sha256", "node_path"),
        ("ffmpeg", "ffmpeg", "ffmpeg_path"),
        ("ffprobe", "ffprobe", "ffprobe_path"),
    ):
        if name in {"browser", "node"} or name in identity:
            if fresh_hash(identity[path_key]) != identity[hash_key]:
                raise SnapshotError("EXPORT_RUNTIME_CHANGED: " + name)
