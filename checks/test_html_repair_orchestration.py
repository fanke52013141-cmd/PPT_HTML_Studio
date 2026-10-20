import copy

import pytest

import html_repair_orchestration as flow
import html_scene_editing as editor
import html_visual_store as store
from checks.test_html_scene_repair import page as page


def body(doc):
    return {'expected_revision': doc['revision'], 'scope': ['headline'],
            'instruction': flow.OVERLAP_INSTRUCTION, 'strategy': 'geometry_first'}


def forbidden():
    pytest.fail('Geometry path must not acquire a model')


def test_geometry_candidate_uses_original_key_and_changes_without_provider_or_save(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    request = body(doc)
    candidate = flow.repair.candidate(run, scene['id'], {**{k:v for k,v in request.items() if k == 'expected_revision'},
        'scope': ['headline'], 'operations': [{'targetId': 'headline', 'kind': 'set_presentation', 'values': {'offsetX': 8}}]})
    candidate.update(review={'passed': True, 'issues': [], 'frame_count': 10}, status='candidate')
    monkeypatch.setattr(flow.geometry, 'geometry_repair', lambda *_: {'status': 'candidate', 'candidate': candidate,
        'baseline': {'passed': False}, 'attempts': [{}], 'elapsed_seconds': 1})
    result = flow.generate_repair(run, scene['id'], request, forbidden)
    assert result['candidate_key'] == candidate['candidate_key']
    assert result['repair_path']['origin'] == 'geometry'
    assert result['changes'] == [{'targetId': 'headline', 'parameter': 'offsetX',
        'before': doc['scene']['nodes'][0].get('presentation', {}).get('offsetX'), 'after': 8}]
    assert editor.load_editor(run, scene['id']) == doc


def test_clear_page_does_not_fall_back_or_write(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    monkeypatch.setattr(flow.geometry, 'geometry_repair', lambda *_: {'status': 'unchanged',
        'baseline': {'passed': True}, 'attempts': [], 'elapsed_seconds': 1})
    result = flow.generate_repair(run, scene['id'], body(doc), forbidden)
    assert result['status'] == 'unchanged' and 'candidate_key' not in result
    assert editor.load_editor(run, scene['id']) == doc


def test_no_legal_geometry_falls_back_once_with_frozen_audio_and_full_checks(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    monkeypatch.setattr(flow.geometry, 'geometry_repair', lambda *_: {'status': 'needs_revision', 'candidate': None,
        'baseline': {'passed': False}, 'attempts': [{}, {}], 'elapsed_seconds': 2})
    calls = []
    generator = object()
    def model(r, s, request, supplied):
        calls.append(copy.deepcopy(request))
        assert supplied is generator
        return {'status': 'unsupported', 'message': '需要人工调整'}
    monkeypatch.setattr(flow.repair, 'generate_repair', model)
    factory_calls = []
    def factory():
        factory_calls.append(True)
        return generator
    result = flow.generate_repair(run, scene['id'], {**body(doc), 'time_range_ms': [1, 2]}, factory)
    assert len(calls) == len(factory_calls) == 1
    assert calls[0]['expected_audio_revision'] == doc['audio_revision']
    assert calls[0]['sampling_mode'] == 'output_frames' and calls[0]['fps'] == 30
    assert calls[0]['time_range_ms'] is None and calls[0]['overlap_policy'] == 'registered'
    assert result['repair_path']['fallback_reason'] and result['repair_path']['origin'] == 'model'
    assert editor.load_editor(run, scene['id']) == doc


def test_identity_goal_and_scope_failures_never_call_model(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    for patch, code in [({'instruction': '改文案'}, 'REPAIR_GEOMETRY_GOAL'),
                        ({'scope': ['headline', 'headline']}, 'REPAIR_SCOPE'),
                        ({'scope': ['missing']}, 'TARGET_NODE_GONE')]:
        with pytest.raises(editor.SceneEditError) as caught:
            flow.generate_repair(run, scene['id'], {**body(doc), **patch}, forbidden)
        assert caught.value.code == code
    with pytest.raises(store.HtmlVisualConflict):
        flow.generate_repair(run, scene['id'], {**body(doc), 'expected_revision': 999}, forbidden)
    with pytest.raises(editor.SceneEditError, match='配音产物已变化'):
        flow.generate_repair(run, scene['id'], {**body(doc), 'expected_audio_revision': 'f'*64}, forbidden)


def test_legacy_default_model_keeps_custom_goal(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    requests = []
    monkeypatch.setattr(flow.repair, 'generate_repair', lambda r,s,b,g: requests.append(b) or {'status': 'needs_input'})
    flow.generate_repair(run, scene['id'], {'expected_revision': doc['revision'], 'scope': ['headline'],
        'instruction': '调整字号'}, lambda: object())
    assert requests[0]['strategy'] == 'model' and requests[0]['instruction'] == '调整字号'


def test_unknown_geometry_error_does_not_replay_or_fall_back(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    def fail(*_):
        raise RuntimeError('checker unavailable')
    monkeypatch.setattr(flow.geometry, 'geometry_repair', fail)
    with pytest.raises(RuntimeError, match='checker unavailable'):
        flow.generate_repair(run, scene['id'], body(doc), forbidden)


def test_model_fallback_rejects_style_edits_before_original_preview(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    monkeypatch.setattr(flow.repair, 'evidence', lambda *_: {'passed': False, 'issues': []})
    monkeypatch.setattr(flow.repair, 'preview_repair', lambda *_: pytest.fail('Style edit reached preview'))
    calls = []
    def generator(**kwargs):
        calls.append(kwargs)
        return {'status': 'candidate', 'operations': [{'targetId': 'headline',
            'kind': 'set_text_style', 'part': 'text', 'values': {'fontSizePx': 12}}]}
    with pytest.raises(editor.SceneEditError) as caught:
        flow.repair.generate_repair(run, scene['id'], body(doc), generator)
    assert caught.value.code == 'REPAIR_EXHAUSTED' and len(calls) == 2
    assert 'REPAIR_GEOMETRY_ONLY' in calls[1]['user_prompt']
    assert editor.load_editor(run, scene['id']) == doc


def test_comparison_uses_matching_fault_and_final_times_only(tmp_path):
    for name in ('a', 'b', 'c', 'd'):
        (tmp_path / name).write_bytes(b'png-fixture')
    baseline = {'screenshots': [{'timeMs': 0, 'file': 'a'}, {'timeMs': 500, 'file': 'b'}, {'timeMs': 1000, 'file': 'c'}],
                'issues': [{'timeMs': 490}]}
    candidate = {'screenshots': [{'timeMs': 0, 'file': 'a'}, {'timeMs': 500, 'file': 'd'}, {'timeMs': 1000, 'file': 'c'}]}
    result = flow._comparison(tmp_path, baseline, candidate)
    assert [s['timeMs'] for s in result['before']] == [500, 1000]
    assert [s['timeMs'] for s in result['after']] == [500, 1000]


def test_model_exception_has_explicit_fallback_reason_and_never_replays(page, monkeypatch):
    run, scene = page
    doc = editor.load_editor(run, scene['id'])
    monkeypatch.setattr(flow.geometry, 'geometry_repair', lambda *_: {'status': 'needs_revision', 'candidate': None,
        'baseline': {'passed': False}, 'attempts': [], 'elapsed_seconds': 1})
    calls = []
    def failed(*args):
        calls.append(True)
        raise TimeoutError('private provider details')
    monkeypatch.setattr(flow.repair, 'generate_repair', failed)
    with pytest.raises(editor.SceneEditError) as caught:
        flow.generate_repair(run, scene['id'], body(doc), lambda: object())
    assert caught.value.code == 'REPAIR_MODEL_UNVERIFIED' and len(calls) == 1
    assert '几何试算未找到合法候选' in str(caught.value) and 'private' not in str(caught.value)
    assert editor.load_editor(run, scene['id']) == doc
