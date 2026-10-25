import copy
import json
from pathlib import Path
import pytest
from html_storyboard_planning import normalize_html_scene_plan,load_template_catalog,HtmlScenePlanError
from html_production_service import compile_plan
from html_visual_review_service import HtmlReviewDependencies,review_scene

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'checks/fixtures/followup-layout-plans.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('record',CASES,ids=lambda r:r['plan']['templateRef']['id'])
def test_registered_expansions_compile_and_pass_full_frames(tmp_path,record):
    catalog=load_template_catalog(ROOT)
    plan=normalize_html_scene_plan(record['plan'],catalog,contract_slide=record['contract'])
    scene,binding=compile_plan(plan,record['contract'],catalog);before=copy.deepcopy(scene)
    report=review_scene(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no provider')),
                        preflight_dir=tmp_path/'full')
    assert report['passed'],report
    assert report['geometry_preflight']['coverage']['frame_complete'] and scene==before
    assert binding['mode']=='beat_ids'


def test_new_layouts_reject_unknown_slots_and_overflow(tmp_path):
    catalog=load_template_catalog(ROOT);record=copy.deepcopy(CASES[0])
    record['plan']['slots']['free-css']={'kind':'text','runs':[{'text':'wrong','emphasis':False}]}
    with pytest.raises(HtmlScenePlanError):normalize_html_scene_plan(record['plan'],catalog,contract_slide=record['contract'])
    record=copy.deepcopy(CASES[0]);record['plan']['slots']['card-1']['body']='超长内容。'*200
    try:
        plan=normalize_html_scene_plan(record['plan'],catalog,contract_slide=record['contract'])
        scene,_=compile_plan(plan,record['contract'],catalog)
    except HtmlScenePlanError:return
    report=review_scene(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no provider')))
    assert report['passed'] is False


def test_summary_follows_grid_without_mutating_source():
    from html_layout_groups import registered_row_candidates
    scene={'nodes':[{'id':k,'slot':k,'type':'summary' if k=='summary' else 'card'} for k in ('a','b','c','d','summary')]}
    boxes={'a':[0,100,180,100],'b':[200,100,180,100],'c':[0,220,180,100],'d':[200,220,180,100],'summary':[0,340,380,50]}
    scene['nodes'][0]['presentation']={'height':150}
    layout={'slots':{k:{'box':dict(zip(('x','y','width','height'),v))} for k,v in boxes.items()}}
    before=copy.deepcopy(scene)
    proposals=registered_row_candidates(scene,layout,{'a'})
    assert any(any(o['targetId']=='summary' and o['values']['offsetY']==34 for o in ops) for ops in proposals)
    assert scene==before


@pytest.mark.parametrize('protected',[False,True])
def test_comparison_column_repair_preserves_manual_and_full_qa(tmp_path,protected):
    from html_linked_layout import solve_production_layout
    record=CASES[1];catalog=load_template_catalog(ROOT)
    plan=normalize_html_scene_plan(record['plan'],catalog,contract_slide=record['contract'])
    scene,binding=compile_plan(plan,record['contract'],catalog)
    scene['version']='0.5.0'
    next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'width':520}
    original=copy.deepcopy(scene)
    manual={'protected_paths':[['scene','nodes','card-2','presentation','offsetX']]} if protected else None
    result=solve_production_layout(scene,binding,run_dir=tmp_path,manual=manual,
        beats=record['contract']['narration_beats'],deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no provider')))
    assert result['summary']['status']==('needs_revision' if protected else 'candidate'),result['summary']
    assert scene==original and result['binding']==binding and result['scene']['motion']==original['motion']
    if protected:assert result['scene']==original
    else:assert result['report']['geometry_preflight']['coverage']['frame_complete']
