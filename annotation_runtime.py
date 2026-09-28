"""Explicit annotation runtime wiring for the application composition root."""

from __future__ import annotations

import os
from pathlib import Path


def configure_annotation_runtime(app, write_json_atomic, read_json_file, reveal_lock_for):
    from annotation_routes import router as annotation_router
    from annotation_job_store import AnnotationJobStore
    from annotation_jobs import AnnotationJobDependencies, AnnotationJobManager
    from annotation_planner import AnnotationPlanner, AnnotationPlannerDependencies
    from annotation_prompt_templates import AnnotationPromptStore
    from database import SessionLocal as DatabaseSessionLocal
    from json_llm_service import generate_json_with_configured_llm as _annotation_llm_call
    from annotation_service import (
        AnnotationServiceDependencies,
        configure_annotation_service,
    )
    from annotation_store import (
        AnnotationStoreDependencies,
        configure_annotation_store,
        get_annotation_store,
    )
    from annotation_text_layout import TextLayoutBuilder, TextLayoutDependencies

    import annotation_ocr_baidu as _annotation_ocr

    def _annotation_ocr_config():
        # W3 过渡:密钥经环境变量注入;全局设置/配置包接线在 W3 收尾。
        return _annotation_ocr.BaiduOcrEngineConfig(
            api_key=os.environ.get("PPT_ANNOTATION_BAIDU_OCR_KEY", "").strip()
        )

    configure_annotation_store(
        AnnotationStoreDependencies(write_json_atomic=write_json_atomic)
    )
    _annotation_layout_builder = TextLayoutBuilder(
        TextLayoutDependencies(
            write_json_atomic=write_json_atomic,
            # runtime_support.read_json_file 的签名是 (path, fallback);
            # 布局层约定缺文件返回 None。
            read_json_file=lambda path: read_json_file(path, None),
            ocr_config_provider=_annotation_ocr_config,
        )
    )
    _annotation_prompt_store = AnnotationPromptStore(
        read_json_file=lambda path: read_json_file(path, None),
        write_json_atomic=write_json_atomic,
        prompts_path_for=lambda run_dir: Path(run_dir) / "planning" / "annotation_prompts.json",
        project_config_path_for=lambda run_dir: Path(run_dir) / "planning" / "project_config.json",
    )

    def _annotation_llm_generate(**kwargs):
        # Prefer the text model connection selected in the project's creation
        # package. Legacy projects without a binding retain the global model.
        binding = None
        db = DatabaseSessionLocal()
        try:
            from account_context import account_scope
            from credential_store import get_credential
            from database import Project
            from model_connection_service import resolve_model_connection
            from project_config_runtime import resolve_project_model_binding

            project = db.query(Project).filter(Project.run_dir == str(kwargs.get("run_dir") or "")).first()
            if project is not None:
                with account_scope(project.account_id):
                    binding = resolve_project_model_binding(
                        project,
                        "annotation_planning",
                        expected_kind="text",
                        resolve_model_connection=resolve_model_connection,
                        get_credential=get_credential,
                    )
        finally:
            db.close()
        return _annotation_llm_call(**kwargs, model_binding=binding)

    _annotation_planner = AnnotationPlanner(
        AnnotationPlannerDependencies(
            prompt_store=_annotation_prompt_store,
            llm_generate=_annotation_llm_generate,
        )
    )
    _annotation_job_manager = AnnotationJobManager(
        AnnotationJobDependencies(
            job_store=AnnotationJobStore(DatabaseSessionLocal),
            service_get_slide_ids=lambda db, project_id: [],
            session_factory=DatabaseSessionLocal,
            text_layout_builder=_annotation_layout_builder,
            recognize=_annotation_ocr.recognize_text_lines,
            annotation_store=get_annotation_store(),
            planner=_annotation_planner,
            lock_for=reveal_lock_for,
        )
    )
    configure_annotation_service(
        AnnotationServiceDependencies(
            store=get_annotation_store(),
            lock_for=reveal_lock_for,
            text_layout_builder=_annotation_layout_builder,
            job_manager=_annotation_job_manager,
            ocr_ready=lambda: bool(os.environ.get("PPT_ANNOTATION_BAIDU_OCR_KEY", "").strip()),
            prompt_store=_annotation_prompt_store,
        )
    )
    app.include_router(annotation_router)
