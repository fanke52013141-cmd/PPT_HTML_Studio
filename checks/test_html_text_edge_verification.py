"""Edge diagnostics abstain on ambiguous evidence and never repair model boxes."""
import copy

import numpy as np
from PIL import Image,ImageDraw
import pytest

from html_text_edge_verification import inspect_text_edge,verify_text_edges


def sample(side=None,background='white',foreground='black'):
    image=Image.new('RGB',(240,160),background);draw=ImageDraw.Draw(image)
    box={'xPx':60,'yPx':50,'widthPx':120,'heightPx':60}
    # Disconnected upright strokes act as analytic ink, not an OCR fixture.
    draw.line((85,65,85,95),fill=foreground,width=3)
    if side=='top':draw.line((110,45,110,80),fill=foreground,width=3)
    if side=='bottom':draw.line((110,85,110,117),fill=foreground,width=3)
    if side=='left':draw.line((55,80,90,80),fill=foreground,width=3)
    if side=='right':draw.line((150,80,188,80),fill=foreground,width=3)
    return image,box


@pytest.mark.parametrize('side',['top','bottom','left','right'])
@pytest.mark.parametrize('background,foreground',[('white','black'),('#e8ebef','#1b2430'),('#102030','white'),('white','#3265b3')])
def test_connected_ink_crossing_each_edge_is_reported(side,background,foreground):
    image,box=sample(side,background,foreground);before=image.tobytes();original=copy.deepcopy(box)
    result=inspect_text_edge(image,box)
    assert result['status']=='possible_clip'
    assert side in result['components'][0]['sides']
    assert image.tobytes()==before and box==original and not result['box_changed']


def test_detached_icon_and_rule_outside_box_are_not_absorbed():
    image,box=sample();draw=ImageDraw.Draw(image)
    draw.ellipse((20,65,45,90),fill='blue');draw.line((45,120,200,120),fill='black',width=3)
    result=inspect_text_edge(image,box)
    assert result['status']=='no_detected_clip' and result['components']==[]


def test_tight_but_non_crossing_boundary_does_not_claim_complete():
    image,box=sample();ImageDraw.Draw(image).line((100,50,100,80),fill='black',width=3)
    result=inspect_text_edge(image,box)
    assert result['status']=='uncertain' and 'ink_touches_boundary' in result['reasons']


@pytest.mark.parametrize('kind',['rule','icon','neighbour','container','image_edge','background','blank','low_contrast'])
def test_ambiguous_evidence_abstains(kind):
    image,box=sample('left');kwargs={};draw=ImageDraw.Draw(image)
    if kind=='rule':
        image,box=sample();ImageDraw.Draw(image).line((45,80,200,80),fill='black',width=2)
    if kind=='icon':
        image,box=sample();ImageDraw.Draw(image).rectangle((45,65,85,100),fill='blue')
    if kind=='neighbour':kwargs['neighbours']=[[40,70,58,90]]
    if kind=='container':kwargs['container']=[58,40,200,130]
    if kind=='image_edge':box['xPx']=0
    if kind=='background':
        values=np.indices((160,240)).sum(axis=0)%2
        image=Image.fromarray(np.repeat((values*255).astype('uint8')[:,:,None],3,axis=2))
    if kind=='blank':image=Image.new('RGB',image.size,'white')
    if kind=='low_contrast':image,box=sample('left','white','#eeeeee')
    assert inspect_text_edge(image,box,**kwargs)['status']=='uncertain'


def test_small_noise_crossing_does_not_become_proven_clipping():
    image,box=sample();draw=ImageDraw.Draw(image)
    draw.point((59,80),fill='black');draw.point((60,80),fill='black')
    assert inspect_text_edge(image,box)['status']=='uncertain'


@pytest.mark.parametrize('damage',['boolean','negative','zero','outside'])
def test_invalid_geometry_is_not_silently_clamped(damage):
    image,box=sample()
    if damage=='boolean':box['xPx']=True
    if damage=='negative':box['yPx']=-1
    if damage=='zero':box['heightPx']=0
    if damage=='outside':box['widthPx']=999
    with pytest.raises(ValueError):inspect_text_edge(image,box)


def test_batch_preserves_model_result_and_keeps_missing_targets_unchecked():
    image,box=sample('left')
    result={'targets':[{'targetId':'t','status':'located','container_box':None,
        'part_regions':[{'partId':'title','regions':[{'text':'字','box':box}]}]},
        {'targetId':'missing','status':'not_found','part_regions':[]}]}
    before=copy.deepcopy(result);checked=verify_text_edges(image,result)
    assert checked['status']=='needs_review' and checked['counts']['possible_clip']==1
    assert checked['regions'][0]['partId']=='title'
    assert not checked['automatic_review_eligible'] and not checked['identity_verified']
    assert result==before


def test_no_checked_regions_is_uncertain_not_a_pass():
    assert verify_text_edges(Image.new('RGB',(20,20),'white'),{'targets':[]})['status']=='uncertain'


def test_transparent_pixels_do_not_become_black_ink():
    image,box=sample('left');image=image.convert('RGBA');image.putpixel((50,50),(0,0,0,0))
    checked=inspect_text_edge(image,box)
    assert checked['status']=='uncertain' and 'transparent_background' in checked['reasons']


def test_window_and_component_budgets_abstain(monkeypatch):
    import html_text_edge_verification as edges
    image,box=sample('left')
    monkeypatch.setattr(edges,'MAX_WINDOW_PIXELS',1)
    assert inspect_text_edge(image,box)['reasons']==['window_budget_exceeded']
    monkeypatch.setattr(edges,'MAX_WINDOW_PIXELS',500000)
    monkeypatch.setattr(edges,'MAX_COMPONENT_PIXELS',1)
    assert inspect_text_edge(image,box)['reasons']==['component_budget_exceeded']
    monkeypatch.setattr(edges,'MAX_COMPONENT_PIXELS',100000)
    monkeypatch.setattr(edges,'MAX_BOUNDARY_COMPONENTS',0)
    assert inspect_text_edge(image,box)['reasons']==['boundary_component_budget_exceeded']


def test_detached_missing_character_remains_an_explicit_blind_spot():
    image,box=sample();ImageDraw.Draw(image).line((195,65,195,95),fill='black',width=3)
    checked=inspect_text_edge(image,box)
    assert checked['status']=='no_detected_clip' and not checked['identity_verified']
