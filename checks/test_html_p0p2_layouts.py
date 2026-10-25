import copy
import json
from pathlib import Path
import pytest
from html_storyboard_planning import normalize_html_scene_plan,load_template_catalog
from html_production_service import compile_plan
from html_semantic_design import build_semantic_design
from html_visual_review_service import HtmlReviewDependencies,review_scene

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'checks/fixtures/p0p2-layout-plans.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['plan']['templateRef']['id'])
def test_new_templates_normalize_semantics_compile_and_full_frames(tmp_path,case):
    catalog=load_template_catalog(ROOT)
    plan=normalize_html_scene_plan(case['plan'],catalog,contract_slide=case['contract'])
    build_semantic_design(plan)
    scene,binding=compile_plan(plan,case['contract'],catalog)
    original=copy.deepcopy(scene)
    report=review_scene(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no provider')),
                        preflight_dir=tmp_path/'full')
    assert report['passed'],report
    assert report['geometry_preflight']['coverage']['frame_complete']
    assert scene==original and binding['mode']=='beat_ids'


def test_unregistered_slot_does_not_expand_template_capability():
    from html_storyboard_planning import HtmlScenePlanError
    case=copy.deepcopy(CASES[0]);case['plan']['slots']['free-css']={'kind':'text','runs':[{'text':'wrong'}]}
    with pytest.raises(HtmlScenePlanError):normalize_html_scene_plan(case['plan'],load_template_catalog(ROOT),contract_slide=case['contract'])
