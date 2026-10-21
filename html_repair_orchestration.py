"""Geometry-first overlap orchestration; original repair owns candidates and save."""
import html_capacity_repair as capacity
import html_geometry_repair as geometry
import html_scene_editing as editor
import html_scene_repair as repair
from html_handoff_diagnostics import pictures
from html_repair_models import RepairGenerateRequest

OVERLAP_INSTRUCTION = "仅调整所选对象的位置与尺寸，解决箭头穿过文字；保留文字、关系、样式、动画和人工保护字段。"
CAPACITY_INSTRUCTION = "仅调整所选对象的尺寸或文字排版，解决容量溢出；保留文字语义、关系、样式、动画和人工保护字段。"


def _comparison(run, before, after):
    # Compare matching moments, prioritising an actual fault and the final frame.
    left = {shot['timeMs']: shot for shot in before.get('screenshots', [])}
    right = {shot['timeMs']: shot for shot in after.get('screenshots', [])}
    common = sorted(left.keys() & right.keys())
    times = []
    if common:
        faults = [i['timeMs'] for i in before.get('issues', []) if 'timeMs' in i]
        if faults:
            times.append(min(common, key=lambda t: abs(t-faults[0])))
        if common[-1] not in times:
            times.append(common[-1])
    return {'before': pictures(run, [left[t] for t in times]),
            'after': pictures(run, [right[t] for t in times])}


def _changes(doc, result):
    before = {n['id']: n for n in doc['scene']['nodes']}
    after = {n['id']: n for n in result.get('scene', {}).get('nodes', [])}
    changes = []
    for op in result.get('request', {}).get('operations', []):
        target = op['targetId']
        if op.get('kind') == 'set_endpoint_point':
            for side in op['values']:
                old = (before.get(target) or {}).get(side, {}).get('point')
                new = (after.get(target) or {}).get(side, {}).get('point')
                if old != new:
                    changes.append({'targetId': target, 'parameter': f'{side}.point',
                                    'before': old, 'after': new})
            continue
        for key in op['values']:
            old = before[target].get('presentation', {}).get(key)
            new = after[target].get('presentation', {}).get(key)
            if old != new:
                changes.append({'targetId': target, 'parameter': key, 'before': old, 'after': new})
    return changes


def generate_repair(run, slide, request, generator_factory):
    """Factory is lazy: a legal geometry candidate never needs a configured provider."""
    request = RepairGenerateRequest.model_validate(request).model_dump(mode='json')
    if request['strategy'] == 'model':
        return repair.generate_repair(run, slide, request, generator_factory())
    if request['strategy'] == 'capacity_first':
        if request['instruction'] != CAPACITY_INSTRUCTION:
            raise editor.SceneEditError('REPAIR_CAPACITY_GOAL', 'capacity_first仅支持固定的容量修复任务；其他目标请使用model策略')
        doc = repair._revision(run, slide, request['expected_revision'])
        scope = request['scope']
        if len(scope) > 4 or len(set(scope)) != len(scope):
            raise editor.SceneEditError('REPAIR_SCOPE', '容量修复请选择1至4个不同对象')
        if any(target not in {node['id'] for node in doc['scene']['nodes']} for target in scope):
            raise editor.SceneEditError('TARGET_NODE_GONE', '修复目标不存在')
        request['expected_audio_revision'] = request.get('expected_audio_revision') or editor.audio_revision(run, slide)
        trial = capacity.repair_capacity(run, slide, request)
        path = {'strategy': 'capacity_first', 'origin': 'deterministic_capacity',
                'fallback_reason': None, 'attempts': len(trial.get('attempts', [])),
                'elapsed_seconds': trial.get('elapsed_seconds')}
        if trial['status'] == 'unchanged':
            return {'status': 'unchanged', 'message': '当前整页注册检查已通过，无需修改。',
                    'review': trial['baseline'], 'repair_path': path, 'changes': []}
        if trial['status'] == 'candidate':
            candidate = trial['candidate']
            return {**candidate, 'repair_path': path,
                    'changes': _changes(doc, {'scene': candidate['scene'],
                                              'request': trial['request']})}
        return {'status': 'needs_revision',
                'message': '确定性容量试算未找到通过原检查的候选；未调用模型，也未修改原页面。',
                'review': trial.get('baseline'), 'repair_path': path, 'changes': [],
                'attempts': trial.get('attempts', []), 'reason': trial.get('reason')}
    if request['instruction'] != OVERLAP_INSTRUCTION:
        raise editor.SceneEditError('REPAIR_GEOMETRY_GOAL', 'geometry_first仅支持固定的箭头文字避让任务；其他目标请使用model策略')
    doc = repair._revision(run, slide, request['expected_revision'])
    scope = request['scope']
    if len(scope) > 4 or len(set(scope)) != len(scope):
        raise editor.SceneEditError('REPAIR_SCOPE', '避让修复请选择1至4个不同对象')
    if any(s not in {n['id'] for n in doc['scene']['nodes']} for s in scope):
        raise editor.SceneEditError('TARGET_NODE_GONE', '修复目标不存在')
    request['expected_audio_revision'] = request['expected_audio_revision'] or editor.audio_revision(run, slide)
    trial = geometry.geometry_repair(run, slide, request)
    baseline = trial['baseline']
    path = {'strategy': 'geometry_first', 'origin': 'geometry', 'fallback_reason': None,
            'geometry_attempts': len(trial['attempts']), 'geometry_seconds': trial['elapsed_seconds']}
    if trial['status'] == 'unchanged':
        return {'status': 'unchanged', 'message': '当前整页注册检查已通过，无需修改。',
                'review': baseline, 'repair_path': path, 'changes': []}
    result = trial.get('candidate')
    if result is None:
        path.update(origin='model', fallback_reason='有界几何试算未找到通过整页检查的候选，已转入原模型修复。')
        # Full registered checks apply equally to the fallback; no sampled-only save.
        request.update(overlap_policy='registered', sampling_mode='output_frames', fps=30, time_range_ms=None)
        generator = generator_factory()
        try:
            result = repair.generate_repair(run, slide, request, generator)
        except editor.SceneEditError as exc:
            raise editor.SceneEditError(exc.code, '几何试算未找到合法候选；模型修复未完成：' + str(exc)) from exc
        except Exception as exc:
            raise editor.SceneEditError('REPAIR_MODEL_UNVERIFIED',
                '几何试算未找到合法候选；模型请求结果未确认，请先核对修复记录，不要自动重试。') from exc
    if editor.load_editor(run, slide) != doc:
        raise editor.SceneEditError('REPAIR_SOURCE_CHANGED', '原页面已变化，候选已丢弃')
    editor._check_audio_revision(run, slide, request['expected_audio_revision'])
    return {**result, 'repair_path': path, 'changes': _changes(doc, result),
            'comparison': _comparison(run, baseline, result.get('review', {}))}
