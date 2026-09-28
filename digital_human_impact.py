"""Keep generated presenter media bound to the audio used to create it."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from artifact_fingerprint import sha256_file
from pipeline_lifecycle import read_json_file, write_json_atomic


def mark_presenter_audio_stale(run_dir: str | Path, slide_ids: Iterable[str]) -> tuple[str, ...]:
    root = Path(run_dir)
    path = root / "planning" / "digital_human.json"
    config = read_json_file(path)
    if not isinstance(config, dict) or not isinstance(config.get("slides"), dict):
        return ()
    entries = config["slides"]
    stale: list[str] = []
    for slide_id in dict.fromkeys(str(value) for value in slide_ids):
        item = entries.get(slide_id)
        if not isinstance(item, dict) or not item.get("job_id"):
            continue
        audio_hash = sha256_file(root / "slides" / slide_id / "voice.mp3") or ""
        if item.get("audio_sha256") and item["audio_sha256"] != audio_hash:
            if item.get("status") != "stale_audio":
                item["status"] = "stale_audio"
            stale.append(slide_id)
    full = entries.get("full")
    if stale and isinstance(full, dict) and full.get("job_id"):
        full["status"] = "stale_audio"
        stale.append("full")
    if stale:
        write_json_atomic(path, config)
    return tuple(stale)
