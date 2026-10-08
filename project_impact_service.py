"""Project-local, recoverable record of concrete downstream effects."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from impact_registry import IMPACT_RULES
from pipeline_lifecycle import project_artifact_lock, read_json_file, write_json_atomic
from project_storage import safe_child


def _path(run_dir: str | Path) -> Path:
    return safe_child(run_dir, "planning", "pending_impacts.json")


def _normalized_values(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_resolved(item: dict[str, Any]) -> bool:
    return item.get("status") == "resolved"


def _normalized_source_version(source_version: str | None) -> str | None:
    if source_version is None:
        return None
    value = str(source_version).strip()
    return value or None


def _generation(item: Mapping[str, Any]) -> int:
    """Return a stable revision for both current and legacy ledger entries."""
    try:
        return max(0, int(item.get("generation", 0)))
    except (TypeError, ValueError):
        return 0


def _item_scope(item: dict[str, Any]) -> str:
    scope = str(item.get("scope") or "").strip()
    if scope:
        return scope
    rule = IMPACT_RULES.get(str(item.get("reason") or ""))
    return rule.scope if rule is not None else "project"


def list_impacts(
    run_dir: str | Path,
    *,
    include_resolved: bool = False,
) -> list[dict[str, Any]]:
    """Return current pending impacts, optionally including resolved audit records.

    Existing callers keep receiving the actionable list.  Each item's
    ``affected`` list contains only work that remains; fully resolved entries
    stay on disk so an old output can still be explained without becoming a
    permanent task.
    """
    payload = read_json_file(_path(run_dir))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return []
    items = [item for item in payload["items"] if isinstance(item, dict)]
    if include_resolved:
        return items
    return [item for item in items if not _is_resolved(item)]


def snapshot_impacts(
    run_dir: str | Path,
    *,
    affected: Iterable[str],
    slide_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Capture pending effects that a later operation is allowed to settle.

    The snapshot is intentionally small and JSON-serializable so asynchronous
    jobs can keep it with their task metadata.  ``generation`` changes for
    every real unversioned edit and for every new source version.  A completion
    therefore cannot settle a record which was re-registered while it ran.
    """
    requested_affected = set(_normalized_values(affected))
    requested_slide_ids = set(_normalized_values(slide_ids))
    if not requested_affected:
        return []
    snapshots: list[dict[str, Any]] = []
    with project_artifact_lock(run_dir):
        for item in list_impacts(run_dir):
            item_affected = _normalized_values(item.get("affected", ()))
            covered = tuple(value for value in item_affected if value in requested_affected)
            if not covered:
                continue
            scope = _item_scope(item)
            if scope == "slide" and requested_slide_ids:
                if str(item.get("scope_id")) not in requested_slide_ids:
                    continue
            elif scope != "slide" and requested_slide_ids:
                continue
            impact_id = str(item.get("id") or "").strip()
            if not impact_id:
                continue
            snapshots.append({
                "id": impact_id,
                "generation": _generation(item),
                "source_version": _normalized_source_version(item.get("source_version")),
                "affected": list(covered),
            })
    return snapshots


def _normalized_snapshot(
    snapshot: Iterable[Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]] | None:
    if snapshot is None:
        return None
    normalized: dict[str, dict[str, Any]] = {}
    for entry in snapshot:
        if not isinstance(entry, Mapping):
            continue
        impact_id = str(entry.get("id") or "").strip()
        if not impact_id or "generation" not in entry or "source_version" not in entry:
            # A partial caller-built snapshot must fail closed: accepting it
            # could let a later edit be settled by an old job.
            continue
        normalized[impact_id] = {
            "generation": _generation(entry),
            "source_version": _normalized_source_version(entry.get("source_version")),
            "affected": _normalized_values(entry.get("affected", ())),
        }
    return normalized


def record_impact(
    run_dir: str | Path,
    *,
    reason: str,
    slide_ids: Iterable[str] = (),
    source_version: str | None = None,
) -> list[dict[str, Any]]:
    """Record an edit's recoverable downstream effect.

    ``source_version`` is the normalized input version observed by the caller.
    Re-recording the same reason/scope/version is a no-op; recording a newer
    version reopens the one existing record instead of creating a duplicate.
    Legacy callers may omit it until their write paths have a source hash.
    """
    rule = IMPACT_RULES[reason]
    normalized = _normalized_values(slide_ids)
    keys = normalized if rule.scope == "slide" and normalized else ("project",)
    normalized_version = _normalized_source_version(source_version)
    now = _now()
    with project_artifact_lock(run_dir):
        items = list_impacts(run_dir, include_resolved=True)
        changed = False
        for key in keys:
            identity = f"{reason}:{key}"
            existing = next((item for item in items if item.get("id") == identity), None)
            if (existing is not None and normalized_version is not None
                    and existing.get("source_version") == normalized_version):
                # A repeated no-op save must not re-open a reviewed/resolved
                # item or create another notification.
                continue
            if existing is not None:
                existing.update({
                    "source": rule.source,
                    "scope": rule.scope,
                    "all_affected": list(rule.affected),
                    "affected": list(rule.affected),
                    "policy": rule.policy,
                    "source_version": normalized_version,
                    "generation": _generation(existing) + 1,
                    "decision": "defer",
                    "status": "pending",
                    "updated_at": now,
                })
                existing.pop("resolved_at", None)
                existing.pop("resolved_by", None)
                changed = True
                continue
            items.append({
                "id": identity,
                "reason": reason,
                "scope_id": key,
                "scope": rule.scope,
                "source": rule.source,
                "all_affected": list(rule.affected),
                "affected": list(rule.affected),
                "policy": rule.policy,
                "source_version": normalized_version,
                "generation": 1,
                "decision": "defer",
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            })
            changed = True
        if changed:
            write_json_atomic(_path(run_dir), {"version": 3, "items": items})
        return [item for item in items if not _is_resolved(item)]


def resolve_impacts(
    run_dir: str | Path,
    *,
    affected: Iterable[str],
    slide_ids: Iterable[str] = (),
    source_version: str | None = None,
    snapshot: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Settle only the artifact effects covered by a successful operation.

    A page-scoped operation settles matching slide records only.  Project
    records need a project-wide success (no ``slide_ids``), which prevents a
    single regenerated page from clearing a project-wide warning.  Covered
    values are removed from ``affected``; the record becomes resolved only
    when no affected work remains.  When a caller has an input hash,
    ``source_version`` prevents an older job from settling a later edit.
    ``snapshot`` additionally captures the record generation at operation
    start.  Use it for asynchronous work: a new unversioned edit has no source
    hash, but still advances the generation and cannot be settled by that job.
    """
    resolved_affected = set(_normalized_values(affected))
    resolved_slide_ids = set(_normalized_values(slide_ids))
    normalized_version = _normalized_source_version(source_version)
    expected = _normalized_snapshot(snapshot)
    if not resolved_affected:
        return []
    now = _now()
    resolved: list[dict[str, Any]] = []
    with project_artifact_lock(run_dir):
        items = list_impacts(run_dir, include_resolved=True)
        for item in items:
            if _is_resolved(item):
                continue
            snapshot_item = None if expected is None else expected.get(str(item.get("id") or ""))
            if expected is not None:
                if snapshot_item is None:
                    continue
                if _generation(item) != snapshot_item["generation"]:
                    continue
                if _normalized_source_version(item.get("source_version")) != snapshot_item["source_version"]:
                    continue
            item_affected = {
                str(value).strip()
                for value in item.get("affected", [])
                if str(value).strip()
            }
            if not item_affected.intersection(resolved_affected):
                continue
            if normalized_version is not None and _normalized_source_version(item.get("source_version")) != normalized_version:
                continue
            scope = _item_scope(item)
            if scope == "slide" and resolved_slide_ids and str(item.get("scope_id")) not in resolved_slide_ids:
                continue
            if scope != "slide" and resolved_slide_ids:
                continue
            covered = resolved_affected.intersection(item_affected)
            if snapshot_item is not None:
                covered.intersection_update(snapshot_item["affected"])
            if not covered:
                continue
            item["affected"] = [
                value for value in item.get("affected", []) if str(value).strip() not in covered
            ]
            previous_coverage = {
                str(value).strip()
                for value in item.get("resolved_by", [])
                if str(value).strip()
            }
            item["resolved_by"] = sorted(previous_coverage.union(covered))
            if item["affected"]:
                item["status"] = "pending"
                item.pop("resolved_at", None)
            else:
                item["status"] = "resolved"
                item["resolved_at"] = now
            item["updated_at"] = now
            resolved.append(item)
        if resolved:
            write_json_atomic(_path(run_dir), {"version": 3, "items": items})
    return resolved


def set_decision(run_dir: str | Path, impact_id: str, decision: str) -> dict[str, Any] | None:
    if decision not in {"defer", "reviewed"}:
        raise ValueError("Unsupported impact decision")
    with project_artifact_lock(run_dir):
        items = list_impacts(run_dir, include_resolved=True)
        for item in items:
            if item.get("id") == impact_id and not _is_resolved(item):
                item["decision"] = decision
                item["updated_at"] = _now()
                write_json_atomic(_path(run_dir), {"version": 3, "items": items})
                return item
    return None
