import copy

from html_repair_feedback import repair_report, repair_screenshots


def test_conflicts_keep_text_parts_ranges_and_raw_evidence_immutable():
    issues = [{'code': 'TEMPORAL_OVERLAP', 'targets': ['arrow', 'chart'], 'timeMs': t,
               'measured': {'reason': 'stroke_crosses_text', 'textRect': {'part': part}}}
              for part in ('chart:min', 'chart:max') for t in (100, 200, 300)]
    report = {'issues': issues, 'coverage': {'times': [100, 200, 300], 'time_sha256': 'pinned'},
              'relationContacts': [{'timeMs': 100}], 'frame_count': 3}
    before = copy.deepcopy(report)
    reduced = repair_report(report)
    assert len(reduced['issues']) == 2 and reduced['rawIssueCount'] == 6
    assert all(i['sampleCount'] == 3 and i['firstTimeMs'] == 100 and i['lastTimeMs'] == 300 for i in reduced['issues'])
    assert reduced['coverage'] == {'timeCount': 3, 'time_sha256': 'pinned'}
    assert 'relationContacts' not in reduced and report == before


def test_images_prioritize_conflict_and_keep_final_state_with_matching_frame_times():
    report = {'screenshots': [{'timeMs': t, 'file': f'{t}.png'} for t in (0, 50, 100, 150, 200, 250)],
              'issues': [{'code': 'TEMPORAL_OVERLAP', 'timeMs': 200}],
              'frames': [{'timeMs': t} for t in (0, 50, 100, 150, 200, 250)]}
    shots = repair_screenshots(report)
    assert len(shots) == 4 and 200 in [s['timeMs'] for s in shots] and shots[-1]['timeMs'] == 250
    assert [f['timeMs'] for f in repair_report(report)['frames']] == [s['timeMs'] for s in shots]


def test_scoped_measurements_keep_all_neighbour_boxes_without_changing_global_checks():
    report = {'screenshots': [{'timeMs': 100, 'file': 'a.png'}],
              'frames': [{'timeMs': 100, 'boxes': {'target': {}, 'neighbour': {}},
                          'geometry': {'target': {}, 'neighbour': {}, 'other-arrow': {'kind': 'arrow', 'from': {'x': 10}}},
                          'textRects': {'target': [], 'neighbour': []}}],
              'overlapPairs': [['target', 'neighbour'], ['other', 'neighbour']],
              'reference_geometry': {'target': {}, 'neighbour': {}}, 'issues': []}
    before = copy.deepcopy(report)
    projected = repair_report(report, {'target'}, ['target'])
    assert projected['frames'][0]['boxes'] == report['frames'][0]['boxes']
    assert projected['frames'][0]['textRects'] == {'target': []}
    assert projected['frames'][0]['geometry']['other-arrow'] == report['frames'][0]['geometry']['other-arrow']
    assert projected['checkedPairCount'] == 2 and len(projected['overlapPairs']) == 1
    assert report == before
