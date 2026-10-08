"""Independent asset production for the HTML backend (C03).

Small-scope wrapper around the existing image provider: per-asset
generation requests with hash-hit reuse, deterministic quality gates,
and a manifest that mirrors the engine's asset registration shape
(id, version, sha256, pixel size, alpha bbox, normalized anchors, role,
declared background, source). Unlike the image backend pipeline there
is no whole-slide white-background normalization and no AI Mask
step — assets are standalone subjects consumed by html-visual scenes.

The provider callable is injected (real implementation wraps
``ai_provider_service``); tests use a stub, per the acceptance rule that
daily model checks run against controlled fixtures.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

from ai_provider_service import open_validated_image

ASSET_VERSION = "0.1.0"
MAX_ASSET_PIXELS = 4_000_000
_MANIFEST_NAME = "manifest.json"


class HtmlAssetError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class HtmlAssetDependencies:
    """provider_callable(prompt: str, *, size: str|None) -> PNG bytes."""

    provider_callable: Callable[..., bytes]
    assets_root: Path


def _asset_dir(assets_root: Path, asset_id: str) -> Path:
    value = str(asset_id or "").strip()
    if not value or any(ch in value for ch in "/\\.:"):
        raise HtmlAssetError("ASSET_ID_INVALID", f"资产标识不合法：{asset_id!r}")
    return Path(assets_root) / value


def _png_bytes(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def inspect_asset_bytes(payload: bytes) -> Dict[str, Any]:
    """Decode and measure one PNG: size, alpha bbox, transparency facts.

    Mirrors the engine build's alpha-bbox computation so the manifest the
    application writes matches what ``visual/build.cjs`` verifies later.
    """
    image = open_validated_image(payload)
    width, height = image.size
    if width * height > MAX_ASSET_PIXELS:
        raise HtmlAssetError(
            "ASSET_PIXEL_BUDGET",
            f"资产像素超预算：{width}x{height} > {MAX_ASSET_PIXELS}",
        )
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    min_alpha, max_alpha = alpha.getextrema()
    bbox = alpha.getbbox()
    opaque_edges = _edges_fully_opaque(rgba)
    return {
        "width": width,
        "height": height,
        "alpha_bbox": list(bbox) if bbox else None,
        "has_transparency": min_alpha < 255,
        "fully_transparent": max_alpha == 0,
        "opaque_edges": opaque_edges,
    }


def _edges_fully_opaque(rgba) -> Dict[str, bool]:
    width, height = rgba.size
    pixels = rgba.load()
    if width == 0 or height == 0:
        return {}
    def edge_opaque(points) -> bool:
        return all(pixels[x, y][3] == 255 for x, y in points)
    return {
        "top": edge_opaque(((x, 0) for x in range(width))),
        "bottom": edge_opaque(((x, height - 1) for x in range(width))),
        "left": edge_opaque(((0, y) for y in range(height))),
        "right": edge_opaque(((width - 1, y) for y in range(height))),
    }


def _read_manifest(assets_root: Path) -> Dict[str, Any]:
    path = Path(assets_root) / _MANIFEST_NAME
    if not path.is_file():
        return {"assets": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HtmlAssetError("ASSET_MANIFEST_CORRUPT", "资产清单无法解析") from exc


def _write_manifest(assets_root: Path, manifest: Dict[str, Any]) -> None:
    path = Path(assets_root) / _MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _request_key(request: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(request, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def produce_asset(
    request: Dict[str, Any],
    dependencies: HtmlAssetDependencies,
) -> Dict[str, Any]:
    """Produce or reuse one independent asset.

    ``request``: {id, role, prompt, need, transparent_background?, size?,
    anchors?: [{id, x, y}]} — anchors are normalized source-pixel
    coordinates on the produced image. A hash hit on (id + request
    content) reuses the stored PNG without calling the provider.
    """
    asset_id = str(request.get("id") or "").strip()
    role = str(request.get("role") or "").strip()
    prompt = str(request.get("prompt") or "").strip()
    need = str(request.get("need") or "").strip()
    if not asset_id or not role or not prompt:
        raise HtmlAssetError(
            "ASSET_REQUEST_INVALID", "资产请求缺少 id/role/prompt"
        )
    if not need:
        raise HtmlAssetError(
            "ASSET_NEED_MISSING", f"资产 {asset_id} 缺少需求描述（need）"
        )
    transparent = request.get("transparent_background", True) is not False
    size = request.get("size")
    anchors_input = request.get("anchors") or []

    asset_dir = _asset_dir(dependencies.assets_root, asset_id)
    manifest = _read_manifest(dependencies.assets_root)
    normalized_request = {
        "id": asset_id,
        "role": role,
        "prompt": prompt,
        "size": size,
        "transparent_background": transparent,
        "anchors": anchors_input,
        "need": need,
        "reference_sha256": request.get("reference_sha256", []),
        "model_config_hash": request.get("model_config_hash"),
    }
    key = _request_key(normalized_request)
    for entry in manifest.get("assets", []):
        if entry.get("id") == asset_id and entry.get("request_key") == key:
            stored = Path(dependencies.assets_root) / entry["file"]
            if stored.is_file() and entry.get("sha256") == hashlib.sha256(
                stored.read_bytes()
            ).hexdigest():
                return {**entry, "cache": "hit"}

    payload = dependencies.provider_callable(prompt, size=size)
    facts = inspect_asset_bytes(payload)
    if facts["fully_transparent"]:
        raise HtmlAssetError(
            "ASSET_EMPTY_RENDER", f"资产 {asset_id} 生成结果完全透明"
        )
    if transparent and not facts["has_transparency"]:
        raise HtmlAssetError(
            "ASSET_BACKGROUND_OPAQUE",
            f"资产 {asset_id} 声明透明背景，但生成结果无透明像素",
        )
    if transparent and facts["opaque_edges"].get("top") and facts["opaque_edges"].get("bottom"):
        raise HtmlAssetError(
            "ASSET_EDGE_BLEED",
            f"资产 {asset_id} 上下边缘完全不透明，疑似带底生成",
        )
    normalized_anchors: List[Dict[str, Any]] = []
    for anchor in anchors_input:
        anchor_id = str((anchor or {}).get("id") or "").strip()
        x, y = (anchor or {}).get("x"), (anchor or {}).get("y")
        if not anchor_id or not isinstance(x, int) or not isinstance(y, int):
            raise HtmlAssetError(
                "ASSET_ANCHOR_INVALID", f"资产 {asset_id} 锚点必须是 id + 源像素整数坐标"
            )
        if not (0 <= x < facts["width"] and 0 <= y < facts["height"]):
            raise HtmlAssetError(
                "ASSET_ANCHOR_OUT_OF_BOUNDS", f"资产 {asset_id} 锚点 ({x},{y}) 越界"
            )
        normalized_anchors.append(
            {
                "id": anchor_id,
                "x": x,
                "y": y,
                "nx": round(x / facts["width"], 6),
                "ny": round(y / facts["height"], 6),
            }
        )

    digest = hashlib.sha256(payload).hexdigest()
    asset_dir.mkdir(parents=True, exist_ok=True)
    stored = asset_dir / f"{asset_id}-{digest[:12]}.png"
    stored.write_bytes(payload)
    entry = {
        "id": asset_id,
        "version": ASSET_VERSION,
        "file": str(stored.relative_to(Path(dependencies.assets_root))),
        "sha256": digest,
        "request_key": key,
        "model_config_hash": request.get("model_config_hash"),
        "role": role,
        "need": need,
        "transparent_background": transparent,
        "size": {"width": facts["width"], "height": facts["height"]},
        "alpha_bbox": facts["alpha_bbox"],
        "has_transparency": facts["has_transparency"],
        "opaque_edges": facts["opaque_edges"],
        "anchors": normalized_anchors,
        "source": "html_asset_service provider",
        "cache": "miss",
    }
    manifest["assets"] = [
        e for e in manifest.get("assets", []) if e.get("id") != asset_id
    ] + [entry]
    _write_manifest(dependencies.assets_root, manifest)
    return entry


def load_asset_entry(
    asset_id: str, dependencies: HtmlAssetDependencies
) -> Dict[str, Any]:
    """Return the registered manifest entry, verifying stored bytes."""
    manifest = _read_manifest(dependencies.assets_root)
    for entry in manifest.get("assets", []):
        if entry.get("id") == asset_id:
            stored = _asset_dir(dependencies.assets_root, asset_id) / Path(
                entry["file"]
            ).name
            if not stored.is_file() or hashlib.sha256(
                stored.read_bytes()
            ).hexdigest() != entry.get("sha256"):
                raise HtmlAssetError(
                    "ASSET_HASH_MISMATCH", f"资产 {asset_id} 存储字节与清单不符"
                )
            return entry
    raise HtmlAssetError("ASSET_NOT_FOUND", f"资产 {asset_id} 未登记")
