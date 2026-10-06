"""Bounded isolated alignment execution, with deterministic original-text mapping."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import tempfile
import threading
import unicodedata
from pathlib import Path

from annotation_build import AnnotationBuildError, file_hash, read_json
from repository_paths import ANNOTATION_WORKER_PYTHON, ANNOTATION_WORKER_SCRIPT, ANNOTATION_ALIGNMENT_MODELS_DIR
from runtime_support import run_subprocess_bounded

_WORKER_GATE = threading.BoundedSemaphore(1)
ENGINE_VERSION = "qwen_forced_aligner_0_6b_v1"
MODEL = "Qwen/Qwen3-ForcedAligner-0.6B"
MODEL_REVISION = "c7cbfc2048c462b0d63a45797104fc9db3ad62b7"


def normalized_transcript(beats):
    """Map real TTS text back to visible narration; changed spans are one-to-many.

    Punctuation/tags are omitted only from alignment. Unknown pronunciations are
    left to the engine's dictionary and quality gate instead of guessing seconds.
    """
    from narration_audio_service import beat_tts_text
    from scripts.minimax_tts import strip_tts_markup
    text, mapping = [], []
    for beat in beats:
        original = str(beat.get("spoken_text") or "")
        spoken = strip_tts_markup(beat_tts_text(beat))
        ranges = [None] * len(spoken)
        for tag, a, b, c, d in difflib.SequenceMatcher(None, original, spoken, autojunk=False).get_opcodes():
            if tag == "equal":
                for index in range(c, d):
                    ranges[index] = [a + index - c, a + index - c + 1]
            elif tag == "replace" and b > a:
                # An arbitrary TTS rewrite has no verified pronunciation map.
                # Preserve unmapped spans for manual review rather than assigning
                # every replacement character to an unrelated original phrase.
                continue
        # Expand common percentages only, retaining original range. Other
        # ambiguous numeric pronunciations remain unavailable for manual review.
        expansions = {}
        for match in re.finditer(r"(?<!\d)(\d{1,2})%", spoken):
            number = int(match[1])
            digits = "零一二三四五六七八九"
            reading = digits[number] if number < 10 else (
                (digits[number // 10] if number >= 20 else "") + "十" + (digits[number % 10] if number % 10 else ""))
            bounds = [ranges[match.start()][0], ranges[match.end() - 1][1]] if ranges[match.start()] and ranges[match.end() - 1] else None
            expansions[match.start()] = (match.end(), "百分之" + reading, bounds)
        index = 0
        while index < len(spoken):
            if index in expansions:
                end, reading, bounds = expansions[index]
                text.extend(reading)
                mapping.extend({"beat_id": str(beat.get("id") or beat.get("beat_id")), "range": bounds} for _ in reading)
                index = end
                continue
            # Silent punctuation has no acoustic interval. Preserve the original
            # codepoint map across skipped marks.
            if unicodedata.category(spoken[index]).startswith("P"):
                index += 1
                continue
            text.append(spoken[index].lower())
            mapping.append({"beat_id": str(beat.get("id") or beat.get("beat_id")), "range": ranges[index]})
            index += 1
        text.append(" ")
        mapping.append(None)
    return "".join(text), mapping


def run_alignment(slide_dir, beats, cancel_event):
    directory = Path(slide_dir)
    audio = directory / "voice.mp3"
    if not audio.is_file():
        raise AnnotationBuildError([{"reason": "missing_audio"}])
    transcript, mapping = normalized_transcript(beats)
    if not Path(ANNOTATION_WORKER_PYTHON).is_file():
        raise AnnotationBuildError([{"reason": "alignment_worker_unavailable"}])
    key = {"audio_hash": file_hash(audio), "narration_hash": file_hash(directory / "narration_beats.json"),
           "engine_version": ENGINE_VERSION, "model": MODEL, "model_revision": MODEL_REVISION,
           "transcript_hash": hashlib.sha256(transcript.encode()).hexdigest()}
    existing = read_json(directory / "word_alignment.json", optional=True)
    if existing and existing.get("cache_key") == key:
        return existing
    while not _WORKER_GATE.acquire(timeout=0.25):
        if cancel_event.is_set():
            return None
    try:
        if cancel_event.is_set():
            return None
        with tempfile.TemporaryDirectory(prefix="annotation-align-") as temporary:
            request, response = Path(temporary) / "input.json", Path(temporary) / "output.json"
            request.write_text(json.dumps({"audio": str(audio.resolve()), "text": transcript,
                "mapping": mapping, "model": MODEL, "model_revision": MODEL_REVISION, "models_dir": ANNOTATION_ALIGNMENT_MODELS_DIR,
                "cache_key": key}, ensure_ascii=False), encoding="utf-8")
            result = run_subprocess_bounded(
                [ANNOTATION_WORKER_PYTHON, ANNOTATION_WORKER_SCRIPT, "--input", str(request), "--output", str(response)],
                timeout_sec=600, capture_output=True, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
            if result.returncode == 124:
                raise RuntimeError("Qwen 音频定位超时，请缩短单页音频或人工试听校准")
            if result.returncode != 0:
                # Keep diagnostic tail without credentials or binary response data.
                raise RuntimeError("音频定位失败: " + str(result.stderr or result.stdout)[-1200:])
            return read_json(response)
    finally:
        _WORKER_GATE.release()
