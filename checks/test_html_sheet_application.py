"""Isolated Web/Agent/MCP/CLI sheet workflow with actual job/store/resources."""
import json
import uuid
from functools import partial
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import Project, LocalJob, SessionLocal
from repository_paths import RUNS_DIR
import html_asset_sheet_routes as web
import html_visual_review_routes as tasks
import html_visual_routes as visual
import html_task_store as store
from html_asset_sheet_jobs import HtmlSheetJobs
from project_model_binding_service import freeze_project_models
from checks.test_html_asset_sheet_generation import plan_fixture


class CapturedExecutor:
    def __init__(self): self.calls = []
    def submit(self, *args): self.calls.append(args)
    def run(self, index=0):
        function, *args = self.calls[index]
        function(*args)


@pytest.fixture
def app_fixture(monkeypatch):
    from agent_api import routes as agent
    from database import get_db
    from agent_api.errors import AgentAPIError, agent_error_handler
    db = SessionLocal()
    ids = {kind: 'sheet-' + uuid.uuid4().hex for kind in ('html', 'image', 'foreign')}
    for kind, pid in ids.items():
        run = Path(RUNS_DIR) / pid; run.mkdir(parents=True)
        db.add(Project(id=pid, name=kind, account_id='another' if kind == 'foreign' else 'default',
            visual_backend='image' if kind == 'image' else 'html', run_dir=str(run)))
    db.commit()
    source, plan = plan_fixture()
    settings = {'image_model':'before', 'image_api_key':'private-fixture-key',
                'llm_model': 'vision-before', 'llm_api_key': 'private-text-fixture-key'}
    calls = []
    def provider(prompt, **kwargs):
        calls.append(kwargs['model_binding'].model)
        return source
    executor = CapturedExecutor()
    jobs = HtmlSheetJobs(SessionLocal, executor, provider=provider,
        freeze_models=partial(freeze_project_models, setting=settings.get, credential=lambda ref: {}))
    monkeypatch.setattr(web, '_jobs', jobs)
    application = FastAPI()
    application.include_router(web.router); application.include_router(tasks.router); application.include_router(agent.router)
    application.add_exception_handler(AgentAPIError, agent_error_handler)
    def database():
        session = SessionLocal()
        try: yield session
        finally: session.close()
    application.dependency_overrides[visual._get_db] = database
    application.dependency_overrides[tasks._get_db] = database
    application.dependency_overrides[get_db] = database
    with TestClient(application) as client:
        yield client, ids, plan, executor, settings, calls
    db.query(LocalJob).filter(LocalJob.project_id.in_(ids.values())).delete(synchronize_session=False)
    db.query(Project).filter(Project.id.in_(ids.values())).delete(synchronize_session=False)
    db.commit(); db.close()


def base(ids, agent=False):
    return ('/api/agent/v1' if agent else '/api') + f'/projects/{ids["html"]}/html-asset-sheets'


def generated(fixture):
    client, ids, plan, executor, *_ = fixture
    response = client.post(base(ids) + '/generate', json={'plan': plan})
    assert response.status_code == 200, response.text
    job = response.json()['data']['task']; executor.run()
    listed = client.get(base(ids)).json()['data']
    assert listed['task']['status'] == 'succeeded', listed
    item = listed['candidates'][0]
    path = f'/{item["sheet_id"]}/{item["request_key"]}'
    return path, job


def test_full_flow_freezes_submission_and_never_persists_secret(app_fixture):
    client, ids, plan, executor, settings, calls = app_fixture
    submitted = client.post(base(ids) + '/generate', json={'plan':plan}).json()['data']['task']
    again = client.post(base(ids) + '/generate', json={'plan':plan}).json()['data']['task']
    assert again['id'] == submitted['id'] and len(executor.calls) == 1
    settings.update(image_model='after', image_api_key='another-private-key')
    executor.run()
    assert calls == ['before']
    listed = client.get(base(ids)).json()['data']
    assert listed['task']['status'] == 'succeeded'
    item = listed['candidates'][0]; path=f'/{item["sheet_id"]}/{item["request_key"]}'
    document = client.get(base(ids)+path).json()['data']
    assert document['revision'] == 0
    accept_url = base(ids)+path+'/one/accept'
    assert client.post(accept_url, json={'expected_revision':0}).status_code == 400
    review_url = base(ids)+path+'/one/review'
    payload={'identity':'approved','edge':'approved','expected_revision':0,'note':'actual review'}
    assert client.put(review_url, json=payload).json()['data']['revision'] == 1
    conflict = client.put(review_url, json=payload)
    assert conflict.status_code == 409 and conflict.json()['detail']['current_revision'] == 1
    assert client.post(accept_url, json={'expected_revision':1}).json()['data']['changed'] is True
    assert client.post(accept_url, json={'expected_revision':1}).json()['data']['changed'] is False
    image = client.get(base(ids)+path+'/one/image')
    assert image.status_code == 200 and image.headers['cache-control'] == 'no-store'
    db=SessionLocal()
    try:
        record=db.query(LocalJob).filter(LocalJob.id==submitted['id']).one()
        assert 'private-fixture-key' not in record.payload_json and 'another-private-key' not in record.payload_json
    finally: db.close()


def test_cancel_queued_and_restart_retry_reject_old_attempt(app_fixture):
    client, ids, plan, executor, _, calls = app_fixture
    task=client.post(base(ids)+'/generate',json={'plan':plan}).json()['data']['task']
    task_url=f'/api/projects/{ids["html"]}/html-review/tasks/{task["id"]}'
    assert client.post(task_url+'/cancel',json={}).json()['task']['status']=='cancelled'
    executor.run(); assert not calls
    retry=client.post(base(ids)+'/generate',json={'plan':plan}).json()['data']['task']
    assert retry['attempt']==2
    db=SessionLocal()
    try: store.recover_interrupted(db)
    finally: db.close()
    assert client.get(task_url).json()['task']['status']=='interrupted'
    third=client.post(base(ids)+'/generate',json={'plan':plan}).json()['data']['task']
    assert third['attempt']==3
    executor.run(1); assert not calls
    executor.run(2); assert calls == ['before']
    assert client.get(task_url).json()['task']['status']=='succeeded'


def test_account_backend_strict_fields_and_no_fake_segmentation(app_fixture):
    client, ids, plan, executor, *_=app_fixture
    for kind, status in [('foreign',404),('image',400)]:
        endpoint=f'/api/projects/{ids[kind]}/html-asset-sheets'
        assert client.get(endpoint).status_code==status
        assert client.post(endpoint+'/generate',json={'plan':plan}).status_code==status
    assert client.post(base(ids)+'/generate',json={'plan':plan,'api_key':'forbidden'}).status_code==422
    plan['slots'][0]['method']='mask'
    failure=client.post(base(ids)+'/generate',json={'plan':plan})
    assert failure.status_code==400 and failure.json()['detail']['code']=='SHEET_SEGMENTER_REQUIRED'
    assert not executor.calls


def test_stop_inflight_provider_prevents_late_success_and_candidate_writes(app_fixture, monkeypatch):
    client, ids, plan, executor, *_ = app_fixture
    submitted = client.post(base(ids)+'/generate', json={'plan':plan}).json()['data']['task']
    source, _ = plan_fixture()
    def provider(*a, **kw):
        url=f'/api/projects/{ids["html"]}/html-review/tasks/{submitted["id"]}'
        assert client.post(url+'/cancel',json={}).json()['task']['status']=='cancelled'
        return source
    monkeypatch.setattr(web._jobs, 'provider', provider)
    executor.run()
    listed=client.get(base(ids)).json()['data']
    assert listed['task']['status']=='cancelled' and not listed['candidates']


@pytest.mark.parametrize('name', ['list','generate','read','review','accept','assess','retry'])
def test_mcp_and_cli_reach_actual_agent_routes(name, app_fixture, monkeypatch, tmp_path, capsys):
    from agent_contract.capabilities import CAPABILITIES
    from agent_client.client import AgentClient
    from mcp_server.tools import _dispatch
    from cli import pptctl
    client, ids, plan, *_ = app_fixture
    path, _ = generated(app_fixture)
    sheet_id, key = path.lstrip('/').split('/')
    if name=='accept':
        client.put(base(ids)+path+'/one/review',json={'identity':'approved','edge':'approved','expected_revision':0})
    cap=next(c for c in CAPABILITIES if c.id=='html_sheet.'+name)
    args={'project_id':ids['html']}
    if name in ('read','review','accept','assess','retry'): args.update(sheet_id=sheet_id,request_key=key)
    if name in ('review','accept','retry'): args['asset_id']='one'
    if name=='generate': args['plan']=plan
    if name=='review': args.update(identity='approved',edge='approved',expected_revision=0)
    if name=='accept': args['expected_revision']=1
    if name=='retry': args['expected_revision']=0
    def request(self, method, endpoint, body=None, **kw):
        response=client.request(method, endpoint, json=body)
        assert response.status_code==200, response.text
        return response.json()
    monkeypatch.setattr(AgentClient,'_request',request)
    result=_dispatch(cap.id,args,AgentClient())
    assert result['project_id']==ids['html']
    if name=='review': args['expected_revision']=result['data']['revision']
    argv=cap.cli_command.split()+['--project',ids['html']]
    for field in ('sheet_id','request_key','asset_id'):
        if field in args: argv+=['--'+field.replace('_','-'),args[field]]
    if cap.agent_api_method!='GET':
        payload={k:v for k,v in args.items() if k not in ('project_id','sheet_id','request_key','asset_id')}
        file=tmp_path/'request.json'; file.write_text(json.dumps(payload),encoding='utf-8')
        argv+=['--file',str(file)]
    parsed=pptctl.build_parser().parse_args(argv); parsed.func(parsed)
    assert json.loads(capsys.readouterr().out)['project_id']==ids['html']
