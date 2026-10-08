"""Validate measured provider words against exact normalized narration order."""
from __future__ import annotations

import math
import unicodedata


def _spoken(text):
    return ''.join(c.lower() for c in text if not c.isspace()
                   and not unicodedata.category(c).startswith('P'))


def provider_word_alignment(timeline, transcript, mapping, *, audio_hash, narration_hash):
    """Accept nested measured words only; display subtitle splits are never used.

    Match the whole spoken sequence so repeated words cannot be searched into
    the wrong occurrence. Each provider word retains its measured interval;
    multi-character words are not subdivided with invented timestamps.
    """
    if (not isinstance(timeline, dict) or not audio_hash
            or timeline.get('provider_timestamps_audio_hash') != audio_hash):
        return None
    expected = [(c, origin) for c, origin in zip(transcript, mapping)
                if _spoken(c)]
    titles = timeline.get('provider_timestamps')
    if not isinstance(titles, list):
        return None
    duration = timeline.get('audio_content_duration_sec')
    if not isinstance(duration, (float, int)) or isinstance(duration, bool) or not math.isfinite(duration):
        return None
    cursor, tokens = 0, []
    for title in titles:
        if not isinstance(title, dict) or not isinstance(title.get('timestamped_words'), list):
            return None
        for word in title['timestamped_words']:
            if not isinstance(word, dict) or not isinstance(word.get('word'), str):
                return None
            text = _spoken(word['word'])
            if not text:
                continue
            actual = ''.join(c for c, _ in expected[cursor:cursor + len(text)])
            if text != actual:
                pronunciation = word.get('pronounce_word')
                text = _spoken(pronunciation) if isinstance(pronunciation, str) else ''
                actual = ''.join(c for c, _ in expected[cursor:cursor + len(text)])
                if not text or text != actual:
                    return None
            try:
                start, end = word['time_begin'] / 1000, word['time_end'] / 1000
                if (isinstance(word['time_begin'], bool) or isinstance(word['time_end'], bool)
                        or not all(math.isfinite(v) for v in (start, end))
                        or start < 0 or end <= start or end > duration + .05):
                    return None
            except (KeyError, TypeError, ValueError):
                return None
            if tokens and start < tokens[-1]['end'] - .04:
                return None
            origins = [origin for _, origin in expected[cursor:cursor + len(text)]]
            cursor += len(text)
            if not all(origin and origin.get('range') for origin in origins):
                continue
            if len({origin['beat_id'] for origin in origins}) != 1:
                continue
            bounds = [min(o['range'][0] for o in origins), max(o['range'][1] for o in origins)]
            tokens.append({'beat_id': origins[0]['beat_id'], 'range': bounds,
                           'text': word['word'], 'start': start, 'end': end,
                           'source': 'provider_word', 'precision': 'word'})
    if cursor != len(expected) or not tokens:
        return None
    return {'schema_version': 1, 'time_reference': 'audio', 'tokens': tokens,
            'audio_hash': audio_hash, 'narration_hash': narration_hash,
            'engine': {'engine_version': 'minimax_nested_words_v1', 'adapter': 'provider_word'}}
