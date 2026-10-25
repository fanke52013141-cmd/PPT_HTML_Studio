"""Read-only per-criterion evidence verification. Never execute report commands."""
import json
import ast
from pathlib import Path
import xml.etree.ElementTree as ET
from artifact_fingerprint import sha256_file, sha256_json

FACETS={
    'unit':['unit'], 'integration':['integration'], 'real_browser':['real_browser'],
    'evidence':['evidence'], 'integration_real_browser':['integration','real_browser'],
    'file_evaluation_and_model':['file_evaluation','real_model'],
    'integration_and_paired_model':['integration','paired_model'],
    'integration_and_model':['integration','real_model'],
    'integration_fault_injection':['integration','fault_injection'],
    'real_model_and_human_review':['real_model','human_review'],
    'release_and_real_end_to_end':['release','real_end_to_end'],
}
AUTOMATED={'unit','integration','real_browser','fault_injection'}


def safe(root,name):
    if not isinstance(name,str) or not name or '\\' in name:
        raise ValueError('EVIDENCE_PATH_INVALID')
    path=(Path(root)/name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(Path(root).resolve()):
        raise ValueError('EVIDENCE_PATH_INVALID')
    return path


def validate_rules(plan,rules):
    expected={f'AC-{i:03d}' for i in range(1,70)}
    originals={r['id']:r for r in plan['acceptance']}
    entries=rules['criteria']
    if len(plan['acceptance'])!=69 or len(originals)!=69 or set(originals)!=expected or len(entries)!=69 or {r['id'] for r in entries}!=expected:
        raise ValueError('AC_RULES_INCOMPLETE_OR_DUPLICATE')
    for rule in entries:
        original=originals[rule['id']]
        if rule['criterion_sha256']!=sha256_json(original) or rule['required_level']!=original['required_level']:
            raise ValueError('AC_RULE_STALE:'+rule['id'])
        if rule['required_facets']!=FACETS[rule['required_level']] or not rule.get('checks') or not rule.get('remaining'):
            raise ValueError('AC_RULE_GATE_MISSING:'+rule['id'])
        if any(not c.get('selector') or c.get('coverage') not in ('complete','supporting') for c in rule['checks']):
            raise ValueError('AC_RULE_CHECK_INVALID')
        if {c['facet'] for c in rule['checks']}!=set(rule['required_facets']):
            raise ValueError('AC_RULE_CHECK_FACETS_INCOMPLETE')
    return entries


def verify(plan,rules,evidence,repo):
    entries=validate_rules(plan,rules)
    if evidence.get('rules_sha256')!=sha256_json(rules):raise ValueError('EVIDENCE_RULES_STALE')
    records=evidence.get('records',[])
    identities=[(r['criterion_id'],r['facet']) for r in records]
    if len(set(identities))!=len(identities):raise ValueError('DUPLICATE_AC_EVIDENCE')
    by_id={r['id']:r for r in entries}
    for record in records:
        if record['criterion_id'] not in by_id or record['facet'] not in by_id[record['criterion_id']]['required_facets']:
            raise ValueError('UNDECLARED_AC_EVIDENCE')
    results=[];verified_runs={}
    for rule in entries:
        facets=[]
        for facet in rule['required_facets']:
            record=next((r for r in records if (r['criterion_id'],r['facet'])==(rule['id'],facet)),None)
            status,reason='pending','MISSING_REQUIRED_EVIDENCE'
            if record:
                try:
                    artifact=record['artifact'];path=safe(repo,artifact['path'])
                    if sha256_file(path)!=artifact['sha256']:raise ValueError('EVIDENCE_BYTES_CHANGED')
                    checks=[c for c in rule['checks'] if c['facet']==facet]
                    required_sources={c['selector'].split('::')[0] for c in checks}
                    required_sources.update(rule['source_paths'])
                    sources=record.get('sources',{})
                    if not required_sources or not required_sources.issubset(sources):raise ValueError('EVIDENCE_SOURCE_CLOSURE_MISSING')
                    if any(sha256_file(safe(repo,p))!=h for p,h in sources.items()):raise ValueError('EVIDENCE_SOURCE_STALE')
                    if facet not in AUTOMATED:
                        # File/model/human/release proof requires its dedicated authority,
                        # not an uploaded passed flag or a renamed JUnit file.
                        reason='EXTERNAL_AUTHORITY_REQUIRED'
                    else:
                        if record.get('kind')!='junit' or record.get('provenance')!='offline_engineering_tests':
                            raise ValueError('EVIDENCE_KIND_INVALID')
                        sealed=record.get('run_manifest')
                        if not sealed:raise ValueError('UNSEALED_TEST_EXECUTION')
                        manifest_path=safe(repo,sealed['path'])
                        if sha256_file(manifest_path)!=sealed['sha256']:raise ValueError('RUN_MANIFEST_CHANGED')
                        run_key=(str(manifest_path),sealed['sha256'])
                        if run_key not in verified_runs:
                            from scripts.verify_reconstruction_v2_acceptance import validate_bundle
                            outcome=validate_bundle(manifest_path.parent,Path(repo).resolve())
                            if not outcome['passed']:raise ValueError('RUN_BUNDLE_STALE_OR_INCOMPLETE')
                            verified_runs[run_key]=read(manifest_path)
                        manifest=verified_runs[run_key]
                        relative=path.relative_to(manifest_path.parent).as_posix()
                        if manifest['files'].get(relative)!=artifact['sha256']:
                            raise ValueError('TEST_NOT_IN_SEALED_RUN')
                        if any(manifest['sources'].get(name)!=digest for name,digest in sources.items()):
                            raise ValueError('SOURCE_NOT_FROM_TEST_EXECUTION')
                        cases=list(ET.parse(path).getroot().iter('testcase'))
                        for check in checks:
                            module,name=check['selector'].split('::',1)
                            cls=module.removesuffix('.py').replace('/','.')
                            matched=[c for c in cases if c.get('classname','').removeprefix('checks.')==cls.removeprefix('checks.')
                                     and (c.get('name')==name or c.get('name','').startswith(name+'['))]
                            if not matched:raise ValueError('REQUIRED_CHECK_MISSING')
                            if any(any(c.find(k) is not None for k in ('failure','error','skipped')) for c in matched):
                                raise ValueError('REQUIRED_CHECK_NOT_PASSED')
                            if 'expected_cases' in check and {c.get('name') for c in matched}!=set(check['expected_cases']):
                                raise ValueError('PARAMETER_CASES_INCOMPLETE')
                            if check['coverage']=='complete' and 'expected_cases' not in check:
                                source=ast.parse(safe(repo,module).read_text(encoding='utf-8'))
                                function=next((n for n in source.body if isinstance(n,ast.FunctionDef) and n.name==name),None)
                                if function is None:raise ValueError('REQUIRED_CHECK_SOURCE_MISSING')
                                if any('parametrize' in ast.unparse(d) for d in function.decorator_list):
                                    raise ValueError('PARAMETER_EXPECTATIONS_REQUIRED')
                        complete=bool(checks) and all(c['coverage']=='complete' for c in checks)
                        status,reason=('passed','EXACT_CHECKS_PASSED') if complete else ('pending','SUPPORTING_PROOF_ONLY')
                except (OSError,ValueError,KeyError,ET.ParseError) as error:
                    status,reason='failed',str(error)
            facets.append({'facet':facet,'status':status,'reason':reason})
        status='failed' if any(f['status']=='failed' for f in facets) else 'passed' if all(f['status']=='passed' for f in facets) else 'pending'
        results.append({'id':rule['id'],'status':status,'facets':facets,'remaining':rule['remaining'] if status!='passed' else None})
    return {'format':'hps.ac-verification/0.1.0','rules_sha256':sha256_json(rules),'criteria':results,
            'counts':{s:sum(r['status']==s for r in results) for s in ('passed','failed','pending')},
            'all_required_passed':all(r['status']=='passed' for r in results)}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
