"""Resolved HTML inputs shared by approval, freshness and export gates.

No HTTP/database wiring. Definitions and source files are hashed, not merely
their reference IDs. Missing files stay explicit and never count as approval.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=512)
def _cached_hash(path: str, modified: int, size: int) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    stat = path.stat()
    return _cached_hash(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


def resolved_scene_inputs(
    scene: dict, run_dir: str | Path, repo_root: str | Path
) -> dict:
    repo = Path(repo_root)
    run = Path(run_dir)
    visual = repo / "html_engine/visual"
    files: dict[str, str | None] = {}
    asset_ids = {n.get("assetRef", {}).get("id") for n in scene.get("nodes", [])}
    for ref_key, folder in (
        ("themeRef", "themes"),
        ("layoutRef", "layouts"),
        ("templateRef", "templates"),
    ):
        ref = scene.get(ref_key) or {}
        name = str(ref.get("id") or "")
        if not name or not all(c.isalnum() or c in "_-" for c in name):
            raise ValueError("Invalid registered reference")
        if name:
            files[f"{folder}/{name}.json"] = _hash(visual / folder / f"{name}.json")
    for filename in (
        "preview/player.js",
        "generated/catalog.json",
        "assets.json",
        "preview/data.js",
        "icons.cjs",
        "effects/registry.json",
    ):
        files[filename] = _hash(visual / filename)
    manifest_path = run / "planning/html_visual/resources.json"
    project_assets = []
    if manifest_path.is_file():
        resources = json.loads(manifest_path.read_text(encoding="utf-8"))
        for record in resources.get("assets", []):
            if record.get("id") not in asset_ids:
                continue
            project_assets.append(record)
            path = (run / record["file"]).resolve()
            if not path.is_relative_to(run.resolve()):
                raise ValueError("HTML asset escapes project")
            files[f"project/{record['file']}"] = _hash(path)
    # Built-in assets are also real inputs (the pack is generated from these).
    asset_ids = {n.get("assetRef", {}).get("id") for n in scene.get("nodes", [])}
    assets_file = visual / "assets.json"
    if assets_file.is_file():
        for record in json.loads(assets_file.read_text(encoding="utf-8")):
            if record["id"] in asset_ids:
                path = (repo / record["path"]).resolve()
                if not path.is_relative_to(repo.resolve()):
                    raise ValueError("Built-in asset escapes repository")
                files[f"builtin/{record['path']}"] = _hash(path)
    theme_name = str((scene.get("themeRef") or {}).get("id") or "")
    theme_path = visual / "themes" / f"{theme_name}.json"
    font = {}
    if theme_path.is_file():
        font = json.loads(theme_path.read_text(encoding="utf-8")).get("font", {})
    if font.get("family") == "Microsoft YaHei":
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("msyh.ttc", "msyhbd.ttc", "msyhl.ttc"):
            files[f"font/{name}"] = _hash(fonts / name)
    payload = {
        "scene": scene,
        "files": files,
        "font": font,
        "project_assets": sorted(project_assets, key=lambda a: a["id"]),
        "binding_sha256": _hash(
            run / "planning/html_visual" / f"binding-{scene['id']}.json"
        ),
    }
    payload["digest"] = hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return payload


def html_project_inputs(
    run_dir: str | Path, repo_root: str | Path | None = None
) -> dict | None:
    run = Path(run_dir)
    directory = run / "planning/html_visual"
    contract = run / "planning/visual_contract.json"
    if contract.is_file():
        from html_visual_store import scene_path

        paths = [
            scene_path(run, s["slide_id"])
            for s in json.loads(contract.read_text(encoding="utf-8")).get("slides", [])
        ]
        paths = [p for p in paths if p.is_file()]
    else:
        paths = sorted(directory.glob("scene-*.json"))
    if not paths:
        return None
    repo = Path(repo_root) if repo_root else Path(__file__).resolve().parent
    result = {}
    for path in paths:
        try:
            result[path.name] = resolved_scene_inputs(
                json.loads(path.read_text(encoding="utf-8")), run, repo
            )
        except (ValueError, KeyError, TypeError):
            result[path.name] = {"invalid_document": _hash(path)}
    result["order"] = [p.name for p in paths]
    return result


def html_readiness(
    run_dir: str | Path, repo_root: str | Path, slide_ids: list[str]
) -> dict:
    from html_visual_store import load_scene, HtmlVisualError
    from html_visual_review_service import HtmlReviewDependencies, approval_status

    issues: list[dict[str, Any]] = []
    deps = HtmlReviewDependencies(
        repo_root=Path(repo_root), json_generator=lambda **kw: {}
    )
    for slide_id in slide_ids:
        try:
            scene = load_scene(run_dir, slide_id)
            status = approval_status(
                scene, run_dir=run_dir, deps=deps, slide_id=slide_id
            )
        except (HtmlVisualError, ValueError, KeyError, TypeError) as exc:
            status = {"valid": False, "reason": f"invalid_scene: {exc}"}
        if not status["valid"]:
            issues.append(
                {"slide_id": slide_id, "message": f"{slide_id}: {status['reason']}"}
            )
    if not slide_ids:
        issues.append({"message": "分镜规划尚未生成"})
    return {
        "ready": not issues,
        "issues": issues,
        "slide_count": len(slide_ids),
        "content_mode": "html_snapshot",
        "export_mode": "html_snapshot",
    }
