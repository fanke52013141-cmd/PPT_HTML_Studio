"""Initialize/record a four-case external file-mode evaluation. Never calls a provider."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import html_external_evaluation as evaluation  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--source-run", type=Path, required=True)
    prepare.add_argument("--project", required=True)
    prepare.add_argument("--slide", required=True)
    prepare.add_argument("--agent", required=True)
    init = sub.add_parser("init")
    init.add_argument("--spec", type=Path, required=True, help="Host-only four-case JSON; runs must be inside session")
    init.add_argument("--mode", choices=("external_real", "offline_replay"), default="external_real")
    init.add_argument("--agent", required=True, help="Actual external model/tool/session identity, not credentials")
    record = sub.add_parser("record")
    record.add_argument("--case", choices=tuple(evaluation.CASES), required=True)
    record.add_argument("--delivery", type=Path, required=True)
    record.add_argument("--previous-feedback-sha256")
    record.add_argument("--human-interventions", type=int, required=True)
    sub.add_parser("summary")
    args = parser.parse_args()
    if args.action == "prepare":
        result = evaluation.prepare(args.source_run, args.session, args.project, args.slide, agent_identity=args.agent)
    elif args.action == "init":
        result = evaluation.initialize(args.session, json.loads(args.spec.read_text(encoding="utf-8"))["cases"], mode=args.mode, agent_identity=args.agent)
    elif args.action == "record":
        result = evaluation.record(args.session, args.case, args.delivery,
                                   feedback_sha256=args.previous_feedback_sha256, human_interventions=args.human_interventions)
    else:
        result = evaluation.summary(json.loads((args.session / "evaluation.json").read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
