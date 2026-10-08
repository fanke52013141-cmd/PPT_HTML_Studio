"""Asset-sheet candidates retain pixels, provenance and explicit review gates."""
import copy
import hashlib
import io

import pytest
from PIL import Image, ImageDraw

import html_asset_sheet as sheet


def png(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def fixture(method='source_alpha'):
    image = Image.new('RGBA', (32, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((3, 3, 12, 12), fill=(150, 60, 30, 128))
    draw.rectangle((19, 3, 28, 12), fill=(40, 90, 180, 255))
    source = png(image)
    spec = {'format': sheet.FORMAT, 'version': sheet.VERSION, 'id': 'board',
            'source_sha256': hashlib.sha256(source).hexdigest(), 'slots': [
                {'id': 'left', 'asset_id': 'one', 'role': 'subject', 'need': 'one',
                 'rect': [0, 0, 16, 16], 'method': method,
                 'anchors': [{'id': 'focus', 'x': 5, 'y': 5}]},
                {'id': 'right', 'asset_id': 'two', 'role': 'subject', 'need': 'two',
                 'rect': [16, 0, 16, 16], 'method': 'source_alpha',
                 'anchors': [{'id': 'focus', 'x': 21, 'y': 5}]},
            ]}
    return source, spec


def test_multiple_objects_exact_pixels_local_anchors_and_repeatability():
    source, spec = fixture()
    before = copy.deepcopy(spec)
    first = sheet.extract_asset_sheet(source, spec)
    assert first == sheet.extract_asset_sheet(source, spec)
    assert spec == before
    assets = first['manifest']['assets']
    assert len(assets) == 2
    assert all(a['identity_review'] == a['edge_review'] == 'pending' for a in assets)
    assert assets[1]['anchors'][0] == {'id': 'focus', 'x': 5, 'y': 5, 'nx': 5/16, 'ny': 5/16}
    for asset in assets:
        assert asset['source']['sha256'] == hashlib.sha256(source).hexdigest()
        assert asset['sha256'] == hashlib.sha256(first['images'][asset['id']]).hexdigest()
    result = Image.open(io.BytesIO(first['images']['one']))
    assert result.getpixel((5, 5)) == (150, 60, 30, 128)
    assert result.getpixel((0, 0)) == (0, 0, 0, 0)


def test_soft_mask_multiplies_alpha_and_changes_cache_key():
    source, spec = fixture('mask')
    mask = Image.new('L', (32, 16))
    ImageDraw.Draw(mask).rectangle((3, 3, 12, 12), fill=128)
    result = sheet.extract_asset_sheet(source, spec, masks={'left': png(mask)})
    assert not result['manifest']['failures']
    assert Image.open(io.BytesIO(result['images']['one'])).getpixel((5, 5)) == (150, 60, 30, 64)
    ImageDraw.Draw(mask).rectangle((3, 3, 12, 12), fill=255)
    second = sheet.extract_asset_sheet(source, spec, masks={'left': png(mask)})
    assert result['manifest']['request_key'] != second['manifest']['request_key']


def test_white_boundary_removal_keeps_enclosed_white():
    image = Image.new('RGBA', (16, 16), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((3, 3, 12, 12), fill='black')
    draw.rectangle((5, 5, 10, 10), fill='white')
    source, spec = fixture()
    source = png(image)
    spec['source_sha256'] = hashlib.sha256(source).hexdigest()
    spec['slots'] = spec['slots'][:1]
    slot = spec['slots'][0]
    slot.update(method='boundary_color', background={'rgb': [255]*3, 'tolerance': 0})
    result = sheet.extract_asset_sheet(source, spec)
    extracted = Image.open(io.BytesIO(result['images']['one']))
    assert extracted.getpixel((0, 0))[3] == 0
    assert extracted.getpixel((7, 7)) == (255, 255, 255, 255)


@pytest.mark.parametrize('mutation,code', [
    (lambda s: s.update(extra=True), 'SHEET_FIELDS'),
    (lambda s: s.update(version='future'), 'SHEET_VERSION'),
    (lambda s: s.update(source_sha256='0'*64), 'SHEET_HASH'),
    (lambda s: s['slots'][1].update(id='left'), 'SHEET_DUPLICATE_ID'),
    (lambda s: s['slots'][1].update(rect=[8, 0, 16, 16]), 'SHEET_SLOT_OVERLAP'),
    (lambda s: s['slots'][0].update(rect=[True, 0, 16, 16]), 'SHEET_RECT'),
    (lambda s: s['slots'][0].update(rect=[0, 0, 33, 16]), 'SHEET_RECT'),
    (lambda s: s['slots'][0].update(role=''), 'SHEET_SEMANTICS'),
])
def test_invalid_board_rejected(mutation, code):
    source, spec = fixture()
    mutation(spec)
    with pytest.raises(sheet.HtmlAssetSheetError) as exc:
        sheet.extract_asset_sheet(source, spec)
    assert exc.value.code == code


@pytest.mark.parametrize('failure,code', [
    ('missing', 'SHEET_MASK_MISSING'), ('outside', 'SHEET_MASK_OUTSIDE_SLOT'),
    ('mode', 'SHEET_MASK_FORMAT'), ('size', 'SHEET_MASK_SIZE'),
    ('empty', 'SHEET_EMPTY'), ('anchor', 'SHEET_ANCHOR_EMPTY'),
])
def test_one_slot_failure_retains_other_candidate(failure, code):
    source, spec = fixture('mask')
    mask = Image.new('L', (32, 16))
    ImageDraw.Draw(mask).rectangle((3, 3, 12, 12), fill=255)
    if failure == 'outside':
        mask.putpixel((20, 5), 255)
    elif failure == 'mode':
        mask = mask.convert('RGB')
    elif failure == 'size':
        mask = mask.crop((0, 0, 16, 16))
    elif failure == 'empty':
        mask = Image.new('L', (32, 16))
    elif failure == 'anchor':
        spec['slots'][0]['anchors'][0].update(x=1, y=1)
    result = sheet.extract_asset_sheet(source, spec, masks={} if failure == 'missing' else {'left': png(mask)})
    assert result['manifest']['status'] == 'partial'
    assert list(result['images']) == ['two']
    assert result['manifest']['failures'][0]['code'] == code


def test_opaque_fake_transparency_is_not_accepted():
    source, spec = fixture()
    image = Image.new('RGBA', (32, 16), (230, 230, 230, 255))
    source = png(image)
    spec['source_sha256'] = hashlib.sha256(source).hexdigest()
    result = sheet.extract_asset_sheet(source, spec)
    assert not result['images']
    assert {f['code'] for f in result['manifest']['failures']} == {'SHEET_EDGE_CONTACT'}


def test_decode_budgets_and_unregistered_masks(monkeypatch):
    source, spec = fixture()
    with pytest.raises(sheet.HtmlAssetSheetError, match='PNG'):
        sheet.extract_asset_sheet(b'bad', spec)
    with pytest.raises(sheet.HtmlAssetSheetError) as exc:
        sheet.extract_asset_sheet(source, spec, masks={'unknown': b'bad'})
    assert exc.value.code == 'SHEET_MASK_KEYS'
    monkeypatch.setattr(sheet, 'MAX_SHEET_PIXELS', 10)
    with pytest.raises(sheet.HtmlAssetSheetError) as exc:
        sheet.extract_asset_sheet(source, spec)
    assert exc.value.code == 'SHEET_PIXEL_BUDGET'
    monkeypatch.setattr(sheet, 'MAX_PNG_BYTES', 10)
    with pytest.raises(sheet.HtmlAssetSheetError) as exc:
        sheet.extract_asset_sheet(source, spec)
    assert exc.value.code == 'SHEET_BYTE_BUDGET'


def test_candidate_store_is_immutable_cached_and_does_not_publish(tmp_path):
    from html_asset_sheet_store import persist_sheet_candidates
    source, spec = fixture()
    first = persist_sheet_candidates(tmp_path, source, spec)
    second = persist_sheet_candidates(tmp_path, source, spec)
    assert first['cache'] == 'miss' and second['cache'] == 'hit'
    assert first['directory'] == second['directory']
    folder = tmp_path / first['directory']
    assert (folder / 'source.png').read_bytes() == source
    assert (folder / 'asset-one.png').exists()
    assert not (tmp_path / 'planning/html_visual/resources.json').exists()
    assert not (tmp_path / 'planning/html_visual/revision.json').exists()
    spec['slots'][0]['need'] = 'revised identity review requirement'
    newer = persist_sheet_candidates(tmp_path, source, spec)
    assert newer['directory'] != first['directory']
    assert (folder / 'asset-one.png').exists()
    (folder / 'asset-one.png').write_bytes(b'corrupted')
    spec['slots'][0]['need'] = 'one'
    with pytest.raises(sheet.HtmlAssetSheetError) as exc:
        persist_sheet_candidates(tmp_path, source, spec)
    assert exc.value.code == 'SHEET_CANDIDATE_CORRUPT'
    assert (folder / 'asset-one.png').read_bytes() == b'corrupted'


def test_candidate_store_failed_staging_leaves_no_published_directory(tmp_path, monkeypatch):
    from pathlib import Path
    from html_asset_sheet_store import persist_sheet_candidates
    source, spec = fixture()
    original = Path.write_bytes
    def fail(path, data):
        if path.name == 'asset-one.png':
            raise OSError('simulated interrupted write')
        return original(path, data)
    monkeypatch.setattr(Path, 'write_bytes', fail)
    with pytest.raises(OSError, match='interrupted'):
        persist_sheet_candidates(tmp_path, source, spec)
    parent = tmp_path / 'planning/html_visual/asset-sheets/board'
    assert not list(parent.iterdir())
