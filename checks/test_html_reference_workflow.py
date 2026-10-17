"""Shared reference policy and real pixel continuity, independent of model wording."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from html_design_agent import (validate_fidelity, validate_understanding, component_context,
                               review_target_evidence, retain_unchanged_issues, review_fidelity)
from html_design_policy import reference_observation
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from checks.html_design_agent_fixture import response_for, with_coverage

ROOT = Path(__file__).resolve().parents[1]


def issue(**kw):
    return dict(targetId='summary', category='layout', severity='minor',
                requirement='unsupported_presentation', reference_detail='decorative_icon',
                evidence='reference-only icon differs; text and relation intact',
                suggestion='omit optional decoration', **kw)


def scene():
    return {'version':'0.7.0','nodes':[{'id':'summary','type':'summary','slot':'summary',
        'from':{'text':'起点'},'to':{'text':'终点'},'term':'过程','takeaway':'关系不变'}]}


def test_decorations_are_observations_not_silent_deletion():
    result = validate_fidelity({'status':'changes_requested','issues':[issue()]},scene())
    assert result['status']=='pass' and not result['issues']
    assert result['reference_observations'][0]['evidence'].startswith('reference-only')


@pytest.mark.parametrize('need', ['semantic_text','semantic_relation','geometry','typography',
    'asset_identity','asset_rendering','theme_conflict','registered_variant'])
def test_minor_and_decoration_label_never_exempt_required_defects(need):
    item = issue(); item['requirement']=need
    result=validate_fidelity({'status':'changes_requested','issues':[item]},scene())
    assert result['status']=='changes_requested' and result['issues'] and not result['reference_observations']


@pytest.mark.parametrize('damage',['major','image','missing_discriminant','missing_text'])
def test_uncertain_reference_differences_fail_closed(damage):
    item=issue(); current=scene()
    if damage=='major':item['severity']='major'
    if damage=='image':current['nodes'][0]['type']='image'
    if damage=='missing_discriminant':item.pop('reference_detail')
    if damage=='missing_text':current['nodes'][0].pop('term')
    assert validate_fidelity({'status':'changes_requested','issues':[item]},current)['issues']


def test_understanding_needs_complete_allocation_even_for_allowed_decorations():
    current=scene();context=component_context(current,ROOT)
    allocation=response_for({'artifact_prefix':'design_understanding-case','user_prompt':json.dumps(context)})
    observation={k:v for k,v in issue().items() if k in ('targetId','requirement','reference_detail','evidence')}
    observation['route']='capabilities'
    with pytest.raises(ValueError,match='complete ready allocations'):
        validate_understanding({'status':'unsupported','objects':[],'issues':[observation]},context)
    allocation['issues']=[observation]
    result=validate_understanding(allocation,context)
    assert result['status']=='ready' and result['objects'] and not result['issues']
    assert result['reference_observations']


def test_unchanged_region_cannot_disappear_after_other_objects_change(tmp_path):
    current=scene();image=tmp_path/'first.png'
    Image.new('RGB',(1600,900),'white').save(image)
    report={'geometry':{'summary':{'box':{'x':50,'y':600,'width':1400,'height':170}}}}
    evidence=review_target_evidence(current,image,report)
    blocker=issue();blocker.update(reference_detail=None,requirement='geometry',evidence='missing actual arrow')
    previous={'result':{'issues':[blocker]},'target_evidence':evidence}
    second=tmp_path/'second.png'
    with Image.open(image) as img:
        ImageDraw.Draw(img).rectangle((20,30,400,100),fill='black');img.save(second)
    result={'status':'pass','issues':[]}
    retained=retain_unchanged_issues(result,previous,review_target_evidence(current,second,report))
    assert retained[0]['reason']=='unchanged_rendered_region'
    assert result['status']=='changes_requested' and result['issues']==[blocker]
    # A changed crop permits fresh review, without the program claiming it fixed.
    with Image.open(second) as img:
        ImageDraw.Draw(img).line((200,650,1200,650),fill='black',width=4);img.save(second)
    fresh={'status':'pass','issues':[]}
    assert not retain_unchanged_issues(fresh,previous,review_target_evidence(current,second,report))


def test_missing_region_evidence_does_not_clear_unchanged_node(tmp_path):
    current=scene();image=tmp_path/'shot.png';Image.new('RGB',(16,9),'white').save(image)
    evidence=review_target_evidence(current,image,{})
    blocker=issue();blocker['reference_detail']=None
    result={'status':'pass','issues':[]}
    assert retain_unchanged_issues(result,{'result':{'issues':[blocker]},'target_evidence':evidence},evidence)
    assert result['status']=='changes_requested'


def test_previous_reference_mismatch_stops_before_model(tmp_path):
    image=tmp_path/'shot.png';Image.new('RGB',(16,9),'white').save(image)
    def forbidden(**kw):
        pytest.fail('stale previous reference must stop before model')
    with pytest.raises(HtmlReviewError,match='前轮'):
        review_fidelity(scene(),image,image,{},None,folder=tmp_path/'audit',run_dir=tmp_path,
            deps=HtmlReviewDependencies(ROOT,forbidden),previous={'design_sha256':'different'})


def test_real_review_entry_retains_raw_pass_and_blocks_unchanged_prior_issue(tmp_path):
    image=tmp_path/'shot.png';Image.new('RGB',(1600,900),'white').save(image)
    current=scene();report={'geometry':{'summary':{'box':{'x':50,'y':600,'width':1400,'height':170}}}}
    blocker=issue();blocker.update(requirement='semantic_relation',reference_detail=None,evidence='arrow missing')
    calls=[]
    def generator(**kw):
        calls.append(json.loads(kw['user_prompt']))
        raw = {'status':'changes_requested','issues':[blocker]} if len(calls)==1 else {'status':'pass','issues':[]}
        return with_coverage(calls[-1],raw)
    deps=HtmlReviewDependencies(ROOT,generator)
    first=review_fidelity(current,image,image,report,None,folder=tmp_path/'0',run_dir=tmp_path,deps=deps)
    second=review_fidelity(current,image,image,report,None,folder=tmp_path/'1',run_dir=tmp_path,deps=deps,previous=first)
    assert calls[1]['prior_open_issues'][0]['requirement']=='semantic_relation'
    assert 'understanding' not in calls[1]
    assert second['result']['status']=='changes_requested' and second['continuity']['retained']
    raw=json.loads((tmp_path/'1/response.json').read_text(encoding='utf-8'))
    assert set(raw)=={'facts'} and all(not f['differences'] for f in raw['facts'])
