"""Pure bounded repair progress decisions. Never authorizes edits or approval."""
from html_build_snapshot import digest, json_bytes


def repair_exit_reason(report, *, rounds, max_rounds, stopped, reason=None):
    if report.get("passed"):
        return None
    if reason:
        return reason
    if stopped:
        return "model_stop"
    if "CONTENT_CAPACITY_EXCEEDED" not in str(report.get("message", "")):
        return "non_capacity_failure"
    return "budget_exhausted" if rounds >= max_rounds else "missing_diagnostic_evidence"


class RepairProgress:
    def __init__(self):
        self.operations = set()
        self.states = set()
        self.diagnostic = None

    def check_operations(self, operations):
        identity = digest(json_bytes(operations))
        if identity in self.operations:
            return "repeated_patch"
        self.operations.add(identity)
        return None

    def observe(self, scene, binding, report):
        state = digest(json_bytes({"scene": scene, "binding": binding}))
        if state in self.states:
            return "repeated_candidate"
        self.states.add(state)
        raw = report.get("diagnostic", report)
        problems = raw.get("capacityIssues", []) + raw.get("issues", [])
        # Compare actual measurements under the same checker; don't mistake
        # unchanged issue IDs for failure when overflow is getting smaller.
        facts = [{k: problem[k] for k in ("code", "target", "targets", "part", "timeMs", "available", "measured") if k in problem}
                 for problem in problems]
        identity = digest(json_bytes(sorted(facts, key=lambda p: json_bytes(p)))) if facts else None
        reason = "unchanged_measurements" if identity is not None and identity == self.diagnostic else None
        self.diagnostic = identity
        return reason
