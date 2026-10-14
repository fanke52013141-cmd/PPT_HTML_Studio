"""Production adapters: the course coordinator never calls HTTP or replaces providers."""
from pathlib import Path
import json
from artifact_fingerprint import sha256_json, sha256_file
from html_course_jobs import CourseBoundary, HtmlCourseJobs


class CourseActions:
    def __init__(self, dependencies):
        self.deps = dependencies
        self.root = Path(dependencies.repo_root)

    def services(self, db, project):
        return self.deps.pipeline_service_factory(db, project.id)

    def identity(self, project):
        from project_config_runtime import load_project_config
        from project_model_binding_service import freeze_project_models
        from tts_service import current_tts_cache_key
        article = self.deps.read_project_article_source(project, required=True)
        models = freeze_project_models(project).summary()
        sources = ("html_course_jobs.py", "html_course_runtime.py", "html_production_service.py", "html_workflow_jobs.py", "html_semantic_review_service.py", "html_audio_binder.py", "html_audio_binding_service.py", "tts_service.py", "storyboard_service.py", "storyboard_project_config.py", "storyboard_llm.py")
        return {"article_sha256": sha256_json(article), "config_sha256": sha256_json(load_project_config(project)),
                "models": models, "tts": current_tts_cache_key(project),
                "sources": {s: sha256_file(self.root/s) for s in sources}}

    def contract(self, project):
        path = Path(project.run_dir)/"planning/visual_contract.json"
        if not path.exists():
            return None
        from one_click_resume_policy import has_contract
        if not has_contract(project):
            return None  # Regenerate through the original source-owned storyboard facade.
        result = json.loads(path.read_text(encoding="utf-8"))
        from html_visual_store import validate_slide_id
        slides = result.get("slides")
        if not isinstance(slides, list) or not 1 <= len(slides) <= 40:
            raise ValueError("课程必须包含1至40页")
        ids = [validate_slide_id(s["slide_id"]) for s in slides]
        if len(set(ids)) != len(ids):
            raise ValueError("课程页面ID重复")
        return result

    def check_contract(self, project, frozen):
        if frozen and self.contract(project) != frozen:
            raise CourseBoundary("paused", "storyboard", "有序分镜已变化，不能继续原课程版本")

    def storyboard(self, db, project):
        services = self.services(db, project)
        for method in (services.storyboard_script, services.storyboard_visual, services.storyboard_compose):
            result = method()
            if result.get("success") is False:
                raise ValueError("分镜阶段未成功")

    def scene_ready(self, project, slide):
        from html_visual_store import load_scene
        from html_storyboard_planning import normalize_html_scene_plan, load_template_catalog
        from html_scene_editing import _validate_binding, SceneEditError
        scene = load_scene(project.run_dir, slide["slide_id"])
        if scene is None:
            return False
        base = Path(project.run_dir)/"planning/html_visual"
        try:
            plan = json.loads((base/f'plan-{slide["slide_id"]}.json').read_text(encoding="utf-8"))
            if plan["version"] != "0.2.0" or scene["version"] not in ("0.6.0", "0.7.0"):
                raise ValueError("旧场景不可代替语义课程")
            normalize_html_scene_plan(plan, load_template_catalog(self.root), contract_slide=slide)
            binding = json.loads((base/f'binding-{slide["slide_id"]}.json').read_text(encoding="utf-8"))
            _validate_binding(binding, scene, slide["narration_beats"])
        except (OSError, ValueError, KeyError, SceneEditError) as error:
            # Existing scenes, including manual edits, must never be replaced silently.
            raise CourseBoundary("waiting_for_review", "html_pages", "现有页面需核验或显式重建；保留原场景和手工修改", slide["slide_id"]) from error
        return True

    def produce(self, db, project, slide):
        from html_visual_review_routes import _jobs
        if _jobs is None:
            raise ValueError("HTML生产服务未配置")
        return _jobs.submit(db, project, slide, options={"plan_version": "0.2.0"})

    def preflight_page(self, project, sid):
        from project_model_binding_service import freeze_project_models, ModelBindingError
        try:
            freeze_project_models(project, required=("planning", "text", "image"))
        except ModelBindingError as error:
            raise CourseBoundary("waiting_for_user", "html_pages", "生成连接或凭据未就绪；请检查项目文字规划、视觉及图片生成连接", sid) from error

    def latest_page(self, db, project, sid):
        return __import__('html_task_store').current_slide_task(db, project.id, sid, project.run_dir)

    def narration(self, db, project):
        result = self.services(db, project).init_narration()
        if result.get("success") is False:
            raise ValueError("旁白初始化失败")
        from scripts.minimax_tts import strip_tts_markup
        doc = json.loads((Path(project.run_dir)/"planning/narration_beats.json").read_text(encoding="utf-8"))
        contract = self.contract(project)
        if [s["slide_id"] for s in doc["slides"]] != [s["slide_id"] for s in contract["slides"]]:
            raise CourseBoundary("waiting_for_review", "narration", "旁白页序与当前分镜不同；保留编辑，请先核验")
        for actual, expected in zip(doc["slides"], contract["slides"]):
            signature = lambda beats: [(b.get("id") or b.get("beat_id"), strip_tts_markup(b.get("spoken_text", "")).strip()) for b in beats]
            if signature(actual["beats"]) != signature(expected["narration_beats"]):
                raise CourseBoundary("waiting_for_review", "narration", "旁白原句与权威分镜不同；请先核验，不能自动覆盖", actual["slide_id"])

    def audio_ready(self, project, contract):
        from tts_artifacts import artifact_status, artifact_paths
        from tts_service import current_tts_cache_key, _tts_artifact_matches_runtime
        from scripts.minimax_tts import strip_tts_markup
        runtime = current_tts_cache_key(project)
        return all(artifact_status(project.run_dir, s["slide_id"])["complete"]
                   and (runtime is not None and _tts_artifact_matches_runtime(artifact_paths(project.run_dir, s["slide_id"]), runtime))
                   and strip_tts_markup(artifact_paths(project.run_dir, s["slide_id"])["text"].read_text(encoding="utf-8")).replace(" ", "").replace("\n", "") == strip_tts_markup("".join(b["spoken_text"] for b in s["narration_beats"])).replace(" ", "").replace("\n", "")
                   for s in contract["slides"])

    def tts(self, db, project):
        from tts_service import get_tts_async_service
        return get_tts_async_service().create_job(db, project.id, {"force": False})["job"]

    def semantic_status(self, project, sid):
        from html_semantic_review_service import status
        return status(project.run_dir, sid, self.root)

    def semantic(self, db, project, sid):
        from html_semantic_review_jobs import configured_jobs
        from html_semantic_qa_models import SemanticSubmitRequest
        from html_visual_store import _read_revision
        return configured_jobs().submit(db, project, sid, SemanticSubmitRequest(expected_revision=_read_revision(project.run_dir)["revision"]))

    def approved(self, project, contract):
        from html_creation_workflow import target_readiness
        if not contract:
            return False
        return target_readiness(project.run_dir, self.root, [s["slide_id"] for s in contract["slides"]], "video")["ready"]

    def render(self, db, project):
        result = self.services(db, project).render_video()
        return {"id": result["task_id"]}

    def child(self, db, project, child_id):
        from database import LocalJob
        from html_task_store import recovery_action
        job = db.query(LocalJob).filter(LocalJob.id == child_id, LocalJob.project_id == project.id).one()
        return {"id": job.id, "status": job.status, "error": job.error, "result": job.get_payload().get("result", {}),
                "can_resume": recovery_action(job)["can_resume"]}

    def resume_child(self, db, project, child_id):
        from database import LocalJob
        job = db.query(LocalJob).filter(LocalJob.id == child_id, LocalJob.project_id == project.id).one()
        if job.job_type == "html_plan_generate":
            from html_visual_review_routes import _jobs
            return _jobs.resume(db, project, job)
        if job.job_type == "html_semantic_review":
            from html_semantic_review_jobs import configured_jobs
            return configured_jobs().resume(db, project, job)
        raise ValueError("该原任务需要单独核验")

    def completed(self, project, output):
        if not output or not self.approved(project, self.contract(project)):
            return False
        with self.deps.session_factory() as db:
            result = self.services(db, project).render_video_status(output["id"])
        video = result.get("video") or {}
        return result.get("status") in ("completed", "succeeded") and video.get("artifact_state") == "current" and not video.get("historical")


_jobs = None
_lock = __import__('threading').Lock()


def configured_course_jobs():
    global _jobs
    with _lock:
        if _jobs is None:
            from one_click_orchestrator import get_one_click_dependencies
            deps = get_one_click_dependencies()
            _jobs = HtmlCourseJobs(deps.session_factory, CourseActions(deps))
    return _jobs
