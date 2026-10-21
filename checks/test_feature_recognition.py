"""Metric denominators, archived-contract fairness and sealed-input integrity."""
import json

import pytest

from scripts.evaluate_feature_recognition import digest, evaluate, metrics, prediction


def response(feature=False):
    return {'status': 'ready', 'issues': [], 'objects': [
        {'targetId': 'card', 'owner': 'code', 'assetMode': 'none', 'variant': None,
         'icon': None, 'appearance': 'fixture',
         'required_features': ['independent_illustration'] if feature else []}]}


def dataset(tmp_path, modern=True):
    root = tmp_path / 'dataset'
    root.mkdir()
    # No rendering/provider: this fixture tests protocol sealing only.
    (root / 'reference.png').write_bytes(b'fixed-image-fixture')
    payload = {'objects': [{'id': 'card', 'type': 'card'}]}
    schema = {'$defs': {'Allocation': {'properties': {'required_features': {
        'items': {'enum': ['independent_illustration'] if modern else ['label_value_stacked']}}}}}}
    request = {'user_prompt': json.dumps(payload), 'schema_hint': json.dumps(schema),
               'image_sha256': [digest(root / 'reference.png')]}
    for name, value in [('request.json', request), ('response.json', response()),
                        ('labels.json', {'authority': 'controlled_fixture', 'targets': [
                            {'targetId': 'card', 'feature': 'independent_illustration',
                             'expected': True, 'evidence': 'Declared controlled gold'}]})]:
        (root / name).write_text(json.dumps(value))
    case = {'id': 'fixture', 'course_id': 'fixture', 'page_id': 's', 'provenance': 'controlled_fixture'}
    for key, name in [('reference', 'reference.png'), ('request', 'request.json'),
                      ('response', 'response.json'), ('labels', 'labels.json')]:
        case[key] = {'path': name, 'sha256': digest(root / name)}
    path = root / 'dataset.json'
    path.write_text(json.dumps({'format': 'hps.feature_recognition_dataset', 'version': '0.1.0', 'cases': [case]}))
    return path


def test_unknown_and_ambiguous_never_disappear_from_denominators():
    result = metrics([{'expected': True, 'predicted': True}, {'expected': True, 'predicted': False},
                      {'expected': True, 'predicted': None}, {'expected': False, 'predicted': True},
                      {'expected': False, 'predicted': False}, {'expected': False, 'predicted': None},
                      {'expected': None, 'predicted': True}])
    assert (result['tp'], result['fn'], result['fp'], result['tn']) == (1, 1, 1, 1)
    assert result['false_negative_rate_on_decisive'] == 0.5
    assert result['miss_or_unresolved_over_all_positives'] == 2 / 3
    assert result['decision_coverage'] == 4 / 6 and result['excluded_ambiguous'] == 1
    assert metrics([])['false_negative_rate_on_decisive'] is None


@pytest.mark.parametrize('modern', [False, True])
def test_old_contract_missing_feature_is_unresolved_but_gap_remains_missed(tmp_path, modern):
    path = dataset(tmp_path, modern)
    result = evaluate(path, tmp_path / 'output')
    feature = result['by_provenance']['controlled_fixture']
    assert feature['fn'] == (1 if modern else 0)
    assert feature['unresolved_positive'] == (0 if modern else 1)
    assert result['capability_gap_by_provenance']['controlled_fixture']['fn'] == 1
    assert result['provider_calls'] == result['author_writes'] == 0
    with pytest.raises(ValueError, match='OUTPUT_MUST_BE_NEW'):
        evaluate(path, tmp_path / 'output')


@pytest.mark.parametrize('name', ['reference.png', 'request.json', 'response.json', 'labels.json'])
def test_every_evidence_file_is_verified_before_output(tmp_path, name):
    path = dataset(tmp_path)
    (path.parent / name).write_bytes(b'tampered')
    with pytest.raises(ValueError, match='SEALED_INPUT_CHANGED'):
        evaluate(path, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_path_escape_is_rejected(tmp_path):
    path = dataset(tmp_path)
    doc = json.loads(path.read_text())
    doc['cases'][0]['labels']['path'] = '../labels.json'
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='INVALID_DATASET_PATH'):
        evaluate(path, tmp_path / 'output')


def test_typed_unsupported_is_not_unproven_feature_recognition(tmp_path):
    path = dataset(tmp_path)
    raw = {'status': 'unsupported', 'objects': [], 'issues': [{
        'targetId': 'card', 'route': 'capabilities', 'requirement': 'unsupported_presentation',
        'evidence': 'A declared capability mismatch'}]}
    assert prediction(raw, 'card', 'independent_illustration')[0] is None
    doc = json.loads(path.read_text())
    (path.parent / 'response.json').write_text(json.dumps(raw))
    doc['cases'][0]['response']['sha256'] = digest(path.parent / 'response.json')
    path.write_text(json.dumps(doc))
    result = evaluate(path, tmp_path / 'output')
    assert result['by_provenance']['controlled_fixture']['unresolved_positive'] == 1
    assert result['capability_gap_by_provenance']['controlled_fixture']['tp'] == 1


def test_invalid_response_and_missing_target_are_unresolved():
    for raw in (None, {}, {'status': 'ready', 'objects': [], 'issues': []}):
        assert prediction(raw, 'card', 'independent_illustration')[0] is None
    assert prediction(response(True), 'card', 'independent_illustration')[0] is True
    assert prediction(response(), 'card', 'independent_illustration')[0] is False
