import copy
import hashlib
import io
import json

import numpy as np
from PIL import Image
import pytest

from checks.test_html_asset_sheet import fixture, png
from html_asset_sheet import extract_asset_sheet, HtmlAssetSheetError
from html_asset_sheet_cleanup import clean_alpha
from html_asset_sheet_store import persist_sheet_candidates
from html_asset_sheet_review import _candidate, accept_candidate
from html_asset_sheet_assessment import assess_candidates, read_advisory, recommended_action, configured_vision

PARAMS = {'threshold': 1, 'guard_radius': 2, 'max_removed_fraction': .02}
FINDING = {'identity': 'match', 'edge': 'clean', 'extra_content': False, 'reason': '主体完整'}


def test_cleanup_preserves_subject_soft_edges_and_input():
    a = np.zeros((32, 32, 4), dtype=np.uint8)
    a[12:20, 12:20] = (20, 40, 60, 128)
    a[11, 12] = (20, 40, 60, 1)
    a[0, 0] = (100, 100, 100, 1)
    before = a.copy()
    cleaned, info = clean_alpha(a, PARAMS)
    assert np.array_equal(a, before)
    assert np.array_equal(cleaned[10:22, 10:22], before[10:22, 10:22])
    assert cleaned[0, 0, 3] == 0 and info['removed_pixels'] == info['removed_alpha_mass'] == 1


@pytest.mark.parametrize('params', [{**PARAMS, 'threshold': True}, {**PARAMS, 'threshold': 5},
    {**PARAMS, 'max_removed_fraction': float('nan')}, {**PARAMS, 'guard_radius': 1}, {**PARAMS, 'extra': 1}])
def test_bad_cleanup_params(params):
    with pytest.raises(ValueError):
        clean_alpha(np.zeros((10, 10, 4), dtype=np.uint8), params)


def test_cleanup_budget_and_weak_only_protection():
    a = np.ones((32, 32, 4), dtype=np.uint8)
    with pytest.raises(ValueError):
        clean_alpha(a, PARAMS)
    a[15, 15, 3] = 255
    with pytest.raises(ValueError):
        clean_alpha(a, PARAMS)


def prepared(tmp_path, cleanup=False):
    source, spec = fixture()
    if cleanup:
        image = Image.open(io.BytesIO(source))
        image.putpixel((0, 0), (10, 20, 30, 1))
        source = png(image)
        spec['source_sha256'] = hashlib.sha256(source).hexdigest()
        spec['slots'][0]['alpha_cleanup'] = copy.deepcopy(PARAMS)
    value = persist_sheet_candidates(tmp_path, source, spec)
    return 'board', value['manifest']['request_key']


def test_new_cleanup_candidates_reverify_and_human_gate(tmp_path):
    args = prepared(tmp_path, True)
    _, _, manifest = _candidate(tmp_path, *args)
    assert len(manifest['assets']) == 2
    assert manifest['assets'][0]['processing']['alpha_cleanup']['removed_pixels'] == 1
    value = assess_candidates(tmp_path, *args, provider=lambda **kw: FINDING, model_hash='a'*64)
    assert value['findings']['one']['action'] == 'accept_candidate'
    with pytest.raises(HtmlAssetSheetError) as exc:
        accept_candidate(tmp_path, *args, 'one', expected_revision=0)
    assert exc.value.code == 'SHEET_REVIEW_REQUIRED'
    assert not list(tmp_path.rglob('reviews.json')) and not list(tmp_path.rglob('resources.json'))


def test_advisory_cache_evidence_and_reference_invalidation(tmp_path):
    args = prepared(tmp_path)
    calls = []
    def provider(**kw):
        calls.append(kw)
        assert kw['candidate_bytes'].startswith(b'\x89PNG')
        assert 'need' in kw and '内部ID' in kw['system_prompt']
        return FINDING
    first = assess_candidates(tmp_path, *args, provider=provider, model_hash='a'*64)
    assert assess_candidates(tmp_path, *args, provider=provider, model_hash='a'*64) == first
    assert len(calls) == 2
    ref = png(Image.new('RGBA', (8, 8), 'red'))
    second = assess_candidates(tmp_path, *args, provider=provider, model_hash='a'*64, reference_bytes=ref)
    assert len(calls) == 4 and second['assessment_key'] != first['assessment_key']
    _, directory, manifest = _candidate(tmp_path, *args)
    assert len(list(directory.glob('advisory-*.json'))) == 2
    assert read_advisory(directory, manifest) == second
    data = json.loads((directory / 'advisory.json').read_text())
    data['findings']['one']['action'] = 'regenerate'
    (directory / 'advisory.json').write_text(json.dumps(data))
    with pytest.raises(HtmlAssetSheetError):
        read_advisory(directory, manifest)


@pytest.mark.parametrize('finding', [{**FINDING, 'edge': 'uncertain'}, {**FINDING, 'identity': 'uncertain'}])
def test_uncertain_requires_manual(finding):
    assert recommended_action(finding) == 'manual_review'


def test_extra_content_regenerate_and_bad_provider_has_no_partial_record(tmp_path):
    assert recommended_action({**FINDING, 'extra_content': True}) == 'regenerate'
    args = prepared(tmp_path)
    def failure(**kw):
        raise RuntimeError('secret-test-key')
    with pytest.raises(HtmlAssetSheetError) as exc:
        assess_candidates(tmp_path, *args, provider=failure, model_hash='a'*64)
    assert 'secret-test-key' not in str(exc.value)
    assert not list(tmp_path.rglob('advisory*.json'))
    with pytest.raises(HtmlAssetSheetError):
        assess_candidates(tmp_path, *args, provider=lambda **kw: {**FINDING, 'extra_content': 'false'}, model_hash='a'*64)


def test_cancel_before_persist_and_source_corruption(tmp_path):
    args = prepared(tmp_path)
    def checkpoint():
        raise RuntimeError('stopped')
    with pytest.raises(RuntimeError):
        assess_candidates(tmp_path, *args, provider=lambda **kw: FINDING, model_hash='a'*64, checkpoint=checkpoint)
    _, directory, _ = _candidate(tmp_path, *args)
    (directory / 'source.png').write_bytes(b'broken')
    with pytest.raises(HtmlAssetSheetError):
        assess_candidates(tmp_path, *args, provider=lambda **kw: FINDING, model_hash='a'*64)


def test_old_candidate_compatibility(tmp_path):
    source, spec = fixture()
    before = extract_asset_sheet(source, spec)
    args = prepared(tmp_path)
    assert _candidate(tmp_path, *args)[2] == before['manifest']


def test_vision_adapter_transmits_both_images_and_closes(monkeypatch):
    from types import SimpleNamespace
    import ai_provider_service
    import llm_concurrency
    from contextlib import contextmanager
    sent = {}
    @contextmanager
    def governed(endpoint):
        assert endpoint == 'https://example.test'
        sent['governed'] = True
        yield
    monkeypatch.setattr(llm_concurrency, 'governed_llm_request', governed)
    def create(**kw):
        sent.update(kw)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(FINDING)))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=lambda: sent.update(closed=True))
    monkeypatch.setattr(ai_provider_service, 'get_openai_client', lambda **kw: client)
    binding = SimpleNamespace(require_ready=lambda: None, api_key='secret', endpoint='https://example.test', model='vision')
    assert configured_vision(model_binding=binding, system_prompt='check', need='robot', candidate_bytes=b'candidate', reference_bytes=b'reference') == FINDING
    content = sent['messages'][1]['content']
    assert len(content) == 3 and all('data:image/png;base64,' in c['image_url']['url'] for c in content[1:])
    assert 'secret' not in json.dumps(sent) and sent['closed'] is True and sent['governed'] is True
    sent.clear()
    def stopped():
        raise RuntimeError('cancelled after queue')
    with pytest.raises(RuntimeError):
        configured_vision(model_binding=binding, system_prompt='check', need='robot', candidate_bytes=b'candidate', checkpoint=stopped)
    assert 'messages' not in sent and sent['closed'] is True
