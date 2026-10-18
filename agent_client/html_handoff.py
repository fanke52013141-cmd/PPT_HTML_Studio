"""Portable external-Agent exchange over existing registered API operations.

No model execution, credentials in packets, database access or approval writes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, model_validator
from agent_client.client import AgentClient
from agent_contract.capabilities import CAPABILITIES
from agent_contract.versions import get_contract_hash
from html_motion_activity import motion_activity
from html_repair_models import RepairOperation, RepairRequest


class ExternalResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    format: Literal['hps.html.external_result'] = 'hps.html.external_result'
    version: Literal['0.1.0'] = '0.1.0'
    task_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    status: Literal['proposed', 'needs_input', 'unsupported']
    message: str = Field(min_length=1, max_length=4000)
    operations: list[RepairOperation] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def check_status(self):
        if bool(self.operations) != (self.status == 'proposed'):
            raise ValueError('Only proposed results require operations')
        return self


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def call(client, capability_id, project_id, slide_id, body=None):
    cap = next(c for c in CAPABILITIES if c.id == capability_id)
    if body is not None:
        body = cap.request_model.model_validate(body).model_dump(mode='json')
    return client._request(cap.agent_api_method, cap.agent_api_path.format(
        project_id=quote(project_id, safe=''), slide_id=quote(slide_id, safe='')), body=body, timeout=300)


def export_task(client, project_id, slide_id, goal, scope):
    if not goal.strip() or len(goal) > 4000 or not 1 <= len(scope) <= 40 or len(set(scope)) != len(scope):
        raise ValueError('Goal and unique bounded scope required')
    meta = client.get_meta()
    if meta['contract_hash'] != get_contract_hash():
        raise ValueError('CONTRACT_CHANGED: use a matching client')
    doc = call(client, 'html_editor.read', project_id, slide_id)
    if not set(scope) <= {n['id'] for n in doc['scene']['nodes']}:
        raise ValueError('Scope includes missing objects')
    manual = doc.get('manual') or {}
    if manual and 'protected_paths' not in manual:
        raise ValueError('Legacy manual protection needs current server normalization')
    preview = call(client, 'html_editor.preview', project_id, slide_id, {
        'scene': doc['scene'], 'binding': doc['binding'], 'expected_revision': doc['revision'],
        'expected_audio_revision': doc['audio_revision']})
    if preview['clock'] != 'audio_timeline':
        raise ValueError('REAL_AUDIO_TIMING_REQUIRED')
    packet = {'format': 'hps.html.external_task', 'version': '0.1.0',
              'project_id': project_id, 'slide_id': slide_id, 'goal': goal, 'scope': scope,
              'contract_hash': meta['contract_hash'], 'expected_revision': doc['revision'],
              'audio_revision': doc['audio_revision'],
              'context': {'scene': doc['scene'], 'binding': doc['binding'],
                          'protected_paths': manual.get('protected_paths', []),
                          'bound_scene': preview['scene'], 'timing': preview['timing']},
              'motion_activity': motion_activity(preview['scene']),
              'operation_schema': RepairOperation.model_json_schema(),
              'result_schema': ExternalResult.model_json_schema(),
              'limits': {'max_operations': 20, 'source': 'ai', 'paid_requests': 0,
                         'approval': 'human_current_report_required', 'automatic_save': False}}
    return {**packet, 'task_id': digest(packet)}


def repair_request(client, packet, result):
    packet = copy.deepcopy(packet)
    task_id = packet.pop('task_id')
    if packet.get('format') != 'hps.html.external_task' or packet.get('version') != '0.1.0' or digest(packet) != task_id:
        raise ValueError('TASK_CHANGED')
    result = ExternalResult.model_validate(result)
    if result.task_id != task_id:
        raise ValueError('RESULT_TASK_MISMATCH')
    if result.status != 'proposed':
        raise ValueError(f'{result.status}: {result.message}')
    if packet['contract_hash'] != get_contract_hash() or client.get_meta()['contract_hash'] != packet['contract_hash']:
        raise ValueError('CONTRACT_CHANGED')
    current = call(client, 'html_editor.read', packet['project_id'], packet['slide_id'])
    if current['revision'] != packet['expected_revision']:
        raise ValueError('REVISION_CHANGED: export a new task')
    if current['audio_revision'] != packet['audio_revision']:
        raise ValueError('AUDIO_CHANGED: export a new task')
    if any(o.targetId not in packet['scope'] for o in result.operations):
        raise ValueError('REPAIR_SCOPE')
    body = RepairRequest(expected_revision=packet['expected_revision'], source='ai',
                         expected_audio_revision=packet['audio_revision'],
                         scope=packet['scope'], operations=result.operations).model_dump(mode='json')
    return body


def preview_result(client, packet, result):
    body = repair_request(client, packet, result)
    preview = call(client, 'html_repair.preview', packet['project_id'], packet['slide_id'], body)
    return {'format': 'hps.html.external_preview', 'version': '0.1.0',
            'task_id': packet['task_id'], 'result_hash': digest(result), 'preview': preview}


def save_result(client, packet, result, receipt):
    body = repair_request(client, packet, result)
    if (receipt.get('format') != 'hps.html.external_preview' or receipt.get('version') != '0.1.0'
            or receipt.get('task_id') != packet['task_id'] or receipt.get('result_hash') != digest(result)
            or receipt['preview'].get('status') != 'candidate' or not receipt['preview']['review']['passed']):
        raise ValueError('VALID_PREVIEW_REQUIRED')
    return call(client, 'html_repair.save', packet['project_id'], packet['slide_id'],
                {**body, 'candidate_key': receipt['preview']['candidate_key']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=None)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    for field in ('project', 'slide', 'goal'):
        export.add_argument('--' + field, required=True)
    export.add_argument('--scope', nargs='+', required=True)
    for command in ('preview', 'save'):
        sub = commands.add_parser(command)
        sub.add_argument('--task', type=Path, required=True)
        sub.add_argument('--result', type=Path, required=True)
        if command == 'save':
            sub.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    client = AgentClient(**({'base_url': args.base_url} if args.base_url else {}))
    def read(file):
        return json.loads(file.read_text(encoding='utf-8-sig'))
    if args.command == 'export':
        output = export_task(client, args.project, args.slide, args.goal, args.scope)
    elif args.command == 'preview':
        output = preview_result(client, read(args.task), read(args.result))
    else:
        output = save_result(client, read(args.task), read(args.result), read(args.receipt))
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
