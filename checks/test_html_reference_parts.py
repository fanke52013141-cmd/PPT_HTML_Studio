"""Content-part coverage and geometry are independent acceptance checks."""
import copy

import pytest

from html_reference_localization import mapped_reference_targets, validate_mapped_locations


def case():
    targets=mapped_reference_targets({'nodes':[{'id':'h','type':'header','number':'02','title':'正式定义'}]})
    boxes=[{'xPx':20,'yPx':30,'widthPx':40,'heightPx':30},
           {'xPx':200,'yPx':30,'widthPx':180,'heightPx':30}]
    raw={'targets':[{'targetId':'h','status':'located','container_presence':'absent','container_box':None,
        'identity_evidence':'left numeral and separate title',
        'part_regions':[{'partId':p['partId'],'status':'located','regions':[{'text':p['text'],'box':b}]}
                        for p,b in zip(targets[0]['text_parts'],boxes)]}]}
    return targets,raw


def test_number_is_explicit_content_identity_and_separate_region():
    targets,raw=case();before=copy.deepcopy(raw)
    assert targets[0]['identity']['number']=='02'
    result=validate_mapped_locations(raw,targets,[500,300])['targets'][0]
    assert result['box']=={'xPx':20,'yPx':30,'widthPx':360,'heightPx':30}
    assert len(result['text_boxes'])==2 and raw==before


@pytest.mark.parametrize('damage',['missing_number','duplicate_part','unknown_part','number_without_region',
    'wrong_transcript','shared_box','outside','partial_status','legacy_text_boxes','missing_target'])
def test_missing_or_fabricated_part_declarations_cannot_pass(damage):
    targets,raw=case();row=raw['targets'][0];part=row['part_regions'][0]
    if damage=='missing_number':row['part_regions'].pop(0)
    if damage=='duplicate_part':row['part_regions'].append(copy.deepcopy(part))
    if damage=='unknown_part':part['partId']='other'
    if damage=='number_without_region':part['regions']=[]
    if damage=='wrong_transcript':part['regions'][0]['text']='03'
    if damage=='shared_box':row['part_regions'][1]['regions'][0]['box']=part['regions'][0]['box']
    if damage=='outside':part['regions'][0]['box']['xPx']=490
    if damage=='partial_status':part.update(status='not_found',regions=[])
    if damage=='legacy_text_boxes':row['text_boxes']=[]
    if damage=='missing_target':raw['targets']=[]
    with pytest.raises(ValueError):validate_mapped_locations(raw,targets,[500,300])


def test_multiline_part_keeps_order_and_all_line_bounds():
    targets,raw=case();part=raw['targets'][0]['part_regions'][1]
    part['regions']=[{'text':'正式','box':{'xPx':200,'yPx':30,'widthPx':80,'heightPx':30}},
                     {'text':'定义','box':{'xPx':200,'yPx':90,'widthPx':80,'heightPx':30}}]
    assert validate_mapped_locations(raw,targets,[500,300])['targets'][0]['box']['heightPx']==90
    part['regions'].reverse()
    with pytest.raises(ValueError,match='MISMATCH'):validate_mapped_locations(raw,targets,[500,300])


@pytest.mark.parametrize('status',['not_found','ambiguous'])
def test_unlocated_target_keeps_parts_without_inventing_coordinates(status):
    targets,raw=case();row=raw['targets'][0];row.update(status=status)
    for part in row['part_regions']:part.update(status=status,regions=[])
    assert validate_mapped_locations(raw,targets,[500,300])['targets'][0]['box'] is None


def test_repeated_text_has_distinct_identity_paths_not_text_as_key():
    targets=mapped_reference_targets({'nodes':[{'id':'s','type':'summary',
        'from':{'text':'机关'},'to':{'text':'机关'},'term':'遴选','takeaway':'择优'}]})
    assert [p['partId'] for p in targets[0]['text_parts']]==['term','takeaway','from/text','to/text']


def test_geometry_change_does_not_change_part_identity():
    scene={'nodes':[{'id':'h','type':'header','number':'02','title':'标题','slot':'private',
                     'presentation':{'offsetX':200},'actions':[{'x':30}]}]}
    before=mapped_reference_targets(scene)
    scene['nodes'][0]['presentation']={'offsetX':-400}
    assert mapped_reference_targets(scene)==before
    assert 'presentation' not in str(before)
