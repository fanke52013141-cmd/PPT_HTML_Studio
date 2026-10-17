"""Benchmark controls must reject the actual dispersed-number failure."""
import copy
from pathlib import Path

import pytest

from html_reference_localization import mapped_reference_targets,validate_mapped_locations
from scripts.evaluate_html_reference_layouts import build_cases,score


@pytest.fixture
def cases(tmp_path):
    if not Path('C:/Windows/Fonts/msyh.ttc').is_file():pytest.skip('Windows Chinese benchmark font unavailable')
    return build_cases(tmp_path)


def box(rect):
    return dict(xPx=rect[0],yPx=rect[1],widthPx=rect[2]-rect[0],heightPx=rect[3]-rect[1])


def oracle(case):
    """Scorer calibration only, never submitted as a model response in live runs."""
    gold=case['gold'];targets=mapped_reference_targets(case['scene']);rows=[]
    for target in targets:
        missing=target['targetId']==gold['missing']
        rows.append({'targetId':target['targetId'],'status':'not_found' if missing else 'located',
            'identity_evidence':None if missing else 'scorer calibration',
            'container_presence':'present' if not missing and gold['container'] else 'absent',
            'container_box':box(gold['container']) if not missing and gold['container'] else None,
            'part_regions':[{'partId':p['partId'],'status':'not_found' if missing else 'located',
                'regions':[] if missing else [{'text':p['text'] if len(gold['parts'][p['partId']])==1 else
                    ('第一行正文' if index==0 else '第二行正文'),'box':box(rect)}
                    for index,rect in enumerate(gold['parts'][p['partId']])]} for p in target['text_parts']]})
    return validate_mapped_locations({'targets':rows},targets,gold['image_size'])


def test_all_four_layout_oracles_and_missing_controls_pass(cases):
    assert len(cases)==4
    for case in cases:
        checked=score(oracle(case),case['gold'])
        assert checked['joint_pass'] and all(checked['part_geometry'].values())


def test_header_transcript_with_missing_numeral_box_fails_shared_metric(cases):
    case=cases[0];raw=oracle(case);target=raw['targets'][0]
    target['text_boxes']=target['text_boxes'][1:]
    target.pop('part_regions') # Historical baseline has no part correspondence.
    checked=score(raw,case['gold'])
    assert not checked['text_lines_pass'] and not checked['joint_pass']


def test_big_envelope_does_not_replace_two_separate_ink_lines(cases):
    case=cases[2];raw=oracle(case);target=raw['targets'][0]
    target['text_boxes']=[target['box']]
    checked=score(raw,case['gold'])
    assert checked['text_envelope_pass'] and not checked['text_lines_pass'] and not checked['joint_pass']


def test_swapping_part_regions_cannot_pass_identity_geometry(cases):
    case=cases[0];raw=oracle(case);parts=raw['targets'][0]['part_regions']
    parts[0]['regions'],parts[1]['regions']=copy.deepcopy(parts[1]['regions']),copy.deepcopy(parts[0]['regions'])
    checked=score(raw,case['gold'])
    assert checked['text_lines_pass'] and not checked['joint_pass']


def test_correct_body_does_not_compensate_for_missing_background(cases):
    case=cases[1];raw=oracle(case);target=raw['targets'][0]
    target.update(container_box=None,container_presence='absent')
    checked=score(raw,case['gold'])
    assert checked['text_lines_pass'] and not checked['container_pass'] and not checked['joint_pass']
