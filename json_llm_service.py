"""Shared configured JSON generation and one-shot LLM repair.

治理约定
--------
每次 ``chat.completions.create`` 都是一次真实上游请求，必须单独通过
:gfunc:`llm_concurrency.governed_llm_request` 申请额度（项目槽 + 网关全局），
请求结束即释放。格式回退与 JSON 修复是**独立的请求**，各自计量；
只有明确的参数/格式不兼容错误才去掉 ``response_format`` 重试。
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
import time
from typing import Any, Dict

from fastapi import HTTPException
from openai import OpenAI

from ai_provider_service import get_openai_client
from config_store import get_setting
from llm_concurrency import governed_llm_request, is_llm_format_incompatibility
from runtime_support import (
    clean_json_markdown,
    json_decode_context,
    parse_int_setting,
    write_debug_text,
)


logger = logging.getLogger("PPTStudio.JsonLlm")


def _request_options(model, binding=None, *, reasoning_effort_override=None):
    options = {}
    if model in {"glm-5.3", "glm-5.3-flash", "glm-5.3-flashx"}:
        if (reasoning_effort_override is not None
                and reasoning_effort_override not in {"low", "high", "max"}):
            raise ValueError("reasoning_effort_override must be low, high, or max")
        options = {"extra_body": {"thinking": {"type": "enabled"}},
                   "reasoning_effort": reasoning_effort_override
                   or getattr(binding, "reasoning_effort", None) or "max"}
    return options


def parse_json_or_repair_with_llm(
    *,
    cleaned_content: str,
    raw_content: str,
    client: OpenAI,
    model: str,
    run_dir: str,
    artifact_prefix: str,
    schema_hint: str = "",
    max_tokens: int = 16000,
    base_url: str = "",
    request_options: Dict[str, Any] | None = None,
    completion_callback=None,
) -> Dict[str, Any]:
    try:
        value = json.loads(cleaned_content)
    except json.JSONDecodeError as first_error:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = write_debug_text(run_dir, f"{artifact_prefix}_{timestamp}.raw_failed.txt", raw_content)
        cleaned_path = write_debug_text(run_dir, f"{artifact_prefix}_{timestamp}.cleaned_failed.json", cleaned_content)
        context = json_decode_context(cleaned_content, first_error)
        logger.warning(
            "Invalid JSON from LLM for %s: %s. Raw saved to %s, cleaned saved to %s. Context near error: %r",
            artifact_prefix,
            first_error,
            raw_path,
            cleaned_path,
            context,
        )

        repair_prompt = (
            "You repair invalid JSON emitted by another model. "
            "Return only one valid JSON object. No markdown, no comments, no explanation. "
            "Fix syntax issues such as missing commas, unescaped quotes, trailing text, "
            "or incomplete brackets while preserving the original Chinese content and structure."
        )
        repair_user = (
            f"JSON parser error: {first_error}\n\n"
            f"Schema hint:\n{schema_hint[:12000]}\n\n"
            f"Invalid JSON to repair:\n{cleaned_content[:120000]}"
        )

        try:
            try:
                with governed_llm_request(base_url):
                    repair_response = (completion_callback or client.chat.completions.create)(
                        model=model,
                        **(request_options or _request_options(model)),
                        temperature=1.0 if model.startswith("glm-5.3") else 0,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": repair_prompt},
                            {"role": "user", "content": repair_user},
                        ],
                    )
            except Exception as repair_format_error:
                if not is_llm_format_incompatibility(repair_format_error):
                    raise
                logger.warning(
                    "LLM JSON repair with response_format failed for %s, retrying without it: %s",
                    artifact_prefix,
                    type(repair_format_error).__name__,
                )
                with governed_llm_request(base_url):
                    repair_response = (completion_callback or client.chat.completions.create)(
                        model=model,
                        **(request_options or _request_options(model)),
                        temperature=1.0 if model.startswith("glm-5.3") else 0,
                        max_tokens=max_tokens,
                        messages=[
                            {"role": "system", "content": repair_prompt},
                            {"role": "user", "content": repair_user},
                        ],
                    )
        except Exception as repair_error:
            logger.error("LLM JSON repair request failed for %s: %s", artifact_prefix, type(repair_error).__name__)
            raise first_error from repair_error

        repaired_raw = repair_response.choices[0].message.content.strip()
        repaired_cleaned = clean_json_markdown(repaired_raw)
        write_debug_text(run_dir, f"{artifact_prefix}_{timestamp}.repaired_raw.txt", repaired_raw)
        try:
            value = json.loads(repaired_cleaned)
        except json.JSONDecodeError as repair_parse_error:
            repaired_path = write_debug_text(
                run_dir,
                f"{artifact_prefix}_{timestamp}.repaired_failed.json",
                repaired_cleaned,
            )
            logger.error(
                "LLM JSON repair still invalid for %s: %s. Repaired content saved to %s. Context near error: %r",
                artifact_prefix,
                repair_parse_error,
                repaired_path,
                json_decode_context(repaired_cleaned, repair_parse_error),
            )
            raise first_error from repair_parse_error

    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def generate_json_with_configured_llm(**kwargs) -> Dict[str, Any]:
    binding = kwargs.get("model_binding")
    if binding is not None and hasattr(binding, "require_ready"):
        binding.require_ready()
    try:
        return _generate_json_with_configured_llm(**kwargs)
    except Exception:
        if binding is None:
            raise
        raise HTTPException(status_code=500, detail="AI 生成失败，请检查模型连接或稍后重试。") from None


def _generate_json_with_configured_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    run_dir: str,
    artifact_prefix: str,
    schema_hint: str,
    temperature: float = 0.35,
    max_tokens_default: int = 12000,
    model_binding: Any = None,
    request_timeout: float = 120.0,
    max_tokens_limit: int | None = None,
    image_paths: list[str] | None = None,
    stream_output: bool = False,
    on_stream_progress=None,
    reasoning_effort_override: str | None = None,
) -> Dict[str, Any]:
    llm_api_key = getattr(model_binding, "api_key", None) if model_binding is not None else get_setting("llm_api_key")
    llm_base_url = getattr(model_binding, "endpoint", None) if model_binding is not None else get_setting("llm_base_url")
    llm_model = getattr(model_binding, "model", None) if model_binding is not None else get_setting("llm_model")
    if not llm_api_key:
        raise HTTPException(status_code=400, detail="未配置大模型 API 密钥，请在系统设置中配置后再试。")
    if not llm_model:
        raise HTTPException(status_code=400, detail="未配置大模型名称，请在系统设置中配置后再试。")
    request_options = _request_options(llm_model, model_binding,
                                       reasoning_effort_override=reasoning_effort_override)
    max_tokens = parse_int_setting(
        getattr(model_binding, "max_tokens", None) if getattr(model_binding, "max_tokens", None) is not None
        else get_setting("llm_max_tokens", str(max_tokens_default)),
        max_tokens_default,
        1024,
        65536,
    )
    if max_tokens_limit is not None:
        max_tokens = min(max_tokens, max(1024, int(max_tokens_limit)))
    if getattr(model_binding, "temperature", None) is not None:
        temperature = model_binding.temperature
    user_content = user_prompt
    if image_paths:
        if llm_model == "glm-5.3" or getattr(model_binding, "supports_images", None) is False:
            raise HTTPException(400, "此模型只支持文字输入，请选择多模态模型")
        import base64
        from pathlib import Path
        from PIL import Image
        import io
        if len(image_paths) > 4:
            raise HTTPException(400, "一次修复最多4张截图")
        root = Path(run_dir).resolve()
        parts = [{"type":"text", "text":user_prompt}]
        for name in image_paths:
            path = Path(name).resolve()
            if not path.is_relative_to(root) or path.suffix.lower() != ".png" or path.stat().st_size > 8*1024*1024:
                raise HTTPException(400, "截图路径或字节预算不合法")
            data = path.read_bytes()
            with Image.open(io.BytesIO(data)) as image:
                if image.format != "PNG" or image.width*image.height > 4_000_000:
                    raise HTTPException(400, "截图格式或像素预算不合法")
                image.verify()
            parts.append({"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(data).decode("ascii")}})
        user_content = parts
    if llm_model.startswith("glm-5.3") and request_timeout == 120.0:
        request_timeout = 600.0
    client = get_openai_client(api_key=llm_api_key, base_url=llm_base_url,
                               timeout=min(request_timeout, 120) if stream_output else request_timeout)
    from pathlib import Path
    from json_llm_transport import receive_completion
    calls = 0
    def complete(**params):
        nonlocal calls
        calls += 1
        return receive_completion(client, params, streaming=stream_output, timeout=request_timeout,
            read_timeout=min(request_timeout, 120) if stream_output else request_timeout,
            evidence_path=Path(run_dir) / "logs" / f"{artifact_prefix}-stream-{calls}.json",
            progress=on_stream_progress)
    started = time.monotonic()
    logger.info("JSON task %s: model=%s input_chars=%s max_tokens=%s reasoning_effort=%s timeout=%ss",
                artifact_prefix, llm_model, len(system_prompt) + len(user_prompt), max_tokens,
                request_options.get("reasoning_effort", "provider_default"), request_timeout)
    try:
        try:
            try:
                with governed_llm_request(llm_base_url):
                    response = complete(
                        model=llm_model,
                        **request_options,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                    )
            except Exception as format_error:
                if not is_llm_format_incompatibility(format_error):
                    raise
                logger.warning(
                    "AI JSON generation with response_format failed for %s, retrying without it: %s",
                    artifact_prefix,
                    type(format_error).__name__,
                )
                with governed_llm_request(llm_base_url):
                    response = complete(
                        model=llm_model,
                        **request_options,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        messages=[
                            {"role": "system", "content": system_prompt + "\n只输出纯 JSON，不要 Markdown，不要解释。"},
                            {"role": "user", "content": user_content},
                        ],
                    )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"AI 生成失败: {exc}") from exc

        raw_content = response.choices[0].message.content.strip()
        return parse_json_or_repair_with_llm(
            cleaned_content=clean_json_markdown(raw_content),
            raw_content=raw_content,
            client=client,
            model=llm_model,
            run_dir=run_dir,
            artifact_prefix=artifact_prefix,
            schema_hint=schema_hint,
            max_tokens=max_tokens,
            base_url=str(llm_base_url or ""),
            request_options=request_options,
            completion_callback=complete,
        )
    finally:
        client.close()
        logger.info("JSON task %s finished after %.1fs", artifact_prefix, time.monotonic() - started)


generate_json_with_configured_llm.supports_stream_progress = True
