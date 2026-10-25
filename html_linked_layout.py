"""Unsaved linked layout and declared endpoint routing over original QA."""
from __future__ import annotations

import copy
from dataclasses import replace
import json
import math
from pathlib import Path
import time
import uuid

from artifact_fingerprint import sha256_file, sha256_json
from html_capacity_repair import solve_capacity_candidate, _layout_for
from html_geometry_repair import propose_endpoint_routes
import html_scene_editing as editor
from html_scene_repair import candidate_from_document
from html_visual_review_service import review_scene, HtmlReviewError
from pipeline_lifecycle import write_json_atomic
from html_page_budget import page_budgeted
from html_layout_groups import registered_row_candidates


def linked_layout_candidates(scene, layout, affected):
    """Pack a registered vertical card column plus its summary, at most 4 IDs.

    Original slots establish order/column membership. Only position changes;
    the original compiler, protected-field guard and full QA judge the result.
    """
    boxes = {n['id']: layout['slots'][n['slot']]['box'] for n in scene['nodes']}
    cards = sorted((n for n in scene['nodes'] if n['type'] == 'card'),
                   key=lambda n: (boxes[n['id']]['y'], n['id']))
    if not 2 <= len(cards) <= 3 or not affected.intersection(n['id'] for n in cards):
        return []
    first = boxes[cards[0]['id']]
    for previous, current in zip(cards, cards[1:]):
        a, b = boxes[previous['id']], boxes[current['id']]
        if abs(b['x'] - first['x']) > 1 or abs(b['width'] - first['width']) > 1 or b['y'] < a['y'] + a['height']:
            return []
    summaries = [n for n in scene['nodes'] if n['type'] == 'summary'
                 and boxes[n['id']]['y'] >= boxes[cards[-1]['id']]['y'] + boxes[cards[-1]['id']]['height']]
    rows = cards + sorted(summaries, key=lambda n: (boxes[n['id']]['y'], n['id']))[:1]
    operations = []
    previous_end = None
    for i, node in enumerate(rows):
        box, p = boxes[node['id']], node.get('presentation', {})
        y = box['y'] + p.get('offsetY', 0)
        if previous_end is not None:
            old = boxes[rows[i - 1]['id']]
            gap = max(8, min(16, box['y'] - old['y'] - old['height']))
            y = max(y, previous_end + gap)
        height = p.get('height', box['height'])
        if y < 0 or y + height > 800 or abs(y - box['y']) > 400:
            return []
        if y != box['y'] + p.get('offsetY', 0):
            operations.append({'targetId': node['id'], 'kind': 'set_presentation',
                               'values': {'offsetY': round(y - box['y'], 3)}})
        previous_end = y + height
    return [operations] if operations else []


@page_budgeted
def solve_production_layout(scene, binding, *, run_dir, deps, manual=None, beats=None,
                            checkpoint=lambda: None, progress=lambda value: None,
                            max_geometry_checks=8, geometry_budget_seconds=120, allowed_scope=None):
    if type(max_geometry_checks) is not int or not 1 <= max_geometry_checks <= 16:
        raise ValueError('Geometry checks must be in 1..16')
    if type(geometry_budget_seconds) not in (int, float) or not math.isfinite(geometry_budget_seconds) or not 0 < geometry_budget_seconds <= 240:
        raise ValueError('Geometry budget must be in (0,240]')
    capacity = solve_capacity_candidate(scene, binding, run_dir=run_dir, deps=deps, manual=manual,
                                        beats=beats, checkpoint=checkpoint, progress=progress, allowed_scope=allowed_scope)
    if capacity['summary']['reason'] != 'GEOMETRY_REPAIR_REQUIRED':
        return capacity
    run = Path(run_dir).resolve()
    audit = run / 'planning/html_visual/candidates' / scene['id'] / 'linked-layout' / uuid.uuid4().hex
    audit.mkdir(parents=True)
    original = copy.deepcopy({'scene': scene, 'binding': binding, 'manual': manual,
                              'resources': editor.resources(run), 'beats': beats})
    from html_input_manifest import resolved_scene_inputs
    source_identity = resolved_scene_inputs(scene, run, deps.repo_root)
    catalog = json.loads((deps.repo_root / 'html_engine/visual/generated/catalog.json').read_text(encoding='utf-8'))
    layout = _layout_for(scene, catalog)
    current, report = capacity['scene'], capacity['report']
    attempts, seen = [], {sha256_json(current)}
    checks, started = 0, time.monotonic()
    status, reason = 'needs_revision', 'NO_LINKED_LAYOUT_WITHIN_POLICY'
    while checks < max_geometry_checks and time.monotonic() - started < geometry_budget_seconds:
        checkpoint()
        preflight = report.get('geometry_preflight', {})
        affected = {target for issue in preflight.get('issues', []) for target in issue.get('targets', [])}
        proposals = linked_layout_candidates(current, layout, affected) + registered_row_candidates(current, layout, affected)
        raw_dir = (run / preflight.get('audit', '')).resolve()
        raw_path = raw_dir / 'report.json'
        if not raw_dir.is_relative_to(run) or not raw_path.is_file() or sha256_file(raw_path) != preflight.get('raw_report_sha256'):
            raise HtmlReviewError('关系修复缺少当前完整动态证据', code='LINKED_LAYOUT_EVIDENCE_INVALID')
        raw = json.loads(raw_path.read_text(encoding='utf-8'))
        arrows = sorted(n['id'] for n in current['nodes'] if n['type'] == 'arrow' and n['id'] in affected)
        if len(arrows) <= 4:
            proposals += [p['operations'] for p in propose_endpoint_routes(
                {**original, 'scene': current}, arrows, raw, raw.get('frames', []))]
        improved = False
        for operations in proposals:
            checkpoint()
            remaining = geometry_budget_seconds - (time.monotonic() - started)
            if checks >= max_geometry_checks or remaining <= 0:
                break
            scope = sorted({op['targetId'] for op in operations})
            if len(scope) > 4:
                continue
            if allowed_scope is not None and set(scope)-set(allowed_scope):
                continue
            try:
                candidate = candidate_from_document(run, scene['id'],
                    {'expected_revision': 0, 'source': 'ai', 'scope': scope, 'operations': operations},
                    {**original, 'scene': current})
            except (editor.SceneEditError, ValueError) as error:
                attempts.append({'operations': operations, 'code': getattr(error, 'code', type(error).__name__)})
                continue
            identity = sha256_json(candidate['scene'])
            if identity in seen:
                continue
            seen.add(identity)
            folder = audit / str(checks)
            checks += 1
            def bounded_runner(*args, **kwargs):
                left = geometry_budget_seconds - (time.monotonic() - started)
                if left <= 0:
                    raise TimeoutError('Linked layout budget exhausted')
                kwargs['timeout_sec'] = min(kwargs.get('timeout_sec', left), left)
                return deps.run_subprocess_bounded(*args, **kwargs)
            try:
                checked = review_scene(candidate['scene'], run_dir=run,
                    deps=replace(deps, stage_timeout_sec=min(deps.stage_timeout_sec, remaining),
                                 run_subprocess_bounded=bounded_runner),
                    preflight_dir=folder / 'temporal')
            except (TimeoutError, HtmlReviewError) as error:
                if time.monotonic() - started < geometry_budget_seconds:
                    raise
                write_json_atomic(folder / 'error.json', {'code':'LINKED_LAYOUT_BUDGET','message':str(error)[:500]})
                break
            write_json_atomic(folder / 'scene.json', candidate['scene'])
            write_json_atomic(folder / 'report.json', checked)
            attempts.append({'operations': operations, 'passed': bool(checked.get('passed')),
                             'report': str((folder / 'report.json').relative_to(run))})
            progress({'linked_layout_checks': checks, 'linked_layout_max_checks': max_geometry_checks})
            if checked.get('passed') and checked.get('geometry_preflight', {}).get('passed'):
                current, report, status, reason = candidate['scene'], checked, 'candidate', None
                break
            if checked.get('geometry_preflight', {}).get('issue_group_count', float('inf')) < preflight.get('issue_group_count', 0):
                current, report, improved = candidate['scene'], checked, True
                break
        if status == 'candidate' or not improved:
            break
    if status != 'candidate' and (checks >= max_geometry_checks or time.monotonic() - started >= geometry_budget_seconds):
        status, reason = 'budget_exhausted', 'LINKED_LAYOUT_BUDGET'
    checkpoint()
    if (resolved_scene_inputs(scene, run, deps.repo_root) != source_identity
        or {'scene':scene,'binding':binding,'manual':manual,'resources':editor.resources(run),'beats':beats} != original):
        status, reason = 'stale', 'LINKED_LAYOUT_SOURCE_STALE'
    summary = {'version': 'linked-layout/0.1.0', 'status': status, 'reason': reason,
               'passed': status == 'candidate', 'audit': str(audit.relative_to(run)),
               'capacity': capacity['summary'], 'attempts': attempts, 'provider_calls': 0,
               'model_calls': 0, 'author_writes': 0,
               'elapsed_seconds': round(time.monotonic() - started, 3)}
    result = {'scene': current if status == 'candidate' else scene, 'binding': binding,
              'report': report, 'summary': summary}
    write_json_atomic(audit / 'result.json', result)
    return result
