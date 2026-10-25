import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from checks.test_html_annotation_store import reviewed_fixture
from html_evaluation_models import StartExperiment
from html_evaluation_execution import freeze,execute

ROOT=Path(__file__).resolve().parents[1]


def response(kwargs):
    payload=json.loads(kwargs['user_prompt'])
    return {'targets':[{'targetId':t['targetId'],'status':'located','container_presence':'absent','container_box':None,
        'identity_evidence':'controlled response fixture','part_regions':[{'partId':p['partId'],'status':'located',
            'regions':[{'text':p['text'],'box':{'xPx':10,'yPx':10,'widthPx':40,'heightPx':15}}]} for p in t['text_parts']]} for t in payload['reference_targets']]}


def generator(calls,*,unknown=False,repeat_http=1,cancel=None,usage=None):
    from json_llm_transport import receive_completion
    def generate(**kwargs):
        calls.append(kwargs)
        def create(**params):
            if cancel:cancel()
            if unknown:raise TimeoutError('controlled transport unknown')
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(response(kwargs))))],
                usage=SimpleNamespace(model_dump=lambda:usage) if usage is not None else None)
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        for _ in range(repeat_http):raw=receive_completion(client,{})
        return json.loads(raw.choices[0].message.content)
    return generate


def setup(run,**options):
    reviewed_fixture(run)
    command=StartExperiment(action='start_experiment',dataset_id='labels',**options).model_dump()
    models={'before':None,'after':None}
    key,folder,identity=freeze(run,command,ROOT,models)
    return folder,identity,models


def test_frozen_pair_order_no_gold_and_exact_result_reuse(tmp_path):
    folder,identity,models=setup(tmp_path);calls=[]
    result=execute(folder,identity,repo=ROOT,generator=generator(calls),models=models)
    assert len(calls)==4 and result['http_calls']==4 and not result['stopped']
    assert [r['arm'] for r in result['trials']['trials']]==['before','after','after','before']
    for call in calls:
        payload=json.loads(call['user_prompt'])
        assert 'gold' not in payload and 'presentation' not in call['user_prompt']
        assert set(payload)=={'reference_targets','box_coordinates','image_size','task'}
    again=execute(folder,identity,repo=ROOT,generator=generator(calls),models=models)
    assert len(calls)==4 and again['http_calls']==4


def test_unknown_transport_stops_all_dispatch_and_blocks_retry(tmp_path):
    folder,identity,models=setup(tmp_path);calls=[]
    result=execute(folder,identity,repo=ROOT,generator=generator(calls,unknown=True),models=models)
    assert len(calls)==1 and result['trials']['trials'][0]['state']=='unknown'
    assert sum(r['state']=='not_run' for r in result['trials']['trials'])==3
    with pytest.raises(ValueError,match='PRIOR_OUTCOME_UNKNOWN'):
        execute(folder,identity,repo=ROOT,generator=generator(calls),models=models)
    assert len(calls)==1


def test_real_http_budget_covers_nested_calls_and_stops_before_dispatch(tmp_path):
    folder,identity,models=setup(tmp_path,max_http_calls=2);calls=[]
    result=execute(folder,identity,repo=ROOT,generator=generator(calls,repeat_http=3),models=models)
    assert result['http_calls']==2 and len(calls)==1 and result['stopped']
    assert result['trials']['trials'][0]['state']=='failed'


def test_cancellation_after_response_never_advances_next_arm(tmp_path):
    folder,identity,models=setup(tmp_path);calls=[];cancelled=[False]
    def checkpoint():
        if cancelled[0]:raise ValueError('cancelled')
    result=execute(folder,identity,repo=ROOT,generator=generator(calls,cancel=lambda:cancelled.__setitem__(0,True)),models=models,checkpoint=checkpoint)
    assert len(calls)==1 and result['stopped']
    assert sum(r['state']=='not_run' for r in result['trials']['trials'])==3


def test_frozen_reference_change_prevents_any_provider_call(tmp_path):
    folder,identity,models=setup(tmp_path);calls=[]
    (folder/'dataset'/identity['dataset']['cases'][0]['reference']['path']).write_bytes(b'damaged')
    with pytest.raises(ValueError,match='HASH_CHANGED'):
        execute(folder,identity,repo=ROOT,generator=generator(calls),models=models)
    assert not calls


def test_per_trial_usage_includes_all_real_http_calls(tmp_path):
    folder,identity,models=setup(tmp_path);calls=[]
    result=execute(folder,identity,repo=ROOT,generator=generator(calls,repeat_http=2,
        usage={'prompt_tokens':2,'completion_tokens':3,'total_tokens':5}),models=models)
    assert result['http_calls']==8
    assert all(row['usage']=={'prompt_tokens':4,'completion_tokens':6,'total_tokens':10} for row in result['comparison']['rows'])
    assert all(row['cost'] is None for row in result['comparison']['rows'])
