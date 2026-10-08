"""Confirm and export the seeded scenarios through the isolated API."""
import argparse
import json
import time
from pathlib import Path
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project_id', choices=['annotation_cases_landscape', 'annotation_cases_portrait'])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    run = root / 'outputs/annotation-bcd/isolated/runs' / args.project_id
    rows = json.loads((run / 'acceptance_mapping.json').read_text(encoding='utf-8'))
    base = 'http://127.0.0.1:8015/api/projects/' + args.project_id
    evidence = []

    def call(method, path, **kwargs):
        response = requests.request(method, base+path, timeout=180, **kwargs)
        response.encoding = 'utf-8'
        value = response.json()
        if not response.ok:
            raise RuntimeError(f'{path}: {response.status_code}: {value}')
        return value

    for row in rows:
        sid = row['slide_id']
        path = '/annotations/slides/' + sid
        page = call('GET', path)
        if not page['items']:
            evidence.append({'case': row['case'], 'kind': row['kind'], 'slide_id': sid, 'annotation': 'no_items_expected'})
            continue
        # Review flags may require manual inspection; never auto-accept them.
        blocked = [item['annotation_id'] for item in page['items'] if item['status']['spatial'] == 'needs_review' or item.get('review_issues')]
        if blocked:
            raise RuntimeError('independent spatial review needed: ' + str(blocked))
        job = call('POST', '/annotations/jobs', json={'operation': 'preview', 'slide_ids': [sid], 'expected_revision': page['revision']})
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            preview = call('GET', '/annotations/jobs/' + job['job_id'])
            if preview['status'] not in ('queued', 'running'):
                break
            time.sleep(1)
        if preview['status'] != 'succeeded':
            raise RuntimeError(str({k: preview.get(k) for k in ('status', 'error', 'error_detail')}))
        confirmed = call('POST', path+'/confirm', json={'expected_revision': page['revision'], 'prepared_build_id': preview['result']['build_id']})
        evidence.append({'case': row['case'], 'kind': row['kind'], 'slide_id': sid, 'confirmed': confirmed['confirmed'], 'build_id': confirmed['build_id'],
                         'events': [{k: e.get(k) for k in ('annotation_id', 'start_sec', 'draw_end_sec', 'timing_source')} for e in preview['result']['timeline']['events']]})
        print(args.project_id, sid, 'confirmed', flush=True)
    call('POST', '/steps/7/confirm')
    render = call('POST', '/steps/8/render')
    destination = root / 'outputs/annotation-bcd/full-cases'
    destination.mkdir(exist_ok=True)
    (destination / (args.project_id+'.json')).write_text(json.dumps({'scenarios': evidence, 'submission': render}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(args.project_id, 'render submitted', render['task_id'], flush=True)


if __name__ == '__main__':
    main()
