# -*- coding: utf-8 -*-
"""百度通用文字识别 OCR 适配器(勾画标注模块 W0 选型落地)。

职责边界
--------
- 本模块是勾画标注模块 OCR 统一接口的首个引擎适配器,只做:
  受控参数封装、API Key 或 AK/SK 鉴权、有界 HTTP 传输、响应解析与错误映射、
  缓存键计算。
- 纯模块:不导入 server、FastAPI、数据库或任何应用装配代码;上游 API Key
  由调用方注入,本模块不读取全局设置,也绝不把密钥写入日志或错误信息。
- 坐标语义:百度返回的 location/chars 均为**提交图像原始像素坐标系**(原点
  左上角)。调用方(统一的 annotation_text_layout 层)负责记录 ROI/缩放/
  旋转的完整反变换;本适配器不做任何坐标换算。
- 文本保真:引擎会把半角冒号等归一化为全角(如实测 ``18:00`` 识别为
  ``18:00``),本模块原样保留识别文本;纠正与重定位属于上层
  ``annotation_text_layout`` 的职责,不在引擎适配器内加工。
- 字级真实性:``recognize_granularity="small"`` 返回引擎真实检测的单字框;
  无单字结果时粒度诚实标记为 ``line``,严禁上层把整行框均分成"字框"。

鉴权方式(2026-09-27 实测定稿)
--------------------------------
新版统一 API Key(``bce-v3/{AK}/{SK}`` 格式,授权范围含"AI 开放能力")直接以
``Authorization: Bearer <API Key>`` 请求头调用 aip.baidubce.com,无需换取
access_token,也无需 bce-auth-v1/v3 签名。错误密钥返回 HTTP 200 +
``error_code=23``(IAM API-KEY authentication failed),不是 HTTP 4xx。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import urlsplit, quote, parse_qsl
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import httpx

__all__ = [
    "BAIDU_OCR_ENGINE_VERSION",
    "BAIDU_OCR_GENERAL_ENDPOINT",
    "BaiduOcrEngineConfig",
    "BaiduOcrChar",
    "BaiduOcrLine",
    "BaiduOcrResult",
    "BaiduOcrError",
    "parse_baidu_ocr_response",
    "recognize_text_lines",
    "build_ocr_cache_key",
]

BAIDU_OCR_GENERAL_ENDPOINT = "https://aip.baidubce.com/rest/2.0/ocr/v1/general"

# 引擎/配置快照版本:默认参数或解析行为变更时必须递增,并同步更新
# docs/annotation-validation/adapter-decision.md,缓存键会携带该版本。
BAIDU_OCR_ENGINE_VERSION = "baidu_ocr_general_v1"

# 官方通用文字识别接口限制:base64 编码后不超过 8M(见接口文档 image 参数)。
BAIDU_OCR_MAX_BASE64_BYTES = 8 * 1024 * 1024

# 每日/总量配额耗尽:按 governor 语义应等待或暂停,不当作内容错误。
_QUOTA_ERROR_CODES = frozenset({17, 19})
# QPS 超限:可短暂等待后重试。
_RATE_LIMIT_ERROR_CODES = frozenset({4, 18})
# 鉴权/密钥类错误:重试无意义,需用户修正配置。
_AUTH_ERROR_CODES = frozenset({15, 23, 110, 111})
# 图片本身非法:重试无意义。
_IMAGE_ERROR_CODES = frozenset({216200, 216201, 216202, 216203})


@dataclass(frozen=True)
class BaiduOcrEngineConfig:
    """一次 OCR 调用的受控参数快照;字段变更会进入缓存键。"""

    api_key: str = field(repr=False)
    language_type: str = "CHN_ENG"
    recognize_granularity: str = "small"
    detect_direction: bool = True
    probability: bool = True
    timeout_sec: float = 20.0
    endpoint: str = BAIDU_OCR_GENERAL_ENDPOINT
    secret_key: str = field(default="", repr=False)

    def public_snapshot(self) -> Dict[str, Any]:
        """返回不含密钥的配置快照,用于日志与缓存键。"""
        return {
            "engine_version": BAIDU_OCR_ENGINE_VERSION,
            "endpoint": self.endpoint,
            "language_type": self.language_type,
            "recognize_granularity": self.recognize_granularity,
            "detect_direction": self.detect_direction,
            "probability": self.probability,
            "auth_mode": "ak_sk" if self.secret_key else "api_key",
        }


@dataclass(frozen=True)
class BaiduOcrChar:
    """单字识别结果;仅 recognize_granularity=small 时由引擎真实检测。"""

    char: str
    left: int
    top: int
    width: int
    height: int

    @property
    def polygon(self) -> List[List[int]]:
        return [
            [self.left, self.top],
            [self.left + self.width, self.top],
            [self.left + self.width, self.top + self.height],
            [self.left, self.top + self.height],
        ]


@dataclass(frozen=True)
class BaiduOcrLine:
    """整行识别结果;box/polygon 为提交图像原始像素坐标。"""

    text: str
    left: int
    top: int
    width: int
    height: int
    chars: Tuple[BaiduOcrChar, ...] = ()
    probability_average: Optional[float] = None

    @property
    def polygon(self) -> List[List[int]]:
        return [
            [self.left, self.top],
            [self.left + self.width, self.top],
            [self.left + self.width, self.top + self.height],
            [self.left, self.top + self.height],
        ]


@dataclass(frozen=True)
class BaiduOcrResult:
    """规范化 OCR 结果;granularity 诚实反映本次响应的真实粒度。"""

    lines: Tuple[BaiduOcrLine, ...]
    direction: Optional[int]
    log_id: Optional[int]
    granularity: str  # "char" | "line"
    engine_version: str = BAIDU_OCR_ENGINE_VERSION
    request_elapsed_sec: Optional[float] = None


@dataclass(eq=False)
class BaiduOcrError(Exception):
    """统一的 OCR 适配器错误;message 不包含任何密钥片段。

    注意:不能加 frozen=True——异常在 raise/from 链路上会被运行时回写
    ``__cause__``/``__traceback__``,冻结会在真实抛出路径上炸出
    ``FrozenInstanceError``。
    """

    code: str
    message: str
    category: str  # auth | quota | rate_limit | image | engine | network | protocol
    retryable: bool
    http_status: Optional[int] = None

    def __str__(self) -> str:  # pragma: no cover - 仅展示
        return f"baidu ocr error [{self.category}/{self.code}]: {self.message}"


def _error_from_payload(payload: Dict[str, Any], http_status: Optional[int]) -> BaiduOcrError:
    raw_code = payload.get("error_code")
    message = str(payload.get("error_msg") or payload.get("error_description") or "unknown baidu ocr error")
    if isinstance(raw_code, int):
        if raw_code in _AUTH_ERROR_CODES:
            return BaiduOcrError(str(raw_code), message, "auth", False, http_status)
        if raw_code in _QUOTA_ERROR_CODES:
            return BaiduOcrError(str(raw_code), message, "quota", False, http_status)
        if raw_code in _RATE_LIMIT_ERROR_CODES:
            return BaiduOcrError(str(raw_code), message, "rate_limit", True, http_status)
        if raw_code in _IMAGE_ERROR_CODES:
            return BaiduOcrError(str(raw_code), message, "image", False, http_status)
        return BaiduOcrError(str(raw_code), message, "engine", True, http_status)
    return BaiduOcrError(str(raw_code), message, "protocol", False, http_status)


def _require_int_location(location: Any, owner: str) -> Tuple[int, int, int, int]:
    if not isinstance(location, dict):
        raise BaiduOcrError("bad_location", f"{owner} location missing or not an object", "protocol", False)
    values: List[int] = []
    for key in ("left", "top", "width", "height"):
        value = location.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise BaiduOcrError(
                "bad_location",
                f"{owner} location.{key} must be a non-negative int, got {value!r}",
                "protocol",
                False,
            )
        values.append(value)
    return values[0], values[1], values[2], values[3]


def parse_baidu_ocr_response(payload: Any) -> BaiduOcrResult:
    """解析百度通用文字识别 JSON 响应为规范化结果。

    错误响应(HTTP 200 + error_code)抛出 :class:`BaiduOcrError`;结构非法
    抛出 category=protocol 错误,绝不把损坏响应伪装成空成功。
    """
    if not isinstance(payload, dict):
        raise BaiduOcrError("bad_payload", "ocr response is not a JSON object", "protocol", False)
    if "error_code" in payload or "error" in payload and isinstance(payload.get("error"), dict):
        nested = payload.get("error")
        if isinstance(nested, dict):
            merged = {"error_code": nested.get("code"), "error_msg": nested.get("message")}
            raise _error_from_payload(merged, None)
        raise _error_from_payload(payload, None)

    rows = payload.get("words_result")
    if not isinstance(rows, list):
        raise BaiduOcrError("bad_words_result", "ocr response missing words_result array", "protocol", False)

    direction = payload.get("direction")
    if direction is not None and not isinstance(direction, int):
        direction = None

    lines: List[BaiduOcrLine] = []
    has_chars = False
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise BaiduOcrError("bad_row", f"words_result[{index}] is not an object", "protocol", False)
        text = row.get("words")
        if not isinstance(text, str):
            raise BaiduOcrError("bad_words", f"words_result[{index}].words is not a string", "protocol", False)
        left, top, width, height = _require_int_location(row.get("location"), f"words_result[{index}]")

        chars: List[BaiduOcrChar] = []
        raw_chars = row.get("chars")
        if isinstance(raw_chars, list):
            for char_index, raw_char in enumerate(raw_chars):
                if not isinstance(raw_char, dict):
                    raise BaiduOcrError(
                        "bad_char", f"words_result[{index}].chars[{char_index}] is not an object", "protocol", False
                    )
                char_text = raw_char.get("char")
                if not isinstance(char_text, str) or not char_text:
                    raise BaiduOcrError(
                        "bad_char",
                        f"words_result[{index}].chars[{char_index}].char is missing",
                        "protocol",
                        False,
                    )
                c_left, c_top, c_width, c_height = _require_int_location(
                    raw_char.get("location"), f"words_result[{index}].chars[{char_index}]"
                )
                chars.append(BaiduOcrChar(char_text, c_left, c_top, c_width, c_height))
        if chars:
            has_chars = True

        probability_average: Optional[float] = None
        probability = row.get("probability")
        if isinstance(probability, dict):
            average = probability.get("average")
            if isinstance(average, (int, float)):
                probability_average = float(average)

        lines.append(BaiduOcrLine(text, left, top, width, height, tuple(chars), probability_average))

    log_id = payload.get("log_id")
    if not isinstance(log_id, int):
        log_id = None

    return BaiduOcrResult(
        lines=tuple(lines),
        direction=direction,
        log_id=log_id,
        granularity="char" if has_chars else "line",
    )


# transport: (endpoint, headers, form, timeout_sec) -> (http_status, parsed_json_or_text)
Transport = Callable[[str, Dict[str, str], Dict[str, str], float], Tuple[Optional[int], Any]]


def _httpx_transport(endpoint: str, headers: Dict[str, str], form: Dict[str, str], timeout_sec: float) -> Tuple[Optional[int], Any]:
    with httpx.Client(timeout=timeout_sec) as client:
        response = client.post(endpoint, data=form, headers=headers)
    try:
        return response.status_code, response.json()
    except ValueError as exc:
        raise BaiduOcrError(
            "bad_payload",
            f"baidu ocr returned non-JSON body (http {response.status_code})",
            "protocol",
            False,
        ) from exc


def signed_ocr_headers(config, headers, *, timestamp=None):
    """BCE v1 AK/SK signing; credentials never enter the URL or public snapshot."""
    url = urlsplit(config.endpoint)
    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {**headers, "Host": url.netloc, "x-bce-date": timestamp}
    signed = {key.lower(): value.strip() for key, value in result.items() if key.lower() in ("host", "x-bce-date", "content-type")}
    canonical_headers = "\n".join(sorted(quote(k, safe="") + ":" + quote(v, safe="") for k, v in signed.items()))
    query = "&".join(sorted(quote(k, safe="") + "=" + quote(v, safe="") for k, v in parse_qsl(url.query, keep_blank_values=True) if k.lower() != "authorization"))
    canonical = "\n".join(("POST", quote(url.path or "/", safe="/"), query, canonical_headers))
    prefix = f"bce-auth-v1/{config.api_key}/{timestamp}/1800"
    signing_key = hmac.new(config.secret_key.encode(), prefix.encode(), hashlib.sha256).hexdigest()
    signature = hmac.new(signing_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    result["Authorization"] = prefix + "/" + ";".join(sorted(signed)) + "/" + signature
    return result


def recognize_text_lines(
    image_bytes: bytes,
    config: BaiduOcrEngineConfig,
    *,
    transport: Optional[Transport] = None,
) -> BaiduOcrResult:
    """提交图像字节并返回规范化识别结果。

    图像大小按官方限制校验(base64 后不超过 8M);超限抛出 category=image
    错误,调用方决定重编码策略并自行记录反变换。不做重试:重试/退避由
    任务层(governor 语义)统一控制。
    """
    if not image_bytes:
        raise BaiduOcrError("empty_image", "image bytes are empty", "image", False)
    # 必须 decode 为 str:httpx 的 data= 里出现 bytes 值会触发 multipart 编码,
    # aip 端点要求 application/x-www-form-urlencoded,收到 multipart 会报
    # image format error(216201)。实测 2026-09-27。
    encoded = base64.b64encode(image_bytes).decode("ascii")
    if len(encoded) > BAIDU_OCR_MAX_BASE64_BYTES:
        raise BaiduOcrError(
            "image_too_large",
            f"base64 size {len(encoded)} exceeds limit {BAIDU_OCR_MAX_BASE64_BYTES}",
            "image",
            False,
        )
    if not config.api_key:
        raise BaiduOcrError("missing_api_key", "baidu ocr api key is not configured", "auth", False)

    form = {
        "image": encoded,
        "language_type": config.language_type,
        "recognize_granularity": config.recognize_granularity,
        "detect_direction": "true" if config.detect_direction else "false",
        "probability": "true" if config.probability else "false",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {config.api_key}",
    }

    if config.secret_key:
        headers = signed_ocr_headers(config, headers)
    active_transport = transport or _httpx_transport
    started = time.monotonic()
    try:
        status, payload = active_transport(config.endpoint, headers, form, config.timeout_sec)
    except httpx.HTTPError as exc:
        # 密钥只在请求头里;异常文本不含密钥,可安全透传类别信息。
        raise BaiduOcrError("network", f"baidu ocr request failed: {type(exc).__name__}", "network", True) from exc
    elapsed = time.monotonic() - started

    if isinstance(payload, dict) and "error_code" in payload:
        raise _error_from_payload(payload, status)
    result = parse_baidu_ocr_response(payload)
    # 覆盖 dataclass 默认值需要重建;字段顺序见定义。
    return BaiduOcrResult(
        lines=result.lines,
        direction=result.direction,
        log_id=result.log_id,
        granularity=result.granularity,
        engine_version=BAIDU_OCR_ENGINE_VERSION,
        request_elapsed_sec=round(elapsed, 4),
    )


def build_ocr_cache_key(
    image_bytes: bytes,
    config: BaiduOcrEngineConfig,
    *,
    roi: Optional[Sequence[int]] = None,
) -> str:
    """计算 OCR 结果缓存键:图像字节哈希 + 引擎/配置版本 + 可选 ROI。

    只换音频不换图时命中同一键;密钥不参与缓存键(相同配置换账号结果一致,
    且避免把凭据派生信息落盘)。
    """
    digest = hashlib.sha256()
    digest.update(b"baidu-ocr-v1\n")
    digest.update(json.dumps(config.public_snapshot(), sort_keys=True, ensure_ascii=False).encode("utf-8"))
    digest.update(b"\n")
    digest.update(hashlib.sha256(image_bytes).digest())
    if roi is not None:
        normalized_roi = [int(v) for v in roi]
        digest.update(b"\nroi=" + json.dumps(normalized_roi).encode("utf-8"))
    return digest.hexdigest()
