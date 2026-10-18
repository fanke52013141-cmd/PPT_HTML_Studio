"""Read-only schedule diagnostics; motion existence is not visual quality."""

import math


def motion_activity(scene):
    """Use already audio-bound milliseconds, never infer timing from prose."""
    duration = scene['durationMs']
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid scene duration')
    actions = scene['motion']
    for action in actions:
        if any(type(action[k]) not in (int, float) or not math.isfinite(action[k])
               for k in ('startMs', 'durationMs')) or action['durationMs'] < 0:
            raise ValueError('Invalid motion interval')
    windows = scene.get('beats') or [{'id': 'page', 'startMs': 0, 'endMs': duration}]
    reports = []
    for index, beat in enumerate(windows):
        start, end = beat['startMs'], beat['endMs']
        if not 0 <= start < end <= duration:
            raise ValueError('Invalid beat interval')
        selected = [a for a in actions if a['startMs'] < end and a['startMs'] + a['durationMs'] > start]
        intervals = sorted((max(start, a['startMs']), min(end, a['startMs'] + a['durationMs'])) for a in selected)
        cursor, active, gaps = start, 0, []
        for left, right in intervals:
            if left > cursor:
                gaps.append([cursor, left])
            active += max(0, right - max(left, cursor))
            cursor = max(cursor, right)
        if cursor < end:
            gaps.append([cursor, end])
        longest = max(gaps, key=lambda g: g[1] - g[0], default=[start, start])
        targets = sorted({a['targetId'] for a in selected})
        # Explanatory groups only: a lone introductory title need not keep moving.
        warnings = []
        if len(targets) >= 3 and longest[1] - longest[0] >= max(4000, (end - start) * .6):
            warnings.append('long_static_interval')
        enters = [a for a in selected if a['type'] == 'enter']
        if (len({a['targetId'] for a in enters}) >= 3 and end - start >= 4000
                and max(a['startMs'] for a in enters) - min(a['startMs'] for a in enters) <= 100
                and max(a['durationMs'] for a in enters) <= 1000):
            warnings.append('simultaneous_short_entrances')
        reports.append({'beat_id': beat.get('id'), 'beat_index': index, 'start_ms': start, 'end_ms': end,
                        'target_ids': targets, 'active_ms': active,
                        'static_fraction': 1 - active / (end - start),
                        'longest_static_interval_ms': longest, 'warnings': warnings})
    return {'format': 'hps.html.motion_activity', 'version': '0.1.0',
            'status': 'warning' if any(b['warnings'] for b in reports) else 'no_schedule_warning',
            'beats': reports,
            'limits': 'Schedule only; not pixel movement, semantic correctness, aesthetic approval or a render gate.'}
