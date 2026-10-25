import copy
import json
from pathlib import Path
import pytest
from artifact_fingerprint import sha256_file,sha256_json
from html_acceptance_criteria import verify,validate_rules

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return (json.loads((ROOT/'docs/plans/html-backend-development/reconstruction-acceptance-plan-v2.json').read_text(encoding='utf-8')),
            json.loads((ROOT/'config/html_acceptance_criteria.json').read_text(encoding='utf-8')))


def test_all_69_rules_preserve_required_layers():
    import ast
    plan,rules=inputs();entries=validate_rules(plan,rules)
    assert len(entries)==69
    for rule in entries:
        for check in rule['checks']:
            module,name=check['selector'].split('::')
            functions={n.name for n in ast.parse((ROOT/module).read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
            assert name in functions,(rule['id'],check['selector'])
    result=verify(plan,rules,{'rules_sha256':sha256_json(rules),'records':[]},ROOT)
    assert result['counts']=={'passed':0,'failed':0,'pending':69}
    missing=copy.deepcopy(rules);missing['criteria'].pop()
    with pytest.raises(ValueError,match='INCOMPLETE'):validate_rules(plan,missing)


@pytest.mark.parametrize('damage',['none','missing','stale_source','stale_report','skip','failure','wrong_test','wrong_rule','supporting','unsealed'])
def test_missing_stale_skipped_evidence_never_passes(tmp_path,damage):
    plan,rules=inputs();rule=rules['criteria'][5]
    module,name=rule['checks'][0]['selector'].split('::')
    for source in set(rule['source_paths']+[module]):
        path=tmp_path/source;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(f'def {name}():\n    return True\n')
    from checks.test_html_optimization_acceptance import bundle
    directory,_,manifest=bundle(tmp_path)
    report=directory/'tests.xml'
    content=f'<testcase classname="{module.removesuffix(".py").replace("/",".")}" name="{name}">' + ('<skipped/>' if damage=='skip' else '<failure/>' if damage=='failure' else '') + '</testcase>'
    report.write_text('<testsuite>'+content+'</testsuite>')
    record={'criterion_id':rule['id'],'facet':'unit','kind':'junit','provenance':'offline_engineering_tests',
        'artifact':{'path':'evidence/tests.xml','sha256':sha256_file(report)},
        'sources':{p:sha256_file(tmp_path/p) for p in set(rule['source_paths']+[module])}}
    manifest['sources']=copy.deepcopy(record['sources']);manifest['files']['tests.xml']=sha256_file(report)
    manifest_path=directory/'manifest.json';manifest_path.write_text(json.dumps(manifest))
    record['run_manifest']={'path':'evidence/manifest.json','sha256':sha256_file(manifest_path)}
    if damage=='missing':records=[]
    else:records=[record]
    if damage=='stale_source':(tmp_path/module).write_text('changed')
    if damage=='stale_report':report.write_text('changed')
    if damage=='wrong_test':
        report.write_text('<testsuite>'+content.replace(name,'unrelated')+'</testsuite>');record['artifact']['sha256']=sha256_file(report)
    if damage=='supporting':rule['checks'][0]['coverage']='supporting'
    if damage=='unsealed':record.pop('run_manifest')
    evidence={'rules_sha256':sha256_json(rules),'records':records}
    if damage=='wrong_rule':evidence['rules_sha256']='0'*64
    if damage=='wrong_rule':
        with pytest.raises(ValueError,match='RULES_STALE'):verify(plan,rules,evidence,tmp_path)
        return
    result=verify(plan,rules,evidence,tmp_path)
    status=result['criteria'][5]['status']
    assert status==('passed' if damage=='none' else 'pending' if damage in ('missing','supporting') else 'failed')


def test_duplicate_unknown_criterion_and_unsafe_path_are_rejected(tmp_path):
    plan,rules=inputs();record={'criterion_id':'AC-006','facet':'unit','artifact':{'path':'../escape','sha256':'0'*64}}
    evidence={'rules_sha256':sha256_json(rules),'records':[record,record]}
    with pytest.raises(ValueError,match='DUPLICATE'):verify(plan,rules,evidence,tmp_path)
    evidence['records']=[{**record,'criterion_id':'AC-999'}]
    with pytest.raises(ValueError,match='UNDECLARED'):verify(plan,rules,evidence,tmp_path)
    evidence['records']=[record]
    assert verify(plan,rules,evidence,tmp_path)['criteria'][5]['status']=='failed'


def test_external_model_or_human_claims_do_not_pass_from_uploaded_flag(tmp_path):
    plan,rules=inputs();rule=rules['criteria'][59];module=rule['checks'][0]['selector'].split('::')[0]
    path=tmp_path/module;path.parent.mkdir(parents=True);path.write_text('source')
    report=tmp_path/'claim.json';report.write_text('{"passed":true,"human_approved":true}')
    records=[{'criterion_id':rule['id'],'facet':facet,'kind':'claim','provenance':'real_model',
              'artifact':{'path':'claim.json','sha256':sha256_file(report)},'sources':{module:sha256_file(path)}}
             for facet in rule['required_facets']]
    value=verify(plan,rules,{'rules_sha256':sha256_json(rules),'records':records},tmp_path)['criteria'][59]
    assert value['status']=='pending'
