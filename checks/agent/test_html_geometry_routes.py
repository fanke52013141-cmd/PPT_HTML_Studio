"""Shared Web/Agent dispatch and schema-driven MCP/CLI contracts; no providers."""
import pytest

from checks.agent.test_html_editor_binding_integration import api as api
import html_repair_orchestration as flow


def test_web_agent_geometry_skips_model_configuration_and_preserves_scene(api, monkeypatch):
    client, ids, run, scene = api
    import project_model_binding_service as models
    def forbidden(*args, **kwargs):
        pytest.fail('Successful geometry must not freeze models')
    monkeypatch.setattr(models, 'freeze_project_models', forbidden)
    monkeypatch.setattr(flow.geometry, 'geometry_repair', lambda *_: {'status': 'unchanged',
        'baseline': {'passed': True, 'issues': []}, 'attempts': [], 'elapsed_seconds': 1})
    body = {'expected_revision': 1, 'scope': ['headline'], 'strategy': 'geometry_first',
            'instruction': flow.OVERLAP_INSTRUCTION}
    for prefix in ['/api', '/api/agent/v1']:
        base = f"{prefix}/projects/{ids['html']}/html-visual/condensation"
        response = client.post(base + '/repair/generate', json=body)
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'unchanged'
        assert client.get(base + '/editor').json()['revision'] == 1
        assert client.post(base + '/repair/generate', json={**body, 'strategy': 'invalid'}).status_code == 422
        assert client.post(base + '/repair/generate', json={**body, 'expected_revision': 999}).status_code == 409


def test_geometry_contract_all_transports_share_new_optional_strategy():
    from agent_contract.capabilities import get_capability
    from agent_contract.schema import capability_input_schema
    cap = get_capability('html_repair.generate')
    schema = capability_input_schema(cap)
    assert schema['properties']['strategy']['enum'] == ['model', 'geometry_first', 'capacity_first', 'layout_first']
    assert schema['properties']['strategy']['default'] == 'model'
    assert cap.version == '1.8' and cap.mcp_tool_name == 'ppt_html_repair_generate'
    assert cap.cli_command == 'html repair-generate'
