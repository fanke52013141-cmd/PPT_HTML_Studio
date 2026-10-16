"""Run the offline workflow incident checklist; no live provider mode."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "checks/fixtures/html_workflow_evaluation.json"
PROFILE = "offline-contract-regression/0.3.0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_manifest(path=MANIFEST):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["version"] != "0.3.0" or not data["cases"]:
        raise ValueError("INVALID_MANIFEST")
    ids = set()
    for case in data["cases"]:
        if not re.fullmatch(r"WF-\d{3}", case["id"]) or case["id"] in ids:
            raise ValueError("INVALID_CASE_ID")
        ids.add(case["id"])
        if not case["checks"] or set(case["expected"]) != {
            "calls", "reuse", "route", "terminal", "author", "approval"}:
            raise ValueError("INCOMPLETE_CASE")
        for check in case["checks"]:
            if type(check.get("expected_items")) is not int or check["expected_items"] < 1:
                raise ValueError("INVALID_EXPECTED_ITEM_COUNT")
            runner, target = check["runner"], check["target"]
            valid = (runner == "pytest" and re.fullmatch(
                r"checks/test_[a-z0-9_]+\.py::test_[a-z0-9_]+", target))
            valid = valid or (runner == "node" and target in {"checks/test_html_review_panel.cjs", "checks/test_html_labeled_explanation.cjs"})
            if not valid or not (ROOT / target.split("::")[0]).is_file():
                raise ValueError("INVALID_EXECUTOR")
    return data


def read_junit(path):
    """Preserve every parametrized item; skipped/absent items never pass."""
    result = {}
    for item in ET.parse(path).iter("testcase"):
        target = item.attrib.get("classname", "").replace(".", "/") + ".py::" + item.attrib["name"].split("[")[0]
        status = "passed"
        if item.find("failure") is not None or item.find("error") is not None:
            status = "failed"
        elif item.find("skipped") is not None:
            status = "skipped"
        result.setdefault(target, []).append({"name": item.attrib["name"], "status": status,
                                               "elapsed_seconds": float(item.attrib.get("time", 0))})
    return result


def case_result(case, evidence):
    checks = []
    for check in case["checks"]:
        key = check["runner"] + ":" + check["target"]
        items = evidence.get(key, [])
        passed = len(items) == check["expected_items"] and all(item["status"] == "passed" for item in items)
        checks.append({**check, "status": "passed" if passed else "not_passed", "items": items})
    return {**case, "status": "passed" if all(c["status"] == "passed" for c in checks) else "not_passed",
            "checks": checks}


def compare(report, baseline):
    if (baseline.get("profile") != report["profile"] or baseline.get("manifest_sha256") != report["manifest_sha256"]
            or [c["id"] for c in baseline["cases"]] != [c["id"] for c in report["cases"]]):
        raise ValueError("BASELINE_NOT_COMPARABLE")
    previous = {c["id"]: c["status"] for c in baseline["cases"]}
    return {"regressed": [c["id"] for c in report["cases"] if previous[c["id"]] == "passed" and c["status"] != "passed"],
            "recovered": [c["id"] for c in report["cases"] if previous[c["id"]] != "passed" and c["status"] == "passed"],
            "unchanged": [c["id"] for c in report["cases"] if previous[c["id"]] == c["status"]]}


def run_command(command, log, env, timeout):
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as output:
        try:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
        except OSError as error:
            output.write(type(error).__name__)
            return {"exit_code": None, "error": type(error).__name__, "elapsed_seconds": 0}
        try:
            code = process.wait(timeout=timeout)
            error = None
        except subprocess.TimeoutExpired:
            # Terminate the whole tree: Python's venv launcher can have children on Windows.
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
            else:
                process.kill()
            process.wait()
            code, error = process.returncode, "timeout"
    return {"exit_code": code, "error": error, "elapsed_seconds": round(time.monotonic() - started, 3)}


def source_identity():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT)
    try:
        extra = {}
        for name in git("ls-files", "--others", "--exclude-standard").decode().splitlines():
            path = ROOT / name
            if path.suffix in {".py", ".js", ".cjs", ".json", ".md", ".html", ".css"}:
                extra[name] = sha(path.read_bytes())
        return {"head": git("rev-parse", "HEAD").decode().strip(),
                "tracked_diff_sha256": sha(git("diff", "--binary", "HEAD")),
                "untracked_text_sha256": sha(json.dumps(extra, sort_keys=True).encode())}
    except (OSError, subprocess.CalledProcessError):
        return {"head": None, "identity_unavailable": True}


def markdown(report):
    lines = ["# HTML 流程固定案例评估", "", f"结果：{report['status']}；通过 {report['passed_cases']}/{len(report['cases'])} 项。",
             "", "离线契约回归；耗时是测试执行时间，非生产时延。expected 为预期断言，不是观测到的模型用量；usage/cost 未测。", "",
             "| 案例 | 结果 | 调用/复用预期 | 路由/停点预期 | 作者/批准预期 |", "| --- | --- | --- | --- | --- |"]
    for case in report["cases"]:
        e = case["expected"]
        cells = [case["id"] + " " + case["title"], case["status"], e["calls"] + "；" + e["reuse"],
                 e["route"] + "；" + e["terminal"], e["author"] + "；" + e["approval"]]
        lines.append("| " + " | ".join(s.replace("|", "\\|").replace("\n", " ") for s in cells) + " |")
    if report.get("comparison") is not None:
        lines += ["", "与基线比较：`" + json.dumps(report["comparison"], ensure_ascii=False) + "`。不按测试耗时判断模型效率提升。"]
    lines += ["", "执行日志、JUnit 分项和来源散列见同目录 report.json。未收集、跳过或执行器失败均不能通过。"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--list", action="store_true", help="Show cases without running tests")
    args = parser.parse_args(argv)
    manifest = load_manifest()
    if args.list:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    out = args.out.resolve()
    if not out.is_relative_to((ROOT / "outputs").resolve()) or out.exists():
        raise ValueError("OUTPUT_MUST_BE_NEW_DIRECTORY_UNDER_OUTPUTS")
    report = {"version": "0.1.0", "profile": PROFILE, "manifest_sha256": sha(MANIFEST.read_bytes()),
              "started_at": datetime.now(timezone.utc).isoformat(), "source": source_identity(),
              "provider_requests": "not_exercised", "usage": None, "cost": None,
              "cases": manifest["cases"], "executors": {}}
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    if baseline is not None:
        # Reject incompatible case sets before any execution or output creation.
        compare({**report, "cases": [{**c, "status": "not_run"} for c in manifest["cases"]]}, baseline)
    out.mkdir(parents=True)
    evidence = {}
    selectors = sorted({c["target"] for case in manifest["cases"] for c in case["checks"] if c["runner"] == "pytest"})
    with tempfile.TemporaryDirectory(prefix="html-workflow-eval-", ignore_cleanup_errors=True) as isolated:
        env = {**os.environ, "PPT_STUDIO_DB_PATH": str(Path(isolated) / "projects.db"),
               "PPT_STUDIO_RUNS_DIR": str(Path(isolated) / "runs"), "PYTHONIOENCODING": "utf-8",
               "PYTEST_ADDOPTS": "", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
        junit = out / "pytest.xml"
        report["executors"]["pytest"] = run_command(
            [sys.executable, "-m", "pytest", *selectors, "-q", "--junitxml=" + str(junit)], out / "pytest.log", env, 1200)
        if junit.is_file():
            try:
                evidence.update({"pytest:" + key: value for key, value in read_junit(junit).items()})
            except (ET.ParseError, ValueError, KeyError) as error:
                report["executors"]["pytest"]["parse_error"] = type(error).__name__
        for target in sorted({c["target"] for case in manifest["cases"] for c in case["checks"] if c["runner"] == "node"}):
            result = run_command([shutil.which("node") or "node", target], out / (Path(target).stem + ".log"), env, 120)
            report["executors"][target] = result
            evidence["node:" + target] = [{"name": target, "status": "passed" if result["exit_code"] == 0 else "failed",
                                          "elapsed_seconds": result["elapsed_seconds"]}]
    report["cases"] = [case_result(case, evidence) for case in manifest["cases"]]
    report["passed_cases"] = sum(c["status"] == "passed" for c in report["cases"])
    executors_passed = all(r["exit_code"] == 0 and not r.get("parse_error") for r in report["executors"].values())
    report["status"] = "passed" if executors_passed and report["passed_cases"] == len(report["cases"]) else "not_passed"
    report["comparison"] = compare(report, baseline) if baseline is not None else None
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["evidence_sha256"] = {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "report.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "passed_cases": report["passed_cases"], "cases": len(report["cases"]), "report": str(out / "report.md")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
