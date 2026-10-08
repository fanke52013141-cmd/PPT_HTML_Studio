"""A redundant narration save must not clear generated audio or annotation work."""

from pathlib import Path
from types import SimpleNamespace

import narration_service


def test_identical_narration_save_skips_persistence_and_invalidation(tmp_path, monkeypatch):
    project = SimpleNamespace(run_dir=str(tmp_path))
    beats_path = tmp_path / "planning" / "narration_beats.json"
    beats_path.parent.mkdir()
    beats_path.write_text('{"slides": []}', encoding="utf-8")
    confirmation = tmp_path / "planning" / "audio_confirmed.json"
    confirmation.write_text("{}", encoding="utf-8")
    actions = []

    monkeypatch.setattr(narration_service, "project_or_404", lambda *_: project)
    monkeypatch.setattr(narration_service, "prepare_narration_payload", lambda _project, value: value)
    monkeypatch.setattr(narration_service, "persist_narration_beats", lambda *_: actions.append("persist"))
    monkeypatch.setattr(narration_service, "handle_step_navigation", lambda *_: actions.append("complete"))
    result = narration_service.update_step6_result("project", {"slides": []}, object())

    assert result == {"success": True, "changed": False}
    assert actions == []
    assert confirmation.exists()
    assert Path(beats_path).read_text(encoding="utf-8") == '{"slides": []}'
