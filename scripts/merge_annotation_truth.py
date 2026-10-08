"""Merge independent reviewer JSON into immutable prediction records."""
import argparse
import json
from pathlib import Path
from package_annotation_truth import merge_labels
from evaluate_annotation_alignment import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    predictions = json.loads(args.predictions.read_text(encoding='utf-8'))
    labels = json.loads(args.labels.read_text(encoding='utf-8'))
    merged = merge_labels(predictions, labels)
    result = evaluate(merged)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in [('labelled.json', merged), ('evaluation.json', result)]:
        (args.output/name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('total','automatic_coverage','p95_ms','passed')}))


if __name__ == '__main__':
    main()
