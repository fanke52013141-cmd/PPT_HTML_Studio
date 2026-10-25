import copy
import pytest
from html_layout_groups import registered_row_candidates


@pytest.mark.parametrize('mixed,grid', [(False,False),(True,False),(False,True)])
def test_registered_row_order_and_grid_baselines(mixed, grid):
    nodes = [{'id':'a','type':'image' if mixed else 'card','slot':'a','presentation':{'width':220,'height':120}},
             {'id':'b','type':'text' if mixed else 'card','slot':'b'}]
    slots = {'a':{'box':{'x':0,'y':100,'width':180,'height':100}},'b':{'box':{'x':200,'y':100,'width':180,'height':100}}}
    if grid:
        nodes += [{'id':'c','type':'card','slot':'c'},{'id':'d','type':'card','slot':'d'}]
        slots.update(c={'box':{'x':0,'y':210,'width':180,'height':100}}, d={'box':{'x':200,'y':210,'width':180,'height':100}})
    scene = {'nodes':nodes}; before = copy.deepcopy(scene)
    proposals = registered_row_candidates(scene, {'slots':slots}, {'a'})
    assert proposals and proposals[0][0]['targetId']=='b'
    assert proposals[0][0]['values']['offsetX']==32
    if grid: assert any(op['targetId']=='c' and op['values']['offsetY']==22 for op in proposals[0])
    assert scene==before


def test_no_free_reflow_or_canvas_overflow():
    nodes=[{'id':'a','slot':'a','type':'card','presentation':{'width':1500}}, {'id':'b','slot':'b','type':'card'}]
    layout={'slots':{'a':{'box':{'x':0,'y':100,'width':400,'height':100}},'b':{'box':{'x':500,'y':100,'width':400,'height':100}}}}
    assert registered_row_candidates({'nodes':nodes},layout,{'a'})==[]
    assert registered_row_candidates({'nodes':nodes},layout,{'unrelated'})==[]


def test_registered_horizontal_row_real_browser(tmp_path):
    import json
    from checks.test_html_production_preflight import stage_scene
    from checks.test_html_candidate_capacity_solver import ROOT
    from html_linked_layout import solve_production_layout
    from html_visual_review_service import HtmlReviewDependencies
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    cases=json.loads((ROOT/'checks/fixtures/course-structure-plans.json').read_text(encoding='utf-8'))
    contract=cases[3]['contract']
    _,binding=compile_plan(cases[3]['plan'],contract,load_template_catalog(ROOT))
    (tmp_path/'planning').mkdir()
    (tmp_path/'planning/visual_contract.json').write_text(json.dumps({'slides':[contract]}),encoding='utf-8')
    scene=stage_scene()
    first=next(n for n in scene['nodes'] if n['slot']=='stage-1')
    first['presentation']={'width':530}
    original=copy.deepcopy(scene)
    result=solve_production_layout(scene,binding,run_dir=tmp_path,beats=contract['narration_beats'],
        deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('No model')))
    assert result['summary']['status']=='candidate',result['summary']
    assert result['report']['geometry_preflight']['coverage']['frame_complete']
    assert result['scene']['motion']==original['motion'] and scene==original


def test_staggered_mixed_pair_and_vertical_pair_only_separate_existing_overlap():
    from html_layout_groups import mixed_layout_candidates
    scene={'nodes':[{'id':'image','slot':'subject','type':'image'},
                    {'id':'text','slot':'body','type':'text','presentation':{'width':250}}]}
    layout={'slots':{'body':{'box':{'x':60,'y':200,'width':150,'height':80}},
                     'subject':{'box':{'x':300,'y':180,'width':200,'height':150}}}}
    proposals=mixed_layout_candidates(scene,layout,{'image','text'})
    assert proposals[0]==[{'targetId':'text','kind':'set_presentation','values':{'offsetX':-22}}]
    scene['nodes'][1]['presentation']={'height':160}
    layout['slots']['subject']['box']={'x':70,'y':300,'width':200,'height':150}
    assert any(op['values'].get('offsetY')==-72 for ops in mixed_layout_candidates(scene,layout,{'text'}) for op in ops)
    assert mixed_layout_candidates(scene,layout,{'unrelated'})==[]


def test_staggered_card_image_real_browser(tmp_path):
    from checks.test_html_candidate_capacity_solver import document, ROOT
    from html_linked_layout import solve_production_layout
    from html_visual_review_service import HtmlReviewDependencies
    scene=document()
    next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'width':900}
    original=copy.deepcopy(scene)
    result=solve_production_layout(scene,None,run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no model')))
    assert result['summary']['status']=='candidate', result['summary']
    assert result['report']['geometry_preflight']['coverage']['frame_complete']
    assert result['scene']['motion']==original['motion'] and scene==original


@pytest.mark.parametrize('protected',[False,True])
def test_registered_grid_full_pipeline_and_manual_protection(tmp_path,protected):
    import json
    from checks.test_html_candidate_capacity_solver import ROOT
    from html_linked_layout import solve_production_layout
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan
    from html_visual_review_service import HtmlReviewDependencies
    record=json.loads((ROOT/'checks/fixtures/knowledge-grid-plan.json').read_text(encoding='utf-8'))
    catalog=load_template_catalog(ROOT)
    plan=normalize_html_scene_plan(record['plan'],catalog,contract_slide=record['contract'])
    scene,binding=compile_plan(plan,record['contract'],catalog)
    (tmp_path/'planning').mkdir()
    (tmp_path/'planning/visual_contract.json').write_text(json.dumps({'slides':[record['contract']]}),encoding='utf-8')
    scene['version']='0.5.0'  # Registered presentation editing version.
    next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'height':230}
    manual={'protected_paths':[['scene','nodes','card-3','presentation','offsetY']]} if protected else None
    original=copy.deepcopy(scene)
    result=solve_production_layout(scene,binding,run_dir=tmp_path,manual=manual,beats=record['contract']['narration_beats'],
        deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no model')))
    assert result['summary']['status']==('needs_revision' if protected else 'candidate'),result['summary']
    assert result['binding']==binding and result['scene']['motion']==original['motion'] and scene==original
    if not protected:
        assert result['report']['geometry_preflight']['coverage']['frame_complete']
        assert next(n for n in result['scene']['nodes'] if n['id']=='card-3')['presentation']['offsetY']==22
    else:
        assert result['scene']==original
        assert any(a.get('code')=='MANUAL_FIELD_PROTECTED' for a in result['summary']['attempts'])
