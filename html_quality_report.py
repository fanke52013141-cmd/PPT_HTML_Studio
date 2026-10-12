"""Version-bound QA views. Technical pass never grants aesthetic approval."""
from __future__ import annotations

from html_build_snapshot import digest, json_bytes, fresh_hash, safe_file, verify_snapshot, SnapshotError

VERSION = "0.1.0"


def build_quality_report(snapshot, raw, *, evidence_files, checker_identity):
    manifest = verify_snapshot(snapshot)
    issues = []
    for source in raw.get("issues", []) + raw.get("capacityIssues", []):
        issue = {"code": source.get("code", "CAPACITY_ISSUE"),
                 "targets": source.get("targets", [source["nodeId"]] if source.get("nodeId") else []),
                 "time_ms": source.get("timeMs", raw.get("timeMs")), "severity": "ERROR",
                 "part": source.get("part"), "source_path": source.get("path"),
                 "details": source, "allowed_repairs": []}
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
              "scope": {"kind": "static_end_frame", "time_ms": raw.get("timeMs"), "continuous_time_verified": False},
              "issues": issues, "evidence": evidence_files, "approval_granted": False}
    report["report_digest"] = digest(json_bytes(report))
    return report


def validate_quality_report(report, snapshot, *, evidence_dir):
    try:
        manifest = verify_snapshot(snapshot)
        original = dict(report)
        identity = original.pop("report_digest")
        if report.get("format") != "hps.html.quality_report" or report.get("version") != VERSION:
            return {"valid": False, "reason": "report_version"}
        if digest(json_bytes(original)) != identity:
            return {"valid": False, "reason": "report_modified"}
        if report.get("snapshot_id") != manifest["snapshot_id"]:
            return {"valid": False, "reason": "snapshot_changed"}
        evidence_names = {e["path"] for e in report["evidence"]}
        if "raw-report.json" not in evidence_names or (report["checks"]["engineering"] == "passed" and "end-frame.png" not in evidence_names):
            return {"valid": False, "reason": "evidence_missing"}
        for entry in report["evidence"]:
            if fresh_hash(safe_file(evidence_dir, entry["path"])) != entry["sha256"]:
                return {"valid": False, "reason": "evidence_changed"}
        return {"valid": True, "engineering": report["checks"]["engineering"], "approval_granted": False}
    except (SnapshotError, OSError, ValueError, KeyError, TypeError):
        return {"valid": False, "reason": "snapshot_or_report_invalid"}
