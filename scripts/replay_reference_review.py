"""Replay a corrected local workbench using an explicitly supplied review response.

Offline response replay only. Real configured transport can call the shared
html_reference_workbench.resume_review owner; this CLI never contacts providers.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from html_reference_workbench import resume_review  # noqa: E402
from html_visual_review_service import HtmlReviewDependencies  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from artifact_fingerprint import sha256_json  # noqa: E402


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--session',type=Path,required=True,help='Workbench directory')
    parser.add_argument('--correction',type=Path,required=True)
    parser.add_argument('--response',type=Path,required=True,help='ReviewFacts JSON for offline replay')
    args=parser.parse_args()
    response=json.loads(args.response.read_text(encoding='utf-8'))
    result=resume_review(args.session,args.correction,run_dir=args.run_dir,
        deps=HtmlReviewDependencies(ROOT,lambda **kw:response),
        execution_mode='offline_supplied_response', execution_identity=sha256_json(response))
    result={**result,'execution_mode':'offline_supplied_response','real_provider_calls':0}
    write_json_atomic(args.session/'offline-replay.json',result)
    print(json.dumps({'status':result['result']['status'],'mode':result['execution_mode'],'human_approval':'pending'}))


if __name__=='__main__':main()
