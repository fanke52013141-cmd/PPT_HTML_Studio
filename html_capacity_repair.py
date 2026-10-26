"""Deterministic capacity repair: bounded size/typography candidates only.

The original compiler, capacity measurements and temporal QA remain the only
validator. Candidates never change text content, object identity, relations,
motion or manual-protected fields, and never shrink text below a readable floor.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import time
import uuid

import html_scene_editing as editor
import html_scene_repair as repair
from html_candidate_agent import _capacity_size_hint, _geometry_constraints
from html_repair_static import PARTS
from html_visual_review_service import HtmlReviewDependencies, review_scene
from html_visual_store import validate_slide_id
from artifact_fingerprint import sha256_json
from pipeline_lifecycle import write_json_atomic

ROOT = Path(__file__).resolve().parent
VERSION = "capacity-repair/0.1.0"
MIN_READABLE_PX = 24.0
FONT_STEPS = (0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3)
MAX_CANDIDATES = 16


def _layout_for(scene, catalog):
    layout = next(
        (item for item in catalog["layouts"]
         if all(item[key] == scene["layoutRef"][key] for key in ("id", "version"))),
        None,
    )
    if layout is None:
        raise ValueError("未注册的布局版本")
    return layout


def _augment_hint(hint, node, layout, issue):
    """Derive a size hint from CSS text overflow when no canvas box trigger exists."""
    box = layout["slots"][node["slot"]]["box"]
    presentation = node.get("presentation") or {}
    extra = {"width": 0.0, "height": 0.0}
    for trigger in issue.get("triggers", []):
        dimension, actual, limit = trigger.get("dimension"), trigger.get("actual"), trigger.get("limit")
        if not isinstance(actual, (int, float)) or not isinstance(limit, (int, float)):
            continue
        overflow = max(0.0, actual - limit)
        if dimension in ("text_bottom_overflow", "text_top_overflow"):
            extra["height"] = max(extra["height"], overflow)
        elif dimension in ("text_right_overflow", "text_left_overflow"):
            extra["width"] = max(extra["width"], overflow)
    enriched = dict(hint or {})
    for dimension, overflow in extra.items():
        if overflow <= 0 or dimension in enriched:
            continue
        current = presentation.get(dimension, box[dimension])
        enriched[dimension] = {
            "currentOuter": current,
            "currentEffective": current,
            "insets": 0,
            "suggestedOuter": math.ceil(current + overflow + 2),
        }
    return enriched


def _size_values(node, scene, layout, variants, hint, issue):
    constraints = _geometry_constraints(node, scene, layout, variants, hint)
    if not constraints["feasible"]:
        return None
    values = {}
    for dimension in ("width", "height"):
        suggested = (hint or {}).get(dimension, {}).get("suggestedOuter")
        if suggested:
            values[dimension] = suggested
    if not values:
        return None
    suggested = constraints["suggestedPresentation"]
    for key in ("offsetX", "offsetY"):
        if suggested.get(key):
            values[key] = suggested[key]
    return values


def _explicit_fonts(node, issue):
    typography = (node.get("presentation") or {}).get("typography") or {}
    parts = [part for part in PARTS.get(node["type"], []) if part in typography]
    for part in parts:
        current = typography[part].get("fontSizePx")
        if isinstance(current, (int, float)) and current > MIN_READABLE_PX:
            yield part, float(current)
    # A diagnostic font is measured by the renderer, not guessed from a theme.
    measured = (issue.get("typography") or {}).get("fontSizePx")
    target = issue.get("target", "")
    part = issue.get("part") or (target[len(node["id"]) + 1:] if target.startswith(node["id"] + ".") else "")
    if target == node["id"] and len(PARTS.get(node["type"], [])) == 1:
        part = PARTS[node["type"]][0]
    if part in PARTS.get(node["type"], []) and part not in parts:
        if type(measured) in (int, float) and math.isfinite(measured) and measured > MIN_READABLE_PX:
            yield part, float(measured)


def capacity_candidates(scene, layout, diagnostic, catalog, scope):
    """Bounded candidates: grow the box first, then bounded readable type steps."""
    nodes = {node["id"]: node for node in scene["nodes"]}
    variants = (catalog.get("presentationVariants") or {}).get("variants", [])
    issues = diagnostic.get("capacityIssues") or []
    candidates = []
    for issue in issues:
        target = issue.get("target")
        if target not in nodes and isinstance(target, str):
            target = next((key for key in sorted(nodes, key=len, reverse=True)
                           if target.startswith(key + ".")), target)
        if target not in scope or target not in nodes:
            continue
        node = nodes[target]
        if node["type"] == "annotation":
            continue
        hint = _capacity_size_hint(node, layout, [{**issue, "target": target}])
        hint = _augment_hint(hint, node, layout, issue)
        # An explicitly compressed box should first recover its registered
        # content budget instead of repeatedly growing a centred text box by
        # half of the required distance. Motion/canvas bounds still apply.
        for dimension in ("width", "height"):
            registered = layout["slots"][node["slot"]]["box"][dimension]
            current = (node.get("presentation") or {}).get(dimension, registered)
            if dimension in hint and current < registered:
                hint[dimension]["suggestedOuter"] = max(hint[dimension]["suggestedOuter"], registered)
        values = _size_values(node, scene, layout, variants, hint, issue)
        if values:
            candidates.append([{"targetId": target, "kind": "set_presentation",
                                "values": values}])
        for part, current in _explicit_fonts(node, issue):
            # Font-size candidates first: the 16-candidate cap must not crowd
            # out concrete sizes when a node exposes several text parts.
            for step in FONT_STEPS:
                size = round(current * step, 1)
                if size < MIN_READABLE_PX:
                    break
                candidates.append([{"targetId": target, "kind": "set_text_style",
                                    "part": part, "values": {"fontSizePx": size}}])
            current_line_height = ((((node.get("presentation") or {}).get("typography") or {})
                                    .get(part) or {}).get("lineHeight"))
            for line_height in (1.3, 1.2, 1.1, 1.0):
                if current_line_height is not None and line_height >= current_line_height:
                    continue  # Duplicates or loosens the current state.
                candidates.append([{"targetId": target, "kind": "set_text_style",
                                    "part": part, "values": {"lineHeight": line_height}}])
    unique, seen = [], set()
    for operations in candidates:
        signature = json.dumps(operations, sort_keys=True)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(operations)
    # Allocate the bounded list across targets, parts and operation families.
    # A long title's font ladder must not remove every body/line-height option.
    queues = {}
    for operations in unique:
        operation = operations[0]
        family = ('size' if operation['kind'] == 'set_presentation' else
                  'font' if 'fontSizePx' in operation['values'] else 'line_height')
        key = (operation['targetId'], operation.get('part', ''), family)
        queues.setdefault(key, []).append(operations)
    ordered = [queue[index] for index in range(max(map(len, queues.values()), default=0))
               for _, queue in sorted(queues.items()) if index < len(queue)]
    return ordered[:MAX_CANDIDATES]


from html_page_budget import page_budgeted


def net_operations(operations):
    """Merge absolute assignments without changing the original editor guard."""
    merged = {}
    for operation in operations:
        key = (operation['targetId'], operation['kind'], operation.get('part'))
        if key not in merged:
            merged[key] = {**operation, 'values': {}}
        merged[key]['values'].update(operation['values'])
    return list(merged.values())


@page_budgeted
def solve_capacity_candidate(scene, binding, *, run_dir, deps, manual=None, beats=None,
                             checkpoint=lambda: None, progress=lambda value: None,
                             max_states=32, max_depth=4, beam_width=4, max_final_checks=4, budget_seconds=120,
                             allowed_scope=None):
    """Bounded cumulative repair of an unsaved document; never loads its author.

    Intermediate diagnostic states are not saveable. Only a final original
    full-frame review can issue a candidate. This is independent of editor
    revision/audio guards, which remain in the saved-page adapter.
    """
    for value in (max_states, max_depth, beam_width, max_final_checks):
        if type(value) is not int or not 1 <= value <= 64:
            raise ValueError("capacity search limits must be integers in 1..64")
    if type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or not 0 < budget_seconds <= 240:
        raise ValueError("capacity search budget must be in (0,240]")
    validate_slide_id(scene.get("id"))
    if allowed_scope is not None and (not allowed_scope or len(set(allowed_scope))!=len(allowed_scope)
        or set(allowed_scope)-{n['id'] for n in scene['nodes']}):
        raise ValueError('CAPACITY_SCOPE_INVALID')
    run = Path(run_dir)
    audit = run / "planning/html_visual/candidates" / scene["id"] / "capacity-solver" / uuid.uuid4().hex
    audit.mkdir(parents=True)
    started = time.monotonic()
    original = copy.deepcopy({"scene": scene, "binding": binding, "manual": manual,
                              "resources": editor.resources(run), "beats": beats})
    from html_input_manifest import resolved_scene_inputs
    source_inputs = resolved_scene_inputs(scene, run, deps.repo_root)
    catalog = json.loads((deps.repo_root / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    layout = _layout_for(scene, catalog)
    attempts, seen = [], {sha256_json(scene)}
    examined = 0
    final_checks = 0

    def finish(status, reason, candidate=None, report=None):
        checkpoint()
        if (candidate is not None or status in ("candidate", "unchanged")) and (
            {"scene": scene, "binding": binding, "manual": manual, "resources": editor.resources(run), "beats": beats} != original
            or resolved_scene_inputs(scene, run, deps.repo_root) != source_inputs
        ):
            status, reason, candidate = "stale", "CAPACITY_SOURCE_STALE", None
        summary = {"version": "candidate-capacity/0.1.0", "status": status, "reason": reason,
                   "audit": str(audit.relative_to(run)), "measured_states": examined,
                   "model_calls": 0, "provider_calls": 0, "author_writes": 0,
                   "elapsed_seconds": round(time.monotonic() - started, 3),
                   "source_sha256": sha256_json({"document": original, "inputs": source_inputs}),
                   "passed": status in ("candidate", "unchanged") and bool(report and report.get("passed")),
                   "policy": {"max_states": max_states, "max_depth": max_depth, "beam_width": beam_width,
                              "max_final_checks": max_final_checks, "budget_seconds": budget_seconds},
                   "final_checks": final_checks, "attempts": attempts}
        result = {"scene": candidate["scene"] if candidate else original["scene"],
                  "binding": original["binding"], "report": report, "summary": summary}
        write_json_atomic(audit / "result.json", result)
        return result

    def measure(doc, operations, *, final=False):
        nonlocal examined, final_checks
        checkpoint()
        remaining = budget_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return None
        from dataclasses import replace
        def run_bounded(*args, **kwargs):
            left = budget_seconds - (time.monotonic() - started)
            if left <= 0:
                raise TimeoutError("Capacity search budget exhausted")
            kwargs["timeout_sec"] = min(kwargs.get("timeout_sec", left), left)
            return deps.run_subprocess_bounded(*args, **kwargs)
        bounded = replace(deps, stage_timeout_sec=min(deps.stage_timeout_sec, remaining),
                          run_subprocess_bounded=run_bounded)
        folder = audit / f"{examined:03d}{'-final' if final else ''}"
        folder.mkdir()
        if final:
            final_checks += 1
        try:
            report = review_scene(doc["scene"], run_dir=run, deps=bounded,
                                  diagnostic=not final,
                                  **({"preflight_dir": folder / "temporal"} if final else {}))
        except (TimeoutError, ValueError) as error:
            if time.monotonic() - started >= budget_seconds:
                write_json_atomic(folder / "error.json", {"code": "CAPACITY_SEARCH_BUDGET", "message": str(error)[:500]})
                return None
            raise
        examined += 1
        write_json_atomic(folder / "scene.json", doc["scene"])
        write_json_atomic(folder / "report.json", report)
        shot = run / report.get("screenshot", "missing")
        if shot.is_file():
            (folder / "render.png").write_bytes(shot.read_bytes())
        attempts.append({"operations": operations, "final": final,
                         "passed": bool(report.get("passed")),
                         "report": str((folder / "report.json").relative_to(run))})
        progress({"capacity_solver_states": examined, "capacity_solver_max_states": max_states})
        return report

    def targets(report):
        node_ids = {node["id"] for node in scene["nodes"]}
        return sorted({key for issue in report.get("capacityIssues", []) for key in node_ids
                       if issue.get("target") == key or str(issue.get("target", "")).startswith(key + ".")})

    def rank(state):
        issues = state["report"].get("capacityIssues", [])
        excess = sum(max(0, trigger.get("actual", 0) - trigger.get("limit", 0)) /
                     max(abs(trigger.get("limit", 0)), 1)
                     for issue in issues for trigger in issue.get("triggers", [])
                     if all(type(trigger.get(k)) in (int, float) for k in ("actual", "limit")))
        return len(issues), excess, len(state["operations"]), sha256_json(state["doc"]["scene"])

    baseline = measure(original, [])
    if baseline is None:
        return finish("budget_exhausted", "CAPACITY_SEARCH_BUDGET")
    if not baseline.get("capacityIssues"):
        if baseline.get("passed") or baseline.get("geometry"):
            if examined >= max_states:
                return finish("budget_exhausted", "CAPACITY_SEARCH_BUDGET", report=baseline)
            final = measure(original, [], final=True)
            if final and final.get("passed") and final.get("geometry_preflight", {}).get("passed"):
                return finish("unchanged", None, report=final)
            if final and final.get("geometry_preflight", {}).get("issues"):
                return finish("needs_revision", "GEOMETRY_REPAIR_REQUIRED", candidate=original, report=final)
            return finish("blocked" if final else "budget_exhausted", "FINAL_CHECK_INCOMPLETE", report=final)
        return finish("blocked", baseline.get("code", "NO_CAPACITY_ISSUE"), report=baseline)
    scope = targets(baseline)
    if allowed_scope is not None:
        scope=[i for i in scope if i in allowed_scope]
    if not scope or len(scope) > 4:
        return finish("needs_revision", "CAPACITY_SCOPE_REQUIRED", report=baseline)
    frontier = [{"doc": original, "operations": [], "report": baseline}]
    for _ in range(max_depth):
        if examined >= max_states or time.monotonic() - started >= budget_seconds:
            return finish("budget_exhausted", "CAPACITY_SEARCH_BUDGET", report=frontier[0]["report"])
        expanded = []
        for state in frontier:
            # Round-robin targets before spending the bounded measurement budget.
            queues = []
            for target in scope:
                raw = capacity_candidates(state["doc"]["scene"], layout, state["report"], catalog, [target])
                groups = [[ops for ops in raw if ops[0]["kind"] == "set_presentation"],
                          [ops for ops in raw if "fontSizePx" in ops[0]["values"]],
                          [ops for ops in raw if "lineHeight" in ops[0]["values"]]]
                queues.append([group[i] for i in range(max(map(len, groups), default=0))
                               for group in groups if i < len(group)])
            proposals = [queue[index] for index in range(max(map(len, queues), default=0))
                         for queue in queues if index < len(queue)]
            measured_here = 0
            for operations in proposals:
                if measured_here >= 4:
                    break
                checkpoint()
                if examined >= max_states or time.monotonic() - started >= budget_seconds:
                    return finish("budget_exhausted", "CAPACITY_SEARCH_BUDGET", report=state["report"])
                combined = net_operations(state["operations"] + operations)
                if len(combined) > 20:
                    continue
                try:
                    candidate = repair.candidate_from_document(run, scene["id"],
                        {"expected_revision": 0, "source": "ai", "scope": scope, "operations": combined}, original)
                except (editor.SceneEditError, ValueError) as error:
                    attempts.append({"operations": combined, "passed": False,
                                     "code": getattr(error, "code", type(error).__name__), "message": str(error)[:300]})
                    continue
                identity = sha256_json(candidate["scene"])
                if identity in seen:
                    continue
                seen.add(identity)
                measured_here += 1
                doc = {**original, "scene": candidate["scene"]}
                report = measure(doc, combined)
                if report is None:
                    return finish("budget_exhausted", "CAPACITY_SEARCH_BUDGET")
                if not report.get("capacityIssues") and (report.get("passed") or report.get("geometry")):
                    if examined >= max_states or final_checks >= max_final_checks:
                        return finish("budget_exhausted", "CAPACITY_SEARCH_BUDGET", report=report)
                    final = measure(doc, combined, final=True)
                    if final and final.get("passed") and final.get("geometry_preflight", {}).get("passed"):
                        return finish("candidate", None, candidate=doc, report=final)
                    if final and final.get("geometry_preflight", {}).get("issues"):
                        return finish("needs_revision", "GEOMETRY_REPAIR_REQUIRED", candidate=doc, report=final)
                    continue
                if report.get("capacityIssues"):
                    expanded.append({"doc": doc, "operations": combined, "report": report})
        if not expanded:
            return finish("needs_revision", "NO_NEW_VALID_CANDIDATE", report=baseline)
        frontier = sorted(expanded, key=rank)[:beam_width]
    return finish("budget_exhausted", "CAPACITY_SEARCH_DEPTH", report=frontier[0]["report"])


def repair_capacity(run, slide, request, *, scene=None, binding=None, manual=None, beats=None):
    """Read-only deterministic candidate; successful result is an original repair candidate."""
    started = time.monotonic()
    if scene is None:
        doc = repair._revision(run, slide, request["expected_revision"])
    else:
        doc = {"scene": copy.deepcopy(scene), "binding": copy.deepcopy(binding),
               "manual": copy.deepcopy(manual), "resources": editor.resources(run), "beats": beats}
    def source_unchanged():
        if scene is None:
            return editor.load_editor(run, slide) == doc
        return ({"scene": scene, "binding": binding, "manual": manual,
                 "resources": editor.resources(run), "beats": beats} == doc)
    scope = request.get("scope") or []
    nodes = {node["id"]: node for node in doc["scene"]["nodes"]}
    if not scope or len(scope) > 4 or len(set(scope)) != len(scope) or any(s not in nodes for s in scope):
        raise ValueError("Select one to four distinct existing objects")
    audio = request.get("expected_audio_revision") or editor.audio_revision(run, slide)
    deps = HtmlReviewDependencies(ROOT, lambda **kw: {})
    strict = review_scene(doc["scene"], run_dir=run, deps=deps)
    if strict.get("passed"):
        return {"status": "unchanged", "passed": True, "attempts": [], "provider_calls": 0,
                "baseline": strict, "author_unchanged": True,
                "elapsed_seconds": round(time.monotonic() - started, 3)}
    diagnostic = review_scene(doc["scene"], run_dir=run, deps=deps, diagnostic=True)
    if not diagnostic.get("capacityIssues"):
        unchanged = source_unchanged()
        return {"status": "needs_revision", "passed": False, "reason": "NO_CAPACITY_ISSUE",
                "attempts": [], "provider_calls": 0, "baseline": strict, "diagnostic": diagnostic,
                "author_unchanged": unchanged,
                "elapsed_seconds": round(time.monotonic() - started, 3)}
    catalog = json.loads((ROOT / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    layout = _layout_for(doc["scene"], catalog)
    candidates = capacity_candidates(doc["scene"], layout, diagnostic, catalog, scope)
    attempts = []
    for operations in candidates:
        body = {"expected_revision": request["expected_revision"],
                "expected_audio_revision": audio, "operations": operations,
                "scope": scope, "source": "ai"}
        attempt = {"operations": operations}
        attempts.append(attempt)
        try:
            candidate = repair.candidate_from_document(run, slide, body, doc)
            check = review_scene(candidate["scene"], run_dir=run, deps=deps)
            attempt.update(passed=bool(check.get("passed")),
                           message=check.get("message"),
                           issue_count=len(check.get("issues", [])))
            if check.get("passed"):
                unchanged = source_unchanged()
                return {"status": "candidate" if unchanged else "needs_revision",
                        "passed": unchanged, "candidate": {**candidate, "review": check},
                        "request": body, "review": check, "attempts": attempts,
                        "proposed_count": len(candidates), "provider_calls": 0,
                        "author_unchanged": unchanged, "version": VERSION,
                        "elapsed_seconds": round(time.monotonic() - started, 3)}
        except (editor.SceneEditError, ValueError) as exc:
            attempt.update(passed=False, code=getattr(exc, "code", type(exc).__name__),
                           message=str(exc)[:240])
    unchanged = source_unchanged()
    return {"status": "needs_revision", "passed": False, "reason": "NO_DETERMINISTIC_CAPACITY_FIT",
            "candidate": None, "attempts": attempts, "proposed_count": len(candidates),
            "provider_calls": 0, "author_unchanged": unchanged, "version": VERSION,
            "elapsed_seconds": round(time.monotonic() - started, 3)}
