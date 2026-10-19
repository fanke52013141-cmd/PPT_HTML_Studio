"""Portable static preflight. Python 3.10+ and Node 20+, no pip/npm/network."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from html_repair_static import apply_static  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()


def preflight(task_path, result_path, checker_path=None):
    root = task_path.parent.resolve()
    task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    checks = []
    def record(name, ok, **details):
        checks.append({"criterion_id": name, "status": "preflight_passed" if ok else "failed", **details})
    encoded = json.dumps({k: v for k, v in task.items() if k != "task_id"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    record("task_identity", task["task_id"] == digest(encoded) == result.get("task_id"))
    for entry in task["files"]:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != entry["sha256"] or path.stat().st_size != entry["size"]:
            record("input_integrity", False, file=entry["path"])
    scene = copy.deepcopy(task["context"].get("scene"))
    if task["task_type"] != "static_repair" or not scene:
        record("portable_task_type", False, message="此预检仅支持静态修复；动画仍需原音频绑定预览")
    if any(c["status"] == "failed" for c in checks):
        return {"format": "hps.html.preflight", "version": "1.0.0", "task_id": task["task_id"], "preflight_passed": False, "checks": checks}
    nodes = {node["id"]: node for node in scene["nodes"]}
    try:
        for operation in result.get("operations", []):
            if operation["targetId"] not in task["scope"]:
                raise ValueError("operation outside scope")
            apply_static(scene, nodes[operation["targetId"]], operation)
        record("scope_and_static_mutation", True)
    except (ValueError, KeyError, TypeError) as exc:
        record("scope_and_static_mutation", False, message=str(exc))
    record("motion_preserved", scene["motion"] == task["context"]["scene"]["motion"])
    for requirement in task["context"].get("execution", {}).get("font_requirements", []):
        value = nodes[requirement["targetId"]].get("presentation", {}).get("typography", {}).get(requirement["part"], {}).get("fontSizePx")
        record(requirement["id"], value is not None and value >= requirement["minimum_px"], actual=value, minimum=requirement["minimum_px"])
    checker = checker_path or root / "tools/preflight.cjs"
    process = subprocess.run(["node", str(checker)], input=json.dumps({"task": task, "result": result, "scene": scene}, ensure_ascii=False),
                             text=True, encoding="utf-8", capture_output=True, timeout=30)
    if process.returncode:
        record("checker_execution", False, message=process.stderr[-2000:])
    else:
        checked = json.loads(process.stdout)
        checks.extend(checked["checks"])
    return {"format": "hps.html.preflight", "version": "1.0.0", "task_id": task["task_id"],
            "result_file_sha256": digest(result_path.read_bytes()),
            "preflight_passed": not any(c["status"] == "failed" for c in checks), "checks": checks,
            "verification_boundary": "Offline structural preflight only; DOM capacity, actual overlap, visuals, audio and author save NOT performed.",
            "not_run": ["original_dom_capacity", "sampled_overlap", "human_visual", "audio", "manual_protection"],
            "saved": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, default=Path("task.json"))
    parser.add_argument("--result", type=Path, default=Path("result.json"))
    parser.add_argument("--out", type=Path, default=Path("preflight.json"))
    args = parser.parse_args()
    if args.task.is_file():
        try:
            task = json.loads(args.task.read_text(encoding="utf-8-sig"))
            inputs = {args.task.resolve(), args.result.resolve(), (args.task.parent / "manifest.json").resolve()}
            inputs.update((args.task.parent / entry["path"]).resolve() for entry in task["files"])
            if args.out.resolve() in inputs:
                parser.error("--out 不得覆盖任务输入、工具、manifest或result.json")
        except (ValueError, KeyError):
            pass
    try:
        report = preflight(args.task, args.result)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        report = {"format": "hps.html.preflight", "version": "1.0.0", "preflight_passed": False,
                  "checks": [{"criterion_id": "preflight_environment", "status": "failed", "message": str(exc)}], "saved": False}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["preflight_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
