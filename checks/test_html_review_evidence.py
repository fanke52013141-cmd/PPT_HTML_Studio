"""Local comparison provenance, coverage and strict adapter budgets."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from html_review_evidence import comparison_evidence
from html_design_agent import review_fidelity
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from checks.html_design_agent_fixture import with_coverage

ROOT = Path(__file__).resolve().parents[1]


def inputs(tmp_path, count=6):
    reference, screenshot = tmp_path/'reference.png', tmp_path/'shot.png'
    Image.new('RGB', (1280, 720), 'white').save(reference)
    Image.new('RGB', (1600, 900), 'white').save(screenshot)
    scene = {'version':'0.7.0', 'nodes':[{'id':f'n{i}','type':'text','slot':'caption','runs':[{'text':'test','emphasis':False}], 'role':'source'} for i in range(count)]}
    report = {'geometry':{n['id']:{'box':{'x':100,'y':100,'width':800,'height':120}} for n in scene['nodes']}}
    return scene, reference, screenshot, report


@pytest.mark.parametrize('count', [1, 6, 40])
def test_all_objects_mapped_within_four_image_and_pixel_budget(tmp_path, count):
    scene, ref, shot, report = inputs(tmp_path, count)
    manifest, paths = comparison_evidence(scene, ref, shot, report, folder=tmp_path/'evidence')
    assert len(paths) <= 2 and len(manifest['targets']) == count
    assert manifest['status'] == 'complete_windows'
    assert len({(e['image_index'],e['row']) for e in manifest['targets']}) == count
    for path in paths:
        with Image.open(path) as im:
            assert im.format == 'PNG' and im.width*im.height < 4_000_000
        assert path.stat().st_size <= 8*1024*1024
    assert manifest['reference_localization'] == 'unverified_same_coordinate_window'
    target = manifest['targets'][0]
    assert target['current_pixels'] != target['reference_pixels']
    assert json.loads((tmp_path/'evidence/manifest.json').read_text()) == manifest


@pytest.mark.parametrize('damage', ['missing','negative','nan','boolean','offscreen','aspect'])
def test_missing_or_invalid_geometry_is_explicit_never_invented(tmp_path, damage):
    scene, ref, shot, report = inputs(tmp_path, 1)
    box = report['geometry']['n0']['box']
    if damage == 'missing':report = {}
    if damage == 'negative':box['width'] = -1
    if damage == 'nan':box['x'] = float('nan')
    if damage == 'boolean':box['x'] = True
    if damage == 'offscreen':box['x'] = 1700
    if damage == 'aspect':Image.new('RGB', (720,1280), 'white').save(ref)
    manifest, paths = comparison_evidence(scene, ref, shot, report, folder=tmp_path/'evidence')
    assert not paths and manifest['status'] == 'partial_windows'
    assert manifest['targets'][0]['status'] == 'unavailable'


def test_review_passes_actual_sheets_to_existing_adapter_once(tmp_path):
    scene, ref, shot, report = inputs(tmp_path)
    calls = []
    def generator(**kwargs):
        calls.append(kwargs)
        payload = json.loads(kwargs['user_prompt'])
        assert len(kwargs['image_paths']) == 4
        assert payload['local_comparisons']['status'] == 'complete_windows'
        assert all(Path(p).is_file() for p in kwargs['image_paths'])
        return with_coverage(payload, {'status':'pass','issues':[]})
    result = review_fidelity(scene,ref,shot,report,None,folder=tmp_path/'review',run_dir=tmp_path,
                             deps=HtmlReviewDependencies(ROOT,generator),local_comparisons=True)
    assert len(calls) == 1 and result['coverage_check']['expected'] == 24
    request = json.loads((tmp_path/'review/request.json').read_text(encoding='utf-8'))
    assert len(request['image_sha256']) == 4
    assert result['local_evidence']['reference_sha256'] == result['design_sha256']


def test_escaping_evidence_folder_stops_before_io_or_model(tmp_path):
    scene, ref, shot, report = inputs(tmp_path)
    with pytest.raises(HtmlReviewError) as error:
        review_fidelity(scene,ref,shot,report,None,folder=tmp_path.parent/'outside',run_dir=tmp_path,
            deps=HtmlReviewDependencies(ROOT,lambda **kw:pytest.fail('unexpected model request')))
    assert error.value.code == 'DESIGN_AGENT_IMAGE_INVALID'


def test_changed_reference_and_scene_change_provenance(tmp_path):
    scene, ref, shot, report = inputs(tmp_path)
    first,_ = comparison_evidence(scene,ref,shot,report,folder=tmp_path/'first')
    changed = copy.deepcopy(scene);changed['nodes'][0]['runs'][0]['text']='new'
    Image.new('RGB',(1280,720),'black').save(ref)
    second,_ = comparison_evidence(changed,ref,shot,report,folder=tmp_path/'second')
    assert first['scene_sha256'] != second['scene_sha256']
    assert first['reference_sha256'] != second['reference_sha256']
    assert first['sheets'][0]['sha256'] != second['sheets'][0]['sha256']


def test_local_comparison_experiment_is_not_default_production_policy(tmp_path):
    scene, ref, shot, report = inputs(tmp_path)
    def generator(**kwargs):
        payload=json.loads(kwargs['user_prompt'])
        assert len(kwargs['image_paths'])==2 and 'local_comparisons' not in payload
        assert 'design-fidelity-review/1.0.0' in kwargs['system_prompt']
        return with_coverage(payload,{'status':'pass','issues':[]})
    result=review_fidelity(scene,ref,shot,report,None,folder=tmp_path/'review',run_dir=tmp_path,
                          deps=HtmlReviewDependencies(ROOT,generator))
    assert result['local_evidence'] is None
    assert not (tmp_path/'review/local-evidence').exists()
