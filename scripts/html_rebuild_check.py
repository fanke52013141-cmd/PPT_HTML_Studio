"""S03 read-only capture / dry-run; never starts a server or runs a model."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from html_rebuild_inputs import capture_inputs
from html_rebuild_plan import plan_rebuild


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    capture = modes.add_parser("capture")
    capture.add_argument("--run-dir", required=True)
    compare = modes.add_parser("plan")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    args = parser.parse_args()
    try:
        result = capture_inputs(args.run_dir) if args.mode == "capture" else plan_rebuild(
            json.loads(Path(args.before).read_text(encoding="utf-8-sig")),
            json.loads(Path(args.after).read_text(encoding="utf-8-sig")),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({"error": "REBUILD_INPUT_INVALID"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
