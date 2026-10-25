from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError
from html_evaluation_models import EvaluationCommand
from mcp_server.tools import _dispatch
from cli.pptctl import build_parser
from agent_client.client import AgentClient


def test_all_evaluation_operations_share_closed_discriminated_schema():
    with pytest.raises(ValidationError):EvaluationCommand.model_validate({'command':{'action':'shell','cmd':'whoami'}})
    with pytest.raises(ValidationError):EvaluationCommand.model_validate({'command':{'action':'start_experiment',
        'dataset_id':'labels','endpoint':'https://invalid'}})
    client=MagicMock()
    body={'action':'read_case','dataset_id':'labels','case_id':'page-0'}
    _dispatch('html_evaluation.command',{'project_id':'p/a','command':body},client)
    client._request.assert_called_once_with('POST','/api/agent/v1/projects/p%2Fa/html-evaluation/action',body={'command':body})
    parser=build_parser();args=parser.parse_args(['html','evaluation-command','--project','p','--file','command.json'])
    assert args.file=='command.json' and args.capability_id=='html_evaluation.command'


def test_evaluation_sdk_methods_use_project_api():
    client=AgentClient();client._request=MagicMock(return_value={})
    client.html_evaluation_read('p');client._request.assert_called_with('GET','/projects/p/html-evaluation')
    client.html_evaluation_command('p',{'action':'read_case'})
    client._request.assert_called_with('POST','/projects/p/html-evaluation/action',body={'command':{'action':'read_case'}})
