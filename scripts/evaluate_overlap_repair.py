"""Exercise original repair/feedback/save on frozen courses with supplied decisions.

This is a controlled integration experiment, not autonomous model acceptance.
Decisions: {slide_id: [[operation, ...], ...]}, at most two rounds per slide.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from artifact_fingerprint import sha256_file, sha256_json  # noqa: E402
import html_scene_editing as editor  # noqa: E402
import html_scene_repair as repair  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from scripts.benchmark_capacity import run_course_baseline, source_identity  # noqa: E402


def evaluate(source_run, output, decisions):
    if not isinstance(decisions, dict) or not decisions or any(
        not isinstance(rounds, list) or not 1 <= len(rounds) <= 2
        or any(not isinstance(ops, list) or not 1 <= len(ops) <= 20 for ops in rounds)
        for rounds in decisions.values()
    ):
        raise ValueError("Supply one or two nonempty operation rounds per slide")
    # Validate before freezing a run or collecting expensive browser evidence.
    from html_repair_models import RepairOperation
    for rounds in decisions.values():
        for operations in rounds:
            for operation in operations:
                RepairOperation.model_validate(operation)
    source_run, output = Path(source_run).resolve(), Path(output).resolve()
    baseline = run_course_baseline(source_run, output, list(decisions), "output_frames")
    write_json_atomic(output / "decisions.json", decisions)
    run = output / "isolated-run"
    results = []
    for slide, rounds in decisions.items():
        original = editor.load_editor(run, slide)
        # Scope is explicit and fixed across both full patches.
        scope = sorted({op['targetId'] for operations in rounds for op in operations})
        request = {'expected_revision': original['revision'], 'scope': scope,
                   'expected_audio_revision': editor.audio_revision(run, slide),
                   'instruction': '修复箭头经过文字区域的问题；保留原文、关系、动作及音频。',
                   'sampling_mode': 'output_frames', 'fps': 30, 'overlap_policy': 'registered'}
        calls = []

        def supplied_decision(**kwargs):
            payload = json.loads(kwargs['user_prompt'])
            calls.append({'evaluation_basis': payload['evaluation_basis'],
                          'image_context': payload['image_context'],
                          'issues': payload['temporal_report'].get('issues', [])})
            index = len(calls) - 1
            if index >= len(rounds):
                return {'status': 'unsupported', 'message': 'No further supplied decision'}
            return {'status': 'candidate', 'operations': copy.deepcopy(rounds[index])}

        candidate = repair.generate_repair(run, slide, request, supplied_decision)
        write_json_atomic(output / slide / 'candidate.json', candidate)
        candidate_only = editor.load_editor(run, slide) == original
        record = {'slide_id': slide, 'calls': calls, 'candidate_only_author_unchanged': candidate_only,
                  'status': candidate.get('status'), 'provider_calls': 0, 'model': None, 'cost': None,
                  'autonomous_model_acceptance': 'not_run', 'human_visual_acceptance': 'pending_review'}
        if candidate.get('review', {}).get('passed'):
            # Changes beyond presentation are forbidden for this experiment.
            def content(scene):
                scene = copy.deepcopy(scene)
                for node in scene['nodes']:
                    node.pop('presentation', None)
                return scene
            if content(original['scene']) != content(candidate['scene']) or original['binding'] != candidate['binding']:
                raise ValueError('Semantic, motion or binding change outside experiment scope')
            save = repair.save_repair(run, slide, {**candidate['request'], 'candidate_key': candidate['candidate_key']})
            current = editor.load_editor(run, slide)
            checkpoint = editor.saved_versions(run, slide, original['revision'])
            record.update(passed=True, saved_revision=save['revision'],
                          history_preserved=checkpoint['scene'] == original['scene'] and checkpoint['binding'] == original['binding'],
                          audio_unchanged=editor.audio_revision(run, slide) == request['expected_audio_revision'],
                          saved_scene_sha256=sha256_json(current['scene']),
                          frame_count=candidate['review']['frame_count'],
                          frame_complete=candidate['review']['coverage']['frame_complete'])
        else:
            record['passed'] = False
        results.append(record)
        write_json_atomic(output / 'repair-progress.json', results)
    manifest = json.loads((output / 'course-manifest.json').read_text(encoding='utf-8'))
    source = json.loads((output / 'source-manifest.json').read_text(encoding='utf-8'))
    summary = {'mode': 'supplied_decisions_real_browser_feedback', 'baseline': baseline,
               'cases': results, 'source_unchanged': all(sha256_file(source_run / p) == digest for p, digest in manifest['files'].items()),
               'code_unchanged': source_identity()['working_tree_sha256'] == source['working_tree_sha256'],
               'boundary': 'Original courses untouched; explicit save only in isolated run; no provider or approval writes.'}
    write_json_atomic(output / 'repair-summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decisions', type=Path, required=True)
    args = parser.parse_args()
    summary = evaluate(args.source_run, args.output, json.loads(args.decisions.read_text(encoding='utf-8')))
    print(json.dumps({'passed': all(c['passed'] for c in summary['cases']),
                      'source_unchanged': summary['source_unchanged'], 'code_unchanged': summary['code_unchanged']}))


if __name__ == '__main__':
    main()
