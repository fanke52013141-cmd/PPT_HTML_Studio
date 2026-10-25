from checks.test_html_e_production import case as case,run
from checks.test_html_candidate_capacity_solver import ROOT
from html_annotation_store import create_dataset,case_view


def test_dataset_creation_uses_original_verified_design_and_saved_author(case):
    first=run(case)
    run(case,design_candidate_key=first['design']['key'])
    from pipeline_lifecycle import write_json_atomic
    write_json_atomic(case.run/'planning/visual_contract.json',{'slides':[case.contract]})
    before=len(case.requests)
    result=create_dataset(case.run,{'dataset_id':'new-labels','samples':[
        {'slide_id':case.contract['slide_id'],'course_id':'science','split':'development'}]},ROOT)
    view=case_view(case.run,'new-labels',result['cases'][0]['id'])
    assert view['state']['revision']==0 and view['state']['status']=='draft'
    assert len(case.requests)==before
    assert view['reference'].read_bytes()
