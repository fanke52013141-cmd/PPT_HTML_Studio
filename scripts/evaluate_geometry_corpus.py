"""Evaluate explicitly sourced pages without saving authors or approvals.

The host-only spec contains cases with id, course_id, page_id, source_run,
slide_id, scope and provenance (original, archived_candidate, controlled_variation,
or fixture). Repeated candidates of a page never count as independent pages.
Live fallback is opt-in, at most one case and two physical model calls per run.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from artifact_fingerprint import sha256_file  # noqa: E402
import html_geometry_repair as geometry  # noqa: E402
import html_repair_orchestration as orchestration  # noqa: E402
import html_scene_editing as editor  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from scripts.benchmark_capacity import run_course_baseline, source_identity  # noqa: E402

PROVENANCE = {'original', 'archived_candidate', 'controlled_variation', 'fixture'}


def validate_cases(cases):
    if not isinstance(cases, list) or not 1 <= len(cases) <= 20:
        raise ValueError('Supply one to twenty explicit cases')
    ids = set()
    for case in cases:
        identity = case.get('id', '')
        if (not identity or len(identity) > 80 or
                any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in identity) or identity in ids):
            raise ValueError('Distinct safe case ids required')
        ids.add(identity)
        if case.get('provenance') not in PROVENANCE or not all(
                isinstance(case.get(k), str) and case[k].strip()
                for k in ('course_id', 'page_id', 'source_run', 'slide_id', 'source_note')):
            raise ValueError('Explicit course/page provenance and source note required')
        scope = case.get('scope')
        if not isinstance(scope, list) or not 1 <= len(scope) <= 4 or len(set(scope)) != len(scope):
            raise ValueError('Select one to four distinct objects')
        if not all(isinstance(target, str) and target for target in scope):
            raise ValueError('Scope must contain object ids')
        try:
            editor.store.validate_slide_id(case['slide_id'])
        except editor.store.HtmlVisualError as exc:
            raise ValueError('Invalid slide identity') from exc
    return cases


def issue_groups(report):
    groups = Counter((i.get('code'), i.get('measured', {}).get('reason'),
                      tuple(sorted(i.get('targets', [])))) for i in report.get('issues', []))
    return [{'code': code, 'reason': reason, 'targets': list(targets), 'occurrences': count}
            for (code, reason, targets), count in groups.items()]


def fallback_eligible(report):
    """Require actual crossing evidence; nontext moments of those pairs remain checked."""
    groups = issue_groups(report)
    crossed = {tuple(i['targets']) for i in groups if i['reason'] == 'stroke_crosses_text'}
    return bool(crossed) and all(i['code'] == 'TEMPORAL_OVERLAP' and
        i['reason'] in ('stroke_crosses_text', 'stroke_crosses_object') and
        tuple(i['targets']) in crossed for i in groups)


def metrics(rows):
    result = {}
    for provenance in sorted(PROVENANCE):
        selected = [r for r in rows if r['provenance'] == provenance]
        faulty = [r for r in selected if r.get('baseline_passed') is False]
        solved = [r for r in faulty if r.get('status') == 'candidate']
        result[provenance] = {
            'cases': len(selected),
            'distinct_courses': len({r['course_id'] for r in selected}),
            'distinct_pages': len({(r['course_id'], r['page_id']) for r in selected}),
            'blocked': sum(r['status'] == 'blocked' for r in selected),
            'faulty_cases': len(faulty), 'geometry_candidates': len(solved),
            'geometry_case_hit_rate': len(solved) / len(faulty) if faulty else None,
            'clear_unchanged': sum(r['status'] == 'unchanged' for r in selected),
        }
    return result


class LiveFallback:
    """Single-threaded diagnostic budget; every transport attempt is persisted."""

    def __init__(self, source, folder, timeout):
        self.source, self.folder, self.timeout = source, folder, timeout
        self.calls = []
        self.model = None
        self.started = None

    def factory(self):
        from scripts.compare_repair_runners import freeze_model
        import json_llm_service as llm
        self.model = freeze_model(self.source)
        self.started = time.monotonic()
        write_json_atomic(self.folder / 'live-intent.json', {
            'model': self.model.summary(), 'max_physical_calls': 2,
            'total_timeout_seconds': self.timeout, 'save': False, 'approval': False})

        def generate(**kwargs):
            remaining = self.timeout - (time.monotonic() - self.started)
            if remaining <= 0:
                raise TimeoutError('Live case total budget exhausted')
            return llm.generate_json_with_configured_llm(
                **kwargs, model_binding=self.model, request_timeout=remaining)

        generate.supports_stream_progress = True
        return generate

    def measured(self, original, client, params, **kwargs):
        if len(self.calls) >= 2 or any(c['state'] == 'unknown' for c in self.calls):
            raise ValueError('Physical request budget exhausted or unknown result; no replay')
        remaining = self.timeout - (time.monotonic() - self.started)
        if remaining <= 0:
            raise TimeoutError('Live case total budget exhausted')
        row = {'state': 'unknown', 'usage': None, 'cost': None}
        self.calls.append(row)
        path = self.folder / 'http-calls.json'
        write_json_atomic(path, self.calls)
        started = time.monotonic()
        try:
            response = original(client.with_options(timeout=remaining), params,
                                **{**kwargs, 'timeout': min(kwargs.get('timeout', remaining), remaining)})
            row['state'] = 'returned'
            usage = getattr(response, 'usage', None)
            row['usage'] = usage.model_dump() if usage is not None else None
            return response
        except Exception as exc:
            row['exception_type'] = type(exc).__name__
            status = getattr(exc, 'status_code', None)
            if status is not None:
                row.update(state='returned_error', http_status=status)
            raise
        finally:
            row['elapsed_seconds'] = round(time.monotonic() - started, 3)
            write_json_atomic(path, self.calls)


def evaluate(cases, output, *, live_case=None, timeout=600):
    validate_cases(cases)
    output = Path(output).resolve()
    if output.exists() or not 30 <= timeout <= 900:
        raise ValueError('New output directory and timeout 30..900 required')
    if live_case is not None and live_case not in {c['id'] for c in cases}:
        raise ValueError('Unknown live case')
    for case in cases:
        source = Path(case['source_run']).resolve()
        if source == output or source in output.parents or output in source.parents:
            raise ValueError('Output must be outside every source run')
    output.mkdir(parents=True)
    os.environ['PPT_STUDIO_DB_PATH'] = str(output / 'isolated.db')
    os.environ['PPT_STUDIO_RUNS_DIR'] = str(output / 'runtime-runs')
    identity = source_identity()
    write_json_atomic(output / 'source-manifest.json', identity)
    write_json_atomic(output / 'cases.json', cases)
    rows = []
    for case in cases:
        started = time.monotonic()
        folder, source = output / case['id'], Path(case['source_run']).resolve()
        row = {k: case[k] for k in ('id', 'course_id', 'page_id', 'provenance', 'source_note')}
        row.update(status='blocked', provider_calls=0, human_visual_acceptance='pending_review',
                   real_model_acceptance='not_run', cost=None)
        try:
            run_course_baseline(source, folder, [case['slide_id']])
            run, slide = folder / 'isolated-run', case['slide_id']
            doc = editor.load_editor(run, slide)
            request = {'expected_revision': doc['revision'], 'expected_audio_revision': editor.audio_revision(run, slide),
                       'scope': case['scope'], 'strategy': 'geometry_first',
                       'instruction': orchestration.OVERLAP_INSTRUCTION}
            trial = geometry.geometry_repair(run, slide, request)
            write_json_atomic(folder / 'geometry.json', trial)
            row.update(status=trial['status'], baseline_passed=trial['baseline']['passed'],
                       issue_groups=issue_groups(trial['baseline']),
                       geometry_seconds=trial['elapsed_seconds'],
                       sampled_checks=sum(a['sampling_mode'] == 'sampled' for a in trial['attempts']),
                       full_checks=sum(a['sampling_mode'] == 'output_frames' for a in trial['attempts']),
                       author_unchanged=trial['author_unchanged'])
            candidate = trial.get('candidate')
            if candidate:
                row['operations'] = candidate['request']['operations']
                row['frame_count'] = candidate['review']['frame_count']
                row['comparison'] = orchestration._comparison(run, trial['baseline'], candidate['review'])
            if case['id'] == live_case:
                if trial['status'] != 'needs_revision' or not fallback_eligible(trial['baseline']):
                    row['real_model_acceptance'] = 'not_needed_or_outside_arrow_text_task'
                else:
                    import json_llm_transport as transport
                    budget = LiveFallback(source, folder, timeout)
                    original = transport.receive_completion
                    transport.receive_completion = lambda client, params, **kw: budget.measured(original, client, params, **kw)
                    try:
                        result = orchestration.generate_repair(run, slide, request, budget.factory)
                        write_json_atomic(folder / 'live-result.json', result)
                        row['real_model_acceptance'] = result.get('status', 'unknown')
                        row['live_passed'] = bool(result.get('review', {}).get('passed'))
                    except Exception as exc:
                        row.update(real_model_acceptance='failed', live_error_code=getattr(exc, 'code', type(exc).__name__))
                    finally:
                        transport.receive_completion = original
                        row['provider_calls'] = len(budget.calls)
                        if any(c['state'] == 'unknown' for c in budget.calls):
                            row['real_model_acceptance'] = 'unknown'
            row['author_unchanged'] = editor.load_editor(run, slide) == doc
        except Exception as exc:
            row.update(status='blocked', error_code=getattr(exc, 'code', type(exc).__name__),
                       error_message=str(exc)[-1200:])
        manifest = folder / 'course-manifest.json'
        if manifest.is_file():
            files = json.loads(manifest.read_text(encoding='utf-8'))['files']
            row['source_unchanged'] = all((source / p).is_file() and sha256_file(source / p) == digest
                                          for p, digest in files.items())
        row['elapsed_seconds'] = round(time.monotonic() - started, 3)
        rows.append(row)
        write_json_atomic(folder / 'result.json', row)
        write_json_atomic(output / 'progress.json', {'cases': rows})
        print(json.dumps({k: v for k, v in row.items() if k not in ('comparison', 'issue_groups')}, ensure_ascii=False), flush=True)
    summary = {'cases': rows, 'metrics': metrics(rows),
               'code_unchanged': source_identity()['working_tree_sha256'] == identity['working_tree_sha256'],
               'provider_calls': sum(r['provider_calls'] for r in rows),
               'boundary': 'Original, archived, controlled and fixture denominators are separate. No author save or approval. No continuous-time or visual acceptance claim.'}
    write_json_atomic(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live-case', help='Explicitly authorize one fresh geometry-unsolved arrow/text case')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    evaluate(json.loads(args.spec.read_text(encoding='utf-8'))['cases'], args.output,
             live_case=args.live_case, timeout=args.timeout)


if __name__ == '__main__':
    main()
