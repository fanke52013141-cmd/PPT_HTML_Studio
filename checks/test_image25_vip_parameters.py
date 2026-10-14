from types import SimpleNamespace

import pytest
import ai_provider_service as provider
import html_image_provider


@pytest.mark.parametrize('transparent', [True, False])
@pytest.mark.parametrize('model', ['gpt-image-2.5-flare-vip', 'gpt-image-2.5-sunburst-vip', 'gpt-image-2-vip'])
def test_wire_dimensions_quality_and_optional_background(monkeypatch, model, transparent):
    calls = []

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            calls.append(kwargs['json'])
            return SimpleNamespace(status_code=200, json=lambda: {'id': 'task'}, headers={})

        def get(self, url, **kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {'status': 'completed', 'result': {'data': [{'url': 'https://example.test/output.png'}]}}, headers={})

    monkeypatch.setattr(provider.httpx, 'Client', Client)
    monkeypatch.setattr(provider, '_governed_image_request', lambda base, operation, **kwargs: operation())
    provider.generate_toapis_image_response(api_key='fixture', base_url='https://example.test', model=model,
        prompt='fixture', size='2048x1152', quality='low', transparent_background=transparent)
    wire = calls[0]
    if model.startswith('gpt-image-2.5-'):
        assert wire['size'] == '2048x1152'
        assert 'resolution' not in wire
    else:
        assert wire['size'] == '16:9'
        assert wire['resolution'] == '1k'
    assert wire['quality'] == 'low'
    assert wire.get('background') == ('transparent' if transparent else None)


def test_html_adapter_passes_transparency_without_using_live_settings(monkeypatch):
    captured = {}
    monkeypatch.setattr(provider, 'generate_image_response', lambda *args, **kwargs: captured.update(kwargs))
    monkeypatch.setattr(provider, 'extract_image_bytes_from_response', lambda response: b'fixture')
    binding = SimpleNamespace(require_ready=lambda: None, api_key='fixture', endpoint='https://api.toapis.com', model='gpt-image-2.5-flare-vip', provider='toapis')
    assert html_image_provider.configured_image('fixture', size='2048x2048', transparent_background=True, model_binding=binding) == b'fixture'
    assert captured['transparent_background'] is True


def test_resume_does_not_upload_references_or_submit(monkeypatch):
    events = []
    class Client:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            raise AssertionError('resume must not upload or submit')
        def get(self, url, **kwargs):
            events.append(url)
            return SimpleNamespace(status_code=200, json=lambda: {'status': 'completed', 'result': {'data': [{'url': 'https://example.test/output.png'}]}}, headers={})
    monkeypatch.setattr(provider.httpx, 'Client', Client)
    monkeypatch.setattr(provider, '_governed_image_request', lambda base, operation, **kwargs: operation())
    result = provider.generate_toapis_image_response(api_key='fixture', base_url='https://example.test',
        model='fixture', prompt='', size=None, resume_task_id='existing-task', reference_paths=['nonexistent.png'])
    assert result['toapis_task_id'] == 'existing-task'
    assert len(events) == 1 and events[0].endswith('/existing-task')


@pytest.mark.parametrize('endpoint', ['https://api.toapis.com', 'https://api.toapis.com/v1', 'https://api.toapis.com/v1/images/generations'])
def test_official_production_wire_and_reference_upload(monkeypatch, tmp_path, endpoint):
    events = []
    reference = tmp_path / 'reference.png'
    reference.write_bytes(b'fixture')

    class Client:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, **kwargs):
            events.append((url, kwargs))
            body = {'success': True, 'data': {'url': 'https://example.test/ref.png'}} if 'files' in kwargs else {'id': 'official-task'}
            return SimpleNamespace(status_code=200, json=lambda: body, headers={})
        def get(self, url, **kwargs):
            events.append((url, kwargs))
            return SimpleNamespace(status_code=200, json=lambda: {'status': 'completed', 'result': {'data': [{'url': 'https://example.test/output.png'}]}}, headers={})

    monkeypatch.setattr(provider.httpx, 'Client', Client)
    monkeypatch.setattr(provider, '_governed_image_request', lambda base, operation, **kwargs: operation())
    receipts = []
    provider.generate_toapis_image_response(api_key='fixture', base_url=endpoint,
        model='gpt-image-2.5-sunburst-official', prompt='fixture', size='2048x1152',
        resolution='2k', quality='low', reference_paths=[str(reference)], on_task_submitted=receipts.append)
    assert [event[0] for event in events] == ['https://api.toapis.com/v1/uploads/images', 'https://api.toapis.com/v1/images/generations', 'https://api.toapis.com/v1/images/generations/official-task']
    assert events[1][1]['json'] == {'model': 'gpt-image-2.5-sunburst-official', 'prompt': 'fixture', 'n': 1, 'size': '2048x1152', 'quality': 'low', 'image_urls': ['https://example.test/ref.png']}
    assert receipts == ['official-task']


@pytest.mark.parametrize('size, transparent, expected, resolution', [('1280x720', False, '2048x1152', '2k'), ('1024x1024', True, '1024x1024', '1k')])
def test_html_official_frozen_2k_dimensions(monkeypatch, size, transparent, expected, resolution):
    captured = {}
    def generate(client, model, prompt, dimensions, **kwargs):
        captured.update(size=dimensions, **kwargs)
    monkeypatch.setattr(provider, 'generate_image_response', generate)
    monkeypatch.setattr(provider, 'extract_image_bytes_from_response', lambda response: b'fixture')
    binding = SimpleNamespace(require_ready=lambda: None, api_key='fixture', endpoint='https://api.toapis.com/v1', model='gpt-image-2.5-sunburst-official', provider='toapis', image_resolution='2K', image_quality='low')
    html_image_provider.configured_image('fixture', size=size, transparent_background=transparent, model_binding=binding)
    assert captured['size'] == expected
    assert captured['public_config'] == {'toapis_resolution': resolution, 'toapis_quality': 'low'}
