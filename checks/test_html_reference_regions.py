"""Text scope never silently expands to a background container."""
import copy

import pytest

from html_reference_localization import validate_region_locations


def targets(scope='visible_content'):
    return [{'targetId':'note','type':'text','region_scope':scope,'identity':{'text':'source'}}]


def response():
    return {'targets':[{'targetId':'note','status':'located',
        'container_box':{'xPx':20,'yPx':100,'widthPx':960,'heightPx':160},
        'text_boxes':[{'xPx':100,'yPx':130,'widthPx':350,'heightPx':30},
                      {'xPx':100,'yPx':175,'widthPx':280,'heightPx':30}],
        'identity_evidence':'two actual lines on light background','visible_text':'source second line'}]}


def test_text_envelope_excludes_background_and_includes_both_lines():
    raw=response();before=copy.deepcopy(raw)
    result=validate_region_locations(raw,targets(),[1000,500])['targets'][0]
    assert result['box']=={'xPx':100,'yPx':130,'widthPx':350,'heightPx':75}
    assert result['selected_source']=='text_envelope' and raw==before


@pytest.mark.parametrize('scope',['complete_card','complete_relation_module'])
def test_registered_complete_object_scope_preserves_container(scope):
    result=validate_region_locations(response(),targets(scope),[1000,500])['targets'][0]
    assert result['box']==response()['targets'][0]['container_box']
    assert result['selected_source']=='container_box'


def test_text_without_background_does_not_need_an_invented_container():
    raw=response();raw['targets'][0]['container_box']=None
    assert validate_region_locations(raw,targets(),[1000,500])['targets'][0]['box']['widthPx']==350


@pytest.mark.parametrize('damage',['outside_container','missing_lines','missing_text','missing_container','pixel_bounds',
    'unknown_target','duplicate','missing','legacy_box','negative_width','not_found_with_lines','not_found_with_container','blank_identity'])
def test_invalid_separated_regions_fail_closed(damage):
    raw=response();row=raw['targets'][0];expected=targets()
    if damage=='outside_container':row['text_boxes'][0]['xPx']=0
    if damage=='missing_lines':row['text_boxes']=[]
    if damage=='missing_text':row['visible_text']=None
    if damage=='missing_container':row['container_box']=None;expected=targets('complete_card')
    if damage=='pixel_bounds':row['container_box']['widthPx']=2000
    if damage=='unknown_target':row['targetId']='unknown'
    if damage=='duplicate':raw['targets'].append(copy.deepcopy(row))
    if damage=='missing':raw['targets']=[]
    if damage=='legacy_box':row['box']=row['container_box']
    if damage=='negative_width':row['text_boxes'][0]['widthPx']=-1
    if damage=='not_found_with_lines':row.update(status='not_found',container_box=None,visible_text=None)
    if damage=='not_found_with_container':row.update(status='not_found',text_boxes=[],visible_text=None)
    if damage=='blank_identity':row['identity_evidence']='  '
    with pytest.raises(ValueError):validate_region_locations(raw,expected,[1000,500])


def test_missing_object_has_neither_container_nor_text_region():
    raw=response();raw['targets'][0].update(status='not_found',container_box=None,text_boxes=[],visible_text=None)
    result=validate_region_locations(raw,targets(),[1000,500])['targets'][0]
    assert result['box'] is None and result['selected_source'] is None


@pytest.mark.parametrize('presence,box_ok,valid',[('present',True,True),('absent',False,True),
    ('present',False,False),('absent',True,False),('uncertain',False,False)])
def test_explicit_presence_cannot_hide_missing_or_conflicting_container(presence,box_ok,valid):
    raw=response();raw['targets'][0]['container_presence']=presence
    if not box_ok:raw['targets'][0]['container_box']=None
    if valid:
        assert validate_region_locations(raw,targets(),[1000,500],require_container_presence=True)['targets'][0]['box']
    else:
        with pytest.raises(ValueError):validate_region_locations(raw,targets(),[1000,500],require_container_presence=True)


def test_new_requests_require_presence_legacy_archives_do_not():
    assert validate_region_locations(response(),targets(),[1000,500])
    with pytest.raises(ValueError):validate_region_locations(response(),targets(),[1000,500],require_container_presence=True)


def test_missing_object_cannot_claim_uncertain_background_as_confirmed_absence():
    raw=response();raw['targets'][0].update(status='not_found',container_presence='uncertain',
        container_box=None,text_boxes=[],visible_text=None)
    with pytest.raises(ValueError):validate_region_locations(raw,targets(),[1000,500],require_container_presence=True)


@pytest.mark.parametrize('status',['located','ambiguous','not_found'])
def test_identity_evidence_optional_only_when_object_asserted_missing(status):
    raw=response();row=raw['targets'][0];row.pop('identity_evidence')
    row.update(status=status,container_presence='present' if status=='located' else 'absent')
    if status!='located':row.update(container_box=None,text_boxes=[],visible_text=None)
    if status=='not_found':
        assert validate_region_locations(raw,targets(),[1000,500],require_container_presence=True)['targets'][0]['identity_evidence'] is None
    else:
        with pytest.raises(ValueError,match='MISSING_IDENTITY'):
            validate_region_locations(raw,targets(),[1000,500],require_container_presence=True)


def test_layer_metrics_do_not_hide_background_omission_behind_correct_text():
    from scripts.score_html_reference_localization import score_layers
    row=response()['targets'][0];row.update(box=None,container_presence='absent',container_box=None)
    gold={'reference_sha256':'sealed','text_regions':{'note':[100,130,450,205]},
          'containers':{'note':[20,100,980,260]},'criteria':{'minimum_iou':0.6,'minimum_gold_coverage':0.9}}
    checked=score_layers({'reference_sha256':'sealed','result':{'targets':[row]}},gold)[0]
    assert checked['text_pass'] and not checked['container_pass']
    row.update(container_presence='present',container_box={'xPx':20,'yPx':100,'widthPx':960,'heightPx':160})
    assert score_layers({'reference_sha256':'sealed','result':{'targets':[row]}},gold)[0]['container_pass']
