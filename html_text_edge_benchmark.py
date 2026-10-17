"""Offline blinded line annotations and abstention-aware text-edge metrics."""
from __future__ import annotations

from html import escape
import json
import math
from pathlib import Path
import statistics

from PIL import Image

from artifact_fingerprint import sha256_file, sha256_json
from html_text_edge_report import _png, _rect
from html_text_edge_verification import verify_text_edges

POLICY = 'text-edge-human-benchmark/0.1.0'
LABELER = Path(__file__).parent/'scripts/assets/text_edge_labeler.js'


def _json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def prepare(cases, destination):
    """Create unlabelled tasks; algorithm predictions are outside the blind HTML."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError('BENCHMARK_OUTPUT_MUST_BE_NEW')
    samples, predictions, images, sources = [], [], {}, []
    case_ids = set()
    for case_id, reference, record_path in cases:
        if not case_id or case_id in case_ids:
            raise ValueError('BENCHMARK_DUPLICATE_CASE')
        case_ids.add(case_id)
        reference, record_path = Path(reference), Path(record_path)
        record_hash = sha256_file(record_path)
        record = json.loads(record_path.read_text(encoding='utf-8'))
        image_hash = sha256_file(reference)
        if image_hash != record['reference_sha256']:
            raise ValueError('BENCHMARK_REFERENCE_CHANGED')
        with Image.open(reference) as image:
            if list(image.size) != record['image_size']:
                raise ValueError('BENCHMARK_IMAGE_SIZE_CHANGED')
            diagnostic = verify_text_edges(image, record['result'])
            if 'edge_verification' in record and record['edge_verification'] != diagnostic:
                raise ValueError('BENCHMARK_DIAGNOSTIC_CHANGED')
            images[image_hash] = _png(image)
            targets = {t['targetId']: t for t in record['result']['targets']}
            for row in diagnostic['regions']:
                target = targets[row['targetId']]
                part = next(p for p in target['part_regions'] if p['partId'] == row['partId'])
                b = row['box']
                rect = [b['xPx'], b['yPx'], b['xPx']+b['widthPx'], b['yPx']+b['heightPx']]
                sample = {'case_id': case_id, 'reference_sha256': image_hash,
                          'result_sha256': sha256_json(record['result']),
                          'targetId': row['targetId'], 'partId': row['partId'],
                          'region_index': row['region_index'], 'proposed_bounds': rect,
                          'image_size': record['image_size'],
                          'text': part['regions'][row['region_index']]['text']}
                sample['sample_id'] = sha256_json(sample)
                samples.append(sample)
                predictions.append({'sample_id': sample['sample_id'], 'status': row['status']})
        if sha256_file(reference) != image_hash or sha256_file(record_path) != record_hash:
            raise ValueError('BENCHMARK_SOURCE_CHANGED')
        sources.append({'case_id': case_id, 'record_sha256': record_hash,
                        'reference_sha256': image_hash,
                        'unlocated_targets': [t['targetId'] for t in record['result']['targets'] if t['status'] != 'located']})
    samples.sort(key=lambda s: s['sample_id'])
    package = {'policy': POLICY, 'samples': samples, 'sources': sources,
               'unique_reference_images': len(images), 'cases': len(cases),
               'sample_scope': 'proposed_line_regions_only',
               'predictions_sha256': sha256_json(predictions),
               'labeler_sha256': sha256_file(LABELER)}
    package_hash = sha256_json(package)
    predictions = {'package_sha256': package_hash, 'regions': predictions}
    rendered = _render(package, package_hash, images)
    destination.mkdir(parents=True)
    _json(destination/'package.json', package)
    _json(destination/'predictions.json', predictions)
    _json(destination/'annotations-template.json', {
        'policy': POLICY, 'package_sha256': package_hash, 'reviewer_id': '',
        'declared_human_blind_review': False, 'timing_protocol': 'foreground_explicit_start/0.1.0', 'rows': []})
    (destination/'blind-review.html').write_text(rendered, encoding='utf-8')
    return {'state': 'pending_human_review', 'package_sha256': package_hash,
            'samples': len(samples), 'unique_reference_images': len(images), 'cases': len(cases),
            'model_calls': 0, 'source_records_changed': 0}


def _render(package, package_hash, images):
    cards = []
    definitions = []
    for image_hash, data in images.items():
        if not any(s['reference_sha256']==image_hash for s in package['samples']):
            continue
        width, height = next(s['image_size'] for s in package['samples'] if s['reference_sha256']==image_hash)
        definitions.append(f'<image id="reference-{image_hash}" href="{data}" width="{width}" height="{height}"/>')
    for index, sample in enumerate(package['samples']):
        rect = sample['proposed_bounds']
        width, height = sample['image_size']
        margin = max(64, min(160, (rect[3]-rect[1])*2))
        window = [max(0, rect[0]-margin), max(0, rect[1]-margin),
                  min(width, rect[2]+margin), min(height, rect[3]+margin)]
        # Show wider context than the diagnostic window, independent of its ink/status.
        vw, vh = window[2]-window[0], window[3]-window[1]
        image = (f'<use href="#reference-{sample["reference_sha256"]}" '
                 f'x="{-window[0]}" y="{-window[1]}"/>')
        cards.append(f'''<article data-index="{index}" hidden>
<h2>样本 {index+1} / {len(package['samples'])}</h2>
<p>{escape(sample['targetId'])} / {escape(sample['partId'])} / 行索引 {sample['region_index']}</p>
<p>待核对转录（可能有误）：{escape(sample['text'])}</p>
<p>原框 [左, 上, 右, 下]：{rect}；上下文左上原点：{window[:2]}</p>
<div class="viewport"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}"
width="{vw}" height="{vh}" data-width="{vw}" data-height="{vh}" data-origin-x="{window[0]}" data-origin-y="{window[1]}" role="img" aria-label="原图上下文及被评估文字框">
{image}{_rect(rect,window,'#dc2626')}</svg></div>
<details><summary>查看完整原图</summary><div class="viewport"><svg xmlns="http://www.w3.org/2000/svg"
viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="完整原始参考图">
<use href="#reference-{sample['reference_sha256']}"/></svg></div></details></article>''')
    data = json.dumps({'package_sha256': package_hash, 'samples': package['samples']}, ensure_ascii=False)
    data = data.replace('<', '\\u003c').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>逐行文字盲审标注</title><style>
body{font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:auto;padding:24px;color:#172033;background:#f8fafc}
article,section,header{background:white;border:1px solid #cbd5e1;border-radius:10px;padding:18px;margin:16px 0}
input,select,button{font:inherit;padding:8px;margin:4px}input[type=number]{width:100px}label{display:inline-block}
.viewport{overflow:auto;background:#e2e8f0;padding:12px}svg{display:block;max-width:none}svg[data-origin-x]{touch-action:none;cursor:crosshair}img{max-width:100%;height:auto}
p{overflow-wrap:anywhere}button:disabled{opacity:.5}[hidden]{display:none!important}
</style><header><h1>逐行文字盲审标注</h1>
<p>先独立核对原图。红框是被评估的原框，页内没有算法预测。请填写完整文字墨迹的原图像素边界，不照抄红框。
完整文字在红框之外标“截字”，在红框内标“完整”；无法判断或身份有误请单独标记。</p>
<p>点击开始后计时；暂停、隐藏页面或失焦即停止，恢复需再次点击开始。本页不自动保存，请完成后导出JSON。</p>
<label>复核者代号 <input id="reviewer" maxlength="80"></label>
<label><input type="checkbox" id="human">我本人已独立核对，未参考算法诊断</label>
<p id="progress" aria-live="polite"></p></header><svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" aria-hidden="true"><defs>''' + ''.join(definitions) + '</defs></svg><main>' + ''.join(cards) + '''</main>
<section id="editor"><button id="start" type="button">开始／继续计时</button><button id="pause" type="button">暂停</button>
<span id="timer" aria-live="polite">尚未开始</span>
<label>局部放大 <select id="zoom"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select></label>
<p><label>判断 <select id="label"><option value="">请选择</option><option value="clipped">截字</option><option value="complete">完整</option><option value="unjudgeable">无法判断</option><option value="identity_mismatch">文字身份有误</option></select></label></p>
<p>完整文字墨迹边界（原图像素，无法判断／身份有误时留空）：局部图上拖框可填写，也可直接输入。</p>
<label>左 <input id="left" type="number" min="0" step="1"></label><label>上 <input id="top" type="number" min="0" step="1"></label>
<label>右 <input id="right" type="number" min="1" step="1"></label><label>下 <input id="bottom" type="number" min="1" step="1"></label>
<p><label>复核备注 <input id="notes" maxlength="1000"></label></p>
<button id="save" type="button">保存本行并下一行</button><button id="previous" type="button">上一行</button>
<button id="next" type="button">下一行</button><button id="export" type="button">导出标注JSON</button>
<p id="message" role="status"></p><a id="download" hidden>下载标注JSON</a></section>
<script>const REVIEW_DATA=''' + data + ';</script><script>' + LABELER.read_text(encoding='utf-8') + '</script></html>'


def score(package, annotations, predictions):
    """Missing human truth stays missing; uncertain predictions are abstentions."""
    package_hash = sha256_json(package)
    if package.get('policy') != POLICY or annotations.get('policy') != POLICY:
        raise ValueError('BENCHMARK_POLICY_MISMATCH')
    if annotations.get('package_sha256') != package_hash or predictions.get('package_sha256') != package_hash:
        raise ValueError('BENCHMARK_PACKAGE_MISMATCH')
    if sha256_json(predictions['regions']) != package.get('predictions_sha256'):
        raise ValueError('BENCHMARK_PREDICTIONS_CHANGED')
    samples = {s['sample_id']: s for s in package['samples']}
    if len(samples) != len(package['samples']):
        raise ValueError('BENCHMARK_DUPLICATE_SAMPLE')
    for sample in samples.values():
        if sha256_json({k:v for k,v in sample.items() if k != 'sample_id'}) != sample['sample_id']:
            raise ValueError('BENCHMARK_SAMPLE_CHANGED')
    predicted = {r['sample_id']: r['status'] for r in predictions['regions']}
    if (len(predicted) != len(predictions['regions']) or set(predicted) != set(samples)
            or any(s not in ('possible_clip','uncertain','no_detected_clip') for s in predicted.values())):
        raise ValueError('BENCHMARK_PREDICTIONS_INVALID')
    rows = annotations['rows']
    if rows and (annotations.get('declared_human_blind_review') is not True
                 or not isinstance(annotations.get('reviewer_id'),str) or not annotations['reviewer_id'].strip()
                 or annotations.get('timing_protocol') != 'foreground_explicit_start/0.1.0'):
        raise ValueError('BENCHMARK_HUMAN_DECLARATION_REQUIRED')
    seen, times = set(), []
    tp=fp=fn=tn=positive=negative=abstain_positive=abstain_negative=unjudgeable=mismatch=0
    for row in rows:
        key=row['sample_id']
        if key not in samples or key in seen:
            raise ValueError('BENCHMARK_ANNOTATION_ID_INVALID')
        seen.add(key)
        elapsed=row.get('active_review_ms')
        if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<=0:
            raise ValueError('BENCHMARK_REVIEW_TIME_INVALID')
        times.append(elapsed/1000)
        label=row.get('label')
        if label not in ('clipped','complete','unjudgeable','identity_mismatch'):
            raise ValueError('BENCHMARK_LABEL_INVALID')
        bounds=row.get('truth_bounds')
        if label in ('unjudgeable','identity_mismatch'):
            if bounds is not None:
                raise ValueError('BENCHMARK_UNJUDGED_BOUNDS')
            unjudgeable+=label=='unjudgeable';mismatch+=label=='identity_mismatch'
            continue
        if (not isinstance(bounds,list) or len(bounds)!=4 or any(type(v) is not int for v in bounds)
                or not 0<=bounds[0]<bounds[2]<=samples[key]['image_size'][0]
                or not 0<=bounds[1]<bounds[3]<=samples[key]['image_size'][1]):
            raise ValueError('BENCHMARK_TRUTH_BOUNDS_INVALID')
        original=samples[key]['proposed_bounds']
        clipped=not(original[0]<=bounds[0] and original[1]<=bounds[1]
                    and bounds[2]<=original[2] and bounds[3]<=original[3])
        if clipped!=(label=='clipped'):
            raise ValueError('BENCHMARK_LABEL_BOUNDS_CONFLICT')
        positive+=clipped;negative+=not clipped
        prediction=predicted[key]
        if prediction=='uncertain':
            abstain_positive+=clipped;abstain_negative+=not clipped
        elif prediction=='possible_clip':
            tp+=clipped;fp+=not clipped
        else:
            fn+=clipped;tn+=not clipped
    def ratio(a,b):return a/b if b else None
    judged=positive+negative
    return {'policy':POLICY,'state':'pending_human_review' if not rows else
            'partially_reviewed' if len(rows)<len(samples) else 'reviewed',
            'package_sha256':package_hash,'samples':len(samples),'labelled':len(rows),'unlabelled':len(samples)-len(rows),
            'unique_reference_images':len({s['reference_sha256'] for s in package.get('sources',samples.values())}),
            'case_count':len({s['case_id'] for s in package.get('sources',samples.values())}),
            'unlocated_target_observations':sum(len(s.get('unlocated_targets',[])) for s in package.get('sources',[])),
            'truth':{'clipped':positive,'complete':negative,'unjudgeable':unjudgeable,'identity_mismatch':mismatch},
            'decisive':{'tp':tp,'fp':fp,'fn':fn,'tn':tn,
                        'precision':ratio(tp,tp+fp),'false_positive_rate':ratio(fp,fp+tn),
                        'false_negative_rate':ratio(fn,tp+fn),'coverage':ratio(tp+fp+fn+tn,judged)},
            'abstentions':{'clipped':abstain_positive,'complete':abstain_negative},
            'alarm_recall':ratio(tp,positive),'review_routing_recall':ratio(tp+abstain_positive,positive),
            'review_routing_complete_rate':ratio(fp+abstain_negative,negative),
            'timing':{'source':'self_declared_human_foreground' if rows else None,
                      'total_active_seconds':sum(times) if times else None,
                      'median_active_seconds':statistics.median(times) if times else None,
                      'time_improvement':None},
            'model_calls':0,'automatic_review_eligible':False,
            'limit':'Proposed regions only; self-declared single reviewer, no identity certification, no independent second review or paired timing baseline.'}
