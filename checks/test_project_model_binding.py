import json
from types import SimpleNamespace

import pytest

from model_connection_service import ResolvedModelConnection
from project_model_binding_models import ProjectModelBindingUpdate
import project_model_binding_service as service


def connection(name="first", kind="text"):
    return ResolvedModelConnection(name, 1, kind, "openai", name, "https://example.test/v1",
                                   "credential-ref", {}, "active")


@pytest.fixture
def env(tmp_path):
    project = SimpleNamespace(run_dir=str(tmp_path), visual_backend="html")
    settings = {"llm_model": "global-text", "image_model": "global-image",
                "llm_api_key": "secret-text", "image_api_key": "secret-image"}
    kwargs = {"setting": settings.get, "credential": lambda ref: {"api_key": "private-key"},
              "resolver": lambda ref: connection(ref)}
    return project, settings, kwargs


def update(revision=0, **text):
    return ProjectModelBindingUpdate(expected_revision=revision, text=text or {"mode": "inherit"},
                                     image={"mode": "inherit"})


def test_two_projects_fixed_vs_global_and_frozen_task(env, tmp_path):
    project, settings, kwargs = env
    second = SimpleNamespace(run_dir=str(tmp_path / "second"))
    service.save_project_model_binding(project, update(mode="fixed", connection_id="first"), binder=connection)
    service.save_project_model_binding(second, update(mode="fixed", connection_id="second"), binder=connection)
    task = service.freeze_project_models(project, **kwargs)
    settings.update(llm_model="changed", image_api_key="new-key")
    assert task.text.model == "first"
    assert task.image.api_key == "secret-image"
    assert service.freeze_project_models(second, **kwargs).text.model == "second"
    assert service.freeze_project_models(project, **kwargs).image.api_key == "new-key"
    assert "private-key" not in repr(task)
    public = json.dumps(service.get_project_model_binding(project, **kwargs))
    assert "private-key" not in public and "credential-ref" not in public and "example.test" not in public
    assert "private-key" not in service._path(project).read_text()


def test_noop_rebind_and_conflict(env):
    project, _, kwargs = env
    request = update(mode="fixed", connection_id="first")
    assert service.save_project_model_binding(project, request, binder=connection)["changed"]
    before = service._path(project).read_bytes()
    no_resolve = lambda ref: pytest.fail("no-op must not resolve current connection")
    assert not service.save_project_model_binding(project, update(1, mode="fixed", connection_id="first"), binder=no_resolve)["changed"]
    assert service._path(project).read_bytes() == before
    with pytest.raises(service.ModelBindingConflict):
        service.save_project_model_binding(project, request, binder=connection)
    newer = lambda ref: connection("new-model")
    service.save_project_model_binding(project, update(1, mode="fixed", connection_id="first", rebind=True), binder=newer)
    assert service.freeze_project_models(project, **kwargs).text.model == "new-model"


def test_old_package_and_explicit_global(env, monkeypatch):
    project, _, kwargs = env
    monkeypatch.setattr(service, "get_config_value", lambda p, key: {"connection_id": "package"} if key.endswith("storyboard") else None)
    assert service.freeze_project_models(project, **kwargs).text.source == "creation_config"
    service.save_project_model_binding(project, update())
    assert service.freeze_project_models(project, **kwargs).text.source == "global"


def test_missing_optional_image_does_not_block_text(env):
    project, settings, kwargs = env
    settings.pop("image_model")
    task = service.freeze_project_models(project, **kwargs)
    with pytest.raises(service.ModelBindingError, match="图片"):
        task.image.require_ready()


def test_no_credential_fallback_or_error_leak(env):
    project, _, kwargs = env
    service.save_project_model_binding(project, update(mode="fixed", connection_id="first"), binder=connection)
    def broken(ref):
        raise RuntimeError("private-key")
    kwargs["credential"] = broken
    with pytest.raises(service.ModelBindingError) as exc:
        service.freeze_project_models(project, **kwargs)
    assert "private-key" not in str(exc.value)


def test_corrupt_file_fails_closed(env):
    project, _, kwargs = env
    service._path(project).parent.mkdir(parents=True)
    service._path(project).write_text('{"schema_version":"unknown"}')
    with pytest.raises(service.ModelBindingError, match="损坏"):
        service.freeze_project_models(project, **kwargs)


def test_kind_mismatch_and_inline_secret_rejected(env):
    project, _, _ = env
    with pytest.raises(service.ModelBindingError):
        service.save_project_model_binding(project, update(mode="fixed", connection_id="wrong"), binder=lambda ref: connection(kind="image"))
    with pytest.raises(ValueError):
        update(mode="fixed", connection_id="a", api_key="never-accepted")


def test_image_adapter_uses_frozen_credentials_and_attachments(env, monkeypatch, tmp_path):
    import ai_provider_service as provider
    import html_image_provider
    project, settings, kwargs = env
    task = service.freeze_project_models(project, **kwargs)
    settings["image_model"] = "changed"
    calls = []
    class Images:
        def edit(self, **params):
            calls.append(params)
            assert params["image"][0].read() == b"reference"
            return "response"
    client = SimpleNamespace(images=Images(), close=lambda: calls.append("closed"))
    def get_client(**options):
        assert options["api_key"] == "secret-image"
        return client
    monkeypatch.setattr(provider, "get_openai_client", get_client)
    monkeypatch.setattr(provider, "is_toapis_image_provider", lambda *args: False)
    monkeypatch.setattr(provider, "_governed_image_request", lambda base, call: call())
    monkeypatch.setattr(provider, "extract_image_bytes_from_response", lambda response: b"image")
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"reference")
    assert html_image_provider.configured_image("test", reference_paths=[ref], model_binding=task.image) == b"image"
    assert calls[0]["model"] == "global-image"
    assert calls[-1] == "closed"


def test_concurrent_saves_have_one_winner(env):
    from concurrent.futures import ThreadPoolExecutor
    project, _, _ = env
    def save(name):
        try:
            service.save_project_model_binding(project, update(mode="fixed", connection_id=name), binder=connection)
            return "saved"
        except service.ModelBindingConflict:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(save, ["one", "two"])) == ["conflict", "saved"]


def test_http_routes_use_account_gate_and_preserve_conflict(env, monkeypatch):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from database import get_db
    import project_model_binding_routes as routes
    project, _, kwargs = env
    def access(db, project_id):
        if project_id != "allowed":
            raise HTTPException(404, "项目不存在")
        return project
    monkeypatch.setattr(routes, "project_or_404", access)
    monkeypatch.setattr(routes, "get_project_model_binding", lambda p: service.get_project_model_binding(p, **kwargs))
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_db] = lambda: None
    with TestClient(app) as client:
        assert client.get("/api/projects/other/model-binding").status_code == 404
        assert client.get("/api/projects/allowed/model-binding").json()["revision"] == 0
        data = update().model_dump()
        assert client.put("/api/projects/allowed/model-binding", json=data).status_code == 200
        assert client.put("/api/projects/allowed/model-binding", json=data).status_code == 409
        project.visual_backend = "image"
        assert client.get("/api/projects/allowed/model-binding").status_code == 400


def test_provider_initialization_error_is_redacted(env, monkeypatch):
    import ai_provider_service as provider
    from html_image_provider import configured_image
    project, _, kwargs = env
    task = service.freeze_project_models(project, **kwargs)
    monkeypatch.setattr(provider, "is_toapis_image_provider", lambda *args: False)
    def fail(**kwargs):
        raise RuntimeError("private-key secret-image")
    monkeypatch.setattr(provider, "get_openai_client", fail)
    with pytest.raises(ValueError) as exc:
        configured_image("prompt", model_binding=task.image)
    assert "private-key" not in str(exc.value) and "secret-image" not in str(exc.value)


def test_save_preserves_approved_work_and_legacy_noop(env, tmp_path):
    project, _, _ = env
    approved = tmp_path / "approval.json"
    audio = tmp_path / "confirmed.wav"
    approved.write_bytes(b"approved")
    audio.write_bytes(b"audio")
    legacy = ProjectModelBindingUpdate(expected_revision=0, text={"mode": "legacy"}, image={"mode": "legacy"})
    assert not service.save_project_model_binding(project, legacy)["changed"]
    assert not service._path(project).exists()
    service.save_project_model_binding(project, update())
    assert approved.read_bytes() == b"approved" and audio.read_bytes() == b"audio"
