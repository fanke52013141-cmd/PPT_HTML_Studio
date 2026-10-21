"""System-level positive/negative decisions, not hand-repaired course pages."""
import copy
import json
from pathlib import Path

from PIL import Image
import pytest

from html_design_agent import component_context, validate_understanding, review_checklist, review_fidelity, understand_design
from html_review_facts import project_facts, ReviewFactsIncomplete
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from artifact_fingerprint import sha256_json, sha256_file

ROOT = Path(__file__).resolve().parents[1]


def scene():
    return json.loads((ROOT / 'html_engine/visual/fixtures/labeled-explanation/scene.json').read_text(encoding='utf-8'))


def ready(context):
    return {'status': 'ready', 'issues': [], 'objects': [
        {'targetId': n['id'], 'owner': context['capabilities'][n['id']]['owner'],
         'assetMode': context['capabilities'][n['id']]['assetMode'],
         'variant': None, 'icon': None, 'appearance': 'Explicit fixture observation'}
        for n in context['objects']], 'feature_observations': [
            {'targetId': n['id'], 'feature': 'independent_illustration',
             'presence': 'present' if n['type'] == 'image' else 'absent',
             'evidence': 'Controlled visual observation'} for n in context['objects']]}


def facts(s):
    return {'facts': [{**c, 'certainty': 'confirmed', 'evidence': 'Explicit fixture observation',
                      'reference_alignment': None, 'differences': []} for c in review_checklist(s)]}


def test_illustration_fact_cannot_be_satisfied_by_card_icon_or_figure():
    s = scene()
    context = component_context(s, ROOT)
    original = copy.deepcopy(s)
    for n in s['nodes']:
        assert context['capabilities'][n['id']]['currentPresentation']['independent_illustration'] == (n['type'] == 'image')
        for f in context['capabilities'][n['id']]['variantFacts'].values():
            assert f['independent_illustration'] is False
        response = ready(context)
        row = next(r for r in response['objects'] if r['targetId'] == n['id'])
        row['required_features'] = ['independent_illustration']
        next(r for r in response['feature_observations'] if r['targetId'] == n['id'])['presence'] = 'present'
        result = validate_understanding(response, context)
        assert result['status'] == ('ready' if n['type'] == 'image' else 'unsupported')
    card = next(n for n in s['nodes'] if n['type'] == 'card')
    f = context['capabilities'][card['id']]['currentPresentation']
    assert f['visual_content'] == 'registered_icon_only' and not f['image_slot'] and not f['icon_is_illustration']
    assert validate_understanding(ready(context), context)['status'] == 'ready'
    assert s == original


def test_illustration_requirement_stops_after_single_understanding_decision(tmp_path):
    s = scene()
    reference = tmp_path / 'reference.png'
    Image.new('RGB', (1600, 900), 'white').save(reference)
    calls, progress = [], []

    def provider(**kw):
        calls.append(kw)
        assert kw['request_timeout'] == 600 and kw['reasoning_effort_override'] == 'low'
        assert 'design-understanding/0.7.5' in kw['system_prompt']
        assert 'independent_illustration' in json.loads(kw['schema_hint'])['$defs']['Allocation']['properties']['required_features']['items']['enum']
        context = json.loads(kw['user_prompt'])
        response = ready(context)
        card = next(n for n in context['objects'] if n['type'] == 'card')
        next(r for r in response['objects'] if r['targetId'] == card['id'])['required_features'] = ['independent_illustration']
        next(r for r in response['feature_observations'] if r['targetId'] == card['id'])['presence'] = 'present'
        return response

    with pytest.raises(HtmlReviewError) as caught:
        understand_design(s, reference, run_dir=tmp_path,
                          deps=HtmlReviewDependencies(ROOT, provider), progress=progress.append)
    assert caught.value.code == 'DESIGN_ALLOCATION_UNSUPPORTED' and len(calls) == 1
    assert progress[-1]['next_action']['routes'] == ['capabilities']
    assert progress[-1]['next_action']['automatic_retry'] is False
    assert not list(tmp_path.glob('planning/html_visual/scene-*.json'))


def test_all_uncertain_observations_are_retained_without_projection():
    s = {'version': '0.7.0', 'nodes': [{'id': 'subject', 'type': 'image'}, {'id': 'caption', 'type': 'text'}]}
    response = facts(s)
    for row in response['facts']:
        if row['dimension'] in ('asset_identity', 'typography'):
            row['certainty'] = 'uncertain'
    original = copy.deepcopy(response)
    with pytest.raises(ReviewFactsIncomplete) as caught:
        project_facts(response, s, review_checklist(s), {})
    d = caught.value.details
    assert d['route'] == 'evidence_review'
    assert {(r['targetId'], r['dimension']) for r in d['unresolved']} == {('subject', 'asset_identity'), ('caption', 'typography')}
    assert all(r['evidence'] == 'Explicit fixture observation' for r in d['unresolved'])
    assert response == original


def test_checklist_failure_is_response_repair_not_asset_rework():
    s = {'nodes': [{'id': 'subject', 'type': 'image'}]}
    response = facts(s)
    response['facts'].pop()
    response['facts'].append(copy.deepcopy(response['facts'][0]))
    with pytest.raises(ReviewFactsIncomplete) as caught:
        project_facts(response, s, review_checklist(s), {})
    assert caught.value.details['route'] == 'response_repair'
    assert caught.value.details['missing'] == [{'targetId': 'subject', 'dimension': 'asset_rendering'}]
    assert caught.value.details['duplicate'] == [{'targetId': 'subject', 'dimension': 'geometry'}]


def test_uncertainty_audit_binds_sources_emits_stop_and_never_retries(tmp_path):
    s = {'version': '0.7.0', 'nodes': [{'id': 'subject', 'type': 'image', 'slot': 'subject'}]}
    reference = tmp_path / 'reference.png'
    Image.new('RGB', (1600, 900), 'white').save(reference)
    response = facts(s)
    next(r for r in response['facts'] if r['dimension'] == 'asset_identity')['certainty'] = 'uncertain'
    calls, progress = [], []

    def provider(**kw):
        calls.append(kw)
        return copy.deepcopy(response)

    folder = tmp_path / 'review'
    with pytest.raises(HtmlReviewError) as caught:
        review_fidelity(s, reference, reference, {}, None, folder=folder, run_dir=tmp_path,
                        deps=HtmlReviewDependencies(ROOT, provider), progress=progress.append)
    assert caught.value.code == 'DESIGN_REVIEW_COVERAGE_INCOMPLETE' and len(calls) == 1
    diagnostic = json.loads((folder / 'diagnostic.json').read_text(encoding='utf-8'))
    assert diagnostic['details']['unresolved'][0]['dimension'] == 'asset_identity'
    assert diagnostic['scene_sha256'] == sha256_json(s)
    assert diagnostic['response_sha256'] == sha256_json(response)
    assert diagnostic['design_sha256'] == diagnostic['screenshot_sha256'] == sha256_file(reference)
    assert diagnostic['next_action'] == progress[-1]['next_action']
    assert diagnostic['next_action']['routes'] == ['evidence_review']
    assert diagnostic['next_action']['automatic_retry'] is False
    assert not (folder / 'result.json').exists()
    assert json.loads((folder / 'response.json').read_text(encoding='utf-8')) == response
