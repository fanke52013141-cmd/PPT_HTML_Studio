"""Independent reference payload, identity pairing and conservative review stops."""
import copy
import json
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from checks.html_design_agent_fixture import with_coverage
from html_design_agent import review_fidelity
from html_reference_localization import mapped_reference_targets, localize_reference
from html_review_evidence import localized_comparison_evidence
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError

ROOT=Path(__file__).resolve().parents[1]


def inputs(tmp_path):
    ref,shot=tmp_path/'reference.png',tmp_path/'html.png'
    reference=Image.new('RGB',(1000,500),'white')
    ImageDraw.Draw(reference).text((700,50),'alpha',fill='black')
    reference.save(ref)
    current=Image.new('RGB',(1600,900),'white')
    ImageDraw.Draw(current).text((100,100),'alpha',fill='black')
    current.save(shot)
    scene={'version':'0.7.0','nodes':[{'id':'caption','type':'text','slot':'caption','role':'source',
                                     'runs':[{'text':'alpha','emphasis':False}]}]}
    report={'geometry':{'caption':{'box':{'x':100,'y':100,'width':200,'height':60}}}}
    return scene,ref,shot,report


def locate(payload, status='located'):
    return {'targets':[{'targetId':t['targetId'],'status':status,'container_presence':'absent',
        'container_box':None,'identity_evidence':'Controlled image observation',
        'part_regions':[{'partId':p['partId'],'status':status,'regions':[
            {'text':p['text'],'box':{'xPx':700+j*110,'yPx':50+i*20,'widthPx':100,'heightPx':16}}]
            if status=='located' else []} for j,p in enumerate(t['text_parts'])]}
        for i,t in enumerate(payload['reference_targets'])]}


def test_independent_boxes_pair_displaced_target_and_reuse_only_same_identity(tmp_path):
    scene,ref,shot,report=inputs(tmp_path)
    calls=[]
    def generator(**kwargs):
        payload=json.loads(kwargs['user_prompt']);calls.append(kwargs)
        if kwargs['artifact_prefix'].startswith('design_reference_localization-'):
            assert 'geometry' not in payload and 'objects' not in payload
            assert 'presentation' not in str(payload) and 'offsetX' not in str(payload)
            assert len(kwargs['image_paths'])==1
            return locate(payload, 'not_found' if payload['reference_targets'][0]['text_parts'][0]['text']=='beta' else 'located')
        assert len(kwargs['image_paths'])==3
        assert 'design-fidelity-review/1.1.0' in kwargs['system_prompt']
        evidence=payload['independent_reference_evidence']
        assert evidence['reference_localization']=='independent_model_observation'
        row=evidence['targets'][0]
        assert row['reference_pixels']==[700,50,800,66]
        assert row['current_pixels']==[100,100,300,160]
        assert row['center_delta_normalized']['x'] < -0.5
        return with_coverage(payload,{'status':'pass','issues':[]})
    deps=HtmlReviewDependencies(ROOT,generator)
    one=review_fidelity(scene,ref,shot,report,None,folder=tmp_path/'one',run_dir=tmp_path,
                        deps=deps,localized_reference=True)
    changed=copy.deepcopy(scene);changed['nodes'][0]['presentation']={'offsetY':12}
    two=review_fidelity(changed,ref,shot,report,None,folder=tmp_path/'two',run_dir=tmp_path,
                        deps=deps,localized_reference=True,previous=one)
    assert len(calls)==3 and two['reference_localization']['reused_for_identical_targets']
    changed['nodes'][0]['runs'][0]['text']='beta'
    with pytest.raises(HtmlReviewError,match='定位未决'):
        review_fidelity(changed,ref,shot,report,None,folder=tmp_path/'three',run_dir=tmp_path,
                         deps=deps,localized_reference=True,previous=two)
    assert len(calls)==4


@pytest.mark.parametrize('status',['ambiguous','not_found'])
def test_unresolved_locator_stops_without_fidelity_or_retry(tmp_path,status):
    scene,ref,shot,report=inputs(tmp_path)
    calls=[]
    def generator(**kwargs):
        calls.append(kwargs)
        assert kwargs['artifact_prefix'].startswith('design_reference_localization-')
        return locate(json.loads(kwargs['user_prompt']),status)
    with pytest.raises(HtmlReviewError) as caught:
        review_fidelity(scene,ref,shot,report,None,folder=tmp_path/'review',run_dir=tmp_path,
            deps=HtmlReviewDependencies(ROOT,generator),localized_reference=True)
    assert caught.value.code=='REFERENCE_LOCALIZATION_UNRESOLVED' and len(calls)==1
    diagnostic=json.loads((tmp_path/'review/diagnostic.json').read_text(encoding='utf-8'))
    assert diagnostic['next_action']['routes']==['evidence_review']
    assert diagnostic['next_action']['automatic_retry'] is False


def test_reference_source_tamper_rejected(tmp_path):
    scene,ref,shot,report=inputs(tmp_path)
    record=localize_reference(scene,ref,folder=tmp_path/'loc',run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,lambda **kw:locate(json.loads(kw['user_prompt']))))
    Image.new('RGB',(1000,500),'black').save(ref)
    with pytest.raises(ValueError,match='SOURCE_MISMATCH'):
        localized_comparison_evidence(scene,ref,shot,report,record,folder=tmp_path/'evidence')


def test_card_body_is_a_required_localization_part():
    targets=mapped_reference_targets({'nodes':[{'id':'card','type':'card','title':'Title','body':'Exact body'}]})
    assert {p['partId']:p['text'] for p in targets[0]['text_parts']}=={'title':'Title','body':'Exact body'}


def test_relation_identity_does_not_leak_html_endpoint_coordinates():
    targets=mapped_reference_targets({'nodes':[{'id':'relation','type':'arrow',
        'from':{'objectId':'a','point':{'x':0.5,'y':1}},
        'to':{'objectId':'b','point':{'x':0.5,'y':0}}}]})
    assert targets[0]['identity']=={'from':{'objectId':'a'},'to':{'objectId':'b'}}
