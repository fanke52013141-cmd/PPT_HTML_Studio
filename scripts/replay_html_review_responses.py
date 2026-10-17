"""Revalidate saved first-review JSON locally; no provider call or task rewrite."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(path):
    return Path(path).read_text(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('REPLAY_OUTPUT_MUST_BE_NEW')
    args.out.mkdir(parents=True)
    os.environ['PPT_STUDIO_DB_PATH'] = str(args.out.resolve()/'isolated.db')
    os.environ['PPT_STUDIO_RUNS_DIR'] = str(args.out.resolve()/'runs')
    from artifact_fingerprint import sha256_file
    from pipeline_lifecycle import write_json_atomic
    from html_design_agent import validate_fidelity
    from html_runtime_skills import load_runtime_skill
    experiment = args.experiment.resolve()
    manifest = json.loads(read(experiment/'manifest.json'))
    known = {c['name']:set(c['known_typography_targets']) for c in manifest['cases']}
    rows = []
    for trial in json.loads(read(experiment/'trials.json')):
        if trial['arm'] != 'after':
            continue
        folder = experiment/f"{trial['case']}-after-{trial['repetition']}"/'review'
        if not (folder/'response.json').is_file():
            rows.append({'state':'not_returned', 'case':trial['case'], 'repetition':trial['repetition']})
            continue
        payload = json.loads(json.loads(read(folder/'request.json'))['user_prompt'])
        row = {'case':trial['case'], 'repetition':trial['repetition'], 'original_state':trial['state'],
               'response_sha256':sha256_file(folder/'response.json'),
               'request_sha256':sha256_file(folder/'request.json')}
        try:
            result = validate_fidelity(json.loads(read(folder/'response.json')),
                {'nodes':payload['objects']}, require_coverage=True, alignment=payload.get('text_alignment_contract'))
            found = {i['targetId'] for i in result['issues'] if i['requirement']=='typography'} & known[trial['case']]
            row.update(state='valid', known_found=sorted(found), all_known_found=found==known[trial['case']], result=result)
        except ValueError as error:
            row.update(state='rejected', error=str(error)[:1200], known_found=[], all_known_found=False)
        rows.append(row)
    record = {'kind':'offline_saved_response_replay', 'model_calls':0, 'author_writes':0,
              'runtime_skill':load_runtime_skill(ROOT,stage='design_fidelity_review').identity,
              'validator_source_sha256':sha256_file(ROOT/'html_design_agent.py'),
              'rows':rows, 'valid':sum(r['state']=='valid' for r in rows),
              'known_found':sum(len(r.get('known_found',[])) for r in rows),
              'known_expected':sum(len(known[r['case']]) for r in rows),
              'all_known_found_trials':sum(r.get('all_known_found',False) for r in rows),
              'limit':'Saved 0.9.0 model outputs under the new parser; not new model or end-to-end production validation'}
    write_json_atomic(args.out/'replay.json', record)
    print(json.dumps({k:v for k,v in record.items() if k not in ('rows','runtime_skill')},ensure_ascii=False))


if __name__ == '__main__':
    main()
