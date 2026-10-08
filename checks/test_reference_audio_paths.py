from pathlib import Path

import reference_audio_paths as references


def test_managed_reference_rebinds_after_portable_directory_move(tmp_path: Path, monkeypatch) -> None:
    new_root = tmp_path / "new-app"
    managed = new_root / "data" / "model_voice_references"
    managed.mkdir(parents=True)
    recording = managed / "connection-123.wav"
    recording.write_bytes(b"reference-audio")
    monkeypatch.setattr(references, "REPO_ROOT", str(new_root))
    monkeypatch.setattr(references, "MODEL_VOICE_REFERENCES_DIR", str(managed))

    assert references.resolve_reference_audio_path(
        "data/model_voice_references/connection-123.wav"
    ) == str(recording.resolve())
    old = Path("D:/old-app/data/model_voice_references/connection-123.wav")
    assert references.resolve_reference_audio_path(str(old)) == str(recording.resolve())
    assert references.resolve_reference_audio_path("D:/other/missing.wav") == "D:/other/missing.wav"
