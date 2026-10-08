"""Actual persisted action jobs + HTTP, controlled multimodal/image providers."""
import io
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from checks.test_html_sheet_application import app_fixture as app_fixture, base, generated
from checks.test_html_asset_sheet import png
from checks.test_html_asset_sheet_generation import plan_fixture
from database import LocalJob, Project, SessionLocal
import html_asset_sheet_routes as web
import html_task_store as store
from html_asset_sheet_review import _candidate

FINDING = {'identity': 'match', 'edge': 'clean', 'extra_content': False, 'reason': '对象可见'}


def task_url(ids, task):
    return f'/api/projects/{ids["html"]}/html-review/tasks/{task["id"]}'


def single_png():
    image = Image.new('RGBA', (1024, 1024))
    ImageDraw.Draw(image).ellipse((128, 128, 896, 896), fill=(30, 60, 90, 255))
    return png(image)


def test_assessment_frozen_deduped_and_unapproved(app_fixture, monkeypatch):
    client, ids, _, executor, settings, _ = app_fixture
    path, _ = generated(app_fixture)
    calls = []
    def assessor(**kw):
        calls.append(kw)
        return FINDING
    monkeypatch.setattr(web._jobs, 'assessor', assessor)
    submitted = client.post(base(ids) + path + '/assess', json={})
    assert submitted.status_code == 200, submitted.text
    job = submitted.json()['data']['task']
    assert client.post(base(ids) + path + '/assess', json={}).json()['data']['task']['reused']
    settings['llm_model'] = 'vision-after'
    executor.run(1)
    assert client.get(task_url(ids, job)).json()['task']['status'] == 'succeeded'
    assert len(calls) == 2 and all(c['model_binding'].model == 'vision-before' for c in calls)
    assert all(c['candidate_bytes'].startswith(b'\x89PNG') and c['reference_bytes'] is None for c in calls)
    doc = client.get(base(ids) + path).json()['data']
    assert doc['advisory']['findings']['one']['action'] == 'accept_candidate'
    assert doc['decisions'] == doc['accepted'] == {}
    assert client.post(base(ids) + path + '/one/accept', json={'expected_revision': 0}).status_code == 400
    db = SessionLocal()
    try:
        row = db.get(LocalJob, job['id'])
        assert 'private-text-fixture-key' not in row.payload_json
        assert 'private-fixture-key' not in row.payload_json
    finally:
        db.close()


def test_retry_single_frozen_reference_and_parent_preservation(app_fixture, monkeypatch):
    client, ids, _, executor, settings, _ = app_fixture
    path, _ = generated(app_fixture)
    sheet_id, request_key = path.lstrip('/').split('/')
    db = SessionLocal()
    try:
        run_dir = db.get(Project, ids['html']).run_dir
    finally:
        db.close()
    parent = _candidate(run_dir, sheet_id, request_key)[1]
    before = {p.name: p.read_bytes() for p in parent.iterdir() if p.is_file()}
    calls = []
    def provider(prompt, **kw):
        calls.append((prompt, kw))
        return single_png()
    monkeypatch.setattr(web._jobs, 'provider', provider)
    submitted = client.post(base(ids) + path + '/one/retry', json={'expected_revision': 0, 'need': '独立杯子，不要光芒'})
    assert submitted.status_code == 200, submitted.text
    job = submitted.json()['data']['task']
    settings['image_model'] = 'after'
    executor.run(1)
    task = client.get(task_url(ids, job)).json()['task']
    assert task['status'] == 'succeeded', task
    assert len(calls) == 1 and calls[0][1]['model_binding'].model == 'before'
    assert calls[0][1]['reference_paths'] == [str(parent / 'source.png')]
    assert calls[0][1]['size'] == '1024x1024'
    assert [a['id'] for a in task['result']['manifest']['assets']] == ['one']
    assert task['result']['retry_parent']['request_key'] == request_key
    assert {p.name: p.read_bytes() for p in parent.iterdir() if p.is_file()} == before
    assert not list(Path(run_dir).rglob('resources.json'))
    assert task['result']['manifest']['assets'][0]['anchors'] == []


def test_retry_extraction_failure_is_allowed(app_fixture, monkeypatch):
    client, ids, plan, executor, *_ = app_fixture
    source, _ = plan_fixture()
    image = Image.open(io.BytesIO(source))
    image.putpixel((0, 0), (10, 20, 30, 255))
    monkeypatch.setattr(web._jobs, 'provider', lambda *a, **kw: png(image))
    path, _ = generated(app_fixture)
    doc = client.get(base(ids) + path).json()['data']
    assert doc['manifest']['failures'][0]['asset_id'] == 'one'
    monkeypatch.setattr(web._jobs, 'provider', lambda *a, **kw: single_png())
    task = client.post(base(ids) + path + '/one/retry', json={'expected_revision': 0}).json()['data']['task']
    executor.run(1)
    assert client.get(task_url(ids, task)).json()['task']['status'] == 'succeeded'


@pytest.mark.parametrize('action', ['assess', 'retry'])
def test_action_cancel_and_recover_attempts(app_fixture, monkeypatch, action):
    client, ids, _, executor, *_ = app_fixture
    path, _ = generated(app_fixture)
    endpoint = base(ids) + path + ('/assess' if action == 'assess' else '/one/retry')
    body = {} if action == 'assess' else {'expected_revision': 0}
    task = client.post(endpoint, json=body).json()['data']['task']
    assert client.post(task_url(ids, task) + '/cancel', json={}).status_code == 200
    executor.run(1)
    assert client.get(task_url(ids, task)).json()['task']['status'] == 'cancelled'
    retry = client.post(endpoint, json=body).json()['data']['task']
    assert retry['attempt'] == 2
    db = SessionLocal()
    try:
        store.recover_interrupted(db)
    finally:
        db.close()
    assert client.get(task_url(ids, task)).json()['task']['status'] == 'interrupted'
    third = client.post(endpoint, json=body).json()['data']['task']
    assert third['attempt'] == 3
    executor.run(2)  # old attempt is refused
    monkeypatch.setattr(web._jobs, 'assessor', lambda **kw: FINDING)
    monkeypatch.setattr(web._jobs, 'provider', lambda *a, **kw: single_png())
    executor.run(3)
    assert client.get(task_url(ids, task)).json()['task']['status'] == 'succeeded'


@pytest.mark.parametrize('action', ['assess', 'retry'])
def test_stop_inflight_prevents_late_result(app_fixture, monkeypatch, action):
    client, ids, _, executor, *_ = app_fixture
    path, _ = generated(app_fixture)
    endpoint = base(ids) + path + ('/assess' if action == 'assess' else '/one/retry')
    task = client.post(endpoint, json={} if action == 'assess' else {'expected_revision': 0}).json()['data']['task']
    def stop(*a, **kw):
        client.post(task_url(ids, task) + '/cancel', json={})
        return FINDING if action == 'assess' else single_png()
    monkeypatch.setattr(web._jobs, 'assessor' if action == 'assess' else 'provider', stop)
    executor.run(1)
    assert client.get(task_url(ids, task)).json()['task']['status'] == 'cancelled'
    assert client.get(base(ids) + path).json()['data']['advisory'] is None
    assert len(client.get(base(ids)).json()['data']['candidates']) == 1


def test_retry_revision_change_and_acceptance_block_spend(app_fixture, monkeypatch):
    client, ids, _, executor, *_ = app_fixture
    path, _ = generated(app_fixture)
    body = {'expected_revision': 0}
    assert client.post(base(ids) + path + '/one/retry', json={'expected_revision': True}).status_code == 422
    assert client.post(base(ids) + path + '/one/retry', json={'expected_revision': 3}).status_code == 409
    task = client.post(base(ids) + path + '/one/retry', json=body).json()['data']['task']
    client.put(base(ids) + path + '/one/review', json={'expected_revision': 0, 'identity': 'approved', 'edge': 'approved'})
    client.post(base(ids) + path + '/one/accept', json={'expected_revision': 1})
    monkeypatch.setattr(web._jobs, 'provider', lambda *a, **kw: pytest.fail('must not spend after acceptance'))
    executor.run(1)
    assert client.get(task_url(ids, task)).json()['task']['status'] == 'failed'
    response = client.post(base(ids) + path + '/one/retry', json={'expected_revision': 1})
    assert response.status_code == 400 and response.json()['detail']['code'] == 'SHEET_ACCEPTED_LOCKED'


def test_action_scope_fields_and_missing_model(app_fixture):
    client, ids, _, executor, settings, _ = app_fixture
    path, _ = generated(app_fixture)
    for kind in ('image', 'foreign'):
        prefix = f'/api/projects/{ids[kind]}/html-asset-sheets'
        assert client.post(prefix + path + '/assess', json={}).status_code in (400, 404)
        assert client.post(prefix + path + '/one/retry', json={'expected_revision': 0}).status_code in (400, 404)
    assert client.post(base(ids) + path + '/assess', json={'api_key': 'forbidden'}).status_code == 422
    assert client.post(base(ids) + path + '/missing/retry', json={'expected_revision': 0}).status_code == 400
    settings['llm_api_key'] = ''
    assert client.post(base(ids) + path + '/assess', json={}).status_code == 400
    assert len(executor.calls) == 1


def test_parent_revision_changes_inflight_prevent_candidate_write(app_fixture, monkeypatch):
    client, ids, _, executor, *_ = app_fixture
    path, _ = generated(app_fixture)
    job = client.post(base(ids) + path + '/one/retry', json={'expected_revision': 0}).json()['data']['task']
    def provider(*a, **kw):
        client.put(base(ids) + path + '/one/review', json={'expected_revision': 0, 'identity': 'rejected', 'edge': 'rejected'})
        return single_png()
    monkeypatch.setattr(web._jobs, 'provider', provider)
    executor.run(1)
    assert client.get(task_url(ids, job)).json()['task']['status'] == 'failed'
    assert len(client.get(base(ids)).json()['data']['candidates']) == 1
    assert client.get(base(ids) + path).json()['data']['decisions']['one']['identity'] == 'rejected'
