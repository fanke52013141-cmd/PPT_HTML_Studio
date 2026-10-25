"""Controlled full-render/protection/overflow evidence for both new templates."""
import argparse
import copy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from artifact_fingerprint import sha256_file,sha256_json  # noqa:E402
from html_storyboard_planning import normalize_html_scene_plan,load_template_catalog,HtmlScenePlanError  # noqa:E402
from html_production_service import compile_plan  # noqa:E402
from html_linked_layout import solve_production_layout  # noqa:E402
from html_visual_review_service import HtmlReviewDependencies,review_scene  # noqa:E402
from pipeline_lifecycle import write_json_atomic  # noqa:E402


def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    source=ROOT/'checks/fixtures/followup-layout-plans.json'
    records=json.loads(source.read_text(encoding='utf-8'));catalog=load_template_catalog(ROOT)
    rows=[]
    def no_provider(**kwargs):raise AssertionError('Provider must not be called')
    deps=HtmlReviewDependencies(ROOT,no_provider)
    for record in records:
        ident=record['plan']['templateRef']['id']
        plan=normalize_html_scene_plan(record['plan'],catalog,contract_slide=record['contract'])
        original,binding=compile_plan(plan,record['contract'],catalog)
        for scenario in ('baseline','repair','protected','overflow'):
            folder=output/ident/scenario;folder.mkdir(parents=True)
            write_json_atomic(folder/'planning/visual_contract.json',{'slides':[record['contract']]})
            scene=copy.deepcopy(original);before=sha256_json(scene)
            if scenario=='baseline':
                report=review_scene(scene,run_dir=folder,deps=deps,preflight_dir=folder/'full')
                passed=report.get('passed') and report.get('geometry_preflight',{}).get('coverage',{}).get('frame_complete')
                result={'expected':'complete_pass','passed':bool(passed),'report':report}
            elif scenario in ('repair','protected'):
                scene['version']='0.5.0'
                card=next(n for n in scene['nodes'] if n['id']=='card-1')
                wide=ident=='wide-body-pair-v1';card['presentation']={'height':230} if wide else {'width':520}
                before=sha256_json(scene)
                manual={'protected_paths':[['scene','nodes','card-2','presentation','offsetY' if wide else 'offsetX']]} if scenario=='protected' else None
                repaired=solve_production_layout(scene,binding,run_dir=folder,deps=deps,manual=manual,
                    beats=record['contract']['narration_beats'])
                expected='needs_revision' if manual else 'candidate'
                passed=repaired['summary']['status']==expected and repaired['binding']==binding
                if manual:passed=passed and repaired['scene']==scene
                else:passed=passed and repaired['report']['geometry_preflight']['coverage']['frame_complete']
                result={'expected':expected,'passed':bool(passed),'result':repaired}
            else:
                crowded=copy.deepcopy(record['plan']);crowded['slots']['card-1']['body']='超长内容。'*200
                try:
                    overflow=normalize_html_scene_plan(crowded,catalog,contract_slide=record['contract'])
                    candidate,_=compile_plan(overflow,record['contract'],catalog)
                    report=review_scene(candidate,run_dir=folder,deps=deps)
                    result={'expected':'rejected','passed':report['passed'] is False,'report':report}
                except HtmlScenePlanError as error:
                    result={'expected':'rejected','passed':True,'code':getattr(error,'code','PLAN_REJECTED'),'message':str(error)}
            result.update(template=ident,scenario=scenario,source_unchanged=sha256_json(scene)==before)
            result['passed']=result['passed'] and result['source_unchanged']
            write_json_atomic(folder/'acceptance.json',result);rows.append(result)
    summary={'format':'hps.followup-layout-benchmark/0.1.0','provenance':'controlled_fixture',
        'passed':all(r['passed'] for r in rows),'cases':rows,'provider_calls':0,'author_writes':0,'human_approval':'pending',
        'fixture_sha256':sha256_file(source),'runner_sha256':sha256_file(Path(__file__))}
    write_json_atomic(output/'summary.json',summary)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    result=run(p.parse_args().output)
    print({'passed':result['passed'],'cases':len(result['cases'])})
    return 0 if result['passed'] else 1


if __name__=='__main__':sys.exit(main())
