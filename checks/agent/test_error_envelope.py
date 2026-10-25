"""Agent API schema-validation errors use the unified error envelope (P2-10)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from agent_api import register_agent_error_handlers


class _Body(BaseModel):
    name: str


def _make_app() -> FastAPI:
    app = FastAPI()
    register_agent_error_handlers(app)

    @app.post("/api/agent/v1/thing")
    def _agent_thing(body: _Body):
        return {"ok": True}

    @app.post("/api/web/thing")
    def _web_thing(body: _Body):
        return {"ok": True}

    return app


def test_agent_validation_errors_use_error_envelope():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    resp = client.post("/api/agent/v1/thing", json={"name": 123})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"] and body["error"]["details"][0]["loc"][-1] == "name"


def test_non_agent_paths_keep_fastapi_default_shape():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    resp = client.post("/api/web/thing", json={"name": 123})
    assert resp.status_code == 422
    assert "detail" in resp.json()
