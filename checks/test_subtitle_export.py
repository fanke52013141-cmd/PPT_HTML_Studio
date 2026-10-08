from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import subtitle_export_routes as routes
from subtitle_export_service import SubtitleExportError, build_subtitle_export


def _write_slide(
    run_dir: Path,
    slide_id: str,
    *,
    srt: str,
    timeline: dict,
) -> None:
    slide_dir = run_dir / "slides" / slide_id
    slide_dir.mkdir(parents=True, exist_ok=True)
    (slide_dir / "subtitles.srt").write_text(srt, encoding="utf-8")
    (slide_dir / "audio_timeline.json").write_text(
        json.dumps(timeline), encoding="utf-8"
    )


def test_subtitle_export_merges_contract_order_offsets_and_reindexes(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "project-a"
    _write_slide(
        run_dir,
        "slide_002",
        srt="9\n00:00:00,000 --> 00:00:01,000\n第二页\n",
        timeline={"audio_start_sec": 0.5, "duration_sec": 2.0},
    )
    _write_slide(
        run_dir,
        "slide_001",
        srt=(
            "7\n00:00:00,000 --> 00:00:01,000\n第一页甲\n\n"
            "8\n00:00:01,100 --> 00:00:02,000\n第一页乙\n"
        ),
        timeline={
            "audio_start_sec": 0.25,
            "audio_content_duration_sec": 2.0,
            "duration_sec": 2.25,
            "segments": [{"start": 0, "end": 2.0}],
        },
    )

    result = build_subtitle_export(run_dir, ["slide_001", "slide_002"])

    assert result.slide_count == 2
    assert result.cue_count == 3
    # 页游标推进量 = Remotion 页长（audio_end 2.25 + 0.4s 尾帧 = 2.65），
    # 第二页字幕随之右移到 2.65 + audio_start 0.5 = 3.15。
    assert result.content == (
        "1\n00:00:00,250 --> 00:00:01,250\n第一页甲\n\n"
        "2\n00:00:01,350 --> 00:00:02,250\n第一页乙\n\n"
        "3\n00:00:03,150 --> 00:00:04,150\n第二页\n"
    )


def test_subtitle_export_refuses_missing_or_invalid_subtitles(tmp_path: Path) -> None:
    run_dir = tmp_path / "project-a"
    _write_slide(
        run_dir,
        "slide_001",
        srt="not a subtitle",
        timeline={"duration_sec": 1},
    )
    with pytest.raises(SubtitleExportError, match="SRT 字幕块格式无效"):
        build_subtitle_export(run_dir, ["slide_001"])

    (run_dir / "slides" / "slide_001" / "subtitles.srt").unlink()
    with pytest.raises(SubtitleExportError, match="缺少字幕文件"):
        build_subtitle_export(run_dir, ["slide_001"])


def test_subtitle_export_treats_legacy_missing_audio_start_as_zero(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "project-a"
    _write_slide(
        run_dir,
        "slide_001",
        srt="1\n00:00:00,000 --> 00:00:01,000\n兼容旧时间线\n",
        timeline={"duration_sec": 1, "segments": [{"end": 1}]},
    )
    result = build_subtitle_export(run_dir, ["slide_001"])
    assert "00:00:00,000 --> 00:00:01,000" in result.content


def test_subtitle_export_rejects_path_escape_and_project_isolation(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "runs" / "project-a"
    _write_slide(
        tmp_path / "runs" / "project-b",
        "slide_001",
        srt="1\n00:00:00,000 --> 00:00:01,000\n不应读取\n",
        timeline={"duration_sec": 1},
    )
    with pytest.raises(SubtitleExportError, match="无效页面"):
        build_subtitle_export(run_dir, ["../project-b"])
    with pytest.raises(SubtitleExportError, match="缺少字幕文件"):
        build_subtitle_export(run_dir, ["slide_001"])


def test_subtitle_download_route_returns_srt_headers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "route-project"
    _write_slide(
        run_dir,
        "slide_001",
        srt="1\n00:00:00,000 --> 00:00:01,000\n路由字幕\n",
        timeline={"audio_start_sec": 0, "duration_sec": 1},
    )
    project = SimpleNamespace(id="route-project", run_dir=str(run_dir))
    monkeypatch.setattr(routes, "project_or_404", lambda _db, _id: project)
    monkeypatch.setattr(routes, "project_run_dir_or_500", lambda _project: str(run_dir))
    monkeypatch.setattr(routes, "read_current_slide_ids_or_404", lambda _project: ["slide_001"])

    readiness = routes.get_subtitle_export_readiness("route-project", object())
    response = routes.download_subtitles_srt("route-project", object())

    assert readiness["ready"] is True
    assert response.headers["content-type"] == "text/srt; charset=utf-8"
    assert response.headers["content-disposition"] == (
        'attachment; filename="route-project-subtitles.srt"'
    )
    assert response.body.decode("utf-8").endswith("路由字幕\n")


def test_subtitle_export_page_starts_match_video_page_durations(
    tmp_path: Path,
) -> None:
    """三页回归：字幕页起点必须等于视频页起点（误差 <= 1 帧），无累计漂移。

    页 1 由音频决定页长；页 2 由更长的 reveal 动画决定页长；页 3 是缺
    duration_sec 的旧格式时间线（segments 决定音频结尾）。每页首条字幕
    的起始时间必须等于前面各页"视频页长"之和。
    """
    from scripts.build_remotion_props import slide_duration

    run_dir = tmp_path / "project-a"

    def write_animation(slide_id: str, payload: dict | None) -> None:
        path = run_dir / "slides" / slide_id / "animation_timeline.json"
        if payload is None:
            return
        path.write_text(json.dumps(payload), encoding="utf-8")

    pages = [
        # (slide_id, srt, audio_timeline, animation_timeline or None)
        (
            "slide_001",
            "1\n00:00:00,000 --> 00:00:01,000\n音频决定页长\n",
            {"audio_start_sec": 0.0, "duration_sec": 2.0, "segments": [{"start": 0, "end": 2.0}]},
            None,
        ),
        (
            "slide_002",
            "1\n00:00:00,000 --> 00:00:01,000\n动画决定页长\n",
            {"audio_start_sec": 0.0, "duration_sec": 1.0, "segments": [{"start": 0, "end": 1.0}]},
            {"duration_sec": 3.0, "events": [{"at": 0, "duration": 3.0}]},
        ),
        (
            "slide_003",
            "1\n00:00:00,000 --> 00:00:01,000\n旧格式时间线\n",
            {"audio_start_sec": 0.0, "segments": [{"start": 0, "end": 1.5}]},
            None,
        ),
    ]
    for slide_id, srt, timeline, animation in pages:
        _write_slide(run_dir, slide_id, srt=srt, timeline=timeline)
        write_animation(slide_id, animation)

    result = build_subtitle_export(
        run_dir, [page[0] for page in pages]
    )

    # 与视频侧同一页长规则的独立推算：逐页 slide_duration 累加
    expected_starts: list[float] = []
    cursor = 0.0
    for _slide_id, _srt, timeline, animation in pages:
        expected_starts.append(cursor)
        cursor += slide_duration(
            timeline,
            animation if animation is not None else {},
            run_dir / "slides",
        )

    cue_starts = [
        line.split(" --> ")[0]
        for line in result.content.splitlines()
        if " --> " in line
    ]
    assert len(cue_starts) == 3
    # 手算页起点：0、2.4（2.0+0.4 尾帧）、5.4（2.4+3.0 动画页长）
    assert cue_starts == ["00:00:00,000", "00:00:02,400", "00:00:05,400"]
    # 与视频侧 slide_duration 推算一致（一帧 1/30s 以内）
    one_frame_ms = 1000 / 30
    for cue_start, expected in zip(cue_starts, expected_starts):
        cue_ms = (
            int(cue_start[0:2]) * 3_600_000
            + int(cue_start[3:5]) * 60_000
            + int(cue_start[6:8]) * 1_000
            + int(cue_start[9:12])
        )
        assert abs(cue_ms - expected * 1_000) <= one_frame_ms
