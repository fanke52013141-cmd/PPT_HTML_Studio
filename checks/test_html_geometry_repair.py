import copy
import json

import pytest

import html_geometry_repair as geometry
import html_scene_editing as editor
from checks.test_html_scene_repair import page as page


def fixture_geometry():
    nodes = [{'id': 'label', 'type': 'text', 'presentation': {'offsetY': -10}},
             {'id': 'arrow', 'type': 'arrow', 'from': {'objectId': 'source', 'point': {'x': 1, 'y': .5}},
              'to': {'objectId': 'destination', 'point': {'x': 0, 'y': .5}}},
             {'id': 'source', 'type': 'card'}, {'id': 'destination', 'type': 'figure'}]
    frame = {'geometry': {'arrow': {'from': {'x': 100, 'y': 200}, 'to': {'x': 400, 'y': 200}}},
             'boxes': {'label': {'x': 240, 'y': 180, 'width': 80, 'height': 40},
                       'source': {'x': 0, 'y': 150, 'width': 100, 'height': 100}},
             'textRects': {'label': [{'x': 240, 'y': 180, 'width': 80, 'height': 30}]},
             'visible': {'label': 1, 'arrow': 1}}
    issue = {'code': 'TEMPORAL_OVERLAP', 'targets': ['label', 'arrow'],
             'measured': {'reason': 'stroke_crosses_text'}}
    return {'scene': {'nodes': nodes}}, {'issues': [issue]}, [frame]


def test_bounded_deterministic_proposals_preserve_input_and_absolute_values():
    doc, report, frames = fixture_geometry()
    before = copy.deepcopy((doc, report, frames))
    proposals = geometry.propose(doc, ['label'], report, frames)
    assert proposals and proposals == geometry.propose(doc, ['label'], report, frames)
    assert proposals == sorted(proposals, key=lambda p: (p['rank'], json.dumps(p['operations'], sort_keys=True)))
    presentation = [p for p in proposals if p['operations'][0]['kind'] == 'set_presentation']
    endpoints = [p for p in proposals if p['operations'][0]['kind'] == 'set_endpoint_point']
    assert presentation
    for p in presentation:
        op = p['operations'][0]
        assert op['targetId'] == 'label'
        assert set(op['values']) <= {'offsetX', 'offsetY'}
        for key, value in op['values'].items():
            assert abs(value-doc['scene']['nodes'][0]['presentation'].get(key, 0)) <= 96
    for p in endpoints:
        op = p['operations'][0]
        assert op['targetId'] == 'arrow'
        assert set(op['values']) <= {'from', 'to'}
        assert all(0 <= coordinate <= 1 for point in op['values'].values()
                   for coordinate in point.values())
    assert (doc, report, frames) == before


def test_unsupported_conflicts_or_scope_do_not_generate_faux_fixes():
    doc, report, frames = fixture_geometry()
    # Declared point endpoints now get deterministic attachment-point candidates.
    endpoints = geometry.propose(doc, ['arrow'], report, frames)
    assert endpoints and all(p['operations'][0]['kind'] == 'set_endpoint_point' for p in endpoints)
    report['issues'][0]['measured']['reason'] = 'stroke_crosses_object'
    assert geometry.propose(doc, ['arrow'], report, frames) == []
    assert geometry.propose(doc, ['label'], report, frames) == []
    with pytest.raises(ValueError):
        geometry.propose(doc, ['missing'], report, frames)


def test_size_proposals_have_explicit_conservative_bounds():
    doc, report, frames = fixture_geometry()
    proposals = geometry.propose(doc, ['source'], report, frames)
    for p in proposals:
        values = p['operations'][0]['values']
        if 'width' in values:
            assert 75 <= values['width'] <= 115
        assert not set(values) & {'height', 'fontSizePx', 'from', 'to'}


def test_existing_figure_containment_is_kept_by_numeric_filter():
    doc, report, frames = fixture_geometry()
    frames[0]['boxes']['destination'] = {'x': 220, 'y': 100, 'width': 120, 'height': 200}
    proposals = [p for p in geometry.propose(doc, ['label'], report, frames) if 'x' in p['delta']]
    assert proposals
    for proposal in proposals:
        delta = proposal['delta']
        assert 240+delta['x'] >= 220 and 320+delta['x'] <= 340


def test_original_guard_rejects_protected_candidate_before_browser(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    doc['manual'] = {'protected_paths': [['scene', 'nodes', 'headline', 'presentation']]}
    monkeypatch.setattr(editor, 'load_editor', lambda *_: copy.deepcopy(doc))
    raw = run / 'raw.json'
    raw.write_text('{"frames": []}', encoding='utf-8')
    monkeypatch.setattr(geometry.repair, 'evidence', lambda *_: {'passed': False, 'measurements_path': 'raw.json'})
    monkeypatch.setattr(geometry, 'propose', lambda *_: [{'operations': [{'targetId': 'headline',
        'kind': 'set_presentation', 'values': {'offsetX': 16}}], 'rank': [0, 1, 1]}])
    result = geometry.geometry_repair(run, scene['id'], {'expected_revision': doc['revision'], 'scope': ['headline']})
    assert result['status'] == 'needs_revision' and result['author_unchanged']
    assert result['attempts'][0]['code'] == 'MANUAL_FIELD_PROTECTED'


def test_full_validation_budget_is_bounded_and_never_accepts_only_sampled_pass(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    (run / 'raw.json').write_text('{"frames": []}', encoding='utf-8')
    monkeypatch.setattr(geometry.repair, 'evidence', lambda *_: {'passed': False, 'measurements_path': 'raw.json'})
    monkeypatch.setattr(geometry, 'propose', lambda *_: [{'operations': [{'targetId': 'headline',
        'kind': 'set_presentation', 'values': {'offsetX': i}}], 'rank': [0, i, i]} for i in range(20)])
    requests = []
    def preview(run, slide, body):
        requests.append(body)
        return {'review': {'passed': body['sampling_mode'] == 'sampled', 'issues': [], 'evidence_dir': 'local'}}
    monkeypatch.setattr(geometry.repair, 'preview_repair', preview)
    result = geometry.geometry_repair(run, scene['id'], {'expected_revision': doc['revision'],
                              'scope': ['headline'], 'time_range_ms': [100, 200]})
    assert result['status'] == 'needs_revision' and len(requests) == 9
    assert sum(r['sampling_mode'] == 'sampled' for r in requests) == 6
    assert sum(r['sampling_mode'] == 'output_frames' for r in requests) == 3
    assert all(r['time_range_ms'] is None and r['fps'] == 30 and r['source'] == 'ai' for r in requests)


def test_clear_page_is_noop_and_scope_cannot_expand(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    monkeypatch.setattr(geometry.repair, 'evidence', lambda *_: {'passed': True})
    result = geometry.geometry_repair(run, scene['id'], {'expected_revision': doc['revision'], 'scope': ['headline']})
    assert result['status'] == 'unchanged' and result['attempts'] == []
    for scope in ([], ['missing'], ['headline', 'headline']):
        with pytest.raises(ValueError):
            geometry.geometry_repair(run, scene['id'], {'expected_revision': doc['revision'], 'scope': scope})


def test_stale_audio_stops_before_browser_or_candidate(page):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    with pytest.raises(editor.SceneEditError) as caught:
        geometry.geometry_repair(run, scene['id'], {'expected_revision': doc['revision'],
                'scope': ['headline'], 'expected_audio_revision': 'f'*64})
    assert caught.value.code == 'AUDIO_REVISION_CONFLICT'


def test_slot_arrow_uses_shared_svg_segments_and_keeps_input_immutable():
    doc, report, frames = fixture_geometry()
    doc['scene']['nodes'][1] = {'id': 'arrow', 'type': 'arrow'}
    frames[0]['geometry']['arrow'] = {'kind': 'arrow', 'box': {'x': 100, 'y': 190, 'width': 300, 'height': 20}}
    frames[0]['vectorPaths'] = {'arrow': [{'d': 'M 100 200 H 400 M 390 190 L 400 200 L 390 210',
        'matrix': [1, 0, 0, 1, 0, 0], 'radius': 2, 'supported': True}]}
    before = copy.deepcopy((doc, report, frames))
    proposals = geometry.propose(doc, ['label'], report, frames)
    assert proposals and all(p['operations'][0]['targetId'] == 'label' for p in proposals)
    assert (doc, report, frames) == before
    report['issues'].append({**report['issues'][0], 'measured': {'reason': 'stroke_crosses_object'}})
    assert geometry.propose(doc, ['label'], report, frames)
    report['issues'].append({'code': 'TEMPORAL_OVERLAP', 'targets': ['source', 'arrow'],
                             'measured': {'reason': 'stroke_crosses_object'}})
    assert geometry.propose(doc, ['label'], report, frames) == []
    report['issues'] = before[1]['issues']
    # Curves are not silently approximated by their box or by a fake endpoint.
    frames[0]['vectorPaths']['arrow'][0]['d'] = 'M100 200 Q200 180 400 200'
    assert geometry.propose(doc, ['label'], report, frames) == []
