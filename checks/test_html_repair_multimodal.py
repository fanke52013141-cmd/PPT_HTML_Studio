from types import SimpleNamespace
from contextlib import nullcontext
import base64
import pytest
from PIL import Image
from fastapi import HTTPException
import json_llm_service as service


@pytest.fixture
def client(monkeypatch):
    calls = []

    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))]
        )

    fake = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        close=lambda: None,
    )
    monkeypatch.setattr(
        service,
        "get_setting",
        lambda key, default="": {
            "llm_api_key": "test-only",
            "llm_model": "test-model",
            "llm_base_url": "https://example.invalid",
        }.get(key, default),
    )
    monkeypatch.setattr(service, "get_openai_client", lambda **kw: fake)
    monkeypatch.setattr(
        service, "governed_llm_request", lambda *args, **kw: nullcontext()
    )
    return calls


def request(run, paths=None):
    return service.generate_json_with_configured_llm(
        system_prompt="s",
        user_prompt="u",
        run_dir=str(run),
        artifact_prefix="isolated",
        schema_hint="{}",
        image_paths=paths,
    )


def test_actual_png_payload_and_text_backward_compatibility(tmp_path, client):
    p = tmp_path / "frame.png"
    Image.new("RGB", (10, 10), "white").save(p)
    assert request(tmp_path, [str(p)]) == {"ok": True}
    parts = client[-1]["messages"][1]["content"]
    assert parts[0] == {"type": "text", "text": "u"}
    assert (
        base64.b64decode(parts[1]["image_url"]["url"].split(",", 1)[1])
        == p.read_bytes()
    )
    request(tmp_path)
    assert client[-1]["messages"][1]["content"] == "u"


def test_attachment_escape_and_budget_rejected(tmp_path, client):
    inside = tmp_path / "run"
    inside.mkdir()
    p = tmp_path / "outside.png"
    Image.new("RGB", (10, 10), "white").save(p)
    with pytest.raises(HTTPException):
        request(inside, [str(p)])
    with pytest.raises(HTTPException):
        request(tmp_path, [str(p)] * 5)
    assert client == []
