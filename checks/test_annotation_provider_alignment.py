"""Measured provider timing, occurrence identity, freshness and fallback gates."""
from dataclasses import replace
import hashlib
import json
import threading
from pathlib import Path

import pytest

from annotation_alignment import resolve_anchor_times
from annotation_alignment_worker import normalized_transcript, run_alignment
from annotation_provider_alignment import provider_word_alignment
from checks.test_annotation_timeline import _item


def timeline(text='标注随后标注'):
    words = [{'word': c, 'time_begin': i * 120, 'time_end': (i + 1) * 120}
             for i, c in enumerate(text)]
    return {'provider_timestamps': [{'text': text, 'timestamped_words': words}],
            'provider_timestamps_audio_hash': 'audio', 'audio_content_duration_sec': 2}


def align(payload, text='标注随后标注'):
    transcript, mapping = normalized_transcript([{'beat_id': 'b', 'spoken_text': text}])
    return provider_word_alignment(payload, transcript, mapping, audio_hash='audio', narration_hash='n')


def test_second_occurrence_keeps_exact_original_range():
    result = align(timeline())
    item = _item()
    item = replace(item, anchor=replace(item.anchor, beat_id='b', range_start=4, range_end=6, quote='标注'))
    cue = resolve_anchor_times([item], result, audio_hash='audio', narration_hash='n')[item.annotation_id]
    assert cue['start'] == pytest.approx(.48)
    assert cue['source'] == 'provider_word'


def test_captured_minimax_nested_words_keep_measured_boundaries():
    titles = json.loads((Path(__file__).parent / 'fixtures/annotations/minimax_nested_words.json').read_text(encoding='utf-8'))
    result = align({'provider_timestamps':titles, 'provider_timestamps_audio_hash':'audio',
                    'audio_content_duration_sec':4.93425}, titles[0]['text'])
    assert len(result['tokens']) == 25
    core = next(t for t in result['tokens'] if t['text'] == '核')
    assert core['start'] == pytest.approx(2.1688888888888886)
    assert core['range'] == [13,14]


@pytest.mark.parametrize('change', ['audio', 'missing_word', 'different_text', 'sentence', 'nan', 'overlap'])
def test_bad_provider_result_requires_fallback(change):
    data = timeline()
    words = data['provider_timestamps'][0]['timestamped_words']
    if change == 'audio': data['provider_timestamps_audio_hash'] = 'replaced'
    elif change == 'missing_word': words.pop()
    elif change == 'different_text': words[2]['word'] = '错'
    elif change == 'sentence': del data['provider_timestamps'][0]['timestamped_words']
    elif change == 'nan': words[0]['time_begin'] = float('nan')
    elif change == 'overlap': words[1]['time_begin'] = 0
    assert align(data) is None


def test_partial_word_never_gets_an_invented_character_start():
    data = timeline('核心概念')
    data['provider_timestamps'][0]['timestamped_words'] = [
        {'word': '核心概念', 'time_begin': 0, 'time_end': 480}]
    result = align(data, '核心概念')
    item = _item()
    item = replace(item, anchor=replace(item.anchor, beat_id='b', range_start=2, range_end=4, quote='概念'))
    assert not resolve_anchor_times([item], result)


def test_audio_delays_do_not_shift_provider_audio_clock():
    data = timeline()
    data['audio_start_sec'] = .5
    assert align(data)['tokens'][1]['start'] == pytest.approx(.12)


def test_qwen_is_required_even_when_provider_timestamps_exist(tmp_path, monkeypatch):
    import annotation_alignment_worker as worker
    (tmp_path / 'voice.mp3').write_bytes(b'unique audio')
    (tmp_path / 'narration_beats.json').write_text('{}', encoding='utf-8')
    data = timeline()
    data['provider_timestamps_audio_hash'] = hashlib.sha256(b'unique audio').hexdigest()
    (tmp_path / 'audio_timeline.json').write_text(json.dumps(data), encoding='utf-8')
    monkeypatch.setattr(worker, 'ANNOTATION_WORKER_PYTHON', str(tmp_path / 'unavailable.exe'))
    from annotation_build import AnnotationBuildError
    with pytest.raises(AnnotationBuildError):
        run_alignment(tmp_path, [{'beat_id':'b', 'spoken_text':'标注随后标注'}], threading.Event())


def test_sync_tts_keeps_raw_words_outside_display_subtitle_splitting(tmp_path, monkeypatch):
    import sys
    from scripts import minimax_tts as tts
    titles = timeline()['provider_timestamps']
    titles[0].update(time_begin=0, time_end=720)
    monkeypatch.setattr(sys, 'argv', ['minimax_tts', '--text', '标注随后标注',
        '--api-key', 'test-only', '--endpoint', 'https://example.test/v1/t2a_v2',
        '--subtitle-type', 'word', '--out-audio', str(tmp_path/'voice.mp3'),
        '--out-timeline', str(tmp_path/'audio_timeline.json')])
    seen = []
    def fake_tts(payload, *args):
        seen.append(payload)
        return {'data': {'audio': b'audio'.hex(), 'subtitle_file':'https://example.test/subtitle'},
                'base_resp':{'status_code':0}}
    monkeypatch.setattr(tts, 'call_minimax_tts', fake_tts)
    monkeypatch.setattr(tts, 'request_bytes_with_retry', lambda *a, **k: json.dumps(titles).encode())
    monkeypatch.setattr(tts, 'probe_audio_duration_sec', lambda *a, **k: 2)
    assert tts.main() == 0
    result = json.loads((tmp_path/'audio_timeline.json').read_text(encoding='utf-8'))
    assert seen[0]['subtitle_type'] == 'word'
    assert result['provider_timestamps'] == titles
    assert result['provider_timestamps_audio_hash'] == hashlib.sha256(b'audio').hexdigest()
    transcript, mapping = normalized_transcript([{'beat_id':'b', 'spoken_text':'标注随后标注'}])
    assert provider_word_alignment(result, transcript, mapping,
        audio_hash=result['provider_timestamps_audio_hash'], narration_hash='n')
