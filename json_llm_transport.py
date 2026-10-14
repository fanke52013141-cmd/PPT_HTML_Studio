"""Bounded JSON stream aggregation; reasoning text never leaves the transport."""
from __future__ import annotations

from types import SimpleNamespace
import time

from pipeline_lifecycle import write_json_atomic

MAX_CONTENT_CHARS = 1_000_000


def receive_completion(client, params, *, streaming=False, timeout=1800,
                       evidence_path=None, progress=None):
    if not streaming:
        return client.chat.completions.create(**params)
    started = time.monotonic()
    content = []
    record = {"stream": True, "first_chunk_seconds": None, "first_content_seconds": None,
              "chunks": 0, "content_chars": 0, "reasoning_chars": 0,
              "finish_reason": None, "usage": None, "state": "waiting",
              "total_timeout_seconds": timeout}
    last_emit = -5.0

    def emit(force=False):
        nonlocal last_emit
        elapsed = time.monotonic() - started
        if not force and elapsed - last_emit < 5:
            return
        last_emit = elapsed
        record["elapsed_seconds"] = round(elapsed, 3)
        if evidence_path is not None:
            write_json_atomic(evidence_path, record)
        if progress:
            progress({k: record[k] for k in ("state", "elapsed_seconds", "content_chars",
                                            "reasoning_chars", "first_chunk_seconds")})

    try:
        emit(True)
        with client.chat.completions.create(**params, stream=True,
                                            stream_options={"include_usage": True}) as stream:
            for chunk in stream:
                elapsed = time.monotonic() - started
                if elapsed > timeout:
                    raise TimeoutError("JSON_STREAM_TOTAL_TIMEOUT")
                record["chunks"] += 1
                if record["first_chunk_seconds"] is None:
                    record["first_chunk_seconds"] = round(elapsed, 3)
                usage = getattr(chunk, "usage", None)
                if usage is not None:
                    record["usage"] = usage.model_dump()
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
        if record["finish_reason"] != "stop" or not content:
            raise ValueError("JSON_STREAM_INCOMPLETE")
        record["state"] = "completed"
        emit(True)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="".join(content)))])
    except Exception as error:
        record.update(state="failed", error_class=type(error).__name__,
                      status_code=getattr(error, "status_code", None))
        emit(True)
        raise
