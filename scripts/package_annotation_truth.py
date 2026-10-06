"""Create a prediction-blind human review page and optionally merge labels."""
import argparse
import hashlib
import json
from pathlib import Path


def merge_labels(predictions, labels):
    by_id = {r['sample_id']: r for r in labels}
    if len(by_id) != len(labels):
        raise ValueError('duplicate human label ID')
    known = {r['sample_id'] for r in predictions}
    if set(by_id) - known:
        raise ValueError('unknown human label ID')
    merged = []
    for prediction in predictions:
        row = dict(prediction)
        label = by_id.get(row['sample_id'])
        if label:
            if label.get('truth_source') != 'human' or not str(label.get('reviewer') or '').strip():
                raise ValueError('independent human reviewer required')
            if label.get('truth_audio_sha256') != row.get('audio_sha256'):
                raise ValueError('human label audio hash mismatch')
            for field in ('truth_start_sec', 'truth_audio_sha256', 'truth_source', 'reviewer', 'labelled_at'):
                row[field] = label.get(field)
        merged.append(row)
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--labels', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = json.loads((args.run_dir / 'acceptance_mapping.json').read_text(encoding='utf-8'))
    public = []
    for row in rows:
        audio = args.run_dir / 'slides' / row['slide_id'] / 'voice.mp3'
        if not audio.is_file():
            raise ValueError('missing audio: ' + row['sample_id'])
        row['audio_sha256'] = hashlib.sha256(audio.read_bytes()).hexdigest()
        public.append({k: row[k] for k in ('sample_id', 'category', 'text', 'quote', 'range', 'audio_sha256')})
        public[-1]['audio_url'] = f"http://127.0.0.1:8015/api/projects/{args.run_dir.name}/slides/{row['slide_id']}/audio"
    html = Path(__file__).with_name('annotation_truth_review.html').read_text(encoding='utf-8')
    html = html.replace('__SAMPLES__', json.dumps(public, ensure_ascii=False).replace('<', '\\u003c'))
    (args.output / 'index.html').write_text(html, encoding='utf-8')
    (args.output / 'predictions.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.labels:
        merged = merge_labels(rows, json.loads(args.labels.read_text(encoding='utf-8')))
        from evaluate_annotation_alignment import evaluate
        report = evaluate(merged)
        for name, data in [('labelled.json', merged), ('evaluation.json', report)]:
            (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'samples': len(rows), 'unique_audio_hashes': len({r['audio_sha256'] for r in rows}), 'human_labels': sum(r.get('truth_start_sec') is not None for r in rows)}))


if __name__ == '__main__':
    main()
