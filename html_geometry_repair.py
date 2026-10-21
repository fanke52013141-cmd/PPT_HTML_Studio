"""Bounded geometry proposals; original scene repair remains the only validator."""
import itertools
import json
import math
from pathlib import Path
import time

import html_scene_editing as editor
import html_scene_repair as repair

VERSION = 'geometry-repair/0.1.1'
DELTAS = (0, -8, 8, -16, 16, -24, 24, -32, 32, -48, 48, -64, 64, -96, 96)


def line_hits(a, b, rect, padding=8):
    """Conservative proposal heuristic, never a substitute for original SVG QA."""
    lo, hi = 0., 1.
    for start, delta, lower, upper in ((a['x'], b['x']-a['x'], rect['x']-padding, rect['x']+rect['width']+padding),
                                        (a['y'], b['y']-a['y'], rect['y']-padding, rect['y']+rect['height']+padding)):
        if abs(delta) < 1e-9:
            if start < lower or start > upper:
                return False
        else:
            x, y = (lower-start)/delta, (upper-start)/delta
            lo, hi = max(lo, min(x, y)), min(hi, max(x, y))
            if lo > hi:
                return False
    return True


def _changed_box(box, delta):
    return {k: box[k]+delta.get(k, 0) for k in ('x', 'y', 'width', 'height')}


def _rect_gap(a, b):
    return math.hypot(max(b['x']-a['x']-a['width'], a['x']-b['x']-b['width'], 0),
                      max(b['y']-a['y']-a['height'], a['y']-b['y']-b['height'], 0))


def _score(node, delta, conflicts, frames, nodes):
    hits = 0
    for frame in frames:
        for arrow_id, text_id in conflicts:
            if frame.get('visible', {}).get(arrow_id, 1) <= .01 or frame.get('visible', {}).get(text_id, 1) <= .01:
                continue
            geometry = frame.get('geometry', {}).get(arrow_id)
            arrow = nodes[arrow_id]
            if geometry and 'from' in geometry and 'to' in geometry:
                endpoints = {}
                for edge in ('from', 'to'):
                    point = dict(geometry[edge])
                    if arrow.get(edge, {}).get('objectId') == node['id']:
                        normalized = arrow[edge].get('point')
                        if not normalized:
                            return None
                        point['x'] += delta['x'] + normalized['x']*delta['width']
                        point['y'] += delta['y'] + normalized['y']*delta['height']
                    endpoints[edge] = point
                segments = [{'a': endpoints['from'], 'b': endpoints['to'], 'radius': 8}]
            else:
                # Slot arrows have no relation endpoints. Only translate their
                # intersected text; never invent endpoint identities or routing.
                if text_id != node['id'] or arrow.get('from') or arrow.get('to'):
                    return None
                segments = frame.get('_proposal_segments', {}).get(arrow_id)
                if not segments:
                    return None
            for rect in frame.get('textRects', {}).get(text_id, []):
                # Resize proposals only touch endpoint cards; their own text
                # reflow is left to original browser/static capacity validation.
                moved = _changed_box(rect, {'x': delta['x'], 'y': delta['y']}) if text_id == node['id'] else rect
                hits += any(line_hits(s['a'], s['b'], moved, max(8, s['radius'])) for s in segments)
    final = frames[-1]
    original = final.get('boxes', {}).get(node['id'])
    if not original:
        return None
    changed = _changed_box(original, delta)
    if changed['x'] < 0 or changed['y'] < 0 or changed['x']+changed['width'] > 1600 or changed['y']+changed['height'] > 800:
        return None
    for other, box in final['boxes'].items():
        if nodes.get(other, {}).get('type') != 'figure':
            continue
        def inside(inner):
            return (inner['x'] >= box['x']-1 and inner['y'] >= box['y']-1
                    and inner['x']+inner['width'] <= box['x']+box['width']+1
                    and inner['y']+inner['height'] <= box['y']+box['height']+1)
        if inside(original) and not inside(changed):
            return None
    gap_loss = 0.
    for other, box in final['boxes'].items():
        if other == node['id'] or nodes.get(other, {}).get('type') in ('arrow', 'annotation', 'figure', 'asset'):
            continue
        gap_loss += max(0, min(16, _rect_gap(original, box))-min(16, _rect_gap(changed, box)))
    change = abs(delta['x'])/original['width'] + abs(delta['y'])/original['height']
    change += 2*(abs(delta['width'])/original['width']+abs(delta['height'])/original['height'])
    return (hits, round(change + gap_loss/16, 6), round(change, 6))


def propose(doc, scope, report, frames):
    nodes = {n['id']: n for n in doc['scene']['nodes']}
    if not scope or len(scope) > 4 or any(s not in nodes for s in scope):
        raise ValueError('Select one to four existing objects')
    issues = report.get('issues', [])
    crossed = {tuple(sorted(i.get('targets', []))) for i in issues
               if i.get('measured', {}).get('reason') == 'stroke_crosses_text'}
    if not crossed or any(i.get('code') != 'TEMPORAL_OVERLAP'
            or i.get('measured', {}).get('reason') not in ('stroke_crosses_text', 'stroke_crosses_object')
            or tuple(sorted(i.get('targets', []))) not in crossed for i in issues):
        return []
    conflicts = set()
    for issue in issues:
        ids = issue['targets']
        arrows = [i for i in ids if nodes[i]['type'] == 'arrow']
        if len(arrows) != 1:
            return []
        conflicts.add((arrows[0], next(i for i in ids if i != arrows[0])))
    # Bound numeric work independently of course duration. Always include first,
    # last and evenly spaced raw frames; the original checker samples all times.
    if len(frames) > 24:
        frames = [frames[round(i*(len(frames)-1)/23)] for i in range(24)]
    if not frames:
        return []
    # Reuse the original SVG parser rather than implementing a second path
    # grammar. Numeric work stays bounded to 24 frames; browser QA still judges
    # every candidate, including heads, reflow and intermediate motion.
    implicit = {arrow for arrow, _ in conflicts if not nodes[arrow].get('from') and not nodes[arrow].get('to')}
    if implicit:
        parsed = editor._node("""
const fs=require('node:fs'),{linearSegments}=require('./html_engine/tools/vector-overlap.cjs');
const frames=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(frames.map(frame=>Object.fromEntries(Object.entries(frame).map(([id,paths])=>{
  const segments=[];
  if(!Array.isArray(paths) || !paths.length) return [id,null];
  for(const p of paths) {
    if(!p.supported || !Number.isFinite(p.radius) || p.radius<0) return [id,null];
    const lines=linearSegments(p.d,p.matrix);
    if(!lines) return [id,null];
    segments.push(...lines.map(s=>({...s,radius:p.radius})));
  }
  return [id,segments];
})))));
""", [{arrow: frame.get('vectorPaths', {}).get(arrow) for arrow in sorted(implicit)} for frame in frames])
        frames = [{**frame, '_proposal_segments': segments} for frame, segments in zip(frames, parsed, strict=True)]
    proposals = []
    for target in sorted(set(scope)):
        node = nodes[target]
        if node['type'] not in ('text', 'label', 'badge', 'card'):
            continue
        if not any(target == text or any(nodes[arrow].get(edge, {}).get('objectId') == target for edge in ('from', 'to')) for arrow, text in conflicts):
            continue
        box = frames[-1].get('boxes', {}).get(target)
        if not box or box['width'] <= 0 or box['height'] <= 0:
            continue
        presentation = node.get('presentation', {})
        widths = [0] if node['type'] != 'card' else [d for d in (*DELTAS, -128, 128, -144, 144)
                                                   if .75*box['width'] <= box['width']+d <= 1.15*box['width']]
        for dx, dy, dw in itertools.product(DELTAS, DELTAS, widths):
            if (not dx and not dy and not dw) or (dx and dy) or (dw and dx):
                continue
            delta = {'x': dx, 'y': dy, 'width': dw, 'height': 0}
            score = _score(node, delta, conflicts, frames, nodes)
            if score is None or score[0]:
                continue
            values = {}
            for key, d in (('offsetX', dx), ('offsetY', dy), ('width', dw)):
                if d:
                    values[key] = round(presentation.get(key, box['width'] if key == 'width' else 0)+d, 3)
            if any(abs(v) > 400 for k, v in values.items() if k.startswith('offset')):
                continue
            proposals.append({'operations': [{'targetId': target, 'kind': 'set_presentation', 'values': values}],
                              'rank': list(score), 'delta': delta})
    return sorted(proposals, key=lambda p: (p['rank'], json.dumps(p['operations'], sort_keys=True)))


def geometry_repair(run, slide, request):
    """Read-only bounded preview. Successful result is an original repair candidate."""
    started = time.monotonic()
    doc = editor.load_editor(run, slide)
    if doc['revision'] != request['expected_revision']:
        raise ValueError('Stale scene revision')
    scope = request.get('scope', [])
    if not scope or len(scope) > 4 or len(set(scope)) != len(scope) or any(s not in {n['id'] for n in doc['scene']['nodes']} for s in scope):
        raise ValueError('Select one to four distinct existing objects')
    temporal = {k: v for k, v in request.items() if k in repair.TemporalRequest.model_fields}
    temporal.update(overlap_policy='registered', sampling_mode='output_frames', fps=30, time_range_ms=None)
    temporal['expected_audio_revision'] = request.get('expected_audio_revision') or editor.audio_revision(run, slide)
    baseline = repair.evidence(run, slide, temporal)
    attempts = []
    if baseline.get('passed'):
        if editor.load_editor(run, slide) != doc:
            raise ValueError('Source changed during geometry repair')
        return {'status': 'unchanged', 'passed': True, 'attempts': [], 'provider_calls': 0,
                'baseline': baseline,
                'author_unchanged': True, 'elapsed_seconds': round(time.monotonic()-started, 3)}
    raw = json.loads((Path(run) / baseline['measurements_path']).read_text(encoding='utf-8'))
    proposals = propose(doc, request['scope'], baseline, raw.get('frames', []))
    selected = None
    full_checks = 0
    for proposal in proposals[:6]:
        body = {**temporal, 'sampling_mode': 'sampled', 'step_ms': 250, 'operations': proposal['operations'],
                'scope': request['scope'], 'source': 'ai'}
        attempt = {**proposal, 'sampling_mode': 'sampled'}
        attempts.append(attempt)
        try:
            candidate = repair.preview_repair(run, slide, body)
            attempt.update(passed=candidate['review']['passed'], issue_count=len(candidate['review']['issues']),
                           evidence_dir=candidate['review']['evidence_dir'])
            if candidate['review']['passed']:
                if full_checks >= 3:
                    continue
                full_checks += 1
                full_body = {**body, 'sampling_mode': 'output_frames'}
                full_attempt = {**proposal, 'sampling_mode': 'output_frames'}
                attempts.append(full_attempt)
                try:
                    full_candidate = repair.preview_repair(run, slide, full_body)
                    full_attempt.update(passed=full_candidate['review']['passed'],
                                        issue_count=len(full_candidate['review']['issues']),
                                        evidence_dir=full_candidate['review']['evidence_dir'])
                    if full_candidate['review']['passed']:
                        selected = full_candidate
                        break
                except (editor.SceneEditError, ValueError) as exc:
                    full_attempt.update(passed=False, code=getattr(exc, 'code', type(exc).__name__))
        except (editor.SceneEditError, ValueError) as exc:
            attempt.update(passed=False, code=getattr(exc, 'code', type(exc).__name__))
    unchanged = editor.load_editor(run, slide) == doc
    if not unchanged:
        raise ValueError('Source changed during geometry repair; candidate discarded')
    return {'status': 'candidate' if selected else 'needs_revision', 'passed': selected is not None,
            'baseline': baseline,
            'candidate': selected, 'proposed_count': len(proposals), 'attempts': attempts, 'provider_calls': 0,
            'author_unchanged': unchanged, 'version': VERSION,
            'elapsed_seconds': round(time.monotonic()-started, 3)}
