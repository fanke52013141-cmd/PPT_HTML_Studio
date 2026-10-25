import copy
import json
import pytest
from checks.test_html_paired_evaluation import pair_fixture
from html_annotation_store import directory,case_view,save_labels,review_labels,sealed_dataset


def dataset_fixture(run):
    folder=directory(run,'labels');folder.mkdir(parents=True)
    data,_=pair_fixture(folder)
    (folder/'dataset.json').write_text(json.dumps(data),encoding='utf-8')
    return folder,data


def annotate(run,case='page-0'):
    packet=case_view(run,'labels',case);mapping=copy.deepcopy(packet['state']['mapping'])
    mapping['targets'][0]['identity_evidence']='Checked directly against the reference image'
    state=save_labels(run,{'dataset_id':'labels','case_id':case,'expected_revision':packet['state']['revision'],
        'source_sha256':packet['state']['source_sha256'],'annotator':'Alice','mapping':mapping})
    return review_labels(run,{'dataset_id':'labels','case_id':case,'expected_revision':state['revision'],
        'source_sha256':state['source_sha256'],'reviewer':'Bob','decision':'accept','note':'逐字核对原图及完整定位边界。'})


def reviewed_fixture(run):
    dataset_fixture(run)
    for case in ('page-0','page-1'):annotate(run,case)
    return sealed_dataset(run,'labels')


def test_annotation_revision_independent_review_and_immutable_gold(tmp_path):
    folder,_=dataset_fixture(tmp_path)
    before=case_view(tmp_path,'labels','page-0');source=before['reference'].read_bytes()
    state=annotate(tmp_path)
    assert state['revision']==2 and state['status']=='reviewed'
    assert case_view(tmp_path,'labels','page-1')['state']['revision']==0
    assert before['reference'].read_bytes()==source
    assert (folder/'annotations/page-0/annotation-versions/1.json').exists()
    gold=next((folder/'annotations/page-0/annotation-versions').glob('gold-*.json'));bytes_before=gold.read_bytes()
    packet=case_view(tmp_path,'labels','page-0')
    save_labels(tmp_path,{'dataset_id':'labels','case_id':'page-0','expected_revision':2,'source_sha256':state['source_sha256'],
        'annotator':'Alice','mapping':packet['state']['mapping']})
    assert gold.read_bytes()==bytes_before
    with pytest.raises(ValueError,match='UNREVIEWED'):sealed_dataset(tmp_path,'labels')


def test_same_reviewer_stale_save_and_outside_boxes_are_rejected(tmp_path):
    dataset_fixture(tmp_path);packet=case_view(tmp_path,'labels','page-0')
    body={'dataset_id':'labels','case_id':'page-0','expected_revision':0,'source_sha256':packet['state']['source_sha256'],
        'annotator':'Alice','mapping':packet['state']['mapping']}
    state=save_labels(tmp_path,body)
    with pytest.raises(ValueError,match='CONFLICT'):save_labels(tmp_path,body)
    with pytest.raises(ValueError,match='INDEPENDENT_REVIEWER'):
        review_labels(tmp_path,{'dataset_id':'labels','case_id':'page-0','expected_revision':1,'source_sha256':state['source_sha256'],
            'reviewer':'alice','decision':'accept','note':'审核者不可与标注者相同。'})
    body['expected_revision']=1;body['mapping']['targets'][0]['part_regions'][0]['regions'][0]['box']['widthPx']=200
    with pytest.raises(ValueError,match='OUT_OF_BOUNDS'):save_labels(tmp_path,body)


def test_sealed_dataset_requires_each_case_and_original_hashes(tmp_path):
    folder,_=reviewed_fixture(tmp_path)
    assert sealed_dataset(tmp_path,'labels')[1]['cases']
    (folder/'page-0.png').write_bytes(b'tampered')
    with pytest.raises(ValueError,match='HASH_CHANGED'):case_view(tmp_path,'labels','page-0')


def test_annotation_rejection_retains_draft_history(tmp_path):
    dataset_fixture(tmp_path);packet=case_view(tmp_path,'labels','page-0')
    state=save_labels(tmp_path,{'dataset_id':'labels','case_id':'page-0','expected_revision':0,'source_sha256':packet['state']['source_sha256'],
        'annotator':'Alice','mapping':packet['state']['mapping']})
    rejected=review_labels(tmp_path,{'dataset_id':'labels','case_id':'page-0','expected_revision':1,'source_sha256':state['source_sha256'],
        'reviewer':'Bob','decision':'reject','note':'文字边界需要重新核对修改。'})
    assert rejected['status']=='changes_requested' and rejected['review']['draft_revision']==1
