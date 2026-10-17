"""Controlled cross-layout localization benchmark, not production slide artwork.

Gold is rendered and sealed before requests, never supplied to the Agent.
Default is offline fixture construction; --live explicitly enables eight calls.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def build_cases(out):
    """Fixed Chinese raster fixtures; boxes measured from font ink, not Agent output."""
    from artifact_fingerprint import sha256_file,sha256_json
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',30)
    cases=[]
    specs=[
        ('dispersed-title',{'id':'header','type':'header','number':'02','title':'正式定义'},
         [('number','02',(55,65)),('title','正式定义',(430,65))],None,False),
        ('icon-source',{'id':'source','type':'text','text':'来源：公开办法'},
         [('text','来源：公开办法',(235,175))],[55,125,945,260],True),
        ('multiline-note',{'id':'note','type':'text','text':'第一行正文第二行正文'},
         [('text','第一行正文',(110,100)),('text','第二行正文',(110,235))],None,False),
        ('relation-labels',{'id':'relation','type':'summary','from':{'text':'下级机关'},
                            'to':{'text':'上级机关'},'term':'公开遴选','takeaway':'公开择优选人'},
         [('from/text','下级机关',(90,90)),('term','公开遴选',(420,190)),
          ('to/text','上级机关',(740,90)),('takeaway','公开择优选人',(390,335))],
         [40,35,960,435],False),
    ]
    for name,node,placements,container,icon in specs:
        folder=out/name;folder.mkdir(parents=True)
        image=Image.new('RGB',(1000,500),'white');draw=ImageDraw.Draw(image)
        if container:draw.rounded_rectangle(container,radius=12,fill='#e8ebef')
        if icon:draw.ellipse((100,160,160,220),fill='#3d6f98')
        if name=='relation-labels':
            draw.line((280,115,715,115),fill='#555555',width=4)
            draw.polygon([(715,115),(695,105),(695,125)],fill='#555555')
        parts={}
        for key,text,xy in placements:
            draw.text(xy,text,font=font,fill='#1b2430')
            # PIL textbbox uses ink bounds; margin covers antialias edge.
            b=draw.textbbox(xy,text,font=font)
            parts.setdefault(key,[]).append([b[0]-2,b[1]-2,b[2]+2,b[3]+2])
        image.save(folder/'reference.png')
        missing={'id':'missing-control','type':'text','text':'不存在的火星基地987654321'}
        scene={'nodes':[node,missing]}
        gold={'reference_sha256':sha256_file(folder/'reference.png'),'image_size':[1000,500],
              'targetId':node['id'],'parts':parts,'container':container,
              'minimum_iou':0.6,'minimum_gold_coverage':0.9,'missing':'missing-control'}
        write(folder/'scene.json',scene);write(folder/'gold.json',gold)
        cases.append({'name':name,'folder':folder,'scene':scene,'gold':gold})
    write(out/'fixture-manifest.json',{'kind':'controlled_raster_benchmark','production_artwork':False,
        'cases':[{'name':c['name'],'reference_sha256':c['gold']['reference_sha256'],
                  'scene_sha256':sha256_json(c['scene']),'gold_sha256':sha256_file(c['folder']/'gold.json')}
                 for c in cases], 'gold_sent_to_model':False,'repetitions_per_arm':1,
        'limit':'Four controlled layouts do not establish real-slide accuracy or repeated-call stability.'})
    return cases


def envelope(rects):
    return [min(b[0] for b in rects),min(b[1] for b in rects),
            max(b[2] for b in rects),max(b[3] for b in rects)] if rects else None


def score(result,gold):
    from scripts.score_html_reference_localization import overlap,pixel_rect
    rows={r['targetId']:r for r in result['targets']}
    target=rows[gold['targetId']]
    truth=envelope([b for boxes in gold['parts'].values() for b in boxes])
    predicted=envelope([pixel_rect(b) for b in target.get('text_boxes',[])])
    def matches(a,b):
        return bool(a and b and overlap(a,b)[0]>=gold['minimum_iou'] and
                    overlap(a,b)[1]>=gold['minimum_gold_coverage'])
    def complete_lines(predicted,expected):
        # Distinct ink lines require distinct regions; a giant union cannot hide gaps.
        def assign(index,used):
            if index==len(expected):return True
            return any(matches(box,expected[index]) and assign(index+1,used|{j})
                       for j,box in enumerate(predicted) if j not in used)
        return assign(0,set())
    container=target.get('container_box')
    cp=(matches(pixel_rect(container),gold['container']) if container else False) if gold['container'] else (
        target.get('container_presence')=='absent' and container is None)
    parts={p['partId']:p for p in target.get('part_regions',[])}
    part_scores={key:complete_lines([pixel_rect(r['box']) for r in parts.get(key,{}).get('regions',[])],boxes)
                 for key,boxes in gold['parts'].items()} if parts else None
    missing=rows[gold['missing']]
    negative=missing['status']=='not_found' and missing['box'] is None
    text=target['status']=='located' and matches(predicted,truth)
    lines=complete_lines([pixel_rect(b) for b in target.get('text_boxes',[])],
                         [b for boxes in gold['parts'].values() for b in boxes])
    return {'text_envelope_pass':text,'text_lines_pass':lines,'container_pass':cp,'missing_pass':negative,
            'part_geometry':part_scores,'joint_pass':bool(text and lines and cp and negative and
                (all(part_scores.values()) if part_scores is not None else True))}


def provider(out):
    """Read-only existing connection, same GLM low effort and output budget."""
    import sqlite3
    from types import SimpleNamespace
    from credential_store import CredentialDependencies,configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies,configure_model_connection_dependencies
    from project_model_binding_service import freeze_project_models
    import json_llm_service as llm
    def read(path):return json.loads(path.read_text(encoding='utf-8'))
    def readonly(*_):raise ValueError('READ_ONLY_CONFIGURATION')
    configure_credential_dependencies(CredentialDependencies(read_store=lambda:read(ROOT/'data/credentials.json'),write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(read_registry=lambda:read(ROOT/'data/model_connections.json'),write_registry=readonly))
    with sqlite3.connect((ROOT/'data/projects.db').as_uri()+'?mode=ro',uri=True) as db:
        settings=dict(db.execute("select key,value from settings where key in ('html_visual_connection_id','html_planning_connection_id')"))
    model=freeze_project_models(SimpleNamespace(run_dir=str(out),account_id='default',
        creation_config_package_id=None,creation_config_snapshot_json=None),setting=settings.get).text.require_ready()
    write(out/'model.json',model.summary())
    attempts=[];factory=llm.get_openai_client
    def client_factory(**kw):
        client=factory(**kw);create=client.chat.completions.create
        def capture(**request):
            if len(attempts)>=16:raise RuntimeError('HTTP_BUDGET_EXHAUSTED')
            attempts.append({'state':'intent','reasoning_effort':request.get('reasoning_effort'),
                             'max_tokens':request.get('max_tokens')})
            write(out/'http-attempts.json',attempts)
            try:
                value=create(**request);attempts[-1]['state']='returned_or_stream_opened';return value
            except Exception:
                attempts[-1]['state']='unknown';raise
            finally:write(out/'http-attempts.json',attempts)
        client.chat.completions.create=capture
        return client
    llm.get_openai_client=client_factory
    def generate(**kw):return llm.generate_json_with_configured_llm(**kw,model_binding=model,stream_output=True)
    return generate,attempts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--after-only',action='store_true',help='Distinct bounded protocol-fix experiment; preserves previous failures')
    args=parser.parse_args();out=args.out.resolve()
    if out.exists():raise ValueError('OUTPUT_MUST_BE_NEW_NO_UNKNOWN_RETRY')
    out.mkdir(parents=True)
    os.environ['PPT_STUDIO_DB_PATH']=str(out/'isolated.db')
    os.environ['PPT_STUDIO_RUNS_DIR']=str(out/'runs')
    cases=build_cases(out)
    if not args.live:
        print('Four fixtures sealed; no provider calls. --live: at most 8 requests (4 with --after-only).');return
    from artifact_fingerprint import sha256_file
    from html_reference_localization import localize_reference,reference_targets,ContainerLocations,validate_region_locations
    from html_visual_review_service import HtmlReviewDependencies
    generate,attempts=provider(out);trials=[]
    old_body=ROOT/'config/html_runtime_skills/design-reference-localization-0.4.1.md'
    registry=json.loads((ROOT/'config/html_runtime_skills.json').read_text(encoding='utf-8'))
    version=next(s['version'] for s in registry['skills'] if s['stage']=='design_reference_localization')
    write(out/'experiment.json',{'adapter_requests_maximum':4 if args.after_only else 8,'http_attempts_maximum':16,
        'baseline_prompt_sha256':sha256_file(old_body),'baseline':'0.4.1','after':version,
        'source_sha256':{p:sha256_file(ROOT/p) for p in ('html_reference_localization.py','html_design_agent.py',
            'config/html_runtime_skills.json')},'author_writes':0,'production_project_writes':0})
    stop=False
    for index,case in enumerate(cases):
        for arm in (('after',) if args.after_only else ('before','after') if index%2==0 else ('after','before')):
            folder=case['folder']/arm;folder.mkdir();row={'case':case['name'],'arm':arm,'state':'intent'}
            trials.append(row);write(out/'trials.json',trials);started=time.monotonic();count=len(attempts)
            def generator(**kw):
                kw['artifact_prefix']=case['name']+'-'+arm+'-'+kw['artifact_prefix'];return generate(**kw)
            try:
                if arm=='after':
                    record=localize_reference(case['scene'],case['folder']/'reference.png',folder=folder,
                        run_dir=out,deps=HtmlReviewDependencies(ROOT,generator));result=record['result']
                else:
                    payload={'reference_targets':reference_targets(case['scene']),
                        'box_coordinates':'original_image_pixels','image_size':[1000,500],
                        'task':'Find each identity in the reference image independently; no HTML position is supplied.'}
                    # Baseline intentionally preserves its omitted-number input defect.
                    for target in payload['reference_targets']:target['identity'].pop('number',None)
                    request={'system_prompt':old_body.read_text(encoding='utf-8'),
                        'user_prompt':json.dumps(payload,ensure_ascii=False),
                        'schema_hint':json.dumps(ContainerLocations.model_json_schema(),ensure_ascii=False)}
                    write(folder/'request.json',request)
                    raw=generator(**request,image_paths=[str(case['folder']/'reference.png')],run_dir=str(out),
                        artifact_prefix='reference-localization',request_timeout=600,reasoning_effort_override='low')
                    write(folder/'response.json',raw)
                    result=validate_region_locations(raw,payload['reference_targets'],[1000,500],require_container_presence=True)
                    write(folder/'result.json',{'result':result,'reference_sha256':case['gold']['reference_sha256']})
                if sha256_file(case['folder']/'reference.png')!=case['gold']['reference_sha256']:
                    raise ValueError('BENCHMARK_REFERENCE_CHANGED')
                row.update(state='returned',score=score(result,case['gold']))
            except Exception as error:
                state='rejected' if (folder/'response.json').exists() else 'unknown' if len(attempts)>count else 'not_submitted'
                row.update(state=state,error_type=type(error).__name__)
                write(folder/'failure.json',{'state':state,'error_type':type(error).__name__,
                      'message':str(error)[:800] if state=='rejected' else 'No complete response; do not resubmit.'})
                stop=state in ('unknown','not_submitted')
            row['elapsed_seconds']=round(time.monotonic()-started,3);write(out/'trials.json',trials)
            print(json.dumps(row,ensure_ascii=False),flush=True)
            if stop:break
        if stop:break
    summary={}
    for arm in ('before','after'):
        rows=[r for r in trials if r['arm']==arm]
        summary[arm]={'attempted':len(rows),'valid':sum(r['state']=='returned' for r in rows),
            **{k:sum(bool(r.get('score',{}).get(k)) for r in rows)
               for k in ('text_envelope_pass','text_lines_pass','container_pass','missing_pass','joint_pass')},
            'median_seconds':statistics.median(r['elapsed_seconds'] for r in rows) if rows else None}
    write(out/'summary.json',{'arms':summary,'stopped':stop,'http_attempts':len(attempts),
        'limit':'One sample per controlled layout; not repeated-call stability or production visual approval.'})


if __name__=='__main__':main()
