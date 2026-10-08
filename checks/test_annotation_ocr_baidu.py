# -*- coding: utf-8 -*-
"""百度 OCR 适配器(annotation_ocr_baidu)离线单测。

默认全部离线:HTTP 传输用注入的 stub,响应样本取自 2026-09-27 真实调用
的截录。真实引擎验收用例由环境变量 ``PPT_ANNOTATION_BAIDU_OCR_KEY`` 显式
开启,默认 pytest 不访问网络、不消耗配额。
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import httpx
import pytest

from annotation_ocr_baidu import (
    BAIDU_OCR_ENGINE_VERSION,
    BaiduOcrEngineConfig,
    BaiduOcrError,
    build_ocr_cache_key,
    parse_baidu_ocr_response,
    recognize_text_lines,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "annotations"

# --- 2026-09-27 真实调用截录(字级粒度,detect_direction=true) ---
RECORDED_CHAR_PAYLOAD = {
    "log_id": 2104189872890201493,
    "direction": 0,
    "words_result_num": 2,
    "words_result": [
        {
            "words": "2026年秋季课程报名说明",
            "location": {"left": 124, "top": 115, "width": 720, "height": 59},
            "chars": [
                {"char": "2", "location": {"left": 124, "top": 115, "width": 29, "height": 57}},
                {"char": "0", "location": {"left": 165, "top": 115, "width": 30, "height": 57}},
                {"char": "年", "location": {"left": 284, "top": 115, "width": 45, "height": 57}},
            ],
        },
        {
            "words": "报名截止时间9月30日18:00",
            "location": {"left": 120, "top": 307, "width": 511, "height": 37},
            "chars": [
                {"char": "报", "location": {"left": 131, "top": 307, "width": 29, "height": 37}},
                {"char": "名", "location": {"left": 168, "top": 307, "width": 28, "height": 37}},
            ],
        },
    ],
}

RECORDED_LINE_PAYLOAD = {
    "log_id": 2104189870773476184,
    "direction": 0,
    "words_result_num": 2,
    "words_result": [
        {
            "words": "Online registration opens on Sep 1st",
            "location": {"left": 121, "top": 561, "width": 582, "height": 39},
            "probability": {"average": 1.0, "variance": 0.0, "min": 1.0},
        },
        {
            "words": "Registration Fee:250 CNY per student",
            "location": {"left": 118, "top": 643, "width": 624, "height": 35},
            "probability": {"average": 0.9999933, "variance": 0.0, "min": 0.9988},
        },
    ],
}

CONFIG = BaiduOcrEngineConfig(api_key="bce-v3/ALTAK-testkey/0000000000000000000000000000000000")


# ---------------------------------------------------------------- 解析


def test_parse_char_payload_keeps_true_char_boxes():
    result = parse_baidu_ocr_response(RECORDED_CHAR_PAYLOAD)
    assert result.granularity == "char"
    assert result.direction == 0
    assert result.log_id == 2104189872890201493
    assert len(result.lines) == 2
    first = result.lines[0]
    assert first.text == "2026年秋季课程报名说明"
    assert (first.left, first.top, first.width, first.height) == (124, 115, 720, 59)
    assert first.polygon == [[124, 115], [844, 115], [844, 174], [124, 174]]
    char = first.chars[0]
    assert char.char == "2"
    assert char.polygon == [[124, 115], [153, 115], [153, 172], [124, 172]]
    # 引擎归一化的全角冒号必须原样保留,不得在上层再加工
    assert "18:00" in result.lines[1].text


def test_parse_line_only_payload_reports_line_granularity():
    result = parse_baidu_ocr_response(RECORDED_LINE_PAYLOAD)
    assert result.granularity == "line"
    assert result.lines[0].chars == ()
    assert result.lines[0].probability_average == 1.0
    assert abs(result.lines[1].probability_average - 0.9999933) < 1e-9
    assert result.engine_version == BAIDU_OCR_ENGINE_VERSION


@pytest.mark.parametrize(
    "payload,category,retryable",
    [
        ({"error_code": 23, "error_msg": "IAM API-KEY authentication failed"}, "auth", False),
        ({"error_code": 110, "error_msg": "Access token invalid"}, "auth", False),
        ({"error_code": 18, "error_msg": "Open api qps request limit reached"}, "rate_limit", True),
        ({"error_code": 17, "error_msg": "Open api daily request limit reached"}, "quota", False),
        ({"error_code": 216201, "error_msg": "image format error"}, "image", False),
        ({"error_code": 282200, "error_msg": "logic engine error"}, "engine", True),
        # 千帆面兼容的错误体:非 int code 不猜分类,如实报 protocol
        ({"error": {"code": "InvalidParameter", "message": "bad request", "type": "invalid_request_error"}}, "protocol", False),
    ],
)
def test_error_payload_maps_to_categories(payload, category, retryable):
    with pytest.raises(BaiduOcrError) as excinfo:
        parse_baidu_ocr_response(payload)
    assert excinfo.value.category == category
    assert excinfo.value.retryable is retryable


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "not-a-dict",
        {},
        {"words_result": "no"},
        {"words_result": [{"words": "文本"}]},  # 缺 location
        {"words_result": [{"words": "文本", "location": {"left": -1, "top": 0, "width": 1, "height": 1}}]},
        {"words_result": [{"words": 42, "location": {"left": 0, "top": 0, "width": 1, "height": 1}}]},
        {"words_result": [{"words": "文本", "location": {}, "chars": [{"char": "", "location": {}}]}]},
    ],
)
def test_malformed_payload_raises_protocol_error_not_empty_success(payload):
    with pytest.raises(BaiduOcrError) as excinfo:
        parse_baidu_ocr_response(payload)
    assert excinfo.value.category == "protocol"


# ---------------------------------------------------------------- 调用


def _stub_transport(captured, payload=None, raise_exc=None):
    def transport(endpoint, headers, form, timeout_sec):
        captured.update(
            endpoint=endpoint, headers=headers, form=form, timeout_sec=timeout_sec
        )
        if raise_exc is not None:
            raise raise_exc
        return 200, payload
    return transport


def test_recognize_builds_bounded_request_and_parses_response():
    image_bytes = b"\x89PNG-fake-bytes"
    captured: dict = {}
    transport = _stub_transport(captured, payload=RECORDED_CHAR_PAYLOAD)

    result = recognize_text_lines(image_bytes, CONFIG, transport=transport)

    assert captured["endpoint"] == CONFIG.endpoint
    assert captured["headers"]["Authorization"] == f"Bearer {CONFIG.api_key}"
    assert captured["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert captured["timeout_sec"] == CONFIG.timeout_sec
    assert base64.b64decode(captured["form"]["image"]) == image_bytes
    # 防回归:image 字段必须是 str。bytes 值会让 httpx 走 multipart 编码,
    # 真实端点返回 image format error(216201)。
    assert isinstance(captured["form"]["image"], str)
    assert captured["form"]["recognize_granularity"] == "small"
    assert captured["form"]["language_type"] == "CHN_ENG"
    assert captured["form"]["detect_direction"] == "true"
    assert captured["form"]["probability"] == "true"
    assert result.granularity == "char"
    assert result.request_elapsed_sec is not None and result.request_elapsed_sec >= 0


def test_recognize_rejects_oversize_image_before_transport():
    captured: dict = {}

    def must_not_call(*args, **kwargs):  # pragma: no cover - 不应触达
        captured["called"] = True
        raise AssertionError("transport must not be called for oversize image")

    oversize = b"\x89PNG" + b"0" * (6 * 1024 * 1024 + 1)  # base64 后 > 8M
    with pytest.raises(BaiduOcrError) as excinfo:
        recognize_text_lines(oversize, CONFIG, transport=must_not_call)
    assert excinfo.value.category == "image"
    assert "called" not in captured


@pytest.mark.parametrize(
    "image_bytes,config,code",
    [
        (b"", CONFIG, "empty_image"),
        (b"\x89PNG-ok", BaiduOcrEngineConfig(api_key=""), "missing_api_key"),
    ],
)
def test_recognize_input_guards(image_bytes, config, code):
    with pytest.raises(BaiduOcrError) as excinfo:
        recognize_text_lines(image_bytes, config, transport=_stub_transport({}, payload={}))
    assert excinfo.value.code == code


def test_network_failure_maps_to_retryable_and_never_leaks_key():
    captured: dict = {}
    transport = _stub_transport(captured, raise_exc=httpx.ConnectError("connection refused"))
    with pytest.raises(BaiduOcrError) as excinfo:
        recognize_text_lines(b"\x89PNG-fake", CONFIG, transport=transport)
    assert excinfo.value.category == "network"
    assert excinfo.value.retryable is True
    assert CONFIG.api_key not in str(excinfo.value)
    assert CONFIG.api_key not in excinfo.value.message


def test_http_error_payload_from_transport_maps_category():
    captured: dict = {}
    transport = _stub_transport(captured, payload={"error_code": 18, "error_msg": "Open api qps request limit reached"})
    with pytest.raises(BaiduOcrError) as excinfo:
        recognize_text_lines(b"\x89PNG-fake", CONFIG, transport=transport)
    assert excinfo.value.category == "rate_limit"
    assert excinfo.value.retryable is True
    assert excinfo.value.http_status == 200


# ---------------------------------------------------------------- 缓存键


def test_cache_key_stable_and_sensitive():
    image_a = b"image-a-bytes"
    image_b = b"image-b-bytes"
    assert build_ocr_cache_key(image_a, CONFIG) == build_ocr_cache_key(image_a, CONFIG)
    assert build_ocr_cache_key(image_a, CONFIG) != build_ocr_cache_key(image_b, CONFIG)

    other_granularity = BaiduOcrEngineConfig(api_key=CONFIG.api_key, recognize_granularity="big")
    assert build_ocr_cache_key(image_a, CONFIG) != build_ocr_cache_key(image_a, other_granularity)

    assert build_ocr_cache_key(image_a, CONFIG) != build_ocr_cache_key(image_a, CONFIG, roi=[100, 100, 800, 600])

    # 换密钥不换内容 => 同一缓存键;密钥派生信息不落盘
    other_key = BaiduOcrEngineConfig(api_key="bce-v3/ALTAK-other/ffffffffffffffffffffffffffffffff")
    assert build_ocr_cache_key(image_a, CONFIG) == build_ocr_cache_key(image_a, other_key)


def test_public_snapshot_excludes_secret():
    snapshot = CONFIG.public_snapshot()
    assert CONFIG.api_key not in json.dumps(snapshot)
    assert snapshot["engine_version"] == BAIDU_OCR_ENGINE_VERSION


# ---------------------------------------------------------------- 真实引擎(opt-in)

_REAL_KEY = os.environ.get("PPT_ANNOTATION_BAIDU_OCR_KEY", "").strip()


@pytest.mark.skipif(not _REAL_KEY, reason="set PPT_ANNOTATION_BAIDU_OCR_KEY to run the real engine acceptance")
def test_real_engine_recognizes_frozen_fixture():
    image_bytes = (FIXTURES / "sample_slide.png").read_bytes()
    result = recognize_text_lines(image_bytes, BaiduOcrEngineConfig(api_key=_REAL_KEY))

    assert result.granularity == "char"
    assert result.direction is not None
    texts = [line.text for line in result.lines]
    assert len(texts) >= 6
    date_line = next(line for line in result.lines if "9月30日" in line.text)
    assert date_line.width > 0 and date_line.height > 0
    assert any("2026" in text for text in texts)
    assert result.request_elapsed_sec is not None
