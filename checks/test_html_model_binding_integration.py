"""Submit-to-worker configuration freezing through the actual job/store code."""
from contextlib import nullcontext
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import SimpleNamespace
import json
import uuid

import pytest

from database import LocalJob, Project, SessionLocal
from html_visual_review_service import HtmlReviewDependencies
import html_workflow_jobs as jobs_module
import json_llm_service as llm
from project_model_binding_service import freeze_project_models

ROOT = Path(__file__).resolve().parents[1]


class Capture:
    def __init__(self):
        self.calls = []

    def submit(self, *args):
        self.calls.append(args)


def test_submit_change_settings_worker_keeps_old_configuration(tmp_path, monkeypatch):
    from html_image_provider import configured_image
    import ai_provider_service as image_service
    settings = {"llm_model": "old-text", "image_model": "old-image",
                "llm_api_key": "text-secret", "image_api_key": "image-secret", "llm_max_tokens": "4096"}
    captured = []
    def json_create(**kwargs):
        captured.append(("text", kwargs))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))])
    text_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=json_create)), close=lambda: None)
    monkeypatch.setattr(llm, "get_openai_client", lambda **kw: text_client)
    monkeypatch.setattr(llm, "governed_llm_request", lambda *args: nullcontext())
    monkeypatch.setattr(llm, "get_setting", lambda *args: pytest.fail("frozen text must not read global settings"))
    image_client = SimpleNamespace(images=SimpleNamespace(generate=lambda **kw: captured.append(("image", kw))), close=lambda: None)
    monkeypatch.setattr(image_service, "get_openai_client", lambda **kw: image_client)
    monkeypatch.setattr(image_service, "is_toapis_image_provider", lambda *args: False)
    monkeypatch.setattr(image_service, "_governed_image_request", lambda base, call: call())
    monkeypatch.setattr(image_service, "extract_image_bytes_from_response", lambda value: b"png")
    deps = HtmlReviewDependencies(repo_root=ROOT, json_generator=llm.generate_json_with_configured_llm)
    executor = Capture()
    jobs = jobs_module.HtmlWorkflowJobs(SessionLocal, deps, configured_image, executor,
                                      freeze_models=partial(freeze_project_models, setting=settings.get, credential=lambda ref: {}))
    project = Project(id="freeze-" + uuid.uuid4().hex, name="isolated", account_id="default",
                      run_dir=str(tmp_path), visual_backend="html")
    db = SessionLocal()
    try:
        db.add(project)
        db.commit()
        task = jobs.submit(db, project, {"slide_id": "s1"})
        assert jobs.submit(db, project, {"slide_id": "s1"})["reused"]
        assert len(executor.calls) == 1
        settings.update(llm_model="new-text", image_model="new-image", llm_api_key="new-secret", llm_max_tokens="16384")
        new_task = jobs.submit(db, project, {"slide_id": "s1"})
        assert new_task["id"] != task["id"]
        def produce(contract, *, deps, provider, checkpoint, model_summary, **kwargs):
            checkpoint()
            assert deps is not jobs.deps
            assert model_summary["text"]["model"] == "old-text"
            assert model_summary["text"]["parameters"] == {"max_tokens": 4096}
            assert deps.json_generator(system_prompt="test", user_prompt="input", run_dir=str(tmp_path),
                                       artifact_prefix="test", schema_hint="{}") == {"ok": True}
            assert provider("picture") == b"png"
            return {"saved": {"changed": False}}
        monkeypatch.setattr(jobs_module, "produce_scene", produce)
        args = executor.calls[0]
        args[0](*args[1:])
        db.expire_all()
        job = db.query(LocalJob).filter(LocalJob.id == task["id"]).one()
        assert job.status == "succeeded", job.error
        payload = json.dumps(job.get_payload())
        assert "text-secret" not in payload and "image-secret" not in payload
        assert job.get_payload()["input"]["model_summary"]["text"]["model"] == "old-text"
        assert captured[0][1]["model"] == "old-text" and captured[0][1]["max_tokens"] == 4096
        assert captured[1][1]["model"] == "old-image"
        assert jobs.deps is deps and jobs.provider is configured_image
    finally:
        db.close()


def test_frozen_json_initialization_error_does_not_leak(tmp_path, monkeypatch):
    project = SimpleNamespace(run_dir=str(tmp_path))
    settings = {"llm_model": "text", "llm_api_key": "secret-key"}
    frozen = freeze_project_models(project, setting=settings.get, credential=lambda ref: {})
    def fail(**kwargs):
        raise RuntimeError("secret-key")
    monkeypatch.setattr(llm, "get_openai_client", fail)
    with pytest.raises(llm.HTTPException) as exc:
        llm.generate_json_with_configured_llm(model_binding=frozen.text, system_prompt="s", user_prompt="u",
                                              run_dir=str(tmp_path), artifact_prefix="test", schema_hint="{}")
    assert "secret-key" not in str(exc.value.detail)


def test_frozen_parameter_hash_changes_and_clamps(tmp_path):
    settings = {"llm_model": "text", "llm_api_key": "secret-key", "llm_max_tokens": "4096"}
    freeze = partial(freeze_project_models, SimpleNamespace(run_dir=str(tmp_path)), setting=settings.get, credential=lambda ref: {})
    first = freeze()
    settings["llm_max_tokens"] = "999999"
    second = freeze()
    assert first.text.max_tokens == 4096 and second.text.max_tokens == 64000
    assert first.text.config_hash != second.text.config_hash
    assert replace(first.text, error="missing").api_key == first.text.api_key
