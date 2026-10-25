"""Frozen paired localization execution over original JSON transport and receipts."""
import json
import time
from pathlib import Path
from artifact_fingerprint import sha256_file,sha256_json
from html_paired_evaluation import checked,compare
from html_annotation_store import read,sealed_dataset
from html_acceptance_criteria import safe
from html_reference_localization import mapped_reference_targets,validate_mapped_locations,MappedLocations
from html_reference_replay import execute_once
from html_json_observer import observe_json_requests
from html_page_budget import PageBudget
from pipeline_lifecycle import write_json_atomic

SOURCES=('html_evaluation_execution.py','html_evaluation_jobs.py','html_annotation_store.py',
    'html_evaluation_models.py','html_paired_evaluation.py','html_reference_replay.py','html_reference_localization.py',
    'json_llm_service.py','json_llm_transport.py','html_json_observer.py','scripts/score_html_reference_localization.py',
    'html_page_budget.py','project_model_binding_service.py','ai_provider_service.py','llm_concurrency.py')


def freeze(run,command,repo,models):
    source,data=sealed_dataset(run,command['dataset_id'])
    identity={'dataset':data,'options':command,'models':{arm:model.summary() if model else {'source':'injected'} for arm,model in models.items()},
        'sources':{name:sha256_file(Path(repo)/name) for name in SOURCES},'prompts':{}}
    for arm in ('before','after'):
        path=Path(repo)/f'config/html_runtime_skills/design-reference-localization-{command[arm]["protocol"]}.md'
        identity['prompts'][arm]={'path':str(path.relative_to(repo)).replace('\\','/'),'sha256':sha256_file(path)}
    key=sha256_json(identity);folder=safe(run,'planning/html_visual/evaluation/experiments/'+key)
    if not (folder/'frozen.json').exists():
        folder.mkdir(parents=True,exist_ok=True)
        for case in data['cases']:
            for field in ('reference','scene','gold'):
                item=case[field];original=checked(source,item)
                snapshot_root=safe(folder,'dataset')
                target=safe(snapshot_root,item['path']);target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(original.read_bytes())
                if sha256_file(target)!=item['sha256']:raise ValueError('EXPERIMENT_INPUT_CHANGED')
        write_json_atomic(folder/'dataset/dataset.json',data)
        for arm,item in identity['prompts'].items():
            target=safe(folder,arm+'.md');target.write_bytes((Path(repo)/item['path']).read_bytes())
            if sha256_file(target)!=item['sha256']:raise ValueError('EXPERIMENT_PROMPT_CHANGED')
        write_json_atomic(folder/'frozen.json',identity)
    if read(folder/'frozen.json')!=identity:raise ValueError('EXPERIMENT_IDENTITY_CHANGED')
    return key,folder,identity


def execute(folder,identity,*,repo,generator,models,checkpoint=lambda:None,progress=lambda value:None):
    folder=Path(folder).resolve();data=identity['dataset'];options=identity['options'];root=folder/'dataset'
    if (folder/'result-receipt.json').exists():
        previous=completed_result(folder,identity,repo)
        if not previous['stopped']:
            checkpoint()
            return {**previous,'cache_receipt':{'reused':True,'dispatches_this_call':0}}
    budget=PageBudget(seconds=options['total_seconds'],model_limit=options['max_model_calls'],browser_limit=3,final_reserve_seconds=0)
    if (folder/'budget.json').exists():
        previous=read(folder/'budget.json')
        budget.model_calls=previous['model_calls'];budget.events=previous['events']
        budget.started-=previous.get('elapsed_seconds',0)
    trials={'dataset_sha256':sha256_json(data),'repetitions':options['repetitions'],'arms':['before','after'],'trials':[]}
    order=[]
    for repetition in range(options['repetitions']):
        for index,case in enumerate(data['cases']):
            for arm in (('before','after') if (index+repetition)%2==0 else ('after','before')):
                row={'case_id':case['id'],'repetition':repetition,'arm':arm,'state':'not_run','seconds':None}
                trials['trials'].append(row);order.append((case,arm,row))
    http=read(folder/'http.json') if (folder/'http.json').exists() else []
    if any(h['state'] in ('intent','unknown') for h in http):raise ValueError('EXPERIMENT_PRIOR_OUTCOME_UNKNOWN')
    def fresh():
        checkpoint();budget.check(final=True)
        if read(folder/'frozen.json')!=identity:raise ValueError('EXPERIMENT_FROZEN_STATE_CHANGED')
        for name,digest in identity['sources'].items():
            if sha256_file(Path(repo)/name)!=digest:raise ValueError('EXPERIMENT_SOURCE_STALE')
        for arm,item in identity['prompts'].items():
            if sha256_file(folder/(arm+'.md'))!=item['sha256']:raise ValueError('EXPERIMENT_PROMPT_CHANGED')
        for case in data['cases']:
            for field in ('reference','scene','gold'):checked(root,case[field])
    def save():
        write_json_atomic(folder/'trials.json',trials)
        write_json_atomic(folder/'http.json',http)
        write_json_atomic(folder/'budget.json',{'model_calls':budget.model_calls,'http_calls':len(http),'events':budget.events,
            'elapsed_seconds':time.monotonic()-budget.started})
    def observe(state,**facts):
        if state=='intent':
            fresh()
            if len(http)>=options['max_http_calls']:raise ValueError('EXPERIMENT_HTTP_BUDGET')
            if any(h['state'] in ('intent','unknown') for h in http):raise ValueError('EXPERIMENT_UNKNOWN_REQUEST')
            http.append({'state':'intent','trial':active_index})
        else:
            http[-1].update(state=state,**facts)
        save()
    save()
    for active_index,(case,arm,row) in enumerate(order):
        trial=safe(folder,'trials/'+str(active_index));started=time.monotonic();call_http_start=len(http)
        try:
            fresh()
            scene=read(checked(root,case['scene']));reference=checked(root,case['reference'])
            targets=mapped_reference_targets(scene)
            from PIL import Image
            with Image.open(reference) as image:size=list(image.size)
            payload={'reference_targets':targets,'box_coordinates':'original_image_pixels','image_size':size,
                'task':'Find each identity in the reference image independently; no HTML position is supplied.'}
            request={'system_prompt':(folder/(arm+'.md')).read_text(encoding='utf-8'),
                'user_prompt':json.dumps(payload,ensure_ascii=False),'schema_hint':json.dumps(MappedLocations.model_json_schema(),ensure_ascii=False)}
            def dispatch():
                budget.claim('model',f'{case["id"]}:{arm}:{row["repetition"]}',final=True)
                def report_stream(value=None):
                    checkpoint()
                    progress({'completed':sum(r['state']!='not_run' for r in trials['trials']),'total':len(order),
                        'http_calls':len(http),'model_calls':budget.model_calls,'trial':active_index,
                        'case_id':case['id'],'arm':arm,'state':'requesting','stream':value})
                report_stream()
                write_json_atomic(trial/'request.json',{**request,'reference_sha256':case['reference']['sha256'],
                    'model':identity['models'][arm],'protocol':options[arm]['protocol'],'gold_supplied':False,'candidate_geometry_supplied':False})
                arguments={**request,'image_paths':[str(reference)],'run_dir':str(folder),
                    'artifact_prefix':'paired-'+str(active_index),'request_timeout':min(options['request_seconds'],budget.remaining(final=True)),
                    'reasoning_effort_override':'low','stream_output':True,'on_stream_progress':report_stream}
                if models[arm] is not None:arguments['model_binding']=models[arm]
                with observe_json_requests(observe):result=generator(**arguments)
                write_json_atomic(trial/'raw.json',result)
                fresh()
                validate_mapped_locations(result,targets,size)
                usages=[h.get('usage') for h in http[call_http_start:]]
                counters=('prompt_tokens','completion_tokens','total_tokens')
                usage={key:sum(u[key] for u in usages) for key in counters} if usages and all(
                    isinstance(u,dict) and all(type(u.get(key)) is int and u[key]>=0 for key in counters) for u in usages) else None
                return {'response':result,'usage':usage}
            result=execute_once(trial,{'experiment':sha256_json(identity),'index':active_index},dispatch,fresh)
            # The scored response remains the raw closed Schema, not derived crops.
            response=trial/'response.json';write_json_atomic(response,result['response'])
            receipt=trial/'receipt.json';write_json_atomic(receipt,{'reference_sha256':case['reference']['sha256'],
                'response_sha256':sha256_file(response),'mode':'configured_transport' if models[arm] else 'injected_response',
                'usage':result.get('usage'),'cost':None,'request_sha256':sha256_file(trial/'request.json')})
            def item(path):return {'path':path.relative_to(folder).as_posix(),'sha256':sha256_file(path)}
            row.update(state='returned',response=item(response),receipt=item(receipt))
        except Exception as error:
            known=(trial/'raw.json').exists() or (len(http)>call_http_start and http[-1]['state'] in ('returned','rejected','output_limit'))
            row.update(state='failed' if known else 'unknown' if len(http)>call_http_start else 'not_run',error_class=type(error).__name__)
            write_json_atomic(trial/'failure.json',{'state':row['state'],'error_class':type(error).__name__,'automatic_retry':False})
            row['seconds']=round(time.monotonic()-started,3);save()
            # A validation rejection may proceed to the other arm; unknown,
            # source changes, cancellation and budget exhaustion stop dispatch.
            if (trial/'raw.json').exists() and type(error).__name__ in ('ValueError','HtmlReviewError'):
                try:fresh()
                except Exception:break
                if 'LOCALIZATION' in str(error):continue
            break
        row['seconds']=round(time.monotonic()-started,3);save()
        progress({'completed':sum(r['state']!='not_run' for r in trials['trials']),'total':len(order),
            'http_calls':len(http),'model_calls':budget.model_calls,'trial':active_index})
    save()
    # Trial paths refer to folder; dataset paths refer to its nested snapshot.
    scored=copy_dataset_paths(data)
    comparison=compare(scored,{**trials,'dataset_sha256':sha256_json(scored)},folder)
    result={'trials':trials,'comparison':comparison,'http_calls':len(http),'model_calls':budget.model_calls,
        'stopped':any(r['state']!='returned' for r in trials['trials']),'author_saved':False,'human_approval':'pending'}
    write_json_atomic(folder/'result.json',result)
    write_json_atomic(folder/'result-receipt.json',{'experiment':sha256_json(identity),'result_sha256':sha256_file(folder/'result.json')})
    return result


def copy_dataset_paths(data):
    import copy
    result=copy.deepcopy(data)
    for case in result['cases']:
        for field in ('reference','scene','gold'):case[field]['path']='dataset/'+case[field]['path']
    return result


def completed_result(folder,identity,repo):
    """Verify the full recorded chain before recovering a database terminal state."""
    folder=Path(folder)
    if read(folder/'frozen.json')!=identity:raise ValueError('EXPERIMENT_FROZEN_STATE_CHANGED')
    for name,digest in identity['sources'].items():
        if sha256_file(Path(repo)/name)!=digest:raise ValueError('EXPERIMENT_SOURCE_STALE')
    for case in identity['dataset']['cases']:
        for field in ('reference','scene','gold'):checked(folder/'dataset',case[field])
    for arm,prompt in identity['prompts'].items():
        if sha256_file(safe(folder,arm+'.md'))!=prompt['sha256']:raise ValueError('EXPERIMENT_PROMPT_CHANGED')
    seal=read(folder/'result-receipt.json')
    if seal.get('experiment')!=sha256_json(identity) or sha256_file(folder/'result.json')!=seal.get('result_sha256'):
        raise ValueError('EXPERIMENT_RESULT_RECEIPT_CHANGED')
    result=read(folder/'result.json')
    for index,row in enumerate(result['trials']['trials']):
        if row['state']!='returned':continue
        response=checked(folder,row['response']);receipt=read(checked(folder,row['receipt']))
        trial=safe(folder,'trials/'+str(index));attempt=read(trial/'attempt.json')
        if (receipt.get('request_sha256')!=sha256_file(trial/'request.json') or
            receipt.get('response_sha256')!=sha256_file(response) or attempt.get('state')!='completed' or
            attempt.get('identity')!={'experiment':sha256_json(identity),'index':index} or
            attempt.get('result_sha256')!=sha256_file(trial/'completed.json') or
            read(trial/'completed.json')['response']!=read(response)):
            raise ValueError('EXPERIMENT_TRIAL_RECEIPT_CHANGED')
    return result
