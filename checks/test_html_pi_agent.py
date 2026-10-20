"""Real Pi SDK against a local scripted provider, never a model-quality claim."""
import json
import copy
from dataclasses import replace
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from checks.test_html_external_package import page as page
import html_scene_editing as editor
import html_scene_repair as repair
import html_agent_jobs as jobs
from html_agent_models import AgentJobRequest
from html_agent_store import AgentJobStore, JobConflict
from project_model_binding_service import FrozenModel

REAL_EVIDENCE = repair.evidence


@pytest.fixture
def job_store():
    from database import SessionLocal
    return AgentJobStore(SessionLocal)


def request(page, **changes):
    return AgentJobRequest.model_validate({"idempotency_key": "test-pi-" + page[0].name,
        "task": {"task_type": "static_repair", "goal": "把标题字号提高至28，保留其他内容",
            "scope": ["headline"], "expected_revision": 1,
            "font_requirements": [{"id": "title_min", "targetId": "headline", "part": "text", "minimum_px": 28}]}, **changes})


class ScriptedProvider:
    def __init__(self, *, bad_first=True, stop=False, forbidden=False, operation=None, http_error=False):
        self.requests, self.bad_first, self.stop, self.forbidden = [], bad_first, stop, forbidden
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def handle(self):
                try: super().handle()
                except (ConnectionResetError, BrokenPipeError): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.requests.append(body)
                if http_error:
                    self.send_response(503); self.end_headers(); self.wfile.write(b'{"error":{"message":"test unavailable"}}'); return
                index = len(owner.requests) - 1
                first_user = next(message for message in body["messages"] if message["role"] == "user")
                content = first_user["content"]
                if isinstance(content, list): content = next(c["text"] for c in content if c["type"] == "text")
                prompt = json.loads(content)
                task_id = prompt["task_id"]
                def result(size=28):
                    return {"task_id": task_id, "status": "proposed", "message": "调整标题字号",
                        "operations": [operation or {"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": size}}]}
                sequence = [("read_material", {"name": name}) for name in ["ENTRY.md", "decision-input.json", "constraints.json", "task.json", "content.json"]]
                # Derive actual screenshot name from the real task tool response.
                baseline = "evidence/baseline-0.png"
                for task_response in [m for m in body["messages"] if m.get("role") == "tool"]:
                    content = task_response["content"]
                    if isinstance(content, list): content = next(c["text"] for c in content if c["type"] == "text")
                    try:
                        material = json.loads(content)
                        if material.get("name") == "task.json":
                            baseline = json.loads(material["text"])["context"]["evidence"]["screenshots"][0]["file"]
                    except (ValueError, KeyError): pass
                sequence += [("view_image", {"name": baseline})]
                if owner.stop:
                    sequence += [("submit_result", {"result": {"task_id": task_id, "status": "unsupported", "message": "保护字段不可修改", "operations": []}, "baseline_notes": "", "candidate_notes": ""})]
                else:
                    if owner.bad_first: sequence += [("check_candidate", {"result": result(27)})]
                    sequence += [("check_candidate", {"result": result()}),
                        ("view_image", {"name": f"candidate/{2 if owner.bad_first else 1}/0.png"}),
                        ("submit_result", {"result": result(), "baseline_notes": "原图标题与正文可见，保持灰阶风格", "candidate_notes": "修改后标题可读，原文与对象保留"})]
                if owner.forbidden:
                    sequence = [("bash", {"command": "echo forbidden"})]
                name, arguments = sequence[min(index, len(sequence)-1)]
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                chunks = [
                    {"id": f"chat-{index}", "object": "chat.completion.chunk", "created": 0, "model": "local-test",
                     "choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{"index": 0, "id": f"call-{index}", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]}, "finish_reason": None}]},
                    {"id": f"chat-{index}", "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}},
                ]
                try:
                    for chunk in chunks: self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError): pass
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def model(self):
        return FrozenModel("openai", "local-test", f"http://127.0.0.1:{self.server.server_port}/v1", "local-test-secret",
            "test", None, "mock-config", supports_images=True, max_tokens=2048)


def execute(page, job_store, provider, payload=None):
    payload = payload or request(page)
    model = provider.model()
    job = jobs.submit(page[0], "project-a", page[1]["id"], payload, model, store=job_store, launch=False)
    jobs._work(job_store, page[0], "project-a", page[1]["id"], payload, model, job["job_id"])
    return job_store.read("project-a", page[1]["id"], job["job_id"])


def test_glm_tool_workflow_sends_native_thinking_budget(page, job_store):
    with ScriptedProvider(bad_first=False) as provider:
        model = replace(provider.model(), model="glm-5.3-flash", max_tokens=65536, temperature=1.0)
        provider.model = lambda: model
        result = execute(page, job_store, provider)
        assert result["status"] == "succeeded", result["error"]
        assert all(body["thinking"] == {"type": "enabled"}
                   and body["max_tokens"] == 65536 and body["temperature"] == 1.0
                   for body in provider.requests)
        stored = job_store.read("project-a", page[1]["id"], result["job_id"], private=True)
        assert stored["payload"]["model"]["execution_profile"]["thinking_level"] == "enabled"


def test_real_sdk_tools_images_second_round_strict_delivery_without_author_save(page, job_store):
    before = editor.load_editor(*page[:1], page[1]["id"])
    with ScriptedProvider() as provider:
        job = execute(page, job_store, provider)
    assert job["status"] == "succeeded", json.dumps({"error": job["error"], "tools": [str(m.get("content"))[:500] for m in provider.requests[-1]["messages"] if m["role"] == "tool"]}, ensure_ascii=False)
    assert job["usage"]["candidate_rounds"] == 2 and job["usage"]["cost"] is None
    assert job["result"]["preview"]["passed"] and job["result"]["delivery"]["delivery_base64"]
    assert editor.load_editor(page[0], page[1]["id"]) == before
    assert len(provider.requests) <= 12
    names = {tool["function"]["name"] for tool in provider.requests[0]["tools"]}
    assert names == {"read_material", "view_image", "check_candidate", "submit_result"}
    assert any('data:image/png;base64,' in json.dumps(body) for body in provider.requests)
    stored = job_store.read("project-a", page[1]["id"], job["job_id"], private=True)
    assert "local-test-secret" not in json.dumps(stored)


def test_idempotency_scope_conflict_cancel_and_recovery(page, job_store):
    with ScriptedProvider() as provider:
        payload = request(page)
        model = provider.model()
        a = jobs.submit(page[0], "project-a", page[1]["id"], payload, model, store=job_store, launch=False)
        assert jobs.submit(page[0], "project-a", page[1]["id"], payload, None, store=job_store, launch=False) == a
        changed = payload.model_copy(deep=True); changed.task.goal = "不同目标"
        with pytest.raises(JobConflict): jobs.submit(page[0], "project-a", page[1]["id"], changed, model, store=job_store, launch=False)
        with pytest.raises(KeyError): job_store.read("foreign", page[1]["id"], a["job_id"])
        with pytest.raises(KeyError): job_store.update("project-a", "other", a["job_id"], cancel_requested=True)
        job_store.update("project-a", page[1]["id"], a["job_id"], cancel_requested=True)
        jobs._work(job_store, page[0], "project-a", page[1]["id"], payload, model, a["job_id"])
        assert job_store.read("project-a", page[1]["id"], a["job_id"])["status"] == "cancelled"
        assert not provider.requests
        another = payload.model_copy(deep=True); another.idempotency_key += "-restart"
        b = jobs.submit(page[0], "project-a", page[1]["id"], another, model, store=job_store, launch=False)
        job_store.recover()
        assert job_store.read("project-a", page[1]["id"], b["job_id"])["status"] == "interrupted"


def test_missing_vision_stops_before_paid_call(page, job_store):
    from dataclasses import replace
    with ScriptedProvider() as provider:
        with pytest.raises(jobs.ExecutionError, match="图像"):
            jobs.submit(page[0], "project-a", page[1]["id"], request(page), replace(provider.model(), supports_images=False), store=job_store)
        assert not provider.requests


@pytest.mark.parametrize("mode", ["stop", "budget"])
def test_stop_and_budget_never_return_success_or_delivery(page, job_store, mode):
    payload = request(page)
    if mode == "budget": payload.limits.max_model_calls = 2
    with ScriptedProvider(stop=mode == "stop") as provider:
        job = execute(page, job_store, provider, payload)
    assert job["status"] == "failed", job
    assert job["result"] is None
    assert job["error"]["code"] == ("constraints_unsatisfied" if mode == "stop" else "budget_exceeded")


def test_original_manual_protection_cannot_be_bypassed_by_pi(page, job_store):
    run, scene = page
    current = editor.load_editor(run, scene["id"])
    protected = copy.deepcopy(current["scene"])
    protected["version"] = "0.5.0"
    import html_visual_store as store
    store.save_scene(run, scene["id"], protected, 1)
    next(n for n in protected["nodes"] if n["id"] == "headline").setdefault("presentation", {}).setdefault("typography", {})["text"] = {"fontSizePx": 30}
    editor.save_editor(run, scene["id"], protected, current["binding"], 2, origin="human")
    before = editor.load_editor(run, scene["id"])
    payload = request(page); payload.task.expected_revision = 3
    with ScriptedProvider(bad_first=False) as provider:
        job = execute(page, job_store, provider, payload)
    assert job["status"] == "failed" and job["result"] is None
    assert editor.load_editor(run, scene["id"]) == before


def test_baseline_change_after_preview_returns_stale_not_delivery(page, job_store, monkeypatch):
    from html_agent_execution import Execution
    from html_visual_store import save_scene
    original = Execution.call
    def call(self, name, args):
        response = original(self, name, args)
        if name == "check_candidate" and self.checked.get("passed"):
            doc = editor.load_editor(self.run, self.slide)
            doc["scene"]["name"] += " changed"
            save_scene(self.run, self.slide, doc["scene"], doc["revision"])
        return response
    monkeypatch.setattr(Execution, "call", call)
    with ScriptedProvider(bad_first=False) as provider:
        job = execute(page, job_store, provider)
    assert job["status"] == "failed" and job["error"]["code"] == "stale_input", job
    assert job["result"] is None


def test_real_sdk_with_actual_original_dom_and_screenshots(page, job_store, monkeypatch):
    monkeypatch.setattr(repair, "evidence", REAL_EVIDENCE)
    before = editor.load_editor(page[0], page[1]["id"])
    with ScriptedProvider(bad_first=False) as provider:
        job = execute(page, job_store, provider)
    assert job["status"] == "succeeded", {"error": job["error"], "usage": job["usage"]}
    assert job["result"]["preview"]["comparison"]["after"]
    assert job["result"]["preview"]["review"]["passed"]
    assert editor.load_editor(page[0], page[1]["id"]) == before


def test_audio_bound_animation_task_runs_through_same_sdk(page, job_store):
    import hashlib
    import io
    import wave
    import html_visual_store as store
    run, original = page
    scene = copy.deepcopy(original)
    scene.update(version="0.7.0", initialVisibleIds=[])
    for index, action in enumerate(scene["motion"]): action["actionId"] = f"animation-{index}"
    store.save_scene(run, scene["id"], scene, 1)
    beats = editor.beats_for(run, scene["id"])
    binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_ids",
        "sourceBeats": [{"id": b["id"], "spoken_text": b["text"], "spoken_text_sha256": hashlib.sha256(b["text"].encode()).hexdigest()} for b in beats],
        "actions": {a["actionId"]: {"beatId": f"b{min(2, int(a['startMs'] // 6000)) + 1}", "edge": "start",
                    "offsetMs": int(a["startMs"] - min(2, int(a["startMs"] // 6000)) * 6000)} for a in scene["motion"]}}
    editor.binding_path(run, scene["id"]).write_text(json.dumps(binding), encoding="utf-8")
    folder = run / "slides" / scene["id"]; folder.mkdir(parents=True)
    (folder / "audio_timeline.json").write_text(json.dumps({"duration_sec": 18, "segments": [
        {"id": b["id"], "text": b["text"], "start": index*6, "end": (index+1)*6} for index,b in enumerate(beats)]}), encoding="utf-8")
    voice = io.BytesIO()
    with wave.open(voice, "wb") as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(8000); output.writeframes(b"\0\0"*8000*18)
    (folder / "voice.mp3").write_bytes(voice.getvalue())
    (folder / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:06,000\n测试\n", encoding="utf-8")
    action = next(a for a in scene["motion"] if a["targetId"] == "headline")
    operation = {"targetId": "headline", "kind": "set_binding", "action": action["type"], "actionId": action["actionId"], "values": {"offsetMs": 100}}
    payload = request(page); payload.task.task_type = "animation_repair"; payload.task.expected_revision = 2
    payload.task.font_requirements = []; payload.task.goal = "将标题入场相对原句偏移调整为100ms"
    before = editor.load_editor(run, scene["id"])
    with ScriptedProvider(bad_first=False, operation=operation) as provider:
        job = execute((run, scene), job_store, provider, payload)
    assert job["status"] == "succeeded", job["error"]
    assert editor.load_editor(run, scene["id"]) == before


def test_provider_error_is_not_retried_or_marked_success(page, job_store):
    with ScriptedProvider(http_error=True) as provider:
        job = execute(page, job_store, provider)
    assert len(provider.requests) == 1
    assert job["status"] == "failed" and job["error"]["code"] == "provider_error"
    assert job["result"] is None


def test_tool_budget_is_separate_and_unregistered_tools_cannot_run(page, job_store):
    payload = request(page); payload.limits.max_tool_calls = 1
    with ScriptedProvider() as provider:
        job = execute(page, job_store, provider, payload)
    assert job["status"] == "failed" and job["error"]["code"] == "budget_exceeded"
    payload.idempotency_key += "-unknown"; payload.limits.max_model_calls = 2
    with ScriptedProvider(forbidden=True) as provider:
        job = execute(page, job_store, provider, payload)
    assert job["status"] == "failed" and job["result"] is None
    assert job["usage"]["tool_calls"] == 0


def test_cancel_and_timeout_while_queued_make_no_model_call(page, job_store, monkeypatch):
    with ScriptedProvider() as provider:
        payload = request(page); payload.limits.timeout_seconds = 10
        job = jobs.submit(page[0], "project-a", page[1]["id"], payload, provider.model(), store=job_store, launch=False)
        ticks = iter([0, 11, 12])
        monkeypatch.setattr(jobs.time, "monotonic", lambda: next(ticks))
        jobs._work(job_store, page[0], "project-a", page[1]["id"], payload, provider.model(), job["job_id"])
        value = job_store.read("project-a", page[1]["id"], job["job_id"])
        assert value["status"] == "failed" and value["error"]["code"] == "timeout"
        assert not provider.requests


def test_queue_snapshot_and_cancel_publish_race_are_authoritative(page, job_store):
    import html_visual_store as visual
    with ScriptedProvider() as provider:
        payload = request(page)
        job = jobs.submit(page[0], "project-a", page[1]["id"], payload, provider.model(), store=job_store, launch=False)
        doc = editor.load_editor(page[0], page[1]["id"])
        doc["scene"]["name"] += " queued change"
        visual.save_scene(page[0], page[1]["id"], doc["scene"], 1)
        jobs._work(job_store, page[0], "project-a", page[1]["id"], payload, provider.model(), job["job_id"])
        value = job_store.read("project-a", page[1]["id"], job["job_id"])
        assert value["error"]["code"] == "stale_input" and not provider.requests
        payload.idempotency_key += "-race"; payload.task.expected_revision = 2
        race = jobs.submit(page[0], "project-a", page[1]["id"], payload, provider.model(), store=job_store, launch=False)
        job_store.update("project-a", page[1]["id"], race["job_id"], cancel_requested=True)
        value = job_store.update("project-a", page[1]["id"], race["job_id"], status="succeeded", result={"unwanted": True})
        assert value["status"] == "cancelled" and value["result"] is None


def test_same_model_turn_cannot_claim_review_of_images_it_has_not_received(page, tmp_path):
    from html_agent_execution import Execution, ExecutionError
    from checks.test_html_external_package import export, result
    packet = export(page, require_verification=True, require_image_understanding=True)
    execution = Execution(page[0], "project-a", page[1]["id"], packet, request(page).limits, tmp_path / "tool-session")
    execution.epoch = 1
    for name in ("ENTRY.md", "decision-input.json", "constraints.json", "task.json", "content.json"):
        execution.call("read_material", {"name": name})
    execution.call("view_image", {"name": packet["context"]["evidence"]["screenshots"][0]["file"]})
    proposed = result(packet).model_dump(mode="json")
    execution.call("check_candidate", {"result": proposed})
    execution.call("view_image", {"name": next(iter(execution.images))})
    with pytest.raises(ExecutionError, match="实际查看"):
        execution.call("submit_result", {"result": proposed, "baseline_notes": "synthetic", "candidate_notes": "synthetic"})
    assert execution.final is None
