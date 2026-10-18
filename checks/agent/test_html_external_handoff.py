import copy
import json
import pytest
from agent_client.html_handoff import export_task, preview_result, save_result, ExternalResult
from agent_contract.versions import get_contract_hash


class Client:
    def __init__(self):
        self.calls = []
        self.contract = get_contract_hash()
        self.doc = {'revision': 6, 'audio_revision': 'a'*64, 'binding': None,
                    'scene': {'id': 'slide_001', 'durationMs': 10000, 'nodes': [{'id': 'title'}],
                              'motion': [{'actionId': 'entry', 'targetId': 'title', 'type': 'enter',
                                          'startMs': 0, 'durationMs': 500}]},
                    'manual': {'protected_paths': [['scene', 'nodes', 'title', 'text']]}}

    def get_meta(self):
        return {'contract_hash': self.contract}

    def _request(self, method, path, body=None, **kwargs):
        self.calls.append((method, path, body))
        if path.endswith('/editor'):
            return copy.deepcopy(self.doc)
        if path.endswith('/editor/preview'):
            return {'clock': 'audio_timeline', 'scene': self.doc['scene'], 'timing': {}}
        if path.endswith('/repair/preview'):
            return {'candidate_key': 'b'*64, 'review': {'passed': True}, 'status': 'candidate'}
        if path.endswith('/repair/save'):
            assert body['source'] == 'ai' and body['expected_audio_revision'] == 'a'*64
            return {'revision': 7, 'changed': True}
        pytest.fail('Unexpected route: ' + path)


@pytest.fixture
def exchange():
    client = Client()
    packet = export_task(client, 'p', 'slide_001', 'Spread existing animation across narration', ['title'])
    result = {'format': 'hps.html.external_result', 'version': '0.1.0', 'task_id': packet['task_id'],
              'status': 'proposed', 'message': 'Longer entry', 'operations': [
                  {'kind': 'set_motion', 'targetId': 'title', 'action': 'enter',
                   'actionId': 'entry', 'values': {'durationMs': 1200}}]}
    return client, packet, result


def test_round_trip_uses_original_guards_and_never_runs_a_provider(exchange):
    client, packet, result = exchange
    assert packet['context']['protected_paths'] == client.doc['manual']['protected_paths']
    assert packet['limits']['paid_requests'] == 0
    receipt = preview_result(client, packet, result)
    assert not any(c[1].endswith('/save') for c in client.calls)
    assert save_result(client, packet, result, receipt)['revision'] == 7
    assert all('/editor' in c[1] or '/repair/' in c[1] for c in client.calls)
    assert 'Authorization' not in json.dumps(packet)


@pytest.mark.parametrize('field,value', [('revision', 7), ('audio_revision', 'c'*64)])
def test_changed_scene_or_audio_stops_before_repair(exchange, field, value):
    client, packet, result = exchange
    client.doc[field] = value
    with pytest.raises(ValueError, match='CHANGED'):
        preview_result(client, packet, result)
    assert not any('/repair/' in c[1] for c in client.calls)


def test_contract_drift_and_tampered_packet_stop(exchange):
    client, packet, result = exchange
    packet['scope'].append('other')
    with pytest.raises(ValueError, match='TASK_CHANGED'):
        preview_result(client, packet, result)
    packet['scope'].pop()
    client.contract = 'bad'
    with pytest.raises(ValueError, match='CONTRACT_CHANGED'):
        preview_result(client, packet, result)


def test_scope_source_and_wrong_task_are_rejected(exchange):
    client, packet, result = exchange
    result['operations'][0]['targetId'] = 'other'
    with pytest.raises(ValueError, match='REPAIR_SCOPE'):
        preview_result(client, packet, result)
    result['operations'][0]['targetId'] = 'title'
    result['source'] = 'human'
    with pytest.raises(ValueError):
        preview_result(client, packet, result)
    result.pop('source')
    result['task_id'] = 'd'*64
    with pytest.raises(ValueError, match='RESULT_TASK_MISMATCH'):
        preview_result(client, packet, result)


def test_unpreviewed_or_changed_result_cannot_save(exchange):
    client, packet, result = exchange
    receipt = preview_result(client, packet, result)
    result['operations'][0]['values']['durationMs'] = 1500
    with pytest.raises(ValueError, match='VALID_PREVIEW_REQUIRED'):
        save_result(client, packet, result, receipt)
    assert not any(c[1].endswith('/save') for c in client.calls)


@pytest.mark.parametrize('status', ['needs_input', 'unsupported'])
def test_unable_result_does_not_claim_success_or_call_repair(exchange, status):
    client, packet, result = exchange
    result.update(status=status, operations=[])
    ExternalResult.model_validate(result)
    with pytest.raises(ValueError, match=status):
        preview_result(client, packet, result)
    assert not any('/repair/' in c[1] for c in client.calls)
