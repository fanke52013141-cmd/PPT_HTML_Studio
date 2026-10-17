"""Prepare blind human tasks or score explicit human labels; never call a provider."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    build=commands.add_parser('prepare')
    build.add_argument('--case',nargs=3,action='append',required=True,metavar=('CASE_ID','REFERENCE','RECORD'))
    build.add_argument('--out',type=Path,required=True)
    evaluate=commands.add_parser('score')
    evaluate.add_argument('--package',type=Path,required=True)
    evaluate.add_argument('--annotations',type=Path,required=True)
    evaluate.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    from html_text_edge_benchmark import prepare,score
    if args.command=='prepare':
        result=prepare(args.case,args.out)
    else:
        if args.out.exists():raise ValueError('BENCHMARK_OUTPUT_MUST_BE_NEW')
        def read(path):return json.loads(path.read_text(encoding='utf-8'))
        result=score(read(args.package/'package.json'),read(args.annotations),read(args.package/'predictions.json'))
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
