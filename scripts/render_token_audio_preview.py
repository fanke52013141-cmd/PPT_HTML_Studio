"""Real-audio review artifacts only; never manufactures production approvals."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from html_audio_binder import bind_scene_to_audio
from html_pptx_snapshot import (
    HtmlSnapshotDependencies,
    build_snapshot_pptx,
    render_snapshots,
)
from html_visual_review_service import HtmlReviewDependencies, review_scene
from runtime_support import run_subprocess_killable


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    run = ROOT / "outputs/image25-sheet/token-production-v1"
    preview = run / "audio-review-preview"
    if preview.exists():
        raise SystemExit("Refusing to replace audio review artifacts")
    scene = json.loads(
        (run / "planning/html_visual/scene-token-closure.json").read_text(
            encoding="utf-8"
        )
    )
    timeline = json.loads(
        (run / "slides/token-closure/audio_timeline.json").read_text(encoding="utf-8")
    )
    segments = timeline["segments"]

    def segment_containing(text):
        return next(s["id"] for s in segments if text in s["text"])

    first = segments[0]["id"]
    binding = {
        "format": "hps.html.motion_binding",
        "version": "0.1.0",
        "mode": "beat_ids",
        "actions": {},
    }
    targets = {
        "card-1": segment_containing("完整的词"),
        "card-2": segment_containing("不等于字数"),
        "card-3": segment_containing("用量和费用"),
        "summary": segment_containing("用量和费用"),
    }
    for motion in scene["motion"]:
        binding["actions"][f"{motion['targetId']}:{motion['type']}"] = {
            "beatId": targets.get(motion["targetId"], first),
            "edge": "start",
            "offsetMs": 0,
        }
    write(run / "planning/html_visual/binding-token-closure.json", binding)
    bound = bind_scene_to_audio(scene, timeline, binding)
    write(preview / "bound-scene.json", bound)
    env = os.environ.copy()
    env.update(
        HPS_HTML_RESOURCES=str(run / "planning/draft_preview/resources.json"),
        HPS_CHROME="C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe",
        FFMPEG_BIN="C:/Users/Administrator/AppData/Local/Programs/FFmpeg/bin/ffmpeg.exe",
        FFPROBE_BIN="C:/Users/Administrator/AppData/Local/Programs/FFmpeg/bin/ffprobe.exe",
    )

    def draft_process(*args, **kwargs):
        kwargs["env"] = env
        return run_subprocess_killable(*args, **kwargs)

    def no_model(**kwargs):
        raise AssertionError("No model planning in this sample")

    report = review_scene(
        bound,
        run_dir=run,
        deps=HtmlReviewDependencies(
            repo_root=ROOT,
            json_generator=no_model,
            run_subprocess_bounded=draft_process,
        ),
    )
    if not report["passed"]:
        raise RuntimeError("Bound scene static review failed")
    pptx_scene = dict(bound, beats=[])
    images = render_snapshots(
        pptx_scene,
        [bound["durationMs"]],
        preview / "pptx-snapshots",
        deps=HtmlSnapshotDependencies(
            repo_root=ROOT, run_dir=run, run_subprocess_bounded=draft_process
        ),
    )
    pptx = build_snapshot_pptx(
        [{"timeMs": bound["durationMs"], "label": "review_only_final"}],
        images,
        preview / "token-review-only.pptx",
    )
    write(
        preview / "preview-evidence.json",
        {
            "status": "rendering_review_only",
            "productionApproval": "pending",
            "audioConfirmation": "pending_user_listening",
            "sceneStaticReview": report,
            "pptx": pptx,
            "timingSource": timeline["timing_source"],
            "providerTimestampCount": timeline["provider_timestamp_count"],
            "subtitleSegments": len(segments),
            "timingLimitation": "Provider returned 2 coarse windows; 5 display segments include within-window distribution, require listening review",
        },
    )
    result = draft_process(
        [
            "node",
            str(ROOT / "html_engine/tools/export-slide-video.cjs"),
            str(preview / "bound-scene.json"),
            str(run / "slides/token-closure/voice.mp3"),
            str(preview / "token-review-only.mp4"),
            "30",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout_sec=300,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-1200:])
    probe = draft_process(
        [
            env["FFPROBE_BIN"],
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(preview / "token-review-only.mp4"),
        ],
        capture_output=True,
        text=True,
        timeout_sec=30,
    )
    decode = draft_process(
        [
            env["FFMPEG_BIN"],
            "-v",
            "error",
            "-i",
            str(preview / "token-review-only.mp4"),
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout_sec=60,
    )
    if probe.returncode or decode.returncode:
        raise RuntimeError("Probe or complete decode failed")
    evidence = json.loads(
        (preview / "preview-evidence.json").read_text(encoding="utf-8")
    )
    evidence.update(
        status="review_artifacts_rendered",
        video=json.loads(result.stdout),
        ffprobe=json.loads(probe.stdout),
        completeDecode={"returncode": decode.returncode, "stderr": decode.stderr},
        productionExport="not_submitted: approvals pending",
    )
    write(preview / "preview-evidence.json", evidence)
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "durationMs": bound["durationMs"],
                "pptxPages": 1,
                "decodeExitCode": decode.returncode,
                "preview": str(preview),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
