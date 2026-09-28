"""Resolve portable, application-managed voice reference recordings."""

from __future__ import annotations

from pathlib import Path

from repository_paths import MODEL_VOICE_REFERENCES_DIR, REPO_ROOT


def resolve_reference_audio_path(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    path = Path(raw)
    if path.is_file():
        return str(path.resolve())
    root = Path(MODEL_VOICE_REFERENCES_DIR)
    if not path.is_absolute():
        candidate = (Path(REPO_ROOT) / path).resolve()
        if candidate.is_file() and candidate.parent == root.resolve():
            return str(candidate)
    # Old portable packages stored an absolute path under their previous
    # installation's data/model_voice_references directory.  Rebind only that
    # known managed location, never an arbitrary missing user file.
    parts = [part.lower() for part in path.parts]
    if len(parts) >= 3 and parts[-3:-1] == ["data", "model_voice_references"]:
        candidate = root / path.name
        if candidate.is_file():
            return str(candidate.resolve())
    return raw
