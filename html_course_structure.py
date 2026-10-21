"""Pure, explicit plan coverage checks before design/provider allocation.

No NLP inference: required capabilities come from an authored contract manifest.
"""

import json
import math
from pathlib import Path

from html_semantic_plan import SemanticPlanError


def _validate_node(content, obj, code):
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (Path(__file__).parent / "html_engine/visual/schema.json").read_text(
            encoding="utf-8"
        )
    )
    rule = next(
        n
        for n in schema["$defs"]["node"]["oneOf"]
        if n["properties"]["type"]["const"] == obj["kind"]
    )
    node = {k: v for k, v in content.items() if k != "kind"}
    node.update(id=obj["id"], slot=obj["slot"], type=obj["kind"])
    if not Draft202012Validator({"$defs": schema["$defs"], **rule}).is_valid(node):
        raise SemanticPlanError(code, obj["id"])


def validate_course_structure(plan, contract, template):
    def fail(code, message):
        raise SemanticPlanError(code, message)

    objects = {o["id"]: o for o in plan["objects"]}
    slots = plan["slots"]
    relation_ids = set()
    for obj in objects.values():
        content = slots[obj["slot"]]
        if obj["kind"] == "chart":
            _validate_node(content, obj, "PLAN_CHART_INVALID")
            points = content["points"]
            if (
                not all(math.isfinite(p[k]) for p in points for k in ("x", "y"))
                or not all(math.isfinite(content[k]) for k in ("min", "max"))
                or content["max"] <= content["min"]
                or any(p["x"] <= points[i - 1]["x"] for i, p in enumerate(points) if i)
            ):
                fail("PLAN_CHART_INVALID", obj["id"])
            if "plateau" in content:
                a, b = content["plateau"]
                if (
                    a >= b
                    or b >= len(points)
                    or any(p["y"] != points[a]["y"] for p in points[a : b + 1])
                ):
                    fail("PLAN_CHART_PLATEAU", obj["id"])
        if obj["kind"] != "arrow":
            continue
        if (
            template.get("relationPolicy") == "explicit"
            or "from" in content
            or "to" in content
        ):
            if "presentation" in content:
                fail("PLAN_RELATION_GEOMETRY", obj["id"])
            _validate_node(content, obj, "PLAN_RELATION_ENDPOINT")
            for key in ("from", "to"):
                endpoint = content.get(key, {})
                if not isinstance(endpoint, dict) or not isinstance(
                    endpoint.get("objectId"), str
                ):
                    fail("PLAN_RELATION_ENDPOINT", obj["id"])
                target = objects.get(endpoint.get("objectId"))
                if not target or target["kind"] in ("arrow", "annotation"):
                    eligible = {
                        i: o for i, o in objects.items()
                        if o["kind"] not in ("arrow", "annotation")
                    }
                    fail("PLAN_RELATION_ENDPOINT", json.dumps({
                        "path": ["slots", obj["slot"], key, "objectId"],
                        "reason": "endpoint_must_reference_object_id",
                        "actual": endpoint["objectId"],
                        "allowed_object_ids": sorted(eligible),
                        "matching_slot_object_ids": sorted(
                            i for i, o in eligible.items()
                            if o["slot"] == endpoint["objectId"]
                        ),
                        "instruction": "引用objects[].id，不能用槽位名、素材ID或关系对象代替；仅提示，不自动改写端点。",
                    }, ensure_ascii=False))
                if set(endpoint) == {"objectId", "anchorId"}:
                    target_content = slots[target["slot"]]
                    if target["kind"] != "image" or endpoint[
                        "anchorId"
                    ] != target_content.get("anchorId", "focus"):
                        fail("PLAN_RELATION_ENDPOINT", obj["id"])
                elif set(endpoint) == {"objectId", "point"}:
                    point = endpoint["point"]
                    if (
                        not isinstance(point, dict)
                        or set(point) != {"x", "y"}
                        or any(
                            type(v) not in (int, float)
                            or not math.isfinite(v)
                            or not 0 <= v <= 1
                            for v in point.values()
                        )
                    ):
                        fail("PLAN_RELATION_ENDPOINT", obj["id"])
                else:
                    fail("PLAN_RELATION_ENDPOINT", obj["id"])
            if content["from"] == content["to"]:
                fail("PLAN_RELATION_ENDPOINT", obj["id"])
            for beat in plan.get("beats", []):
                if any(
                    a.get("objectId") == obj["id"] and a.get("type") != "enter"
                    for a in beat.get("actions", [])
                ):
                    fail("PLAN_RELATION_ACTION", obj["id"])
            relation_ids.add(obj["id"])
    requirements = contract.get("visual_requirements", [])
    coverage = plan.get("visual_coverage", {})
    if (
        not isinstance(requirements, list)
        or not isinstance(coverage, dict)
        or any(
            not isinstance(r, dict)
            or not isinstance(r.get("id"), str)
            or not r["id"].strip()
            for r in requirements
        )
    ):
        fail("PLAN_VISUAL_REQUIREMENTS", "Explicit manifest required")
    required_ids = {r["id"] for r in requirements}
    if len(required_ids) != len(requirements) or set(coverage) != required_ids:
        fail(
            "PLAN_VISUAL_COVERAGE",
            json.dumps({
                "path": ["visual_coverage"],
                "reason": "coverage_keys_must_match_authored_requirements",
                "required_ids": sorted(required_ids),
                "missing_ids": sorted(required_ids - set(coverage)),
                "unexpected_ids": sorted(set(coverage) - required_ids, key=str),
                "duplicate_requirement_ids": sorted(
                    i for i in required_ids
                    if sum(r["id"] == i for r in requirements) > 1
                ),
                "instruction": "键只能来自权威visual_requirements[].id，不能取visual_groups/语块/对象/槽位ID；需求缺省或为空时仅允许省略visual_coverage或返回{}。",
            }, ensure_ascii=False),
        )
    for req in requirements:
        ids = coverage[req["id"]]
        if (
            req.get("kind") not in ("relation", "chart", "stage")
            or type(req.get("minCount")) is not int
            or req["minCount"] < 1
            or not isinstance(ids, list)
            or any(not isinstance(i, str) for i in ids)
            or len(ids) != len(set(ids))
            or len(ids) < req["minCount"]
            or any(i not in objects for i in ids)
        ):
            fail("PLAN_VISUAL_COVERAGE", json.dumps({
                "path": ["visual_coverage", req["id"]],
                "reason": "coverage_requires_unique_existing_object_ids_and_min_count",
                "requirement": req,
                "actual": ids,
                "allowed_object_ids": sorted(objects),
            }, ensure_ascii=False))
        allowed = (
            relation_ids
            if req["kind"] == "relation"
            else {
                i
                for i, o in objects.items()
                if o["kind"] == ("chart" if req["kind"] == "chart" else "card")
            }
        )
        if not set(ids) <= allowed:
            fail("PLAN_VISUAL_COVERAGE", json.dumps({
                "path": ["visual_coverage", req["id"]],
                "reason": "coverage_object_kind_mismatch",
                "requirement": req,
                "actual": ids,
                "allowed_object_ids": sorted(allowed),
            }, ensure_ascii=False))
    return {
        "requirements": len(requirements),
        "mapped": len(coverage),
        "meaning": "pending_semantic_review",
    }
