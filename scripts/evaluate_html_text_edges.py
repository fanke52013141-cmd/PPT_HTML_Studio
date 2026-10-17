"""Offline pixel diagnostics on sealed Agent outputs and independent controls.

No model calls, no box changes, no reclassification of original experiments.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def pixel_box(rect):
    return {'xPx':rect[0],'yPx':rect[1],'widthPx':rect[2]-rect[0],'heightPx':rect[3]-rect[1]}


def controls(folder, *, font_path='C:/Windows/Fonts/msyh.ttc',font_size=32):
    """Ink truth is from a separately rendered alpha mask, never model coordinates."""
    from html_text_edge_verification import inspect_text_edge
    from artifact_fingerprint import sha256_file
    rows=[];font=ImageFont.truetype(font_path,font_size)
    for style,bg,fg in [('light','#ffffff','#1b2430'),('grey','#e8ebef','#1b2430'),
                        ('reverse','#102030','#ffffff'),('colour','#ffffff','#3265b3')]:
        layer=Image.new('L',(420,150),0);ImageDraw.Draw(layer).text((90,45),'文字边缘核验',font=font,fill=255)
        ink=np.asarray(layer)>=128
        ys,xs=np.nonzero(ink);bounds=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
        for mode in ('complete','left','top','right','bottom','near_icon'):
            image=Image.new('RGB',layer.size,bg);image.paste(fg,(0,0,image.width,image.height),layer)
            rect=[bounds[0]-3,bounds[1]-3,bounds[2]+3,bounds[3]+3]
            if mode=='left':rect[0]=bounds[0]+3
            if mode=='top':rect[1]=bounds[1]+3
            if mode=='right':rect[2]=bounds[2]-3
            if mode=='bottom':rect[3]=bounds[3]-3
            if mode=='near_icon':
                ImageDraw.Draw(image).ellipse((rect[0]-28,rect[1]+4,rect[0]-8,rect[3]-4),fill='#3399cc')
                ImageDraw.Draw(image).line((rect[0]-5,rect[3]+9,rect[2]+5,rect[3]+9),fill='#555555',width=2)
            inside=np.zeros_like(ink);inside[rect[1]:rect[3],rect[0]:rect[2]]=True
            expected=bool(np.any(ink & ~inside))
            name=style+'-'+mode;path=folder/(name+'.png');path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
            checked=inspect_text_edge(image,pixel_box(rect))
            rows.append({'name':name,'reference_sha256':sha256_file(path),'strong_ink_outside':expected,
                         'font_file':Path(font_path).name,'font_size':font_size,
                         'outside_ink_pixels':int(np.count_nonzero(ink & ~inside)),
                         'original_box':pixel_box(rect),'diagnostic':checked})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layouts',type=Path,required=True)
    parser.add_argument('--realpage',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--heldout-controls',action='store_true',help='Unchanged algorithm, different fonts and sizes')
    args=parser.parse_args();out=args.out.resolve()
    if out.exists():raise ValueError('OUTPUT_MUST_BE_NEW')
    out.mkdir(parents=True)
    os.environ['PPT_STUDIO_DB_PATH']=str(out/'isolated.db');os.environ['PPT_STUDIO_RUNS_DIR']=str(out/'runs')
    from artifact_fingerprint import sha256_file,sha256_json
    from html_text_edge_verification import verify_text_edges,POLICY
    rows=[];started=time.monotonic()
    for name in ('dispersed-title','icon-source','multiline-note','relation-labels'):
        folder=args.layouts/name;path=folder/'after/result.json'
        record=json.loads(path.read_text(encoding='utf-8'));gold=json.loads((folder/'gold.json').read_text(encoding='utf-8'))
        image=folder/'reference.png'
        if sha256_file(image)!=gold['reference_sha256']:raise ValueError('REFERENCE_CHANGED')
        sealed=sha256_json(record)
        with Image.open(image) as source:checked=verify_text_edges(source,record['result'])
        assert sealed==sha256_json(record)
        rows.append({'kind':'saved_layout','name':name,'source_sha256':sha256_file(path),
                     'reference_sha256':gold['reference_sha256'],'diagnostic':checked})
    path=args.realpage/'localization-trials.json';trials=json.loads(path.read_text(encoding='utf-8'))
    for trial in trials:
        if trial['state']!='returned':continue
        image=args.realpage/f"localization-{trial['trial']}/reference.png";record=trial['record']
        if sha256_file(image)!=record['reference_sha256']:raise ValueError('REFERENCE_CHANGED')
        with Image.open(image) as source:checked=verify_text_edges(source,record['result'])
        rows.append({'kind':'saved_real_page','name':str(trial['trial']),'source_sha256':sha256_file(path),
                     'reference_sha256':record['reference_sha256'],'diagnostic':checked})
    for row in rows:write(out/(row['kind']+'-'+row['name']+'.json'),row)
    if args.heldout_controls:
        calibration=[]
        for face,size in (('msyh.ttc',18),('msyh.ttc',54),('simsun.ttc',18),('simsun.ttc',54)):
            calibration.extend(controls(out/'controls'/f'{face}-{size}',font_path='C:/Windows/Fonts/'+face,font_size=size))
    else:calibration=controls(out/'controls')
    write(out/'controls.json',calibration)
    positive=[r for r in calibration if r['strong_ink_outside']]
    negative=[r for r in calibration if not r['strong_ink_outside']]
    summary={'policy':POLICY,'model_calls':0,'boxes_changed':0,'source_records_changed':0,
        'source_code_sha256':sha256_file(ROOT/'html_text_edge_verification.py'),
        'elapsed_seconds':round(time.monotonic()-started,3),
        'control_set':'heldout_fonts_sizes' if args.heldout_controls else 'initial_msyh_32',
        'controls':{'clipped':len(positive),'possible_clip':sum(r['diagnostic']['status']=='possible_clip' for r in positive),
                    'clipped_uncertain':sum(r['diagnostic']['status']=='uncertain' for r in positive),
                    'clipped_not_detected':sum(r['diagnostic']['status']=='no_detected_clip' for r in positive),
                    'complete':len(negative),'complete_false_clip':sum(r['diagnostic']['status']=='possible_clip' for r in negative),
                    'complete_uncertain':sum(r['diagnostic']['status']=='uncertain' for r in negative)},
        'saved_cases':[{'kind':r['kind'],'name':r['name'],'status':r['diagnostic']['status'],
                        'counts':r['diagnostic']['counts']} for r in rows],
        'limit':'Offline edge evidence, not new Agent success, OCR verification, automatic repair or visual approval.'}
    write(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
