from contextlib import nullcontext
import json
from types import SimpleNamespace as NS

import pytest

from json_llm_transport import receive_completion
import json_llm_service as service


class Stream:
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def __iter__(self):
        return iter(self.chunks)


def chunk(text="", *, reasoning="", finish=None):
    return NS(choices=[NS(index=0, delta=NS(content=text, reasoning_content=reasoning),
                          finish_reason=finish)], usage=None)


def client_for(chunks, calls):
    stream = Stream(chunks)
    def create(**kwargs):
        calls.append(kwargs)
        return stream
    return NS(chat=NS(completions=NS(create=create)), close=lambda: None), stream


def test_aggregates_only_content_and_keeps_reasoning_private(tmp_path):
    calls, progress = [], []
    client, stream = client_for([chunk(reasoning="private reasoning"), chunk('{"ok":'),
                                 chunk('true}', finish="stop")], calls)
    path = tmp_path / "transport.json"
    result = receive_completion(client, {"model": "test"}, streaming=True,
                                evidence_path=path, progress=progress.append)
    assert result.choices[0].message.content == '{"ok":true}' and stream.closed
    assert calls[0]["stream"] and calls[0]["stream_options"]["include_usage"]
    record = json.loads(path.read_text())
    assert record["state"] == "completed" and record["reasoning_chars"] == 17
    assert "private reasoning" not in path.read_text() + str(progress)


def test_stream_headers_id_and_safe_usage_are_available_without_raw_headers(tmp_path):
    client, stream = client_for([NS(choices=[NS(index=0, delta=NS(content='{}', reasoning_content=''), finish_reason='stop')],
                                    usage=NS(model_dump=lambda: {'total_tokens': 12, 'secret': 'opaque'}))], [])
    stream.response = NS(headers={'x-request-id': 'request_123', 'authorization': 'secret'})
    events = []
    result = receive_completion(client, {}, streaming=True, evidence_path=tmp_path / 'trace.json', progress=events.append)
    assert result.usage.model_dump()['total_tokens'] == 12
    assert events[-1]['request_id'] == 'request_123' and events[-1]['headers_seconds'] is not None
    assert 'secret' not in (tmp_path / 'trace.json').read_text() + str(events)


@pytest.mark.parametrize("finish", [None, "length", "content_filter"])
def test_partial_stream_never_enters_json_repair(tmp_path, monkeypatch, finish):
    calls = []
    client, stream = client_for([chunk('{"ok":true}', finish=finish)], calls)
    monkeypatch.setattr(service, "get_openai_client", lambda **_kw: client)
    monkeypatch.setattr(service, "get_setting", lambda key, default=None: {
        "llm_api_key": "fake", "llm_model": "glm-5.3"}.get(key, default))
    monkeypatch.setattr(service, "governed_llm_request", lambda *_args: nullcontext())
    monkeypatch.setattr(service, "parse_json_or_repair_with_llm", lambda **_kw: pytest.fail("partial output parsed"))
    with pytest.raises(service.HTTPException):
        service.generate_json_with_configured_llm(system_prompt="s", user_prompt="u",
            run_dir=str(tmp_path), artifact_prefix="partial", schema_hint="{}", stream_output=True)
    assert len(calls) == 1 and stream.closed
    evidence = json.loads((tmp_path / "logs/partial-stream-1.json").read_text())
    assert evidence["failure_reason"] == ("output_limit" if finish == "length" else "incomplete_response")


def test_stream_wall_budget_and_error_metadata(tmp_path, monkeypatch):
    import json_llm_transport as transport
    clock = {"now": 0}
    monkeypatch.setattr(transport.time, "monotonic", lambda: clock["now"])
    def chunks():
        clock["now"] = 2
        yield chunk(reasoning="hidden")
        clock["now"] = 11
        yield chunk("late", finish="stop")
    client, stream = client_for(chunks(), [])
    path = tmp_path / "timeout.json"
    with pytest.raises(TimeoutError):
        receive_completion(client, {}, streaming=True, timeout=10, evidence_path=path)
    report = json.loads(path.read_text())
    assert report["error_class"] == "TimeoutError" and report["state"] == "failed"
    assert stream.closed and report["content_chars"] == 0
    assert report["failure_reason"] == "total_timeout"


def test_stream_repair_preserves_frozen_options(tmp_path, monkeypatch):
    captured = []
    def create(**kwargs):
        captured.append(kwargs)
        return Stream([chunk('{"ok":' if len(captured) == 1 else '{"ok":true}', finish="stop")])
    client = NS(chat=NS(completions=NS(create=create)), close=lambda: None)
    monkeypatch.setattr(service, "get_openai_client", lambda **_kw: client)
    monkeypatch.setattr(service, "governed_llm_request", lambda *_args: nullcontext())
    binding = NS(api_key="fake", endpoint="https://example.test/v4", model="glm-5.3",
                 max_tokens=65536, temperature=1.0, reasoning_effort="max")
    assert service.generate_json_with_configured_llm(model_binding=binding, system_prompt="s",
        user_prompt="u", run_dir=str(tmp_path), artifact_prefix="repair", schema_hint="{}",
        stream_output=True) == {"ok": True}
    assert len(captured) == 2
    assert all(c["stream"] and c["max_tokens"] == 65536 and c["reasoning_effort"] == "max"
               and c["extra_body"]["thinking"]["type"] == "enabled" for c in captured)


def test_explicit_scene_planning_effort_override_is_scoped_and_audited(tmp_path, monkeypatch):
    captured = []
    client, _stream = client_for([chunk('{"ok":true}', finish="stop")], captured)
    monkeypatch.setattr(service, "get_openai_client", lambda **_kw: client)
    monkeypatch.setattr(service, "governed_llm_request", lambda *_args: nullcontext())
    binding = NS(api_key="fake", endpoint="https://example.test/v4", model="glm-5.3",
                 max_tokens=65536, temperature=1.0, reasoning_effort="max")
    result = service.generate_json_with_configured_llm(
        model_binding=binding, system_prompt="s", user_prompt="u", run_dir=str(tmp_path),
        artifact_prefix="scene-plan", schema_hint="{}", stream_output=True,
        reasoning_effort_override="low",
    )
    assert result == {"ok": True}
    assert len(captured) == 1
    assert captured[0]["reasoning_effort"] == "low"
    assert captured[0]["max_tokens"] == 65536
    assert captured[0]["extra_body"]["thinking"]["type"] == "enabled"
    assert binding.reasoning_effort == "max"
    evidence = json.loads((tmp_path / "logs/scene-plan-stream-1.json").read_text())
    assert evidence["reasoning_effort"] == "low"


def test_read_silence_is_distinct_from_total_budget_and_never_retries(tmp_path, monkeypatch):
    import httpx
    import json_llm_transport as transport
    clock = {"now": 0}
    monkeypatch.setattr(transport.time, "monotonic", lambda: clock["now"])
    def chunks():
        clock["now"] = 156
        yield chunk(reasoning="private")
        clock["now"] = 281
        raise httpx.ReadTimeout("secret provider endpoint")
    calls, events = [], []
    client, stream = client_for(chunks(), calls)
    path = tmp_path / "read-timeout.json"
    with pytest.raises(httpx.ReadTimeout):
        receive_completion(client, {}, streaming=True, timeout=1800, read_timeout=120,
                           evidence_path=path, progress=events.append)
    report = json.loads(path.read_text())
    assert report["failure_reason"] == "read_timeout" and report["last_chunk_seconds"] == 156
    assert report["silence_seconds"] == 125 and report["total_timeout_seconds"] == 1800
    assert events[-1]["read_timeout_seconds"] == 120 and events[-1]["failure_reason"] == "read_timeout"
    assert len(calls) == 1 and stream.closed and report["content_chars"] == 0
    assert "secret provider endpoint" not in path.read_text() + str(events)


def test_provider_error_classification_does_not_treat_all_timeouts_as_read_timeouts():
    from json_llm_transport import failure_reason
    import httpx
    assert failure_reason(httpx.ConnectTimeout("private")) == "transport_error"
    assert failure_reason(ValueError("JSON_STREAM_INCOMPLETE")) == "incomplete_response"
    assert failure_reason(ValueError("JSON_STREAM_OUTPUT_LIMIT")) == "output_limit"


def test_output_limit_reports_only_safe_usage_and_final_reason(tmp_path):
    events = []
    usage = NS(model_dump=lambda: {"prompt_tokens": 4516, "completion_tokens": 64000,
        "total_tokens": 68516, "completion_tokens_details": {"reasoning_tokens": 62196,
        "provider_private_field": "secret"}, "provider_private_field": "secret"})
    terminal = NS(choices=[NS(index=0, delta=NS(content="", reasoning_content=""),
                              finish_reason="length")], usage=usage)
    client, _ = client_for([chunk('{"partial":'), terminal], [])
    with pytest.raises(ValueError, match="JSON_STREAM_OUTPUT_LIMIT"):
        receive_completion(client, {}, streaming=True, evidence_path=tmp_path / "stream.json",
                           progress=events.append)
    final = events[-1]
    assert final["failure_reason"] == "output_limit" and final["finish_reason"] == "length"
    assert final["usage"]["completion_tokens_details"]["reasoning_tokens"] == 62196
    assert "secret" not in str(final) + (tmp_path / "stream.json").read_text()
