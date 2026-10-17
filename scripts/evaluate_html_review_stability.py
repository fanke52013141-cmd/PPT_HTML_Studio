"""Paired, first-review-only trials on sealed screenshots; never repairs a page."""
from __future__ import annotations
import argparse
import itertools
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--coverage-baseline',type=Path,
                        help='Sealed 0.8.0 evaluation directory; compare with coverage policy rather than archived 0.6.0')
    parser.add_argument('--facts',action='store_true',help='Evaluate single facts protocol instead of local windows')
    parser.add_argument('--localization',action='store_true',help='Three reference-only trials with missing-object negative control')
    args=parser.parse_args()
    if not args.live:
        print('3 reference-only localization requests maximum; no author writes' if args.localization else
              '2 fixed screenshots x 2 policies x 3 trials = 12 requests maximum; no repairs or author writes')
        return
    out=args.out.resolve()
    if out.exists():raise ValueError('OUTPUT_MUST_BE_NEW: never retry unknown trials')
    out.mkdir(parents=True)
    os.environ['PPT_STUDIO_DB_PATH']=str(out/'isolated.db')
    os.environ['PPT_STUDIO_RUNS_DIR']=str(out/'isolated-runs')
    from artifact_fingerprint import sha256_file,sha256_json
    from pipeline_lifecycle import write_json_atomic
    from credential_store import CredentialDependencies,configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies,configure_model_connection_dependencies
    from project_model_binding_service import freeze_project_models
    from html_visual_review_service import HtmlReviewDependencies,HtmlReviewError
    from html_design_agent import review_fidelity,validate_fidelity
    import json_llm_service as llm
    archive=args.archive.resolve()
    cases=[]
    for index,known in ((0,['stat-1','stat-2','stat-3','caption']),(1,['caption'])):
        folder=archive/str(index)
        request=read(folder/'fidelity/request.json');payload=json.loads(request['user_prompt'])
        record=read(folder/'fidelity/result.json');shot=folder/'candidate.png';reference=archive/'reference.png'
        if sha256_file(shot)!=record['screenshot_sha256'] or sha256_file(reference)!=record['design_sha256']:
            raise ValueError('ARCHIVED_IMAGES_CHANGED')
        for key in ('prior_open_issues','current_target_evidence','previous_target_evidence','review_checklist'):payload.pop(key,None)
        scene=read(archive/'allocation-capacity-repair.json')['scene'];scene['nodes']=payload['objects']
        if sha256_json(scene)!=record['scene_sha256']:raise ValueError('ARCHIVED_SCENE_CHANGED')
        if args.coverage_baseline:
            request=read(args.coverage_baseline/f'fixed-{index}-after-0/review/request.json')
            if request['image_sha256'] != [sha256_file(reference),sha256_file(shot)]:
                raise ValueError('BASELINE_IMAGE_MISMATCH')
            payload=json.loads(request['user_prompt'])
            if payload['objects'] != scene['nodes']:raise ValueError('BASELINE_OBJECT_MISMATCH')
            if request['runtime_skill']['skills'][0]['version'] != '0.8.0':raise ValueError('BASELINE_POLICY_MISMATCH')
        cases.append({'name':f'fixed-{index}','known_typography_targets':known,'request':request,'payload':payload,
            'scene':scene,
            'reference':reference,'shot':shot,'reference_sha256':sha256_file(reference),'screenshot_sha256':sha256_file(shot)})
    write_json_atomic(out/'manifest.json',{'profile':'reference-localization/0.5.0' if args.localization else
        'first-review-facts/0.1.0' if args.facts else 'first-review-stability/0.1.0','author_writes':0,
        'cases':[{k:c[k] for k in ('name','known_typography_targets','reference_sha256','screenshot_sha256')} for c in cases],
        'known_issue_scope':'only verified text alignment defects; other detections are not automatically false positives',
        'adapter_requests_maximum':3 if args.localization else 12,'repetitions':3})
    def readonly(*_):raise ValueError('Read only provider configuration')
    configure_credential_dependencies(CredentialDependencies(read_store=lambda:read(ROOT/'data/credentials.json'),write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(read_registry=lambda:read(ROOT/'data/model_connections.json'),write_registry=readonly))
    with sqlite3.connect((ROOT/'data/projects.db').as_uri()+'?mode=ro',uri=True) as db:
        settings=dict(db.execute("select key,value from settings where key in ('html_visual_connection_id','html_planning_connection_id')"))
    model=freeze_project_models(SimpleNamespace(run_dir=str(archive.parents[5]),account_id='default',
        creation_config_package_id=None,creation_config_snapshot_json=None),setting=settings.get).text.require_ready()
    write_json_atomic(out/'model.json',model.summary())
    http=[]
    factory=llm.get_openai_client
    def client_factory(**kwargs):
        client=factory(**kwargs)
        create=client.chat.completions.create
        def capture(**request):
            if len(http)>=24:raise RuntimeError('HTTP_BUDGET_EXHAUSTED')
            event={'state':'intent','stream':request.get('stream'),
                   'reasoning_effort':request.get('reasoning_effort'),'max_tokens':request.get('max_tokens')}
            http.append(event);write_json_atomic(out/'http-attempts.json',http)
            try:
                value=create(**request);event['state']='stream_opened' if request.get('stream') else 'returned';return value
            except Exception:
                event['state']='unknown';raise
            finally:write_json_atomic(out/'http-attempts.json',http)
        client.chat.completions.create=capture
        return client
    llm.get_openai_client=client_factory
    if args.localization:
        from html_reference_localization import localize_reference
        import copy,shutil
        rows=[]
        for index in range(3):
            folder=out/f'localization-{index}';folder.mkdir()
            shutil.copy2(cases[0]['reference'],folder/'reference.png')
            current=copy.deepcopy(cases[0]['scene'])
            current['nodes'].append({'id':'missing-control','type':'text','runs':[{'text':'火星基地累计登陆人数：987654321','emphasis':False}]})
            row={'trial':index,'state':'intent'};rows.append(row);write_json_atomic(out/'localization-trials.json',rows)
            started=time.monotonic();http_before=len(http)
            def generator(**kw):
                kw['artifact_prefix']=f"localization-{index}-{kw['artifact_prefix']}"
                return llm.generate_json_with_configured_llm(**kw,model_binding=model,stream_output=True)
            try:
                record=localize_reference(current,folder/'reference.png',folder=folder/'audit',run_dir=out,
                    deps=HtmlReviewDependencies(ROOT,generator))
                row.update(state='returned',record=record)
            except Exception as error:
                returned=(folder/'audit/response.json').is_file()
                row.update(state='rejected' if returned else 'unknown' if len(http)>http_before else 'not_submitted',error_type=type(error).__name__)
            row['elapsed_seconds']=round(time.monotonic()-started,3)
            write_json_atomic(out/'localization-trials.json',rows)
            if row['state'] in ('unknown','not_submitted'):break
        print(json.dumps([{'trial':r['trial'],'state':r['state'],'elapsed_seconds':r['elapsed_seconds']} for r in rows]))
        return
    trials=[]
    stopped=False
    for repetition in range(3):
        for case in cases:
            # Alternate order to reduce a fixed temporal/load bias.
            for arm in (('before','after') if repetition%2==0 else ('after','before')):
                folder=out/f"{case['name']}-{arm}-{repetition}"
                folder.mkdir()
                item={'case':case['name'],'arm':arm,'repetition':repetition,'state':'intent'}
                trials.append(item);write_json_atomic(out/'trials.json',trials)
                def generator(**kw):
                    kw['artifact_prefix'] = f"{folder.name}-{kw['artifact_prefix']}"
                    return llm.generate_json_with_configured_llm(**kw,model_binding=model,stream_output=True)
                started=time.monotonic()
                http_before=len(http)
                try:
                    import shutil
                    shutil.copy2(case['reference'],folder/'reference.png');shutil.copy2(case['shot'],folder/'candidate.png')
                    if arm=='before':
                        prompts={k:case['request'][k] for k in ('system_prompt','schema_hint')}
                        prompts['user_prompt']=json.dumps(case['payload'],ensure_ascii=False)
                        write_json_atomic(folder/'request.json',prompts)
                        raw=generator(**prompts,run_dir=str(out),artifact_prefix=folder.name,
                            image_paths=[str(folder/'reference.png'),str(folder/'candidate.png')],request_timeout=600,reasoning_effort_override='low')
                        write_json_atomic(folder/'response.json',raw)
                        if not args.coverage_baseline and (raw.get('status')=='pass') != (not raw.get('issues')):
                            raise ValueError('Archived policy status/issue contradiction')
                        result=validate_fidelity(raw,case['scene'],require_coverage=bool(args.coverage_baseline),
                            alignment=case['payload'].get('text_alignment_contract'))
                        if args.coverage_baseline:
                            item['coverage']={'status':'complete','expected':len(case['payload']['review_checklist']),
                                              'reported':len(result['coverage'])}
                    else:
                        # Copies keep the actual production image-path gate intact.
                        record=review_fidelity(case['scene'],folder/'reference.png',folder/'candidate.png',case['payload'],None,
                            folder=folder/'review',run_dir=out,deps=HtmlReviewDependencies(ROOT,generator),local_comparisons=not args.facts)
                        result=record['result'];item['coverage']=record['coverage_check']
                    item.update(state='returned',result=result)
                except HtmlReviewError as error:
                    item.update(state='rejected',error_code=error.code)
                except Exception as error:
                    returned=(folder/'response.json').is_file() or (folder/'review/response.json').is_file()
                    logs=[read(p) for p in (out/'logs').glob(f'{folder.name}-*-stream-*.json')]
                    output_limit=any(l.get('finish_reason')=='length' and l.get('failure_reason')=='output_limit' for l in logs)
                    item.update(state='rejected' if returned else 'output_limit' if output_limit else 'unknown' if len(http)>http_before else 'not_submitted',error_type=type(error).__name__)
                    stopped=not returned
                item['http_attempts']=len(http)-http_before
                item['elapsed_seconds']=round(time.monotonic()-started,3)
                result=item.get('result',{})
                found={i['targetId'] for i in result.get('issues',[]) if i['requirement']=='typography'}
                known=set(case['known_typography_targets'])
                item.update(known_found=sorted(found&known),known_missing=sorted(known-found))
                write_json_atomic(out/'trials.json',trials)
                if stopped:break
            if stopped:break
        if stopped:break
    metrics=[]
    for case in cases:
        for arm in ('before','after'):
            rows=[t for t in trials if t['case']==case['name'] and t['arm']==arm]
            signatures=[{(i['targetId'],i['requirement']) for i in t.get('result',{}).get('issues',[])} for t in rows if t['state']=='returned']
            pairs=list(itertools.combinations(signatures,2))
            metrics.append({'case':case['name'],'arm':arm,'trials':len(rows),
                'valid_returns':sum(t['state']=='returned' for t in rows),
                'complete_coverage':sum(t.get('coverage',{}).get('status')=='complete' for t in rows),
                'known_found':sum(len(t['known_found']) for t in rows),'known_expected':len(rows)*len(case['known_typography_targets']),
                'all_known_found_trials':sum(t['state']=='returned' and not t['known_missing'] for t in rows),
                'pairwise_issue_jaccard':[len(a&b)/len(a|b) if a|b else 1 for a,b in pairs],
                'elapsed_seconds':[t['elapsed_seconds'] for t in rows]})
    write_json_atomic(out/'summary.json',{'stopped':stopped,'stopped_on_unknown':any(t['state']=='unknown' for t in trials),'metrics':metrics,'adapter_requests':len(trials),
        'http_attempts':len(http),'usage':None,'cost':None,
        'limits':'At most three repetitions and two screenshots; early stop may leave fewer trials. No general visual accuracy or population significance claim.'})
    print(json.dumps(metrics,ensure_ascii=False))


if __name__=='__main__':main()
