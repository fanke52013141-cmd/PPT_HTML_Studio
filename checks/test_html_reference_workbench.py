import json
import pytest

from artifact_fingerprint import sha256_json
from checks.test_html_independent_review import inputs, locate
from checks.test_html_candidate_capacity_solver import document, ROOT
from checks.html_design_agent_fixture import with_coverage
from html_reference_localization import localize_reference
from html_reference_workbench import export_workbench, resume_review
from html_visual_review_service import HtmlReviewDependencies


def session(tmp_path):
    scene, ref, shot, report=inputs(tmp_path)
    base=document()
    scene.update({k:base[k] for k in ('id','themeRef','layoutRef','templateRef')})
    scene['nodes'][0]['slot']='headline'
    record=localize_reference(scene,ref,folder=tmp_path/'loc',run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,lambda **kw:locate(json.loads(kw['user_prompt']),'not_found')))
    folder=tmp_path/'workbench'
    export_workbench(scene,ref,shot,report,record,folder=folder,run_dir=tmp_path,repo_root=ROOT)
    correction=json.loads((folder/'correction.json').read_text(encoding='utf-8'))
    from html_reference_localization import mapped_reference_targets
    correction['mapping']=locate({'reference_targets':mapped_reference_targets(scene)})
    (folder/'correction.json').write_text(json.dumps(correction),encoding='utf-8')
    return scene,folder,correction


def test_manual_mapping_replays_only_fidelity_and_preserves_pending_approval(tmp_path):
    _,folder,_=session(tmp_path)
    calls=[]
    def generator(**kw):
        calls.append(kw)
        assert kw['artifact_prefix'].startswith('design_fidelity_review-')
        return with_coverage(json.loads(kw['user_prompt']),{'status':'pass','issues':[]})
    result=resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,generator))
    assert len(calls)==1 and result['human_approval']=='pending'
    assert result['reference_localization']['manual_correction']['visual_approval'] is False
    corrected = result['reference_localization']
    assert corrected['edge_report']['result_sha256'] == sha256_json(corrected['result'])
    assert corrected['edge_report']['regions'] == 1
    assert not (tmp_path/'planning/html_visual/scene-condensation.json').exists()
    html=(folder/'index.html').read_text(encoding='utf-8')
    assert 'data:image/png;base64,' in html and 'session_sha256' in html
    reused=resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,generator))
    assert reused['replay_receipt']['reused'] is True and len(calls)==1
    assert reused['replay_receipt']['dispatches_this_call']==0


def test_unknown_completion_and_changed_result_never_dispatch_again(tmp_path):
    _,folder,_=session(tmp_path)
    calls=[]
    def generator(**kw):
        calls.append(kw)
        raise TimeoutError('unknown transport completion')
    deps=HtmlReviewDependencies(ROOT,generator)
    with pytest.raises(TimeoutError):resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=deps)
    with pytest.raises(ValueError,match='ALREADY_SUBMITTED'):
        resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=deps)
    assert len(calls)==1


def test_offline_and_configured_transport_have_separate_receipts(tmp_path):
    _,folder,_=session(tmp_path)
    calls=[]
    def generator(**kw):
        calls.append(kw)
        return with_coverage(json.loads(kw['user_prompt']),{'status':'pass','issues':[]})
    deps=HtmlReviewDependencies(ROOT,generator)
    offline=resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=deps,
        execution_mode='offline_supplied_response',execution_identity='a'*64)
    assert offline['execution_mode']=='offline_supplied_response'
    live=resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=deps)
    assert live['execution_mode']=='configured_transport' and len(calls)==2
    path=next(p for p in (folder/'replays').glob('*/completed.json')
              if json.loads(p.read_text(encoding='utf-8'))['execution_mode']=='configured_transport')
    path.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='EVIDENCE_INVALID'):
        resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=deps)
    assert len(calls)==2


def test_changes_during_dispatch_are_rejected_and_not_retried(tmp_path):
    _,folder,_=session(tmp_path)
    calls=[]
    def generator(**kw):
        calls.append(kw)
        (folder/'correction.json').write_text('{}')
        return with_coverage(json.loads(kw['user_prompt']),{'status':'pass','issues':[]})
    with pytest.raises(ValueError,match='SOURCE_STALE'):
        resume_review(folder,folder/'correction.json',run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,generator))
    assert len(calls)==1


@pytest.mark.parametrize('change',['reference','author','transcript','identity','session'])
def test_stale_or_invalid_mapping_never_calls_provider(tmp_path,change):
    scene,folder,correction=session(tmp_path)
    if change=='reference': (tmp_path/'reference.png').write_bytes(b'changed')
    elif change=='author':
        from html_scene_editing import edit_path
        path=edit_path(tmp_path,scene['id']);path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
    elif change=='transcript': correction['mapping']['targets'][0]['part_regions'][0]['regions'][0]['text']='wrong'
    elif change=='identity': correction['mapping']['targets'][0]['targetId']='unknown'
    else: correction['session_sha256']=sha256_json({})
    (folder/'correction.json').write_text(json.dumps(correction),encoding='utf-8')
    with pytest.raises((ValueError,OSError)):
        resume_review(folder,folder/'correction.json',run_dir=tmp_path,
                      deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('No provider on invalid evidence')))
