import pytest
from scripts.package_annotation_truth import merge_labels


def test_human_merge_retains_predictions_and_binds_audio():
    source = [{'sample_id':'a1', 'audio_sha256':'abc', 'predicted_start_sec':2.0, 'reliable':True}]
    labels = [{'sample_id':'a1', 'truth_audio_sha256':'abc', 'truth_source':'human', 'reviewer':'reviewer1', 'truth_start_sec':2.1}]
    merged = merge_labels(source, labels)
    assert merged[0]['predicted_start_sec'] == 2.0
    assert merged[0]['truth_start_sec'] == 2.1
    assert 'truth_start_sec' not in source[0]
    labels[0]['truth_audio_sha256'] = 'changed'
    with pytest.raises(ValueError, match='hash'):
        merge_labels(source, labels)


def test_human_merge_rejects_unknown_duplicate_and_unattributed_labels():
    source = [{'sample_id':'a1', 'audio_sha256':'abc'}]
    label = {'sample_id':'a1','truth_audio_sha256':'abc','truth_source':'human','reviewer':'r','truth_start_sec':1}
    with pytest.raises(ValueError, match='duplicate'):
        merge_labels(source, [label, label])
    with pytest.raises(ValueError, match='unknown'):
        merge_labels(source, [{**label,'sample_id':'other'}])
    with pytest.raises(ValueError, match='reviewer'):
        merge_labels(source, [{**label,'reviewer':''}])


def test_out_of_audio_truth_cannot_pass_evaluation():
    from scripts.evaluate_annotation_alignment import evaluate
    row = {'sample_id':'a1','category':'test','truth_start_sec':5,'duration_sec':3,
           'truth_source':'human','audio_sha256':'abc','truth_audio_sha256':'abc',
           'predicted_start_sec':5,'reliable':True}
    with pytest.raises(ValueError, match='outside'):
        evaluate([row])
