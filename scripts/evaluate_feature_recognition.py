"""Score sealed design-understanding responses against separate visual labels.

Provider-free: archived replay and future captured model responses use the same
scorer. No prompt execution, author mutation, approval, or inferred prose labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from html_design_agent import Understanding  # noqa: E402

# v0.2.0 separates the code object that owns an illustration from containers,
# registered icons, annotations and text, and requires an explicit reason when a
# target is excluded as ambiguous.
OWNERSHIP = frozenset({'image', 'container', 'icon', 'annotation', 'text', 'ambiguous'})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sealed_file(root, record):
    relative = record['path']
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError('INVALID_DATASET_PATH')
    parts = relative.split('/')
    if any(p in ('', '.', '..') for p in parts):
        raise ValueError('INVALID_DATASET_PATH')
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or digest(path) != record['sha256']:
        raise ValueError('SEALED_INPUT_CHANGED')
    return path


def prediction(response, target, feature, *, require_observations=False, expected_targets=None):
    """Typed targeted stops are abstentions, not proof of feature recognition."""
    if response is None:
        return None, 'not_returned'
    try:
        result = Understanding.model_validate(response)
    except ValueError:
        return None, 'invalid_response'
    if result.feature_observations is not None:
        observations = result.feature_observations
        ids = [r.targetId for r in observations]
        if (len(ids) != len(set(ids)) or target not in ids
                or (expected_targets is not None and set(ids) != set(expected_targets))):
            return None, 'incomplete_feature_observations'
        item = next(r for r in observations if r.targetId == target and r.feature == feature)
        return ({'present': True, 'absent': False, 'uncertain': None}[item.presence],
                'explicit_observation_' + item.presence)
    if require_observations:
        return None, 'required_feature_observations_missing'
    if result.status != 'ready' or result.issues:
        return None, 'unsupported_or_issue_requires_feature_verification'
    ids = [r.targetId for r in result.objects]
    if len(ids) != len(set(ids)) or target not in ids:
        return None, 'missing_or_duplicate_allocation'
    item = next(r for r in result.objects if r.targetId == target)
    return feature in item.required_features, 'explicit_feature' if feature in item.required_features else 'feature_omitted'


def metrics(rows):
    scored = [r for r in rows if r['expected'] is not None]
    tp = sum(r['expected'] is True and r['predicted'] is True for r in scored)
    fn = sum(r['expected'] is True and r['predicted'] is False for r in scored)
    tn = sum(r['expected'] is False and r['predicted'] is False for r in scored)
    fp = sum(r['expected'] is False and r['predicted'] is True for r in scored)
    positive = sum(r['expected'] is True for r in scored)
    negative = len(scored) - positive
    unknown_positive = sum(r['expected'] is True and r['predicted'] is None for r in scored)
    unknown_negative = sum(r['expected'] is False and r['predicted'] is None for r in scored)
    ratio = lambda a, b: a / b if b else None
    return {'labeled_targets': len(scored), 'excluded_ambiguous': len(rows) - len(scored),
            'positives': positive, 'negatives': negative, 'tp': tp, 'fn': fn, 'tn': tn, 'fp': fp,
            'unresolved_positive': unknown_positive, 'unresolved_negative': unknown_negative,
            'false_negative_rate_on_decisive': ratio(fn, tp + fn),
            'false_positive_rate_on_decisive': ratio(fp, tn + fp),
            'confirmed_recall_over_all_positives': ratio(tp, positive),
            'miss_or_unresolved_over_all_positives': ratio(fn + unknown_positive, positive),
            'decision_coverage': ratio(tp + fn + tn + fp, len(scored))}


def gap_prediction(response, target):
    if response is None:
        return None
    try:
        parsed = Understanding.model_validate(response)
    except ValueError:
        return None
    if parsed.status == 'ready' and not parsed.issues:
        ids = [r.targetId for r in parsed.objects]
        return False if ids.count(target) == 1 and len(ids) == len(set(ids)) else None
    if parsed.status == 'unsupported' and not parsed.objects and any(
        r.targetId == target and r.requirement == 'unsupported_presentation' for r in parsed.issues
    ):
        return True
    return None


def evaluate(dataset_path, output):
    dataset_path, output = Path(dataset_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('OUTPUT_MUST_BE_NEW')
    root = dataset_path.parent
    dataset_hash = digest(dataset_path)
    data = read(dataset_path)
    dataset_version = data.get('version')
    if data.get('format') != 'hps.feature_recognition_dataset' or dataset_version not in ('0.1.0', '0.2.0'):
        raise ValueError('INVALID_DATASET_VERSION')
    ownership_labels = dataset_version == '0.2.0'
    cases = data['cases']
    if not cases or len(cases) > 40 or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('INVALID_CASES')
    rows, gap_rows, seals = [], [], []
    for case in cases:
        if case['provenance'] not in ('archived_model', 'controlled_fixture', 'new_model_capture'):
            raise ValueError('INVALID_PROVENANCE')
        files = {key: sealed_file(root, case[key]) for key in ('reference', 'request', 'labels')}
        if case.get('response'):
            files['response'] = sealed_file(root, case['response'])
        request = read(files['request'])
        schema = json.loads(request['schema_hint'])
        feature_requested = 'independent_illustration' in (
            schema.get('$defs', {}).get('Allocation', {}).get('properties', {})
            .get('required_features', {}).get('items', {}).get('enum', [])
        )
        observations_requested = 'feature_observations' in schema.get('required', [])
        labels = read(files['labels'])
        payload = json.loads(request['user_prompt'])
        if request['image_sha256'] != [digest(files['reference'])]:
            raise ValueError('REFERENCE_REQUEST_MISMATCH')
        nodes = {n['id']: n for n in payload['objects']}
        if len(nodes) != len(payload['objects']):
            raise ValueError('DUPLICATE_INPUT_OBJECT')
        if labels.get('authority') not in ('assistant_visual_review', 'human_visual_review', 'controlled_fixture'):
            raise ValueError('LABEL_AUTHORITY_REQUIRED')
        seen = set()
        response = read(files['response']) if 'response' in files else None
        if ownership_labels and labels.get('version') != '0.2.0':
            raise ValueError('LABEL_VERSION_MISMATCH')
        for label in labels['targets']:
            target = label['targetId']
            if (target in seen or target not in nodes or type(label['expected']) not in (bool, type(None))
                    or not label.get('evidence') or label.get('feature') != 'independent_illustration'):
                raise ValueError('INVALID_LABEL')
            if ownership_labels:
                ownership = label.get('ownership')
                if ownership not in OWNERSHIP:
                    raise ValueError('INVALID_LABEL_OWNERSHIP')
                if ownership == 'ambiguous':
                    if (label['expected'] is not None
                            or not isinstance(label.get('ambiguous_reason'), str)
                            or not label['ambiguous_reason'].strip()):
                        raise ValueError('AMBIGUOUS_LABEL_REQUIRES_REASON')
                elif label['expected'] is None or label.get('ambiguous_reason'):
                    raise ValueError('INVALID_AMBIGUOUS_LABEL')
            seen.add(target)
            predicted, reason = prediction(response, target, label['feature'],
                                           require_observations=observations_requested, expected_targets=nodes)
            if not feature_requested and not observations_requested:
                predicted, reason = None, 'feature_not_in_archived_output_contract'
            rows.append({'case_id': case['id'], 'course_id': case['course_id'], 'page_id': case['page_id'],
                         'provenance': case['provenance'], 'label_authority': labels['authority'],
                         'label_ownership': label.get('ownership'), **label,
                         'predicted': predicted, 'prediction_reason': reason})
            gap_rows.append({**rows[-1],
                             'expected': None if label['expected'] is None else (label['expected'] and nodes[target]['type'] != 'image'),
                             'predicted': gap_prediction(response, target),
                             'prediction_reason': 'ready_or_targeted_unsupported_presentation',
                             'boundary': 'Targeted capability-stop detection, not proof of correct visual rationale.'})
        seals.extend((p, digest(p)) for p in files.values())
    groups = sorted({r['provenance'] for r in rows})
    result = {'dataset_sha256': dataset_hash, 'provider_calls': 0, 'author_writes': 0,
              'cases': len(cases), 'distinct_courses': len({c['course_id'] for c in cases}),
              'distinct_pages': len({(c['course_id'], c['page_id']) for c in cases}),
              'by_provenance': {g: metrics([r for r in rows if r['provenance'] == g]) for g in groups},
              'capability_gap_by_provenance': {g: metrics([r for r in gap_rows if r['provenance'] == g]) for g in groups},
              'by_label_authority': {a: metrics([r for r in rows if r['label_authority'] == a])
                                     for a in sorted({r['label_authority'] for r in rows})},
              'rows': rows, 'capability_gap_rows': gap_rows,
              'boundary': 'Feature declaration recall and typed capability-stop recall are distinct, not all-defect detection or production success. No live requests. '
                          'Legacy prompts not requesting this feature are unresolved for feature recall, never false negatives. '
                          'Ambiguous labels excluded; explicit complete feature observations are scored independently of allocation status; '
                          'legacy unsupported/invalid/missing responses remain unresolved. '
                          'Archived and controlled/new captures have separate denominators; labels are not human approval.'}
    if ownership_labels:
        ambiguous = [r for r in rows if r['label_ownership'] == 'ambiguous']
        result['labels_version'] = '0.2.0'
        result['by_ownership'] = {o: metrics([r for r in rows if r['label_ownership'] == o])
                                  for o in sorted(OWNERSHIP)}
        result['ambiguous_reasons'] = dict(Counter(r['ambiguous_reason'] for r in ambiguous))
        result['boundary'] += (' Ownership classes are scored separately; container, icon, annotation and text '
                               'targets must not claim an illustration already owned by an image. '
                               'Ambiguous targets stay excluded from decisive denominators and keep their reason.')
    if digest(dataset_path) != dataset_hash or any(digest(p) != h for p, h in seals):
        raise ValueError('INPUT_CHANGED_DURING_EVALUATION')
    output.mkdir(parents=True)
    (output / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    result = evaluate(args.dataset, args.output)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'capability_gap_rows')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
