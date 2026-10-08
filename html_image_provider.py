"""Configured image transport for HTML references/assets; no slide whitening.

Atlas/reference attachments are sent as actual images, not only filenames.
"""

from pathlib import Path
from contextlib import ExitStack


def configured_image(
    prompt, *, size="1024x1024", reference_paths=None, transparent_background=True,
    model_binding=None,
):
    if model_binding is not None:
        model_binding.require_ready()
    try:
        return _configured_image(
            prompt, size=size, reference_paths=reference_paths,
            transparent_background=transparent_background, model_binding=model_binding,
        )
    except Exception:
        # SDK initialization, request and close errors can contain auth headers.
        raise ValueError("图片服务请求失败，请检查模型连接、限流状态或稍后重试。") from None


def _configured_image(
    prompt, *, size="1024x1024", reference_paths=None, transparent_background=True,
    model_binding=None,
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
        )
        return extract_image_bytes_from_response(response)
    client = get_openai_client(api_key=key, base_url=base, timeout=120)
    try:
        with ExitStack() as stack:
            params = {"model": model, "prompt": prompt, "size": size, "n": 1}
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
