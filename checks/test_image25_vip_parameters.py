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
