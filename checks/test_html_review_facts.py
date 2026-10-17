"""One authoritative observation table, strict projection and no invented facts."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from html_design_agent import review_checklist, validate_fidelity, review_fidelity
from html_visual_review_service import HtmlReviewDependencies

ROOT=Path(__file__).resolve().parents[1]


def scene():
    return {'version':'0.7.0','nodes':[{'id':'caption','type':'text','slot':'caption',
            'runs':[{'text':'source','emphasis':False}],'role':'source'}]}


def facts():
    return {'facts':[{**check,'certainty':'confirmed','evidence':'Reference left / actual center',
                     'reference_alignment':'left' if check['dimension']=='typography' else None,
                     'differences':[]} for check in review_checklist(scene())]}


def test_alignment_difference_is_derived_without_second_model_problem_list():
    raw=facts()
    checked=validate_fidelity(raw,scene(),alignment={'caption':{'align':'center'}},require_facts=True)
    assert checked['status']=='changes_requested' and len(checked['issues'])==1
    assert checked['issues'][0]['requirement']=='typography'
    assert checked['fact_projection']['issue_sources'][0]['source']=='alignment_comparison'
    assert checked['facts']==raw['facts'] and set(raw)=={'facts'}
    row=next(r for r in checked['coverage'] if r['dimension']=='typography')
    assert row['status']=='issue' and row['issue_indices']==[0]


@pytest.mark.parametrize('damage',['missing','duplicate','extra','uncertain','blank','missing_alignment',
    'alignment_uncertain','alignment_on_geometry','dimension_mismatch','duplicate_top_level','legacy_only'])
def test_incomplete_or_conflicting_facts_fail_closed(damage):
    raw=facts();row=raw['facts'][2]
    if damage=='missing':raw['facts'].pop()
    if damage=='duplicate':raw['facts'].append(copy.deepcopy(row))
    if damage=='extra':row['targetId']='unknown'
    if damage=='uncertain':row['certainty']='uncertain'
    if damage=='blank':row['evidence']='  '
    if damage=='missing_alignment':row['reference_alignment']=None
    if damage=='alignment_uncertain':row['reference_alignment']='uncertain'
    if damage=='alignment_on_geometry':raw['facts'][0]['reference_alignment']='left'
    if damage=='dimension_mismatch':row['differences']=[{'requirement':'geometry','severity':'minor','suggestion':'move'}]
    if damage=='duplicate_top_level':raw['issues']=[]
    if damage=='legacy_only':raw={'status':'pass','issues':[]}
    with pytest.raises(ValueError):
        validate_fidelity(raw,scene(),alignment={'caption':{'align':'center'}},require_facts=True)


def test_matching_alignment_passes_and_reports_one_source_per_difference():
    raw=facts();raw['facts'][2]['differences']=[{'requirement':'typography','severity':'minor','suggestion':'enlarge'}]
    checked=validate_fidelity(raw,scene(),alignment={'caption':{'align':'left'}},require_facts=True)
    assert len(checked['issues'])==1 and checked['fact_projection']['issue_sources'][0]['source']=='reported_difference'


def test_actual_model_schema_has_facts_only_and_no_parallel_coverage_or_status(tmp_path):
    picture=tmp_path/'reference.png';Image.new('RGB',(1600,900),'white').save(picture)
    def generator(**kwargs):
        schema=json.loads(kwargs['schema_hint'])
        assert set(schema['properties'])=={'facts'}
        assert all(k not in schema['$defs']['Difference']['properties'] for k in ('targetId','evidence','reference_alignment'))
        assert len(kwargs['image_paths'])==2
        return facts()
    result=review_fidelity(scene(),picture,picture,{},None,folder=tmp_path/'review',run_dir=tmp_path,
                           deps=HtmlReviewDependencies(ROOT,generator))
    assert len(result['result']['facts'])==4 and result['coverage_check']['status']=='complete'
