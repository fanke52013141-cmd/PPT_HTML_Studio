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

import html_scene_editing as editor
import html_scene_repair as repair
from html_candidate_agent import _capacity_size_hint, _geometry_constraints
from html_repair_static import PARTS
from html_visual_review_service import HtmlReviewDependencies, review_scene

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


def capacity_candidates(scene, layout, diagnostic, catalog, scope):
    """Bounded candidates: grow the box first, then bounded readable type steps."""
    nodes = {node["id"]: node for node in scene["nodes"]}
    variants = (catalog.get("presentationVariants") or {}).get("variants", [])
    issues = diagnostic.get("capacityIssues") or []
    candidates = []
    for issue in issues:
        target = issue.get("target")
        if target not in scope or target not in nodes:
            continue
        node = nodes[target]
        if node["type"] == "annotation":
            continue
        hint = _capacity_size_hint(node, layout, [issue])
        hint = _augment_hint(hint, node, layout, issue)
        values = _size_values(node, scene, layout, variants, hint, issue)
        if values:
            candidates.append([{"targetId": target, "kind": "set_presentation",
                                "values": values}])
        for part, current in _explicit_fonts(node, issue):
            for line_height in (1.3, 1.2, 1.1, 1.0):
                candidates.append([{"targetId": target, "kind": "set_text_style",
                                    "part": part, "values": {"lineHeight": line_height}}])
            for step in FONT_STEPS:
                size = round(current * step, 1)
                if size < MIN_READABLE_PX:
                    break
                candidates.append([{"targetId": target, "kind": "set_text_style",
                                    "part": part, "values": {"fontSizePx": size}}])
    unique, seen = [], set()
    for operations in candidates:
        signature = json.dumps(operations, sort_keys=True)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(operations)
    return unique[:MAX_CANDIDATES]


def repair_capacity(run, slide, request, *, scene=None, binding=None):
    """Read-only deterministic candidate; successful result is an original repair candidate."""
    started = time.monotonic()
    if scene is None:
        doc = repair._revision(run, slide, request["expected_revision"])
    else:
        doc = {"scene": copy.deepcopy(scene), "binding": copy.deepcopy(binding),
               "manual": None, "resources": editor.resources(run)}
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
        unchanged = editor.load_editor(run, slide) == doc
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
                unchanged = editor.load_editor(run, slide) == doc
                return {"status": "candidate" if unchanged else "needs_revision",
                        "passed": unchanged, "candidate": {**candidate, "review": check},
                        "request": body, "review": check, "attempts": attempts,
                        "proposed_count": len(candidates), "provider_calls": 0,
                        "author_unchanged": unchanged, "version": VERSION,
                        "elapsed_seconds": round(time.monotonic() - started, 3)}
        except (editor.SceneEditError, ValueError) as exc:
            attempt.update(passed=False, code=getattr(exc, "code", type(exc).__name__),
                           message=str(exc)[:240])
    unchanged = editor.load_editor(run, slide) == doc
    return {"status": "needs_revision", "passed": False, "reason": "NO_DETERMINISTIC_CAPACITY_FIT",
            "candidate": None, "attempts": attempts, "proposed_count": len(candidates),
            "provider_calls": 0, "author_unchanged": unchanged, "version": VERSION,
            "elapsed_seconds": round(time.monotonic() - started, 3)}
