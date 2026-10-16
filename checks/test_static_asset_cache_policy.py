"""API namespace matching must not exclude api_client.js from UI cache policy."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app_middleware import install_static_asset_cache_policy


@pytest.mark.parametrize("path,disabled", [
    ("/", True), ("/api_client.js", True), ("/storyboard.js", True),
    ("/stitch.css", True), ("/api", False), ("/api/projects", False),
])
def test_static_paths_and_exact_api_namespace(path, disabled):
    app = FastAPI()
    install_static_asset_cache_policy(app)

    @app.get("/{rest:path}")
    def read(rest):
        return {"ok": True}

    response = TestClient(app).get(path)
    assert ("no-store" in response.headers.get("cache-control", "")) is disabled
