"""Project candidate orchestration; original article/storyboard/repair owners validate."""
import json
from pathlib import Path
import threading
import time

from account_context import account_scope, get_current_account_id
from html_agent_execution import ExecutionError
from html_agent_store import derive_job_id, digest
from pipeline_lifecycle import project_artifact_lock
import html_agent_jobs as jobs

SCOPE = "__project__"
SOURCE_FILES = ("inputs/article.md", "planning/slide_script_plan.json", "planning/slide_visual_plan.json",
                "planning/script_review.json", "planning/step2_prompts.json", "planning/visual_contract.json")


def identity(run, title):
    from hashlib import sha256
    from html_build_snapshot import safe_file
    return digest({"title": title, "files": {name: sha256(safe_file(run, name).read_bytes()).hexdigest()
        if safe_file(run, name).is_file() else None for name in SOURCE_FILES}})


def prepare(project, task):
    """Freeze actual prompts/source; candidate jobs do not migrate or write originals."""
    run = Path(project.run_dir)
    inputs = {"title": project.name, "source_identity": identity(run, project.name)}
    if task.task_type == "article.generate":
        from article_service import read_project_article_generation_system_content, build_article_generation_user_content
        inputs.update(system=read_project_article_generation_system_content(project),
                      prompt=build_article_generation_user_content(task.topic))
    elif task.task_type == "storyboard.plan":
        from storyboard_prompt_templates import step2_prompt_response
        from storyboard_planning import build_step2_script_user_prompt
        article = run / "inputs/article.md"
        if not article.is_file() or article.stat().st_size > 256 * 1024:
            raise ExecutionError("invalid_input", "需要已保存、256KB以内的完整原文")
        text = article.read_text(encoding="utf-8-sig")
        if not text.strip(): raise ExecutionError("invalid_input", "原文不能为空")
        prompts = step2_prompt_response(project)
        if not prompts["compatibility"]["compatible"]:
            raise ExecutionError("invalid_input", "当前分镜Prompt需要升级到现行契约")
        inputs.update(article=text, system=prompts["composed"]["script_system_content"],
            prompt=build_step2_script_user_prompt(project_title=project.name, article_content=text,
                generation_requirement=task.requirement, target_duration_sec=project.target_duration_sec))
        inputs["phase"] = task.phase
        if task.phase == "visual":
            from storyboard_plan_store import saved_script, script_review
            from storyboard_planning import build_step2_visual_user_prompt, script_qualifier_risks
            plan = saved_script(project)
            review = script_review(project, {"title": project.name, "content": text})
            if not plan or (review and review.get("status") == "pending") or script_qualifier_risks(text, plan):
                raise ExecutionError("invalid_input", "先保存并解决正式讲稿的原文限定审阅")
            inputs.update(script=plan, system=prompts["composed"]["visual_system_content"],
                          prompt=build_step2_visual_user_prompt(plan))
            if task.requirement.strip():
                inputs["prompt"] += "\n本轮可视化补充要求（不得改写正式讲稿）：" + task.requirement.strip()
    else:
        inputs["pages"] = {item.slide_id: jobs.baseline_identity(run, item.slide_id) for item in task.items}
    if len(json.dumps(inputs, ensure_ascii=False).encode()) > 1024 * 1024:
        raise ExecutionError("invalid_input", "任务输入超过1MB")
    return inputs


def submit(project, request, model, *, store=None, launch=True):
    store = store or jobs.configure()
    job_id = derive_job_id(project.id, request.idempotency_key)
    try: store.read(project.id, SCOPE, job_id)
    except KeyError: pass
    else: return store.create(project.id, SCOPE, request, {})[0]
    jobs.ready(model, require_images=request.task.task_type == "scene.batch_repair")
    with project_artifact_lock(project.run_dir):
        inputs = prepare(project, request.task)
    metadata = {**model.summary(), "runner_identity": jobs.runner_identity(),
        "account_id": get_current_account_id(), "inputs": inputs}
    job, created = store.create(project.id, SCOPE, request, metadata)
    if launch and created:
        threading.Thread(target=work, args=(store, Path(project.run_dir), project.id,
            request, model, job["job_id"], metadata), daemon=True).start()
    return job


def work(store, run, project_id, request, model, job_id, metadata):
    started = time.monotonic()
    usage = {"model_calls": 0, "tool_calls": 0, "tokens": None, "cost": None}
    items = []
    acquired = False

    def guard():
        row = store.read(project_id, SCOPE, job_id, private=True)
        if row["payload"].get("cancel_requested"): raise ExecutionError("cancelled", "任务已取消")
        if time.monotonic() - started > request.limits.timeout_seconds: raise ExecutionError("timeout", "总任务时限已用完")
        if jobs.runner_identity() != metadata["runner_identity"]: raise ExecutionError("stale_input", "执行器源码已变化")
        if identity(run, metadata["inputs"]["title"]) != metadata["inputs"]["source_identity"]:
            raise ExecutionError("stale_input", "原文或分镜已变化，旧候选不可交付")
        from database import Project
        with store.factory() as db:
            project = db.get(Project, project_id)
            if (not project or project.name != metadata["inputs"]["title"] or project.account_id != metadata["account_id"]
                    or project.visual_backend != "html" or Path(project.run_dir).resolve() != run.resolve()):
                raise ExecutionError("stale_input", "项目身份或目录已变化")

    def record(value):
        usage.update(value)
        store.update(project_id, SCOPE, job_id, usage=usage)

    try:
        with account_scope(metadata["account_id"]):
            guard()
            store.update(project_id, SCOPE, job_id, status="running", progress=5)
            if request.task.task_type == "scene.batch_repair":
                items = batch(store, run, project_id, request, model, job_id, metadata, usage, guard)
                failed = any(item["status"] != "succeeded" for item in items)
                result = {"task_type": request.task.task_type, "items": items,
                          "outcome": "partial_failure" if failed else "all_succeeded", "saved": False}
            else:
                next_guard = 0.0
                while not jobs._slot.acquire(timeout=0.2):
                    # Same backoff rationale as the single-page worker: the
                    # workflow guard hashes full source identity each call.
                    if time.monotonic() >= next_guard:
                        guard()
                        next_guard = time.monotonic() + 1.0
                acquired = True
                from html_pi_json import PiJSON
                pi = PiJSON(model, run / "planning/html_visual/pi-jobs" / job_id,
                    limits=request.limits, checkpoint=guard, record=record, manage_slot=False)
                inputs = metadata["inputs"]
                schema = {"content": "完整Markdown文章"} if request.task.task_type == "article.generate" else {
                    "title": "标题", "slides": [{"slide_id": "slide_001", "slide_title": "页标题", "narration": "完整原文事实与限定"}]}
                if inputs.get("phase") == "visual":
                    schema = {"slides": [{"slide_id": "slide_001", "visual_elements": [
                        {"element_id": "el_001", "role": "title", "visual_type": "text", "visual_description": "正式页标题", "narration": "原讲稿首段"},
                        {"element_id": "el_002", "role": "body", "visual_type": "text", "visual_description": "画面文字", "narration": "原讲稿其余完整片段"}]}]}
                prompt = inputs["prompt"]
                for round_index in range(request.limits.max_candidate_rounds):
                    candidate = pi(system_prompt=inputs["system"], user_prompt=prompt, schema_hint=schema)
                    usage["candidate_rounds"] = round_index + 1
                    try:
                        result = validate_candidate(request.task.task_type, candidate, inputs)
                        break
                    except ValueError as error:
                        # A received, invalid business object is a known outcome.
                        # Provider exceptions never enter this validation repair loop.
                        if round_index + 1 == request.limits.max_candidate_rounds:
                            raise
                        prompt = json.dumps({"original_input": inputs["prompt"], "previous_candidate": candidate,
                            "validation_feedback": str(error)[:2000],
                            "instruction": "依据原文和原校验反馈返回完整修正版；不能更改规则或省略限定。"}, ensure_ascii=False)
            guard()
            usage["elapsed_seconds"] = round(time.monotonic() - started, 3)
            store.update(project_id, SCOPE, job_id, status="succeeded", progress=100,
                         usage=usage, result=result, error=None)
    except Exception as error:
        code = error.code if isinstance(error, ExecutionError) else "invalid_result"
        usage["elapsed_seconds"] = round(time.monotonic() - started, 3)
        try:
            store.update(project_id, SCOPE, job_id, status="cancelled" if code == "cancelled" else "failed",
                usage=usage, result=None,
                error={"code": code, "message": str(error)[:1000] if isinstance(error, ExecutionError)
                    else "候选未通过原业务校验，未改变正式内容", "retryable": False})
        except Exception:
            # Persist failure inside the failure path must not kill the worker
            # silently; startup recovery marks abandoned jobs interrupted.
            import logging
            logging.getLogger(__name__).exception("Pi workflow %s terminal update failed", job_id)
    finally:
        jobs.cleanup_job_folder(run, job_id)
        if acquired: jobs._slot.release()


def validate_candidate(task_type, candidate, inputs):
    if task_type == "article.generate":
        if set(candidate) != {"content"} or not isinstance(candidate["content"], str) or not candidate["content"].strip():
            raise ExecutionError("invalid_result", "文章必须返回唯一的非空content字段")
        if len(candidate["content"].encode()) > 256 * 1024:
            raise ExecutionError("invalid_result", "文章超过256KB")
        return {"task_type": task_type, "candidate": candidate, "saved": False,
                "apply_via": "原文章导入/保存入口", "source_identity": inputs["source_identity"]}
    if inputs.get("phase") == "visual":
        from storyboard_planning import normalize_slide_visual_plan
        plan = normalize_slide_visual_plan(candidate, inputs["script"])
        ids = [x["slide_id"] for x in plan["slides"]]
        if len(ids) != len(set(ids)) or set(ids) != {x["slide_id"] for x in inputs["script"]["slides"]}:
            raise ExecutionError("invalid_result", "可视化页必须与正式讲稿逐页一致")
        return {"task_type": task_type, "phase": "visual", "candidate": plan, "saved": False,
                "source_identity": inputs["source_identity"], "apply_via": "原可视化保存入口"}
    from storyboard_planning import normalize_slide_script_plan, script_qualifier_risks
    plan = normalize_slide_script_plan(candidate, inputs["title"])
    if len(plan["slides"]) > 100:
        raise ExecutionError("invalid_result", "分镜超过100页")
    if len({x["slide_id"] for x in plan["slides"]}) != len(plan["slides"]):
        raise ExecutionError("invalid_result", "分镜页ID重复")
    risks = script_qualifier_risks(inputs["article"], plan)
    if risks: raise ExecutionError("qualifier_risk", "分镜改变原文限定范围，候选不可采用")
    return {"task_type": task_type, "candidate": plan, "saved": False,
            "apply_via": "原讲稿保存入口（继续检查当前审阅与原文限定）",
            "source_identity": inputs["source_identity"], "semantic_approval": "not_requested"}


def batch(store, run, project, request, model, job_id, metadata, usage, guard):
    from html_agent_models import AgentJobRequest, AgentLimits
    results = []
    for index, item in enumerate(request.task.items):
        guard()
        remaining_model = request.limits.max_model_calls - usage["model_calls"]
        remaining_tools = request.limits.max_tool_calls - usage["tool_calls"]
        if remaining_model < 1 or remaining_tools < 1:
            results.append({"slide_id": item.slide_id, "status": "not_started", "error": {"code": "budget_exceeded"}})
            continue
        if jobs.baseline_identity(run, item.slide_id) != metadata["inputs"]["pages"][item.slide_id]:
            results.append({"slide_id": item.slide_id, "status": "failed", "error": {"code": "stale_input"}})
            continue
        limits = AgentLimits(max_model_calls=remaining_model, max_tool_calls=remaining_tools,
            timeout_seconds=request.limits.timeout_seconds, max_candidate_rounds=request.limits.max_candidate_rounds)
        child_request = AgentJobRequest(idempotency_key=f"batch-{job_id[:48]}-{index}", task=item.task,
                                       limits=limits, delivery_policy="candidate")
        child = jobs.submit(run, project, item.slide_id, child_request, model, store=store, launch=False)
        jobs._work(store, run, project, item.slide_id, child_request, model, child["job_id"], parent_guard=guard)
        child = store.read(project, item.slide_id, child["job_id"])
        results.append({"slide_id": item.slide_id, **child})
        for key in ("model_calls", "tool_calls"):
            usage[key] += child["usage"][key]
        if child["usage"].get("tokens") is not None:
            usage["tokens"] = (usage["tokens"] or 0) + child["usage"]["tokens"]
        store.update(project, SCOPE, job_id, usage=usage, partial_items=results,
                     progress=5 + int(85 * (index + 1) / len(request.task.items)))
    return results
