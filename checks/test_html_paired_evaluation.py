"""Scoring mechanics use controlled labels, never real-model quality claims."""
import copy
import json
from pathlib import Path
import pytest
from artifact_fingerprint import sha256_file,sha256_json
from html_paired_evaluation import compare


def pair_fixture(root):
    from PIL import Image
    def save(name,value):
        path=root/name;path.write_text(json.dumps(value),encoding='utf-8')
        return {'path':name,'sha256':sha256_file(path)}
    cases=[];trials=[]
    for i,split in enumerate(('development','holdout')):
        name=f'page-{i}';ref=root/(name+'.png');Image.new('RGB',(100,60),('white','gray')[i]).save(ref)
        reference={'path':ref.name,'sha256':sha256_file(ref)}
        scene=save(name+'-scene.json',{'nodes':[{'id':'title','type':'text','text':'alpha'}]})
        gold=save(name+'-gold.json',{'label_version':'human-layout/1','authority':'controlled_fixture',
            'reference_sha256':reference['sha256'],'targets':{'title':{'status':'located','container':None,
                'parts':{'text':[{'text':'alpha','box':[10,10,50,25]}]}}}})
        response=save(name+'-response.json',{'targets':[{'targetId':'title','status':'located',
            'container_presence':'absent','container_box':None,'identity_evidence':'controlled fixture',
            'part_regions':[{'partId':'text','status':'located','regions':[{'text':'alpha','box':{
                'xPx':10,'yPx':10,'widthPx':40,'heightPx':15}}]}]}]})
        cases.append({'id':name,'course_id':'course-'+str(i),'split':split,'reference':reference,'scene':scene,'gold':gold})
        for arm in ('before','after'):
            trials.append({'case_id':name,'repetition':0,'arm':arm,'state':'returned','seconds':1,
                'response':response,'claimed_pass':True})
    dataset={'format':'hps.paired-dataset/0.1.0','label_version':'human-layout/1','provenance':'controlled_fixture','cases':cases}
    trialset={'dataset_sha256':sha256_json(dataset),'repetitions':1,'arms':['before','after'],'trials':trials}
    return dataset,trialset


def test_pair_denominators_and_holdout_are_separate(tmp_path):
    dataset,trials=pair_fixture(tmp_path)
    result=compare(dataset,trials,tmp_path)
    assert result['summary']['holdout']['after']['localization_correct']==1
    assert result['summary']['development']['before']['expected']==1
    with pytest.raises(ValueError,match='DENOMINATOR'):
        compare(dataset,{**trials,'trials':trials['trials'][:-1]},tmp_path)
    broken=copy.deepcopy(dataset);broken['cases'][1]['course_id']='course-0'
    with pytest.raises(ValueError,match='SPLIT_LEAKAGE'):compare(broken,{**trials,'dataset_sha256':sha256_json(broken)},tmp_path)
    broken=copy.deepcopy(dataset);broken['cases'][1]['reference']=broken['cases'][0]['reference']
    with pytest.raises(ValueError,match='LEAKAGE'):compare(broken,{**trials,'dataset_sha256':sha256_json(broken)},tmp_path)


def test_failed_and_unknown_are_in_denominator_and_unknown_cost_is_null(tmp_path):
    dataset,trials=pair_fixture(tmp_path)
    trials['trials'][0]['state']='unknown';trials['trials'][1]['state']='failed'
    result=compare(dataset,trials,tmp_path)
    assert result['summary']['development']['before']['unknown']==1
    assert result['summary']['development']['before']['localization_expected']==1
    assert result['summary']['development']['after']['failed']==1
    assert result['summary']['holdout']['after']['total_cost'] is None


@pytest.mark.parametrize('file',['scene','gold','reference','response'])
def test_tampered_source_or_gold_or_response_rejected(tmp_path,file):
    dataset,trials=pair_fixture(tmp_path)
    item=trials['trials'][0][file] if file=='response' else dataset['cases'][0][file]
    (tmp_path/item['path']).write_bytes(b'damaged')
    with pytest.raises(ValueError,match='HASH_CHANGED'):compare(dataset,trials,tmp_path)


def test_external_pass_claims_cannot_create_human_or_model_acceptance(tmp_path):
    dataset,trials=pair_fixture(tmp_path)
    for row in trials['trials']:row.update(human_approved=True,quality='passed',cost=0)
    result=compare(dataset,trials,tmp_path)
    assert result['real_model_quality']=='not_certified' and result['human_visual_approval']=='pending'
    assert all(r['fidelity']=='pending_independent_review' and r['cost'] is None for r in result['rows'])


def test_text_and_region_precision_are_scored_not_external_pass(tmp_path):
    dataset,trials=pair_fixture(tmp_path)
    item=trials['trials'][1]['response'];path=tmp_path/item['path'];value=json.loads(path.read_text())
    value['targets'][0]['part_regions'][0]['regions'][0]['text']='wrong'
    path.write_text(json.dumps(value));item['sha256']=sha256_file(path)
    result=compare(dataset,trials,tmp_path)
    assert result['summary']['development']['after']['localization_correct']==0


def test_repository_dataset_has_sealed_distinct_course_splits():
    from html_paired_evaluation import validate_dataset,read
    root=Path(__file__).resolve().parents[1]/'checks/fixtures/reconstruction-pairs'
    cases=validate_dataset(read(root/'dataset.json'),root)
    assert len(cases)==4 and {c['split'] for c in cases}=={'development','holdout'}


def test_pixel_difference_and_engineering_are_separate_from_visual_approval(tmp_path):
    dataset,trials=pair_fixture(tmp_path)
    row=trials['trials'][0];row['screenshot']=dataset['cases'][0]['reference']
    result=compare(dataset,trials,tmp_path)
    assert result['rows'][0]['reference_pixel_distance']['normalized_mae']==0
    assert result['rows'][0]['fidelity']=='pending_independent_review'
    assert result['summary']['development']['before']['pixel_comparison_measured']==1


def test_sample_preparation_preserves_bytes_and_drafts_cannot_be_scored(tmp_path):
    from scripts.prepare_reconstruction_dataset import prepare
    from html_paired_evaluation import validate_dataset
    source=tmp_path/'source';source.mkdir();dataset,_=pair_fixture(source)
    spec={'label_version':'new-labels/1','cases':[{k:c[k] for k in ('id','course_id','split')}|
        {'reference':c['reference']['path'],'scene':c['scene']['path']} for c in dataset['cases']]}
    output=tmp_path/'sealed';prepared=prepare(spec,source,output)
    assert (output/'page-0/reference.png').read_bytes()==(source/'page-0.png').read_bytes()
    with pytest.raises(ValueError,match='AUTHORITY'):validate_dataset(prepared,output)
    with pytest.raises(ValueError,match='ALREADY_EXISTS'):prepare(spec,source,output)


def test_invalid_model_response_remains_a_failed_pair_member(tmp_path):
    dataset,trials=pair_fixture(tmp_path)
    item=trials['trials'][0]['response'];path=tmp_path/item['path'];path.write_text('{"targets":[]}')
    item['sha256']=sha256_file(path)
    result=compare(dataset,trials,tmp_path)
    assert result['summary']['development']['before']['expected']==1
    assert result['summary']['development']['before']['failed']==1
    assert result['rows'][0]['failure_reason']=='invalid_localization_response'
