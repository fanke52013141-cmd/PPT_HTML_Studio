import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from html_reference_localization import reference_targets, validate_locations, localize_reference, validate_pixel_locations
from html_visual_review_service import HtmlReviewDependencies

ROOT=Path(__file__).resolve().parents[1]


def scene():
    return {'nodes':[{'id':'caption','type':'text','slot':'caption','runs':[{'text':'source'}],
                     'presentation':{'offsetX':900},'actions':[{'x':10}]}],'layoutRef':{'id':'secret'}}


def response():
    return {'targets':[{'targetId':'caption','status':'located','box':{'x':100,'y':300,'width':600,'height':100},
                        'identity_evidence':'source line matches','visible_text':'source'}]}


@pytest.mark.parametrize('damage',['missing','duplicate','unknown','bounds','zero','boolean','status','empty_identity'])
def test_invalid_localization_cannot_be_used(damage):
    raw=response();r=raw['targets'][0]
    if damage=='missing':raw['targets']=[]
    if damage=='duplicate':raw['targets'].append(copy.deepcopy(r))
    if damage=='unknown':r['targetId']='other'
    if damage=='bounds':r['box']['x']=900
    if damage=='zero':r['box']['width']=0
    if damage=='boolean':r['box']['x']=True
    if damage=='status':r['status']='not_found'
    if damage=='empty_identity':r['identity_evidence']='  '
    with pytest.raises(ValueError):validate_locations(raw,reference_targets(scene()))


def test_not_found_and_ambiguous_are_honest_unlocated_results():
    for status in ('not_found','ambiguous'):
        raw=response();raw['targets'][0].update(status=status,box=None)
        assert validate_locations(raw,reference_targets(scene()))['targets'][0]['box'] is None


def test_locator_receives_reference_only_and_ignores_all_html_positions(tmp_path):
    image=tmp_path/'ref.png';Image.new('RGB',(1000,500),'white').save(image)
    calls=[]
    def generator(**kwargs):
        payload=json.loads(kwargs['user_prompt']);calls.append(payload)
        assert set(payload)=={'reference_targets','box_coordinates','task','image_size'}
        assert set(payload['reference_targets'][0])=={'targetId','type','identity','region_scope','text_parts'}
        assert payload['image_size']==[1000,500] and payload['box_coordinates']=='original_image_pixels'
        assert len(kwargs['image_paths'])==1
        assert set(json.loads(kwargs['schema_hint'])['properties'])=={'targets'}
        raw=response();row=raw['targets'][0];row.pop('box')
        row.update(container_box={'xPx':80,'yPx':130,'widthPx':800,'heightPx':100},
                   container_presence='present',
                   part_regions=[{'partId':'runs/0','status':'located','regions':[{'text':'source','box':{'xPx':100,'yPx':150,'widthPx':600,'heightPx':50}}]}])
        row.pop('visible_text')
        return raw
    record=localize_reference(scene(),image,folder=tmp_path/'loc',run_dir=tmp_path,
                              deps=HtmlReviewDependencies(ROOT,generator))
    assert record['quality']=='model_proposed_unverified' and not record['candidate_geometry_supplied']
    assert record['edge_verification']['status']=='uncertain' # White fixture has no text pixel evidence.
    assert record['edge_verification']['policy']=='reference-text-edge/0.1.0'
    assert not record['edge_verification']['automatic_review_eligible']
    assert record['result']['targets'][0]['pixel_box']==[100,150,700,200]
    with Image.open(tmp_path/'loc/target-1.png') as crop:assert crop.size==(600,50)
    changed=scene();changed['nodes'][0]['presentation']={'offsetX':-500}
    assert reference_targets(scene())==reference_targets(changed)


@pytest.mark.parametrize('damage',['units','bounds','negative','status','duplicate','blank'])
def test_pixel_contract_never_guesses_units_or_clamps_invalid_boxes(damage):
    raw=response();raw['targets'][0]['box']={'xPx':100,'yPx':100,'widthPx':600,'heightPx':50}
    row=raw['targets'][0]
    if damage=='units':row['box']=response()['targets'][0]['box']
    if damage=='bounds':row['box']['xPx']=900
    if damage=='negative':row['box']['xPx']=-1
    if damage=='status':row['status']='ambiguous'
    if damage=='duplicate':raw['targets'].append(copy.deepcopy(row))
    if damage=='blank':row['identity_evidence']='  '
    with pytest.raises(ValueError):validate_pixel_locations(raw,reference_targets(scene()),[1000,500])


def test_card_scope_survives_text_node_type_without_leaking_geometry():
    current=scene();current['nodes'][0]['presentation']['variant']='text-card-stacked'
    target=reference_targets(current)[0]
    assert target['region_scope']=='complete_card'
    assert 'presentation' not in target['identity'] and 'slot' not in target['identity']


@pytest.mark.parametrize('status',['not_found','ambiguous','located'])
def test_null_visible_text_is_honest_only_for_unlocated_text(status):
    raw=response();raw['targets'][0].update(status=status,visible_text=None,
        box={'xPx':10,'yPx':10,'widthPx':20,'heightPx':20} if status=='located' else None)
    if status=='located':
        with pytest.raises(ValueError,match='MISSING_VISIBLE_TEXT'):
            validate_pixel_locations(raw,reference_targets(scene()),[1000,500])
    else:assert validate_pixel_locations(raw,reference_targets(scene()),[1000,500])['targets'][0]['box'] is None


def test_localization_metrics_penalize_tiny_partial_and_whole_canvas_boxes():
    from scripts.score_html_reference_localization import overlap
    gold=[100,100,700,300]
    assert overlap(gold,gold)==(1,1)
    iou,coverage=overlap([100,100,300,200],gold)
    assert iou<0.6 and coverage<0.9
    iou,coverage=overlap([0,0,2048,1152],gold)
    assert iou<0.6 and coverage==1
    assert overlap([800,500,900,600],gold)==(0,0)
