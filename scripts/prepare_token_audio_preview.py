"""Prepare an isolated Token audio review sample with the existing TTS adapter."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from html_asset_sheet_store import persist_sheet_candidates
from html_visual_store import save_scene
from runtime_support import run_subprocess_killable
from tts_provider_service import (
    TtsProviderDependencies,
    configure_tts_provider_dependencies,
    configured_tts_api_key,
    provider_tts_command,
    provider_tts_environment,
    _redact_tts_process_output,
)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    run = ROOT / "outputs/image25-sheet/token-production-v1"
    if run.exists():
        raise SystemExit("Refusing to replace an existing audio experiment")
    previous = (
        ROOT / "outputs/image25-sheet/toapis-bulb-reference-v1/extraction-2-clean"
    )
    spec = json.loads((previous / "spec.json").read_text(encoding="utf-8"))
    # Concept callout anchor, explicit author definition; not a scientific part label.
    spec["slots"][0]["anchors"] = [{"id": "focus", "x": 994, "y": 547}]
    candidate = persist_sheet_candidates(
        run, (previous / "source.png").read_bytes(), spec
    )
    write(run / "candidate-evidence.json", candidate)
    entry = dict(candidate["manifest"]["assets"][0])
    entry["file"] = candidate["directory"] + "/asset-bulb.png"
    write(
        run / "planning/draft_preview/resources.json",
        {"purpose": "unapproved_draft_preview_only", "assets": [entry]},
    )
    scene = json.loads(
        (ROOT / "outputs/image25-sheet/token-palette-v2/scene-draft.json").read_text(
            encoding="utf-8"
        )
    )
    scene["themeRef"]["id"] = "amber-science"
    save_scene(run, scene["id"], scene, expected_revision=0)
    slide = run / "slides" / scene["id"]
    slide.mkdir(parents=True)
    narration = "Token 是模型处理文本时使用的基本单位。\n一个 Token 不一定对应一个完整的词，也可以是词的一部分或标点。\nToken 数量不等于字数，具体切分由分词器决定。\n许多服务按输入和输出 Token 计算用量和费用。"
    text = slide / "tts_text.txt"
    text.write_text(narration, encoding="utf-8")
    connection = sqlite3.connect(
        (ROOT / "data/projects.db").resolve().as_uri() + "?mode=ro", uri=True
    )
    try:
        settings = dict(connection.execute("SELECT key,value FROM settings"))
    finally:
        connection.close()
    configure_tts_provider_dependencies(
        TtsProviderDependencies(
            get_setting=lambda key, default=None: settings.get(key, default),
            write_project_log=lambda *args, **kwargs: None,
        )
    )
    key = configured_tts_api_key("minimax")
    if not key:
        raise SystemExit("MiniMax credential unavailable")
    if settings.get("tts_provider", "minimax") != "minimax":
        raise SystemExit("This experiment expects the configured MiniMax provider")
    env = provider_tts_environment(key, "")
    env["FFPROBE_BIN"] = (
        "C:/Users/Administrator/AppData/Local/Programs/FFmpeg/bin/ffprobe.exe"
    )
    command = provider_tts_command(
        provider="minimax",
        text_file=str(text),
        out_audio=str(slide / "voice.mp3"),
        out_meta=str(slide / "tts_metadata.json"),
        out_srt=str(slide / "subtitles.srt"),
        out_timeline=str(slide / "audio_timeline.json"),
        slide_id=scene["id"],
        endpoint=settings["tts_endpoint"],
        region=settings.get("tts_region", ""),
        model=settings["tts_model"],
        voice_id=settings["tts_voice_id"],
        clone_voice_id=settings.get("tts_clone_voice_id", ""),
        provider_extra=settings.get("tts_provider_extra", ""),
        speed=settings.get("tts_speed", "1.2"),
        volume=settings.get("tts_volume", "1"),
        pitch=settings.get("tts_pitch", "0"),
    )
    result = run_subprocess_killable(
        command,
        env=env,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout_sec=600,
    )
    safe_stdout = _redact_tts_process_output(result.stdout, env)
    safe_stderr = _redact_tts_process_output(result.stderr, env)
    write(
        run / "tts-execution.json",
        {
            "provider": "minimax",
            "model": settings["tts_model"],
            "returncode": result.returncode,
            "stdout": safe_stdout[-1000:],
            "stderr": safe_stderr[-1500:],
            "audio_confirmation": "pending_user_listening",
            "production_export": "not_started",
        },
    )
    print(
        json.dumps(
            {
                "run": str(run),
                "tts_returncode": result.returncode,
                "audio_exists": (slide / "voice.mp3").is_file(),
                "error": safe_stderr[-500:] if result.returncode else None,
            },
            ensure_ascii=False,
        )
    )
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
