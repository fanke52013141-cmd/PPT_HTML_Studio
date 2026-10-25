from html_reconstruction_diagnostics import diagnostics


def test_diagnostics_deterministic_and_units_retained():
    scene={'nodes':[{'id':'card.body'}]}
    report={'capacityIssues':[{'target':'card.body','triggers':[
        {'actual':40,'limit':20,'unit':'css_px'},{'actual':4,'limit':3,'unit':'lines'}]}]}
    first=diagnostics(scene,report,stage='capacity')
    assert first==diagnostics(scene,report,stage='capacity')
    assert first['issues'][0]['targets']==['card.body']
    assert [m['unit'] for m in first['issues'][0]['measurements']]==['css_px','lines']


def test_unknown_code_is_incomplete_not_capacity():
    value=diagnostics({'nodes':[]},{'code':'UNKNOWN_ENGINE_CODE'},stage='review')
    assert value['issues'][0]['code']=='UNKNOWN_ENGINE_CODE'
    assert value['issues'][0]['kind']=='incomplete' and value['automatic_retry'] is False


def test_asset_geometry_and_reference_have_distinct_routes():
    scene={'nodes':[]}
    assert diagnostics(scene,{'code':'ASSET_HASH_MISMATCH'},stage='review')['routes']==['assets']
    assert diagnostics(scene,{'unresolved_targets':['a']},stage='review')['routes']==['evidence_review']
    assert diagnostics(scene,{'passed':True},stage='review')['issues']==[]


def test_no_fit_budget_and_unknown_remain_distinct():
    codes=['NO_DETERMINISTIC_CAPACITY_FIT','BUDGET_EXHAUSTED','PROVIDER_OUTCOME_UNKNOWN']
    rows=[diagnostics({'nodes':[]},{'code':c},stage='repair')['issues'][0] for c in codes]
    assert [r['kind'] for r in rows]==['no_fit','budget','unknown']
    assert all(not r['automatic_repair_eligible'] for r in rows)


def test_units_are_not_aggregated_or_rounded():
    report={'capacityIssues':[{'target':'card.body','triggers':[
        {'actual':3.125,'limit':3,'unit':'lines'}, {'actual':20.12345,'limit':20,'unit':'css_px'}]}]}
    value=diagnostics({'nodes':[{'id':'card.body'}]},report,stage='saved_repair')
    assert value['issues'][0]['measurements']==report['capacityIssues'][0]['triggers']
    report['capacityIssues'][0]['triggers'][0]['actual']=999
    assert value['issues'][0]['measurements'][0]['actual']==3.125


def test_every_registered_code_and_unknown_units_have_explicit_routes():
    from html_reconstruction_diagnostics import CATALOG
    for code,(kind,route,label) in CATALOG.items():
        row=diagnostics({'nodes':[]},{'code':code},stage='review')['issues'][0]
        assert (row['kind'],row['route'],row['action_label'])==(kind,route,label)
    value=diagnostics({'nodes':[]},{'capacityIssues':[{'triggers':[{'unit':'mystery','actual':1}]}]},stage='capacity')
    assert value['issues'][0]['unknown_units']==['mystery']
    assert value['issues'][0]['automatic_repair_eligible'] is False
    row=diagnostics({'nodes':[]},{'issues':[{'code':'UNRECOGNIZED'}]},stage='temporal')['issues'][0]
    assert row['kind']=='incomplete' and not row['automatic_repair_eligible']


def test_geometry_units_and_earliest_time_are_preserved():
    issue={'code':'TEMPORAL_OVERLAP','targets':['a','b'],'firstTimeMs':12.5,'measured':{'overlapWidth':2.25,'overlapHeight':8}}
    row=diagnostics({'nodes':[]},{'issues':[issue],'geometry_preflight':{'issues':[issue]}},stage='temporal')['issues']
    assert len(row)==1 and row[0]['first_time_ms']==12.5
    assert row[0]['measurement_units']=={'overlapWidth':'canvas_px','overlapHeight':'canvas_px'}
