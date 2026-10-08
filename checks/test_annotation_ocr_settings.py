# -*- coding: utf-8 -*-
"""勾画 OCR 密钥设置接线回归:

- `annotation_ocr_baidu_api_key` 属于密钥集合:读取时脱敏、保存时保留掩码;
- annotation_runtime 以设置优先、环境变量兜底的方式解析密钥(源级契约);
- project_service 放行的暂停值与编排器阶段表对齐(annotation 不再被丢弃)。
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import settings_service  # noqa: E402


def test_annotation_ocr_key_is_treated_as_a_secret() -> None:
    assert "annotation_ocr_baidu_api_key" in settings_service.SETTINGS_SECRET_KEYS

    masked = settings_service.mask_sensitive_settings(
        {"annotation_ocr_baidu_api_key": "bce-v3/ak/sk"}, force=True
    )
    assert masked["annotation_ocr_baidu_api_key"] == settings_service.MASKED_SETTINGS_VALUE

    preserved = settings_service.preserve_masked_secrets(
        {"annotation_ocr_baidu_api_key": settings_service.MASKED_SETTINGS_VALUE},
        {"annotation_ocr_baidu_api_key": "bce-v3/ak/sk"},
    )
    assert preserved["annotation_ocr_baidu_api_key"] == "bce-v3/ak/sk"


def test_annotation_runtime_resolves_ocr_key_settings_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """设置库有值用设置库;为空回退环境变量(源级契约守卫)。"""
    source = (ROOT / "annotation_runtime.py").read_text(encoding="utf-8")
    assert 'get_setting("annotation_ocr_baidu_api_key")' in source
    assert 'PPT_ANNOTATION_BAIDU_OCR_KEY' in source
    assert "_annotation_ocr_api_key" in source
    # ocr_ready 必须与配置解析同源,否则设置页填了 Key 仍提示未配置
    assert "ocr_ready=lambda: bool(_annotation_ocr_api_key())" in source


def test_orchestrator_aliases_legacy_mask_pause_to_ai_mask() -> None:
    source = (ROOT / "one_click_orchestrator.py").read_text(encoding="utf-8")
    # 存量创作包的 "mask" 在匹配时归一为 "ai_mask"
    assert '"ai_mask" if raw_name == "mask" else raw_name' in source
