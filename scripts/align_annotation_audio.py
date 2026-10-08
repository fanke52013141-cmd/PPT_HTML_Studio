"""Offline Qwen worker; never interpolate missing character times."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def map_tokens(text, mapping, items, repaired, duration):
    """Map the complete sequence in order, quarantining repaired ranges."""
    spoken = [(i, char) for i, char in enumerate(text) if not char.isspace()]
    if len(mapping) != len(text) or ''.join(item['text'] for item in items).lower() != ''.join(c for _, c in spoken).lower():
        raise ValueError('对齐文字与讲稿不一致，请人工校准')
    cursor, tokens, failed = 0, [], set()
    for number, item in enumerate(items):
        positions = [i for i, _ in spoken[cursor:cursor + len(item['text'])]]
        cursor += len(item['text'])
        origins = [mapping[i] for i in positions]
        valid_origins = [origin for origin in origins if origin and origin.get('range')]
        start, end = item['start'], item['end']
        usable = (len(valid_origins) == len(origins) and bool(origins)
                  and all(math.isfinite(v) for v in (start, end))
                  and 0 <= start < end <= duration + .04
                  and number * 2 not in repaired and number * 2 + 1 not in repaired
                  and len({origin['beat_id'] for origin in valid_origins}) == 1)
        if not usable:
            failed.update((origin['beat_id'], tuple(origin['range'])) for origin in valid_origins)
            continue
        bounds = [min(origin['range'][0] for origin in origins), max(origin['range'][1] for origin in origins)]
        tokens.append({'beat_id': origins[0]['beat_id'], 'range': bounds,
                       'text': item['text'], 'start': start, 'end': end,
                       'source': 'qwen_alignment', 'precision': 'character' if len(item['text']) == 1 else 'word'})
    return [token for token in tokens if not any(
        beat == token['beat_id'] and bounds[0] < token['range'][1] and bounds[1] > token['range'][0]
        for beat, bounds in failed)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    import torch
    from huggingface_hub import snapshot_download
    from qwen_asr import Qwen3ForcedAligner
    from qwen_asr.inference.qwen3_forced_aligner import Qwen3ForceAlignProcessor
    from qwen_asr.inference.utils import normalize_audios

    class AuditedProcessor(Qwen3ForceAlignProcessor):
        def parse_timestamp(self, words, timestamps):
            self.raw = timestamps.tolist()
            result = super().parse_timestamp(words, timestamps)
            fixed = [v for item in result for v in (item['start_time'], item['end_time'])]
            self.repaired = [i for i, (raw, final) in enumerate(zip(self.raw, fixed)) if raw != final]
            return result

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    model_path = snapshot_download(data['model'], revision=data['model_revision'],
                                   cache_dir=data['models_dir'], local_files_only=True)
    model = Qwen3ForcedAligner.from_pretrained(model_path, dtype=torch.bfloat16,
        device_map='cpu', local_files_only=True, low_cpu_mem_usage=True, attn_implementation='sdpa')
    model.aligner_processor = AuditedProcessor()
    audio = normalize_audios(data['audio'])[0]
    result = model.align(audio=(audio, 16000), text=data['text'], language='Chinese')[0]
    items = [{'text': item.text, 'start': item.start_time, 'end': item.end_time} for item in result.items]
    tokens = map_tokens(data['text'], data['mapping'], items, model.aligner_processor.repaired, len(audio) / 16000)
    if not tokens:
        raise ValueError('未测得有效时间，请人工试听校准')
    payload = {'schema_version': 1, 'time_reference': 'audio', 'tokens': tokens,
        'cache_key': data['cache_key'], 'audio_hash': data['cache_key']['audio_hash'],
        'narration_hash': data['cache_key']['narration_hash'],
        'engine': {'engine_version': data['cache_key']['engine_version'], 'model': data['model'],
                   'model_revision': data['model_revision']},
        'diagnostics': {'raw_timestamp_ms': model.aligner_processor.raw,
                        'repaired_indices': model.aligner_processor.repaired}}
    args.output.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
