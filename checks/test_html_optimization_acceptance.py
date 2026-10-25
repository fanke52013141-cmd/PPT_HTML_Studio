import json
import pytest

from artifact_fingerprint import sha256_file
from pipeline_lifecycle import write_json_atomic
from scripts.verify_reconstruction_v2_acceptance import validate_bundle, junit_passed, GATES, EXPECTED_CASES


def bundle(tmp_path):
    repo=tmp_path/'repo'; repo.mkdir(); (repo/'source.py').write_text('source')
    root=tmp_path/'evidence';root.mkdir()
    (root/'tests.xml').write_text('<testsuites><testsuite><testcase name="tested"/></testsuite></testsuites>')
    for name in ('capacity','linked'):
        write_json_atomic(root/name/'summary.json',{'passed':True,'provenance':'controlled_fixture',
            'cases':[{'case':case,'passed':True,'actual_status':status} for case,status in EXPECTED_CASES[name].items()]})
        for case,status in EXPECTED_CASES[name].items():
            if status in ('candidate','unchanged'):
                write_json_atomic(root/name/case/'report.json',{'passed':True,'issues':[],
                    'coverage':{'frame_complete':True,'mode':'output_frames','fps':30,'rangeMs':[0,1],'times':[0,1]},
                    'frames':[{'timeMs':0},{'timeMs':1}]})
    manifest={'format':'hps.optimization7.acceptance/0.1.0',
        'sources':{'source.py':sha256_file(repo/'source.py')},
        'gates':{k:{'status':'passed','junit':'tests.xml','provenance':'offline_engineering_tests'} for k in GATES},
        'real_model_quality':'not_run','human_visual_acceptance':'pending',
        'files':{p.relative_to(root).as_posix():sha256_file(p) for p in root.rglob('*') if p.is_file()}}
    write_json_atomic(root/'manifest.json',manifest)
    return root,repo,manifest


@pytest.mark.parametrize('change',['none','missing','source','skip','gate','path','mock','temporal','cases'])
def test_verifier_rejects_missing_stale_skipped_or_mock_evidence(tmp_path,change):
    root,repo,manifest=bundle(tmp_path)
    if change=='missing':(root/'tests.xml').unlink()
    elif change=='source':(repo/'source.py').write_text('changed')
    elif change=='skip':
        (root/'tests.xml').write_text('<testsuite><testcase><skipped/></testcase></testsuite>')
        manifest['files']['tests.xml']=sha256_file(root/'tests.xml')
    elif change=='gate':manifest['gates'].pop('O7-01')
    elif change=='path':manifest['files']['../outside']='bad'
    elif change=='mock':manifest['gates']['O7-01']['provenance']='mock_real_model_pass'
    elif change=='temporal':
        path=root/'capacity/normal/report.json';path.unlink();manifest['files'].pop(path.relative_to(root).as_posix())
    elif change=='cases':
        path=root/'capacity/summary.json';summary=json.loads(path.read_text(encoding='utf-8'))
        summary['cases']=summary['cases'][-1:];write_json_atomic(path,summary)
        manifest['files']['capacity/summary.json']=sha256_file(path)
    write_json_atomic(root/'manifest.json',manifest)
    assert validate_bundle(root,repo)['passed'] is (change=='none')


def test_empty_or_skipped_test_suites_do_not_pass(tmp_path):
    path=tmp_path/'empty.xml';path.write_text('<testsuite tests="0"/>')
    assert junit_passed(path) is False
