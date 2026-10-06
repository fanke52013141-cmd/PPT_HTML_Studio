from dataclasses import replace

import pytest

from annotation_alignment import resolve_anchor_times
from annotation_alignment_worker import normalized_transcript
from annotation_timeline import build_annotation_timeline
from checks.test_annotation_timeline import _item


def fixture_tokens():
    item = _item()
    item = replace(item, anchor=replace(item.anchor, range_start=0, range_end=2, quote='标注'))
    tokens = [{'beat_id': item.anchor.beat_id, 'range': [i, i+1], 'start': 1+i*.12,
               'end': 1.1+i*.12, 'precision': 'character', 'source': 'forced_alignment',
               'score': .99} for i in range(2)]
    return item, tokens


@pytest.mark.parametrize('change', [
    {'score': .2}, {'score': None}, {'score': float('nan')},
    {'start': 1, 'end': 2.2}, {'start': .8, 'end': .9},
])
def test_weak_or_nonmonotonic_alignment_needs_manual_review(change):
    item, tokens = fixture_tokens()
    tokens[1].update(change)
    assert not resolve_anchor_times([item], {'tokens': tokens})


def test_valid_alignment_and_provider_without_score_remain_usable():
    item, tokens = fixture_tokens()
    assert resolve_anchor_times([item], {'tokens': tokens})[item.annotation_id]['start'] == 1
    for token in tokens:
        token['source'] = 'provider_word'
        del token['score']
    assert resolve_anchor_times([item], {'tokens': tokens})


def test_manual_audio_calibration_overrides_ai_and_adds_delay_once():
    item, _ = fixture_tokens()
    item = replace(item, timing=replace(item.timing, trigger_mode='manual',
                                       manual_start_sec=1.011, time_reference='audio'))
    timeline, issues = build_annotation_timeline(
        slide_id='slide_001', items=[item], beat_times={item.anchor.beat_id: (0, 3)},
        slide_duration=5, image_hash='a', narration_hash='b', audio_hash='c',
        confirmed_input_hashes={}, audio_start_sec=.5, require_precise=True,
        anchor_times={item.annotation_id: {'start': 3, 'end': 3.3, 'source': 'forced_alignment'}})
    assert not issues
    assert timeline['events'][0]['start_sec'] == pytest.approx(46/30)


def test_silent_punctuation_never_consumes_acoustic_character_or_changes_occurrence():
    text, mapping = normalized_transcript([{'beat_id': 'b', 'spoken_text': '标注，随后讲到“标注”。'}])
    assert text == '标注随后讲到标注 '
    assert mapping[6]['range'] == [8, 9]
    assert mapping[7]['range'] == [9, 10]
    assert len(text) == len(mapping)


def test_percentage_expansion_survives_punctuation_removal():
    text, mapping = normalized_transcript([{'beat_id': 'b', 'spoken_text': '增长20%，结束。'}])
    assert text == '增长百分之二十结束 '
    assert all(entry['range'] == [2, 5] for entry in mapping[2:7])
    assert mapping[7]['range'] == [6, 7]
