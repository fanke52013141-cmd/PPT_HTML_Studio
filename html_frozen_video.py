"""Formal snapshot-only video runner, verified page-local cache and isolated staging."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from html_build_snapshot import digest, fresh_hash, json_bytes, verify_snapshot
from html_export_snapshot import (
    freeze_course,
    verify_course,
    page_folder,
    export_env,
    runtime_identity,
)
from pipeline_lifecycle import project_artifact_lock, write_json_atomic
from artifact_fingerprint import render_input_fingerprint


def validate_video(runner, path, fps, expected_frames=None):
    env = runner._media_env()
    probe = runner._probe(path, fps)
    video = next(s for s in probe["streams"] if s.get("codec_type") == "video")
    audio = next(s for s in probe["streams"] if s.get("codec_type") == "audio")
    frames = int(video.get("nb_frames", 0))
    if frames <= 0 or (expected_frames is not None and frames != expected_frames):
        raise ValueError("EXPORT_FRAME_COUNT_MISMATCH")
    if abs(float(probe["format"]["duration"]) - frames / fps) > 0.15:
        raise ValueError("EXPORT_DURATION_MISMATCH")
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise ValueError("EXPORT_CODEC_MISMATCH")
    audio_duration = float(audio.get("duration", 0))
    if audio_duration <= 0 or abs(audio_duration - frames / fps) > 0.2:
        raise ValueError("EXPORT_AUDIO_DURATION_MISMATCH")
    deps = runner.dependencies
    result = deps.run_subprocess_bounded(
        [
            env.get("FFMPEG_BIN", deps.ffmpeg_bin),
            "-v",
            "error",
            "-xerror",
            "-err_detect",
            "explode",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout_sec=deps.stage_timeout_sec,
    )
    if result.returncode or (result.stderr or "").strip():
        raise ValueError("EXPORT_FULL_DECODE_FAILED: " + (result.stderr or "")[-300:])
    return probe, {
        "frames": frames,
        "fps": fps,
        "duration_sec": frames / fps,
        "audio_duration_sec": audio_duration,
        "structure": {
            "width": video.get("width"),
            "height": video.get("height"),
            "pix_fmt": video.get("pix_fmt"),
            "video_codec": video["codec_name"],
            "audio_codec": audio["codec_name"],
            "color_space": video.get("color_space"),
        },
        "full_decode": "passed",
        "sha256": fresh_hash(path),
    }


def run_frozen(runner, project, output_dir, set_stage, fps, fingerprint_factory=None):
    from html_render_runner import HtmlRenderResult, HtmlRenderError

    deps = runner.dependencies
    if type(fps) is not int or not 1 <= fps <= 60:
        raise ValueError("EXPORT_FPS_INVALID")
    run = Path(project.run_dir).resolve()
    course = freeze_course(
        run,
        deps.repo_root,
        target="video",
        fingerprint_factory=fingerprint_factory
        or (
            lambda: render_input_fingerprint(
                run, visual_settings={}, pipeline_version="html_snapshot_0.1.0"
            )
        ),
    )
    manifest = verify_course(course)
    identity = runtime_identity(
        deps.repo_root, course, deps.run_subprocess_bounded, node_bin=deps.node_bin
    )
    media_env = runner._media_env()
    # Probe/concat/decode must use the same executable pair passed to Node.
    from dataclasses import replace

    runner = type(runner)(
        replace(
            deps,
            ffmpeg_bin=media_env.get("FFMPEG_BIN", deps.ffmpeg_bin),
            ffprobe_bin=media_env.get("FFPROBE_BIN", deps.ffprobe_bin),
        )
    )
    deps = runner.dependencies
    for name, binary in (("ffmpeg", deps.ffmpeg_bin), ("ffprobe", deps.ffprobe_bin)):
        resolved = shutil.which(binary)
        if not resolved:
            raise ValueError("EXPORT_MEDIA_TOOL_MISSING")
        identity[name] = fresh_hash(resolved)
        identity[name + "_path"] = resolved

    def verify_runtime():
        for name, sha_key, path_key in (
            ("browser", "browser_sha256", "browser"),
            ("node", "node_sha256", "node_path"),
            ("ffmpeg", "ffmpeg", "ffmpeg_path"),
            ("ffprobe", "ffprobe", "ffprobe_path"),
        ):
            if fresh_hash(identity[path_key]) != identity[sha_key]:
                raise ValueError("EXPORT_RUNTIME_CHANGED: " + name)

    work_base = run / "planning/html_visual/export-work"
    work_base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="video-", dir=work_base))
    cache = run / "planning/html_visual/segment-cache"
    cache.mkdir(parents=True, exist_ok=True)
    completed = False
    filename = "render_" + uuid.uuid4().hex + ".mp4"
    candidate = work / filename
    segments, evidence = [], []
    offset = 0
    try:
        for page in manifest["pages"]:
            set_stage("rendering:" + page["slide_id"])
            folder = page_folder(course, page)
            snapshot = verify_snapshot(folder)
            # Ignore global revision/confirmation/order and unused assets: only bytes consumed by this page.
            inputs = [
                e
                for e in snapshot["files"]
                if e["path"].startswith("preview/")
                or e["path"]
                in {"input/scene.json", "audio/voice.mp3", "audio/audio_timeline.json"}
                or e["path"].startswith("source/binding-")
            ]
            key = digest(
                json_bytes(
                    {
                        "version": "0.1.0",
                        "inputs": inputs,
                        "runtime": identity,
                        "tools": [
                            e
                            for e in manifest["files"]
                            if e["path"].startswith("tools/")
                        ],
                        "fps": fps,
                        "codec": "libx264/aac192k/yuv420p/bt709",
                    }
                )
            )
            cached, receipt = cache / (key + ".mp4"), cache / (key + ".json")
            local = work / (page["slide_id"] + ".mp4")
            reused = False
            # Same process ownership model as the application; no per-request gates.
            with project_artifact_lock(cached):
                if cached.is_file() and receipt.is_file():
                    try:
                        old = json.loads(receipt.read_text(encoding="utf-8"))
                        if old["key"] != key or old["validation"][
                            "sha256"
                        ] != fresh_hash(cached):
                            raise ValueError("CACHE_HASH_CHANGED")
                        _, valid = validate_video(
                            runner, cached, fps, old["validation"]["frames"]
                        )
                        reused = True
                    except (ValueError, OSError, KeyError, TypeError, HtmlRenderError):
                        cached.unlink(missing_ok=True)
                        receipt.unlink(missing_ok=True)
                if not reused:
                    env = export_env(deps.repo_root, folder, media_env)
                    env["HPS_CHROME"] = identity["browser"]
                    result = deps.run_subprocess_bounded(
                        [
                            deps.node_bin,
                            str(course / "tools/export-slide-video.cjs"),
                            str(folder / "input/scene.json"),
                            str(folder / "audio/voice.mp3"),
                            str(local),
                            str(fps),
                        ],
                        cwd=str(deps.repo_root),
                        env=env,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout_sec=deps.stage_timeout_sec,
                    )
                    if result.returncode:
                        raise ValueError(
                            "EXPORT_PAGE_FAILED: " + (result.stderr or "")[-400:]
                        )
                    rendered = json.loads(result.stdout)
                    _, valid = validate_video(runner, local, fps, rendered["frames"])
                    verify_course(course)
                    verify_runtime()
                    temp_cache = cache / (key + "." + uuid.uuid4().hex + ".tmp")
                    try:
                        shutil.copyfile(local, temp_cache)
                        os.replace(temp_cache, cached)
                        write_json_atomic(receipt, {"key": key, "validation": valid})
                    finally:
                        temp_cache.unlink(missing_ok=True)
                # Copy under the cache lock. Another job cannot invalidate our input midway.
                shutil.copyfile(cached, local)
            segments.append(local)
            evidence.append(
                {
                    "slide_id": page["slide_id"],
                    "snapshot_id": page["snapshot_id"],
                    "cache_key": key,
                    "reused": reused,
                    "offset_frames": offset,
                    **valid,
                }
            )
            offset += valid["frames"]
        set_stage("composing")
        runner._concat(
            segments, candidate, frame_counts=[p["frames"] for p in evidence], fps=fps
        )
        probe, validation = validate_video(runner, candidate, fps, offset)
        verify_course(course)
        verify_runtime()
        completed = True
        return HtmlRenderResult(
            candidate,
            filename,
            probe,
            tuple(p["slide_id"] for p in manifest["pages"]),
            {"standard": "bt709", "tagged": True, "pipeline": "html_snapshot"},
            {
                "snapshot_id": manifest["snapshot_id"],
                "fingerprint": manifest["fingerprint"],
                "course_path": str(course),
                "frozen_run_dir": str(course / "frozen-run"),
                "runtime": identity,
                "pages": evidence,
                "validation": validation,
                "work_dir": str(work),
            },
        )
    finally:
        if not completed:
            assert work.resolve().parent == work_base.resolve()
            shutil.rmtree(work)
        else:
            for segment in segments:
                segment.unlink(missing_ok=True)
