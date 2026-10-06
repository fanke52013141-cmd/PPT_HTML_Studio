"""Isolated CPU worker: align known speech, returning measured characters only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    import nltk
    nltk_root = Path(data["models_dir"]) / "nltk_data"
    # The Chinese character aligner only needs sentence boundaries. A
    # conservative built-in Punkt configuration avoids a network-only English
    # tokenizer dependency; Chinese punctuation stays in the known speech block.
    punkt_dir = nltk_root / "tokenizers" / "punkt_tab" / "english"
    if not (punkt_dir / "ortho_context.tab").exists():
        punkt_dir.parent.mkdir(parents=True, exist_ok=True)
        from nltk.tokenize.punkt import PunktParameters, save_punkt_params
        save_punkt_params(PunktParameters(), dir=str(punkt_dir))
    nltk.data.path.insert(0, str(nltk_root))
    import whisperx
    import torch
    torch.set_num_threads(4)
    audio = whisperx.load_audio(data["audio"])
    from whisperx.alignment import load_align_model, align
    from huggingface_hub import snapshot_download
    model_path = snapshot_download(repo_id=data["model"], revision=data["model_revision"],
        cache_dir=data["models_dir"], local_files_only=True) if any(
        Path(data["models_dir"]).glob("**/pytorch_model.bin")) else snapshot_download(
        repo_id=data["model"], revision=data["model_revision"], cache_dir=data["models_dir"],
        allow_patterns=["config.json", "preprocessor_config.json", "vocab.json", "special_tokens_map.json", "pytorch_model.bin"])
    model, metadata = load_align_model(language_code="zh", device="cpu", model_name=model_path,
                                       model_cache_only=True)
    result = align([{"text": data["text"], "start": 0, "end": len(audio) / 16000}],
                   model, metadata, audio, "cpu", interpolate_method="ignore", return_char_alignments=True)
    tokens = []
    failed_ranges = set()
    index = 0
    for segment in result["segments"]:
        for char in segment.get("chars", []):
            # chars includes spaces/punctuation in original order. Verify the
            # correspondence rather than matching a repeated character globally.
            while index < len(data["text"]) and data["text"][index].isspace() and char.get("char") != data["text"][index]:
                index += 1
            if index >= len(data["text"]) or char.get("char") != data["text"][index]:
                raise ValueError("alignment character mapping changed")
            origin = data["mapping"][index]
            index += 1
            start, end, score = char.get("start"), char.get("end"), char.get("score")
            if (not origin or not origin.get("range") or start is None or end is None or score is None
                    or not all(math.isfinite(float(v)) for v in (start, end, score))
                    or end <= start or float(score) < 0.35):
                if origin and origin.get("range"):
                    import unicodedata
                    character = char.get("char", "")
                    if character and not character.isspace() and not unicodedata.category(character).startswith("P"):
                        failed_ranges.add((origin["beat_id"], tuple(origin["range"])))
                continue
            if char["char"].lower() not in metadata["dictionary"]:
                failed_ranges.add((origin["beat_id"], tuple(origin["range"])))
                continue
            tokens.append({**origin, "text": char["char"], "start": start, "end": end,
                           "score": score, "source": "forced_alignment", "precision": "character"})
    tokens = [token for token in tokens if (token["beat_id"], tuple(token["range"])) not in failed_ranges]
    if not tokens:
        raise ValueError("未测得可靠字符时间，请人工试听校准")
    payload = {"schema_version": 1, "time_reference": "audio", "tokens": tokens,
               "cache_key": data["cache_key"], "audio_hash": data["cache_key"]["audio_hash"],
               "narration_hash": data["cache_key"]["narration_hash"],
               "engine": {"engine_version": data["cache_key"]["engine_version"], "model": data["model"]}}
    args.output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
