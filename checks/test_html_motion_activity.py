import pytest
from html_motion_activity import motion_activity


def scene(starts, durations):
    return {'durationMs': 18000, 'beats': [{'id': 'explain', 'startMs': 6000, 'endMs': 18000}],
            'motion': [{'actionId': f'a{i}', 'targetId': f'n{i}', 'type': 'enter',
                        'startMs': start, 'durationMs': duration}
                       for i, (start, duration) in enumerate(zip(starts, durations))]}


def test_detects_static_lesson_despite_existing_motion():
    report = motion_activity(scene([6000]*8, [500]*8))
    beat = report['beats'][0]
    assert beat['active_ms'] == 500  # overlapping actions are not eight times as active
    assert beat['longest_static_interval_ms'] == [6500, 18000]
    assert set(beat['warnings']) == {'long_static_interval', 'simultaneous_short_entrances'}


def test_staggered_draw_schedule_and_intro_do_not_trigger_group_warning():
    assert motion_activity(scene([6000, 8000, 10000, 13000, 16000], [1500]*5))['status'] == 'no_schedule_warning'
    assert motion_activity(scene([6000], [500]))['beats'][0]['warnings'] == []


def test_clips_cross_beat_actions_and_counts_empty_intervals():
    report = motion_activity(scene([5000, 17000], [2000, 2000]))
    assert report['beats'][0]['active_ms'] == 2000
    assert motion_activity(scene([], []))['beats'][0]['static_fraction'] == 1
    bound = scene([6000]*3, [500]*3)
    bound['beats'][0].pop('id')  # actual binder emits subtitle segments without semantic IDs
    assert motion_activity(bound)['beats'][0]['beat_index'] == 0


@pytest.mark.parametrize('duration', [-1, float('nan'), float('inf')])
def test_invalid_motion_is_not_scored_as_good(duration):
    with pytest.raises(ValueError):
        motion_activity(scene([6000], [duration]))
