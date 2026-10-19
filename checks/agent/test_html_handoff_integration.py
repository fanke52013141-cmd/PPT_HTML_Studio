"""Web/Agent handler ownership and MCP/CLI forwarding, without network sockets."""
import json
import zipfile
import io
import re
import uuid
import base64

import pytest
from PIL import Image

from agent_client.client import AgentClient, AgentClientError
import html_scene_repair as repair


@pytest.fixture
def api(tmp_path):
    from pathlib import Path
    from database import Project, SessionLocal
    from repository_paths import RUNS_DIR
    import html_visual_store as store
    from html_handoff_models import ExportRequest, ImportRequest, SaveRequest
    import html_handoff_routes as web
    import agent_api.html_handoff_routes as agent
    from html_visual_routes import html_scene_editor_get
    from fastapi.responses import FileResponse

    ids = {kind: "handoff-" + uuid.uuid4().hex for kind in ("html", "image", "foreign")}
    root = Path(__file__).resolve().parents[2]
    scene = json.loads((root / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    db = SessionLocal()
    for kind, pid in ids.items():
        run = Path(RUNS_DIR) / pid
        run.mkdir(parents=True)
        db.add(Project(id=pid, name=kind, run_dir=str(run), visual_backend="image" if kind == "image" else "html",
                       account_id="another-account" if kind == "foreign" else "default"))
    db.commit()
    run = Path(RUNS_DIR) / ids["html"]
    store.save_scene(run, "condensation", scene, 0)
    (run / "planning/visual_contract.json").write_text(json.dumps({"slides": [
        {"slide_id": "condensation", "narration_beats": [{"id": "b1", "text": "准确原句"}]}]}), encoding="utf-8")

    class Response:
        def __init__(self, value=None, status=200, data=None, mime="application/json"):
            self.value, self.status_code = value, status
            self.content = data if data is not None else json.dumps(value).encode()
            self.text = self.content.decode("utf-8", errors="replace")
            self.headers = {"content-type": mime}

        def json(self):
            return self.value

    class Client:
        def request(self, method, path, json=None, **kwargs):
            match = re.fullmatch(r"/api/(agent/v1/)?projects/([^/]+)/html-visual/([^/]+)/(.*)", path)
            assert match, path
            is_agent, project_id, slide_id, suffix = match.groups()
            adapter = agent if is_agent else web
            with SessionLocal() as session:
                try:
                    if suffix == "editor":
                        value = html_scene_editor_get(project_id, slide_id, session)
                    elif suffix.endswith("/bundle"):
                        value = adapter.bundle(project_id, slide_id, suffix.split("/")[-2], session)
                    else:
                        action = suffix.rsplit("/", 1)[-1]
                        model = {"export": ExportRequest, "preview": ImportRequest, "save": SaveRequest}[action]
                        value = getattr(adapter, action)(project_id, slide_id, model.model_validate(json), session)
                    if isinstance(value, FileResponse):
                        return Response(data=Path(value.path).read_bytes(), mime=value.media_type)
                    return Response(value)
                except Exception as error:
                    status = getattr(error, "status_code", 422)
                    detail = getattr(error, "detail", None)
                    if detail is None:
                        detail = {"code": getattr(error, "code", "INVALID"), "message": str(error)}
                    return Response({"detail": detail}, status)

        def post(self, path, **kwargs):
            return self.request("POST", path, **kwargs)

        def get(self, path, **kwargs):
            return self.request("GET", path, **kwargs)

    yield Client(), ids, run, scene
    for pid in ids.values():
        db.query(Project).filter(Project.id == pid).delete()
    db.commit()
    db.close()


@pytest.fixture
def exchange_api(api, monkeypatch):
    client, ids, run, scene = api
    shot = run / "handoff-fixture/frame.png"
    shot.parent.mkdir()
    Image.new("RGB", (1600, 900), "white").save(shot)
    monkeypatch.setattr(repair, "evidence", lambda *a, **k: {
        "passed": True, "screenshots": [{"timeMs": 6000, "file": "handoff-fixture/frame.png"}], "issues": []})
    return client, ids, run, scene


def export(client, pid, prefix="/api/projects"):
    base = f"{prefix}/{pid}/html-visual/condensation/handoff"
    response = client.post(base + "/export", json={"task_type": "static_repair", "goal": "调整当前标题字阶",
        "scope": ["headline"], "expected_revision": 1})
    assert response.status_code == 200, response.text
    return base, response.json()


def test_web_agent_export_download_preview_and_explicit_save_share_service(exchange_api):
    client, ids, run, scene = exchange_api
    web, packet = export(client, ids["html"])
    task = packet["task"]
    archive = client.get(packet["download_url"])
    assert archive.status_code == 200 and archive.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
        assert json.loads(zipped.read("task.json"))["task_id"] == task["task_id"]
    for kind in ("image", "foreign"):
        denied = client.post(f"/api/agent/v1/projects/{ids[kind]}/html-visual/condensation/handoff/export",
            json={"task_type": "static_repair", "goal": "fix", "scope": ["headline"], "expected_revision": 1})
        assert denied.status_code in (400, 404)
    proposed = {"format": "hps.html.external_result", "version": "0.2.0", "task_id": task["task_id"],
                "status": "proposed", "message": "调整标题", "operations": [
                    {"kind": "set_text_style", "targetId": "headline", "part": "text", "values": {"fontSizePx": 28}}]}
    response = client.post(web + "/preview", json={"result": proposed})
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["passed"] and client.get(web.removesuffix("/handoff") + "/editor").json()["revision"] == 1
    agent = f"/api/agent/v1/projects/{ids['html']}/html-visual/condensation/handoff"
    saved = client.post(agent + "/save", json={"result": proposed, "candidate_key": receipt["candidate_key"],
                                               "result_hash": receipt["result_hash"]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["changed"]
    assert client.post(web + "/preview", json={"result": proposed}).status_code == 409


def test_agent_mcp_cli_and_binary_download_match_registered_contract(exchange_api, monkeypatch, tmp_path, capsys):
    from mcp_server.tools import _dispatch
    from cli import pptctl
    client, ids, _, _ = exchange_api
    calls = []
    def request(self, method, path, body=None, **kwargs):
        calls.append((method, path, body))
        response = client.request(method, path, json=body)
        if response.status_code >= 400:
            raise AgentClientError(response.text, response.status_code)
        return response.json()
    monkeypatch.setattr(AgentClient, "_request", request)
    fields = {"task_type": "static_repair", "goal": "仅调整标题", "scope": ["headline"], "expected_revision": 1}
    packet = _dispatch("html_handoff.export", {"project_id": ids["html"], "slide_id": "condensation", **fields}, AgentClient())
    assert packet["download_url"].startswith("/api/agent/v1/")
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps(fields), encoding="utf-8")
    args = pptctl.build_parser().parse_args(["html", "handoff-export", "--project", ids["html"],
                                            "--slide", "condensation", "--file", str(request_file)])
    args.func(args)
    cli = json.loads(capsys.readouterr().out)
    assert cli["task"]["task_id"] == packet["task"]["task_id"]
    monkeypatch.setattr(AgentClient, "get_bytes", lambda self, path: (client.get(path).content, "application/zip"))
    target = tmp_path / "task.zip"
    args = pptctl.build_parser().parse_args(["html", "handoff-bundle", "--project", ids["html"], "--slide", "condensation",
        "--task-id", packet["task"]["task_id"], "--out", str(target)])
    args.func(args)
    assert zipfile.is_zipfile(target)


def test_bad_result_and_unpreviewed_save_do_not_write(exchange_api):
    client, ids, run, _ = exchange_api
    base, packet = export(client, ids["html"], "/api/agent/v1/projects")
    author = run / "planning/html_visual/scene-condensation.json"
    before = author.read_bytes()
    task_id = packet["task"]["task_id"]
    proposed = {"task_id": task_id, "status": "proposed", "message": "bad", "operations": [
        {"targetId": "headline", "kind": "set_presentation", "values": {"width": 99999}}]}
    assert client.post(base + "/preview", json={"result": proposed}).status_code == 422
    proposed["operations"][0]["values"] = {"width": 700}
    response = client.post(base + "/save", json={"result": proposed, "candidate_key": "a" * 64, "result_hash": "b" * 64})
    assert response.status_code == 409 and "VALID_PREVIEW_REQUIRED" in response.text
    assert author.read_bytes() == before


def test_zip_output_web_and_agent_adapters_retain_report_without_implicit_save(exchange_api):
    client, ids, run, _ = exchange_api
    base, packet = export(client, ids["html"])
    proposed = {"task_id": packet["task"]["task_id"], "status": "proposed", "message": "adjust", "operations": [
        {"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 28}}]}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("result.json", json.dumps(proposed))
        archive.writestr("report.md", "# actual external report\nnot_run")
    payload = {"delivery_base64": base64.b64encode(stream.getvalue()).decode()}
    before = (run / "planning/html_visual/scene-condensation.json").read_bytes()
    for prefix in ("/api/projects", "/api/agent/v1/projects"):
        response = client.post(f"{prefix}/{ids['html']}/html-visual/condensation/handoff/preview", json=payload)
        assert response.status_code == 200, response.text
        received = response.json()
        assert received["passed"] and received["delivery"]["kind"] == "zip"
        assert received["delivery"]["report_markdown"].endswith("not_run")
        assert received["result"]["task_id"] == proposed["task_id"] and received["saved"] is False
    assert (run / "planning/html_visual/scene-condensation.json").read_bytes() == before
    assert len(list((run / "planning/html_visual/external-handoffs" / proposed["task_id"] / "deliveries").glob("*/report.md"))) == 1
