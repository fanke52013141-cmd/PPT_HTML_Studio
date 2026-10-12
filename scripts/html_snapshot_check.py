"""Local snapshot freeze/verification and version-bound QA; no model calls."""
import argparse
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generation = sub.add_parser("freeze-generation")
    generation.add_argument("--run-dir", required=True)
    generation.add_argument("--contract", required=True)
    render = sub.add_parser("freeze-render")
    render.add_argument("--run-dir", required=True)
    render.add_argument("--slide", required=True)
    render.add_argument("--target", choices=["html_preview", "video"], default="html_preview")
    for command in (generation, render):
        command.add_argument("--expected-revision", type=int, required=True)
    for mode in ("verify", "review"):
        p = sub.add_parser(mode)
        p.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    from html_build_snapshot import create_generation_snapshot, create_render_snapshot, verify_snapshot
    try:
        if args.command == "freeze-generation":
            result = create_generation_snapshot(args.run_dir, json.loads(Path(args.contract).read_text(encoding="utf-8-sig")), expected_revision=args.expected_revision)
        elif args.command == "freeze-render":
            result = create_render_snapshot(args.run_dir, args.slide, expected_revision=args.expected_revision, target=args.target)
        elif args.command == "verify":
            result = {"valid": True, "manifest": verify_snapshot(args.snapshot)}
        else:
            from html_snapshot_review import review_snapshot
            result = review_snapshot(args.snapshot)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "review" and result["report"]["checks"]["engineering"] != "passed":
            return 1
        return 0
    except Exception as exc:
        from html_build_snapshot import SnapshotError
        code = str(exc) if isinstance(exc, SnapshotError) and re.fullmatch(r"[A-Z0-9_]+", str(exc)) else "SNAPSHOT_OPERATION_FAILED"
        print(json.dumps({"valid": False, "code": code, "message": "检查输入、版本、资源、字体和快照完整性；原作品未修改"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
