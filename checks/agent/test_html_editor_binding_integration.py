"""Five new Agent capabilities: real HTTP adapters/services and transport calls.

pytest conftest isolates database/runs before importing any application module.
No live app service, providers or existing project data are used.
"""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import Project, SessionLocal, get_db
from agent_api import routes
from agent_api.errors import AgentAPIError, agent_error_handler
from agent_contract.capabilities import get_capability
from agent_contract.models import HtmlEditorSaveRequest, ProjectModelBindingSaveRequest
from html_visual_routes import SceneEditorSaveRequest
from project_model_binding_models import ProjectModelBindingUpdate

NEW_IDS = ("project_model_binding.read", "project_model_binding.write", "html_editor.read",
           "html_editor.write", "html_editor.preview")


@pytest.fixture
def api(tmp_path, monkeypatch):
    import project_model_binding_routes as model_routes
    import project_model_binding_service as models
    from model_connection_service import ResolvedModelConnection
    from repository_paths import RUNS_DIR
    from html_visual_store import save_scene

    root = Path(__file__).resolve().parents[2]
    ids = {kind: "agent-n02-" + uuid.uuid4().hex for kind in ("html", "image", "foreign")}
    db = SessionLocal()
    for kind, pid in ids.items():
        run = Path(RUNS_DIR) / pid
        run.mkdir(parents=True)
        db.add(Project(id=pid, name=kind, run_dir=str(run),
                       visual_backend="image" if kind == "image" else "html",
                       account_id="another-account" if kind == "foreign" else "default"))
    db.commit()
    run = Path(RUNS_DIR) / ids['html']
    scene = json.loads((root / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    save_scene(run, 'condensation', scene, 0)
    (run / "planning/visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": "condensation", "narration_beats": [{"id": "b1", "text": "test"}]}]}), encoding="utf-8")
    connection = lambda ident: ResolvedModelConnection(ident, 1, 'text', 'openai', ident,
        'https://private-endpoint.test/v1', 'credential-private-ref', {}, 'active')
    settings = {'llm_model':'global-text','image_model':'global-image','llm_api_key':'secret-text',
                'image_api_key':'secret-image'}
    original_read = models.get_project_model_binding
    original_save = models.save_project_model_binding
    monkeypatch.setattr(model_routes, 'get_project_model_binding', lambda p: original_read(p,
        resolver=connection, credential=lambda _: {'api_key':'private-key'}, setting=settings.get))
    monkeypatch.setattr(model_routes, 'save_project_model_binding', lambda p,r: original_save(p,r,binder=connection))
    # Both adapters use real account/backend gates, actual store and compiler.
    app = FastAPI(); app.include_router(routes.router)
    import html_visual_routes
    app.include_router(html_visual_routes.router); app.include_router(model_routes.router)
    app.add_exception_handler(AgentAPIError, agent_error_handler)
    def database():
        session=SessionLocal()
        try: yield session
        finally: session.close()
    app.dependency_overrides[get_db]=database
    app.dependency_overrides[html_visual_routes._get_db]=database
    with TestClient(app) as client:
        yield client,ids,run,scene
    for pid in ids.values():
        db.query(Project).filter(Project.id==pid).delete()
    db.commit();db.close()


def test_request_parity_and_unknown_fields():
    pairs=((ProjectModelBindingUpdate,ProjectModelBindingSaveRequest),
           (SceneEditorSaveRequest,HtmlEditorSaveRequest))
    for internal,public in pairs:
        assert set(internal.model_fields)==set(public.model_fields)
        a,b=internal.model_json_schema(),public.model_json_schema()
        a.pop('title',None);b.pop('title',None)
        a.pop('description',None);b.pop('description',None)
        # Agent supplies a coordinate-chain description, preserving Web validation.
        for props in (a['properties'],b['properties']):
            for value in props.values():value.pop('description',None)
        assert a==b
        assert b['additionalProperties'] is False


def test_model_binding_read_write_noop_conflict_and_redaction(api):
    client,ids,run,_=api
    url=f"/api/agent/v1/projects/{ids['html']}/model-binding"
    initial=client.get(url); assert initial.status_code==200,initial.text
    assert initial.json()['bindings']['text']['mode']=='legacy'
    data={'expected_revision':0,'text':{'mode':'fixed','connection_id':'model-A'},'image':{'mode':'inherit'}}
    saved=client.put(url,json=data);assert saved.status_code==200,saved.text
    assert saved.json()=={'project_id':ids['html'],'revision':1,'changed':True}
    data['expected_revision']=1
    assert client.put(url,json=data).json()['changed'] is False
    assert client.put(url,json={**data,'expected_revision':0}).status_code==409
    read=client.get(url)
    assert read.json()['effective']['text']['model']=='model-A'
    for hidden in ('private-key','credential-private-ref','private-endpoint','secret-text','secret-image'):
        assert hidden not in read.text
    web=client.get(f"/api/projects/{ids['html']}/model-binding").json()
    assert {k:v for k,v in read.json().items() if k!='project_id'}==web
    for payload in ({**data,'api_key':'not-allowed'}, {**data,'text':{'mode':'fixed','connection_id':'model-A','endpoint':'not-allowed'}}):
        assert client.put(url,json=payload).status_code==422
    assert client.get(f"/api/agent/v1/projects/{ids['foreign']}/model-binding").status_code==404
    assert client.put(f"/api/agent/v1/projects/{ids['image']}/model-binding",json=data).status_code==400


def test_scene_edit_get_preview_write_reopen_and_conflict(api):
    client,ids,run,scene=api
    url=f"/api/agent/v1/projects/{ids['html']}/html-visual/condensation/editor"
    read=client.get(url); assert read.status_code==200,read.text
    assert read.json()['capabilities']['actions']==['enter','exit','emphasize']
    scene['nodes'][0]['title']='Agent authored'
    binding={'format':'hps.html.motion_binding','version':'0.1.0','mode':'beat_ids',
             'actions':{'header:enter':{'beatId':'b1','edge':'start','offsetMs':0}}}
    data={'scene':scene,'binding':binding,'expected_revision':1,'anchor_overrides':{}}
    before=(run/'planning/html_visual/revision.json').read_bytes()
    preview=client.post(url+'/preview',json=data)
    assert preview.status_code==200,preview.text
    assert preview.json()['clock']=='author'
    assert before==(run/'planning/html_visual/revision.json').read_bytes()
    web=client.post(f"/api/projects/{ids['html']}/html-visual/condensation/editor/preview",json=data).json()
    assert {k:v for k,v in preview.json().items() if k not in ('project_id','slide_id')}=={k:v for k,v in web.items() if k!='success'}
    saved=client.put(url,json=data);assert saved.status_code==200,saved.text
    data['expected_revision']=saved.json()['revision']
    assert client.put(url,json=data).json()['changed'] is False
    reopened=client.get(url).json();assert reopened['scene']==scene and reopened['binding']==binding
    conflict=client.put(url,json={**data,'expected_revision':1})
    assert conflict.status_code==409
    assert conflict.json()['error']['details']['current_revision']==2
    assert client.get(url).json()['scene']==scene
    for payload in ({**data,'unknown':True},{**data,'expected_revision':True}):
        assert client.put(url,json=payload).status_code==422
    image=next(n for n in scene['nodes'] if n['type']=='image')
    invalid={**data,'anchor_overrides':{image['id']:[{'id':'focus','x':1.2,'y':0.5}]}}
    assert client.put(url,json=invalid).status_code==422
    assert client.get(url.replace(ids['html'],ids['foreign'])).status_code==404
    assert client.post(url.replace(ids['html'],ids['image'])+'/preview',json=data).status_code==400


@pytest.mark.parametrize('cap_id',NEW_IDS)
def test_mcp_dispatch_and_cli_reach_real_http(cap_id,api,monkeypatch,tmp_path,capsys):
    """No live socket: existing transports execute real FastAPI requests in-process."""
    from agent_client.client import AgentClient,AgentClientError
    from mcp_server.tools import get_tool_handler
    from cli import pptctl
    client,ids,run,scene=api
    cap=get_capability(cap_id)
    args={'project_id':ids['html']}
    if cap_id.startswith('html_editor.'):
        args['slide_id']='condensation'
    if cap_id=='project_model_binding.write':
        args.update(expected_revision=0,text={'mode':'inherit'},image={'mode':'inherit'})
    elif cap_id in ('html_editor.write','html_editor.preview'):
        args.update(scene=scene,binding=None,expected_revision=1,anchor_overrides={})
    calls=[]
    def request(self,method,path,body=None,params=None,timeout=None):
        calls.append((method,path,body))
        response=client.request(method,path,json=body,params=params)
        if response.status_code>=400:raise AgentClientError(response.text,response.status_code)
        return response.json()
    monkeypatch.setattr(AgentClient,'_request',request)
    blocks=get_tool_handler(cap.mcp_tool_name)(copy.deepcopy(args),AgentClient())
    assert not any(b.get('_agent_error') for b in blocks),blocks
    assert calls and calls[0][0]==cap.agent_api_method
    result=json.loads(blocks[0]['text']);assert result['project_id']==ids['html']
    # A write consumed revision; CLI reuses the fresh revision.
    if cap_id=='project_model_binding.write':args['expected_revision']=result['revision']
    if cap_id=='html_editor.write':args['expected_revision']=result['revision']
    argv=cap.cli_command.split()+['--project',ids['html']]
    if 'slide_id' in args:argv+=['--slide',args['slide_id']]
    if cap.agent_api_method!='GET':
        payload={k:v for k,v in args.items() if k not in ('project_id','slide_id')}
        file=tmp_path/'request.json';file.write_text(json.dumps(payload),encoding='utf-8')
        argv+=['--file',str(file)]
    parsed=pptctl.build_parser().parse_args(argv)
    parsed.func(parsed)
    output=json.loads(capsys.readouterr().out)
    assert output['project_id']==ids['html']
