"""All exposed reference/reuse transports resolve the same registered contracts."""
from unittest.mock import MagicMock
import pytest
from agent_client.client import AgentClient
from cli.pptctl import build_parser
from mcp_server.tools import _dispatch


def test_mcp_reference_paths_are_encoded_and_payload_is_strict():
    client=MagicMock()
    _dispatch('html_review.reference_resume',{'project_id':'p/a','slide_id':'s/b','job_id':'j/c',
        'session_sha256':'a'*64,'mapping':{'targets':[]}},client)
    client._request.assert_called_once_with('POST',
        '/api/agent/v1/projects/p%2Fa/html-review/s%2Fb/reference/j%2Fc/resume',
        body={'session_sha256':'a'*64,'mapping':{'targets':[]}})
    with pytest.raises(ValueError,match='Invalid request'):
        _dispatch('html_review.reference_read',{'project_id':'p','slide_id':'s','job_id':'j','api_key':'secret'},client)


def test_sdk_reference_methods_and_cli_correction_file():
    client=AgentClient();client._request=MagicMock(return_value={})
    client.html_reusable_assets('p','s')
    client._request.assert_called_with('GET','/projects/p/html-review/s/reusable-assets')
    client.html_reference_read('p','s','j')
    client._request.assert_called_with('GET','/projects/p/html-review/s/reference/j')
    client.html_reference_resume('p','s','j',{'mapping':{}})
    client._request.assert_called_with('POST','/projects/p/html-review/s/reference/j/resume',body={'mapping':{}})
    args=build_parser().parse_args(['html','reference-resume','--project','p','--slide','s','--job','j','--file','correction.json'])
    assert args.file=='correction.json' and args.capability_id=='html_review.reference_resume'
