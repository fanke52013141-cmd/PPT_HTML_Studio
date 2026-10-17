"""Read-only, self-contained evidence for independently localized text edges."""
from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from pathlib import Path

from PIL import Image

from artifact_fingerprint import sha256_file, sha256_json
from html_text_edge_verification import verify_text_edges

POLICY = 'reference-text-edge-report/0.1.0'
LABELS = {'possible_clip': '疑似截字', 'uncertain': '无法确定', 'no_detected_clip': '未见跨界'}
REASONS = {
    'connected_ink_crosses_box': '连通墨迹跨出原文字框',
    'connected_ink_crosses_box_with_ambiguity': '存在跨界墨迹，同时存在干扰',
    'ink_touches_boundary': '墨迹贴边，证据不足',
    'image_edge_unobservable': '原图边缘之外不可观察',
    'container_edge_nearby': '接近声明的容器边界',
    'transparent_background': '窗口含透明像素',
    'nonuniform_background': '局部背景不均匀',
    'insufficient_or_dense_foreground': '前景过少、低对比或过密',
    'component_leaves_window': '墨迹继续延伸到观察窗口之外',
    'rule_or_underline': '疑似线条或下划线',
    'dense_shape_or_icon': '疑似实心图形或图标',
    'component_outside_container': '墨迹跨出声明的容器',
    'neighbour_region_intersection': '墨迹与其他文字区域相交',
    'window_budget_exceeded': '观察窗口超过计算预算',
    'component_budget_exceeded': '连通组件超过计算预算',
    'boundary_component_budget_exceeded': '边界组件数量超过预算',
}
SIDES = {'left': '左', 'top': '上', 'right': '右', 'bottom': '下'}


def _png(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def _rect(rect, origin, colour):
    x, y, right, bottom = rect
    return (f'<rect x="{x-origin[0]}" y="{y-origin[1]}" width="{right-x}" '
            f'height="{bottom-y}" fill="none" stroke="{colour}" stroke-width="1" '
            'vector-effect="non-scaling-stroke"/>')


def render_report(image, record, diagnostic):
    """Render escaped identities with original pixel coordinates, no author actions."""
    cards = []
    targets = {t['targetId']: t for t in record['result']['targets']}
    for row in diagnostic['regions']:
        target = targets[row['targetId']]
        part = next(p for p in target['part_regions'] if p['partId'] == row['partId'])
        text = part['regions'][row['region_index']]['text']
        window = row['window']
        width, height = window[2]-window[0], window[3]-window[1]
        box = row['box']
        original = [box['xPx'], box['yPx'], box['xPx']+box['widthPx'], box['yPx']+box['heightPx']]
        shapes = _rect(original, window, '#dc2626')
        components = []
        for item in row['components']:
            shapes += _rect(item['ink_bounds'], window, '#0284c7')
            components.append('<li>墨迹框 ' + escape(str(item['ink_bounds'])) + '；方向 ' +
                              escape('、'.join(SIDES[s] for s in item['sides'])) +
                              f'；框外像素 {item["outside_pixels"]}</li>')
        reasons = '；'.join(REASONS.get(r, r) for r in row['reasons']) or '没有检测到连通墨迹跨界；不证明文字完整'
        cards.append(f'''<article data-status="{row['status']}">
<h2>{escape(row['targetId'])} / {escape(row['partId'])} / 行索引 {row['region_index']}</h2>
<p class="status {row['status']}">{LABELS[row['status']]}</p>
<p class="transcript">转录：{escape(text)}</p><p>{escape(reasons)}</p>
<p class="coords">原框 [左, 上, 右, 下]：{original}；观察窗口：{window}</p>
<div class="viewport"><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="原文字框与跨界墨迹局部证据"
viewBox="0 0 {width} {height}" width="{width}" height="{height}" data-width="{width}" data-height="{height}">
<image href="{_png(image.crop(window))}" width="{width}" height="{height}"/>{shapes}</svg></div>
<ul>{''.join(components)}</ul></article>''')
    missing = ''.join('<li>' + escape(t['targetId']) + '：' + escape(t['status']) + '</li>'
                      for t in targets.values() if t['status'] != 'located')
    counts = '；'.join(f'{LABELS[s]} {diagnostic["counts"][s]}' for s in LABELS)
    body = ''.join(cards) or '<p>没有可检查文字区域，状态为无法确定。</p>'
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>文字边缘证据审阅</title><style>
body{font:16px/1.6 system-ui,sans-serif;margin:auto;padding:24px;max-width:1200px;background:#f8fafc;color:#172033}
article,details,header,nav{background:white;border:1px solid #cbd5e1;border-radius:10px;padding:18px;margin:16px 0}
h1{font-size:26px}h2{font-size:18px;overflow-wrap:anywhere}.transcript,.coords{white-space:pre-wrap;overflow-wrap:anywhere}
.status{font-weight:bold}.possible_clip{color:#b91c1c}.uncertain{color:#854d0e}.no_detected_clip{color:#334155}
.viewport{overflow:auto;background:#e2e8f0;padding:12px}svg{display:block;max-width:none}details img{max-width:100%;height:auto}
label{display:inline-block;margin:8px 20px 8px 0}select{font:inherit;padding:4px}small{overflow-wrap:anywhere}
[hidden]{display:none!important}</style><header><h1>文字边缘证据审阅</h1>
<p>只读诊断：红框是原文字框，蓝框是跨界墨迹包围盒，不是建议替换框。未见跨界不证明文字完整。</p>
<p>不核实文字身份，不自动修框，不批准视觉，不调用模型。</p>''' + \
        f'<p>{counts}</p><small>参考图 SHA-256：{escape(record["reference_sha256"])}<br>' + \
        f'定位结果 SHA-256：{sha256_json(record["result"])}<br>策略：{POLICY} / {diagnostic["policy"]}</small></header>' + \
        f'<details><summary>完整参考图（{image.width} × {image.height}）</summary><img alt="完整原始参考图" src="{_png(image)}"></details>' + \
        '<nav><label>状态 <select id="status"><option value="all">全部</option>' + \
        ''.join(f'<option value="{s}">{label}</option>' for s, label in LABELS.items()) + \
        '</select></label><label>局部放大 <select id="zoom"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select></label><p id="visible" aria-live="polite"></p></nav>' + \
        '<section><h2>未定位目标</h2>' + ('<ul>'+missing+'</ul>' if missing else '<p>无。此状态不证明定位正确。</p>') + \
        '</section><main>'+body+'''</main><script>
const cards=Array.from(document.querySelectorAll('article'));
function filter(){const state=document.getElementById('status').value;let shown=0;
cards.forEach(card=>{card.hidden=state!=='all'&&card.dataset.status!==state;if(!card.hidden)shown++;});
document.getElementById('visible').textContent=`显示 ${shown} / ${cards.length} 个文字区域`;}
document.getElementById('status').addEventListener('change',filter);
document.getElementById('zoom').addEventListener('change',event=>{
document.querySelectorAll('svg').forEach(svg=>{svg.setAttribute('width',Number(svg.dataset.width)*Number(event.target.value));
svg.setAttribute('height',Number(svg.dataset.height)*Number(event.target.value));});});filter();
</script></html>'''


def write_text_edge_report(reference, record, destination):
    """Require sealed image and consistent diagnostics; never mutate the record."""
    reference, destination = Path(reference), Path(destination)
    expected = record['reference_sha256']
    if sha256_file(reference) != expected:
        raise ValueError('TEXT_EDGE_REPORT_REFERENCE_CHANGED')
    with Image.open(reference) as image:
        if list(image.size) != record['image_size']:
            raise ValueError('TEXT_EDGE_REPORT_IMAGE_SIZE_CHANGED')
        diagnostic = verify_text_edges(image, record['result'])
        if 'edge_verification' in record and record['edge_verification'] != diagnostic:
            raise ValueError('TEXT_EDGE_REPORT_DIAGNOSTIC_CHANGED')
        rendered = render_report(image, record, diagnostic)
    if sha256_file(reference) != expected:
        raise ValueError('TEXT_EDGE_REPORT_REFERENCE_CHANGED')
    destination.write_text(rendered, encoding='utf-8')
    return {'policy': POLICY, 'file': destination.name, 'sha256': sha256_file(destination),
            'reference_sha256': expected, 'result_sha256': sha256_json(record['result']),
            'regions': len(diagnostic['regions']), 'counts': diagnostic['counts'],
            'model_calls': 0, 'boxes_changed': False, 'automatic_review_eligible': False}
