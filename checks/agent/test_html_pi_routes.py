"""Real Web/Agent route parsing, shared ownership and durable job polling."""
import time
from dataclasses import replace
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from checks.agent.test_html_handoff_integration import api as api, exchange_api as exchange_api
from checks.test_html_pi_agent import ScriptedProvider


def test_web_agent_pi_jobs_scope_idempotency_and_result(exchange_api, monkeypatch):
    _, ids, run, _ = exchange_api
    import html_agent_routes as web
    import agent_api.html_agent_routes as agent
    import html_agent_jobs as jobs
    import project_model_binding_service as binding
    from database import SessionLocal
    from html_agent_store import AgentJobStore
    monkeypatch.setattr(jobs, "_store", AgentJobStore(SessionLocal))
    app = FastAPI(); app.include_router(web.router); app.include_router(agent.router, prefix="/api/agent/v1")
    with ScriptedProvider(bad_first=False) as provider, TestClient(app) as client:
        monkeypatch.setattr(binding, "freeze_project_models", lambda project: SimpleNamespace(text=provider.model()))
        base = f"/api/projects/{ids['html']}/html-visual/condensation/agent/jobs"
        agent_base = f"/api/agent/v1/projects/{ids['html']}/html-visual/condensation/agent/jobs"
        payload = {"idempotency_key": "http-job-unique", "task": {"task_type": "static_repair", "goal": "调整标题",
            "scope": ["headline"], "expected_revision": 1}}
        for kind in ("foreign", "image"):
            response = client.post(f"/api/projects/{ids[kind]}/html-visual/condensation/agent/jobs", json=payload)
            assert response.status_code in (400, 404), response.text
        invalid = client.post(base, json={**payload, "source": "human"})
        assert invalid.status_code == 422
        created = client.post(base, json=payload)
        assert created.status_code == 202, created.text
        job_id = created.json()["job_id"]
        assert client.post(agent_base, json=payload).json()["job_id"] == job_id
        changed = {**payload, "task": {**payload["task"], "goal": "不同任务"}}
        assert client.post(base, json=changed).status_code == 409
        assert client.get(base.replace("condensation", "other") + "/" + job_id).status_code == 404
        for _ in range(150):
            response = client.get(agent_base + "/" + job_id)
            assert response.status_code == 200, response.text
            value = response.json()
            if value["status"] not in ("queued", "running"): break
            time.sleep(.2)
        assert value["status"] == "succeeded", value
        assert client.get(base + "/" + job_id + "/result").json() == value
        assert client.post(base + "/" + job_id + "/cancel", json={}).json()["status"] == "succeeded"
        assert len(provider.requests) < 12


def test_project_workflow_web_agent_scope_and_real_json_sdk(exchange_api, monkeypatch):
    from checks.test_html_pi_workflows import JSONProvider
    _, ids, run, _ = exchange_api
    import html_agent_routes as web
    import agent_api.html_agent_routes as agent
    import html_agent_jobs as jobs
    import project_model_binding_service as binding
    from database import SessionLocal
    from html_agent_store import AgentJobStore
    monkeypatch.setattr(jobs, "_store", AgentJobStore(SessionLocal))
    monkeypatch.setattr("article_service.read_project_article_generation_system_content", lambda project: "生成文章")
    app = FastAPI(); app.include_router(web.router); app.include_router(agent.router, prefix="/api/agent/v1")
    with JSONProvider({"content": "完整候选文章"}) as provider, TestClient(app) as client:
        planning = replace(provider.model(), model="glm-5.3", supports_images=False,
                           max_tokens=65536, temperature=1.0)
        monkeypatch.setattr(binding, "freeze_project_models", lambda project:
                            SimpleNamespace(text=provider.model(), planning=planning))
        base = f"/api/projects/{ids['html']}/agent/jobs"
        agent_base = f"/api/agent/v1/projects/{ids['html']}/agent/jobs"
        payload = {"idempotency_key": "workflow-http-fixed", "task": {"task_type": "article.generate", "topic": "真实主题"}}
        for kind in ("foreign", "image"):
            assert client.post(f"/api/projects/{ids[kind]}/agent/jobs", json=payload).status_code in (400, 404)
        created = client.post(base, json=payload)
        assert created.status_code == 202, created.text
        job_id = created.json()["job_id"]
        assert client.post(agent_base, json=payload).json()["job_id"] == job_id
        for _ in range(100):
            value = client.get(agent_base + "/" + job_id).json()
            if value["status"] not in ("queued", "running"): break
            time.sleep(.2)
        assert value["status"] == "succeeded", value
        assert value["result"]["candidate"]["content"] == "完整候选文章"
        assert client.get(base + "/" + job_id + "/result").json() == value
        assert not value["result"]["saved"] and len(provider.requests) == 1
        assert provider.requests[0]["model"] == "glm-5.3"
        assert provider.requests[0]["thinking"] == {"type": "enabled"}
        assert provider.requests[0]["max_tokens"] == 65536
