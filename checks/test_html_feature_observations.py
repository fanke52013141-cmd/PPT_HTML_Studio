"""Observation coverage survives unsupported allocation; uncertainty never retries."""
import copy
import json
from pathlib import Path

from PIL import Image
import pytest

from artifact_fingerprint import sha256_json
from checks.html_design_agent_fixture import response_for
from html_design_agent import component_context, validate_understanding, understand_design, ObservedUnderstanding
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from scripts.evaluate_feature_recognition import prediction

ROOT = Path(__file__).resolve().parents[1]


def scene():
    return json.loads((ROOT / 'html_engine/visual/fixtures/labeled-explanation/scene.json').read_text(encoding='utf-8'))


def response(context):
    return response_for({'artifact_prefix': 'design_understanding-test', 'user_prompt': json.dumps(context)})


def test_supported_image_is_observed_even_without_duplicate_feature_declaration():
    context = component_context(scene(), ROOT)
    raw = response(context)
    parsed = validate_understanding(raw, context, require_observations=True)
    assert parsed['status'] == 'ready'
    assert parsed['feature_observations'] == raw['feature_observations']
    image = next(n['id'] for n in context['objects'] if n['type'] == 'image')
    assert prediction(raw, image, 'independent_illustration')[0] is True
    assert raw == response(context)


def test_observed_gap_is_derived_without_discarding_other_observations():
    context = component_context(scene(), ROOT)
    raw = response(context)
    target = next(n['id'] for n in context['objects'] if n['type'] == 'card')
    next(o for o in raw['feature_observations'] if o['targetId'] == target)['presence'] = 'present'
    before = copy.deepcopy(raw)
    parsed = validate_understanding(raw, context, require_observations=True)
    assert parsed['status'] == 'unsupported' and parsed['objects'] == []
    assert parsed['issues'][0]['targetId'] == target
    assert parsed['issues'][0]['route'] == 'capabilities'
    assert parsed['feature_observations'] == raw['feature_observations'] and raw == before
    raw.update(status='unsupported', objects=[], issues=parsed['issues'])
    assert validate_understanding(raw, context, require_observations=True)['feature_observations'] == before['feature_observations']
    assert prediction(raw, target, 'independent_illustration')[0] is True


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'unknown', 'blank', 'conflict', 'omitted'])
def test_new_protocol_rejects_incomplete_or_contradictory_observations(mutation):
    context = component_context(scene(), ROOT)
    raw = response(context)
    if mutation == 'missing': raw['feature_observations'].pop()
    if mutation == 'duplicate': raw['feature_observations'].append(copy.deepcopy(raw['feature_observations'][0]))
    if mutation == 'unknown': raw['feature_observations'][0]['targetId'] = 'unregistered'
    if mutation == 'blank': raw['feature_observations'][0]['evidence'] = '   '
    if mutation == 'conflict':
        raw['feature_observations'][0]['presence'] = 'absent'
        raw['objects'][0]['required_features'] = ['independent_illustration']
    if mutation == 'omitted': raw.pop('feature_observations')
    with pytest.raises(ValueError):
        validate_understanding(raw, context, require_observations=True)


@pytest.mark.parametrize('after_structural_repair', [False, True])
def test_uncertainty_preserves_hash_bound_evidence_without_extra_request(tmp_path, after_structural_repair):
    s = scene()
    reference = tmp_path / 'reference.png'
    Image.new('RGB', (1600, 900), 'white').save(reference)
    calls, events = [], []

    def generator(**kwargs):
        calls.append(kwargs)
        raw = response(json.loads(kwargs['user_prompt']))
        if after_structural_repair and len(calls) == 1:
            raw.pop('feature_observations')
        else:
            raw['feature_observations'][0]['presence'] = 'uncertain'
        return raw

    with pytest.raises(HtmlReviewError) as caught:
        understand_design(s, reference, run_dir=tmp_path, deps=HtmlReviewDependencies(ROOT, generator), progress=events.append)
    assert caught.value.code == 'DESIGN_FEATURE_OBSERVATIONS_UNCERTAIN'
    assert len(calls) == (2 if after_structural_repair else 1)
    assert events[-1]['next_action']['automatic_retry'] is False
    assert events[-1]['next_action']['routes'] == ['evidence_review']
    diagnostics = list(tmp_path.glob('planning/html_visual/candidates/*/design-understanding/**/diagnostic.json'))
    diagnostic = next(json.loads(p.read_text(encoding='utf-8')) for p in diagnostics
                      if json.loads(p.read_text(encoding='utf-8'))['code'] == 'DESIGN_FEATURE_OBSERVATIONS_UNCERTAIN')
    raw = response(component_context(s, ROOT))
    raw['feature_observations'][0]['presence'] = 'uncertain'
    assert diagnostic['response_sha256'] == sha256_json(raw)
    assert len(diagnostic['observations']) == 1
    assert not list(tmp_path.glob('**/result.json'))


def test_legacy_missing_table_stays_readable_but_is_not_valid_new_output():
    context = component_context(scene(), ROOT)
    raw = response(context)
    raw.pop('feature_observations')
    assert validate_understanding(raw, context)['feature_observations'] is None
    assert prediction(raw, raw['objects'][0]['targetId'], 'independent_illustration', require_observations=True)[0] is None
    with pytest.raises(ValueError): ObservedUnderstanding.model_validate(raw)


def test_partial_observations_do_not_improve_score_by_shrinking_coverage():
    context = component_context(scene(), ROOT)
    raw = response(context)
    raw['feature_observations'] = raw['feature_observations'][:1]
    assert prediction(raw, raw['feature_observations'][0]['targetId'], 'independent_illustration',
                      expected_targets={n['id'] for n in context['objects']}) == (None, 'incomplete_feature_observations')


def test_raw_issue_misclassification_cannot_bypass_observed_capability_gap():
    from scripts.evaluate_feature_recognition import gap_prediction
    context = component_context(scene(), ROOT)
    raw = response(context)
    target = next(n['id'] for n in context['objects'] if n['type'] == 'card')
    next(o for o in raw['feature_observations'] if o['targetId'] == target)['presence'] = 'present'
    raw.update(status='unsupported', objects=[], issues=[{
        'targetId': target, 'route': 'capabilities', 'requirement': 'asset_identity',
        'evidence': 'Controlled example: model used the wrong requirement name'}])
    assert gap_prediction(raw, target) is None  # Do not rewrite raw-model metrics.
    result = validate_understanding(raw, context, require_observations=True)
    assert any(i['targetId'] == target and i['requirement'] == 'unsupported_presentation'
               for i in result['issues'])
