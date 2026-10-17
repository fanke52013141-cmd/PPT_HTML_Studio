"""Explicit video startup composition; no application import or business logic."""
import os

from database import SessionLocal as VideoSessionLocal
from remotion_runner import (
    RemotionRunner,
    RemotionRunnerDependencies,
)
from video_artifact_service import (
    VideoArtifactDependencies,
    VideoArtifactService,
)
from video_contracts import VideoRenderConfig
from video_render_service import (
    VideoRenderDependencies,
    configure_video_render_service,
)
from html_render_runner import (
    HtmlRenderRunner,
    HtmlRenderRunnerDependencies,
)


def configure_video_runtime(*, repo_root, runs_root, pipeline_version, visual_lead_sec,
                            bind_timeout_sec, build_props_timeout_sec, npm_install_timeout_sec,
                            render_timeout_sec, color_process_timeout_sec, read_project_visual_settings,
                            normalize_hex_color, normalize_subtitle_style, resolve_media_tool,
                            build_current_reveal_assets, write_project_log, run_subprocess_killable,
                            read_contract_slide_ids, max_concurrent_renders):
    video_render_config = VideoRenderConfig(
        repo_root=repo_root,
        runs_root=runs_root,
        pipeline_version=pipeline_version,
        reveal_visual_lead_sec=visual_lead_sec,
        bind_timeout_sec=bind_timeout_sec,
        build_props_timeout_sec=build_props_timeout_sec,
        npm_install_timeout_sec=npm_install_timeout_sec,
        render_timeout_sec=render_timeout_sec,
        color_process_timeout_sec=color_process_timeout_sec,
        render_acceleration=os.environ.get("PPT_STUDIO_RENDER_ACCELERATION", "auto"),
    )
    video_artifact_service = VideoArtifactService(
        VideoArtifactDependencies(
            runs_root=video_render_config.runs_root,
            pipeline_version=video_render_config.pipeline_version,
            render_timeout_sec=video_render_config.render_timeout_sec,
            read_visual_settings=read_project_visual_settings,
            normalize_color=normalize_hex_color,
            normalize_subtitle_style=normalize_subtitle_style,
            resolve_media_tool=resolve_media_tool,
        )
    )
    remotion_runner = RemotionRunner(
        RemotionRunnerDependencies(
            config=video_render_config,
            build_reveal_assets=build_current_reveal_assets,
            write_project_log=write_project_log,
            # Remotion 渲染（npx -> node -> ffmpeg）是典型多层进程树，
            # 超时必须杀掉整棵进程树，避免孙进程残留与管道死锁。
            run_subprocess_bounded=run_subprocess_killable,
            resolve_media_tool=resolve_media_tool,
        )
    )
    # 跨项目渲染并发上限（1-3）：多余提交保留为持久 queued 任务排队。
    video_render_service = configure_video_render_service(
        VideoRenderDependencies(
            session_factory=VideoSessionLocal,
            artifact_service=video_artifact_service,
            remotion_runner=remotion_runner,
            html_runner=HtmlRenderRunner(
                HtmlRenderRunnerDependencies(
                    repo_root=repo_root,
                    read_slide_ids=read_contract_slide_ids,
                )
            ),
            config=video_render_config,
            max_concurrent_renders=max_concurrent_renders,
        )
    )
    return video_render_service
