from contextlib import nullcontext
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from html_json_observer import observe_json_requests
import json_llm_service as llm
from project_model_binding_service import freeze_project_models


@pytest.mark.parametrize('failure',['format','invalid_json'])
def test_original_fallback_and_json_repair_each_count_real_http(tmp_path,monkeypatch,failure):
    binding=freeze_project_models(SimpleNamespace(run_dir=str(tmp_path)),setting={'llm_model':'model','llm_api_key':'fake'}.get).text
    calls=[];events=[]
    def create(**kwargs):
        calls.append(kwargs)
        if failure=='format' and len(calls)==1:raise ValueError('response_format is not supported')
        content='{"ok":' if failure=='invalid_json' and len(calls)==1 else '{"ok":true}'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],usage=None)
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)),close=lambda:None)
    monkeypatch.setattr(llm,'get_openai_client',lambda **kw:client)
    monkeypatch.setattr(llm,'governed_llm_request',lambda *a:nullcontext())
    with observe_json_requests(lambda state,**facts:events.append((state,facts))):
        result=llm.generate_json_with_configured_llm(model_binding=binding,system_prompt='s',user_prompt='u',
            run_dir=str(tmp_path),artifact_prefix='observer',schema_hint='{}')
    assert result=={'ok':True} and len(calls)==2
    assert sum(state=='intent' for state,_ in events)==2
    if failure=='format':assert any(state=='rejected' for state,_ in events)
    assert all('api_key' not in facts and 'messages' not in facts for _,facts in events)


def test_http_budget_callback_fences_original_json_repair_and_is_task_local(tmp_path,monkeypatch):
    binding=freeze_project_models(SimpleNamespace(run_dir=str(tmp_path)),setting={'llm_model':'model','llm_api_key':'fake'}.get).text
    calls=[];count=[0]
    def create(**kw):
        calls.append(kw);return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":'))])
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)),close=lambda:None)
    monkeypatch.setattr(llm,'get_openai_client',lambda **kw:client)
    monkeypatch.setattr(llm,'governed_llm_request',lambda *a:nullcontext())
    def guard(state,**facts):
        if state=='intent':
            if count[0]>=1:raise ValueError('HTTP_LIMIT')
            count[0]+=1
    with observe_json_requests(guard),pytest.raises(HTTPException):
        llm.generate_json_with_configured_llm(model_binding=binding,system_prompt='s',user_prompt='u',run_dir=str(tmp_path),
            artifact_prefix='budget',schema_hint='{}')
    assert len(calls)==1
    from json_llm_transport import receive_completion
    receive_completion(client,{})
    assert len(calls)==2  # Observer context did not leak to an unrelated call.
