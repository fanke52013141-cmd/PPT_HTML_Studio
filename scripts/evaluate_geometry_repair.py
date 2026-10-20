"""Provider-free original-page and controlled-variation geometry evaluation."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from artifact_fingerprint import sha256_file  # noqa: E402
import html_geometry_repair as geometry  # noqa: E402
import html_scene_editing as editor  # noqa: E402
import html_scene_repair as repair  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from scripts.benchmark_capacity import run_course_baseline, source_identity  # noqa: E402

CASES = [
    ('label-original', 'slide_001', 'original', ['obj-anchor-label'], {}),
    ('chart-original', 'slide_003', 'original', ['obj-card-2'], {}),
    ('label-up12', 'slide_001', 'controlled_variation', ['obj-anchor-label'], {'offsetY': -60}),
    ('label-down12', 'slide_001', 'controlled_variation', ['obj-anchor-label'], {'offsetY': -36}),
    ('chart-narrow16', 'slide_003', 'controlled_variation', ['obj-card-2'], {'width': 614}),
    ('chart-wide16', 'slide_003', 'controlled_variation', ['obj-card-2'], {'width': 646}),
    ('normal-stages', 'slide_004', 'clear_control', ['obj-header'], {}),
    ('already-fixed-label', 'slide_001', 'clear_control', ['obj-anchor-label'], {'offsetY': 20}),
    ('arrow-scope', 'slide_001', 'unsupported_control', ['obj-relation-2'], {}),
    ('unrelated-scope', 'slide_003', 'unsupported_control', ['obj-card-1'], {}),
]


def evaluate(source, output):
    source, output = source.resolve(), output.resolve()
    baseline = run_course_baseline(source, output, ['slide_001', 'slide_003', 'slide_004'], 'output_frames')
    records = []
    for name, slide, group, scope, values in CASES:
        started = time.monotonic()
        folder, run = output / name, output / name / 'isolated-run'
        shutil.copytree(output / 'isolated-run', run,
                        ignore=shutil.ignore_patterns('repair-evidence', 'records', 'builds', 'editor-history'))
        if values:
            doc = editor.load_editor(run, slide)
            candidate = repair.candidate(run, slide, {'expected_revision': doc['revision'], 'scope': scope,
                'source': 'ai', 'operations': [{'targetId': scope[0], 'kind': 'set_presentation', 'values': values}]})
            # Explicit controlled input only, outside original run. No approval.
            write_json_atomic(run / f'planning/html_visual/scene-{slide}.json', candidate['scene'])
        doc = editor.load_editor(run, slide)
        result = geometry.geometry_repair(run, slide, {'expected_revision': doc['revision'],
                          'expected_audio_revision': editor.audio_revision(run, slide), 'scope': scope})
        write_json_atomic(folder / 'result.json', result)
        selected = result.get('candidate')
        row = {'case': name, 'slide': slide, 'group': group, 'input_variation': values,
               'status': result['status'], 'passed': result['passed'], 'elapsed_seconds': result['elapsed_seconds'],
               'case_elapsed_seconds': round(time.monotonic()-started, 3),
               'provider_calls': 0, 'author_unchanged': result['author_unchanged'],
               'proposed_count': result.get('proposed_count', 0),
               'sampled_checks': sum(a['sampling_mode'] == 'sampled' for a in result['attempts']),
               'full_checks': sum(a['sampling_mode'] == 'output_frames' for a in result['attempts']),
               'rejected_checks': sum(not a['passed'] for a in result['attempts']),
               'operations': selected['request']['operations'] if selected else [],
               'human_visual_acceptance': 'pending_review'}
        if selected:
            # Check semantic/motion/binding preservation without ignoring style.
            expected = copy.deepcopy(doc['scene'])
            for operation in selected['request']['operations']:
                node = next(n for n in expected['nodes'] if n['id'] == operation['targetId'])
                node.setdefault('presentation', {}).update(operation['values'])
            row.update(preserved=expected == selected['scene'] and doc['binding'] == selected['binding'],
                       frame_count=selected['review']['frame_count'],
                       issue_count=len(selected['review']['issues']),
                       selected_rank=next(a['rank'] for a in result['attempts'] if a['sampling_mode'] == 'output_frames' and a['passed']))
            raw = json.loads((run / selected['review']['measurements_path']).read_text(encoding='utf-8'))
            target = scope[0]
            original_box = next((f.get('boxes', {}).get(target) for f in reversed(raw['frames']) if target in f.get('boxes', {})), None)
            row['after_box'] = original_box
            first_report = min((run / 'planning/html_visual/repair-evidence').glob('*/report.json'),
                               key=lambda p: p.stat().st_mtime_ns)
            before_frame = json.loads(first_report.read_text(encoding='utf-8'))['frames'][-1]
            after_frame = raw['frames'][-1]
            row['before_box'] = before_frame['boxes'][target]
            row['box_change_px'] = {k: round(original_box[k]-row['before_box'][k], 3)
                                   for k in ('x', 'y', 'width', 'height')}
            row['text_lines_before'] = before_frame.get('measurements', {}).get(target, {}).get('lines')
            row['text_lines_after'] = after_frame.get('measurements', {}).get(target, {}).get('lines')
            nodes = {n['id']: n for n in doc['scene']['nodes']}
            for name_, frame in [('before', before_frame), ('after', after_frame)]:
                gaps = [geometry._rect_gap(frame['boxes'][target], box)
                        for other, box in frame['boxes'].items() if other != target
                        and nodes.get(other, {}).get('type') not in ('arrow', 'annotation', 'figure', 'asset')]
                row[f'min_neighbor_box_gap_{name_}_px'] = round(min(gaps), 3) if gaps else None
            source_shot = run / selected['review']['screenshots'][-1]['file']
            shutil.copyfile(source_shot, folder / 'after.png')
        records.append(row)
        write_json_atomic(output / 'geometry-progress.json', records)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    from statistics import median
    metrics = {}
    for group in ('original', 'controlled_variation', 'clear_control', 'unsupported_control'):
        rows = [r for r in records if r['group'] == group]
        metrics[group] = {'cases': len(rows), 'passed': sum(r['passed'] for r in rows),
                          'expected_outcome_met': sum((r['status'] == 'needs_revision') if group == 'unsupported_control' else r['passed'] for r in rows),
                          'median_elapsed_seconds': median(r['elapsed_seconds'] for r in rows)}
    manifest = json.loads((output / 'course-manifest.json').read_text(encoding='utf-8'))
    identity = json.loads((output / 'source-manifest.json').read_text(encoding='utf-8'))
    summary = {'version': geometry.VERSION, 'cases': records, 'metrics': metrics, 'baseline': baseline,
               'source_unchanged': all(sha256_file(source / p) == digest for p, digest in manifest['files'].items()),
               'code_unchanged': source_identity()['working_tree_sha256'] == identity['working_tree_sha256'],
               'provider_calls': 0, 'boundary': '2 original faulty pages, 4 derived inputs, 2 clear and 2 unsupported controls; not 10 independent courses or visual approvals.'}
    write_json_atomic(output / 'geometry-summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.source_run, args.output)


if __name__ == '__main__':
    main()
