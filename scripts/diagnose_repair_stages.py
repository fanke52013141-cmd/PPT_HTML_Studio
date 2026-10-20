"""Explicit, gated live diagnostics: minimal JSON -> one image -> whole-page repair.

All providers use frozen project configuration and original adapters. No author
save, provider retry, approval or production configuration writes are allowed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from artifact_fingerprint import sha256_file, sha256_json  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from scripts.benchmark_capacity import run_course_baseline, source_identity  # noqa: E402
from scripts.compare_repair_runners import content, freeze_model  # noqa: E402

SLIDE = 'slide_003'
STAGES = ('minimal_json', 'single_image', 'full_page')
ORDERS = (('legacy', 'pi'), ('pi', 'legacy'), ('legacy', 'pi'))


def probe_valid(stage, result, minimum_tick):
    if not isinstance(result, dict):
        return False
    if stage == 'minimal_json':
        return set(result) == {'ok'} and result['ok'] is True
    if stage == 'single_image':
        return (set(result) == {'minimum_tick'} and type(result['minimum_tick']) in (int, float)
                and result['minimum_tick'] == minimum_tick)
    raise ValueError('Whole-page results require original checker validation')


def next_stage_allowed(rows):
    return len(rows) == 2 and all(r.get('passed') is True and not r.get('unknown_outcome') for r in rows)


def execute_arm(model, run_dir, folder, stage, arm, image, minimum_tick, request_timeout):
    import html_scene_editing as editor
    import html_scene_repair as repair
    from html_agent_models import AgentLimits
    from html_pi_json import PiJSON
    import json_llm_service as llm
    import json_llm_transport as transport

    limit = 2 if stage == 'full_page' else 1
    folder.mkdir(parents=True, exist_ok=True)
    before = editor.load_editor(run_dir, SLIDE)
    calls, inputs = [], []
    pi = PiJSON(model, folder / 'pi', limits=AgentLimits(max_model_calls=limit,
                max_tool_calls=limit, timeout_seconds=900)) if arm == 'pi' else None
    original_transport = transport.receive_completion
    started = time.monotonic()
    row = {'stage': stage, 'arm': arm, 'passed': False, 'status': 'started',
           'started_at_utc': datetime.now(timezone.utc).isoformat(), 'cost': None}
    write_json_atomic(folder / 'intent.json', row)

    def measured(client, params, **kwargs):
        if len(calls) >= limit:
            raise ValueError('Diagnostic request budget exhausted; no further submission')
        record = {'state': 'unknown', 'usage': None,
                  'parameters': {k: params[k] for k in ('model', 'max_tokens', 'temperature',
                                  'reasoning_effort', 'extra_body', 'response_format') if k in params}}
        calls.append(record)
        call_started = time.monotonic()
        try:
            remaining = min(request_timeout, 900 - (call_started - started))
            if remaining <= 0:
                record['state'] = 'not_submitted'
                raise TimeoutError('Local budget exhausted before submission')
            response = original_transport(client.with_options(timeout=min(remaining, 120)), params,
                                          **{**kwargs, 'timeout': remaining})
            record['state'] = 'returned'
            usage = getattr(response, 'usage', None)
            record['usage'] = usage.model_dump() if usage else None
            return response
        except Exception as exc:
            record.update(exception_type=type(exc).__name__, http_status=getattr(exc, 'status_code', None))
            if record['http_status'] is not None:
                record['state'] = 'returned_error'
            raise
        finally:
            record['elapsed_seconds'] = round(time.monotonic() - call_started, 3)
            write_json_atomic(folder / 'http-calls.json', calls)

    def progress(value):
        write_json_atomic(folder / 'progress.json', value)

    def generate(**kwargs):
        image_files = [Path(p) for p in kwargs.get('image_paths', [])]
        inputs.append({'sha256': sha256_json({'system': kwargs['system_prompt'], 'user': kwargs['user_prompt'],
                       'schema': kwargs['schema_hint'], 'images': [sha256_file(p) for p in image_files]}),
                       'system_bytes': len(kwargs['system_prompt'].encode()),
                       'user_bytes': len(kwargs['user_prompt'].encode()),
                       'image_count': len(image_files), 'image_bytes': sum(p.stat().st_size for p in image_files)})
        write_json_atomic(folder / 'inputs.json', inputs)
        upstream_progress = kwargs.pop('on_stream_progress', None)

        def combined(value):
            progress(value)
            if upstream_progress:
                upstream_progress(value)

        kwargs.update(stream_output=True, on_stream_progress=combined)
        if pi:
            return pi(**kwargs, request_timeout=request_timeout)
        remaining = min(request_timeout, 900 - (time.monotonic() - started))
        if remaining <= 0:
            raise TimeoutError('Local arm budget exhausted')
        return llm.generate_json_with_configured_llm(**kwargs, model_binding=model, request_timeout=remaining)

    generate.supports_stream_progress = True
    transport.receive_completion = measured
    try:
        if stage == 'full_page':
            result = repair.generate_repair(run_dir, SLIDE, {
                'expected_revision': before['revision'], 'expected_audio_revision': editor.audio_revision(run_dir, SLIDE),
                'scope': ['obj-card-2'], 'sampling_mode': 'output_frames', 'fps': 30, 'overlap_policy': 'registered',
                'instruction': '修复箭头经过文字区域的问题。仅使用scope内对象的set_presentation调整布局；保持所有文字内容、字号、样式、关系端点、图表数据、动作及音频绑定；禁止新增删除对象。交由原检查器验证。'}, generate)
            preserved = ('scene' in result and content(result['scene']) == content(before['scene'])
                         and result['binding'] == before['binding'])
            layout_only = all(op['kind'] == 'set_presentation' for op in result.get('request', {}).get('operations', []))
            row.update(passed=bool(result.get('review', {}).get('passed') and preserved and layout_only),
                       status=result.get('stop_reason') or result.get('status'),
                       preserved=preserved, layout_only=layout_only,
                       frame_count=result.get('review', {}).get('frame_count'),
                       issue_count=len(result.get('review', {}).get('issues', [])))
        else:
            user = ('Return exactly {"ok": true}.' if stage == 'minimal_json' else
                    'Read the attached chart. Return its lowest printed temperature-axis tick label as '
                    '{"minimum_tick": number}. Read the printed tick, not the curve endpoint.')
            result = generate(system_prompt='Return only the requested JSON object, with no explanation.',
                              user_prompt=user, schema_hint='{"ok":true}' if stage == 'minimal_json' else '{"minimum_tick":number}',
                              image_paths=[] if stage == 'minimal_json' else [str(image)],
                              run_dir=str(run_dir), artifact_prefix=stage)
            row.update(passed=probe_valid(stage, result, minimum_tick), status='returned')
        write_json_atomic(folder / 'output.json', result)
    except Exception as exc:
        row.update(status=getattr(exc, 'code', type(exc).__name__), exception_type=type(exc).__name__)
    finally:
        transport.receive_completion = original_transport
    trace_path = folder / 'progress.json'
    trace = json.loads(trace_path.read_text(encoding='utf-8')) if trace_path.exists() else {}
    unknown = (row['status'] in ('timeout', 'provider_error', 'runner_error') if pi else
               any(c['state'] == 'unknown' for c in calls))
    if not pi and trace.get('finish_reason') == 'length' and trace.get('failure_reason') == 'output_limit':
        unknown = False
        row['status'] = 'output_limit'
    row.update(elapsed_seconds=round(time.monotonic() - started, 3), decision_calls=len(inputs),
               model_calls=pi.usage['model_calls'] if pi else sum(c['state'] != 'not_submitted' for c in calls),
               usage=pi.usage if pi else [c['usage'] for c in calls], unknown_outcome=unknown,
               author_unchanged=editor.load_editor(run_dir, SLIDE) == before,
               first_business_input_sha256=inputs[0]['sha256'] if inputs else None, stream=trace)
    if not row['author_unchanged']:
        row['passed'] = False
    write_json_atomic(folder / 'result.json', row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
    return row


def run(source, output):
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
    protocol = {'stages': STAGES, 'orders': ORDERS, 'model': model.summary(),
                'pi_profile': execution_profile(model), 'request_timeout_seconds': 600,
                'legacy_read_timeout_seconds': 120, 'pi_sdk_timing': 'host-observed SDK events, not network first byte',
                'max_total_model_calls': 8, 'calls_per_arm': [1, 1, 2],
                'gate': 'Both arms must pass; unknown stops remaining batch, no replay.',
                'boundary': 'Adapter diagnostics, not full Pi autonomous workflow. No author save or human approval.'}
    write_json_atomic(output / 'protocol.json', protocol)
    run_course_baseline(source, output / 'baseline', [SLIDE], 'output_frames')
    base = output / 'baseline/isolated-run'
    report = json.loads((output / 'baseline' / SLIDE / 'temporal-review.json').read_text(encoding='utf-8'))
    image = base / report['screenshots'][-1]['file']
    scene = json.loads((base / f'planning/html_visual/scene-{SLIDE}.json').read_text(encoding='utf-8'))
    minimum_tick = next(n['min'] for n in scene['nodes'] if n['id'] == 'obj-chart')
    rows = []
    blocked = None
    for stage, order in zip(STAGES, ORDERS, strict=True):
        stage_rows = []
        for arm in order:
            if blocked:
                rows.append({'stage': stage, 'arm': arm, 'status': 'not_run', 'blocked_by': blocked})
                continue
            folder = output / stage / arm
            run_dir = folder / 'isolated-run'
            shutil.copytree(base, run_dir, ignore=shutil.ignore_patterns('repair-evidence', 'records', 'builds', 'editor-history'))
            local_image = run_dir / 'probe.png'
            shutil.copyfile(image, local_image)
            row = execute_arm(model, run_dir, folder, stage, arm, local_image, minimum_tick, 600)
            rows.append(row)
            stage_rows.append(row)
            if row['unknown_outcome']:
                blocked = f'{stage}/{arm}:unknown_outcome'
            write_json_atomic(output / 'report.json', {'protocol': protocol, 'records': rows, 'blocked_by': blocked})
        if not blocked and not next_stage_allowed(stage_rows):
            blocked = f'{stage}:gate_failed'
    manifest = json.loads((output / 'baseline/course-manifest.json').read_text(encoding='utf-8'))
    identity = json.loads((output / 'baseline/source-manifest.json').read_text(encoding='utf-8'))
    result = {'protocol': protocol, 'records': rows, 'blocked_by': blocked,
              'source_unchanged': all(sha256_file(source / p) == digest for p, digest in manifest['files'].items()),
              'code_unchanged': source_identity()['working_tree_sha256'] == identity['working_tree_sha256']}
    write_json_atomic(output / 'report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if args.live:
        run(args.source_run, args.output)
    else:
        print(json.dumps({'live': False, 'stages': STAGES, 'orders': ORDERS, 'max_calls': 8}))


if __name__ == '__main__':
    main()
