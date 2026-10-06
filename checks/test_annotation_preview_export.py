"""Export snapshots remain isolated and clean up failed renders."""
import copy
import json
from types import SimpleNamespace

import pytest
import annotation_preview_export as exporter


def prepared():
    return {"timeline": {"fps": 30, "canvas": [320, 180], "slide_duration_sec": 1, "events": []},
            "scene": {"canvas": {}, "layers": [{"asset": "visual_draft.png"}]},
            "audio_timeline": {}, "animation_timeline": {"events": []}}


def test_export_copies_snapshot_and_cleans_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "REPO_ROOT", tmp_path)
    slide = tmp_path / "slide"
    slide.mkdir()
    (slide / "visual_draft.png").write_bytes(b"image")
    (slide / "voice.mp3").write_bytes(b"audio")
    data = prepared()
    original = copy.deepcopy(data)
    def render(args, **kwargs):
        from pathlib import Path
        props = Path(args[6].removeprefix("--props="))
        payload = json.loads(props.read_text(encoding="utf-8"))
        assert payload["slides"][0]["audio_file"].startswith("runtime/annotation_previews/")
        Path(args[5]).write_bytes(b"mp4")
        return SimpleNamespace(returncode=0, stderr="")
    monkeypatch.setattr(exporter, "run_subprocess_killable", render)
    token = exporter.export_preview(slide, data)
    assert (slide / "preview_exports" / f"{token}.mp4").read_bytes() == b"mp4"
    assert data == original
    assert not list((tmp_path / "scripts/remotion/public/runtime/annotation_previews").iterdir())


def test_export_rejects_escape_and_removes_scratch(tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "REPO_ROOT", tmp_path)
    slide = tmp_path / "slide"
    slide.mkdir()
    (tmp_path / "secret.png").write_bytes(b"secret")
    data = prepared()
    data["scene"]["layers"][0]["asset"] = "../secret.png"
    with pytest.raises(ValueError):
        exporter.export_preview(slide, data)
    assert not list((tmp_path / "scripts/remotion/public/runtime/annotation_previews").iterdir())
