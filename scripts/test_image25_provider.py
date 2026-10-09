"""Live 2K/low experiment through the application's governed ToAPIs adapter.

Credential is read without echo, used in memory, and never persisted.
No application composition root, settings or database are loaded.
"""
import argparse
import getpass
import hashlib
import io
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from PIL import Image
import ai_provider_service as provider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('outputs/image25-sheet/toapis-2k-low-v1'))
    parser.add_argument('--prompt', type=Path, default=Path('docs/research/2026-10-08-image25-sheet-experiment/prompt-v2.txt'))
    parser.add_argument('--split-only', action='store_true')
    parser.add_argument('--design-only', action='store_true', help='One opaque full-page design reference; no split or extra illustration call.')
    parser.add_argument('--reference', type=Path, nargs='+', default=[Path('outputs/image25-sheet/reference-original.png')])
    parser.add_argument('--size', default='2048x2048', choices=['2048x2048', '2048x1152'])
    parser.add_argument('--model', default='gpt-image-2.5-flare-vip', choices=['gpt-image-2.5-flare-vip', 'gpt-image-2.5-sunburst-official'])
    args = parser.parse_args()
    if args.design_only and (args.split_only or len(args.reference) != 1):
        parser.error('Design-only requires one reference and cannot combine with split-only.')
    if len(args.reference) > 1 and not args.split_only:
        parser.error('Multiple reference comparisons require --split-only.')
    references = [(str(p), hashlib.sha256(p.read_bytes()).hexdigest()) for p in args.reference]
    split_prompt = args.prompt.read_text(encoding='utf-8').replace('1024x1024', '2048x2048')
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    key = getpass.getpass('ToAPIs credential (hidden): ')
    model = args.model
    base = 'https://api.toapis.com'
    original_client = httpx.Client
    records = []
    active = {}
    synchronous_result = None

    def save():
        (out / 'evidence.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')

    class ObservedClient(original_client):
        def post(self, url, **kwargs):
            nonlocal synchronous_result
            if str(url).endswith('/images/generations'):
                payload = kwargs.get('json', {})
                if model == 'gpt-image-2.5-sunburst-official':
                    # Experiment-only official contract; do not change production VIP behavior.
                    payload.pop('resolution', None)
                    payload['response_format'] = 'b64_json'
                    payload['metadata'] = {'resolution': '2K', 'orientation': 'landscape' if args.size == '2048x1152' else 'square'}
                active['wire'] = {k: v for k, v in payload.items() if k != 'reference_images'}
                active['reference_count'] = len(payload.get('reference_images', []))
                save()
            response = super().post(url, **kwargs)
            if str(url).endswith('/images/generations'):
                body = response.json()
                if response.is_success and isinstance(body.get('data'), list) and body['data']:
                    synchronous_result = body
                active['task_id'] = body.get('id')
                active['submit_http_status'] = response.status_code
                save()
                print(json.dumps({'stage': 'submitted', 'test': active['test'], 'task_id': active.get('task_id'), 'http_status': response.status_code}), flush=True)
            return response

        def get(self, url, **kwargs):
            response = super().get(url, **kwargs)
            if '/images/generations/' in str(url):
                body = response.json()
                active['status'] = body.get('status')
                active['poll_http_status'] = response.status_code
                for name in ('usage', 'cost', 'billing'):
                    value = body.get(name) or (body.get('result') or {}).get(name)
                    if isinstance(value, (dict, int, float)):
                        # Redact recursively before saving provider-reported metrics.
                        active[name] = json.loads(provider._toapis_safe_diagnostic(value, key))
                save()
                print(json.dumps({'test': active['test'], 'status': active['status'], 'http_status': response.status_code}), flush=True)
            return response

    provider.httpx.Client = ObservedClient
    normal_prompt = 'Create a clean 16:9 educational illustration on a pure white opaque background. Arrange a yellow light bulb, a waving blue-white friendly robot with antenna, a milk tea cup with straw, and a pink brain in one balanced composition. Match the reference black outlines, flat pastel colors and recognizable designs. No text, numbers, labels, arrows, hearts, grids or checkerboard. All four subjects completely visible, generous margins. Return one complete 2048x1152 PNG image; background is opaque.'
    cases = [(f'split-{index+1}' if len(references) > 1 else 'split', split_prompt, args.size, True, reference, digest)
             for index, (reference, digest) in enumerate(references)]
    if args.design_only:
        cases = [('design-reference', split_prompt, args.size, False, *references[0])]
    elif not args.split_only:
        cases.append(('complete', normal_prompt, '2048x1152', False, *references[0]))
    for name, prompt, size, transparent, reference, digest in cases:
        active = {'test': name, 'model': model, 'base_url': base, 'requested_size': size,
                  'quality': 'low', 'transparent': transparent, 'started_at': time.time(),
                  'reference_sha256': digest}
        records.append(active)
        save()
        started = time.monotonic()
        try:
            response = provider.generate_toapis_image_response(
                api_key=key, base_url=base, model=model, prompt=prompt, size=size,
                quality='low', transparent_background=transparent,
                reference_paths=[reference], timeout=900,
            )
            png = provider.extract_image_bytes_from_response(response)
            (out / f'{name}.png').write_bytes(png)
            image = Image.open(io.BytesIO(png))
            alpha = image.convert('RGBA').getchannel('A')
            histogram = alpha.histogram()
            active.update(actual_size=list(image.size), mode=image.mode,
                          alpha_min=alpha.getextrema()[0], alpha_max=alpha.getextrema()[1],
                          transparent_pixels=histogram[0], opaque_pixels=histogram[255],
                          pixel_count=image.width * image.height, output=f'{name}.png',
                          elapsed_seconds=round(time.monotonic() - started, 2))
            print(json.dumps({k: v for k, v in active.items() if k not in {'wire'}}, ensure_ascii=False), flush=True)
        except Exception as exc:
            if synchronous_result is not None:
                png = provider.extract_image_bytes_from_response(synchronous_result)
                (out / f'{name}.png').write_bytes(png)
                image = Image.open(io.BytesIO(png))
                active.update(status='completed', actual_size=list(image.size), mode=image.mode,
                              output=f'{name}.png', elapsed_seconds=round(time.monotonic() - started, 2))
                synchronous_result = None
                save()
                print(json.dumps({'test': name, 'status': 'completed', 'actual_size': active['actual_size']}), flush=True)
                continue
            active['error'] = provider._toapis_safe_diagnostic(str(exc), key)
            active['elapsed_seconds'] = round(time.monotonic() - started, 2)
            print(json.dumps({'test': name, 'error': active['error']}, ensure_ascii=False), flush=True)
            save()
            if active.get('submit_http_status') in {401, 403}:
                break
        save()


if __name__ == '__main__':
    main()
