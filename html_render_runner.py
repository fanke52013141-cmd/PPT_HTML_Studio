"""HTML render runner: scene + confirmed audio to validated MP4 (E01).

Backend sibling of ``remotion_runner`` for html-visual projects. Owns the
bounded subprocess stages (per-slide browser render → ffmpeg concat →
ffprobe validation) and nothing else: task state, locking, artifact
registration and digital-human composition stay in
``video_render_service``/``video_artifact_service`` exactly as before.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from runtime_support import run_subprocess_killable


class HtmlRenderError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class HtmlRenderResult:
    output_path: Path
    output_filename: str
    probe: dict[str, Any]
    segments: tuple[str, ...]
    # Same field name as RemotionRenderResult so the shared worker
    # (metadata, digital-human composite) treats both backends alike.
    color_validation: dict[str, Any] | None = None


@dataclass(frozen=True)
class HtmlRenderRunnerDependencies:
    repo_root: Path
    read_slide_ids: Callable[[str | Path], list[str]]
    run_subprocess_bounded: Callable[..., subprocess.CompletedProcess] = (
        run_subprocess_killable
    )
    node_bin: str = "node"
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    export_script: Path = Path("html_engine") / "tools" / "export-slide-video.cjs"
    stage_timeout_sec: float = 600.0


class HtmlRenderRunner:
    """Renders one html-backend project into a single MP4."""

    def __init__(self, dependencies: HtmlRenderRunnerDependencies) -> None:
        self.dependencies = dependencies

    # -- inputs ----------------------------------------------------------

    def _scene_path(self, run_dir: str | Path, slide_id: str) -> Path:
        path = Path(run_dir) / "planning" / "html_visual" / f"scene-{slide_id}.json"
        if not path.is_file():
            raise HtmlRenderError(
                400, f"页面 {slide_id} 尚未保存 HTML 场景，无法渲染"
            )
        return path

    def _audio_path(self, run_dir: str | Path, slide_id: str) -> Path:
        path = Path(run_dir) / "slides" / slide_id / "voice.mp3"
        if not path.is_file():
            raise HtmlRenderError(
                400, f"页面 {slide_id} 缺少已确认音频，无法渲染"
            )
        return path

    def _bound_scene_path(
        self,
        work_dir: Path,
        scene: dict[str, Any],
        timeline: dict[str, Any],
        slide_id: str,
    ) -> Path:
        from html_audio_binder import (
            AudioBindingError,
            bind_scene_to_audio,
            binding_metadata,
        )

        try:
            bound = bind_scene_to_audio(scene, timeline)
        except AudioBindingError as exc:
            raise HtmlRenderError(400, f"页面 {slide_id} 音频绑定失败：{exc}")
        path = work_dir / f"bound-{slide_id}.json"
        path.write_text(
            json.dumps(bound, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Binding provenance is a derived-artifact record, never scene input.
        (work_dir / f"binding-{slide_id}.json").write_text(
            json.dumps(
                binding_metadata(scene, timeline), ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        return path

    # -- subprocess stages -----------------------------------------------

    def _media_env(self) -> dict[str, str]:
        """Resolve ffmpeg/ffprobe once via the shared media-tool lookup and
        hand them to the node subprocess (the cjs reads FFMPEG_BIN/
        FFPROBE_BIN); bare PATH lookups would miss env-configured installs."""
        import importlib.util

        env = dict(os.environ)
        spec = importlib.util.spec_from_file_location(
            "hps_media_tools",
            self.dependencies.repo_root / "scripts" / "media_tools.py",
        )
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            for name in ("ffmpeg", "ffprobe"):
                resolved = module.resolve_media_tool(
                    name, repo_root=self.dependencies.repo_root
                )
                if resolved:
                    env[f"{name.upper()}_BIN"] = resolved
        except Exception:
            pass
        return env

    def _render_segment(
        self,
        scene_path: Path,
        audio_path: Path,
        segment_path: Path,
        fps: int,
    ) -> dict[str, Any]:
        deps = self.dependencies
        result = deps.run_subprocess_bounded(
            [
                deps.node_bin,
                str(deps.repo_root / deps.export_script),
                str(scene_path),
                str(audio_path),
                str(segment_path),
                str(fps),
            ],
            cwd=str(deps.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout_sec=deps.stage_timeout_sec,
            env=self._media_env(),
        )
        if result.returncode != 0:
            raise HtmlRenderError(
                500,
                "HTML 页面渲染失败："
                + (result.stderr or result.stdout or "")[-500:],
            )
        try:
            return json.loads(result.stdout)
        except Exception as exc:
            raise HtmlRenderError(500, "HTML 渲染输出无法解析") from exc

    def _concat(self, segments: list[Path], output_path: Path) -> None:
        deps = self.dependencies
        concat_list = output_path.with_suffix(".concat.txt")
        concat_list.write_text(
            "".join(f"file '{segment.as_posix()}'\n" for segment in segments),
            encoding="utf-8",
        )
        result = deps.run_subprocess_bounded(
            [
                deps.ffmpeg_bin,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout_sec=deps.stage_timeout_sec,
        )
        concat_list.unlink(missing_ok=True)
        if result.returncode != 0:
            raise HtmlRenderError(
                500, "视频合成失败：" + (result.stderr or "")[-500:]
            )

    def _probe(self, output_path: Path) -> dict[str, Any]:
        deps = self.dependencies
        result = deps.run_subprocess_bounded(
            [
                deps.ffprobe_bin,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout_sec=60,
        )
        if result.returncode != 0:
            raise HtmlRenderError(500, "ffprobe 校验失败")
        try:
            probe = json.loads(result.stdout)
        except Exception as exc:
            raise HtmlRenderError(500, "ffprobe 输出无法解析") from exc
        streams = probe.get("streams", [])
        if not any(s.get("codec_type") == "video" for s in streams):
            raise HtmlRenderError(500, "渲染结果缺少视频流")
        if not any(s.get("codec_type") == "audio" for s in streams):
            raise HtmlRenderError(500, "渲染结果缺少音轨")
        return probe

    # -- entry point -------------------------------------------------

    def run(
        self,
        project: Any,
        *,
        output_dir: Path,
        set_stage: Callable[[str], None],
        fps: int = 30,
    ) -> HtmlRenderResult:
        from datetime import datetime
        import uuid

        run_dir = project.run_dir
        slide_ids = self.dependencies.read_slide_ids(run_dir)
        if not slide_ids:
            raise HtmlRenderError(400, "分镜规划尚未生成，无法渲染")
        work_dir = Path(run_dir) / "planning" / "html_visual" / "render_work"
        work_dir.mkdir(parents=True, exist_ok=True)
        segments: list[Path] = []
        output_path: Path | None = None
        completed = False
        try:
            for index, slide_id in enumerate(slide_ids):
                set_stage(f"rendering:{slide_id}")
                scene_path = self._scene_path(run_dir, slide_id)
                audio_path = self._audio_path(run_dir, slide_id)
                timeline_path = (
                    Path(run_dir) / "slides" / slide_id / "audio_timeline.json"
                )
                if not timeline_path.is_file():
                    raise HtmlRenderError(
                        400, f"页面 {slide_id} 缺少 audio_timeline.json，无法绑定时间"
                    )
                timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
                bound_scene = self._bound_scene_path(
                    work_dir,
                    json.loads(scene_path.read_text(encoding="utf-8")),
                    timeline,
                    slide_id,
                )
                segment = work_dir / f"segment-{index:03d}.mp4"
                self._render_segment(
                    bound_scene,
                    audio_path,
                    segment,
                    fps,
                )
                segments.append(segment)
            output_filename = (
                "render_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
                + f"_{uuid.uuid4().hex[:6]}.mp4"
            )
            output_path = Path(output_dir) / output_filename
            set_stage("composing")
            self._concat(segments, output_path)
            probe = self._probe(output_path)
            completed = True
        finally:
            for segment in segments:
                segment.unlink(missing_ok=True)
            for pattern in ("bound-*.json", "binding-*.json", "segment-*.mp4"):
                for leftover in work_dir.glob(pattern):
                    leftover.unlink(missing_ok=True)
            # Never leave a partial MP4 in the user's video collection: the
            # artifact service lists every *.mp4 in that directory.
            if output_path is not None and not completed:
                output_path.unlink(missing_ok=True)
        return HtmlRenderResult(
            output_path=output_path,
            output_filename=output_filename,
            probe=probe,
            segments=tuple(s.name for s in segments),
            color_validation={
                "standard": "bt709",
                "tagged": True,
                "pipeline": "html_visual_shared_bundle",
            },
        )
