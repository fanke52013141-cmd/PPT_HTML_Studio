from types import SimpleNamespace
import threading
import uuid
import pytest
import generation_control as control


def test_exact_operation_stop_does_not_cancel_next_job():
    project_id = uuid.uuid4().hex
    first = control.reserve(project_id, 'video')
    assert not control.request_stop(project_id, 'video', 'wrong')['accepted']
    assert control.request_stop(project_id, 'video', first)['accepted']
    with pytest.raises(control.GenerationStopped):
        control.checkpoint(project_id, 'video')
    control.finish(project_id, 'video', first)
    second = control.reserve(project_id, 'video')
    try:
        control.finish(project_id, 'video', first)
        assert not control.request_stop(project_id, 'video', first)['accepted']
        control.checkpoint(project_id, 'video')
        assert control.status(project_id, 'video')['operation_id'] == second
    finally:
        control.finish(project_id, 'video', second)


def test_signal_crosses_worker_threads_and_cleans_up():
    project_id = uuid.uuid4().hex
    ready = threading.Event()
    proceed = threading.Event()
    outputs = []

    @control.controlled('storyboard_script')
    def generate(project_id):
        ready.set()
        assert proceed.wait(5)
        control.checkpoint(project_id, 'storyboard_script')
        raise AssertionError('cancelled content must not be persisted')

    thread = threading.Thread(target=lambda: outputs.append(generate(project_id)))
    thread.start()
    assert ready.wait(5)
    operation_id = control.status(project_id, 'storyboard_script')['operation_id']
    control.request_stop(project_id, 'storyboard_script', operation_id)
    proceed.set()
    thread.join(5)
    assert not thread.is_alive()
    assert outputs[0]['cancelled'] is True
    assert not control.status(project_id, 'storyboard_script')['active']


def test_controlled_method_uses_project_identity():
    project = SimpleNamespace(id=uuid.uuid4().hex)

    class Service:
        @control.controlled('mask', method=True)
        def annotate(self, project):
            state = control.status(project.id, 'mask')
            assert state['active']
            control.request_stop(project.id, 'mask', state['operation_id'])
            control.checkpoint(project.id, 'mask')

    assert Service().annotate(project)['cancelled']
    assert not control.status(project.id, 'mask')['active']


def test_controlled_call_preserves_keyword_arguments():
    project_id = uuid.uuid4().hex
    @control.controlled('storyboard_visual')
    def generate(project_id, *, payload):
        assert control.status(project_id, 'storyboard_visual')['active']
        return payload
    assert generate(project_id=project_id, payload={'success': True})['success']


def test_stop_handler_runs_once_and_can_finish_without_deadlocking():
    project_id = uuid.uuid4().hex
    identity = control.reserve(project_id, 'tts')
    calls = []
    def cancel_queued():
        calls.append(identity)
        control.finish(project_id, 'tts', identity)
    control.bind_stop_handler(project_id, 'tts', identity, cancel_queued)
    assert control.request_stop(project_id, 'tts', identity)['accepted']
    assert not control.request_stop(project_id, 'tts', identity)['accepted']
    assert calls == [identity]


def test_queued_tts_stop_is_persisted_without_calling_provider(tmp_path):
    from checks.test_persistent_tts_jobs import _session_factory, _make_project, _build_service
    session_factory = _session_factory(tmp_path)
    _make_project(session_factory, tmp_path)
    calls = []
    service = _build_service(session_factory, lambda *_args: calls.append(True), submit_noop=True)
    with session_factory() as db:
        job = service.create_job(db, 'project-tts')['job']
        control.request_stop('project-tts', 'tts', job['id'])
        service.run_job(job['id'])
        final = service.get_job(db, 'project-tts', job['id'])['job']
    assert final['status'] == 'cancelled'
    assert final['error'] is None
    assert final['finished_at']
    assert calls == []
    assert not control.status('project-tts', 'tts')['active']


def test_remotion_stop_removes_unpublished_mp4(tmp_path, monkeypatch):
    from remotion_runner import RemotionRunner, RemotionRunnerDependencies
    from checks.test_video_render_components import _config
    output = tmp_path / 'cancelled.mp4'
    output.write_bytes(b'partial output')
    runner = RemotionRunner(RemotionRunnerDependencies(config=_config(tmp_path),
        build_reveal_assets=lambda *_args: None, write_project_log=lambda *_args, **_kwargs: None,
        run_subprocess_bounded=lambda *_args, **_kwargs: None, resolve_media_tool=lambda *_args: None))
    monkeypatch.setattr(runner, '_select_video_encoder', lambda *_args: None)
    monkeypatch.setattr(runner, '_bind_timeline', lambda *_args: None)
    monkeypatch.setattr(runner, '_build_remotion_props', lambda *_args: ({}, tmp_path))
    monkeypatch.setattr(runner, '_ensure_remotion_dependencies', lambda *_args: None)
    monkeypatch.setattr(runner, '_render_video', lambda *_args: (output, output.name))
    def stopped(*_args):
        raise control.GenerationStopped('用户停止')
    monkeypatch.setattr(runner, '_validate_render_color', stopped)
    with pytest.raises(control.GenerationStopped):
        runner.run(SimpleNamespace(id='test-stop'), output_dir=tmp_path, set_stage=lambda *_args: None)
    assert not output.exists()


def test_exception_releases_control_and_duplicate_does_not_replace_it():
    project_id = uuid.uuid4().hex
    with pytest.raises(ValueError):
        with control.operation(project_id, 'tts'):
            with pytest.raises(control.GenerationAlreadyRunning):
                control.reserve(project_id, 'tts')
            raise ValueError('provider failure')
    assert not control.status(project_id, 'tts')['active']


def test_web_stop_cannot_access_another_account():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from database import Project, SessionLocal, get_db
    from generation_control_routes import router
    project_id = uuid.uuid4().hex
    with SessionLocal() as db:
        db.add(Project(id=project_id, name='Isolated stop fixture', account_id='other-account', run_dir=''))
        db.commit()
    app = FastAPI()
    app.include_router(router)
    def session():
        with SessionLocal() as db:
            yield db
    app.dependency_overrides[get_db] = session
    operation_id = control.reserve(project_id, 'mask')
    try:
        with TestClient(app) as client:
            response = client.post(f'/api/projects/{project_id}/generation-control/mask/stop', json={'operation_id': operation_id})
        assert response.status_code == 404
        assert not control.stop_requested(project_id, 'mask')
    finally:
        control.finish(project_id, 'mask', operation_id)
