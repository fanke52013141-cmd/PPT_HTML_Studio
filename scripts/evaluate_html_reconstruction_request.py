"""Independent same-input reconstruction request replay; never saves author HTML."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sqlite3
import time
from types import SimpleNamespace
from evaluate_html_design_review import ROOT, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', required=True, type=Path)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live:
        print('One independent diagnostic request; no production continuation or author write.')
        return
    out = args.evaluation.resolve()
    result_path = out / 'reconstruction-request-replay.json'
    if result_path.exists():
        raise ValueError('EXISTING_ATTEMPT_MUST_NOT_BE_RETRIED')
    run = out / 'isolated-run'
    os.environ['PPT_STUDIO_DB_PATH'] = str(out / 'isolated.db')
    os.environ['PPT_STUDIO_RUNS_DIR'] = str(out / 'isolated-runs')
    from credential_store import CredentialDependencies, configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies, configure_model_connection_dependencies
    from project_model_binding_service import freeze_project_models
    from pipeline_lifecycle import write_json_atomic
    from html_runtime_skills import load_runtime_skill
    from html_design_agent import component_context
    from json_llm_service import generate_json_with_configured_llm
    from artifact_fingerprint import sha256_file
    def readonly(*_):
        raise ValueError('Read only evaluation configuration')
    configure_credential_dependencies(CredentialDependencies(
        read_store=lambda: read(ROOT / 'data/credentials.json'), write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(
        read_registry=lambda: read(ROOT / 'data/model_connections.json'), write_registry=readonly))
    with sqlite3.connect((ROOT / 'data/projects.db').as_uri() + '?mode=ro', uri=True) as db:
        settings = dict(db.execute("select key,value from settings where key in ('html_visual_connection_id','html_planning_connection_id')"))
    model = freeze_project_models(SimpleNamespace(run_dir=str(run), account_id='default',
        creation_config_package_id=None, creation_config_snapshot_json=None), setting=settings.get).text.require_ready()
    archived = read(args.request)
    payload = json.loads(archived['user_prompt'])
    scene = read(out / 'candidate-scene.json')
    scene['nodes'] = payload['objects']
    payload['capabilities'] = component_context(scene, ROOT)['capabilities']
    skill = load_runtime_skill(ROOT, stage='design_reconstruction', mode='runtime_skill')
    record = {'state':'intent', 'scope':'independent request replay, not full reconstruction',
              'author_writes':0, 'automatic_retry':False, 'model':model.summary(),
              'reference_sha256':sha256_file(run / 'reference.png'), 'runtime_skill':skill.identity,
              'reasoning_effort_override':'low', 'request_timeout_seconds':600}
    write_json_atomic(result_path, record)
    started = time.monotonic()
    try:
        record['response'] = generate_json_with_configured_llm(system_prompt=skill.fragment,
            user_prompt=json.dumps(payload, ensure_ascii=False), schema_hint=archived['schema_hint'],
            run_dir=str(run), artifact_prefix='diagnostic-reconstruction-request',
            image_paths=[str(run / 'reference.png')], request_timeout=600,
            reasoning_effort_override='low', model_binding=model, stream_output=True)
        record['state'] = 'returned'
    except Exception as error:
        record.update(state='unknown', error_type=type(error).__name__)
        raise
    finally:
        record['elapsed_seconds'] = round(time.monotonic()-started, 3)
        write_json_atomic(result_path, record)
    print(json.dumps({'state':record['state'], 'elapsed_seconds':record['elapsed_seconds'],
                      'response_status':record['response'].get('status')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
