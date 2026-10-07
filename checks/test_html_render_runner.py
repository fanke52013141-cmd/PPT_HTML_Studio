"""E01: html render runner subprocess orchestration (stubbed stages)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from html_render_runner import (
    HtmlRenderError,
    HtmlRenderRunner,
    HtmlRenderRunnerDependencies,
)


@dataclass
class FakeResult:
    returncode: int = 0
    stdout: str = "{}"
    stderr: str = ""


def _runner(
    tmp_path: Path,
    results: list[FakeResult],
    calls: list[list],
    contents: list[str] | None = None,
) -> HtmlRenderRunner:
    captured = contents if contents is not None else []

    def fake_run(args, **kwargs):
        args = list(args)
        calls.append(args)
        if len(args) > 2 and str(args[1]).endswith("export-slide-video.cjs"):
            captured.append(Path(args[2]).read_text(encoding="utf-8"))
        if "concat" in args:
            Path(args[-1]).write_bytes(b"mp4")
        return results.pop(0)

    return HtmlRenderRunner(
        HtmlRenderRunnerDependencies(
            repo_root=tmp_path / "repo",
            read_slide_ids=lambda run_dir: ["s1", "s2"],
            run_subprocess_bounded=fake_run,
        )
    )


def _project_files(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    for slide in ("s1", "s2"):
        scene_dir = run_dir / "planning" / "html_visual"
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / f"scene-{slide}.json").write_text(
            json.dumps({
                "format": "hps.visual.scene",
                "id": slide,
                "durationMs": 10000,
                "motion": [
                    {"targetId": "n1", "type": "enter", "startMs": 0,
                     "durationMs": 500, "offsetX": 0, "offsetY": 0},
                ],
            }),
            encoding="utf-8",
        )
        slide_dir = run_dir / "slides" / slide
        slide_dir.mkdir(parents=True, exist_ok=True)
        (slide_dir / "voice.mp3").write_bytes(b"audio")
        (slide_dir / "audio_timeline.json").write_text(
            json.dumps(
                {
                    "audio_content_duration_sec": 10.0,
                    "segments": [
                        {"id": "b1", "start": 0.0, "end": 9.5, "text": "讲解"}
                    ],
                }
            ),
            encoding="utf-8",
        )
    return run_dir


def test_run_renders_segments_concatenates_and_probes(tmp_path: Path) -> None:
    run_dir = _project_files(tmp_path)
    probe = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width":1600,"height":900,"pix_fmt":"yuv420p", "r_frame_rate":"30/1", "color_space":"bt709", "color_transfer":"bt709", "color_primaries":"bt709"},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": "20.0"},
    }
    calls: list[list] = []
    results = [
        FakeResult(stdout=json.dumps({"sceneId": "s1"})),
        FakeResult(stdout=json.dumps({"sceneId": "s2"})),
        FakeResult(returncode=0),
        FakeResult(stdout=json.dumps(probe)),
    ]
    contents: list[str] = []
    runner = _runner(tmp_path, results, calls, contents)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    stages: list[str] = []
    result = runner.run(
        type("P", (), {"run_dir": str(run_dir)})(),
        output_dir=output_dir,
        set_stage=stages.append,
    )
    assert [s for s in stages if s.startswith("rendering:")] == [
        "rendering:s1",
        "rendering:s2",
    ]
    assert "composing" in stages
    # Two node export calls (one per slide), one ffmpeg concat, one ffprobe.
    assert len(calls) == 4
    assert calls[0][1].endswith("export-slide-video.cjs")
    bound = json.loads(contents[0])
    assert bound["durationMs"] == 10000
    assert bound["beats"][0]["endMs"] == 9500
    concat_call = calls[2]
    assert concat_call[0].endswith("ffmpeg")
    assert result.output_path.parent == output_dir
    assert result.output_path.is_file()
    assert result.color_validation == {
        "standard": "bt709",
        "tagged": True,
        "pipeline": "html_visual_shared_bundle",
    }
    # Work directory is cleaned: no temp bound scenes or segments left.
    work = run_dir / "planning" / "html_visual" / "render_work"
    assert list(work.glob("bound-*.json")) == []
    assert list(work.glob("segment-*.mp4")) == []


def test_missing_scene_or_audio_fail_with_clear_errors(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "planning" / "html_visual").mkdir(parents=True)
    (run_dir / "slides" / "s1").mkdir(parents=True)
    (run_dir / "slides" / "s1" / "audio_timeline.json").write_text("{}", encoding="utf-8")
    calls: list[list] = []
    runner = _runner(tmp_path, [], calls)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    with pytest.raises(HtmlRenderError) as scene_missing:
        runner.run(
            type("P", (), {"run_dir": str(run_dir)})(),
            output_dir=output_dir,
            set_stage=lambda s: None,
        )
    assert "尚未保存" in str(scene_missing.value)
    (run_dir / "planning" / "html_visual" / "scene-s1.json").write_text(
        json.dumps({"format": "hps.visual.scene", "id": "s1", "durationMs": 10000}),
        encoding="utf-8",
    )
    with pytest.raises(HtmlRenderError) as audio_missing:
        runner.run(
            type("P", (), {"run_dir": str(run_dir)})(),
            output_dir=output_dir,
            set_stage=lambda s: None,
        )
    assert "已确认音频" in str(audio_missing.value)
    (run_dir / "slides" / "s1" / "voice.mp3").write_bytes(b"a")
    # Malformed timeline rejected by the binder without any subprocess call.
    with pytest.raises(HtmlRenderError) as bad_timeline:
        runner.run(
            type("P", (), {"run_dir": str(run_dir)})(),
            output_dir=output_dir,
            set_stage=lambda s: None,
        )
    assert "音频绑定失败" in str(bad_timeline.value)
    assert calls == []


def test_render_failure_surfaces_stderr(tmp_path: Path) -> None:
    run_dir = _project_files(tmp_path)
    calls: list[list] = []
    results = [
        FakeResult(returncode=1, stderr="boom"),
    ]
    runner = _runner(tmp_path, results, calls)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    with pytest.raises(HtmlRenderError) as failed:
        runner.run(
            type("P", (), {"run_dir": str(run_dir)})(),
            output_dir=output_dir,
            set_stage=lambda s: None,
        )
    assert "boom" in str(failed.value)
