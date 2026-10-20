"""Pipe-only browser fixture: routes local requests without opening network sockets."""
import base64
import json
from pathlib import Path
import sys
import os
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
if "--pi" in sys.argv:
    fixture_run = Path(sys.argv[1]).resolve()
    if not fixture_run.name.startswith("hps-editor-browser-"):
        raise ValueError("isolated fixture required")
    os.environ["PPT_STUDIO_DB_PATH"] = str(fixture_run / "pi-fixture.db")
    os.environ["PPT_STUDIO_RUNS_DIR"] = str(fixture_run / "runs")
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(ROOT))

import html_scene_editing as editor  # noqa: E402
import html_external_handoff as handoff  # noqa: E402
import html_visual_store as store  # noqa: E402
from checks.test_html_scene_editor_fixture import fixture_scene  # noqa: E402
from pipeline_lifecycle import project_artifact_lock  # noqa: E402


run = Path(sys.argv[1]).resolve()
if not run.name.startswith("hps-editor-browser-"):
    raise ValueError("isolated fixture directory required")
scene = fixture_scene(presentation=True)
store.save_scene(run, scene["id"], scene, 0)
beats = [{"id": f"b{i}", "text": f"测试原句{i}"} for i in range(1, 4)]
(run / "planning/visual_contract.json").write_text(json.dumps({"slides": [
    {"slide_id": "condensation", "narration_beats": beats}]}), encoding="utf-8")
import hashlib  # noqa: E402
binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_ids",
           "sourceBeats": [{"id": b["id"], "spoken_text": b["text"],
                            "spoken_text_sha256": hashlib.sha256(b["text"].encode()).hexdigest()} for b in beats],
           "actions": {a["actionId"]: {"beatId": "b1", "edge": "start", "offsetMs": int(a["startMs"])} for a in scene["motion"]}}
(run / "planning/html_visual/binding-condensation.json").write_text(json.dumps(binding), encoding="utf-8")

if "--pi" in sys.argv:
    from database import init_db, SessionLocal
    from html_agent_store import AgentJobStore
    from checks.test_html_pi_agent import ScriptedProvider
    import html_agent_jobs as pi_jobs
    from html_agent_models import AgentJobRequest
    init_db()
    pi_store = AgentJobStore(SessionLocal)
    provider = ScriptedProvider(bad_first=False).__enter__()


def dispatch(method, path, payload):
    if "--pi" in sys.argv and "/agent/jobs" in path:
        if method == "POST" and path.endswith("/jobs"):
            return pi_jobs.submit(run, "isolated", "condensation", AgentJobRequest.model_validate(payload), provider.model(), store=pi_store), None
        job_id = path.split("/agent/jobs/")[1].split("/")[0]
        if path.endswith("/cancel"):
            return pi_store.update("isolated", "condensation", job_id, cancel_requested=True), None
        return pi_store.read("isolated", "condensation", job_id), None
    if method == "GET" and path == "/":
        scripts = ["api_client.js", "html_editor_canvas.js", "html_editor_timeline_bridge.js", "html_handoff_workbench.js", "html_pi_agent.js", "html_external_handoff.js", "html_scene_editor.js"]
        html = ('<meta charset="utf-8"><link rel="stylesheet" href="/static/html_scene_edit.css"><link rel="stylesheet" href="/static/html_workflow.css">'
                '<div id="host"></div><script>function showToast(){}</script>'
                + ''.join(f'<script src="/static/{name}"></script>' for name in scripts)
                + '<script>HtmlSceneEditor.open(document.getElementById("host"),"isolated","condensation")</script>')
        return html.encode(), "text/html"
    if method == "GET" and path.startswith("/static/"):
        file = (ROOT / path.lstrip("/")).resolve()
        if not file.is_relative_to(ROOT / "static"):
            raise ValueError("fixture path")
        return file.read_bytes(), "text/css" if file.suffix == ".css" else "application/javascript"
    if method == "GET" and path.startswith("/api/html-scene-editor/runtime/"):
        name = path.rsplit("/", 1)[-1]
        if name not in ("player.js", "data.js"):
            raise ValueError("fixture runtime")
        return (ROOT / "html_engine/visual/preview" / name).read_bytes(), "application/javascript"
    if path.endswith("/steps/7/audio-status"):
        return {"slides": [{"slide_id": "condensation", "audio_exists": False}]}, None
    with project_artifact_lock(run):
        if "/editor/versions/" in path:
            return editor.saved_versions(run, "condensation", int(path.rsplit("/", 1)[-1])), None
        if path.endswith("/editor/versions"):
            return {"versions": editor.saved_versions(run, "condensation")}, None
        if path.endswith("/editor"):
            if method == "PUT":
                return editor.save_editor(run, "condensation", **payload), None
            return editor.load_editor(run, "condensation"), None
        if path.endswith("/editor/preview"):
            return editor.preview_editor(run, "condensation", payload["scene"], payload["binding"],
                expected_revision=payload["expected_revision"], expected_audio_revision=payload.get("expected_audio_revision")), None
        if "/handoff/work/" in path:
            import html_handoff_workbench as workbench
            name = path.rsplit("/", 1)[-1]
            return {"propose": workbench.preview_proposal, "open": workbench.open_work, "read": workbench.read_work, "update": workbench.update_work,
                    "check": workbench.check_work, "save": workbench.save_work}[name](run, "isolated", "condensation", payload), None
        if path.endswith("/handoff/export"):
            result = handoff.export_bundle(run, "isolated", "condensation", payload)
            result["download_url"] = f"/api/projects/isolated/html-visual/condensation/handoff/{result['task']['task_id']}/bundle"
            return result, None
        if "/handoff/" in path and path.endswith("/bundle"):
            return handoff.bundle_path(run, "isolated", "condensation", path.split("/")[-2]).read_bytes(), "application/zip"
        if path.endswith("/handoff/preview"):
            return handoff.import_preview(run, "isolated", "condensation", payload), None
        if path.endswith("/handoff/save"):
            return handoff.save_result(run, "isolated", "condensation", payload), None
    raise ValueError("unknown fixture route: " + path)


for line in sys.stdin:
    try:
        request = json.loads(line)
        body, mime = dispatch(request["method"], urlsplit(request["url"]).path, request.get("payload"))
        response = {"status": 200, "contentType": mime or "application/json",
                    "body": base64.b64encode(body if isinstance(body, bytes) else json.dumps(body).encode()).decode()}
    except Exception as error:
        status = getattr(error, "status_code", 409 if getattr(error, "code", "") == "AUDIO_REVISION_CONFLICT" else 422)
        response = {"status": status, "contentType": "application/json", "body": base64.b64encode(json.dumps(
            {"detail": {"message": str(error), "code": getattr(error, "code", "INVALID")}}).encode()).decode()}
    print(json.dumps(response), flush=True)
