"""Real Web/Agent/store lifecycle, isolated model responses and project data."""
import json
import uuid
from types import SimpleNamespace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from account_context import account_scope
from artifact_fingerprint import sha256_json
from database import SessionLocal,Project
from repository_paths import RUNS_DIR
from checks.test_html_reference_workbench import session,ROOT
from checks.html_design_agent_fixture import with_coverage
from html_visual_review_service import HtmlReviewDependencies
from html_workflow_jobs import HtmlWorkflowJobs
import html_task_store as store
import html_visual_review_routes as web


class Capture:
    def __init__(self):self.calls=[]
    def submit(self,fn,*args):self.calls.append((fn,args))
    def run(self):fn,args=self.calls.pop(0);fn(*args)


@pytest.fixture
def api():
    project_id='reference-'+uuid.uuid4().hex
    run=Path(RUNS_DIR)/project_id;run.mkdir(parents=True)
    scene,folder,correction=session(run)
    contract={'slide_id':scene['id'],'narration_beats':[]}
    (run/'planning').mkdir(exist_ok=True)
    (run/'planning/visual_contract.json').write_text(json.dumps({'slides':[contract]}),encoding='utf-8')
    db=SessionLocal();project=Project(id=project_id,name='Reference fixture',account_id='default',visual_backend='html',run_dir=str(run));db.add(project);db.commit()
    original=store.submit_task(db,project_id=project.id,task_type='html_plan_generate',submission_key=uuid.uuid4().hex,
        payload={'slide_id':scene['id'],'source_revision':0,'contract_sha256':sha256_json(contract)})
    store.mark_running(db,original['id'])
    value=json.loads((folder/'session.json').read_text(encoding='utf-8'))
    store.record_progress(db,original['id'],{'reference_workbench':{'path':'workbench/index.html','session_sha256':sha256_json(value)}})
    store.mark_failed(db,original['id'],'REFERENCE_LOCALIZATION_UNRESOLVED')
    calls=[];fail=[False]
    def generator(**kw):
        calls.append(kw)
        if fail[0]:raise TimeoutError('unknown')
        return with_coverage(json.loads(kw['user_prompt']),{'status':'pass','issues':[]})
    executor=Capture();jobs=HtmlWorkflowJobs(SessionLocal,HtmlReviewDependencies(ROOT,generator),executor=executor)
    olddeps,oldjobs=web._dependencies,web._jobs
    web.configure_html_review_service(web.HtmlReviewDependencies(ROOT,generator));web.configure_html_jobs(jobs)
    app=FastAPI();app.include_router(web.router)
    from agent_api.routes import router
    app.include_router(router)
    with TestClient(app) as client:
        yield SimpleNamespace(client=client,project=project,scene=scene,folder=folder,run=run,
            original=original['id'],correction=correction,executor=executor,calls=calls,jobs=jobs,db=db,fail=fail,
            base=f'/api/projects/{project.id}/html-review/{scene["id"]}/reference/{original["id"]}')
    web.configure_html_review_service(olddeps);web.configure_html_jobs(oldjobs);db.close()


def test_web_agent_read_submit_and_completed_reuse_do_not_save_author(api):
    read=api.client.get(api.base);assert read.status_code==200,read.text
    assert read.json()['reference']['unresolved_targets']==['caption']
    assert api.client.get(api.base+'/workbench').status_code==200
    agent=api.base.replace('/api/projects/','/api/agent/v1/projects/')
    assert api.client.get(agent).json()['reference']['key']==read.json()['reference']['key']
    task=api.client.post(api.base+'/resume',json=api.correction)
    assert task.status_code==200,task.text
    job=task.json()['task']['id'];api.executor.run()
    result=api.client.get(f'/api/projects/{api.project.id}/html-review/tasks/{job}').json()['task']
    assert result['status']=='succeeded',result
    assert result['result']['author_saved'] is False
    assert api.client.post(agent+'/resume',json=api.correction).json()['task']['id']==job
    assert len(api.calls)==1 and not api.executor.calls
    assert store._job(api.db,api.original).status=='failed'
    assert not (api.run/'planning/html_visual/scene-condensation.json').exists()


def test_cross_account_page_and_session_rejected_before_dispatch(api):
    with account_scope('other-account'):
        assert api.client.get(api.base).status_code==404
    assert api.client.get(api.base.replace('/condensation/','/another-page/')).status_code==404
    bad={**api.correction,'session_sha256':'0'*64}
    assert api.client.post(api.base+'/resume',json=bad).status_code==409
    assert not api.executor.calls and not api.calls


def test_cancelled_reference_never_starts_provider(api):
    task=api.client.post(api.base+'/resume',json=api.correction).json()['task']
    assert api.client.post(f'/api/projects/{api.project.id}/html-review/tasks/{task["id"]}/cancel').status_code==200
    api.executor.run()
    assert not api.calls
    assert api.client.post(api.base+'/resume',json=api.correction).json()['task']['status']=='cancelled'


def test_unknown_reference_never_retries_or_changes_model_to_resubmit(api):
    api.fail[0]=True
    assert api.client.post(api.base+'/resume',json=api.correction).status_code==200
    api.executor.run();assert len(api.calls)==1
    result=api.client.post(api.base+'/resume',json=api.correction)
    assert result.json()['task']['status']=='failed' and not api.executor.calls
    api.jobs.freeze_models=lambda *a,**kw:SimpleNamespace(text=SimpleNamespace(summary=lambda:{'config_hash':'b'*64}))
    assert api.client.post(api.base+'/resume',json=api.correction).status_code==409
    assert not api.executor.calls


def test_changed_contract_blocks_reference(api):
    (api.run/'planning/visual_contract.json').write_text(json.dumps({'slides':[{'slide_id':api.scene['id'],'title':'changed'}]}))
    assert api.client.get(api.base).status_code==409
    assert not api.executor.calls


def test_known_completed_receipt_recovers_database_without_provider_retry(api):
    task=api.client.post(api.base+'/resume',json=api.correction).json()['task']
    api.executor.run()
    job=store._job(api.db,task['id'])
    assert job.status=='succeeded'
    job.status='interrupted';api.db.commit()
    recovered=api.client.post(api.base+'/resume',json=api.correction)
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['task']['status']=='succeeded'
    assert len(api.calls)==1 and not api.executor.calls


def test_orphan_reference_package_cannot_submit_production(api):
    from html_task_store import HtmlTaskError
    import pytest
    with pytest.raises(HtmlTaskError,match='定位续接'):
        api.jobs.submit(api.db,api.project,{'slide_id':api.scene['id']},
            {'reference_review_key':'c'*64,'design_candidate_key':'d'*64})
    assert not api.calls and not api.executor.calls
