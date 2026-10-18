"""Explicit new review references retain original bytes and never grant approval."""
import copy
import json

import pytest
from pydantic import ValidationError

from checks.test_html_e_production import case as case, run
from html_design_candidates import candidate_directory, definition_identity, load_design, current_design
from html_production_service import produce_scene
from html_production_models import HtmlProduceRequest
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError


def old_design(case, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr('html_design_candidates.definition_identity', lambda *a, **kw: '0' * 64)
        return run(case)['design']['key']


def test_explicit_reuse_revalidates_without_calls_writes_or_approval(case, monkeypatch):
    key = old_design(case, monkeypatch)
    directory = candidate_directory(case.run, case.contract['slide_id'], key)
    before = {p: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    def unexpected(*args, **kwargs):
        pytest.fail('Reference reuse called a model/provider')
    deps = HtmlReviewDependencies(case.deps.repo_root, unexpected)
    with pytest.raises(HtmlReviewError) as caught:
        produce_scene(case.contract, run_dir=case.run, deps=deps, provider=unexpected,
                      options={'design_candidate_key': key})
    assert caught.value.code == 'DESIGN_STALE'
    result = produce_scene(case.contract, run_dir=case.run, deps=deps,
                           options={'reuse_design_candidate_key': key})
    assert result['stage'] == 'design_review' and result['reference_reused']
    assert not result['saved']['changed'] and result['design']['approval_status'] == 'not_recorded'
    assert result['design']['key'] != key
    new, _, image = load_design(run_dir=case.run, contract=case.contract,
        key=result['design']['key'], revision=0, definitions=definition_identity(deps.repo_root), model_summary={})
    assert image.read_bytes() == before[directory / 'design-reference.png']
    assert new['candidate']['source_design_key'] == key
    assert {k:v for k,v in new['plan'].items() if k != 'registered'} == {
        k:v for k,v in json.loads(before[directory / 'candidate.json'])['plan'].items() if k != 'registered'}
    assert all(p.read_bytes() == data for p, data in before.items())
    state = current_design(run_dir=case.run, contract=case.contract, repo_root=deps.repo_root)['design']
    assert state['status'] == 'needs_review' and not state['stale']
    assert not (case.run / 'planning/html_visual/scene-e1.json').exists()
    assert not (directory.parent.parent / 'design-acceptance.json').exists()


def test_semantic_plan_reuse_preserves_objects_actions_and_spoken_text(case, monkeypatch):
    from checks.test_html_semantic_plan import semantic_plan
    plan = semantic_plan(case.contract)
    deps = HtmlReviewDependencies(case.deps.repo_root, lambda **kw: copy.deepcopy(plan))
    with monkeypatch.context() as patch:
        patch.setattr('html_design_candidates.definition_identity', lambda *a, **kw: '0' * 64)
        first = produce_scene(case.contract, run_dir=case.run, deps=deps, provider=case.provider,
                              options={'plan_version':'0.2.0'})
    def unexpected(*args, **kwargs):
        pytest.fail('Semantic reference reuse called a model')
    result = produce_scene(case.contract, run_dir=case.run,
        deps=HtmlReviewDependencies(deps.repo_root, unexpected),
        options={'plan_version':'0.2.0', 'reuse_design_candidate_key':first['design']['key']})
    new, _, _ = load_design(run_dir=case.run, contract=case.contract, key=result['design']['key'],
                           revision=0, definitions=definition_identity(deps.repo_root), model_summary={})
    assert new['plan']['version'] == '0.2.0' and len(case.requests) == 1
    original = json.loads((candidate_directory(case.run, case.contract['slide_id'], first['design']['key'])
                           / 'candidate.json').read_text(encoding='utf-8'))['plan']
    assert new['plan']['beats'] == original['beats']
    assert new['plan']['objects'] == original['objects']


def test_reused_reference_can_enter_full_production_after_new_acceptance(case, monkeypatch):
    key = old_design(case, monkeypatch)
    copied = produce_scene(case.contract, run_dir=case.run, deps=case.deps,
                            options={'reuse_design_candidate_key':key})
    assert len(case.requests) == 1 and len(case.llm_calls) == 1
    result = run(case, design_candidate_key=copied['design']['key'])
    assert result['saved']['changed']
    assert not (case.run / 'planning/html_visual/approval-e1.json').exists()


@pytest.mark.parametrize('damage', ['image', 'contract', 'model', 'author', 'normalizer'])
def test_reuse_rejects_changed_or_corrupt_inputs(case, monkeypatch, damage):
    key = old_design(case, monkeypatch)
    contract, summary = copy.deepcopy(case.contract), {}
    if damage == 'image':
        (candidate_directory(case.run, contract['slide_id'], key) / 'design-reference.png').write_bytes(b'changed')
    elif damage == 'contract':
        contract['title'] = 'changed content'
    elif damage == 'model':
        summary = {'source': 'changed model'}
    elif damage == 'author':
        from html_visual_store import save_scene
        scene = json.loads((case.deps.repo_root / 'html_engine/visual/scenes/condensation.json').read_text(encoding='utf-8'))
        scene['id'] = contract['slide_id']
        save_scene(case.run, scene['id'], scene, 0)
    else:
        from html_storyboard_planning import load_template_catalog
        catalog = copy.deepcopy(load_template_catalog(case.deps.repo_root))
        for template in catalog['templates'].values():
            template['structure'] = 'changed structure'
        monkeypatch.setattr('html_storyboard_planning.load_template_catalog', lambda root: catalog)
    with pytest.raises(HtmlReviewError):
        produce_scene(contract, run_dir=case.run, deps=case.deps,
            model_summary=summary, options={'reuse_design_candidate_key': key})


@pytest.mark.parametrize('other', [{'design_candidate_key':'b'*64}, {'design_instruction':'change'},
                                  {'asset_instruction':'change'}, {'prior_unknown_task_id':'html_'+'b'*20}])
def test_reuse_cannot_be_combined_with_acceptance_or_other_work(other):
    with pytest.raises(ValidationError):
        HtmlProduceRequest.model_validate({'reuse_design_candidate_key':'a'*64, **other})
