"""Replay archived review evidence without models, author writes or changing old results."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from artifact_fingerprint import sha256_file
from html_design_agent import validate_fidelity, review_target_evidence, retain_unchanged_issues
from pipeline_lifecycle import write_json_atomic


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists(): raise ValueError('OUTPUT_MUST_BE_NEW')
    arms=[]
    for index in (0,1):
        folder=args.archive/str(index)
        request=read(folder/'fidelity/request.json')
        payload=json.loads(request['user_prompt'])
        scene={'nodes':payload['objects']}
        record=read(folder/'fidelity/result.json')
        shot=folder/'candidate.png'
        if sha256_file(shot)!=record['screenshot_sha256']: raise ValueError('SCREENSHOT_CHANGED')
        if record['design_sha256']!=sha256_file(args.archive/'reference.png'): raise ValueError('REFERENCE_CHANGED')
        arms.append({'result':validate_fidelity(read(folder/'fidelity/response.json'),scene),
                     'target_evidence':review_target_evidence(scene,shot,payload)})
    previous,current=arms
    before=json.loads(json.dumps(current['result']))
    retained=retain_unchanged_issues(current['result'],previous,current['target_evidence'])
    write_json_atomic(args.out,{'profile':'review-continuity-replay/0.1.0','model_calls':0,
        'author_writes':0,'source':str(args.archive.resolve()),'before':before,'after':current['result'],
        'retained':retained,'evidence':arms})
    print(json.dumps({'before':before['status'],'after':current['result']['status'],
                      'retained':retained},ensure_ascii=False))


if __name__=='__main__':main()
