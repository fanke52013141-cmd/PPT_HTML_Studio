"""Full application over loopback TCP, isolated DB/runs and provider boundaries."""
import json
import os
from pathlib import Path
import socket
import threading
import tempfile
import time
from types import SimpleNamespace
import urllib.error
import urllib.request
import uuid

import pytest


def test_current_application_tcp_review_and_course_resume(monkeypatch):
    from database import DB_PATH, Project, SessionLocal
    from repository_paths import RUNS_DIR
    root = Path(__file__).resolve().parents[1]
    assert Path(DB_PATH).resolve() != (root/"data/projects.db").resolve()
    assert Path(RUNS_DIR).resolve() != (root/"runs").resolve()
    assert Path(DB_PATH).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert Path(RUNS_DIR).resolve().parent == Path(DB_PATH).resolve().parent

    # Lazy composition only after isolation/preflight; never imports the live DB.
    import server
    import uvicorn
    import storyboard_service as service
    import html_course_runtime as runtime
    from html_course_jobs import HtmlCourseJobs, CourseBoundary
    from test_script_qualifier_fidelity import SOURCE, plan
    from agent_contract.versions import AGENT_API_VERSION, get_contract_hash

    project_id = "smoke_" + uuid.uuid4().hex[:16]
    run = Path(RUNS_DIR)/project_id
    (run/"inputs").mkdir(parents=True)
    (run/"inputs/article.md").write_text(SOURCE, encoding="utf-8")
    with SessionLocal() as db:
        db.add(Project(id=project_id, name="test", run_dir=str(run), account_id="default",
            visual_backend="html", ai_mode="auto", step_status='{"2":"in_progress"}'))
        db.commit()

    calls = []
    monkeypatch.setattr(service, "read_step2_prompts_for_project", lambda *a, **k: {
        "script_system": "isolated smoke", "script_output_example": "{}"})
    monkeypatch.setattr(service, "run_step2_json_llm", lambda **k: calls.append("script_provider_double") or plan("没有统一标准。"))
    def visual_boundary():
        calls.append("visual_boundary")
        raise CourseBoundary("paused", "storyboard", "isolated smoke stops before downstream provider")
    def services(db, pid):
        return SimpleNamespace(storyboard_script=lambda: service.execute_step2_script_plan(pid, db, {}),
            storyboard_visual=visual_boundary,
            storyboard_compose=lambda: pytest.fail("no downstream model or composition in this smoke"))
    actions = runtime.CourseActions(SimpleNamespace(repo_root=root,
        read_project_article_source=service.read_project_article_source, pipeline_service_factory=services))
    # Freeze a test identity; readiness/credentials are intentionally not tested.
    actions.identity = lambda p: {"smoke_identity": "isolated-provider-boundaries"}
    jobs = HtmlCourseJobs(SessionLocal, actions, poll_seconds=.01)
    monkeypatch.setattr(runtime, "_jobs", jobs)

    # Fail closed if any unanticipated outbound request is attempted.
    attempted_external = []
    for name in ("connect", "connect_ex"):
        original = getattr(socket.socket, name)
        def guarded(sock, address, _original=original):
            if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
                attempted_external.append(str(address[0]))
                raise AssertionError("External connection forbidden in smoke test")
            return _original(sock, address)
        monkeypatch.setattr(socket.socket, name, guarded)

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    instance = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=instance.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    def http(path, payload=None, method=None):
        request = urllib.request.Request(f"http://127.0.0.1:{port}"+path,
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type":"application/json", "X-PPT-Studio-Request":"1"}, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read()
            return response.status, response.headers, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body
    def status_until(expected):
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            code, _, body = http(f"/api/projects/{project_id}/one-click-generate/status")
            assert code == 200
            if body["status"]["status"] == expected:
                return body["status"]
            time.sleep(.05)
        pytest.fail("Course did not reach expected boundary")
    try:
        deadline = time.monotonic()+15
        while not instance.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.02)
        assert instance.started
        code, _, meta = http("/api/agent/v1/meta")
        assert code == 200 and meta["agent_api_version"] == AGENT_API_VERSION
        assert meta["contract_hash"] == get_contract_hash()
        assets = []
        for name in ("index.html", "storyboard.js", "one_click_extension.js", "api_client.js"):
            code, headers, body = http("/" if name == "index.html" else "/"+name)
            assert code == 200 and body == (root/"static"/name).read_bytes()
            assert "no-store" in headers.get("Cache-Control", "")
            assets.append(name)
        base = f"/api/projects/{project_id}"
        code, _, started = http(base+"/one-click-generate", {})
        assert code == 200
        waiting = status_until("waiting_for_user")
        parent_id = waiting["job_id"]
        assert waiting["review_checkpoint"] == "script_review"
        assert calls == ["script_provider_double"]
        code, _, loaded = http(base+"/steps/2/script/result")
        assert code == 200 and loaded["script_plan"] is None
        review_id = loaded["script_review"]["review_id"]
        code, _, _ = http(base+"/one-click-generate", {})
        assert code == 409  # Preserve the service's recoverable conflict status.
        assert calls == ["script_provider_double"]
        code, _, _ = http(base+"/steps/2/script/result", plan(SOURCE), "PUT")
        assert code == 409
        code, _, saved = http(base+"/steps/2/script/result", {**plan(SOURCE), "review_id": review_id}, "PUT")
        assert code == 200 and saved["script_review"]["status"] == "resolved"
        code, _, resumed = http(base+"/one-click-generate", {})
        assert code == 200 and resumed["status"]["job_id"] == parent_id
        stopped = status_until("paused")
        assert stopped["job_id"] == parent_id
        assert calls == ["script_provider_double", "visual_boundary"]
        assert not attempted_external
        evidence = {"api_version": AGENT_API_VERSION, "contract_hash": meta["contract_hash"],
            "transport":"loopback_tcp", "isolated_db":True, "isolated_runs":True,
            "same_parent":True, "script_provider_double_calls":1, "stopped_before_visual_provider":True,
            "assets_byte_equal_no_store":assets, "external_attempts":attempted_external,
            "provider_quality_tested":False, "production_8010_restarted":False}
        if os.environ.get("PPT_STUDIO_SMOKE_REPORT"):
            output = Path(os.environ["PPT_STUDIO_SMOKE_REPORT"])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x",encoding="utf-8") as file:
                json.dump(evidence,file,ensure_ascii=False,indent=2)
    finally:
        instance.should_exit = True  # Graceful teardown of this test-owned thread only.
        thread.join(timeout=10)
        jobs.executor.shutdown(wait=True)
        listener.close()
        assert not thread.is_alive()
