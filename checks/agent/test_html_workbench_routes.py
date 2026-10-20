"""Actual FastAPI parsing, account dispatch, and read-only Agent exposure."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from checks.agent.test_html_handoff_integration import api as api, exchange_api as exchange_api


def test_human_work_http_models_save_and_read_only_agent_route(exchange_api):
    _, ids, _, _ = exchange_api
    import html_handoff_routes as web
    import agent_api.html_handoff_routes as agent
    app = FastAPI()
    app.include_router(web.router)
    app.include_router(agent.router, prefix="/api/agent/v1")
    with TestClient(app) as client:
        base = f"/api/projects/{ids['html']}/html-visual/condensation/handoff"
        agent_base = f"/api/agent/v1/projects/{ids['html']}/html-visual/condensation/handoff"
        exported = client.post(base + "/export", json={"task_type": "static_repair", "goal": "保持原文调整标题",
            "scope": ["headline"], "expected_revision": 1})
        assert exported.status_code == 200, exported.text
        result = {"task_id": exported.json()["task"]["task_id"], "status": "proposed", "message": "标题样式候选",
                  "operations": [{"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 28}}]}
        imported = client.post(base + "/preview", json={"result": result})
        assert imported.status_code == 200, imported.text
        ref = {"task_id": result["task_id"], "result_hash": imported.json()["result_hash"]}
        opened = client.post(base + "/work/open", json=ref)
        assert opened.status_code == 200, opened.text
        assert client.post(agent_base + "/work/read", json=ref).status_code == 200
        assert client.post(agent_base + "/work/update", json=ref).status_code == 404
        assert client.post(agent_base + "/work/propose", json=ref).status_code == 404
        operation = {"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": 1}}
        payload = {**ref, "work_revision": 0, "operations": [operation]}
        updated = client.post(base + "/work/update", json=payload)
        assert updated.status_code == 200, updated.text
        assert client.post(base + "/work/update", json=payload).status_code == 409
        payload["work_revision"] = 1
        assert client.post(base + "/work/check", json={**payload, "source": "human"}).status_code == 422
        checked = client.post(base + "/work/check", json=payload)
        assert checked.status_code == 200 and checked.json()["work"]["check"]["passed"], checked.text
        denied_plan = client.post(base + "/work/propose", json={**payload, "proposal_id": "f"*64})
        assert denied_plan.status_code == 409
        assert client.post(base + "/work/propose", json={**payload, "source": "human"}).status_code == 422
        assert client.post(base + "/work/update", json={**payload, "selected_group_ids": ["invented"]}).status_code == 409
        assert client.post(agent_base + "/work/read", json=ref).json()["work"]["work_revision"] == 1

        saved = client.post(base + "/work/save", json=payload)
        assert saved.status_code == 200 and saved.json()["saved"] and saved.json()["revision"] == 2, saved.text
        assert client.post(agent_base + "/work/read", json=ref).json()["saved"]
        for kind in ("image", "foreign"):
            denied = client.post(f"/api/projects/{ids[kind]}/html-visual/condensation/handoff/work/read", json=ref)
            assert denied.status_code in (400, 404), denied.text
            denied_plan = client.post(f"/api/projects/{ids[kind]}/html-visual/condensation/handoff/work/propose", json={**payload, "proposal_id": "f"*64})
            assert denied_plan.status_code in (400, 404), denied_plan.text
