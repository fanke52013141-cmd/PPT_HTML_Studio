"""Behavioral regressions for the 2026-10-04 audit fixes."""
from pathlib import Path
from types import SimpleNamespace
import copy
import sys

import pytest
from fastapi import HTTPException

import digital_human_routes as routes
from repository_paths import resolve_comfyui_tts_workflow_path
from runtime_support import run_subprocess_killable


def test_audio_export_failure_cleans_temporary_files(tmp_path, monkeypatch):
    project = SimpleNamespace(id="p", run_dir=str(tmp_path))
    audio = tmp_path / "voice.mp3"
    audio.write_bytes(b"audio")
    output = tmp_path / "presenter" / "full.mp3"
    monkeypatch.setattr(routes, "_project_or_404", lambda *args: project)
    monkeypatch.setattr(routes, "read_contract_slide_ids", lambda *args: ["slide_001"])
    monkeypatch.setattr(routes, "_slide_audio_path", lambda *args: audio)
    monkeypatch.setattr(routes, "_full_audio_path", lambda *args: output)
    monkeypatch.setattr(routes, "_find_ffmpeg", lambda: "fake-ffmpeg")
    monkeypatch.setattr(routes.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr="transcode failed"))
    with pytest.raises(HTTPException) as exc:
        routes.export_full_audio("p", {}, None)
    assert exc.value.status_code == 500
    assert not (output.parent / ".tmp_audio_export").exists()


@pytest.mark.parametrize("field", ["output", "base_video"])
def test_composite_rejects_files_outside_project(tmp_path, monkeypatch, field):
    project = SimpleNamespace(id="p", run_dir=str(tmp_path / "project"))
    digi = tmp_path / "presenter.mp4"
    digi.write_bytes(b"video")
    monkeypatch.setattr(routes, "_project_or_404", lambda *args: project)
    monkeypatch.setattr(routes, "_load_config", lambda *args: {"mode": "upload"})
    monkeypatch.setattr(routes, "_upload_digi_path", lambda *args: digi)
    monkeypatch.setattr(routes, "get_digital_human_client", lambda: pytest.fail("must reject before contacting service"))
    with pytest.raises(HTTPException) as exc:
        routes.compose_dh_slide("p", "slide_001", {field: str(tmp_path / "outside.mp4")}, None)
    assert exc.value.status_code == 400
    assert not (tmp_path / "outside.mp4").exists()


def test_composite_uses_downloadable_default_path(tmp_path, monkeypatch):
    project = SimpleNamespace(id="p", run_dir=str(tmp_path))
    digi = tmp_path / "presenter.mp4"
    digi.write_bytes(b"video")
    base = tmp_path / "videos" / "base.mp4"
    base.parent.mkdir()
    base.write_bytes(b"base")
    calls = []
    def composite(**kwargs):
        calls.append(kwargs)
        return {"success": True}
    monkeypatch.setattr(routes, "_project_or_404", lambda *args: project)
    monkeypatch.setattr(routes, "_load_config", lambda *args: {"mode": "upload"})
    monkeypatch.setattr(routes, "_upload_digi_path", lambda *args: digi)
    monkeypatch.setattr(routes, "get_digital_human_client", lambda: SimpleNamespace(composite=composite))
    result = routes.compose_dh_slide("p", "slide_001", {"base_video": "videos/base.mp4"}, None)
    assert Path(calls[0]["base_video"]) == base.resolve()
    assert Path(calls[0]["output"]) == (routes._digi_dir(project) / "composite_slide_001.mp4").resolve()
    assert result["output_url"].endswith("/composite/slide_001/video")


def test_workflow_resolver_accepts_bundled_fallback_and_relative_override(tmp_path):
    bundled = tmp_path / "config" / "indextts2_5_comfyui_workflow.json"
    bundled.parent.mkdir()
    bundled.write_text("{}")
    assert resolve_comfyui_tts_workflow_path("http://localhost:8188", tmp_path) == bundled
    assert resolve_comfyui_tts_workflow_path("custom.json", tmp_path) == tmp_path / "custom.json"
    legacy = tmp_path / "data" / "digital_human" / "comfyui_tts_workflow.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("{}")
    assert resolve_comfyui_tts_workflow_path("", tmp_path) == legacy


def test_killable_subprocess_returns_timeout_and_releases_pipes():
    result = run_subprocess_killable([sys.executable, "-c", "import time; time.sleep(30)"], timeout_sec=0.1, capture_output=True, text=True)
    assert result.returncode == 124
    assert "Timed out" in result.stderr


def test_protected_mask_groups_do_not_count_as_ai_updates():
    import ai_mask_engine as mask
    from checks.test_ai_mask_automation import _mask_element
    protected = {"id": "body", "visual_group_id": "body", "review_status": "locked", "box": {"x": 0, "y": 0, "w": 1, "h": 1}}
    page = {"slide_id": "slide_001", "groups": [copy.deepcopy(protected)], "semantic_blocks": [copy.deepcopy(protected)]}
    manifest = {"slides": [page]}
    elements = {"canvas": {"width": 320, "height": 180}, "elements": [_mask_element("e", 20, 20, 40, 30)]}
    matches = {"matches": [{"group_id": "body", "element_ids": ["e"], "confidence": 0.95}]}
    result = mask._apply(manifest, {"slide_id": "slide_001", "visual_groups": [{"id": "body", "role": "body"}]}, elements, matches, mask.normalize_settings({}))
    assert result["updated"] == 0
    assert result["skipped"] >= 1
    assert page["groups"][0]["box"] == protected["box"]


def test_tts_stage_is_removed_when_command_preparation_fails(tmp_path, monkeypatch):
    import json
    import tts_service as tts
    project = SimpleNamespace(id="tts-cleanup", run_dir=str(tmp_path))
    planning = tmp_path / "planning"
    planning.mkdir()
    (planning / "visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": "slide_001"}]}))
    profile = dict.fromkeys(["provider", "project_runtime", "snapshot_value", "tts_api_key", "tts_secret_key", "runtime_secrets", "endpoint", "model", "voice_id", "clone_voice_id", "region", "provider_extra", "speed", "volume", "pitch", "concurrency", "requests_per_minute", "cache_key"])
    profile.update(provider="comfyui_tts", cache_key={}, runtime_secrets={}, concurrency=1)
    monkeypatch.setattr(tts, "project_or_404", lambda *args: project)
    monkeypatch.setattr(tts, "_resolve_tts_voice_profile", lambda *args: profile)
    monkeypatch.setattr(tts, "_load_beats_by_slide", lambda *args: {})
    monkeypatch.setattr(tts.invalidation_service, "narration_synthesis_started", lambda *args: None)
    text = tmp_path / "text.txt"
    text.write_text("narration")
    paths = {key: str(tmp_path / (key + ".txt")) for key in ("text", "audio", "metadata", "srt", "timeline")}
    monkeypatch.setattr(tts, "slide_tts_artifact_paths", lambda *args: paths)
    monkeypatch.setattr(tts, "ensure_slide_tts_text_file", lambda *args: str(text))
    monkeypatch.setattr(tts, "slide_tts_artifact_status", lambda *args: {"complete": False})
    real_mkdtemp = tts.tempfile.mkdtemp
    created = []
    def tracked_mkdtemp(**kwargs):
        assert "dir" not in kwargs
        path = real_mkdtemp(**kwargs)
        created.append(Path(path))
        return path
    def fail_command(**kwargs):
        raise RuntimeError("preparation failed")
    monkeypatch.setattr(tts.tempfile, "mkdtemp", tracked_mkdtemp)
    monkeypatch.setattr(tts, "provider_tts_command", fail_command)
    with pytest.raises(RuntimeError, match="preparation failed"):
        tts.synthesize_tts_resumable(project.id, SimpleNamespace(commit=lambda: None))
    assert len(created) == 1
    assert not created[0].exists()
