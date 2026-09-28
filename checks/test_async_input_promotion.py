"""Old asynchronous media results never replace current source artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from artifact_fingerprint import sha256_file
from digital_human_impact import mark_presenter_audio_stale
import tts_service


def test_staged_tts_result_keeps_old_audio_after_narration_edit(tmp_path: Path, monkeypatch) -> None:
    slide = tmp_path / "slides" / "slide_001"
    slide.mkdir(parents=True)
    text = slide / "tts_text.txt"
    text.write_text("original", encoding="utf-8")
    live = {key: str(slide / name) for key, name in (
        ("audio", "voice.mp3"), ("metadata", "tts_metadata.json"),
        ("srt", "subtitles.srt"), ("timeline", "audio_timeline.json"),
    )}
    stage = tmp_path / "stage"
    stage.mkdir()
    staged = {key: str(stage / Path(path).name) for key, path in live.items()}
    for key in live:
        Path(live[key]).write_text("old", encoding="utf-8")
        Path(staged[key]).write_text("new", encoding="utf-8")
    monkeypatch.setattr(tts_service, "_load_beats_by_slide", lambda *_args: {"slide_001": []})
    monkeypatch.setattr(tts_service, "current_tts_cache_key", lambda _project: {})
    version = tts_service._tts_job_input_version("slide_001", str(text), [], {})
    job = {"slide_id": "slide_001", "paths": {**live, "text": str(text)},
           "stage_paths": staged, "input_version": version}
    text.write_text("edited", encoding="utf-8")
    assert tts_service._promote_staged_tts_outputs(
        job, SimpleNamespace(run_dir=str(tmp_path)), SimpleNamespace(refresh=lambda _p: None),
    ) is False
    assert Path(live["audio"]).read_text(encoding="utf-8") == "old"


def test_staged_tts_result_promotes_matching_inputs_and_archives_old_audio(tmp_path: Path, monkeypatch) -> None:
    slide = tmp_path / "slides" / "slide_001"
    slide.mkdir(parents=True)
    text = slide / "tts_text.txt"
    text.write_text("stable", encoding="utf-8")
    live = {key: str(slide / name) for key, name in (
        ("audio", "voice.mp3"), ("metadata", "tts_metadata.json"),
        ("srt", "subtitles.srt"), ("timeline", "audio_timeline.json"),
    )}
    stage = tmp_path / "stage"
    stage.mkdir()
    staged = {key: str(stage / Path(path).name) for key, path in live.items()}
    for key in live:
        Path(live[key]).write_text("old", encoding="utf-8")
        Path(staged[key]).write_text("new", encoding="utf-8")
    monkeypatch.setattr(tts_service, "_load_beats_by_slide", lambda *_args: {"slide_001": []})
    monkeypatch.setattr(tts_service, "current_tts_cache_key", lambda _project: {})
    job = {"slide_id": "slide_001", "paths": {**live, "text": str(text)},
           "stage_paths": staged,
           "input_version": tts_service._tts_job_input_version("slide_001", str(text), [], {})}
    assert tts_service._promote_staged_tts_outputs(
        job, SimpleNamespace(run_dir=str(tmp_path)), SimpleNamespace(refresh=lambda _p: None),
    ) is True
    assert Path(live["audio"]).read_text(encoding="utf-8") == "new"
    backups = list((tmp_path / "recovery" / "audio").glob("slide_001-*/voice.mp3"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == "old"


def test_audio_edit_marks_only_dependent_presenter_media_stale(tmp_path: Path) -> None:
    slide = tmp_path / "slides" / "slide_001"
    slide.mkdir(parents=True)
    audio = slide / "voice.mp3"
    audio.write_bytes(b"new audio")
    config_path = tmp_path / "planning" / "digital_human.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"slides": {
        "slide_001": {"job_id": "one", "status": "done", "audio_sha256": "old"},
        "slide_002": {"job_id": "two", "status": "done", "audio_sha256": "old"},
        "full": {"job_id": "full", "status": "done", "audio_sha256": "old"},
    }}), encoding="utf-8")
    assert mark_presenter_audio_stale(tmp_path, ("slide_001",)) == ("slide_001", "full")
    saved = json.loads(config_path.read_text(encoding="utf-8"))["slides"]
    assert saved["slide_001"]["status"] == "stale_audio"
    assert saved["slide_002"]["status"] == "done"
    assert saved["full"]["status"] == "stale_audio"
    assert sha256_file(audio) != "old"
