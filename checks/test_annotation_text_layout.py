# -*- coding: utf-8 -*-
"""annotation_text_layout 单测:缓存键命中、revision 递增、粒度诚实、纠正。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_ocr_baidu import BaiduOcrResult  # noqa: E402
from annotation_text_layout import (  # noqa: E402
    TextLayoutBuilder,
    TextLayoutDependencies,
    build_layout_payload_from_ocr,
    candidate_tokens,
)


def _ocr_result(with_chars=True):
    from annotation_ocr_baidu import BaiduOcrChar, BaiduOcrLine

    lines = [
        BaiduOcrLine(
            text="报名截止9月30日",
            left=120, top=300, width=511, height=37,
            chars=(
                BaiduOcrChar("报", 131, 307, 29, 37),
                BaiduOcrChar("名", 168, 307, 28, 37),
            ) if with_chars else (),
            probability_average=0.99,
        ),
        BaiduOcrLine(
            text="Online registration",
            left=121, top=561, width=582, height=39,
            chars=(),
            probability_average=1.0,
        ),
    ]
    return BaiduOcrResult(lines=tuple(lines), direction=0, log_id=42, granularity="char" if with_chars else "line")


class _MemoryIO:
    def __init__(self):
        self.files = {}

    def write(self, path, payload):
        self.files[str(path)] = payload

    def read(self, path):
        return self.files.get(str(path))


def _builder(io=None, config=None):
    from annotation_ocr_baidu import BaiduOcrEngineConfig

    io = io or _MemoryIO()
    deps = TextLayoutDependencies(
        write_json_atomic=io.write,
        read_json_file=io.read,
        ocr_config_provider=config or (lambda: BaiduOcrEngineConfig(api_key="k" * 10)),
    )
    return TextLayoutBuilder(deps), io


def test_layout_payload_stable_ids_and_char_tokens():
    payload = build_layout_payload_from_ocr(
        "slide_001", "a" * 64, (1920, 1080), _ocr_result(),
        layout_revision=1, cache_key="ck", created_at="t0",
    )
    assert payload["schema_version"] == 1
    assert payload["layout_revision"] == 1
    assert payload["reading_order"] == ["line_001_000", "line_001_001"]
    first = payload["lines"][0]
    assert first["text"] == "报名截止9月30日"
    assert [t["token_id"] for t in first["tokens"]] == ["tok_001_0000", "tok_001_0001"]
    assert first["tokens"][0]["polygon"] == [[131, 307], [160, 307], [160, 344], [131, 344]]
    # 第二行无字级结果 → 空 tokens,布局层按行级候选输出
    assert payload["lines"][1]["tokens"] == []


def test_candidate_tokens_line_fallback_is_honest():
    payload = build_layout_payload_from_ocr(
        "slide_001", "a" * 64, (1920, 1080), _ocr_result(with_chars=False),
        layout_revision=2, cache_key="ck",
    )
    tokens = candidate_tokens(payload)
    assert all(token["granularity"] == "line" for token in tokens)
    assert len(tokens) == 2
    # 严禁整行框均分字框:token 数等于行数
    assert not any(t["token_id"].startswith("tok_") for t in tokens)


def test_get_or_detect_cache_hit_avoids_second_ocr():
    builder, io = _builder()
    calls = []

    def recognize(image_bytes, config):
        calls.append(1)
        return _ocr_result()

    image = b"image-bytes-v1"
    first, detected1 = builder.get_or_detect(
        "run", "slide_001", image, "a" * 64, (1920, 1080), recognize=recognize
    )
    assert detected1 is True and len(calls) == 1

    second, detected2 = builder.get_or_detect(
        "run", "slide_001", image, "a" * 64, (1920, 1080), recognize=recognize
    )
    assert detected2 is False and len(calls) == 1  # 缓存命中,零模型请求
    assert second["layout_revision"] == 1


def test_image_change_bumps_revision_and_invalidates_correction():
    builder, io = _builder()
    image1 = b"image-v1"
    builder.get_or_detect("run", "slide_001", image1, "a" * 64, (1920, 1080), recognize=lambda *_: _ocr_result())

    layout = builder.load("run", "slide_001")
    layout, changed = builder.apply_correction(layout, "tok_001_0000", "报 名")
    assert changed
    builder.save("run", "slide_001", layout)

    image2 = b"image-v2"
    new_layout, detected = builder.get_or_detect(
        "run", "slide_001", image2, "b" * 64, (1920, 1080), recognize=lambda *_: _ocr_result()
    )
    assert detected is True
    assert new_layout["layout_revision"] == 2  # revision 递增,ID 空间整体更新
    assert new_layout["corrections"] == {}  # 重识别不继承纠正


def test_correction_keeps_original_and_flags_char_change():
    payload = build_layout_payload_from_ocr(
        "slide_001", "a" * 64, (1920, 1080), _ocr_result(), layout_revision=1, cache_key="ck",
    )
    builder, io = _builder()
    # 相同长度:chars_changed=False
    updated, changed = builder.apply_correction(payload, "tok_001_0000", "板")
    assert changed
    correction = updated["corrections"]["tok_001_0000"]
    assert correction["text"] == "板" and correction["chars_changed"] is False
    # 字符数变化:chars_changed=True(重定位需求)
    updated, _ = builder.apply_correction(payload, "tok_001_0000", "报名")
    assert updated["corrections"]["tok_001_0000"]["chars_changed"] is True
    # 原识别文本仍保留在 lines 中,纠正只进 corrections
    assert updated["lines"][0]["tokens"][0]["char"] == "报"
    # 清除纠正
    cleared, changed = builder.apply_correction(updated, "tok_001_0000", "")
    assert changed and "tok_001_0000" not in cleared["corrections"]
    # 未知 token
    with pytest.raises(KeyError):
        builder.apply_correction(payload, "tok_999_9999", "x")


def test_candidate_tokens_reflect_correction():
    payload = build_layout_payload_from_ocr(
        "slide_001", "a" * 64, (1920, 1080), _ocr_result(), layout_revision=1, cache_key="ck",
    )
    builder, _ = _builder()
    updated, _ = builder.apply_correction(payload, "tok_001_0000", "板")
    tokens = {t["token_id"]: t for t in candidate_tokens(updated)}
    assert tokens["tok_001_0000"]["text"] == "板"
    assert tokens["tok_001_0000"]["original_text"] == "报"
    assert tokens["tok_001_0000"]["corrected"] is True
    assert tokens["tok_001_0001"]["corrected"] is False
