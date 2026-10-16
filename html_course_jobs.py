"""A05 durable course coordinator over the existing LocalJob and stage services."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import threading
import time

from account_context import account_scope, get_current_account_id
from artifact_fingerprint import sha256_json
import html_task_store as store

TYPE = "html_course_produce"
STAGES = [("storyboard", "内容规划"), ("html_pages", "设计与HTML"),
          ("narration", "旁白"), ("tts", "真实音频"),
          ("semantic", "逐句语义审核"), ("approvals", "当前签收"), ("render", "作品输出")]


class CourseBoundary(Exception):
    def __init__(self, state, stage, message, slide=None, *, outcome=None):
        self.state, self.stage, self.message, self.slide = state, stage, message, slide
        self.outcome = outcome


class HtmlCourseJobs:
    def __init__(self, session_factory, actions, executor=None, poll_seconds=1):
        self.sessions, self.actions = session_factory, actions
        self.executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="html-course")
        self.poll_seconds = poll_seconds
        self.lock = threading.RLock()
        self.futures = {}

    def latest(self, db, project):
        from database import LocalJob
        return db.query(LocalJob).filter(LocalJob.project_id == project.id, LocalJob.job_type == TYPE).order_by(LocalJob.created_at.desc()).first()

    def status(self, project):
        with self.lock, self.sessions() as db:
            job = self.latest(db, project)
            if job is None:
                return {"success": True, "status": {"backend": "html", "status": "idle", "stages": []}}
            future = self.futures.get(job.id)
            if job.status in store.ACTIVE_STATUSES and (future is None or future.done()):
                store._transition(db, job, store.ACTIVE_STATUSES, {"status": "interrupted", "error": "课程执行已中断；显式继续将核对原子任务"})
            result = self.view(job)
            if (self.actions.identity(project) != job.get_payload()["input"]["identity"]
                    or (job.get_payload().get("contract") and self.actions.contract(project) != job.get_payload()["contract"])):
                result.update(status="paused", historical=True, message="课程输入、配置、模型或代码已变化；原记录仅为历史")
            elif job.status == "succeeded" and not self.actions.completed(project, job.get_payload().get("result")):
                result.update(status="paused", historical=True, message="当前输出文件或签收已失效；原成功记录保留")
            return {"success": True, "status": result}

    def view(self, job):
        payload = job.get_payload()
        ledger = payload.get("course_stages", {})
        return {"backend": "html", "job_id": job.id, "run_id": job.id, "status": "completed" if job.status == "succeeded" else job.status,
                "current_stage": job.stage, "message": payload.get("message") or job.error or "",
                "review_checkpoint": payload.get("checkpoint", ""), "slide_id": payload.get("slide_id"),
                "stages": [{"id": key, "name": title, "status": ledger.get(key, {}).get("state", "pending"), "message": ledger.get(key, {}).get("message", "")} for key, title in STAGES],
                "children": payload.get("children", {}), "result": payload.get("result"), "historical": False}

    def start(self, project, payload=None):
        payload = payload or {}
        if payload.get("stop_at"):
            raise store.HtmlTaskError("HTML课程使用固定的逐页设计和签收停点；请在原阶段入口审阅后继续", 409)
        if payload.get("mode", "resume") != "resume" or payload.get("start_from"):
            raise store.HtmlTaskError("HTML课程仅继续原任务；修改输入后开始新版本，不能从任意阶段跳过门禁", 409)
        identity = self.actions.identity(project)
        with self.lock, self.sessions() as db:
            job = self.latest(db, project)
            if job and (job.get_payload()["input"]["identity"] != identity or (job.get_payload().get("contract") and self.actions.contract(project) != job.get_payload()["contract"])):
                if job.status in store.ACTIVE_STATUSES:
                    raise store.HtmlTaskError("原课程仍在运行，先暂停再使用新输入", 409)
                job = None
            if job and job.status == "cancelled":
                raise store.HtmlTaskError("已取消课程不会恢复", 409)
            if job and job.status == "succeeded":
                if not self.actions.completed(project, job.get_payload().get("result")):
                    raise store.HtmlTaskError("已有输出或签收已失效，请先修复当前输入", 409)
                return {"success": True, "already_running": False, "status": self.view(job)}
            if job is None:
                task = store.submit_task(db, project_id=project.id, task_type=TYPE, submission_key=sha256_json({"identity": identity, "contract": self.actions.contract(project)}), payload={"identity": identity, "account_id": get_current_account_id()})
                job = store._job(db, task["id"])
            future = self.futures.get(job.id)
            if future and not future.done():
                return {"success": True, "already_running": True, "status": self.view(job)}
            value = job.get_payload()
            stopped_storyboard = value.get("production_stages", {}).get("storyboard", {})
            if stopped_storyboard.get("state") == "content_review":
                review = getattr(self.actions, "script_review", lambda p: None)(project)
                if not review or review["status"] != "resolved" or review["stale"]:
                    raise store.HtmlTaskError("SCRIPT_QUALIFIER_REVIEW_REQUIRED：请先在分镜页修正并保存当前讲稿，再继续原课程", 409)
            if stopped_storyboard.get("state") in {"cancelled", "busy"} and not self.actions.contract(project):
                raise store.HtmlTaskError("STORYBOARD_REVIEW_REQUIRED：分镜已停止或由其他操作占用；请在原分镜入口核实并完成，再继续课程", 409)
            if any(c.get("state") in {"intent", "unknown"} and not c.get("id") for c in value.get("children", {}).values()):
                raise store.HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：子任务提交结果未确认，禁止重复创建", 409)
            if any(c.get("state") in {"intent", "unknown"} for c in value.get("production_stages", {}).values()):
                raise store.HtmlTaskError("EXTERNAL_OUTCOME_UNKNOWN：分镜请求结果未确认，禁止补发", 409)
            value.pop("pause_requested", None)
            for key in ("message", "checkpoint", "slide_id"):
                value.pop(key, None)
            store._transition(db, job, (job.status,), {"status": "queued", "error": None, "finished_at": None, "payload_json": store.json_dumps(value)})
            try:
                self.futures[job.id] = self.executor.submit(self.run, job.id, project.id, get_current_account_id())
            except Exception:
                store._transition(db, job, ("queued",), {"status": "interrupted", "error": "课程线程未启动"})
                raise
            return {"success": True, "started": True, "status": self.view(job)}

    def pause(self, project):
        with self.lock, self.sessions() as db:
            job = self.latest(db, project)
            if job and job.status in store.ACTIVE_STATUSES:
                data = job.get_payload(); data["pause_requested"] = True
                store._transition(db, job, store.ACTIVE_STATUSES, {"payload_json": store.json_dumps(data)})
        return {**self.status(project), "pause_requested": True}

    def run(self, job_id, project_id, account):
        with account_scope(account), self.sessions() as db:
            from project_path_service import project_or_404
            project = project_or_404(db, project_id)
            store.mark_running(db, job_id)
            def checkpoint():
                db.expire_all()
                current = store._job(db, job_id)
                if current.status != "running" or current.get_payload().get("pause_requested"):
                    raise CourseBoundary("paused", current.stage, "课程已暂停；已有子任务保留")
                if self.actions.identity(project) != current.get_payload()["input"]["identity"]:
                    raise CourseBoundary("paused", current.stage, "课程输入、配置、模型或代码已变化")
                self.actions.check_contract(project, current.get_payload().get("contract"))
                return current
            def save(**values):
                current = checkpoint(); data = current.get_payload(); data.update(values)
                store._transition(db, current, ("running",), {"payload_json": store.json_dumps(data)})
            def stage(name, state="running", message=""):
                current = checkpoint(); data = current.get_payload()
                data.setdefault("course_stages", {})[name] = {"state": state, "message": message}
                store._transition(db, current, ("running",), {"stage": name, "payload_json": store.json_dumps(data)})
            def child(key, submit):
                current = checkpoint(); data = current.get_payload(); record = data.get("children", {}).get(key)
                if record is None:
                    data.setdefault("children", {})[key] = {"state": "intent"}
                    # Submission intent survives a crash before the child ID arrives.
                    store._transition(db, current, ("running",), {"payload_json": store.json_dumps(data)})
                    result = submit()
                    db.expire_all()
                    current = store._job(db, job_id)
                    data = current.get_payload()
                    data["children"][key] = {"state": "returned", "id": result["id"]}
                    store._transition(db, current, ("running",), {"payload_json": store.json_dumps(data)})
                    checkpoint()
                    record = data["children"][key]
                if not record.get("id"):
                    raise CourseBoundary("failed", key, "EXTERNAL_OUTCOME_UNKNOWN：不能重新创建子任务")
                resumed = False
                while True:
                    checkpoint()
                    result = self.actions.child(db, project, record["id"])
                    if result["status"] in ("queued", "running", "rendering"):
                        time.sleep(self.poll_seconds); continue
                    if result["status"] in ("succeeded", "completed"):
                        return result
                    if result["status"] == "cancelled":
                        raise CourseBoundary("paused", store._job(db, job_id).stage,
                                             "原子任务已取消；课程暂停，保留原任务，不自动复活或创建替代请求")
                    # Existing HTML resume verifies original snapshots/unknown outcomes.
                    if result.get("can_resume") and not resumed:
                        self.actions.resume_child(db, project, record["id"])
                        resumed = True
                        continue
                    raise CourseBoundary("failed", key, result.get("error") or "原子任务未成功；请核验原任务，不能创建替代请求")
            try:
                stage("storyboard")
                current = checkpoint().get_payload()
                contract = self.actions.contract(project)
                if not contract:
                    prior = checkpoint().get_payload().get("production_stages", {}).get("storyboard", {})
                    count = int(prior.get("attempts", 0)) + 1
                    if count > 3:
                        raise CourseBoundary("failed", "storyboard", "分镜制作已达三次预算；先核验当前输入和结果")
                    save(production_stages={"storyboard": {"state": "intent", "attempts": count}})
                    self.actions.storyboard(db, project)
                    db.expire_all(); current = store._job(db, job_id); data = current.get_payload()
                    data["production_stages"] = {"storyboard": {"state": "returned", "attempts": count}}
                    store._transition(db, current, ("running",), {"payload_json": store.json_dumps(data)})
                    contract = self.actions.contract(project)
                if not contract:
                    raise CourseBoundary("failed", "storyboard", "分镜为空")
                save(contract=contract)
                stage("storyboard", "done")
                stage("html_pages")
                for slide in contract["slides"]:
                    checkpoint(); sid = slide["slide_id"]
                    if not self.actions.scene_ready(project, slide):
                        prepare = getattr(self.actions, "preflight_page", None)
                        if prepare is not None:
                            prepare(project, sid)
                        result = child("html:"+sid, lambda s=slide: self.actions.produce(db, project, s))
                        if result.get("result", {}).get("stage") == "design_review":
                            # Reconstruction is submitted by the actual per-page design confirmation.
                            result = self.actions.latest_page(db, project, sid)
                            if not self.actions.scene_ready(project, slide):
                                if result and result["status"] in store.ACTIVE_STATUSES:
                                    raise CourseBoundary("paused", "html_pages", "设计已确认，还原子任务正在运行；完成后继续", sid)
                                raise CourseBoundary("waiting_for_review", "html_pages", "请在本页确认设计并完成受控还原", sid)
                        if not self.actions.scene_ready(project, slide):
                            raise CourseBoundary("failed", "html_pages", "当前场景未通过来源/语义结构检查", sid)
                stage("html_pages", "done")
                stage("narration")
                self.actions.narration(db, project)
                stage("narration", "done")
                stage("tts")
                if not self.actions.audio_ready(project, contract):
                    child("tts", lambda: self.actions.tts(db, project))
                if not self.actions.audio_ready(project, contract):
                    raise CourseBoundary("failed", "tts", "音频文件或当前TTS输入未就绪")
                stage("tts", "done")
                stage("semantic")
                for slide in contract["slides"]:
                    sid = slide["slide_id"]; checkpoint()
                    qa = self.actions.semantic_status(project, sid)
                    if qa.get("semantic") in ("stale_or_missing", None):
                        child("semantic:"+sid, lambda s=sid: self.actions.semantic(db, project, s))
                        qa = self.actions.semantic_status(project, sid)
                    if qa.get("engineering") != "passed" or qa.get("semantic") == "failed":
                        raise CourseBoundary("failed", "semantic", "逐句工程或语义检查失败；请修复该页", sid)
                stage("semantic", "done")
                stage("approvals")
                if not self.actions.approved(project, contract):
                    raise CourseBoundary("waiting_for_review", "approvals", "请完成当前HTML视觉、音频及逐句语义人工签收")
                stage("approvals", "done")
                stage("render")
                output = child("render", lambda: self.actions.render(db, project))
                if not self.actions.completed(project, output):
                    raise CourseBoundary("failed", "render", "当前输出文件或批准已失效")
                stage("render", "done")
                checkpoint(); store.mark_succeeded(db, job_id, output)
            except CourseBoundary as boundary:
                db.rollback(); current = store._job(db, job_id); data = current.get_payload()
                data.update(message=boundary.message, slide_id=boundary.slide,
                            checkpoint={"html_pages": "image_review", "tts": "audio_review", "approvals": "audio_review"}.get(boundary.stage, ""))
                if boundary.stage == "storyboard" and boundary.outcome in {"cancelled", "busy", "content_review"}:
                    data.setdefault("production_stages", {}).setdefault("storyboard", {}).update(
                        state=boundary.outcome, requires_review=True)
                    if boundary.outcome == "content_review":
                        data["checkpoint"] = "script_review"
                data.setdefault("course_stages", {}).setdefault(boundary.stage, {}).update(state=boundary.state, message=boundary.message)
                if current.status == "running":
                    store._transition(db, current, ("running",), {"status": boundary.state, "stage": boundary.stage, "payload_json": store.json_dumps(data), "error": boundary.message if boundary.state == "failed" else None, "finished_at": datetime.now()})
            except Exception:
                db.rollback(); current = store._job(db, job_id); data = current.get_payload()
                message = "HTML_COURSE_STAGE_FAILED：请检查当前阶段原任务与配置"
                data.setdefault("course_stages", {}).setdefault(current.stage, {}).update(state="failed", message=message)
                if current.status == "running":
                    store._transition(db, current, ("running",), {"payload_json": store.json_dumps(data)})
                store.mark_failed(db, job_id, message)
