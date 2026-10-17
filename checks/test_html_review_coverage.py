"""No coverage declarations may be inferred from an empty issue list."""
import copy
import json
from pathlib import Path
import pytest
from PIL import Image
from html_design_agent import review_checklist, validate_fidelity, review_fidelity, text_alignment_contract
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from checks.html_design_agent_fixture import with_coverage

ROOT=Path(__file__).resolve().parents[1]


def scene():
    return {'version':'0.7.0','nodes':[{'id':'caption','slot':'caption','type':'text','runs':[{'text':'出处','emphasis':False}], 'role':'source'},
        {'id':'summary','slot':'summary','type':'summary','from':{'text':'A'},'to':{'text':'B'},'term':'关系','takeaway':'结论'},
        {'id':'picture','slot':'image','type':'image'}]}


def covered():
    return with_coverage({'review_checklist':review_checklist(scene())},{'status':'pass','issues':[]})


@pytest.mark.parametrize('damage',['missing','duplicate','unknown_target','unknown_dimension','uncertain','false_issue','bad_index','unlinked_issue','wrong_dimension','wrong_target','pass_with_index'])
def test_invalid_coverage_cannot_sign_pass(damage):
    result=covered()
    if damage=='missing':result['coverage'].pop()
    if damage=='duplicate':result['coverage'].append(copy.deepcopy(result['coverage'][0]))
    if damage=='unknown_target':result['coverage'][0]['targetId']='other'
    if damage=='unknown_dimension':result['coverage'][0]['dimension']='asset_identity'
    if damage=='uncertain':result['coverage'][0]['status']='uncertain'
    if damage=='false_issue':result['coverage'][0]['status']='issue'
    if damage in ('bad_index','unlinked_issue','wrong_dimension','wrong_target','pass_with_index'):
        result['status']='changes_requested'
        result['issues']=[{'targetId':'caption','category':'layout','requirement':'typography','severity':'minor','evidence':'source centered','suggestion':'left align'}]
        row=next(r for r in result['coverage'] if r['targetId']=='caption' and r['dimension']=='typography')
        row.update(status='issue',issue_indices=[0])
        if damage=='bad_index':row['issue_indices']=[99]
        if damage=='unlinked_issue':row.update(status='pass',issue_indices=[])
        if damage=='pass_with_index':row['status']='pass'
        if damage in ('wrong_dimension','wrong_target'):
            row.update(status='pass',issue_indices=[])
            other=next(r for r in result['coverage'] if r['targetId']==('summary' if damage=='wrong_target' else 'caption') and r['dimension']==('typography' if damage=='wrong_target' else 'geometry'))
            other.update(status='issue',issue_indices=[0])
    with pytest.raises(ValueError,match='COVERAGE_INCOMPLETE'):
        validate_fidelity(result,scene(),require_coverage=True)


def test_all_objects_including_caption_and_asset_dimensions_are_required():
    pairs={(r['targetId'],r['dimension']) for r in review_checklist(scene())}
    assert ('caption','typography') in pairs and ('summary','semantic_relation') in pairs
    assert ('picture','asset_identity') in pairs and ('picture','asset_rendering') in pairs
    assert validate_fidelity(covered(),scene(),require_coverage=True)['status']=='pass'


def test_legacy_archive_does_not_gain_current_coverage_status():
    raw={'status':'pass','issues':[]}
    assert validate_fidelity(raw,scene())['coverage']==[]
    with pytest.raises(ValueError,match='COVERAGE_INCOMPLETE'):
        validate_fidelity(raw,scene(),require_coverage=True)


def test_actual_review_rejects_empty_pass_without_second_request(tmp_path):
    picture=tmp_path/'shot.png';Image.new('RGB',(1600,900),'white').save(picture)
    current=scene();current['nodes']=current['nodes'][:2]
    calls=[]
    def model(**kw):
        calls.append(kw)
        assert json.loads(kw['user_prompt'])['review_checklist']==review_checklist(current)
        return {'status':'pass','issues':[]}
    with pytest.raises(HtmlReviewError) as caught:
        review_fidelity(current,picture,picture,{},None,folder=tmp_path/'review',run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,model))
    assert caught.value.code=='DESIGN_REVIEW_COVERAGE_INCOMPLETE' and len(calls)==1
    assert (tmp_path/'review/response.json').is_file() and not (tmp_path/'review/result.json').exists()


def test_text_alignment_contract_uses_versioned_layout_and_whole_part_override():
    current=scene();current['layoutRef']={'id':'data-relation-v1','version':'0.2.0'}
    current['nodes']=current['nodes'][:1]
    assert text_alignment_contract(current,ROOT)['caption']['align']=='center'
    current['nodes'][0]['presentation']={'typography':{'text':{'align':'left'}}}
    assert text_alignment_contract(current,ROOT)['caption']['align']=='left'
    current['layoutRef']['version']='missing'
    assert not text_alignment_contract(current,ROOT)


@pytest.mark.parametrize('reference',[None,'uncertain','left'])
def test_known_actual_alignment_cannot_pass_without_reference_evidence_or_mismatch_issue(reference):
    result=covered()
    row=next(r for r in result['coverage'] if r['targetId']=='caption' and r['dimension']=='typography')
    row['reference_alignment']=reference
    with pytest.raises(ValueError,match='COVERAGE_INCOMPLETE'):
        validate_fidelity(result,scene(),require_coverage=True,alignment={'caption':{'align':'center'}})


def test_program_links_issues_when_model_omits_metadata_indices_and_category():
    raw={'status':'changes_requested','issues':[{'targetId':'caption','requirement':'typography',
         'severity':'minor','evidence':'reference left / actual center','suggestion':'left'}]}
    result=with_coverage({'review_checklist':review_checklist(scene())},raw)
    for row in result['coverage']:
        row.pop('issue_indices')
        if row['targetId']=='caption' and row['dimension']=='typography':row['reference_alignment']='left'
    checked=validate_fidelity(result,scene(),require_coverage=True,alignment={'caption':{'align':'center'}})
    row=next(r for r in checked['coverage'] if r['targetId']=='caption' and r['dimension']=='typography')
    assert row['issue_indices']==[0] and checked['issues'][0]['category']=='layout'


@pytest.mark.parametrize('damage',[None,'conflict','uncertain','no_check','wrong_requirement','unknown_extra'])
def test_duplicate_reference_evidence_is_typed_and_must_agree(damage):
    raw={'status':'changes_requested','issues':[{'targetId':'caption','requirement':'typography',
         'severity':'minor','evidence':'reference left / actual center','suggestion':'left','reference_alignment':'left'}]}
    result=with_coverage({'review_checklist':review_checklist(scene())},raw)
    row=next(r for r in result['coverage'] if r['targetId']=='caption' and r['dimension']=='typography')
    row['reference_alignment']='left'
    if damage=='conflict':result['issues'][0]['reference_alignment']='right'
    if damage=='uncertain':result['issues'][0]['reference_alignment']='uncertain'
    if damage=='no_check':result['coverage'].remove(row)
    if damage=='wrong_requirement':result['issues'][0]['requirement']='geometry'
    if damage=='unknown_extra':result['issues'][0]['unregistered']='ignored?'
    if damage:
        with pytest.raises(ValueError):validate_fidelity(result,scene(),require_coverage=True)
    else:
        assert validate_fidelity(result,scene(),require_coverage=True)['issues'][0]['reference_alignment']=='left'
