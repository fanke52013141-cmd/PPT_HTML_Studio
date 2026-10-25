"""Sealed, provider-free comparison over fixed course/split/case repetitions."""
import json
import math
import statistics
from pathlib import Path
from artifact_fingerprint import sha256_file,sha256_json
from html_acceptance_criteria import safe
from scripts.score_html_reference_localization import overlap
from html_reference_localization import MappedLocations


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def checked(root,item):
    path=safe(root,item['path'])
    if sha256_file(path)!=item['sha256']:raise ValueError('DATA_OR_EVIDENCE_HASH_CHANGED:'+item['path'])
    return path


def validate_dataset(dataset,root):
    if dataset.get('format')!='hps.paired-dataset/0.1.0' or not dataset.get('label_version'):
        raise ValueError('DATASET_CONTRACT_INVALID')
    cases=dataset['cases']
    if not cases or len(cases)>2000 or len({c['id'] for c in cases})!=len(cases):raise ValueError('DATASET_CASES_INVALID')
    references={};courses={}
    for case in cases:
        if case['split'] not in ('development','holdout') or not case['course_id']:raise ValueError('DATASET_SPLIT_INVALID')
        prior=courses.setdefault(case['course_id'],case['split'])
        if prior!=case['split']:raise ValueError('COURSE_SPLIT_LEAKAGE')
        for key in ('reference','scene','gold'):checked(root,case[key])
        reference=case['reference']['sha256']
        if reference in references:raise ValueError('DUPLICATE_REFERENCE_LEAKAGE')
        references[reference]=case['id']
        gold=read(checked(root,case['gold']))
        if gold['reference_sha256']!=reference or gold['label_version']!=dataset['label_version']:
            raise ValueError('GOLD_IDENTITY_INVALID')
        if gold.get('authority') not in ('controlled_fixture','independent_human_labels'):
            raise ValueError('GOLD_AUTHORITY_INVALID')
        if dataset.get('provenance')!='controlled_fixture' and gold['authority']!='independent_human_labels':
            raise ValueError('REAL_SAMPLES_REQUIRE_HUMAN_LABELS')
        if gold['authority']=='independent_human_labels' and not gold.get('annotated_by'):
            raise ValueError('HUMAN_LABEL_REVIEWER_REQUIRED')
        scene=read(checked(root,case['scene']))
        ids={n['id'] for n in scene['nodes']}
        if set(gold['targets'])!=ids:raise ValueError('GOLD_TARGETS_INCOMPLETE')
        from html_reference_localization import mapped_reference_targets
        parts={t['targetId']:{p['partId'] for p in t['text_parts']} for t in mapped_reference_targets(scene)}
        from PIL import Image
        with Image.open(checked(root,case['reference'])) as image:width,height=image.size
        for target_id,target in gold['targets'].items():
            if target['status'] not in ('located','not_found','ambiguous'):raise ValueError('GOLD_STATUS_INVALID')
            if target['status']=='located' and (set(target['parts'])!=parts[target_id] or
                any(not regions or any(not isinstance(r.get('text'),str) or not r['text'] for r in regions)
                    for regions in target['parts'].values())):
                raise ValueError('GOLD_TEXT_PARTS_INCOMPLETE')
            boxes=[r['box'] for rows in target['parts'].values() for r in rows]
            if target.get('container') is not None:boxes.append(target['container'])
            for box in boxes:
                if (not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box)
                    or not 0<=box[0]<box[2]<=width or not 0<=box[1]<box[3]<=height):
                    raise ValueError('GOLD_BOX_INVALID')
    return cases


def localization_score(response,gold):
    parsed=MappedLocations.model_validate(response).model_dump()
    rows={r['targetId']:r for r in parsed['targets']}
    if len(rows)!=len(parsed['targets']) or set(rows)!=set(gold['targets']):raise ValueError('RESPONSE_TARGETS_INCOMPLETE')
    scores=[]
    for key,truth in gold['targets'].items():
        row=rows[key]
        if truth.get('status')!='located':
            scores.append(row['status']==truth['status'] and row['container_box'] is None
                          and all(not p['regions'] for p in row['part_regions']))
            continue
        if row['status']!='located':scores.append(False);continue
        parts={p['partId']:p for p in row['part_regions']}
        correct=len(parts)==len(row['part_regions']) and set(parts)==set(truth['parts'])
        for part,expected in truth['parts'].items():
            regions=parts.get(part,{}).get('regions',[])
            def matches(region,box):
                b=region['box'];pred=[b['xPx'],b['yPx'],b['xPx']+b['widthPx'],b['yPx']+b['heightPx']]
                iou,coverage=overlap(pred,box['box'])
                return region['text']==box['text'] and iou>=0.6 and coverage>=0.9
            def assign(i,used):
                return i==len(expected) or any(matches(region,expected[i]) and assign(i+1,used|{j})
                    for j,region in enumerate(regions) if j not in used)
            correct=correct and len(regions)==len(expected) and assign(0,set())
        container=truth.get('container')
        if container:
            b=row['container_box']
            correct=correct and row['container_presence']=='present' and bool(b)
            if b:correct=correct and overlap([b['xPx'],b['yPx'],b['xPx']+b['widthPx'],b['yPx']+b['heightPx']],container)[0]>=0.6
        else:correct=correct and row['container_presence']=='absent' and row['container_box'] is None
        scores.append(bool(correct))
    return {'correct':sum(scores),'expected':len(scores),'all_correct':all(scores)}


def number(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0


def pixel_distance(reference,current):
    """Pixel difference is descriptive; never semantic or aesthetic approval."""
    from PIL import Image,ImageChops,ImageStat
    with Image.open(reference) as a,Image.open(current) as b:
        if a.size!=b.size:return {'status':'incomparable_dimensions','normalized_mae':None}
        if a.width*a.height>16000000:raise ValueError('PIXEL_COMPARISON_BUDGET_EXCEEDED')
        means=ImageStat.Stat(ImageChops.difference(a.convert('RGB'),b.convert('RGB'))).mean
        return {'status':'measured','normalized_mae':sum(means)/(3*255)}


def compare(dataset,trials,root):
    cases=validate_dataset(dataset,root)
    if trials.get('dataset_sha256')!=sha256_json(dataset):raise ValueError('TRIAL_DATASET_STALE')
    repeat=trials.get('repetitions');arms=trials.get('arms')
    if type(repeat) is not int or not 1<=repeat<=20 or arms!=['before','after']:raise ValueError('PAIR_DESIGN_INVALID')
    expected={(c['id'],r,a) for c in cases for r in range(repeat) for a in arms}
    supplied=[(r['case_id'],r['repetition'],r['arm']) for r in trials['trials']]
    if len(supplied)!=len(set(supplied)) or set(supplied)!=expected:raise ValueError('PAIR_DENOMINATOR_INCOMPLETE')
    rows=[]
    for record in trials['trials']:
        case=next(c for c in cases if c['id']==record['case_id']);gold=read(checked(root,case['gold']))
        state=record['state']
        if state not in ('returned','failed','unknown','not_run'):raise ValueError('TRIAL_STATE_INVALID')
        row={k:record[k] for k in ('case_id','repetition','arm','state')}
        row.update(split=case['split'],course_id=case['course_id'],localization={'correct':0,'expected':len(gold['targets']),'all_correct':False},
            fidelity='pending_independent_review',engineering='not_verified',model_provenance='not_verified',
            seconds=record.get('seconds') if number(record.get('seconds')) else None,usage=None,cost=None)
        row['reference_pixel_distance']={'status':'not_run','normalized_mae':None}
        if state=='returned':
            response_path=checked(root,record['response'])
            try:row['localization']=localization_score(read(response_path),gold)
            except (ValueError,KeyError,TypeError):
                row['state']='failed';row['failure_reason']='invalid_localization_response'
            receipt=read(checked(root,record['receipt'])) if record.get('receipt') else {}
            # Only report measured transport values. Never turn provider metrics
            # or a self-reported pass into fidelity/human approval.
            if receipt:
                if receipt.get('reference_sha256')!=case['reference']['sha256'] or receipt.get('response_sha256')!=record['response']['sha256']:
                    raise ValueError('REQUEST_RECEIPT_IDENTITY_INVALID')
                row['model_provenance']='recorded_'+receipt.get('mode','unknown')
                row['usage']=receipt.get('usage') if isinstance(receipt.get('usage'),dict) else None
                row['cost']=receipt.get('cost') if number(receipt.get('cost')) else None
            if record.get('engineering'):
                report=read(checked(root,record['engineering']));coverage=report.get('coverage',{})
                row['engineering']='observed_pass' if report.get('passed') is True and not report.get('issues') and coverage.get('frame_complete') is True and coverage.get('fps')==30 and coverage.get('mode')=='output_frames' else 'observed_fail'
            if record.get('screenshot'):
                row['reference_pixel_distance']=pixel_distance(checked(root,case['reference']),checked(root,record['screenshot']))
        rows.append(row)
    summaries={}
    for split in ('development','holdout'):
        summaries[split]={}
        for arm in arms:
            selected=[r for r in rows if r['split']==split and r['arm']==arm]
            elapsed=[r['seconds'] for r in selected if r['seconds'] is not None]
            distances=[r['reference_pixel_distance']['normalized_mae'] for r in selected if r['reference_pixel_distance']['normalized_mae'] is not None]
            summaries[split][arm]={'expected':len(selected),'returned':sum(r['state']=='returned' for r in selected),
                'failed':sum(r['state']=='failed' for r in selected),'unknown':sum(r['state']=='unknown' for r in selected),
                'not_run':sum(r['state']=='not_run' for r in selected),
                'localization_correct':sum(r['localization']['correct'] for r in selected),
                'localization_expected':sum(r['localization']['expected'] for r in selected),
                'engineering_observed_pass':sum(r['engineering']=='observed_pass' for r in selected),
                'median_seconds':statistics.median(elapsed) if elapsed else None,
                'mean_reference_pixel_mae':statistics.mean(distances) if distances else None,
                'pixel_comparison_expected':len(selected),'pixel_comparison_measured':len(distances),
                'total_cost':sum(r['cost'] for r in selected) if selected and all(r['cost'] is not None for r in selected) else None,
                'fidelity':'pending_independent_review'}
    deltas={s:{k:summaries[s]['after'][k]-summaries[s]['before'][k] for k in ('returned','localization_correct','engineering_observed_pass')}
            for s in summaries}
    return {'format':'hps.paired-comparison/0.1.0','dataset_sha256':sha256_json(dataset),'summary':summaries,
            'paired_deltas':deltas,'rows':rows,'real_model_quality':'not_certified','human_visual_approval':'pending',
            'provider_calls':0,'holdout_policy':'Never select prompts/templates using holdout results.'}
