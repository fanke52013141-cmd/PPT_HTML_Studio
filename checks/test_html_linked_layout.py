"""Registered linked columns and unsaved declared routing, original browser QA."""
import copy
import json
from pathlib import Path

import pytest

from html_linked_layout import linked_layout_candidates, solve_production_layout
from html_capacity_repair import _layout_for
from html_visual_review_service import HtmlReviewDependencies

ROOT = Path(__file__).resolve().parents[1]


def case():
    scene = json.loads((ROOT/'checks/fixtures/capacity-baseline/ordinary.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT/'html_engine/visual/generated/catalog.json').read_text(encoding='utf-8'))
    next(n for n in scene['nodes'] if n['id']=='card-1')['presentation'] = {'height':140}
    return scene, _layout_for(scene,catalog)


def test_registered_column_proposal_moves_followers_and_preserves_content():
    scene,layout=case()
    original=copy.deepcopy(scene)
    proposals=linked_layout_candidates(scene,layout,{'card-1','card-2'})
    assert len(proposals)==1
    assert {op['targetId'] for op in proposals[0]} == {'card-2','card-3','summary'}
    assert all(set(op['values'])=={'offsetY'} for op in proposals[0])
    assert scene==original
    assert linked_layout_candidates(scene,layout,{'header'})==[]


@pytest.mark.parametrize('damage',['overflow','columns'])
def test_no_candidate_if_group_is_not_supported(damage):
    scene,layout=case()
    if damage=='overflow':
        next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']['height']=400
    else:
        layout=copy.deepcopy(layout)
        layout['slots']['card-2']['box']['x']+=300
    assert linked_layout_candidates(scene,layout,{'card-1'})==[]


def test_three_cards_and_summary_real_browser(tmp_path):
    scene,_=case()
    before=copy.deepcopy(scene)
    result=solve_production_layout(scene,None,run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('No provider')))
    assert result['summary']['status']=='candidate',result['summary']
    assert result['report']['geometry_preflight']['coverage']['frame_complete']
    for old,new in zip(before['nodes'],result['scene']['nodes']):
        assert {k:v for k,v in old.items() if k!='presentation'}=={k:v for k,v in new.items() if k!='presentation'}
    assert result['scene']['motion']==before['motion'] and scene==before


def test_linked_move_cannot_cross_manual_leaf_protection(tmp_path):
    scene,_=case()
    before=copy.deepcopy(scene)
    manual={'protected_paths':[['scene','nodes','card-2','presentation','offsetY']]}
    result=solve_production_layout(scene,None,run_dir=tmp_path,manual=manual,
        deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('No provider')))
    assert result['summary']['status']=='needs_revision'
    assert any(a.get('code')=='MANUAL_FIELD_PROTECTED' for a in result['summary']['attempts'])
    assert result['scene']==scene==before


def test_declared_point_routing_real_browser(tmp_path):
    from checks.test_html_production_preflight import stage_scene
    from html_scene_editing import beats_for
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    cases=json.loads((ROOT/'checks/fixtures/course-structure-plans.json').read_text(encoding='utf-8'))
    _,binding=compile_plan(cases[3]['plan'],cases[3]['contract'],load_template_catalog(ROOT))
    (tmp_path/'planning').mkdir()
    (tmp_path/'planning/visual_contract.json').write_text(json.dumps({'slides':[cases[3]['contract']]}),encoding='utf-8')
    scene=stage_scene()
    arrow=next(n for n in scene['nodes'] if n['id']=='relation-1')
    arrow['from']['point']={'x':0.5,'y':1}
    arrow['to']['point']={'x':0.5,'y':0}
    before=copy.deepcopy(scene)
    result=solve_production_layout(scene,binding,run_dir=tmp_path,beats=beats_for(tmp_path,scene['id']),
        deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('No provider')))
    assert result['summary']['status']=='candidate',result['summary']
    assert result['report']['geometry_preflight']['passed']
    updated=next(n for n in result['scene']['nodes'] if n['id']=='relation-1')
    assert all(updated[side]['objectId']==arrow[side]['objectId'] for side in ('from','to'))
    assert result['binding']==binding and result['scene']['motion']==scene['motion'] and scene==before
