"""M4/M5 genuine Pi SDK transport, original validators, and publication fences."""
import copy
from dataclasses import replace
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from types import SimpleNamespace
import uuid

import pytest
from PIL import Image

from database import Project, SessionLocal
from html_agent_execution import ExecutionError
from html_agent_models import AgentLimits
from html_agent_store import AgentJobStore
from html_agent_workflow_models import WorkflowRequest
import html_agent_workflows as workflows
from html_pi_json import PiJSON
from checks.test_html_pi_agent import ScriptedProvider, execute, request
from checks.test_html_external_package import page as page
from checks.test_html_e_production import case as case
from checks.test_html_production_stages import stage as stage
import html_scene_editing as editor


class JSONProvider(ScriptedProvider):
    def __init__(self, result, *, fail=False):
        self.requests = []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def handle(self):
                try: super().handle()
                except (ConnectionResetError, BrokenPipeError): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.requests.append(body)
                if fail:
                    self.send_response(503); self.end_headers(); return
                self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
                data = result(body) if callable(result) else result
                chunk = {"id": "json-test", "object": "chat.completion.chunk", "created": 0, "model": "local-test",
                    "choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [{"index": 0,
                        "id": "submit", "type": "function", "function": {"name": "submit_json", "arguments": json.dumps({"result": data})}}]}, "finish_reason": None}]}
                end = {"id": "json-test", "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
                       "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
                for value in (chunk, end): self.wfile.write(("data: " + json.dumps(value) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)


def project_for(run, pid=None):
    pid = pid or "pi-workflow-" + uuid.uuid4().hex
    with SessionLocal() as db:
        project = Project(id=pid, name="真实输入测试", run_dir=str(run), visual_backend="html", account_id="default")
        db.add(project); db.commit(); db.refresh(project); db.expunge(project)
        return project


def test_json_sdk_attaches_real_image_and_shares_calls_across_stages(tmp_path):
    image = tmp_path / "real.png"; Image.new("RGB", (100, 60), "gray").save(image)
    with JSONProvider({"answer": "固定结果"}) as provider:
        client = PiJSON(provider.model(), tmp_path / "runtime", limits=AgentLimits(max_model_calls=2))
        for _ in range(2):
            assert client(system_prompt="按图返回JSON", user_prompt="真实阶段输入", image_paths=[image]) == {"answer": "固定结果"}
        with pytest.raises(ExecutionError, match="共享模型预算"):
            client(system_prompt="禁止第三次付费", user_prompt="不可调用")
        assert len(provider.requests) == 2
        assert 'data:image/png;base64,' in json.dumps(provider.requests)
        assert {x["function"]["name"] for x in provider.requests[0]["tools"]} == {"submit_json"}
        assert client.usage["model_calls"] == 2 and client.usage["tokens"] == 30


def test_sdk_stream_progress_counts_arguments_without_saving_their_contents(tmp_path):
    events = []
    with JSONProvider({'answer': 'private-result-do-not-log'}) as provider:
        client = PiJSON(provider.model(), tmp_path)
        assert client(system_prompt='返回JSON', user_prompt='固定', on_stream_progress=events.append) == {'answer': 'private-result-do-not-log'}
    trace = json.loads((tmp_path / 'stream-1.json').read_text(encoding='utf-8'))
    assert trace['state'] == 'completed'
    assert trace['first_event_seconds'] is not None and trace['first_content_seconds'] is not None
    assert trace['tool_argument_chars'] > 0
    assert 'private-result-do-not-log' not in json.dumps(events) + json.dumps(trace)


def test_stream_progress_callback_failure_still_reaps_sdk_process(tmp_path, monkeypatch):
    import html_pi_json as adapter
    processes = []
    original = adapter.subprocess.Popen
    def capture(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(adapter.subprocess, 'Popen', capture)
    def stop_on_output(value):
        if value['state'] == 'outputting':
            raise RuntimeError('local stop')
    with JSONProvider({'answer': 'complete'}) as provider:
        with pytest.raises(RuntimeError, match='local stop'):
            PiJSON(provider.model(), tmp_path)(system_prompt='返回JSON', user_prompt='固定', on_stream_progress=stop_on_output)
        assert len(provider.requests) == 1
    assert processes and all(p.poll() is not None and p.stdin.closed and p.stdout.closed for p in processes)


def test_json_provider_failure_has_no_automatic_retry(tmp_path):
    with JSONProvider({}, fail=True) as provider:
        with pytest.raises(ExecutionError):
            PiJSON(provider.model(), tmp_path)(system_prompt="返回JSON", user_prompt="固定")
        assert len(provider.requests) == 1


def test_glm_native_payload_preserves_thinking_and_65536_budget(tmp_path):
    with JSONProvider({"answer": "完整结果"}) as provider:
        model = replace(provider.model(), model="glm-5.3-flash", max_tokens=65536, temperature=1.0)
        result = PiJSON(model, tmp_path)(system_prompt="返回JSON", user_prompt="固定输入")
        assert result == {"answer": "完整结果"}
        body = provider.requests[0]
        assert body["model"] == "glm-5.3-flash"
        assert body["thinking"] == {"type": "enabled"}
        assert body["max_tokens"] == 65536
        assert body["temperature"] == 1.0
        assert "max_completion_tokens" not in body
        assert "reasoning_effort" not in body
        assert len(provider.requests) == 1


def test_json_stage_deadline_is_stricter_than_whole_job_without_retry(tmp_path):
    def slow(body):
        time.sleep(4)
        return {"content": "迟到结果不能交付"}
    with JSONProvider(slow) as provider:
        client = PiJSON(provider.model(), tmp_path, limits=AgentLimits(timeout_seconds=10))
        started = time.monotonic()
        with pytest.raises(ExecutionError, match="超时"):
            client(system_prompt="返回JSON", user_prompt="固定输入", request_timeout=2)
        assert time.monotonic() - started < 6
        assert len(provider.requests) <= 1
        trace = json.loads((tmp_path / 'stream-1.json').read_text(encoding='utf-8'))
        assert trace['state'] == 'failed' and trace['failure_reason'] == 'timeout'
        assert trace['submission_state'] == 'unverified'


def test_preauthorized_repair_saves_ai_version_and_receipt(page):
    run, scene = page
    project_for(run, "project-a")
    store = AgentJobStore(SessionLocal)
    with ScriptedProvider(bad_first=False) as provider:
        result = execute(page, store, provider, request(page, delivery_policy="save_revision"))
    assert result["status"] == "succeeded", result["error"]
    assert result["result"]["saved"] and result["result"]["saved_revision"] == 2
    assert editor.load_editor(run, scene["id"])["revision"] == 2
    assert editor.read_json(editor.edit_path(run, scene["id"]))["last_origin"] == "ai"
    assert len(editor.saved_versions(run, scene["id"])) == 2
    receipt = editor.read_json(run / "planning/html_visual/pi-commits" / f'{result["job_id"]}.json')
    assert receipt["state"] == "committed"
    assert not result["can_cancel"]


def test_commit_fence_ignores_late_cancel_and_recovery_requires_inspection(tmp_path):
    store = AgentJobStore(SessionLocal)
    payload = WorkflowRequest(idempotency_key="commit-fence-test", task={"task_type": "article.generate", "topic": "测试"})
    row, _ = store.create("fence-project", workflows.SCOPE, payload, {})
    store.begin_commit("fence-project", workflows.SCOPE, row["job_id"])
    cancelled = store.update("fence-project", workflows.SCOPE, row["job_id"], cancel_requested=True)
    assert not cancelled["can_cancel"]
    assert not store.read("fence-project", workflows.SCOPE, row["job_id"], private=True)["payload"]["cancel_requested"]
    store.recover()
    assert store.read("fence-project", workflows.SCOPE, row["job_id"])["error"]["code"] == "save_outcome_unknown"


def test_article_job_freezes_input_idempotency_and_preserves_author(tmp_path, monkeypatch):
    project = project_for(tmp_path)
    monkeypatch.setattr("article_service.read_project_article_generation_system_content", lambda p: "生成完整文章")
    article = tmp_path / "inputs/article.md"; article.parent.mkdir(); article.write_text("原始正式文章", encoding="utf-8")
    store = AgentJobStore(SessionLocal)
    payload = WorkflowRequest(idempotency_key="article-fixed-input", task={"task_type": "article.generate", "topic": "新主题"})
    with JSONProvider({"content": "# 新主题\n\n完整文章候选。"}) as provider:
        job = workflows.submit(project, payload, provider.model(), store=store, launch=False)
        assert workflows.submit(project, payload, None, store=store, launch=False) == job
        metadata = store.read(project.id, workflows.SCOPE, job["job_id"], private=True)["payload"]["model"]
        workflows.work(store, tmp_path, project.id, payload, provider.model(), job["job_id"], metadata)
        result = store.read(project.id, workflows.SCOPE, job["job_id"])
        assert result["status"] == "succeeded", result["error"]
        assert result["result"]["candidate"]["content"].startswith("# 新主题")
        assert not result["result"]["saved"]
        assert article.read_text(encoding="utf-8") == "原始正式文章"
        assert len(provider.requests) == 1
        assert "local-test-secret" not in json.dumps(result)


def test_source_changed_before_queued_job_never_calls_model(tmp_path, monkeypatch):
    project = project_for(tmp_path)
    monkeypatch.setattr("article_service.read_project_article_generation_system_content", lambda p: "生成文章")
    store = AgentJobStore(SessionLocal)
    payload = WorkflowRequest(idempotency_key="stale-fixed-input", task={"task_type": "article.generate", "topic": "新主题"})
    with JSONProvider({"content": "不应调用"}) as provider:
        job = workflows.submit(project, payload, provider.model(), store=store, launch=False)
        metadata = store.read(project.id, workflows.SCOPE, job["job_id"], private=True)["payload"]["model"]
        (tmp_path / "inputs").mkdir(); (tmp_path / "inputs/article.md").write_text("人工修改", encoding="utf-8")
        workflows.work(store, tmp_path, project.id, payload, provider.model(), job["job_id"], metadata)
        assert store.read(project.id, workflows.SCOPE, job["job_id"])["error"]["code"] == "stale_input"
        assert not provider.requests


def test_article_invalid_known_result_gets_one_bounded_feedback_repair(tmp_path, monkeypatch):
    project = project_for(tmp_path)
    monkeypatch.setattr("article_service.read_project_article_generation_system_content", lambda p: "生成完整文章")
    store = AgentJobStore(SessionLocal)
    payload = WorkflowRequest(idempotency_key="article-bounded-repair", task={"task_type": "article.generate", "topic": "主题"})
    replies = iter([{"content": ""}, {"content": "依据正式要求修复后的文章"}])
    with JSONProvider(lambda body: next(replies)) as provider:
        job = workflows.submit(project, payload, provider.model(), store=store, launch=False)
        metadata = store.read(project.id, workflows.SCOPE, job["job_id"], private=True)["payload"]["model"]
        workflows.work(store, tmp_path, project.id, payload, provider.model(), job["job_id"], metadata)
        final = store.read(project.id, workflows.SCOPE, job["job_id"])
        assert final["status"] == "succeeded", final["error"]
        assert final["usage"]["model_calls"] == 2 and final["usage"]["candidate_rounds"] == 2
        assert len(provider.requests) == 2
        assert "validation_feedback" in json.dumps(provider.requests[1])


def test_storyboard_uses_original_normalizer_and_rejects_qualifier_loss():
    inputs = {"title": "示例", "article": "这不是适用于所有地区和岗位的统一标准。", "source_identity": "source"}
    bad = {"slides": [{"slide_id": "slide_001", "narration": "没有统一标准。"}]}
    with pytest.raises(ExecutionError, match="限定范围"):
        workflows.validate_candidate("storyboard.plan", bad, inputs)
    good = copy.deepcopy(bad); good["slides"][0]["narration"] = inputs["article"]
    assert workflows.validate_candidate("storyboard.plan", good, inputs)["candidate"]["slides"][0]["slide_title"] == "第 1 页"


def test_visual_storyboard_checks_original_full_narration_mapping():
    inputs = {"phase": "visual", "source_identity": "source", "script": {
        "slides": [{"slide_id": "slide_001", "narration": "原文第一句。原文第二句。"}]}}
    with pytest.raises(ValueError):
        workflows.validate_candidate("storyboard.plan", {"slides": []}, inputs)
    plan = {"slides": [{"slide_id": "slide_001", "visual_elements": [
        {"element_id": "el_001", "role": "title", "visual_type": "text", "visual_description": "标题", "narration": "原文第一句。"},
        {"element_id": "el_002", "role": "body", "visual_type": "text", "visual_description": "原文", "narration": "原文第二句。"}]}]}
    assert workflows.validate_candidate("storyboard.plan", plan, inputs)["phase"] == "visual"


def test_visual_input_preserves_saved_script_and_includes_requested_changes(tmp_path, monkeypatch):
    project = project_for(tmp_path)
    (tmp_path / "inputs").mkdir(); (tmp_path / "planning").mkdir()
    (tmp_path / "inputs/article.md").write_text("正式原文", encoding="utf-8")
    script = {"title": "标题", "slides": [{"slide_id": "slide_001", "slide_title": "页标题", "narration": "正式完整讲稿"}]}
    (tmp_path / "planning/slide_script_plan.json").write_text(json.dumps(script), encoding="utf-8")
    monkeypatch.setattr("storyboard_prompt_templates.step2_prompt_response", lambda project: {
        "compatibility": {"compatible": True}, "composed": {"script_system_content": "原讲稿规则", "visual_system_content": "原可视化规则"}})
    payload = WorkflowRequest(idempotency_key="visual-requirement-input", task={
        "task_type": "storyboard.plan", "phase": "visual", "requirement": "画面文字简练，保留原讲稿"})
    inputs = workflows.prepare(project, payload.task)
    assert inputs["script"] == script and "画面文字简练" in inputs["prompt"]
    assert "正式完整讲稿" in inputs["prompt"]


def test_batch_consumes_parent_budget_and_preserves_partial_outcomes(tmp_path, monkeypatch):
    store = AgentJobStore(SessionLocal)
    payload = WorkflowRequest(idempotency_key="batch-budget-fixed", limits=AgentLimits(max_model_calls=2), task={
        "task_type": "scene.batch_repair", "items": [{"slide_id": name, "task": {
            "task_type": "static_repair", "goal": "调整标题", "scope": ["headline"], "expected_revision": 1}}
            for name in ("a", "b", "c")]})
    metadata = {"inputs": {"pages": {x: "same" for x in ("a", "b", "c")}}}
    monkeypatch.setattr(workflows.jobs, "baseline_identity", lambda *a: "same")
    parent, _ = store.create("batch-project", workflows.SCOPE, payload, {})
    calls = []
    def submit(run, project, slide, req, model, **kw):
        calls.append(req.limits.max_model_calls)
        return store.create(project, slide, req, {})[0]
    def work(store, run, project, slide, req, model, job_id, **kw):
        store.update(project, slide, job_id, status="failed", usage={"model_calls": 2, "tool_calls": 1,
            "tokens": None, "cost": None}, error={"code": "fixture_failure"})
    monkeypatch.setattr(workflows.jobs, "submit", submit)
    monkeypatch.setattr(workflows.jobs, "_work", work)
    usage = {"model_calls": 0, "tool_calls": 0, "tokens": None, "cost": None}
    result = workflows.batch(store, tmp_path, "batch-project", payload, None, parent["job_id"], metadata, usage, lambda: None)
    assert calls == [2] and usage["model_calls"] == 2
    assert [x["status"] for x in result] == ["failed", "not_started", "not_started"]


def test_pi_generation_requires_selected_design_and_typed_budgets():
    from html_production_models import HtmlProduceRequest
    with pytest.raises(ValueError): HtmlProduceRequest(runner="pi")
    with pytest.raises(ValueError): HtmlProduceRequest(runner="pi", design_candidate_key="a"*64, pi_limits={"max_model_calls": 99})
    valid = HtmlProduceRequest(runner="pi", design_candidate_key="a"*64)
    assert valid.max_image_calls == 0 and valid.pi_limits.max_model_calls == 12


def test_pi_image_budget_blocks_new_calls_and_preserves_original_cache(stage):
    from checks.test_html_e_production import png
    import html_task_store
    calls = []
    provider = stage.wrap(lambda *a, **kw: calls.append(1) or png(), "image")
    stage.image_limit = 0
    with pytest.raises(html_task_store.HtmlTaskError, match="IMAGE_BUDGET_EXCEEDED"):
        provider("first")
    assert not calls
    stage.image_limit = 1
    first = provider("first")
    assert provider("first") == first
    with pytest.raises(html_task_store.HtmlTaskError, match="IMAGE_BUDGET_EXCEEDED"):
        provider("second")
    assert calls == [1]


@pytest.mark.parametrize("through_jobs", [False, True])
def test_pi_selected_design_runs_original_production_and_records_restorable_ai_version(case, through_jobs):
    from html_production_service import produce_scene
    from checks.html_design_agent_fixture import response_for
    def respond(body):
        message = next(x for x in body["messages"] if x["role"] == "user")["content"]
        if isinstance(message, list): message = next(x["text"] for x in message if x["type"] == "text")
        data = json.loads(message)
        payload = json.loads(data["input"])
        if "actual_geometry" in payload:
            return {"status": "unchanged", "message": "脚本供应商仅验证工程接线，不代表真实视觉判断"}
        prefix = "design_fidelity_review-test" if "review_checklist" in payload else "design_understanding-test"
        answer = response_for({"artifact_prefix": prefix, "user_prompt": data["input"]})
        if prefix.startswith("design_fidelity") and not payload.get("review_checklist"):
            return {"status": "unchanged", "message": "脚本供应商仅验证工程接线，不代表真实视觉判断"}
        return answer
    with JSONProvider(respond) as provider:
        from project_model_binding_service import FrozenProjectModels
        frozen = FrozenProjectModels(0, provider.model(), provider.model())
        first = produce_scene(case.contract, run_dir=case.run, deps=case.deps, provider=case.provider,
                              model_summary=frozen.summary() if through_jobs else {})
        (case.run / "planning/visual_contract.json").write_text(json.dumps({"slides": [case.contract]}), encoding="utf-8")
        options={"runner": "pi", "design_candidate_key": first["design"]["key"], "max_image_calls": 1}
        if through_jobs:
            from html_workflow_jobs import HtmlWorkflowJobs
            import html_task_store
            project = project_for(case.run)
            calls = []
            workflow = HtmlWorkflowJobs(SessionLocal, case.deps, provider=case.provider,
                executor=SimpleNamespace(submit=lambda *args: calls.append(args)), freeze_models=lambda project: frozen)
            with SessionLocal() as db:
                task = workflow.submit(db, db.get(Project, project.id), case.contract, options)
            fn, *args = calls[0]; fn(*args)
            with SessionLocal() as db:
                value = html_task_store._job_to_dict(html_task_store._job(db, task["id"]))
            assert value["status"] == "succeeded", value
            result = value["result"]
        else:
            pi = PiJSON(provider.model(), case.run / "pi-runtime")
            deps = replace(case.deps, json_generator=pi, planning_generator=pi)
            result = produce_scene(case.contract, run_dir=case.run, deps=deps, provider=case.provider, options=options)
        assert result["saved"]["changed"] and result["review"]["passed"]
        assert len(provider.requests) >= 3
        assert 'data:image/png;base64,' in json.dumps(provider.requests)
    versions = editor.saved_versions(case.run, case.contract["slide_id"])
    assert versions == [{"revision": result["saved"]["revision"]}]
    saved = editor.saved_versions(case.run, case.contract["slide_id"], versions[0]["revision"])
    assert saved["scene"] == result["scene"]
    provenance = editor.read_json(case.run / f'planning/html_visual/production-provenance-{case.contract["slide_id"]}.json')
    assert provenance["origin"] == "ai" and provenance["runner"] == "pi"
    assert not (case.run / f'planning/html_visual/approval-{case.contract["slide_id"]}.json').exists()
