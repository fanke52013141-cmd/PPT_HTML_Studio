"""Verify exported reference dimensions, exact neutral pixels and content hashes."""
import hashlib
import json
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
output = root / 'standard'
manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
assert hashlib.sha256((root / 'standard-library.html').read_bytes()).hexdigest() == manifest['sourceSha256']
assert len(manifest['files']) == 24
results = []
for entry in manifest['files'] + [{'filename': 'contact-sheet.png'}]:
    path = output / entry['filename']
    with Image.open(path) as image:
        if 'sha256' in entry:
            assert image.size == (1920, 1080), path
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], path
        assert all(r == g == b for r, g, b in image.convert('RGB').get_flattened_data()), path
        results.append({'page': path.name, 'size': image.size, 'grayscale': True})
(output / 'pixel-verification.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
print('Verified 24 full pages and contact sheet: neutral pixels, dimensions, source and image hashes')
