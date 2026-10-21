"""Benchmark deterministic relation-endpoint normalization.

Builds frozen variants from the versioned course-structure plans: every object
id gains an ``obj-`` prefix (so slot names no longer equal object ids), then an
endpoint is rewritten to the target slot name exactly as a model may do. The
benchmark reports whether the plan is accepted, whether the compiled scene is
byte-identical to the canonical plan, and whether genuinely unknown endpoint
references stay rejected. Provider-free and read-only.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from html_production_service import compile_plan  # noqa: E402
from html_storyboard_planning import (  # noqa: E402
    HtmlScenePlanError,
    load_template_catalog,
    normalize_html_scene_plan,
)

FIXTURES = ROOT / "checks/fixtures/course-structure-plans.json"
PREFIX = "obj-"


def _rename_refs(value, ids, *, in_coverage=False):
    """Rename object references without touching kind/slot/action vocabulary."""
    if isinstance(value, list):
        return [
            (PREFIX + item if in_coverage and isinstance(item, str) and item in ids
             else _rename_refs(item, ids, in_coverage=in_coverage))
            for item in value
        ]
    if isinstance(value, dict):
        renamed = {}
        for key, item in value.items():
            if key in ("targetId", "labelId") and isinstance(item, str) and item in ids:
                renamed[key] = PREFIX + item
            elif key == "objectId" and isinstance(item, str) and item in ids:
                renamed[key] = PREFIX + item
            else:
                renamed[key] = _rename_refs(item, ids, in_coverage=in_coverage)
        return renamed
    return value


def transform(plan):
    ids = {obj["id"] for obj in plan["objects"]}
    transformed = _rename_refs(copy.deepcopy(plan), ids)
    for obj in transformed["objects"]:
        obj["id"] = PREFIX + obj["id"]
    transformed["visual_coverage"] = _rename_refs(
        plan.get("visual_coverage"), ids, in_coverage=True
    )
    return transformed


def arrow_endpoints(plan):
    """Yield (arrow object, endpoint key, target slot name)."""
    objects = {obj["id"]: obj for obj in plan["objects"]}
    for obj in plan["objects"]:
        if obj["kind"] != "arrow":
            continue
        content = plan["slots"].get(obj["slot"]) or {}
        for key in ("from", "to"):
            endpoint = content.get(key)
            if not isinstance(endpoint, dict):
                continue
            target = objects.get(endpoint.get("objectId"))
            if target:
                yield obj, key, target["slot"]


def rewrite(plan, arrow, key, requested):
    variant = copy.deepcopy(plan)
    variant["slots"][arrow["slot"]][key]["objectId"] = requested
    return variant


def compile_case(plan, contract, catalog):
    normalized = normalize_html_scene_plan(plan, catalog, contract_slide=contract)
    scene, binding = compile_plan(normalized, contract, catalog)
    return normalized, scene, binding


def run_case(case, catalog):
    contract = case["contract"]
    plan = transform(case["plan"])
    try:
        _, canonical_scene, canonical_binding = compile_case(plan, contract, catalog)
    except HtmlScenePlanError as exc:  # cannot benchmark an invalid base
        return {"slide_id": contract["slide_id"], "base_error": exc.code}
    records = {"slide_id": contract["slide_id"], "slot_variants": 0, "slot_accepted": 0,
               "scene_identical": 0, "slot_reject_codes": {}, "unknown_variants": 0,
               "unknown_rejected": 0, "kind_variants": 0, "kind_rejected": 0,
               "resolutions": 0, "base_error": None}
    arrow_slot = next((obj["slot"] for obj in plan["objects"] if obj["kind"] == "arrow"), None)
    seen = set()
    for arrow, key, slot_name in arrow_endpoints(plan):
        signature = (arrow["id"], key)
        if signature in seen:
            continue
        seen.add(signature)
        records["slot_variants"] += 1
        variant = rewrite(plan, arrow, key, slot_name)
        try:
            normalized, scene, binding = compile_case(variant, contract, catalog)
            records["slot_accepted"] += 1
            if scene == canonical_scene and binding == canonical_binding:
                records["scene_identical"] += 1
            receipts = normalized["registered"]
            records["resolutions"] += len(receipts.get("endpoint_resolutions") or [])
        except HtmlScenePlanError as exc:
            records["slot_reject_codes"][exc.code] = records["slot_reject_codes"].get(exc.code, 0) + 1

        records["unknown_variants"] += 1
        try:
            compile_case(rewrite(plan, arrow, key, "missing-object"), contract, catalog)
        except HtmlScenePlanError:
            records["unknown_rejected"] += 1

        if arrow_slot:
            records["kind_variants"] += 1
            try:
                compile_case(rewrite(plan, arrow, key, arrow_slot), contract, catalog)
            except HtmlScenePlanError:
                records["kind_rejected"] += 1
    return records


def metrics(cases):
    usable = [c for c in cases if not c["base_error"]]
    total = lambda key: sum(c[key] for c in usable)  # noqa: E731
    return {
        "pages": len(usable),
        "slot_name_variants": total("slot_variants"),
        "slot_name_accepted": total("slot_accepted"),
        "slot_name_acceptance_rate": (total("slot_accepted") / total("slot_variants"))
        if total("slot_variants") else None,
        "scene_identity_matches": total("scene_identical"),
        "endpoint_resolution_receipts": total("resolutions"),
        "unknown_variants": total("unknown_variants"),
        "unknown_rejected": total("unknown_rejected"),
        "kind_mismatch_variants": total("kind_variants"),
        "kind_mismatch_rejected": total("kind_rejected"),
        "slot_reject_codes": {
            code: sum(c["slot_reject_codes"].get(code, 0) for c in usable)
            for code in {code for c in usable for code in c["slot_reject_codes"]}
        },
        "cases": cases,
        "provider_calls": 0, "author_writes": 0, "approvals": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="disable the normalization in-process to measure the pre-change behaviour",
    )
    args = parser.parse_args(argv)
    if args.baseline:
        import html_storyboard_planning

        html_storyboard_planning._resolve_relation_endpoints = lambda plan: []
    catalog = load_template_catalog(ROOT)
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    result = metrics([run_case(case, catalog) for case in cases])
    result["mode"] = "baseline" if args.baseline else "normalized"
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
