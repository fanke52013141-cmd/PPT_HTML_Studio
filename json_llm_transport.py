"""Bounded JSON stream aggregation; reasoning text never leaves the transport."""
from __future__ import annotations

from types import SimpleNamespace
import time

from pipeline_lifecycle import write_json_atomic

MAX_CONTENT_CHARS = 1_000_000


def _safe_usage(value):
    """Only provider counters enter task progress; never persist opaque metadata."""
    if value is None:
        return None
    data = value.model_dump() if hasattr(value, "model_dump") else value
    if not isinstance(data, dict):
        return None
    details = data.get("completion_tokens_details") or {}
    return {key: data[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            if type(data.get(key)) is int and data[key] >= 0} | {
        "completion_tokens_details": {"reasoning_tokens": details["reasoning_tokens"]}
        if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int
        and details["reasoning_tokens"] >= 0 else {}
    }


def failure_reason(error):
    """Classify fixed exception types, never persist provider text or payloads."""
    current, seen = error, set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ == "ReadTimeout":
            return "read_timeout"
        current = current.__cause__ or current.__context__
    if isinstance(error, TimeoutError) and str(error) == "JSON_STREAM_TOTAL_TIMEOUT":
        return "total_timeout"
    if isinstance(error, ValueError) and str(error) == "JSON_STREAM_OUTPUT_LIMIT":
        return "output_limit"
    if isinstance(error, ValueError) and str(error) == "JSON_STREAM_INCOMPLETE":
        return "incomplete_response"
    return "transport_error"


def receive_completion(client,params,**kwargs):
    from html_json_observer import notify
    notify('intent')
    try:
        value=_receive_completion(client,params,**kwargs)
    except BaseException as error:
        from llm_concurrency import is_llm_format_incompatibility
        outcome='output_limit' if isinstance(error,ValueError) and str(error)=='JSON_STREAM_OUTPUT_LIMIT' else 'rejected' if is_llm_format_incompatibility(error) else 'unknown'
        notify(outcome,error_class=type(error).__name__)
        raise
    notify('returned',usage=_safe_usage(getattr(value,'usage',None)))
    return value


def _receive_completion(client, params, *, streaming=False, timeout=1800,
                       evidence_path=None, progress=None, read_timeout=None):
    if not streaming:
        return client.chat.completions.create(**params)
    started = time.monotonic()
    content = []
    record = {"stream": True, "first_chunk_seconds": None, "first_content_seconds": None,
              "request_id": None, "headers_seconds": None,
              "chunks": 0, "content_chars": 0, "reasoning_chars": 0,
              "finish_reason": None, "usage": None, "state": "waiting",
              "total_timeout_seconds": timeout, "read_timeout_seconds": read_timeout,
              "last_chunk_seconds": None, "silence_seconds": 0, "failure_reason": None}
    effort = params.get("reasoning_effort")
    record["reasoning_effort"] = effort if effort in {"low", "high", "max"} else None
    last_emit = -5.0

    def emit(force=False):
        nonlocal last_emit
        elapsed = time.monotonic() - started
        if not force and elapsed - last_emit < 5:
            return
        last_emit = elapsed
        record["elapsed_seconds"] = round(elapsed, 3)
        record["silence_seconds"] = round(max(0, elapsed - (record["last_chunk_seconds"] or 0)), 3)
        if evidence_path is not None:
            write_json_atomic(evidence_path, record)
        if progress:
            progress({k: record[k] for k in ("state", "elapsed_seconds", "content_chars",
                                            "reasoning_chars", "first_chunk_seconds", "last_chunk_seconds",
                                            "silence_seconds", "total_timeout_seconds", "read_timeout_seconds",
                                            "reasoning_effort", "failure_reason", "finish_reason", "usage",
                                            "request_id", "headers_seconds")})

    try:
        emit(True)
        with client.chat.completions.create(**params, stream=True,
                                            stream_options={"include_usage": True}) as stream:
            import re
            headers = getattr(getattr(stream, 'response', None), 'headers', {})
            record['headers_seconds'] = round(time.monotonic() - started, 3)
            request_id = headers.get('x-request-id')
            if isinstance(request_id, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,256}', request_id):
                record['request_id'] = request_id
            emit(True)
            for chunk in stream:
                elapsed = time.monotonic() - started
                if elapsed > timeout:
                    raise TimeoutError("JSON_STREAM_TOTAL_TIMEOUT")
                record["chunks"] += 1
                record["last_chunk_seconds"] = round(elapsed, 3)
                if record["first_chunk_seconds"] is None:
                    record["first_chunk_seconds"] = round(elapsed, 3)
                usage = getattr(chunk, "usage", None)
                if usage is not None:
                    record["usage"] = _safe_usage(usage)
                for choice in chunk.choices:
                    if choice.index != 0:
                        raise ValueError("JSON_STREAM_MULTIPLE_CHOICES")
                    delta = choice.delta
                    piece = getattr(delta, "content", None) or ""
                    reasoning = getattr(delta, "reasoning_content", None) or ""
                    record["reasoning_chars"] += len(reasoning)
                    if piece:
                        if record["first_content_seconds"] is None:
                            record["first_content_seconds"] = round(elapsed, 3)
                        content.append(piece)
                        record["content_chars"] += len(piece)
                    if record["content_chars"] > MAX_CONTENT_CHARS:
                        raise ValueError("JSON_STREAM_CONTENT_BUDGET")
                    if choice.finish_reason:
                        record["finish_reason"] = choice.finish_reason
                record["state"] = "outputting" if record["content_chars"] else "thinking"
                emit()
        # Partial/truncated output is never parsed or sent to JSON repair.
        if record["finish_reason"] == "length":
            raise ValueError("JSON_STREAM_OUTPUT_LIMIT")
        if record["finish_reason"] != "stop" or not content:
            raise ValueError("JSON_STREAM_INCOMPLETE")
        record["state"] = "completed"
        emit(True)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="".join(content)))],
                               usage=SimpleNamespace(model_dump=lambda: record['usage']) if record['usage'] else None)
    except Exception as error:
        record.update(state="failed", error_class=type(error).__name__,
                      status_code=getattr(error, "status_code", None), failure_reason=failure_reason(error))
        emit(True)
        raise
