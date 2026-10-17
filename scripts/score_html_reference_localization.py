"""Score completed independent localization trials against predeclared regions."""
import argparse
import itertools
import json
from pathlib import Path
import statistics


def overlap(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    aa=(a[2]-a[0])*(a[3]-a[1]);bb=(b[2]-b[0])*(b[3]-b[1])
    return intersection/(aa+bb-intersection),intersection/bb


def pixel_rect(box):
    return [box['xPx'],box['yPx'],box['xPx']+box['widthPx'],box['yPx']+box['heightPx']]


def score_layers(record,gold):
    if record['reference_sha256']!=gold['reference_sha256']:raise ValueError('GOLD_REFERENCE_MISMATCH')
    targets={t['targetId']:t for t in record['result']['targets']}
    rows=[]
    for target,text_gold in gold['text_regions'].items():
        item=targets[target];lines=item.get('text_boxes',[])
        rects=[pixel_rect(b) for b in lines]
        envelope=([min(b[0] for b in rects),min(b[1] for b in rects),
                   max(b[2] for b in rects),max(b[3] for b in rects)] if rects else None)
        ti,tc=overlap(envelope,text_gold) if envelope else (0,0)
        predicted=item.get('container_box');expected=gold['containers'][target]
        ci,cc=overlap(pixel_rect(predicted),expected) if predicted and expected else (0,0)
        presence=item.get('container_presence','present' if predicted else 'absent')
        expected_presence='present' if expected else 'absent'
        text_pass=item['status']=='located' and ti>=gold['criteria']['minimum_iou'] and tc>=gold['criteria']['minimum_gold_coverage']
        container_pass=(item['status']=='located' and presence==expected_presence and
            (predicted is None if expected is None else predicted is not None and
             ci>=gold['criteria']['minimum_iou'] and cc>=gold['criteria']['minimum_gold_coverage']))
        rows.append({'targetId':target,'text_iou':ti,'text_coverage':tc,'text_pass':text_pass,
            'expected_container':expected_presence,'container_iou':ci,'container_coverage':cc,'container_pass':container_pass,
            'explicit_presence_claim':'container_presence' in item})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment',type=Path,required=True)
    parser.add_argument('--gold',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--layers-gold',type=Path)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('SCORE_OUTPUT_MUST_BE_NEW')
    gold=json.loads(args.gold.read_text(encoding='utf-8'))
    trials=json.loads((args.experiment/'localization-trials.json').read_text(encoding='utf-8'))
    layers_gold=json.loads(args.layers_gold.read_text(encoding='utf-8')) if args.layers_gold else None
    rows=[];boxes={}
    for trial in trials:
        row={'trial':trial['trial'],'state':trial['state'],'targets':[],'negative_pass':False}
        if trial['state']=='returned':
            record=trial['record']
            if record['reference_sha256']!=gold['reference_sha256']:raise ValueError('GOLD_REFERENCE_MISMATCH')
            targets={r['targetId']:r for r in record['result']['targets']}
            for target,box in gold['targets'].items():
                item=targets[target];pred=item.get('pixel_box')
                iou,coverage=overlap(pred,box) if pred else (0,0)
                row['targets'].append({'targetId':target,'iou':iou,'gold_coverage':coverage,
                    'pass':iou>=gold['criteria']['minimum_iou'] and coverage>=gold['criteria']['minimum_gold_coverage']})
                if pred:boxes.setdefault(target,[]).append(pred)
            negative=targets[gold['negative_target']]
            row['negative_pass']=negative['status']==gold['negative_expected'] and negative['box'] is None
            if layers_gold:row['layers']=score_layers(record,layers_gold)
        rows.append(row)
    result={'kind':'independent_localization_score','criteria':gold['criteria'],'trials':len(rows),
        'valid_trials':sum(r['state']=='returned' for r in rows),'positive_passes':sum(t['pass'] for r in rows for t in r['targets']),
        'positive_expected':len(rows)*len(gold['targets']),'negative_passes':sum(r['negative_pass'] for r in rows),
        'negative_expected':len(rows),'rows':rows,
        'pairwise_box_iou':{k:[overlap(a,b)[0] for a,b in itertools.combinations(values,2)] for k,values in boxes.items()},
        'median_seconds':statistics.median(t['elapsed_seconds'] for t in trials),
        'limit':gold['limitations']}
    if layers_gold:
        result['layers']={'text_passes':sum(t['text_pass'] for r in rows for t in r.get('layers',[])),
            'text_expected':len(rows)*len(layers_gold['text_regions']),
            'present_container_passes':sum(t['container_pass'] for r in rows for t in r.get('layers',[]) if t['expected_container']=='present'),
            'present_container_expected':len(rows)*sum(b is not None for b in layers_gold['containers'].values()),
            'absent_container_passes':sum(t['container_pass'] for r in rows for t in r.get('layers',[]) if t['expected_container']=='absent'),
            'absent_container_expected':len(rows)*sum(b is None for b in layers_gold['containers'].values()),
            'all_layers_pass_trials':sum(bool(r.get('layers')) and all(t['text_pass'] and t['container_pass'] for t in r['layers']) and r['negative_pass'] for r in rows),
            'limit':layers_gold['limitations']}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','pairwise_box_iou')},ensure_ascii=False))


if __name__=='__main__':main()
