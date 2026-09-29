# -*- coding: utf-8 -*-
"""ZIP 配置包导入限额回归(R5-004/R5-005):

- config.json 主条目 8MB 上限(此前解压后才解析、无限制);
- 全包解压总量与条目数上限;
- 重复条目与规范化等价资源条目拒绝,不再静默覆盖。
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config_portability_service as cps  # noqa: E402


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def _config_entry(size_hint: int = 0) -> bytes:
    payload = {"version": 1, "providers": {}, "image_styles": {}}
    if size_hint:
        payload["padding"] = "x" * size_hint
    return json.dumps(payload).encode("utf-8")


def test_valid_bundle_still_imports() -> None:
    data = _zip_bytes({
        cps.CONFIG_ZIP_ENTRY: _config_entry(),
        "assets/ref.png": b"fake-png-bytes",
    })
    payload = cps._read_zip_bundle_payload(data)
    assert isinstance(payload, dict)


def test_oversized_config_json_rejected() -> None:
    data = _zip_bytes({
        cps.CONFIG_ZIP_ENTRY: _config_entry(size_hint=cps.CONFIG_ZIP_MAX_CONFIG_JSON_BYTES),
    })
    try:
        cps._read_zip_bundle_payload(data)
    except ValueError as exc:
        assert "config.json" in str(exc)
    else:
        raise AssertionError("超限 config.json 未被拒绝")


def test_duplicate_entries_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(cps.CONFIG_ZIP_ENTRY, _config_entry())
        archive.writestr(cps.CONFIG_ZIP_ENTRY, _config_entry())
    try:
        cps._read_zip_bundle_payload(buffer.getvalue())
    except ValueError as exc:
        assert "重复条目" in str(exc)
    else:
        raise AssertionError("重复主条目未被拒绝")


def test_normalized_duplicate_asset_entries_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(cps.CONFIG_ZIP_ENTRY, _config_entry())
        archive.writestr("assets/a.png", b"one")
        archive.writestr("assets/./a.png", b"two")
    try:
        cps._read_zip_bundle_payload(buffer.getvalue())
    except ValueError as exc:
        assert "等价重复" in str(exc)
    else:
        raise AssertionError("规范化冲突资源条目未被拒绝")
