"""Verify all 69 rules; --require-all fails until every required layer passes."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from html_acceptance_criteria import read,verify,AUTOMATED,validate_rules  # noqa:E402
from artifact_fingerprint import sha256_json,sha256_file  # noqa:E402
from pipeline_lifecycle import write_json_atomic  # noqa:E402


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,default=ROOT/'docs/plans/html-backend-development/reconstruction-acceptance-plan-v2.json')
    p.add_argument('--rules',type=Path,default=ROOT/'config/html_acceptance_criteria.json')
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--capture-junit',type=Path,action='append',default=[])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--require-all',action='store_true')
    a=p.parse_args();plan,rules=read(a.plan),read(a.rules)
    if a.capture_junit:
        import xml.etree.ElementTree as ET
        entries=validate_rules(plan,rules);records=[]
        for rule in entries:
            for facet in rule['required_facets']:
                if facet not in AUTOMATED:continue
                checks=[c for c in rule['checks'] if c['facet']==facet]
                for path in a.capture_junit:
                    manifest_path=path.resolve().parent/'manifest.json'
                    if not manifest_path.is_file():raise ValueError('JUNIT_REQUIRES_SEALED_RUN_MANIFEST')
                    manifest=read(manifest_path)
                    cases=list(ET.parse(path).getroot().iter('testcase'))
                    def exists(check):
                        module,name=check['selector'].split('::');cls=module.removesuffix('.py').replace('/','.').removeprefix('checks.')
                        return any(c.get('classname','').removeprefix('checks.')==cls and
                                   (c.get('name')==name or c.get('name','').startswith(name+'[')) for c in cases)
                    if not all(exists(c) for c in checks):continue
                    sources=set(rule['source_paths']+[c['selector'].split('::')[0] for c in checks])
                    records.append({'criterion_id':rule['id'],'facet':facet,'kind':'junit',
                        'provenance':'offline_engineering_tests','artifact':{
                            'path':path.resolve().relative_to(ROOT).as_posix(),'sha256':sha256_file(path)},
                        'run_manifest':{'path':manifest_path.relative_to(ROOT).as_posix(),'sha256':sha256_file(manifest_path)},
                        'sources':{name:manifest['sources'][name] for name in sorted(sources)}})
                    break
        write_json_atomic(a.evidence,{'rules_sha256':sha256_json(rules),'records':records})
    result=verify(plan,rules,read(a.evidence),ROOT)
    write_json_atomic(a.output,result);print(result['counts'])
    return 1 if result['counts']['failed'] or (a.require_all and not result['all_required_passed']) else 0


if __name__=='__main__':sys.exit(main())
