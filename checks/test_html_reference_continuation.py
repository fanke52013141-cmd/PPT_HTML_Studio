import copy
import json
from PIL import Image
import pytest
from artifact_fingerprint import sha256_json
from checks.test_html_candidate_capacity_solver import document,ROOT
from checks.html_design_agent_fixture import response_for
from html_visual_review_service import HtmlReviewDependencies,review_scene
from html_reference_localization import localize_reference
from html_reference_workbench import export_workbench
from html_design_agent import review_fidelity
from html_reference_publication import publish,restore,load


def test_review_checkpoint_restores_only_registered_static_changes_and_full_rechecks(tmp_path):
    scene=document();target=copy.deepcopy(scene);target['nodes'][0]['presentation']={'height':100}
    ref=tmp_path/'reference.png';Image.new('RGB',(1280,720),'white').save(ref)
    deps=HtmlReviewDependencies(ROOT,lambda **kw:response_for(kw))
    report=review_scene(target,run_dir=tmp_path,deps=deps,preflight_dir=tmp_path/'before')
    assert report['passed'],report
    localization=localize_reference(target,ref,folder=tmp_path/'locator',run_dir=tmp_path,deps=deps,
        target_ids=[n['id'] for n in target['nodes'] if n['type'] in ('text','header','card','summary','label','badge')])
    folder=tmp_path/'workbench'
    export_workbench(target,ref,tmp_path/report['screenshot'],report,localization,folder=folder,run_dir=tmp_path,repo_root=ROOT)
    review=review_fidelity(target,ref,tmp_path/report['screenshot'],report,None,folder=tmp_path/'fidelity',
        run_dir=tmp_path,deps=deps,localized_reference=True,localization_override=localization)
    session=json.loads((folder/'session.json').read_text(encoding='utf-8'))
    key=publish({'folder':folder,'session':session},{**review,'execution_mode':'configured_transport'},tmp_path)
    assert load(tmp_path,key,ROOT)['human_approval']=='pending'
    audit=tmp_path/'restore';audit.mkdir()
    proposed,checked,_=restore(scene,None,key,ref,run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('no new model request')),manual=None,beats=None,audit=audit)
    assert proposed==target and checked['geometry_preflight']['passed']
    assert not (tmp_path/'planning/html_visual/scene-condensation.json').exists()
    damaged=copy.deepcopy(scene);damaged['nodes'][0]['title']='changed'
    with pytest.raises(ValueError,match='CANDIDATE_MISMATCH'):
        restore(damaged,None,key,ref,run_dir=tmp_path,deps=deps,manual=None,beats=None,audit=audit)
    assert sha256_json(scene)!=sha256_json(target)
