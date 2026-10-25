import copy
import json
import pytest
from checks.test_html_asset_service import png_bytes


def resource(tmp_path):
    import hashlib
    from html_asset_service import inspect_asset_bytes
    data=png_bytes();file=tmp_path/'subject.png';file.write_bytes(data);facts=inspect_asset_bytes(data)
    asset={'id':'shared-subject','version':'0.1.0','file':'subject.png','sha256':hashlib.sha256(data).hexdigest(),
           'size':{'width':64,'height':64},'alpha_bbox':facts['alpha_bbox'],
           'anchors':[{'id':'focus','x':32,'y':32}],'need':'same subject'}
    folder=tmp_path/'planning/html_visual';folder.mkdir(parents=True,exist_ok=True)
    (folder/'resources.json').write_text(json.dumps({'assets':[asset]}),encoding='utf-8')
    (folder/'scene-source.json').write_text(json.dumps({'id':'source','nodes':[{'id':'image','assetRef':{'id':asset['id'],'version':asset['version']}}]}),encoding='utf-8')
    return asset,{'slot':'subject','id':asset['id'],'version':asset['version'],'sha256':asset['sha256']}


def test_cross_page_exact_binding_reuses_without_generation_and_preserves_source(tmp_path):
    from html_asset_reuse import available,bind_plan
    from html_production_service import supplied_asset_ids
    from checks.test_html_candidate_capacity_solver import ROOT
    asset,binding=resource(tmp_path)
    plan={'slots':{'subject':{'kind':'image','anchorId':'focus'}},'assets':[{'id':'new-image','slot':'subject','render_owner':'image_asset'}]}
    original=copy.deepcopy(plan)
    assert available(tmp_path)[0]['source_pages']==['source']
    result=bind_plan(plan,[binding],tmp_path)
    assert result['assets'][0]['id']==asset['id'] and plan==original
    assert supplied_asset_ids(result,{},tmp_path,ROOT)=={asset['id']}


@pytest.mark.parametrize('damage',['bytes','hash','anchor','slot','foreign','metadata'])
def test_reuse_rejects_wrong_identity_or_geometry(tmp_path,damage):
    from html_asset_reuse import bind_plan
    _,binding=resource(tmp_path)
    plan={'slots':{'subject':{'kind':'image','anchorId':'focus'}},'assets':[{'id':'new','slot':'subject','render_owner':'image_asset'}]}
    if damage=='bytes':(tmp_path/'subject.png').write_bytes(b'corrupt')
    elif damage=='hash':binding['sha256']='0'*64
    elif damage=='anchor':plan['slots']['subject']['anchorId']='not-present'
    elif damage=='slot':binding['slot']='other'
    elif damage=='foreign':binding['id']='other-project'
    else:
        path=tmp_path/'planning/html_visual/resources.json';data=json.loads(path.read_text());data['assets'][0]['alpha_bbox']=[0,0,64,64];path.write_text(json.dumps(data))
    with pytest.raises((ValueError,OSError)):
        bind_plan(plan,[binding],tmp_path)
