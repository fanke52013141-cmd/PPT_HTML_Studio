"""Score sealed before/after results without provider calls or approval writes."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from html_paired_evaluation import compare,read  # noqa:E402
from pipeline_lifecycle import write_json_atomic  # noqa:E402


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--trials',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=compare(read(a.dataset),read(a.trials),a.root)
    write_json_atomic(a.output,result);print(result['summary'])


if __name__=='__main__':main()
