"""Bounded untrusted delivery parsing. Never execute or extract external files."""
from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
import stat
import zipfile

from html_handoff_models import ExternalResult, ImportRequest

MAX_ZIP_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_RESULT_BYTES = 512 * 1024
MAX_REPORT_BYTES = 256 * 1024
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024


class DeliveryError(ValueError):
    pass


def _text(data):
    try:
        return data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise DeliveryError("交付文本必须为 UTF-8") from exc


def _validate_name(entry):
    name = entry.filename
    value = name[:-1] if entry.is_dir() else name
    if (not value or name != entry.orig_filename or "\\" in name or ":" in name or PurePosixPath(value).is_absolute()
            or any(p in ("", ".", "..") for p in value.split("/"))
            or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
        raise DeliveryError("交付包包含越界路径、链接或加密文件")
    for part in value.split("/"):
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", part) or part.endswith(".")
                or re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", part.split(".")[0], re.IGNORECASE)):
            raise DeliveryError("交付文件名须为可携带的英文、数字、点、横线或下划线，不能使用设备名")
    if entry.is_dir():
        if value != "evidence" and not value.startswith("evidence/"):
            raise DeliveryError("交付包仅允许 evidence 辅助目录")
        return
    if name in ("result.json", "report.md", "verification.json", "preflight.json"):
        return
    if not name.startswith("evidence/") or PurePosixPath(name).suffix.lower() not in (".png", ".json", ".md", ".txt"):
        raise DeliveryError("交付包仅接受 result.json、report.md 和 evidence 内的 PNG/JSON/文本；不接受代码或 HTML")


def read_delivery(payload):
    payload = ImportRequest.model_validate(payload)
    if payload.delivery_base64 is None:
        data = json.dumps(payload.result.model_dump(mode="json"), ensure_ascii=False).encode()
        if len(data) > MAX_RESULT_BYTES:
            raise DeliveryError("结果 JSON 超过512KB")
        files = {"result.json": data}
        if payload.report_markdown is not None:
            files["report.md"] = payload.report_markdown.encode()
        raw, kind = data, "json"
    else:
        try:
            raw = base64.b64decode(payload.delivery_base64, validate=True)
        except (ValueError, TypeError) as exc:
            raise DeliveryError("交付 ZIP 编码无效") from exc
        if len(raw) > MAX_ZIP_BYTES:
            raise DeliveryError("交付 ZIP 超过4MB")
        files, names, total = {}, set(), 0
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                entries = archive.infolist()
                if len(entries) > 32:
                    raise DeliveryError("交付包文件数超过32")
                for entry in entries:
                    _validate_name(entry)
                    folded = entry.filename.rstrip("/").casefold()
                    if folded in names:
                        raise DeliveryError("交付包有重复文件路径")
                    names.add(folded)
                    total += entry.file_size
                    limit = {"result.json": MAX_RESULT_BYTES, "report.md": MAX_REPORT_BYTES}.get(entry.filename, MAX_EVIDENCE_BYTES)
                    if entry.file_size > limit or total > MAX_TOTAL_BYTES:
                        raise DeliveryError("交付包解压大小超过限制")
                    if not entry.is_dir():
                        files[entry.filename] = archive.read(entry)
        except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError) as exc:
            raise DeliveryError("交付 ZIP 损坏或压缩格式不支持") from exc
        if not {"result.json", "report.md"} <= files.keys():
            raise DeliveryError("交付 ZIP 根目录必须包含 result.json 和 report.md")
        kind = "zip"
    if len(files.get("report.md", b"")) > MAX_REPORT_BYTES:
        raise DeliveryError("交付报告超过256KB")
    for name, data in files.items():
        if PurePosixPath(name).suffix.lower() == ".png":
            from PIL import Image
            try:
                with Image.open(io.BytesIO(data)) as image:
                    if image.format != "PNG" or image.width * image.height > 4194304:
                        raise ValueError("image bounds")
                    image.verify()
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                raise DeliveryError("交付 PNG 无效或超过4M像素") from exc
        else:
            _text(data)
    try:
        result = ExternalResult.model_validate_json(_text(files["result.json"]))
    except ValueError as exc:
        raise DeliveryError("result.json 不符合外部结果0.2.0格式，请按原模板填写") from exc
    summary = {"kind": kind, "sha256": hashlib.sha256(raw).hexdigest(),
               "report_markdown": _text(files["report.md"]) if "report.md" in files else None,
               "report_source": "external_report_unverified",
               "files": [{"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()]}
    return result, summary, files, raw
