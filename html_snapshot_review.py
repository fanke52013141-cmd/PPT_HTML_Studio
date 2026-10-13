"""Independent snapshot checking; author sources and approvals are never written."""
from pathlib import Path
import json
import os
import subprocess
import tempfile

from html_build_snapshot import verify_snapshot, fresh_hash, json_bytes, SnapshotError
from html_quality_report import build_quality_report, validate_quality_report


def review_snapshot(snapshot, *, repo_root=None, output_dir=None, temporal=None):
    root = Path(repo_root or Path(__file__).parent).resolve()
    snapshot = Path(snapshot).resolve()
    manifest = verify_snapshot(snapshot)
    if manifest["kind"] != "render":
        raise SnapshotError("RENDER_SNAPSHOT_REQUIRED")
    base = Path(output_dir).resolve() if output_dir else snapshot.parent / "qa"
    base.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="review-", dir=base))
    dynamic = temporal is not None
    tool = root / "html_engine/tools" / ("review-temporal-snapshot.cjs" if dynamic else "review-snapshot.cjs")
    env = dict(os.environ)
    env.pop("HPS_HTML_RESOURCES", None)
    env.pop("HPS_CANDIDATE_DIAGNOSTIC", None)
    checker = {"version": "snapshot-temporal/0.1.0" if dynamic else "snapshot-static/0.1.0", "tool_sha256": fresh_hash(tool),
               "browser_resolver_sha256": fresh_hash(tool.parent / "browser-runtime.cjs"),
               "runner_sha256": fresh_hash(root / "html_snapshot_review.py"),
               "normalizer_sha256": fresh_hash(root / "html_quality_report.py")}
    if dynamic:
        from html_repair_models import TemporalRequest
        spec = TemporalRequest.model_validate({"expected_revision": manifest["source_revision"], **temporal})
        if spec.expected_revision != manifest["source_revision"]:
            raise SnapshotError("SNAPSHOT_REVISION_CONFLICT")
        request = folder / "temporal-request.json"
        request.write_bytes(json_bytes(spec.model_dump(mode="json")))
        checker["temporal_core_sha256"] = fresh_hash(tool.parent / "temporal-review.cjs")
        checker["overlap_policy_sha256"] = fresh_hash(snapshot / "source/qa-policy.json")
    raw_path = folder / "raw-report.json"
    try:
        command = ["node", str(tool), str(snapshot), *([str(request)] if dynamic else []), str(folder)]
        result = subprocess.run(command, cwd=root,
                                env=env, capture_output=True, timeout=240 if dynamic else 60)
        if not raw_path.is_file():
            raw_path.write_bytes(json_bytes({"passed": False, "code": "SNAPSHOT_CHECK_EXECUTION_FAILED"}))
        elif result.returncode:
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            raw["passed"] = False
            raw_path.write_bytes(json_bytes(raw))
    except (subprocess.TimeoutExpired, OSError):
        raw_path.write_bytes(json_bytes({"passed": False, "code": "SNAPSHOT_CHECK_INTERRUPTED"}))
    # Revalidate after browser use: a changed snapshot cannot receive current QA.
    if verify_snapshot(snapshot)["snapshot_id"] != manifest["snapshot_id"] or fresh_hash(tool) != checker["tool_sha256"] or fresh_hash(tool.parent / "browser-runtime.cjs") != checker["browser_resolver_sha256"] or fresh_hash(root / "html_snapshot_review.py") != checker["runner_sha256"] or fresh_hash(root / "html_quality_report.py") != checker["normalizer_sha256"]:
        raise SnapshotError("SNAPSHOT_OR_CHECKER_CHANGED")
    if dynamic and fresh_hash(tool.parent / "temporal-review.cjs") != checker["temporal_core_sha256"]:
        raise SnapshotError("SNAPSHOT_OR_CHECKER_CHANGED")
    raw = json.loads((folder / "raw-report.json").read_text(encoding="utf-8"))
    checker["browser_version"] = raw.get("browserVersion")
    evidence = [{"path": p.name, "sha256": fresh_hash(p)} for p in sorted(folder.iterdir()) if p.is_file()]
    report = build_quality_report(snapshot, raw, evidence_files=evidence, checker_identity=checker)
    (folder / "quality-report.json").write_bytes(json_bytes(report))
    return {"html": str(snapshot / "preview/index.html"), "report_path": str(folder / "quality-report.json"),
            "report": report, "validation": validate_quality_report(report, snapshot, evidence_dir=folder)}
