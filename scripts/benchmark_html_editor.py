"""Explicit live, bounded repair comparison on isolated copies of an existing page.

No providers run without --live. Outputs and raw model evidence stay outside Git.
Costs are unknown unless the provider reports them; never infer prices from tokens.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--slide', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--phase', choices=('baseline', 'tools', 'skill'), required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live:
        parser.error('Real configured model requests require explicit --live')
    import server  # noqa: F401 - configure the actual application service dependencies
    from database import SessionLocal, Project
    from account_context import account_scope
    from project_model_binding_service import freeze_project_models
    from json_llm_service import generate_json_with_configured_llm
    import json_llm_transport
    import html_scene_editing as edit
    import html_scene_repair as repair
    import html_visual_store as store

    source, output = args.run_dir.resolve(), args.output_dir.resolve()
    if source == output or source in output.parents or output.exists():
        raise ValueError('Choose a fresh output directory outside the source run')
    source_scene = source / f'planning/html_visual/scene-{args.slide}.json'
    source_binding = source / f'planning/html_visual/binding-{args.slide}.json'
    source_files = [source_scene, source_binding, source / 'planning/visual_contract.json',
                    *sorted((source / 'slides' / args.slide).iterdir())]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files if p.is_file()}
    output.mkdir(parents=True)
    with SessionLocal() as db:
        project = db.query(Project).filter(Project.id == args.project).one()
        assert Path(project.run_dir).resolve() == source
        with account_scope(project.account_id):
            models = freeze_project_models(project, required=('text',))
    phase_results, transport_calls = [], []
    original_transport = json_llm_transport.receive_completion

    def measured_transport(*positional, **kwargs):
        started = time.perf_counter()
        record = {'elapsed_sec': None, 'usage': None, 'status': 'unknown'}
        transport_calls.append(record)
        try:
            response = original_transport(*positional, **kwargs)
            record['status'] = 'returned'
            usage = getattr(response, 'usage', None)
            if usage is not None:
                record['usage'] = usage.model_dump() if hasattr(usage, 'model_dump') else None
            return response
        finally:
            record['elapsed_sec'] = time.perf_counter() - started

    json_llm_transport.receive_completion = measured_transport
    skill_source = ROOT / '.agents/skills/produce-editable-html/SKILL.md'
    skill_excerpt = next(line for line in skill_source.read_text(encoding='utf-8').splitlines()
                         if line.startswith('按局部编辑Skill执行：'))
    tool_hash = hashlib.sha256(b''.join((ROOT/name).read_bytes() for name in ('html_scene_repair.py', 'html_repair_static.py', 'html_engine/visual/relationship-capacity.cjs'))).hexdigest()
    try:
        for case in ('layout', 'timing', 'protected', 'unsupported'):
            run = output / case
            run.mkdir()
            for path in source_files:
                if path.is_file():
                    destination = run / path.relative_to(source)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
            # Explicit copy of real content/audio. Only this isolated copy gets manual editing.
            author = json.loads(source_scene.read_text(encoding='utf-8'))
            store.save_scene(run, args.slide, author, 0)
            doc = edit.load_editor(run, args.slide)
            author = copy.deepcopy(doc['scene'])
            author['version'] = '0.5.0' if author['version'] in ('0.3.0', '0.4.0') else author['version']
            header = next(n for n in author['nodes'] if n['id'] == 'header')
            header.setdefault('presentation', {})['offsetX'] = 20
            edit.save_editor(run, args.slide, author, doc['binding'], doc['revision'], origin='human')
            doc = edit.load_editor(run, args.slide)
            key = 'header:enter'
            binding_offset = (doc['binding'] or {}).get('actions', {}).get(key, {}).get('offsetMs', 0)
            instructions = {
                'layout': '只把header的presentation.offsetY设为12；保留人工offsetX=20以及所有其他数据。',
                'timing': f'只把header已有enter动作的原句绑定offsetMs设为{binding_offset+200}；不换beatId、不改作者duration、不改布局。',
                'protected': '把header的presentation.offsetX设为99。如果该字段受人工保护，应返回unsupported或needs_input，不能绕过保护。',
                'unsupported': '新增一个对象来表达结冰过程。当前局部编辑接口不支持新增对象时返回unsupported，不修改已有对象代替。',
            }
            instruction = instructions[case]
            if args.phase == 'skill':
                instruction += '\n' + skill_excerpt
            request = {'expected_revision': doc['revision'], 'instruction': instruction,
                       'scope': ['header'], 'time_range_ms': [1000, 1500], 'step_ms': 250}
            started, call_start, rounds = time.perf_counter(), len(transport_calls), []

            def generate(**kwargs):
                rounds.append(time.perf_counter())
                return generate_json_with_configured_llm(**kwargs, model_binding=models.text)

            result = {'case': case, 'success': False, 'mis_edit': False, 'status': None}
            try:
                candidate = repair.generate_repair(run, args.slide, request, generate)
                result['status'] = candidate['status']
                if candidate['status'] == 'candidate':
                    repair.save_repair(run, args.slide, {**candidate['request'], 'candidate_key': candidate['candidate_key']})
                    after = edit.load_editor(run, args.slide)
                    node = next(n for n in after['scene']['nodes'] if n['id'] == 'header')
                    expected_scene, expected_binding = copy.deepcopy(doc['scene']), copy.deepcopy(doc['binding'])
                    if case == 'layout':
                        next(n for n in expected_scene['nodes'] if n['id'] == 'header')['presentation']['offsetY'] = 12
                    if case == 'timing':
                        expected_binding['actions'][key]['offsetMs'] = binding_offset + 200
                    result['success'] = case in ('layout', 'timing') and after['scene'] == expected_scene and after['binding'] == expected_binding
                    result['mis_edit'] = not result['success']
                    assert node['presentation']['offsetX'] == 20
                else:
                    result['success'] = case in ('protected', 'unsupported') and candidate['status'] in ('unsupported', 'needs_input')
                    assert edit.load_editor(run, args.slide)['scene'] == doc['scene']
            except Exception as exc:
                # A failure is retained in the denominator. Never resubmit an unknown request.
                result['status'] = getattr(exc, 'code', type(exc).__name__)
            result.update(rounds=len(rounds), http_calls=len(transport_calls)-call_start,
                          elapsed_sec=time.perf_counter()-started, cost=None)
            phase_results.append(result)
            report = {'phase': args.phase, 'model': models.text.model, 'cases': phase_results,
                      'requests': transport_calls, 'cost': None, 'source_hashes': before,
                      'repair_source_sha256': tool_hash,
                      'skill_excerpt_sha256': hashlib.sha256(skill_excerpt.encode()).hexdigest() if args.phase=='skill' else None,
                      'source_unchanged': all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())}
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(result,ensure_ascii=False),flush=True)
            if any(c['status']=='unknown' for c in transport_calls[call_start:]):
                raise RuntimeError('Unknown provider outcome: stop remaining cases; do not resend')
    finally:
        json_llm_transport.receive_completion = original_transport


if __name__ == '__main__':
    main()
