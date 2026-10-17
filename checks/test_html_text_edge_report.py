"""Read-only report binding, identity safety and original pixel evidence."""
import copy
from html.parser import HTMLParser
import json
import shutil
import subprocess

from PIL import Image, ImageDraw
import pytest

from artifact_fingerprint import sha256_file, sha256_json
from html_text_edge_report import write_text_edge_report
from html_text_edge_verification import verify_text_edges


def fixture(tmp_path):
    image = Image.new('RGB', (240, 160), 'white')
    draw = ImageDraw.Draw(image)
    draw.line((85, 65, 85, 95), fill='black', width=3)
    draw.line((55, 80, 90, 80), fill='black', width=3)
    reference = tmp_path/'reference.png'
    image.save(reference)
    box = {'xPx': 60, 'yPx': 50, 'widthPx': 120, 'heightPx': 60}
    result = {'targets': [{'targetId': 'caption<script>bad()</script>', 'status': 'located',
        'container_box': None, 'part_regions': [{'partId': 'runs/0', 'regions': [
            {'text': '文字 </p><script>bad()</script>', 'box': box}]}]},
        {'targetId': '<missing>', 'status': 'not_found', 'part_regions': []}]}
    return reference, {'result': result, 'reference_sha256': sha256_file(reference),
        'image_size': [240, 160], 'edge_verification': verify_text_edges(image, result)}


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


def test_report_preserves_sources_and_displays_bound_identity_and_ink(tmp_path):
    reference, record = fixture(tmp_path)
    before = copy.deepcopy(record)
    source = reference.read_bytes()
    path = tmp_path/'report.html'
    receipt = write_text_edge_report(reference, record, path)
    html = path.read_text(encoding='utf-8')
    assert record == before and reference.read_bytes() == source
    assert receipt['sha256'] == sha256_file(path)
    assert receipt['result_sha256'] == sha256_json(record['result'])
    assert receipt['regions'] == 1 and receipt['counts']['possible_clip'] == 1
    assert receipt['model_calls'] == 0 and not receipt['automatic_review_eligible']
    assert 'runs/0 / 行索引 0' in html and '[60, 50, 180, 110]' in html
    assert '连通墨迹跨出原文字框' in html and '框外像素' in html
    assert record['reference_sha256'] in html
    assert '<script>bad()</script>' not in html and '&lt;script&gt;bad()&lt;/script&gt;' in html
    assert '&lt;missing&gt;：not_found' in html
    parsed = Elements()
    parsed.feed(html)
    # One original box and one diagnostic component, translated from image to window.
    rects = [attrs for tag, attrs in parsed.items if tag == 'rect']
    row = record['edge_verification']['regions'][0]
    assert len(rects) == len(row['components']) + 1
    assert rects[0]['x'] == str(60-row['window'][0])
    assert rects[1]['x'] == str(row['components'][0]['ink_bounds'][0]-row['window'][0])
    assert all(attrs['href'].startswith('data:image/png;base64,')
               for tag, attrs in parsed.items if tag == 'image')
    assert all('hidden' not in attrs for tag, attrs in parsed.items if tag == 'article')
    assert not any(tag in ('iframe', 'form', 'link') for tag, _ in parsed.items)
    assert not any(attrs.get('src', '').startswith(('http:', 'https:')) for _, attrs in parsed.items)


@pytest.mark.parametrize('damage', ['reference', 'diagnostic', 'size'])
def test_mismatched_evidence_fails_without_creating_report(tmp_path, damage):
    reference, record = fixture(tmp_path)
    if damage == 'reference':
        Image.new('RGB', (240, 160), 'black').save(reference)
    elif damage == 'diagnostic':
        record['edge_verification']['regions'][0]['box']['xPx'] += 1
    else:
        record['image_size'] = [1, 1]
    with pytest.raises(ValueError, match='TEXT_EDGE_REPORT_'):
        write_text_edge_report(reference, record, tmp_path/'report.html')
    assert not (tmp_path/'report.html').exists()


def test_empty_and_historical_records_never_imply_pass(tmp_path):
    reference, record = fixture(tmp_path)
    record.pop('edge_verification')
    record['result']['targets'] = [record['result']['targets'][1]]
    path = tmp_path/'report.html'
    receipt = write_text_edge_report(reference, record, path)
    html = path.read_text(encoding='utf-8')
    assert receipt['regions'] == 0 and '没有可检查文字区域' in html
    assert '不证明文字完整' in html and '批准视觉' in html


def test_cli_writes_new_directory_and_keeps_saved_record(tmp_path, monkeypatch, capsys):
    from scripts.report_html_text_edges import main
    reference, record = fixture(tmp_path)
    path = tmp_path/'result.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    before = path.read_bytes()
    out = tmp_path/'new-report'
    monkeypatch.setattr('sys.argv', ['report', '--reference', str(reference), '--record', str(path), '--out', str(out)])
    main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['source_record_sha256'] == sha256_file(path) and path.read_bytes() == before
    assert receipt['source_records_changed'] == 0 and (out/'text-edges.html').is_file()
    with pytest.raises(FileExistsError):
        main()


def test_filter_and_zoom_script_keep_original_coordinates(tmp_path):
    """Execute shipped JS against a minimal DOM; this is not browser visual QA."""
    reference, record = fixture(tmp_path)
    # Repeat the same bounded fixture with different complete/uncertain backgrounds.
    record['result']['targets'][0]['part_regions'][0]['regions'].append(
        {'text': 'second line', 'box': {'xPx': 120, 'yPx': 15, 'widthPx': 80, 'heightPx': 20}})
    record.pop('edge_verification')
    path = tmp_path/'report.html'
    write_text_edge_report(reference, record, path)
    html = path.read_text(encoding='utf-8')
    parser = Elements()
    parser.feed(html)
    statuses = [attrs['data-status'] for tag, attrs in parser.items if tag == 'article']
    assert set(statuses) == {'possible_clip', 'uncertain'}
    svg_sizes = [{key: attrs['data-'+key] for key in ('width', 'height')}
                 for tag, attrs in parser.items if tag == 'svg']
    node = shutil.which('node')
    assert node, 'Node is required for report interaction checks'
    script = '''const assert=require('node:assert/strict'),vm=require('node:vm');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const cards=input.statuses.map(status=>({dataset:{status},hidden:false}));
const svg=input.sizes.map(size=>({dataset:size,attrs:{},setAttribute(k,v){this.attrs[k]=v;}}));
const controls={status:{value:'all'},zoom:{value:'1'},visible:{textContent:''}};
for(const obj of Object.values(controls))obj.addEventListener=(kind,fn)=>{obj[kind]=fn;};
const document={querySelectorAll:selector=>selector==='article'?cards:svg,getElementById:id=>controls[id]};
vm.runInNewContext(input.script,{document});
assert.equal(cards.filter(c=>!c.hidden).length,2);
controls.status.value='possible_clip';controls.status.change();
assert.equal(cards.filter(c=>!c.hidden).length,1);
assert.equal(controls.visible.textContent,'显示 1 / 2 个文字区域');
controls.status.value='all';controls.status.change();assert.equal(cards.filter(c=>!c.hidden).length,2);
controls.zoom.value='4';controls.zoom.change({target:controls.zoom});
svg.forEach(s=>{assert.equal(s.attrs.width,Number(s.dataset.width)*4);assert.equal(s.attrs.height,Number(s.dataset.height)*4);});
console.log('filter/zoom passed');'''
    completed = subprocess.run([node, '-e', script], input=json.dumps({
        'statuses': statuses, 'sizes': svg_sizes, 'script': html.split('<script>')[1].split('</script>')[0]}),
        text=True, capture_output=True, timeout=10)
    assert completed.returncode == 0, completed.stderr
