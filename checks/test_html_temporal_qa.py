"""S04 frozen output-frame coverage, immutable evidence and repair stagnation."""
import copy
import json
from pathlib import Path

import pytest

from html_build_snapshot import create_render_snapshot, json_bytes, digest
from html_visual_store import save_scene
from html_snapshot_review import review_snapshot
from html_quality_report import validate_quality_report
from html_repair_progress import RepairProgress

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def frozen(tmp_path):
    scene = json.loads((ROOT/'html_engine/visual/scenes/condensation.json').read_text(encoding='utf-8'))
    save_scene(tmp_path,scene['id'],scene,expected_revision=0)
    snapshot=create_render_snapshot(tmp_path,scene['id'],repo_root=ROOT,expected_revision=1)
    return tmp_path, scene, Path(snapshot['path'])


def test_all_output_frames_and_registered_exclusions_are_bound(frozen):
    run,scene,snapshot=frozen
    result=review_snapshot(snapshot,temporal={'sampling_mode':'output_frames','fps':30,'overlap_policy':'registered'})
    report=result['report']
    assert result['validation']['valid']
    assert report['checks']['engineering']=='passed', report['issues'][:4]
    assert report['scope']['coverage']['frame_complete']
    assert report['scope']['frame_count']>=541
    assert report['scope']['continuous_time_verified'] is False
    assert report['scope']['overlap_exclusions']
    assert all(item['source'] and item['reason'] for item in report['scope']['overlap_exclusions'])
    folder=Path(result['report_path']).parent
    shot=next(folder.glob('frame-*.png'))
    shot.write_bytes(b'changed')
    assert validate_quality_report(report,snapshot,evidence_dir=folder)['reason']=='evidence_changed'


def test_missing_frame_cannot_be_rehashed_into_a_pass(frozen):
    _,_,snapshot=frozen
    result=review_snapshot(snapshot,temporal={'sampling_mode':'output_frames','fps':30,'time_range_ms':[0,1000]})
    folder=Path(result['report_path']).parent
    raw_path=folder/'raw-report.json'
    raw=json.loads(raw_path.read_text(encoding='utf-8'))
    raw['frames'].pop(2)
    raw_path.write_bytes(json_bytes(raw))
    report=copy.deepcopy(result['report'])
    report['scope']['frame_count']-=1
    for entry in report['evidence']:
        if entry['path']=='raw-report.json':entry['sha256']=digest(raw_path.read_bytes())
    report.pop('report_digest')
    report['report_digest']=digest(json_bytes(report))
    assert not validate_quality_report(report,snapshot,evidence_dir=folder)['valid']


def test_request_must_be_in_hashed_evidence(frozen):
    _, _, snapshot = frozen
    result = review_snapshot(snapshot, temporal={'time_range_ms': [0, 500]})
    report = copy.deepcopy(result['report'])
    report['evidence'] = [entry for entry in report['evidence'] if entry['path'] != 'temporal-request.json']
    report.pop('report_digest')
    report['report_digest'] = digest(json_bytes(report))
    assert validate_quality_report(report, snapshot, evidence_dir=Path(result['report_path']).parent)['reason'] == 'evidence_missing'


def test_dynamic_report_cannot_be_downgraded_to_static_with_an_added_end_frame(frozen):
    _, _, snapshot = frozen
    result = review_snapshot(snapshot, temporal={'time_range_ms': [0, 500]})
    folder = Path(result['report_path']).parent
    frame = next(folder.glob('frame-*.png'))
    end_frame = folder / 'end-frame.png'
    end_frame.write_bytes(frame.read_bytes())
    report = copy.deepcopy(result['report'])
    report['scope']['kind'] = 'static_end_frame'
    report['evidence'].append({'path': end_frame.name, 'sha256': digest(end_frame.read_bytes())})
    report.pop('report_digest')
    report['report_digest'] = digest(json_bytes(report))
    assert validate_quality_report(report, snapshot, evidence_dir=folder)['reason'] == 'scope_changed'


def test_static_report_cannot_claim_pass_after_raw_failure(frozen):
    _, _, snapshot = frozen
    result = review_snapshot(snapshot)
    folder = Path(result['report_path']).parent
    raw_path = folder / 'raw-report.json'
    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    raw['passed'] = False
    raw_path.write_bytes(json_bytes(raw))
    report = copy.deepcopy(result['report'])
    for entry in report['evidence']:
        if entry['path'] == raw_path.name: entry['sha256'] = digest(raw_path.read_bytes())
    report.pop('report_digest')
    report['report_digest'] = digest(json_bytes(report))
    assert validate_quality_report(report, snapshot, evidence_dir=folder)['reason'] == 'raw_check_failed'


def test_progress_allows_improvement_but_stops_cycles_and_identical_measurements():
    tracker=RepairProgress()
    def report(width):return {'capacityIssues':[{'code':'CONTENT_CAPACITY_EXCEEDED','target':'title','measured':{'width':width},'available':{'width':100}}]}
    assert tracker.observe({'size':80},None,report(200)) is None
    assert tracker.observe({'size':70},None,report(150)) is None
    assert tracker.observe({'size':60},None,report(150))=='unchanged_measurements'
    assert tracker.observe({'size':80},None,report(200))=='repeated_candidate'
    operations=[{'kind':'set_text_style','values':{'fontSizePx':60}}]
    assert tracker.check_operations(operations) is None
    assert tracker.check_operations(operations)=='repeated_patch'


@pytest.mark.parametrize('change',['range','action_boundary','pairs','clock'])
def test_consistent_raw_omission_still_must_match_frozen_request(frozen,change):
    _,_,snapshot=frozen
    result=review_snapshot(snapshot,temporal={'sampling_mode':'output_frames','fps':30,'time_range_ms':[0,1000],'overlap_policy':'registered'})
    folder=Path(result['report_path']).parent
    raw_path=folder/'raw-report.json';raw=json.loads(raw_path.read_text(encoding='utf-8'))
    if change=='range':
        raw['coverage']['rangeMs']=[0,500];raw['rangeMs']=[0,500]
        raw['frames']=[f for f in raw['frames'] if f['timeMs']<=500]
        raw['coverage']['times']=[f['timeMs'] for f in raw['frames']]
    elif change=='action_boundary':
        raw['frames']=[f for f in raw['frames'] if f['timeMs']!=350]
        raw['coverage']['times']=[f['timeMs'] for f in raw['frames']]
    elif change=='pairs':raw['overlapPairs']=[]
    else:raw['clock']='confirmed_audio_inputs'
    raw_path.write_bytes(json_bytes(raw));report=copy.deepcopy(result['report'])
    report['scope'].update(coverage={k:v for k,v in raw['coverage'].items() if k!='times'},frame_count=len(raw['frames']),clock=raw['clock'])
    for entry in report['evidence']:
        if entry['path']=='raw-report.json':entry['sha256']=digest(raw_path.read_bytes())
    report.pop('report_digest');report['report_digest']=digest(json_bytes(report))
    assert not validate_quality_report(report,snapshot,evidence_dir=folder)['valid']


def test_real_candidate_noop_stops_before_spending_full_budget(tmp_path):
    from html_candidate_agent import repair_candidate
    from html_visual_review_service import HtmlReviewDependencies,HtmlReviewError
    scene=json.loads((ROOT/'html_engine/visual/scenes/condensation.json').read_text(encoding='utf-8'))
    scene['version']='0.5.0'
    scene['nodes'][1]['presentation']={'typography':{'text':{'fontSizePx':80}}}
    planning=tmp_path/'planning';planning.mkdir()
    (planning/'visual_contract.json').write_bytes(json_bytes({'slides':[{'slide_id':scene['id'],'narration_beats':[]}]}))
    calls=[]
    def model(**_):
        calls.append(1)
        return {'action':'patch','operations':[{'targetId':'headline','kind':'set_text_style','part':'text','values':{'fontSizePx':80}}]}
    with pytest.raises(HtmlReviewError):repair_candidate(scene,None,run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,model))
    assert len(calls)==1
    summary=json.loads(next((planning/'html_visual/candidates').rglob('result.json')).read_text(encoding='utf-8'))
    assert summary['status']=='needs_revision' and summary['stop_reason']=='repeated_candidate'
    assert not list((planning/'html_visual').glob('scene-*.json'))
