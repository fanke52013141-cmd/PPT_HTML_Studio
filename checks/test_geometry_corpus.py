"""Corpus provenance, preserved author guards and physical request stop policy."""
import copy
import json
from types import SimpleNamespace
import time

import pytest

import html_scene_editing as editor
import html_scene_repair as repair
from checks.test_html_scene_repair import page as page
from pipeline_lifecycle import write_json_atomic
from scripts import benchmark_capacity as baseline
from scripts.evaluate_geometry_corpus import LiveFallback, fallback_eligible, metrics, validate_cases


def test_repeated_archived_versions_do_not_count_as_independent_pages():
    rows = [{'id': str(i), 'course_id': 'course', 'page_id': 'page',
             'provenance': 'archived_candidate', 'status': 'candidate',
             'baseline_passed': False} for i in range(3)]
    rows.append({'id': 'fixture', 'course_id': 'test', 'page_id': 'test',
                 'provenance': 'fixture', 'status': 'unchanged', 'baseline_passed': True})
    result = metrics(rows)
    assert result['archived_candidate']['cases'] == 3
    assert result['archived_candidate']['distinct_pages'] == 1
    assert result['original']['cases'] == 0
    assert result['fixture']['geometry_case_hit_rate'] is None


def test_cases_require_provenance_and_safe_nonduplicated_identity():
    case = {'id': 'case', 'course_id': 'course', 'page_id': 'page', 'source_run': 'run',
            'slide_id': 'slide_001', 'source_note': 'Archived model output',
            'provenance': 'archived_candidate', 'scope': ['label']}
    assert validate_cases([case]) == [case]
    for invalid in ({**case, 'id': '../escape'}, {**case, 'provenance': 'real'},
                    {**case, 'scope': ['label', 'label']}, {**case, 'slide_id': '../scene'}):
        with pytest.raises(ValueError):
            validate_cases([invalid])
    with pytest.raises(ValueError):
        validate_cases([case, copy.deepcopy(case)])


def test_freezing_retains_revision_and_manual_protection(page, tmp_path_factory, monkeypatch):
    run, scene = page
    write_json_atomic(run / 'planning/html_visual/revision.json', {'revision': 7})
    write_json_atomic(editor.edit_path(run, scene['id']), {
        'protected_paths': [['scene', 'nodes', 'headline', 'presentation']]})
    write_json_atomic(run / 'planning/html_visual/approved.json', {'approved': True})
    monkeypatch.setattr(baseline, 'review_scene', lambda *a, **k: {'passed': True})
    monkeypatch.setattr(baseline, 'source_identity', lambda: {'working_tree_sha256': 'frozen'})
    output = tmp_path_factory.mktemp('corpus-parent') / 'frozen'
    baseline.run_course_baseline(run, output, [scene['id']])
    frozen = output / 'isolated-run'
    assert editor.load_editor(frozen, scene['id'])['revision'] == 7
    assert not (frozen / 'planning/html_visual/approved.json').exists()
    request = {'expected_revision': 7, 'source': 'ai', 'scope': ['headline'], 'operations': [
        {'targetId': 'headline', 'kind': 'set_presentation', 'values': {'offsetX': 8}}]}
    with pytest.raises(editor.SceneEditError) as caught:
        repair.candidate(frozen, scene['id'], request)
    assert caught.value.code == 'MANUAL_FIELD_PROTECTED'
    manifest = json.loads((output / 'course-manifest.json').read_text(encoding='utf-8'))
    assert 'planning/html_visual/edits-' + scene['id'] + '.json' in manifest['files']


def test_live_requires_crossing_and_keeps_other_moments_of_same_pair():
    text = {'code': 'TEMPORAL_OVERLAP', 'targets': ['arrow', 'label'],
            'measured': {'reason': 'stroke_crosses_text'}}
    object_hit = {**text, 'measured': {'reason': 'stroke_crosses_object'}}
    assert fallback_eligible({'issues': [text, object_hit]})
    assert not fallback_eligible({'issues': [object_hit]})
    assert not fallback_eligible({'issues': [text, {**object_hit, 'targets': ['arrow', 'other']}]})


def test_unknown_transport_is_persisted_and_never_replayed(tmp_path):
    budget = LiveFallback(tmp_path, tmp_path, 60)
    budget.started = time.monotonic()
    client = SimpleNamespace(with_options=lambda **_: None)
    def unknown(*args, **kwargs):
        raise TimeoutError('unknown outcome')
    with pytest.raises(TimeoutError):
        budget.measured(unknown, client, {})
    assert json.loads((tmp_path / 'http-calls.json').read_text()) == budget.calls
    with pytest.raises(ValueError, match='no replay'):
        budget.measured(unknown, client, {})
    assert len(budget.calls) == 1


def test_format_fallback_and_json_repair_share_two_physical_calls(tmp_path):
    budget = LiveFallback(tmp_path, tmp_path, 60)
    budget.started = time.monotonic()
    client = SimpleNamespace(with_options=lambda **_: None)
    response = SimpleNamespace(usage=None)
    for _ in range(2):
        assert budget.measured(lambda *a, **kw: response, client, {}) is response
    with pytest.raises(ValueError, match='budget'):
        budget.measured(lambda *a, **kw: response, client, {})
    assert len(budget.calls) == 2
