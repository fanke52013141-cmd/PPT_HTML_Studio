"""Capture/verify Git source bytes without reading runtime data or credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def capture(excluded):
    names = set(git("ls-files", "-z").decode("utf-8").split("\0")) - {""}
    # New source/documents are explicit; never enumerate ignored runtime trees.
    for name in git("ls-files", "--others", "--exclude-standard", "-z").decode("utf-8").split("\0"):
        if name.startswith(("docs/", "checks/", "scripts/", ".agents/")):
            names.add(name)
    entries = []
    for name in sorted(names):
        if name == excluded:
            continue
        if name.split("/", 1)[0] in {"data", "runs", "outputs", "logs"}:
            if name.endswith("/.gitkeep"):
                continue
            raise ValueError("RUNTIME_DATA_IN_GIT_BASELINE")
        path = ROOT / name
        entries.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
                        if path.is_file() else None})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"format": "html-studio.source-baseline/0.1.0",
            "parent_commit": git("rev-parse", "HEAD").decode().strip(),
            "identity": hashlib.sha256(payload).hexdigest(), "files": entries,
            "scope": "working-tree bytes; not a source archive or remote commit"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    target = args.path.resolve()
    relative = target.relative_to(ROOT).as_posix()
    current = capture(relative)
    if args.verify:
        expected = json.loads(target.read_text(encoding="utf-8"))
        if expected["identity"] != current["identity"] or expected["files"] != current["files"]:
            print("SOURCE_BASELINE_CHANGED")
            return 1
        print("SOURCE_BASELINE_MATCHED " + current["identity"])
        return 0
    if target.exists():
        raise ValueError("BASELINE_ALREADY_EXISTS")
    target.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(current["identity"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
