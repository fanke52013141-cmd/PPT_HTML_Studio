import copy
import pytest
from checks.test_html_candidate_capacity_solver import ROOT,document
from html_visual_store import save_scene,HtmlVisualConflict
from html_repair_orchestration import generate_repair
from html_saved_layout_repair import INSTRUCTION


def test_saved_layout_uses_shared_solver_original_preview_and_scope(tmp_path):
    scene=document()
    for n in scene['nodes']:
        if n['id'] in ('card-1','card-2'):n['presentation']={'height':80}
    save_scene(tmp_path,scene['id'],scene,0)
    request={'expected_revision':1,'scope':['card-1','card-2'],'instruction':INSTRUCTION,'strategy':'layout_first'}
    result=generate_repair(tmp_path,scene['id'],request,lambda:pytest.fail('no model'))
    assert result['status']=='candidate',result
    assert result['review']['passed'] and result['candidate_key']
    assert result['request']['sampling_mode']=='output_frames'
    from html_scene_editing import load_editor
    assert load_editor(tmp_path,scene['id'])['scene']==scene
    with pytest.raises(HtmlVisualConflict):
        generate_repair(tmp_path,scene['id'],{**request,'expected_revision':0},lambda:None)


def test_shared_solver_cannot_move_unselected_neighbour(tmp_path):
    from html_linked_layout import solve_production_layout
    from html_visual_review_service import HtmlReviewDependencies
    scene=document();next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'height':140}
    original=copy.deepcopy(scene)
    result=solve_production_layout(scene,None,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,lambda **kw:None),allowed_scope=['card-1'])
    assert result['summary']['status']=='needs_revision'
    assert result['scene']==original
