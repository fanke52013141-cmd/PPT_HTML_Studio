"""Pure, bounded extraction of independent candidates from an asset sheet.

Object identity and edge quality remain pending human/model review. This layer
consumes declared slots and optional segmentation masks; it does not invent
identities, regenerate hidden content, approve, or publish project resources.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import re
from collections import deque
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

FORMAT = "hps.html.asset_sheet"
VERSION = "0.1.0"
PROCESSOR_VERSION = "asset-sheet-extraction/0.1.0"
MAX_SHEET_PIXELS = 16_000_000
MAX_SLOT_PIXELS = 4_000_000
MAX_PNG_BYTES = 64 * 1024 * 1024
_ID = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}\Z")


class HtmlAssetSheetError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str):
    raise HtmlAssetSheetError(code, message)


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value):
        _fail("SHEET_FIELDS", "素材板字段缺失或类型不符")
    if set(value) - set(required) - set(optional):
        _fail("SHEET_FIELDS", "素材板含未知字段")


def _identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        _fail("SHEET_ID", "素材板、槽位、资产或锚点 ID 不合法")


def _integer(value, lower, upper):
    return type(value) is int and lower <= value <= upper


def _decode(payload: bytes, *, mask=False):
    if not isinstance(payload, bytes) or len(payload) > MAX_PNG_BYTES:
        _fail("SHEET_BYTE_BUDGET", "PNG 字节类型或预算不符")
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        _fail("SHEET_PNG", "仅接受 PNG")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            w, h = image.size
            if w < 1 or h < 1 or w * h > MAX_SHEET_PIXELS:
                _fail("SHEET_PIXEL_BUDGET", "素材板或遮罩像素超预算")
            if image.format != "PNG" or getattr(image, "n_frames", 1) != 1:
                _fail("SHEET_PNG", "仅接受单帧 PNG")
            if mask and image.mode != "L":
                _fail("SHEET_MASK_FORMAT", "分割遮罩必须为 L 模式灰度 PNG")
            image.load()
            return image.copy() if mask else image.convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        if isinstance(exc, HtmlAssetSheetError):
            raise
        raise HtmlAssetSheetError("SHEET_PNG", "PNG 无法解码") from exc


def _validate(spec: dict, size: tuple[int, int]):
    _fields(spec, ("format", "version", "id", "source_sha256", "slots"))
    if spec["format"] != FORMAT or spec["version"] != VERSION:
        _fail("SHEET_VERSION", "素材板格式或版本不支持")
    _identifier(spec["id"])
    digest = spec["source_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        _fail("SHEET_HASH", "源板摘要格式错误")
    slots = spec["slots"]
    if not isinstance(slots, list) or not 1 <= len(slots) <= 16:
        _fail("SHEET_SLOTS", "素材板必须含 1–16 个槽位")
    ids, asset_ids, rectangles = set(), set(), []
    for slot in slots:
        _fields(slot, ("id", "asset_id", "role", "need", "rect", "method"),
                ("background", "anchors", "alpha_cleanup"))
        for name, used in (("id", ids), ("asset_id", asset_ids)):
            _identifier(slot[name])
            if slot[name] in used:
                _fail("SHEET_DUPLICATE_ID", "槽位/资产 ID 重复")
            used.add(slot[name])
        for name in ("role", "need"):
            if not isinstance(slot[name], str) or not slot[name].strip() or len(slot[name]) > 1000:
                _fail("SHEET_SEMANTICS", "每个槽位必须声明角色和需求")
        rect = slot["rect"]
        if not isinstance(rect, list) or len(rect) != 4 or any(type(v) is not int for v in rect):
            _fail("SHEET_RECT", "槽位矩形必须是四个像素整数")
        x, y, w, h = rect
        if x < 0 or y < 0 or w < 1 or h < 1 or x + w > size[0] or y + h > size[1]:
            _fail("SHEET_RECT", "槽位超出源板")
        if w * h > MAX_SLOT_PIXELS:
            _fail("SHEET_SLOT_BUDGET", "单槽像素超独立资产预算")
        for ox, oy, ow, oh in rectangles:
            if x < ox + ow and ox < x + w and y < oy + oh and oy < y + h:
                _fail("SHEET_SLOT_OVERLAP", "槽位矩形重叠")
        rectangles.append(rect)
        method = slot["method"]
        if 'alpha_cleanup' in slot:
            from html_asset_sheet_cleanup import validate_cleanup
            if method != 'source_alpha':
                _fail('SHEET_CLEANUP_METHOD', '透明清理仅支持source_alpha')
            try:
                validate_cleanup(slot['alpha_cleanup'])
            except ValueError as exc:
                _fail('SHEET_CLEANUP_PARAMS', str(exc))
        if method not in ("source_alpha", "mask", "boundary_color"):
            _fail("SHEET_METHOD", "处理方法不支持")
        if method == "boundary_color":
            bg = slot.get("background")
            _fields(bg, ("rgb", "tolerance"))
            if (not isinstance(bg["rgb"], list) or len(bg["rgb"]) != 3
                    or not all(_integer(v, 0, 255) for v in bg["rgb"])
                    or not _integer(bg["tolerance"], 0, 64)):
                _fail("SHEET_BACKGROUND", "背景色或阈值不合法")
        elif "background" in slot:
            _fail("SHEET_BACKGROUND", "非纯色处理不能声明色键参数")
        anchors = slot.get("anchors", [])
        if not isinstance(anchors, list) or len(anchors) > 16:
            _fail("SHEET_ANCHOR", "锚点必须为最多16项数组")
        anchor_ids = set()
        for anchor in anchors:
            _fields(anchor, ("id", "x", "y"))
            _identifier(anchor["id"])
            if anchor["id"] in anchor_ids:
                _fail("SHEET_ANCHOR", "同资产锚点 ID 重复")
            anchor_ids.add(anchor["id"])
            if not _integer(anchor["x"], x, x + w - 1) or not _integer(anchor["y"], y, y + h - 1):
                _fail("SHEET_ANCHOR", "锚点必须位于所属槽位内")


def _boundary_alpha(rgba, background):
    """Remove only four-connected declared background at the slot boundary."""
    height, width = rgba.shape[:2]
    color = np.asarray(background["rgb"], dtype=np.int16)
    difference = np.abs(rgba[:, :, :3].astype(np.int16) - color).max(axis=2)
    eligible = bytearray(((difference <= background["tolerance"]) | (rgba[:, :, 3] == 0)).tobytes())
    removed = bytearray(width * height)
    queue = deque()

    def add(index):
        if eligible[index] and not removed[index]:
            removed[index] = 1
            queue.append(index)

    for x in range(width):
        add(x)
        add((height - 1) * width + x)
    for y in range(height):
        add(y * width)
        add(y * width + width - 1)
    while queue:
        index = queue.popleft()
        x = index % width
        if x:
            add(index - 1)
        if x + 1 < width:
            add(index + 1)
        if index >= width:
            add(index - width)
        if index + width < width * height:
            add(index + width)
    alpha = rgba[:, :, 3].copy()
    alpha[np.frombuffer(removed, dtype=np.uint8).reshape(height, width) != 0] = 0
    return alpha


def _extract_slot(source, slot, masks):
    x, y, width, height = slot["rect"]
    crop = source.crop((x, y, x + width, y + height))
    rgba = np.array(crop)
    method = slot["method"]
    processing = {"method": method, "version": PROCESSOR_VERSION}
    if 'alpha_cleanup' in slot:
        from html_asset_sheet_cleanup import clean_alpha
        before = Image.fromarray(rgba[:, :, 3]).getbbox()
        try:
            rgba, diagnostic = clean_alpha(rgba, slot['alpha_cleanup'])
        except ValueError as exc:
            _fail('SHEET_CLEANUP_BUDGET', str(exc))
        diagnostic['before_bbox'] = list(before) if before else None
        after = Image.fromarray(rgba[:, :, 3]).getbbox()
        diagnostic['after_bbox'] = list(after) if after else None
        processing['alpha_cleanup'] = diagnostic
    if method == "mask":
        if slot["id"] not in masks:
            _fail("SHEET_MASK_MISSING", "槽位缺少分割遮罩")
        mask_payload = masks[slot["id"]]
        mask = _decode(mask_payload, mask=True)
        if mask.size != source.size:
            _fail("SHEET_MASK_SIZE", "遮罩必须匹配整板尺寸")
        bbox = mask.getbbox()
        if bbox and (bbox[0] < x or bbox[1] < y or bbox[2] > x + width or bbox[3] > y + height):
            _fail("SHEET_MASK_OUTSIDE_SLOT", "分割遮罩包含槽外像素")
        values = np.array(mask.crop((x, y, x + width, y + height)), dtype=np.uint16)
        rgba[:, :, 3] = (rgba[:, :, 3].astype(np.uint16) * values + 127) // 255
        processing["mask_sha256"] = hashlib.sha256(mask_payload).hexdigest()
    elif method == "boundary_color":
        rgba[:, :, 3] = _boundary_alpha(rgba, slot["background"])
        processing["background"] = copy.deepcopy(slot["background"])
    alpha = Image.fromarray(rgba[:, :, 3])
    bbox = alpha.getbbox()
    if not bbox:
        _fail("SHEET_EMPTY", "槽位没有有效前景")
    if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == width or bbox[3] == height:
        _fail("SHEET_EDGE_CONTACT", "主体接触槽位边界，需检查裁切或背景")
    anchors = []
    for anchor in slot.get("anchors", []):
        px, py = anchor["x"] - x, anchor["y"] - y
        if rgba[py, px, 3] == 0:
            _fail("SHEET_ANCHOR_EMPTY", "锚点不在保留前景上")
        anchors.append({"id": anchor["id"], "x": px, "y": py,
                        "nx": px / width, "ny": py / height})
    # Clear invisible RGB without changing visible pixels or soft-alpha colors.
    rgba[rgba[:, :, 3] == 0, :3] = 0
    buffer = io.BytesIO()
    Image.fromarray(rgba).save(buffer, format="PNG")
    payload = buffer.getvalue()
    entry = {
        "id": slot["asset_id"], "slot_id": slot["id"], "version": VERSION,
        "role": slot["role"], "need": slot["need"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": {"width": width, "height": height}, "alpha_bbox": list(bbox),
        "transparent_background": True, "anchors": anchors,
        "crop_rect": list(slot["rect"]), "crop_offset": [x, y], "scale": 1,
        "processing": processing, "status": "pending_review",
        "identity_review": "pending", "edge_review": "pending",
    }
    return entry, payload


def extract_asset_sheet(source_bytes: bytes, specification: dict,
                        *, masks: dict[str, bytes] | None = None) -> dict[str, Any]:
    """Extract candidates without publication; structural failure raises.

    Slot-local failures are returned independently, preserving valid candidates
    for review. Every candidate remains pending identity and edge review.
    """
    source = _decode(source_bytes)
    _validate(specification, source.size)
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != specification["source_sha256"]:
        _fail("SHEET_HASH", "源板字节与声明摘要不符")
    masks = {} if masks is None else masks
    expected_masks = {s["id"] for s in specification["slots"] if s["method"] == "mask"}
    if not isinstance(masks, dict) or set(masks) - expected_masks:
        _fail("SHEET_MASK_KEYS", "遮罩含未声明的槽位")
    assets, failures, images = [], [], {}
    for slot in specification["slots"]:
        try:
            entry, payload = _extract_slot(source, slot, masks)
            entry["source"] = {
                "sheet_id": specification["id"], "sha256": digest,
                "slot_id": slot["id"],
            }
            assets.append(entry)
            images[entry["id"]] = payload
        except HtmlAssetSheetError as exc:
            failures.append({"slot_id": slot["id"], "asset_id": slot["asset_id"],
                             "code": exc.code, "message": str(exc)})
    spec_hash = hashlib.sha256(json.dumps(specification, sort_keys=True,
                                          ensure_ascii=False).encode()).hexdigest()
    mask_hashes = {key: hashlib.sha256(value).hexdigest()
                   for key, value in masks.items() if isinstance(value, bytes)}
    request_key = hashlib.sha256(json.dumps({
        "source": digest, "spec": spec_hash, "masks": mask_hashes,
        "processor": PROCESSOR_VERSION,
    }, sort_keys=True).encode()).hexdigest()
    return {
        "manifest": {
            "format": "hps.html.asset_sheet.extraction", "version": VERSION,
            "sheet_id": specification["id"], "source_sha256": digest,
            "source_size": {"width": source.width, "height": source.height},
            "processor_version": PROCESSOR_VERSION, "spec_sha256": spec_hash,
            "request_key": request_key, "assets": assets, "failures": failures,
            "status": "partial" if failures else "pending_review",
        },
        "images": images,
    }
