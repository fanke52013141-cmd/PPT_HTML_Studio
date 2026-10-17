"""Validate and crop saved pixel-location JSON locally; never calls a provider."""
import argparse
import json
import os
from pathlib import Path
import sys

from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('REPLAY_OUTPUT_MUST_BE_NEW')
    out=args.out.resolve();out.mkdir(parents=True)
    os.environ['PPT_STUDIO_DB_PATH']=str(out/'isolated.db')
    os.environ['PPT_STUDIO_RUNS_DIR']=str(out/'runs')
    from artifact_fingerprint import sha256_file
    from pipeline_lifecycle import write_json_atomic
    from html_reference_localization import validate_pixel_locations,validate_region_locations,validate_mapped_locations
    rows=[]
    for folder in sorted(args.experiment.glob('localization-*')):
        if not (folder/'audit/response.json').is_file():continue
        audit=folder/'audit';request=json.loads((audit/'request.json').read_text(encoding='utf-8'))
        payload=json.loads(request['user_prompt']);image=folder/'reference.png'
        if request['image_sha256']!=[sha256_file(image)]:raise ValueError('REFERENCE_CHANGED')
        dest=out/folder.name;dest.mkdir()
        row={'trial':int(folder.name.split('-')[-1]),'kind':'saved_response_replay',
             'request_sha256':sha256_file(audit/'request.json'),'response_sha256':sha256_file(audit/'response.json'),
             'elapsed_seconds':0}
        try:
            raw=json.loads((audit/'response.json').read_text(encoding='utf-8'))
            version=request['runtime_skill']['skills'][0]['version']
            if version not in ('0.2.0','0.2.1','0.3.0','0.4.0','0.4.1','0.5.0','0.5.1'):raise ValueError('UNSUPPORTED_LOCALIZATION_REPLAY_VERSION')
            validator=validate_mapped_locations if version in ('0.5.0','0.5.1') else validate_region_locations if version in ('0.3.0','0.4.0','0.4.1') else validate_pixel_locations
            result=validator(raw,payload['reference_targets'],payload['image_size'],
                **({'require_container_presence':True} if version in ('0.4.0','0.4.1') else {}))
            with Image.open(image) as source:
                if list(source.size)!=payload['image_size']:raise ValueError('IMAGE_SIZE_CHANGED')
                overlay=source.convert('RGB');draw=ImageDraw.Draw(overlay)
                for index,target in enumerate(result['targets']):
                    if target['box'] is None:continue
                    b=target['box'];rect=[b['xPx'],b['yPx'],b['xPx']+b['widthPx'],b['yPx']+b['heightPx']]
                    crop=dest/f'target-{index+1}.png';source.crop(rect).save(crop)
                    target.update(pixel_box=rect,crop=crop.name,crop_sha256=sha256_file(crop))
                    draw.rectangle(rect,outline='red',width=2);draw.text((rect[0]+2,rect[1]+2),str(index+1),fill='red')
                overlay.save(dest/'regions.png')
            row.update(state='returned',record={'result':result,'reference_sha256':sha256_file(image),
                'quality':'model_proposed_unverified_replay','human_approval':'pending','candidate_geometry_supplied':False})
        except ValueError as error:row.update(state='rejected',error=str(error)[:1200])
        rows.append(row)
    write_json_atomic(out/'localization-trials.json',rows)
    write_json_atomic(out/'manifest.json',{'kind':'offline_saved_response_replay','model_calls':0,'author_writes':0,
        'validator_sha256':sha256_file(ROOT/'html_reference_localization.py'),
        'limit':'Offline validation of saved responses under their registered region contract; no new provider request'})
    print(json.dumps([{'trial':r['trial'],'state':r['state']} for r in rows]))


if __name__=='__main__':main()
