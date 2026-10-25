from html_asset_geometry import asset_geometry_diagnostics


def test_visible_subject_and_named_anchor_are_reported_without_mutation():
    scene={'nodes':[{'id':'subject','type':'image','assetRef':{'id':'asset','version':'0.1.0'}}]}
    asset={'id':'asset','size':{'width':1000,'height':1000},'alpha_bbox':[400,400,600,600],
           'anchors':[{'id':'focus','x':500,'y':500},{'id':'edge','x':0,'y':0}]}
    result=asset_geometry_diagnostics(scene,{'assets':[asset]})
    row=result['targets'][0]
    assert row['visible_size']==[200,200] and row['visible_area_fraction']==0.04
    assert row['warnings']==['small_visible_subject']
    assert row['anchors']==[{'id':'focus','inside_visible_bbox':True},{'id':'edge','inside_visible_bbox':False}]
    assert result['automatic_crop'] is False and asset['alpha_bbox']==[400,400,600,600]
