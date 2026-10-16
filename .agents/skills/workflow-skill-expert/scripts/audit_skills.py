"""Read-only structural inventory, not model-trigger or business quality eval."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import yaml


def inspect(root, registry=None, repo=None):
    root = Path(root).resolve()
    issues, skills = [], []
    paths = sorted(root.glob("*/SKILL.md"))
    if not paths:
        issues.append({"path": str(root), "code": "NO_SKILLS"})
    for path in paths:
        if not path.resolve().is_relative_to(root):
            issues.append({"path": str(path), "code": "PATH_OUTSIDE_ROOT"})
            continue
        raw = path.read_text(encoding="utf-8-sig")
        parts = raw.split("---", 2) if raw.startswith("---") else []
        try:
            header = yaml.safe_load(parts[1]) if len(parts) == 3 else None
        except yaml.YAMLError:
            header = None
        if (not isinstance(header, dict) or header.get("name") != path.parent.name
                or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(header.get("name", "")))
                or not isinstance(header.get("description"), str) or not header["description"].strip()):
            issues.append({"path": str(path), "code": "INVALID_FRONTMATTER"})
        for target in re.findall(r"\]\(([^)]+)\)", raw):
            if re.match(r"(?:https?://|#|mailto:)", target):
                continue
            local = target.split("#", 1)[0]
            if local and not (path.parent / local).is_file():
                issues.append({"path": str(path), "code": "MISSING_REFERENCE", "target": local})
        ui = path.parent / "agents/openai.yaml"
        if ui.exists():
            try:
                doc = yaml.safe_load(ui.read_text(encoding="utf-8"))
                prompt = doc.get("interface", {}).get("default_prompt", "")
                if prompt and f"${path.parent.name}" not in prompt:
                    issues.append({"path": str(ui), "code": "UI_PROMPT_WRONG_SKILL"})
            except (yaml.YAMLError, AttributeError):
                issues.append({"path": str(ui), "code": "INVALID_UI_METADATA"})
        skills.append({"name": path.parent.name, "bytes": len(raw.encode("utf-8")),
                       "lines": len(raw.splitlines()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    runtime = []
    if registry:
        if repo is None:
            raise ValueError("--repo is required with --runtime-registry")
        repo = Path(repo).resolve()
        doc = json.loads(Path(registry).read_text(encoding="utf-8"))
        for skill in doc["skills"]:
            for item in [skill["body"], *skill.get("references", {}).values()]:
                path = (repo / item["path"]).resolve()
                if not path.is_relative_to(repo) or not path.is_file():
                    issues.append({"path": item["path"], "code": "RUNTIME_SOURCE_MISSING"})
                elif hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                    issues.append({"path": item["path"], "code": "RUNTIME_HASH_MISMATCH"})
            runtime.append({"id": skill["id"], "version": skill["version"], "stage": skill["stage"]})
    return {"validation": "structural_only", "skills": skills, "runtime": runtime,
            "issues": issues, "status": "passed" if not issues else "failed"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--runtime-registry", type=Path)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.out and args.out.exists():
        raise ValueError("OUTPUT_EXISTS")
    result = inspect(args.root, args.runtime_registry, args.repo)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as output:
            output.write(text)
    else:
        print(text)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
