"""Configured image transport for HTML references/assets; no slide whitening.

Atlas/reference attachments are sent as actual images, not only filenames.
"""

from pathlib import Path
from contextlib import ExitStack


def configured_image(
    prompt, *, size="1024x1024", reference_paths=None, transparent_background=True,
    model_binding=None,
    resume_task_id="", on_task_submitted=None,
):
    if model_binding is not None:
        model_binding.require_ready()
    try:
        return _configured_image(
            prompt, size=size, reference_paths=reference_paths,
            transparent_background=transparent_background, model_binding=model_binding,
            resume_task_id=resume_task_id, on_task_submitted=on_task_submitted,
        )
    except Exception:
        # SDK initialization, request and close errors can contain auth headers.
        raise ValueError("图片服务请求失败，请检查模型连接、限流状态或稍后重试。") from None


def _configured_image(
    prompt, *, size="1024x1024", reference_paths=None, transparent_background=True,
    model_binding=None,
    resume_task_id="", on_task_submitted=None,
):
    from config_store import get_setting
    from ai_provider_service import (
        get_openai_client,
        is_toapis_image_provider,
        generate_image_response,
        extract_image_bytes_from_response,
        _governed_image_request,
    )

    if model_binding is not None:
        model_binding.require_ready()
        key = model_binding.api_key
        base = model_binding.endpoint
        model = model_binding.model
        provider = model_binding.provider
    else:
        key = get_setting("image_api_key")
        base = get_setting("image_base_url")
        model = get_setting("image_model")
        provider = get_setting("image_provider")
    if not key or not model:
        raise ValueError("未配置图片服务，请先在系统设置中配置。")
    references = [str(Path(p)) for p in reference_paths or []]
    if is_toapis_image_provider(provider, base):
        response = generate_image_response(
            None,
            model,
            prompt,
            size,
            base_url=base,
            api_key=key,
            provider=provider,
            reference_paths=references,
            transparent_background=transparent_background,
            public_config={"toapis_resolution": "2k", "toapis_quality": "low"},
            **({"resume_task_id": resume_task_id, "timeout": 30} if resume_task_id else {}),
            **({"on_task_submitted": on_task_submitted} if on_task_submitted is not None else {}),
        )
        return extract_image_bytes_from_response(response)
    if resume_task_id:
        raise ValueError("当前图片供应商不支持按任务 ID 对账，禁止重新提交。")
    client = get_openai_client(api_key=key, base_url=base, timeout=120)
    try:
        with ExitStack() as stack:
            params = {"model": model, "prompt": prompt, "size": size, "n": 1}
            if "gpt-image" in model.lower():
                params["quality"] = "low"
            if "gpt-image-2.5" in model.lower():
                # This OpenAI-compatible model uses provider metadata for 2K;
                # measured response dimensions, not this hint, are evidence.
                params["extra_body"] = {"metadata": {"resolution": "2K"}}
            if transparent_background:
                params["background"] = "transparent"
            if references:
                params["image"] = [
                    stack.enter_context(open(p, "rb")) for p in references
                ]
                response = _governed_image_request(
                    base, lambda: client.images.edit(**params)
                )
            else:
                response = _governed_image_request(
                    base, lambda: client.images.generate(**params)
                )
            return extract_image_bytes_from_response(response)
    finally:
        client.close()


configured_image.supports_upstream_task = True


def lookup_toapis_result(record, *, model_binding):
    """Resume the paid task only; no reference uploads or image POST."""
    result = configured_image("", model_binding=model_binding, resume_task_id=record["upstream_task_id"])
    return {"request_id": record["request_id"], "state": "succeeded", "result": result}
