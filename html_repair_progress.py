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
        facts = []
        for problem in problems:
            # Saved-page quality reports retain raw checker evidence in details.
            source = {**(problem.get("details") or {}), **problem}
            fact = {k: source[k] for k in ("code", "target", "targets", "part", "timeMs", "time_ms", "available", "measured", "effectiveLimits") if k in source}
            if "triggers" in source:
                # Line count / range overflow can improve without changing the
                # integer DOM box. Ignore prose and ordering, retain predicates.
                triggers = [{k: trigger[k] for k in ("dimension", "actual", "limit", "tolerance", "unit") if k in trigger}
                            for trigger in source["triggers"]]
                fact["triggers"] = sorted(triggers, key=json_bytes)
            facts.append(fact)
        identity = digest(json_bytes(sorted(facts, key=lambda p: json_bytes(p)))) if facts else None
        reason = "unchanged_measurements" if identity is not None and identity == self.diagnostic else None
        self.diagnostic = identity
        return reason
