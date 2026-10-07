"""Real multi-page encoding benchmark; synthetic silence, no live TTS claim."""

import json
from pathlib import Path
import shutil
import time
import wave
import subprocess
import math

from html_render_runner import HtmlRenderRunner, HtmlRenderRunnerDependencies

ROOT = Path(__file__).resolve().parents[1]


def test_three_page_real_video_duration_color_and_cleanup(tmp_path):
    run = tmp_path / "run"
    ids = []
    expected = 0
    for i, name in enumerate(["condensation", "water-facts", "evaporation-process"]):
        slide = f"s{i}"
        ids.append(slide)
        directory = run / "slides" / slide
        directory.mkdir(parents=True)
        with wave.open(str(directory / "voice.wav"), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            out.writeframes(b"\0\0" * 32000)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(directory / "voice.wav"),
                "-c:a",
                "libmp3lame",
                str(directory / "voice.mp3"),
            ],
            check=True,
            capture_output=True,
        )
        duration = float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(directory / "voice.mp3"),
                ]
            )
        )
        expected += math.ceil(duration * 30) / 30
        timeline = {
            "audio_content_duration_sec": duration,
            "segments": [
                {"id": "b1", "start": 0, "end": 1.8, "text": "观察水的状态变化。"}
            ],
        }
        (directory / "audio_timeline.json").write_text(
            json.dumps(timeline, ensure_ascii=False), encoding="utf-8"
        )
        scene = json.loads(
            (ROOT / f"html_engine/visual/scenes/{name}.json").read_text(
                encoding="utf-8"
            )
        )
        scene["id"] = slide
        visual = run / "planning/html_visual"
        visual.mkdir(parents=True, exist_ok=True)
        (visual / f"scene-{slide}.json").write_text(
            json.dumps(scene, ensure_ascii=False), encoding="utf-8"
        )
    out = tmp_path / "video"
    out.mkdir()
    runner = HtmlRenderRunner(
        HtmlRenderRunnerDependencies(
            repo_root=ROOT, read_slide_ids=lambda path: ids, allow_legacy_unbound=True
        )
    )
    started = time.perf_counter()
    result = runner.run(
        type("P", (), {"run_dir": str(run)})(),
        output_dir=out,
        set_stage=lambda stage: None,
        fps=30,
    )
    video = next(s for s in result.probe["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1600, 900)
    assert abs(float(result.probe["format"]["duration"]) - expected) < 0.15
    assert video["color_space"] == "bt709" and video["pix_fmt"] == "yuv420p"
    assert list((run / "planning/html_visual/render_work").glob("segment-*.mp4")) == []
    evidence = ROOT / "docs/reviews/2026-10-08-html-optimization"
    evidence.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result.output_path, evidence / "three-page-smoke.mp4")
    (evidence / "video-benchmark.json").write_text(
        json.dumps(
            {
                "pages": 3,
                "fps": 30,
                "expected_duration": expected,
                "actual_duration": result.probe["format"]["duration"],
                "seconds": round(time.perf_counter() - started, 3),
                "audio": "synthetic silence",
                "legacy_binding": "explicit compatibility test",
                "video_stream": video,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
