import copy
import pytest
from checks.test_html_candidate_capacity_solver import ROOT, document
from html_visual_review_service import HtmlReviewDependencies
from html_design_feasibility import check_design_feasibility


@pytest.mark.parametrize('overflow', [False,True])
def test_real_fonts_text_projection_reports_capacity(tmp_path, overflow):
    scene = document()
    if overflow:
        scene['nodes'][0]['presentation'] = {'height':20}
    before=copy.deepcopy(scene)
    result=check_design_feasibility(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no model')))
    assert result['status']==('changes_required' if overflow else 'passed'), result
    assert result['whole_page_geometry']=='not_checked' and scene==before
    assert (tmp_path/result['report']['screenshot']).is_file()
