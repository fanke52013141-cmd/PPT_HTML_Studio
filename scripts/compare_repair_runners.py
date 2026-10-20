"""Paired live Legacy/Pi JSON-adapter repair evaluation, never author save.

Original generate/preview and 30fps checks judge both arms. Full Pi unattended
tool workflows and whole-page production are outside this experiment.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from artifact_fingerprint import sha256_file, sha256_json  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from scripts.benchmark_capacity import run_course_baseline, source_identity  # noqa: E402

CASES = {'slide_001': ['obj-anchor-label'], 'slide_003': ['obj-card-2']}


def schedule(repeats, slides=None):
    return [(slide, repeat + 1, arm) for repeat in range(repeats)
            for index, slide in enumerate(CASES)
            if slides is None or slide in slides
            for arm in (('legacy', 'pi') if (repeat + index) % 2 == 0 else ('pi', 'legacy'))]


def aggregate(records, planned):
    from statistics import median
    metrics = {}
    for arm in ('legacy', 'pi'):
        rows = [r for r in records if r['arm'] == arm]
        denominator = sum(item[2] == arm for item in planned)
        metrics[arm] = {'planned': denominator, 'attempted': len(rows),
                        'passed': sum(r.get('passed', False) for r in rows),
                        'not_run': denominator - len(rows),
                        'attempted_pass_rate': sum(r.get('passed', False) for r in rows) / len(rows) if rows else None,
                        'median_elapsed_seconds_all_attempts': median(r['elapsed_seconds'] for r in rows) if rows else None,
                        'model_calls': sum(r['model_calls'] for r in rows), 'cost': None}
    pairs = []
    for slide, repeat in dict.fromkeys((s, n) for s, n, _ in planned):
        rows = {r['arm']: r for r in records if r['slide'] == slide and r['repeat'] == repeat}
        comparable = (len(rows) == 2 and bool(rows['legacy'].get('first_input_sha256'))
                      and rows['legacy']['first_input_sha256'] == rows['pi'].get('first_input_sha256'))
        pairs.append({'slide': slide, 'repeat': repeat, 'completed': len(rows) == 2,
                      'same_first_business_input': comparable,
                      'legacy_passed': rows.get('legacy', {}).get('passed'),
                      'pi_passed': rows.get('pi', {}).get('passed')})
    return {'metrics': metrics, 'pairs': pairs,
            'scope': 'Same repair host and business inputs; actual SDK transport envelopes differ. No default-runner decision from this small sample.'}


def freeze_model(source):
    from credential_store import CredentialDependencies, configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies, configure_model_connection_dependencies
    from project_model_binding_service import freeze_project_models

    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    def readonly(*_):
        raise ValueError('Read-only configuration')

    configure_credential_dependencies(CredentialDependencies(
        read_store=lambda: read(ROOT / 'data/credentials.json'), write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(
        read_registry=lambda: read(ROOT / 'data/model_connections.json'), write_registry=readonly))
    with sqlite3.connect((ROOT / 'data/projects.db').as_uri() + '?mode=ro', uri=True) as db:
        settings = dict(db.execute('select key,value from settings'))
    project = SimpleNamespace(run_dir=str(source), account_id='default',
                              creation_config_package_id=None, creation_config_snapshot_json=None)
    return freeze_project_models(project, setting=settings.get).text.require_ready()


def content(scene):
    scene = copy.deepcopy(scene)
    for node in scene['nodes']:
        node.pop('presentation', None)
    return scene


def run(source, output, repeats, slides=None, request_timeout=180):
    source, output = source.resolve(), output.resolve()
    if output.exists() or source in output.parents or output in source.parents:
        raise ValueError('Fresh output outside original run required')
    os.environ['PPT_STUDIO_DB_PATH'] = str(output / 'isolated.db')
    os.environ['PPT_STUDIO_RUNS_DIR'] = str(output / 'runtime-runs')
    model = freeze_model(source)
    from html_agent_jobs import ready, execution_profile
    ready(model)
    from database import init_db
    init_db()
    import html_scene_editing as editor
    import html_scene_repair as repair
    from html_pi_json import PiJSON
    from html_agent_models import AgentLimits
    import json_llm_service as llm
    import json_llm_transport as transport

    planned = schedule(repeats, slides)
    arm_timeout = 600 if request_timeout == 180 else 900
    output.mkdir(exist_ok=True)
    protocol = {'model': model.summary(), 'schedule': planned, 'max_model_calls_per_arm': 2,
                'request_timeout_seconds': request_timeout, 'arm_timeout_seconds': arm_timeout,
                'output_tokens': model.max_tokens, 'temperature': model.temperature,
                'sampling_mode': 'output_frames', 'fps': 30,
                'pi_profile': execution_profile(model), 'human_visual_acceptance': 'pending_review',
                'legacy_request_options': llm._request_options(model.model, model),
                'transport_difference': 'Legacy JSON response_format and reasoning_effort versus Pi submit_json tool and native thinking payload; not byte-identical HTTP envelopes.',
                'stop_policy': 'Stop entire batch after unknown provider outcome; no replay, failed attempts retained.'}
    write_json_atomic(output / 'protocol.json', protocol)
    run_course_baseline(source, output / 'baseline', list(dict.fromkeys(s for s, _, _ in planned)), 'output_frames')
    records = []
    original_transport = transport.receive_completion
    for slide, repeat, arm in planned:
        folder = output / f'{slide}-r{repeat}-{arm}'
        run_dir = folder / 'isolated-run'
        shutil.copytree(output / 'baseline/isolated-run', run_dir,
                        ignore=shutil.ignore_patterns('repair-evidence', 'records', 'builds', 'editor-history'))
        doc = editor.load_editor(run_dir, slide)
        request = {'expected_revision': doc['revision'], 'expected_audio_revision': editor.audio_revision(run_dir, slide),
                   'scope': CASES[slide], 'sampling_mode': 'output_frames', 'fps': 30, 'overlap_policy': 'registered',
                   'instruction': '修复箭头经过文字区域的问题。仅使用scope内对象的set_presentation调整布局；保持所有文字内容、字号、样式、关系端点、图表数据、动作及音频绑定；禁止新增删除对象。不要猜测成功，交由原检查器验证。'}
        calls, business = [], []
        pi = PiJSON(model, folder / 'pi', limits=AgentLimits(max_model_calls=2, max_tool_calls=2, timeout_seconds=arm_timeout)) if arm == 'pi' else None

        def measured(client, params, **kwargs):
            if len(calls) >= 2:
                raise ValueError('Experiment HTTP request budget exhausted')
            row = {'state': 'unknown', 'usage': None,
                   'parameters': {k: params[k] for k in ('model', 'temperature', 'max_tokens', 'reasoning_effort', 'extra_body', 'response_format') if k in params}}
            calls.append(row)
            call_started = time.monotonic()
            try:
                remaining = min(request_timeout, arm_timeout - (call_started - started))
                if remaining <= 0:
                    row['state'] = 'not_submitted'
                    raise TimeoutError('Experiment arm budget exhausted before submission')
                # Every physical attempt, including format fallback/JSON repair,
                # uses the remaining shared arm budget and no SDK retry.
                response = original_transport(client.with_options(timeout=remaining), params,
                                              **{**kwargs, 'timeout': remaining})
                row['state'] = 'returned'
                usage = getattr(response, 'usage', None)
                row['usage'] = usage.model_dump() if usage is not None else None
                return response
            except Exception as exc:
                row.update(exception_type=type(exc).__name__, http_status=getattr(exc, 'status_code', None))
                if row['http_status'] is not None:
                    row['state'] = 'returned_error'
                raise
            finally:
                row['elapsed_seconds'] = round(time.monotonic() - call_started, 3)
                write_json_atomic(folder / 'http-calls.json', calls)

        def generate(**kwargs):
            identity = {'system': kwargs['system_prompt'], 'user': kwargs['user_prompt'],
                        'schema': kwargs['schema_hint'], 'images': [sha256_file(Path(p)) for p in kwargs.get('image_paths', [])]}
            business.append(sha256_json(identity))
            write_json_atomic(folder / 'business-inputs.json', business)
            if pi:
                return pi(**kwargs, request_timeout=request_timeout)
            remaining = min(request_timeout, arm_timeout - (time.monotonic() - started))
            if remaining <= 0:
                raise TimeoutError('Experiment arm budget exhausted')
            return llm.generate_json_with_configured_llm(**kwargs, model_binding=model, request_timeout=remaining)

        generate.supports_stream_progress = True

        row = {'slide': slide, 'repeat': repeat, 'arm': arm, 'passed': False, 'status': 'started', 'cost': None}
        write_json_atomic(folder / 'intent.json', row)
        started = time.monotonic()
        transport.receive_completion = measured
        try:
            result = repair.generate_repair(run_dir, slide, request, generate)
            write_json_atomic(folder / 'candidate.json', result)
            row['status'] = result.get('stop_reason') or result.get('status')
            if result.get('review', {}).get('passed'):
                preserved = content(result['scene']) == content(doc['scene']) and result['binding'] == doc['binding']
                layout_only = all(op['kind'] == 'set_presentation' for op in result['request']['operations'])
                row.update(passed=preserved and layout_only, preserved=preserved, layout_only=layout_only,
                           issue_count=len(result['review']['issues']), frame_count=result['review']['frame_count'])
        except Exception as exc:
            row.update(status=getattr(exc, 'code', type(exc).__name__), exception_type=type(exc).__name__)
        finally:
            transport.receive_completion = original_transport
        row.update(elapsed_seconds=round(time.monotonic() - started, 3), decision_calls=len(business),
                   first_input_sha256=business[0] if business else None,
                   model_calls=pi.usage['model_calls'] if pi else sum(c['state'] != 'not_submitted' for c in calls),
                   usage=pi.usage if pi else [c['usage'] for c in calls],
                   author_unchanged=editor.load_editor(run_dir, slide) == doc,
                   unknown_outcome=any(c['state'] == 'unknown' for c in calls) if not pi else row['status'] in ('timeout', 'provider_error'))
        if not row['author_unchanged']:
            row['passed'] = False
        records.append(row)
        write_json_atomic(folder / 'result.json', row)
        write_json_atomic(output / 'report.json', {**aggregate(records, planned), 'records': records})
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if row['unknown_outcome']:
            break
    manifest = json.loads((output / 'baseline/course-manifest.json').read_text(encoding='utf-8'))
    identity = json.loads((output / 'baseline/source-manifest.json').read_text(encoding='utf-8'))
    report = {**aggregate(records, planned), 'records': records,
              'source_unchanged': all(sha256_file(source / p) == digest for p, digest in manifest['files'].items()),
              'code_unchanged': source_identity()['working_tree_sha256'] == identity['working_tree_sha256']}
    write_json_atomic(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, choices=(1, 2), default=2)
    parser.add_argument('--slides', nargs='+', choices=tuple(CASES), default=list(CASES))
    parser.add_argument('--request-timeout', type=int, choices=(180, 600), default=180)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({'schedule': schedule(args.repeats, args.slides), 'max_calls': 2 * len(schedule(args.repeats, args.slides)),
                          'request_timeout_seconds': args.request_timeout, 'live': False}))
        return
    run(args.source_run, args.output, args.repeats, args.slides, args.request_timeout)


if __name__ == '__main__':
    main()
