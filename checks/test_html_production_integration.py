"""Production consumes editor deltas and freezes asset cache provenance."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import html_production_service as production
import html_scene_editing as editor
import html_visual_store as store
from html_visual_review_service import HtmlReviewError

ROOT = Path(__file__).resolve().parents[1]


def prepare(tmp_path, monkeypatch):
    scene = json.loads((ROOT / 'html_engine/visual/scenes/condensation.json').read_text(encoding='utf-8'))
    store.save_scene(tmp_path, scene['id'], scene, 0)
    contract = {'slide_id': scene['id'], 'narration_beats': [{'id': 'b1'}]}
    folder = tmp_path / 'planning/html_visual'
    (tmp_path / 'planning/visual_contract.json').write_text(json.dumps({'slides': [contract]}))
    plan = {'templateRef': {'id': 'fixed'}, 'registered': {'catalog_sha256': 'reference'}, 'assets': []}
    monkeypatch.setattr(production, 'generate_scene_plan', lambda *a, **kw: copy.deepcopy(plan))
    monkeypatch.setattr(production, 'build_design_brief', lambda *a, **kw: {'asset_needs': []})
    monkeypatch.setattr(production, 'load_effect_registry', lambda *a: {})
    monkeypatch.setattr(production, 'required_keyframes', lambda *a: [{'id': 'final'}])
    monkeypatch.setattr(production, 'freeze_design', lambda *a, **kw: {'frozen': True})
    monkeypatch.setattr(production, 'compile_plan', lambda *a: (copy.deepcopy(scene), None))
    inspected = []
    def review(candidate, **kwargs):
        inspected.append(copy.deepcopy(candidate))
        editor.preview_editor(tmp_path, scene['id'], candidate, None)
        return {'passed': True}
    monkeypatch.setattr(production, 'review_scene', review)
    return scene, contract, folder, inspected, SimpleNamespace(repo_root=ROOT, json_generator=lambda *a, **kw: {})


def test_replanning_keeps_manual_title_and_private_anchor(tmp_path, monkeypatch):
    scene, contract, folder, inspected, deps = prepare(tmp_path, monkeypatch)
    changed = copy.deepcopy(scene)
    changed['nodes'][0]['title'] = '人工保留标题'
    image = next(n for n in changed['nodes'] if n['type'] == 'image')
    original_anchor = json.loads((ROOT / 'html_engine/visual/generated/catalog.json').read_text(encoding='utf-8'))['assets']
    asset = next(a for a in original_anchor if a['id'] == image['assetRef']['id'])
    # Use the real registered subject anchor and change its stable name.
    anchor = copy.deepcopy(asset['anchors'][0])
    anchor['id'] = 'manual-focus'
    image['anchorId'] = anchor['id']
    for annotation in changed['nodes']:
        if annotation['type'] == 'annotation' and annotation.get('targetId') == image['id']:
            annotation['anchorId'] = anchor['id']
    editor.save_editor(tmp_path, scene['id'], changed, None, 1,
                       {image['id']: [anchor]})
    edited = store.load_scene(tmp_path, scene['id'])
    result = production.produce_scene(contract, run_dir=tmp_path, deps=deps,
                                     model_summary={'image': {'config_hash': 'frozen-image'}})
    assert result['scene']['nodes'][0]['title'] == '人工保留标题'
    assert next(n for n in result['scene']['nodes'] if n['id'] == image['id'])['assetRef'] == next(n for n in edited['nodes'] if n['id'] == image['id'])['assetRef']
    assert inspected[-1] == result['scene']
    assert editor.edit_path(tmp_path, scene['id']).is_file()
    assert json.loads((folder / 'candidates/condensation/models.json').read_text())['image']['config_hash'] == 'frozen-image'


def test_replanning_conflict_preserves_current_scene(tmp_path, monkeypatch):
    scene, contract, folder, inspected, deps = prepare(tmp_path, monkeypatch)
    changed = copy.deepcopy(scene)
    changed['nodes'][0]['title'] = '人工标题'
    editor.save_editor(tmp_path, scene['id'], changed, None, 1)
    before = store.load_scene_with_revision(tmp_path, scene['id'])
    broken = copy.deepcopy(scene)
    broken['nodes'] = broken['nodes'][1:]
    monkeypatch.setattr(production, 'compile_plan', lambda *a: (broken, None))
    with pytest.raises(HtmlReviewError) as exc:
        production.produce_scene(contract, run_dir=tmp_path, deps=deps)
    assert exc.value.code == 'MANUAL_EDIT_CONFLICT'
    assert store.load_scene_with_revision(tmp_path, scene['id']) == before
    assert not inspected
    assert (folder / 'candidates/condensation/manual-conflicts.json').is_file()


def test_asset_model_change_invalidates_generation_cache(tmp_path):
    from html_asset_service import HtmlAssetDependencies, produce_asset
    from checks.test_html_asset_service import png_bytes
    calls = []
    def provider(*args, **kwargs):
        calls.append(1)
        return png_bytes()
    deps = HtmlAssetDependencies(provider, tmp_path)
    request = {'id': 'subject', 'role': '主体', 'need': '配图', 'prompt': 'fixture',
               'model_config_hash': 'model-one'}
    first = produce_asset(request, deps)
    assert produce_asset(request, deps)['cache'] == 'hit'
    second = produce_asset({**request, 'model_config_hash': 'model-two'}, deps)
    assert second['request_key'] != first['request_key']
    assert len(calls) == 2
