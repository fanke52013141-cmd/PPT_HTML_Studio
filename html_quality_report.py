"""Version-bound QA views. Technical pass never grants aesthetic approval."""
from __future__ import annotations
import json
import subprocess

from html_build_snapshot import digest, json_bytes, fresh_hash, safe_file, verify_snapshot, SnapshotError

VERSION = "0.2.0"


def build_quality_report(snapshot, raw, *, evidence_files, checker_identity):
    manifest = verify_snapshot(snapshot)
    issues = []
    for source in raw.get("issues", []) + raw.get("capacityIssues", []):
        issue = {"code": source.get("code", "CAPACITY_ISSUE"),
                 "targets": source.get("targets", [source.get("nodeId", source.get("target"))] if source.get("nodeId", source.get("target")) else []),
                 "time_ms": source.get("timeMs", raw.get("timeMs")), "severity": "ERROR",
                 "part": source.get("part"), "source_path": source.get("path"),
                 "details": source, "allowed_repairs": source.get("allowed_repairs", [])}
        # No implicit mutation authorization; the editor's scope decides repairs.
        issue["issue_id"] = digest(json_bytes(issue))[:20]
        issues.append(issue)
    if raw.get("pageErrors") or raw.get("code"):
        detail = {"code": raw.get("code", "PAGE_ERROR"), "severity": "BLOCKER", "targets": [],
                  "time_ms": None, "details": {"pageErrors": raw.get("pageErrors", [])}, "allowed_repairs": []}
        detail["issue_id"] = digest(json_bytes(detail))[:20]
        issues.append(detail)
    if raw.get("passed") is False and not issues:
        detail = {"code": "CHECK_FAILED", "severity": "BLOCKER", "targets": [],
                  "time_ms": None, "details": {}, "allowed_repairs": []}
        detail["issue_id"] = digest(json_bytes(detail))[:20]
        issues.append(detail)
    status = "passed" if raw.get("passed") is True and not issues and not raw.get("diagnosticOnly") else "failed"
    report = {"format": "hps.html.quality_report", "version": VERSION,
              "snapshot_id": manifest["snapshot_id"], "source_revision": manifest["source_revision"],
              "scene_digest": manifest.get("scene_digest"), "checker": checker_identity,
              "checks": {"engineering": status, "visual": "pending_review", "audio": "not_tested", "export": "not_tested"},
              "scope": {"kind": "temporal_execution_failure" if checker_identity.get("version", "").startswith("snapshot-temporal/") else "static_end_frame", "time_ms": raw.get("timeMs"), "continuous_time_verified": False},
              "issues": issues, "evidence": evidence_files, "approval_granted": False}
    if raw.get("coverage"):
        report["scope"] = {"kind": "temporal", "clock": raw.get("clock"),
                           "coverage": {k: v for k, v in raw["coverage"].items() if k != "times"},
                           "frame_count": len(raw.get("frames", [])), "continuous_time_verified": False,
                           "overlap_scope": raw.get("overlapScope"), "overlap_exclusions": raw.get("overlapExclusions", [])}
    report["report_digest"] = digest(json_bytes(report))
    return report


def validate_quality_report(report, snapshot, *, evidence_dir):
    try:
        manifest = verify_snapshot(snapshot)
        original = dict(report)
        identity = original.pop("report_digest")
        if report.get("format") != "hps.html.quality_report" or report.get("version") not in {"0.1.0", VERSION}:
            return {"valid": False, "reason": "report_version"}
        if digest(json_bytes(original)) != identity:
            return {"valid": False, "reason": "report_modified"}
        if report.get("snapshot_id") != manifest["snapshot_id"]:
            return {"valid": False, "reason": "snapshot_changed"}
        evidence_names = {e["path"] for e in report["evidence"]}
        dynamic = report.get("scope", {}).get("kind") == "temporal"
        if dynamic and "temporal-request.json" not in evidence_names:
            return {"valid": False, "reason": "evidence_missing"}
        has_image = any(name.startswith("frame-") and name.endswith(".png") for name in evidence_names) if dynamic else "end-frame.png" in evidence_names
        if "raw-report.json" not in evidence_names or (report["checks"]["engineering"] == "passed" and not has_image):
            return {"valid": False, "reason": "evidence_missing"}
        for entry in report["evidence"]:
            if fresh_hash(safe_file(evidence_dir, entry["path"])) != entry["sha256"]:
                return {"valid": False, "reason": "evidence_changed"}
        raw = json.loads(safe_file(evidence_dir, "raw-report.json").read_text(encoding="utf-8"))
        if bool(raw.get("coverage")) != dynamic:
            return {"valid": False, "reason": "scope_changed"}
        if not dynamic and report["checker"].get("version", "").startswith("snapshot-temporal/") and report.get("scope", {}).get("kind") != "temporal_execution_failure":
            return {"valid": False, "reason": "scope_changed"}
        if report["checks"]["engineering"] == "passed" and (not raw.get("passed") or raw.get("issues") or raw.get("capacityIssues") or raw.get("pageErrors")):
            return {"valid": False, "reason": "raw_check_failed"}
        if dynamic:
            from pathlib import Path
            coverage = raw["coverage"]
            root = Path(__file__).resolve().parent
            core = root / "html_engine/tools/temporal-review.cjs"
            if report["checker"].get("temporal_core_sha256") != fresh_hash(core):
                return {"valid": False, "reason": "checker_changed"}
            if report["checker"].get("vector_overlap_sha256") != fresh_hash(root / "html_engine/tools/vector-overlap.cjs"):
                return {"valid": False, "reason": "checker_changed"}
            from html_repair_models import TemporalRequest
            request = TemporalRequest.model_validate(json.loads(safe_file(evidence_dir, "temporal-request.json").read_text(encoding="utf-8")))
            if request.expected_revision != manifest["source_revision"]:
                return {"valid": False, "reason": "request_revision_changed"}
            scene = json.loads(safe_file(snapshot, "input/scene.json").read_text(encoding="utf-8"))
            policy = json.loads(safe_file(snapshot, "source/qa-policy.json").read_text(encoding="utf-8"))
            code = "const fs=require('fs'),c=require(process.argv[1]),p=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify({coverage:c.timeCoverage(p.scene,p.spec),policy:c.overlapPolicy(p.scene,p.spec,p.policy)}));"
            result = subprocess.run(["node", "-e", code, str(core)], input=json_bytes({"scene": scene, "spec": request.model_dump(mode="json"), "policy": policy}),
                                    cwd=root, capture_output=True, timeout=15, check=True)
            expected = json.loads(result.stdout)
            if coverage != expected["coverage"] or raw.get("clock") != manifest["clock"] or raw.get("overlapPairs") != expected["policy"]["pairs"] or raw.get("overlapExclusions") != expected["policy"]["exclusions"] or raw.get("overlapScope") != expected["policy"]["scope"]:
                return {"valid": False, "reason": "request_coverage_changed"}
            if report["scope"]["coverage"] != {k: v for k, v in coverage.items() if k != "times"} or report["scope"]["frame_count"] != len(raw["frames"]):
                return {"valid": False, "reason": "coverage_changed"}
            if report["scope"].get("clock") != raw.get("clock") or report["scope"].get("overlap_scope") != raw.get("overlapScope") or report["scope"].get("overlap_exclusions") != raw.get("overlapExclusions") or report["scope"].get("continuous_time_verified") is not False:
                return {"valid": False, "reason": "scope_changed"}
            times = [frame["timeMs"] for frame in raw["frames"]]
            if times != coverage["times"]:
                return {"valid": False, "reason": "coverage_missing"}
        return {"valid": True, "engineering": report["checks"]["engineering"], "approval_granted": False}
    except (SnapshotError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {"valid": False, "reason": "snapshot_or_report_invalid"}
