from types import SimpleNamespace
import pytest
import json_llm_service as service

@pytest.mark.parametrize("fails", [False, True])
def test_scoped_budget_and_client_cleanup(monkeypatch, tmp_path, fails):
    calls = []
    closed = []
    def create(**kwargs):
        calls.append(kwargs)
        if fails:
            raise TimeoutError("timed out")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"suggestions":[]}'))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=lambda: closed.append(True))
    from contextlib import nullcontext
    monkeypatch.setattr(service, "get_setting", lambda key, default=None: {"llm_api_key":"test", "llm_model":"test", "llm_max_tokens":"64000"}.get(key,default))
    def factory(**kwargs):
        assert kwargs["timeout"] == 180
        return client
    monkeypatch.setattr(service, "get_openai_client", factory)
    monkeypatch.setattr(service, "governed_llm_request", lambda *_a: nullcontext())
    arguments = dict(system_prompt="system",user_prompt="input",run_dir=str(tmp_path),artifact_prefix="annotation",schema_hint="{}",request_timeout=180,max_tokens_limit=4096)
    if fails:
        with pytest.raises(service.HTTPException): service.generate_json_with_configured_llm(**arguments)
    else:
        assert service.generate_json_with_configured_llm(**arguments) == {"suggestions":[]}
    assert calls[0]["max_tokens"] == 4096
    assert closed == [True]
