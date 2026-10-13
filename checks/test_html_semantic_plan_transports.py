"""Real adapters with isolated projects and deterministic model responses."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_api import routes as agent
from database import Project, SessionLocal, get_db
from html_visual_review_service import HtmlReviewDependencies
import html_visual_review_routes as web
from test_html_narration_semantics import CONTRACT_SLIDE, semantic_plan
from test_html_visual_review import model_plan

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def clients(tmp_path, monkeypatch):
    from repository_paths import RUNS_DIR
    projects = {}
    calls = []

    def generator(**kwargs):
        calls.append(kwargs)
        if "html-plan-0.6.0" in kwargs["system_prompt"]:
            from test_html_object_decomposition import decomposition_plan

            return decomposition_plan()
        return semantic_plan() if "html-plan-0.5.0" in kwargs["system_prompt"] else model_plan()

    deps = HtmlReviewDependencies(repo_root=ROOT, json_generator=generator)
    monkeypatch.setattr(web, "_dependencies", deps)
    monkeypatch.setattr(agent, "_agent_review_deps", lambda: deps)
    db = SessionLocal()
    for kind in ("html", "image", "foreign"):
        pid = "semantic-" + uuid.uuid4().hex
        run = Path(RUNS_DIR) / pid
        (run / "planning").mkdir(parents=True)
        (run / "planning/visual_contract.json").write_text(json.dumps({"slides": [CONTRACT_SLIDE]}), encoding="utf-8")
        db.add(Project(id=pid, name=kind, run_dir=str(run), visual_backend="image" if kind == "image" else "html",
                       account_id="other-account" if kind == "foreign" else "default"))
        projects[kind] = (pid, run)
    db.commit()
    db.close()
    app = FastAPI()
    app.include_router(web.router)
    app.include_router(agent.router)

    def database():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[web._get_db] = database
    with TestClient(app) as client:
        yield client, projects, calls


@pytest.mark.parametrize("prefix", ["/api", "/api/agent/v1"])
def test_http_version_selection_exact_source_and_no_author_writes(clients, prefix):
    client, projects, calls = clients
    pid, run = projects["html"]
    path = f"{prefix}/projects/{pid}/html-review/slide_001/plan/generate"
    legacy = client.post(path, json={})
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["plan"]["version"] == "0.1.0"
    legacy_record = (run / "planning/html_visual/records/plan-slide_001.json").read_bytes()
    semantic = client.post(path, json={"plan_version": "0.2.0"})
    assert semantic.status_code == 200, semantic.text
    result = semantic.json()
    assert result["plan"]["version"] == "0.2.0"
    assert result["plan"]["beats"][0]["spoken_text"] == CONTRACT_SLIDE["narration_beats"][0]["spoken_text"]
    assert result["evidence"]["validation"]["semantic"] == "not_run"
    assert (run / "planning/html_visual/records/plan-slide_001.json").read_bytes() == legacy_record
    assert (run / "planning/html_visual/records/plan-slide_001-v0.2.0.json").is_file()
    decomposed = client.post(path, json={"plan_version": "0.3.0", "asset_budget": 0})
    assert decomposed.status_code == 200, decomposed.text
    assert decomposed.json()["plan"]["design_brief"]["version"] == "0.2.0"
    assert decomposed.json()["plan"]["assetPolicy"]["budget"] == 0
    assert decomposed.json()["plan"]["objectSemantics"]
    from html_reference_package import design_content
    returned = decomposed.json()["plan"]
    assert design_content(returned, returned["design_brief"])["narrationDesign"]["sequence"] == returned["visualSequence"]
    assert (run / "planning/html_visual/records/plan-slide_001.json").read_bytes() == legacy_record
    assert not list((run / "planning/html_visual").glob("scene*.json"))
    assert not list((run / "planning/html_visual").glob("approval*.json"))
    before = len(calls)
    assert client.post(path, json={"plan_version": "garbage"}).status_code == 422
    assert client.post(path, json={"plan_version": "0.3.0", "asset_budget": True}).status_code == 422
    assert client.post(path, json={"plan_version": "0.2.0", "bypass": True}).status_code == 422
    for kind, status in (("image", 400), ("foreign", 404)):
        blocked = f"{prefix}/projects/{projects[kind][0]}/html-review/slide_001/plan/generate"
        assert client.post(blocked, json={"plan_version": "0.2.0"}).status_code == status
    assert len(calls) == before


def test_mcp_cli_and_actual_client_forward_version_body(tmp_path, monkeypatch, capsys):
    from agent_client.client import AgentClient
    import agent_client.client as http
    from mcp_server.tools import _dispatch, get_all_tool_definitions
    from cli.pptctl import build_parser
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b'{"ok":true}'
    requests = []

    def urlopen(request, **kwargs):
        requests.append(request)
        return response

    monkeypatch.setattr(http, "urlopen", urlopen)
    client = AgentClient(base_url="http://isolated.test/api/agent/v1")
    payload = {"plan_version": "0.3.0", "asset_budget": 0, "brief": {"instruction": "preserve source"}}
    _dispatch("html_review.plan_generate", {"project_id": "p1", "slide_id": "slide_001", **payload}, client)
    assert json.loads(requests[-1].data) == payload
    assert requests[-1].full_url.endswith("/projects/p1/html-review/slide_001/plan/generate")
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps(payload), encoding="utf-8")
    args = build_parser().parse_args(["html", "plan-generate", "--project", "p1", "--slide", "slide_001", "--file", str(request_file)])
    args.func(args)
    assert json.loads(requests[-1].data) == payload
    assert '"ok": true' in capsys.readouterr().out
    schema = next(tool for tool in get_all_tool_definitions() if tool["name"] == "ppt_html_plan_generate")["inputSchema"]
    assert schema["properties"]["plan_version"]["enum"] == ["0.1.0", "0.2.0", "0.3.0"]
    client.post_html_plan_generate("p1", "slide_001")
    assert json.loads(requests[-1].data) == {}
