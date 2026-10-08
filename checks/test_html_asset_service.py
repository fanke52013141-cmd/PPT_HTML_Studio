"""C03: independent asset production with hash reuse and quality gates.

Provider calls are stubbed (acceptance: daily model checks use controlled
fixtures); transparency, edge, anchor, and manifest checks run on real
PNG bytes produced with Pillow.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from html_asset_service import (
    HtmlAssetDependencies,
    HtmlAssetError,
    inspect_asset_bytes,
    load_asset_entry,
    produce_asset,
)


def png_bytes(width=64, height=64, *, transparent_margin=8, color=(200, 80, 120, 255)) -> bytes:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for x in range(transparent_margin, width - transparent_margin):
        for y in range(transparent_margin, height - transparent_margin):
            image.putpixel((x, y), color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def opaque_rows_bytes() -> bytes:
    """Transparency present, but top and bottom rows fully opaque."""
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for x in range(32):
        image.putpixel((x, 0), (240, 240, 240, 255))
        image.putpixel((x, 31), (240, 240, 240, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def opaque_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), (240, 240, 240))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def deps(tmp_path: Path, payloads: list[bytes] | None = None) -> tuple:
    calls: list[dict] = []
    queue = list(payloads or [])

    def provider(prompt, size=None):
        calls.append({"prompt": prompt, "size": size})
        if not queue:
            raise AssertionError("provider called more often than stubbed")
        return queue.pop(0)

    return (
        HtmlAssetDependencies(
            provider_callable=provider,
            assets_root=tmp_path / "assets",
        ),
        calls,
    )


def request() -> dict:
    return {
        "id": "cold-cup",
        "role": "主视觉：冷杯表面凝结",
        "prompt": "柔和科普插画：冷杯外壁水滴",
        "need": "表达杯壁水滴，同系列视角",
        "transparent_background": True,
        "anchors": [{"id": "focus", "x": 32, "y": 40}],
    }


def test_inspect_reports_alpha_bbox_and_transparency() -> None:
    facts = inspect_asset_bytes(png_bytes())
    assert facts["width"] == 64 and facts["height"] == 64
    assert facts["alpha_bbox"] == [8, 8, 56, 56]
    assert facts["has_transparency"] is True
    assert facts["opaque_edges"]["top"] is False


def test_produce_registers_manifest_entry_with_normalized_anchor(tmp_path) -> None:
    service, calls = deps(tmp_path, [png_bytes()])
    entry = produce_asset(request(), service)
    assert entry["cache"] == "miss"
    assert entry["sha256"]
    assert entry["anchors"][0]["nx"] == 0.5
    assert entry["alpha_bbox"] == [8, 8, 56, 56]
    assert len(calls) == 1
    # Same request again: hash hit, no provider call, verified bytes.
    again = produce_asset(request(), service)
    assert again["cache"] == "hit"
    assert again["sha256"] == entry["sha256"]
    assert len(calls) == 1


def test_transparent_declaration_gates(tmp_path) -> None:
    service, calls = deps(tmp_path, [opaque_bytes()])
    with pytest.raises(HtmlAssetError) as opaque:
        produce_asset(request(), service)
    assert opaque.value.code == "ASSET_BACKGROUND_OPAQUE"

    service2, _ = deps(tmp_path, [opaque_rows_bytes()])
    with pytest.raises(HtmlAssetError) as bleed:
        produce_asset(request(), service2)
    assert bleed.value.code == "ASSET_EDGE_BLEED"

    fully_transparent = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    buffer = io.BytesIO()
    fully_transparent.save(buffer, format="PNG")
    service3, calls3 = deps(tmp_path, [buffer.getvalue()])
    with pytest.raises(HtmlAssetError) as empty:
        produce_asset(request(), service3)
    assert empty.value.code == "ASSET_EMPTY_RENDER"
    # The provider ran; validation rejected the useless result afterwards.
    assert len(calls3) == 1


def test_anchor_validation(tmp_path) -> None:
    service, _ = deps(tmp_path, [png_bytes(), png_bytes()])
    bad = request()
    bad["anchors"] = [{"id": "focus", "x": 999, "y": 10}]
    with pytest.raises(HtmlAssetError) as out_of_bounds:
        produce_asset(bad, service)
    assert out_of_bounds.value.code == "ASSET_ANCHOR_OUT_OF_BOUNDS"
    bad2 = request()
    bad2["anchors"] = [{"id": "focus", "x": 1.5, "y": 10}]
    with pytest.raises(HtmlAssetError) as not_integer:
        produce_asset(bad2, service)
    assert not_integer.value.code == "ASSET_ANCHOR_INVALID"


def test_load_entry_verifies_stored_bytes(tmp_path) -> None:
    service, _ = deps(tmp_path, [png_bytes()])
    entry = produce_asset(request(), service)
    loaded = load_asset_entry("cold-cup", service)
    assert loaded["sha256"] == entry["sha256"]
    # Corrupt the stored file: reads must fail loudly.
    stored = service.assets_root / entry["file"]
    stored.write_bytes(b"broken")
    with pytest.raises(HtmlAssetError) as mismatch:
        load_asset_entry("cold-cup", service)
    assert mismatch.value.code == "ASSET_HASH_MISMATCH"
    with pytest.raises(HtmlAssetError) as missing:
        load_asset_entry("never-made", service)
    assert missing.value.code == "ASSET_NOT_FOUND"


def test_need_description_is_required(tmp_path) -> None:
    service, _ = deps(tmp_path, [png_bytes()])
    incomplete = request()
    incomplete["need"] = ""
    with pytest.raises(HtmlAssetError) as need:
        produce_asset(incomplete, service)
    assert need.value.code == "ASSET_NEED_MISSING"
