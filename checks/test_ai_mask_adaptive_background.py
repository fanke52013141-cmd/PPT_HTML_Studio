"""Adaptive background detection: distance-from-estimated-background predicate."""
from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageDraw

from ai_mask_component_detection import _estimate_background, detect_elements

SIZE = (480, 360)


def _settings(**overrides):
    base = dict(
        white_threshold=245,
        color_tolerance=12,
        background_mode="auto",
        closing_radius=6,
        add_border=2,
        connectivity=8,
        min_element_area=120,
        component_padding_px=12,
        fine_grained_detection=False,
        pale_support_threshold=254,
        enclosed_support_max_area_px=20000,
    )
    base.update(overrides)
    return base


def _save(tmp_path, image):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "image.png"
    image.save(path)
    return path


def _detect(tmp_path, image, settings):
    image_path = _save(tmp_path, image)
    return detect_elements(image_path, tmp_path / "slide", settings)


def _card_image(background):
    image = Image.new("RGB", SIZE, background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 80, 140, 180), fill=(40, 70, 120))
    draw.rectangle((200, 80, 300, 180), fill=(150, 60, 40))
    draw.text((40, 260), "自适应背景测试", fill=(30, 40, 60))
    return image


def _mask(rle):
    mask = np.zeros((SIZE[1], SIZE[0]), bool)
    for y, x1, x2 in rle["runs"]:
        mask[y, x1:x2] = True
    return mask


def test_border_band_estimate_returns_median_and_mad():
    image = np.full((100, 120, 3), (242, 236, 227), dtype=np.uint8)
    estimate = _estimate_background(image)
    assert estimate["bg_color"] == [242, 236, 227]
    assert estimate["band_mad"] == 0.0
    assert estimate["band_sample_count"] > 0


def test_auto_white_background_matches_legacy_formula_exactly(tmp_path):
    image = _card_image((255, 255, 255))
    legacy = _detect(tmp_path / "legacy", image, _settings(background_mode="white"))
    auto = _detect(tmp_path / "auto", image, _settings(background_mode="auto"))
    assert legacy.get("adaptive_background") is None
    assert auto["adaptive_background"]["path"] == "legacy_white"
    for key in ("elements", "residual_elements", "source_foreground_pixel_count",
                "foreground_pixel_count", "version"):
        assert json.dumps(auto[key], sort_keys=True) == json.dumps(legacy[key], sort_keys=True), key


def test_white_mode_collapses_nonwhite_background_into_one_component(tmp_path):
    beige = (242, 236, 227)
    payload = _detect(tmp_path, _card_image(beige), _settings(background_mode="white"))
    assert len(payload["elements"]) == 1, "the whole canvas must fuse under the legacy predicate"
    mask = np.zeros((SIZE[1], SIZE[0]), bool)
    for element in payload["elements"] + payload["residual_elements"]:
        mask |= _mask(element["mask_rle"])
    assert mask.mean() > 0.5, "the legacy path claims the background as foreground"


def test_auto_mode_separates_cards_on_beige_background(tmp_path):
    beige = (242, 236, 227)
    payload = _detect(tmp_path, _card_image(beige), _settings(background_mode="auto"))
    assert payload["adaptive_background"]["path"] == "adaptive"
    assert payload["adaptive_background"]["bg_color"] == [242, 236, 227]
    assert payload["adaptive_background"]["tolerance"] >= 12
    elements = payload["elements"] + payload["residual_elements"]
    assert len(payload["elements"]) >= 3, "two cards plus the caption line must separate"
    union = np.zeros((SIZE[1], SIZE[0]), bool)
    for element in elements:
        union |= _mask(element["mask_rle"])
    assert union.mean() < 0.3, "the background must not be claimed as foreground"
    left = _owners(payload, 90, 130)
    right = _owners(payload, 250, 130)
    assert len(left) == 1 and len(right) == 1 and left[0] is not right[0]


def _owners(payload, x, y):
    return [
        element for element in payload["elements"] + payload["residual_elements"]
        if _mask(element["mask_rle"])[y, x]
    ]


def test_auto_mode_with_fine_grained_keeps_background_out_of_support(tmp_path):
    beige = (242, 236, 227)
    payload = _detect(tmp_path, _card_image(beige), _settings(
        background_mode="auto", fine_grained_detection=True))
    elements = payload["elements"] + payload["residual_elements"]
    assert len(payload["elements"]) >= 3
    largest = max(int(element["area"]) for element in elements)
    assert largest < 0.5 * SIZE[0] * SIZE[1], "pale support must not swallow the canvas"
    union = np.zeros((SIZE[1], SIZE[0]), bool)
    for element in elements:
        union |= _mask(element["mask_rle"])
    assert union.mean() < 0.3


def test_background_mode_switch_invalidates_detection_cache(tmp_path):
    image = _card_image((242, 236, 227))
    first = _detect(tmp_path / "one", image, _settings(background_mode="auto"))
    rerun = _detect(tmp_path / "one", image, _settings(background_mode="auto"))
    assert rerun["cache_hit"] is True
    other = _detect(tmp_path / "one", image, _settings(background_mode="white"))
    assert other["cache_hit"] is False
    assert other["detection_settings_fingerprint"] != first["detection_settings_fingerprint"]
