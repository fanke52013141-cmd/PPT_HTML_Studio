import copy
import pytest
from checks.test_html_reference_api import api as api
from checks.test_html_annotation_store import dataset_fixture,reviewed_fixture
from checks.test_html_evaluation_execution import generator,ROOT
from html_visual_review_service import HtmlReviewDependencies
from html_evaluation_models import StartExperiment
from account_context import account_scope
import html_task_store as store


def command(api,body,agent=False):
    return api.client.post(f'/api/{"agent/v1/" if agent else ""}projects/{api.project.id}/html-evaluation/action',json={'command':body})


def test_annotation_web_agent_parity_workbench_isolation_and_conflict(api):
    dataset_fixture(api.run)
    base=f'/api/projects/{api.project.id}/html-evaluation'
    assert api.client.get(base).json()['evaluation']['datasets'][0]['id']=='labels'
    body={'action':'read_case','dataset_id':'labels','case_id':'page-0'}
    result=command(api,body);assert result.status_code==200,result.text
    view=result.json()['evaluation'];annotation=view['annotation']
    assert command(api,body,True).json()['evaluation']['annotation']==annotation
    frame=api.client.get(view['workbench_url']);assert frame.status_code==200
    assert 'sandbox allow-scripts allow-downloads' in frame.headers['content-security-policy']
    save={'action':'save_labels','dataset_id':'labels','case_id':'page-0','expected_revision':0,
        'source_sha256':annotation['source_sha256'],'annotator':'Alice','mapping':annotation['mapping']}
    assert command(api,save).status_code==200
    assert command(api,save,True).status_code==409
    with account_scope('another-account'):
        assert api.client.get(base).status_code==404
        assert api.client.get(view['workbench_url']).status_code==404
        assert command(api,body).status_code==404
    bad=copy.deepcopy(save);bad['dataset_id']='../other'
    assert command(api,bad).status_code==422


def test_experiment_dispatch_deduplicates_and_known_receipt_recovers(api):
    reviewed_fixture(api.run);calls=[];api.jobs.deps=HtmlReviewDependencies(ROOT,generator(calls))
    body=StartExperiment(action='start_experiment',dataset_id='labels').model_dump()
    submitted=command(api,body);assert submitted.status_code==200,submitted.text
    task=submitted.json()['evaluation']['task']
    assert command(api,body,True).json()['evaluation']['task']['id']==task['id']
    assert len(api.executor.calls)==1
    api.executor.run();job=store._job(api.db,task['id'])
    assert job.status=='succeeded',job.error
    assert len(calls)==4 and job.get_payload()['result']['author_saved'] is False
    job.status='interrupted';api.db.commit()
    recovered=command(api,body).json()['evaluation']['task']
    assert recovered['status']=='succeeded' and len(calls)==4 and not api.executor.calls


def test_cancel_and_unknown_are_not_restarted_with_new_settings(api):
    reviewed_fixture(api.run);calls=[];api.jobs.deps=HtmlReviewDependencies(ROOT,generator(calls,unknown=True))
    body=StartExperiment(action='start_experiment',dataset_id='labels').model_dump()
    task=command(api,body).json()['evaluation']['task'];api.executor.run()
    assert store._job(api.db,task['id']).status=='failed' and len(calls)==1
    assert command(api,body).json()['evaluation']['task']['id']==task['id'] and not api.executor.calls
    body['repetitions']=2;body['max_model_calls']=8
    assert command(api,body).status_code==409 and len(calls)==1
    from checks.test_html_annotation_store import annotate
    annotate(api.run,'page-0')  # A new gold revision cannot reset the same unknown image request.
    assert command(api,body).status_code==409 and len(calls)==1


def test_queued_cancellation_prevents_all_provider_calls(api):
    reviewed_fixture(api.run);calls=[];api.jobs.deps=HtmlReviewDependencies(ROOT,generator(calls))
    body=StartExperiment(action='start_experiment',dataset_id='labels').model_dump()
    task=command(api,body).json()['evaluation']['task']
    result=api.client.post(f'/api/projects/{api.project.id}/html-review/tasks/{task["id"]}/cancel')
    assert result.status_code==200
    api.executor.run();assert not calls and store._job(api.db,task['id']).status=='cancelled'


def test_late_response_cannot_turn_cancelled_job_into_success(api):
    reviewed_fixture(api.run);calls=[];task_id=[None]
    def cancel():
        assert api.client.post(f'/api/projects/{api.project.id}/html-review/tasks/{task_id[0]}/cancel').status_code==200
    api.jobs.deps=HtmlReviewDependencies(ROOT,generator(calls,cancel=cancel))
    body=StartExperiment(action='start_experiment',dataset_id='labels').model_dump()
    task=command(api,body).json()['evaluation']['task'];task_id[0]=task['id'];api.executor.run()
    assert len(calls)==1 and store._job(api.db,task['id']).status=='cancelled'
    assert command(api,body).json()['evaluation']['task']['status']=='cancelled'
    assert not api.executor.calls


@pytest.mark.parametrize('damage',['request','response','reference'])
def test_database_recovery_rejects_damaged_experiment_evidence(api,damage):
    reviewed_fixture(api.run);calls=[];api.jobs.deps=HtmlReviewDependencies(ROOT,generator(calls))
    body=StartExperiment(action='start_experiment',dataset_id='labels').model_dump()
    task=command(api,body).json()['evaluation']['task'];api.executor.run()
    job=store._job(api.db,task['id']);assert job.status=='succeeded'
    from pathlib import Path
    folder=Path(api.run)/job.get_payload()['input']['experiment_path']
    target=folder/'trials/0'/('request.json' if damage=='request' else 'response.json')
    if damage=='reference':target=folder/'dataset/page-0.png'
    target.write_bytes(b'damaged')
    job.status='interrupted';api.db.commit()
    result=command(api,body)
    assert result.status_code==409,result.text
    assert len(calls)==4 and not api.executor.calls
