"""Original-browser acceptance matrix for the remaining engineering criteria.

Every success retains full output-frame evidence and immutable source inputs.
Fault injection is explicit; no model/provider or production approval is used.
"""
import copy
import json

import pytest

import html_capacity_repair as capacity
import html_scene_editing as editor
from html_linked_layout import solve_production_layout
from html_visual_review_service import HtmlReviewDependencies, review_scene
from html_visual_store import save_scene
from checks.test_html_candidate_capacity_solver import ROOT, document


def no_model(**kwargs):
    pytest.fail('deterministic engineering matrix must not call models')


def complete(result, run):
    assert result['summary']['status'] == 'candidate', result['summary']
    preflight = result['report']['geometry_preflight']
    assert preflight['passed'] and preflight['coverage']['frame_complete']
    raw = json.loads((run/preflight['audit']/'report.json').read_text(encoding='utf-8'))
    assert raw['passed'] and not raw['issues'] and not raw['pageErrors']
    assert len(raw['frames']) == len(raw['coverage']['times']) > 1
    assert [f['timeMs'] for f in raw['frames']] == raw['coverage']['times']
    assert raw['coverage']['fps'] == 30 and raw['coverage']['mode'] == 'output_frames'
    assert result['summary']['provider_calls'] == result['summary']['author_writes'] == 0


@pytest.fixture(scope='module')
def matrix(tmp_path_factory):
    results = {}
    for name, ids in [('two', ['card-1', 'card-2']), ('three', ['card-1', 'card-2', 'card-3']),
                      ('reverse', ['card-1', 'card-2', 'card-3']), ('leaf', ['card-1', 'card-2'])]:
        run = tmp_path_factory.mktemp('engineering-'+name)
        scene = document()
        for node in scene['nodes']:
            if node['id'] in ids: node['presentation'] = {'height': 80}
        if name == 'reverse': scene['nodes'].reverse()
        manual = {'protected_paths': [['scene','nodes','card-1','presentation','width']]} if name == 'leaf' else None
        # Pin all immutable inputs, including protected metadata, narration and
        # opaque prior evidence. Candidate/review files are the allowed outputs.
        files = {'inputs/article.md': b'original article', 'audio/original.mp3': b'audio-evidence',
                 'planning/original-approval.json': b'{"approved":false}'}
        for relative, data in files.items():
            target=run/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        original = copy.deepcopy(scene)
        result = solve_production_layout(scene,None,run_dir=run,manual=manual,
            deps=HtmlReviewDependencies(ROOT,no_model))
        complete(result,run)
        assert scene == original
        assert result['binding'] is None
        assert all((run/relative).read_bytes() == data for relative,data in files.items())
        assert not list((run/'planning/html_visual').glob('scene-*.json'))
        for before in original['nodes']:
            after = next(n for n in result['scene']['nodes'] if n['id']==before['id'])
            assert {k:v for k,v in before.items() if k!='presentation'} == {k:v for k,v in after.items() if k!='presentation'}
        assert result['scene']['motion'] == original['motion']
        results[name] = (run, original, result)
    return results


def test_multiple_objects_and_inherited_fonts_finish_with_original_full_frames(matrix):
    for name,(_,before,result) in matrix.items():
        for key in ('card-1','card-2') + (('card-3',) if name in ('three','reverse') else ()):
            old=next(n for n in before['nodes'] if n['id']==key)
            new=next(n for n in result['scene']['nodes'] if n['id']==key)
            assert new != old
            assert 'typography' not in old.get('presentation',{})


def test_target_order_cannot_starve_any_of_three_objects(matrix):
    _,_,forward=matrix['three'];_,_,reverse=matrix['reverse']
    assert {n['id']:n for n in forward['scene']['nodes']} == {n['id']:n for n in reverse['scene']['nodes']}


def test_leaf_protection_allows_sibling_height_and_preserves_sources(matrix):
    _,before,result=matrix['leaf']
    old=next(n for n in before['nodes'] if n['id']=='card-1')
    new=next(n for n in result['scene']['nodes'] if n['id']=='card-1')
    assert new['presentation']['height'] != old['presentation']['height']
    assert new['presentation'].get('width') == old['presentation'].get('width')


def test_no_unreadable_typography_in_any_original_browser_candidate(matrix):
    for _,_,result in matrix.values():
        for node in result['scene']['nodes']:
            for style in node.get('presentation',{}).get('typography',{}).values():
                assert style.get('fontSizePx',24) >= 24
                assert style.get('lineHeight',1) >= 1


def test_real_browser_budget_has_distinct_terminal_state(tmp_path):
    scene=document();next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'height':80}
    result=capacity.solve_capacity_candidate(scene,None,run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,no_model),max_states=1)
    assert result['summary']['status']=='budget_exhausted'
    assert result['summary']['passed'] is False
    assert result['summary']['reason']=='CAPACITY_SEARCH_BUDGET'
    assert result['summary']['measured_states']==1
    assert (tmp_path/result['summary']['audit']/'000/render.png').is_file()


def test_saved_unsaved_candidate_semantics_and_all_input_snapshots(matrix,tmp_path):
    from html_saved_layout_repair import generate, INSTRUCTION
    run,scene,unsaved=matrix['two']
    save_scene(tmp_path,scene['id'],scene,0)
    prior=editor.load_editor(tmp_path,scene['id'])
    source_bytes={p.relative_to(tmp_path):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    request={'expected_revision':1,'scope':['card-1','card-2','card-3','summary'],'instruction':INSTRUCTION}
    saved=generate(tmp_path,scene['id'],request)
    assert saved['status']=='candidate'
    assert saved['scene']==unsaved['scene']
    assert saved['review']['passed']
    assert editor.load_editor(tmp_path,scene['id'])==prior
    with pytest.raises(Exception) as stale:
        generate(tmp_path,scene['id'],{**request,'expected_revision':0})
    assert type(stale.value).__name__=='HtmlVisualConflict'
    with pytest.raises(editor.SceneEditError) as audio:
        generate(tmp_path,scene['id'],{**request,'expected_audio_revision':'f'*64})
    assert audio.value.code=='AUDIO_REVISION_CONFLICT'
    assert editor.load_editor(tmp_path,scene['id'])==prior
    assert all((tmp_path/name).read_bytes()==data for name,data in source_bytes.items())


def test_manual_block_and_cancelled_search_preserve_document_and_evidence(tmp_path):
    scene=document();next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'height':80}
    original=copy.deepcopy(scene)
    manual={'protected_paths':[['scene','nodes','card-1','presentation']]}
    result=capacity.solve_capacity_candidate(scene,None,manual=manual,run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,no_model))
    assert result['summary']['status']=='needs_revision'
    assert any(a.get('code')=='MANUAL_FIELD_PROTECTED' for a in result['summary']['attempts'])
    assert scene==original and result['scene']==original
    class Cancelled(Exception): pass
    stopped=[]
    def progress(value): stopped.append(value)
    def stop():
        if stopped: raise Cancelled('explicit cooperative stop after first real measurement')
    with pytest.raises(Cancelled):
        capacity.solve_capacity_candidate(scene,None,run_dir=tmp_path,
            checkpoint=stop,progress=progress,deps=HtmlReviewDependencies(ROOT,no_model))
    assert stopped and scene==original
    assert not list((tmp_path/'planning/html_visual').glob('scene-*.json'))


def test_real_capacity_blocks_dynamic_instead_of_claiming_full_pass(tmp_path):
    scene=document();next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'height':20}
    report=review_scene(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,no_model),
                        diagnostic=True,preflight_dir=tmp_path/'temporal')
    assert not report['passed'] and report['capacityIssues']
    assert report['geometry_preflight']['status']=='blocked_by_capacity'
    assert not (tmp_path/'temporal/report.json').exists()



def test_actual_frame_evidence_cannot_be_truncated_or_relabelled(matrix,tmp_path):
    import subprocess
    from html_visual_review_service import _geometry_preflight, HtmlReviewError
    run,_,result=matrix['two']
    scene=result['scene']
    raw=json.loads((run/result['report']['geometry_preflight']['audit']/'report.json').read_text(encoding='utf-8'))
    original_runner=HtmlReviewDependencies(ROOT,no_model).run_subprocess_bounded
    for damage in ('missing_frame','paired_truncation','wrong_fps','missing_report','timeout'):
        folder=tmp_path/damage
        altered=copy.deepcopy(raw)
        if damage=='missing_frame': altered['frames'].pop(2)
        if damage=='paired_truncation':
            altered['frames'].pop(2);altered['coverage']['times'].pop(2)
        if damage=='wrong_fps': altered['coverage']['fps']=24
        def runner(args,**kwargs):
            if '-e' in args:return original_runner(args,**kwargs)
            if damage=='timeout':raise TimeoutError('injected checker timeout')
            if damage!='missing_report':(folder/'report.json').write_text(json.dumps(altered),encoding='utf-8')
            return subprocess.CompletedProcess(args,0,'','')
        with pytest.raises((HtmlReviewError,TimeoutError)):
            _geometry_preflight(scene,tmp_path,HtmlReviewDependencies(ROOT,no_model,runner),folder)


def test_actual_browser_cache_reuses_only_exact_inputs_and_intact_evidence(tmp_path):
    from html_page_budget import page_budgeted, current_budget
    from html_review_cache import cached_review
    from html_visual_review_service import review_scene
    scene=document();calls=[]
    @cached_review
    def render(scene,**kwargs):
        calls.append(1)
        return review_scene.__wrapped__(scene,**kwargs)
    @page_budgeted
    def task(*,run_dir,deps,checkpoint=lambda:None):
        first=render(scene,run_dir=run_dir,deps=deps)
        assert first['passed']
        assert render(scene,run_dir=run_dir,deps=deps)==first and len(calls)==1
        (run_dir/first['screenshot']).write_bytes(b'injected corruption')
        assert render(scene,run_dir=run_dir,deps=deps)['passed'] and len(calls)==2
        changed=copy.deepcopy(scene);changed['name']+=' updated'
        assert render(changed,run_dir=run_dir,deps=deps)['passed'] and len(calls)==3
        assert any(e['kind']=='review_cache_hit' for e in current_budget().events)
    task(run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,no_model))



@pytest.fixture
def production_case(tmp_path):
    from PIL import Image
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    record=json.loads((ROOT/'docs/plans/html-backend-development/evidence/a02-model-smoke-2026-10-13.json').read_text(encoding='utf-8'))
    plan=record['plan']
    contract={'slide_id':plan['slide_id'],'narration_beats':[{'id':b['id'],'spoken_text':b['spoken_text']} for b in plan['beats']]}
    scene,binding=compile_plan(plan,contract,load_template_catalog(ROOT))
    (tmp_path/'planning').mkdir(exist_ok=True)
    (tmp_path/'planning/visual_contract.json').write_text(json.dumps({'slides':[contract]}),encoding='utf-8')
    reference=tmp_path/'reference.png';Image.new('RGB',(1280,720),'white').save(reference)
    return tmp_path,scene,binding,reference,contract


def test_initial_production_overflow_uses_zero_model_deterministic_repair(production_case):
    from html_design_reconstruction import reconstruct_design
    from checks.html_design_agent_fixture import response_for
    run,scene,binding,reference,contract=production_case
    next(n for n in scene['nodes'] if n['id']=='header')['presentation']={'height':20}
    before=copy.deepcopy(scene);calls=[]
    def generator(**kwargs):
        prefix=kwargs['artifact_prefix'];calls.append(prefix)
        assert not prefix.startswith('layout-agent-')
        return response_for(kwargs) or {'status':'unchanged','message':'controlled unchanged'}
    result=reconstruct_design(scene,binding,reference,run_dir=run,
        deps=HtmlReviewDependencies(ROOT,generator),beats=contract['narration_beats'])
    audit=run/result['summary']['audit']
    repaired=json.loads((audit/'allocation-capacity-repair.json').read_text(encoding='utf-8'))
    assert repaired['summary']['status']=='candidate'
    assert repaired['summary']['provider_calls']==repaired['summary']['model_calls']==0
    assert any(p.startswith('design_understanding-') for p in calls)
    assert any(p.startswith('design_fidelity_review-') for p in calls)
    assert result['report']['geometry_preflight']['passed'] and scene==before
    assert result['binding']==binding and result['scene']['motion']==before['motion']
    assert not list((run/'planning/html_visual').glob('scene-*.json'))


def test_variant_overflow_uses_same_zero_model_deterministic_path(production_case):
    from html_design_reconstruction import reconstruct_design
    from checks.html_design_agent_fixture import response_for
    run,scene,binding,reference,contract=production_case
    calls=[]
    def generator(**kwargs):
        prefix=kwargs['artifact_prefix'];calls.append(prefix)
        assert not prefix.startswith('layout-agent-')
        response=response_for(kwargs)
        if response is not None:return response
        # Original reconstruction operation applies a registered variant and
        # a too-short box; the third production checkpoint must repair it.
        return {'status':'candidate','operations':[
            {'targetId':'header','kind':'set_variant','values':{'variant':'header-badge'}},
            {'targetId':'header','kind':'set_presentation','values':{'height':20}}]}
    before=copy.deepcopy(scene)
    result=reconstruct_design(scene,binding,reference,run_dir=run,
        deps=HtmlReviewDependencies(ROOT,generator),beats=contract['narration_beats'])
    audit=run/result['summary']['audit']
    repaired=json.loads((audit/'0/deterministic-layout.json').read_text(encoding='utf-8'))
    assert repaired['status']=='candidate' and repaired['model_calls']==repaired['provider_calls']==0
    assert result['report']['geometry_preflight']['coverage']['frame_complete']
    assert next(n for n in result['scene']['nodes'] if n['id']=='header')['presentation']['variant']=='header-badge'
    assert result['binding']==binding and result['scene']['motion']==before['motion'] and scene==before



def test_source_changes_during_real_search_never_issue_candidate(tmp_path):
    scene=document();next(n for n in scene['nodes'] if n['id']=='card-1')['presentation']={'height':80}
    changes=[]
    def progress(value):
        if not changes:
            scene['name']+=' source changed during search';changes.append(1)
    result=capacity.solve_capacity_candidate(scene,None,run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,no_model),progress=progress)
    assert result['summary']['status']=='stale'
    assert not result['summary']['passed'] and result['summary']['reason']=='CAPACITY_SOURCE_STALE'
    assert not list((tmp_path/'planning/html_visual').glob('scene-*.json'))



def test_entry_arrow_crosses_text_even_when_final_frame_is_clear(tmp_path):
    from checks.test_html_production_preflight import stage_scene
    scene=stage_scene()
    next(n for n in scene['nodes'] if n['id']=='label-1')['runs'][0]['text']='降水形成径流并通过下渗回到地下'
    baseline=review_scene(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,no_model),
                          preflight_dir=tmp_path/'baseline')
    assert baseline['passed']
    action=next(a for a in scene['motion'] if a['targetId']=='label-1' and a['type']=='enter')
    action['offsetY']=-100
    action['startMs']=7000
    report=review_scene(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,no_model),
                        preflight_dir=tmp_path/'entry')
    assert not report['passed']
    raw=json.loads((tmp_path/'entry/report.json').read_text(encoding='utf-8'))
    crossings=[i for i in raw['issues'] if i.get('measured',{}).get('reason')=='stroke_crosses_text']
    assert crossings
    assert all(i['timeMs'] < action['startMs']+action['durationMs'] for i in crossings)
    assert not any(i['timeMs']==scene['durationMs'] for i in raw['issues'])



def test_anchor_and_implicit_endpoints_are_excluded_on_actual_browser_evidence(tmp_path):
    from checks.test_html_production_preflight import stage_scene
    from html_geometry_repair import propose_endpoint_routes
    scene=stage_scene()
    report=review_scene(scene,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,no_model),
                        preflight_dir=tmp_path/'routing-baseline')
    assert report['passed']
    raw=json.loads((tmp_path/'routing-baseline/report.json').read_text(encoding='utf-8'))
    for mode in ('anchor','implicit'):
        altered=copy.deepcopy(scene)
        arrow=next(n for n in altered['nodes'] if n['id']=='relation-1')
        if mode=='anchor': arrow['from']={'objectId':arrow['from']['objectId'],'anchorId':'focus'}
        else: arrow.pop('from');arrow.pop('to')
        before=copy.deepcopy(altered)
        assert propose_endpoint_routes({'scene':altered},['relation-1'],raw,raw['frames'])==[]
        assert altered==before
