"""Preserve original-browser evidence for linked cards and declared routing.

Controlled fixtures only; no provider, author save or human approval.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from html_linked_layout import solve_production_layout  # noqa: E402
from html_production_service import compile_plan  # noqa: E402
from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan  # noqa: E402
from html_visual_review_service import HtmlReviewDependencies  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402


def run(output):
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    records=[]
    cases=json.loads((ROOT/'checks/fixtures/course-structure-plans.json').read_text(encoding='utf-8'))
    for name in ('three-cards-summary','point-routing','protected-column','staggered-frame','grid-rows','protected-grid'):
        folder=output/name
        if name in ('grid-rows','protected-grid'):
            record=json.loads((ROOT/'checks/fixtures/knowledge-grid-plan.json').read_text(encoding='utf-8'))
            catalog=load_template_catalog(ROOT)
            contract=record['contract']
            plan=normalize_html_scene_plan(record['plan'],catalog,contract_slide=contract)
            scene,binding=compile_plan(plan,contract,catalog)
            scene['version']='0.5.0'
            next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'height':230}
        elif name=='point-routing':
            contract=copy.deepcopy(cases[3]['contract'])
            scene,binding=compile_plan(cases[3]['plan'],contract,load_template_catalog(ROOT))
            arrow=next(n for n in scene['nodes'] if n['id']=='relation-1')
            arrow['from']['point']={'x':0.5,'y':1}
            arrow['to']['point']={'x':0.5,'y':0}
        else:
            scene=json.loads((ROOT/'checks/fixtures/capacity-baseline/ordinary.json').read_text(encoding='utf-8'))
            next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']=(
                {'width':900} if name=='staggered-frame' else {'height':140})
            binding=None
            contract={'slide_id':scene['id'],'narration_beats':[]}
        manual={'protected_paths':[['scene','nodes','card-2','presentation','offsetY']]} if name=='protected-column' else None
        if name=='protected-grid':
            manual={'protected_paths':[['scene','nodes','card-3','presentation','offsetY']]}
        write_json_atomic(folder/'planning/visual_contract.json',{'slides':[contract]})
        write_json_atomic(folder/'input-scene.json',scene)
        write_json_atomic(folder/'input-binding.json',binding)
        original=copy.deepcopy(scene)

        def no_provider(**kwargs):
            raise AssertionError('No provider in deterministic layout acceptance')

        result=solve_production_layout(scene,binding,run_dir=folder,manual=manual,
            beats=contract['narration_beats'],deps=HtmlReviewDependencies(ROOT,no_provider))
        expected='needs_revision' if manual else 'candidate'
        summary=result['summary']
        passed=summary['status']==expected and scene==original and result['binding']==binding
        capacity=summary.get('capacity',summary)
        before=folder/capacity['audit']/'000/render.png'
        if before.is_file():
            shutil.copyfile(before,folder/'before.png')
        if not manual:
            passed=passed and result['report']['geometry_preflight']['passed'] is True
            shot=folder/result['report']['screenshot']
            shutil.copyfile(shot,folder/'after.png')
        else:
            passed=passed and result['scene']==original and any(a.get('code')=='MANUAL_FIELD_PROTECTED' for a in summary['attempts'])
        record={'case':name,'passed':bool(passed),'expected':expected,'summary':summary,
                'preflight':result['report'].get('geometry_preflight'),'source_unchanged':scene==original}
        records.append(record)
        write_json_atomic(folder/'acceptance.json',record)
    summary={'format':'hps.linked_layout_acceptance/0.1.0','passed':all(r['passed'] for r in records),
             'provenance':'controlled_fixture','provider_calls':0,'author_writes':0,'approvals':0,'cases':records}
    write_json_atomic(output/'summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=run(args.output)
    print(json.dumps({'passed':result['passed'],'cases':[(r['case'],r['passed']) for r in result['cases']]}))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    sys.exit(main())
