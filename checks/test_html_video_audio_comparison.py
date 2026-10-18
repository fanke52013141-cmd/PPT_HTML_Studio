"""Independent audio-verifier regressions: joins, dropped speech and wrong pages."""
import numpy as np
import pytest

from scripts.verify_html_video_frames import compare_course_audio

RATE = 8000


def voice(samples, frequency):
    time = np.arange(samples) / RATE
    return .2 * np.sin(2 * np.pi * (frequency * time + 311 * time * time))


def inputs():
    sources = [voice(3000, 233), voice(4400, 617)]
    schedule = [{'slide_id': 'first', 'frames': 10, 'offset_frames': 0},
                {'slide_id': 'second', 'frames': 15, 'offset_frames': 10}]
    encoded = np.concatenate([sources[0], np.zeros(200), sources[1], np.zeros(400)])
    return sources, schedule, encoded


def test_aligned_distinct_pages_and_boundary_pass():
    sources, schedule, encoded = inputs()
    result = compare_course_audio(sources, schedule, encoded, 25, RATE)
    assert result['status'] == 'passed' and result['length_passed']
    assert [p['offset_samples'] for p in result['pages']] == [0, 3200]
    assert len(result['boundaries']) == 1
    assert all(p['lag_samples'] == 0 for p in result['pages'])


@pytest.mark.parametrize('damage', ['reordered', 'global_delay', 'second_page_delay', 'truncated', 'muted'])
def test_page_and_boundary_errors_are_not_hidden_by_alignment(damage):
    sources, schedule, encoded = inputs()
    if damage == 'reordered':
        encoded = np.concatenate([encoded[3200:], encoded[:3200]])
    elif damage == 'global_delay':
        encoded = np.concatenate([np.zeros(400), encoded])
    elif damage == 'second_page_delay':
        encoded = np.concatenate([encoded[:3200], np.zeros(400), sources[1]])
    elif damage == 'truncated':
        encoded = encoded[:-800]
    else:
        encoded[:] = 0
    result = compare_course_audio(sources, schedule, encoded, 25, RATE)
    assert result['status'] == 'failed'
    if damage == 'second_page_delay':
        assert result['pages'][0]['status'] == 'passed'
        assert result['pages'][1]['status'] == 'failed'


def test_source_speech_beyond_frame_budget_fails_even_when_export_matches_trimmed_signal():
    sources, schedule, _ = inputs()
    sources = [voice(4000, 233), voice(4800, 617)]
    result = compare_course_audio(sources, schedule, np.concatenate([sources[0][:3200], sources[1]]), 25, RATE)
    assert result['pages'][0]['zero_lag_correlation'] > .999
    assert result['pages'][0]['lost_source_signal'] and result['status'] == 'failed'


def test_silent_join_is_checked_for_glitches_without_claiming_speech_evidence():
    source = np.zeros(8000)
    source[2400:5600] = voice(3200, 233)
    schedule = [{'slide_id': 'first', 'frames': 25, 'offset_frames': 0},
                {'slide_id': 'second', 'frames': 25, 'offset_frames': 25}]
    actual = np.concatenate([source, source])
    result = compare_course_audio([source, source], schedule, actual, 25, RATE)
    assert result['status'] == 'passed' and result['boundaries'][0]['signal'] == 'silent_window'
    actual[8000] = .3
    result = compare_course_audio([source, source], schedule, actual, 25, RATE)
    assert result['boundaries'][0]['status'] == 'failed'


@pytest.mark.parametrize('damage', ['gap', 'duplicate_id', 'invalid_samples', 'missing_page'])
def test_malformed_audio_evidence_is_rejected(damage):
    sources, schedule, actual = inputs()
    if damage == 'gap':
        schedule[1]['offset_frames'] += 1
    elif damage == 'duplicate_id':
        schedule[1]['slide_id'] = schedule[0]['slide_id']
    elif damage == 'invalid_samples':
        sources[0][0] = np.nan
    else:
        sources.pop()
    with pytest.raises(ValueError):
        compare_course_audio(sources, schedule, actual, 25, RATE)


def test_single_page_preserves_existing_lag_fields():
    sources, schedule, actual = inputs()
    result = compare_course_audio(sources[:1], schedule[:1], actual[:3200], 25, RATE)
    assert result['status'] == 'passed' and result['lag_samples'] == 0 and result['lag_ms'] == 0


def test_fractional_frame_clock_has_contiguous_sample_boundaries():
    sources = [voice(8008, 233), voice(8008, 617)]
    schedule = [{'slide_id': 'first', 'frames': 30, 'offset_frames': 0},
                {'slide_id': 'second', 'frames': 30, 'offset_frames': 30}]
    result = compare_course_audio(sources, schedule, np.concatenate(sources), 29.97, RATE)
    assert result['status'] == 'passed'
    assert result['sample_count'] == 16016 and result['pages'][1]['offset_samples'] == 8008
