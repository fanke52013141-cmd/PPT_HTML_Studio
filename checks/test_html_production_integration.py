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
from html_storyboard_planning import load_template_catalog

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


@pytest.fixture
def annotation_alias_plan():
    return {
        "slide_id": "token-test",
        "templateRef": {"id": "explanation-cards-v1", "version": "0.1.0"},
        "layoutRef": {"id": "science-explanation-v1", "version": "0.2.0"},
        "slots": {
            "subject": {"kind": "image", "assetRef": {"id": "subject-art", "version": "0.1.0"}, "anchorId": "focus"},
            "anchor-label": {"kind": "text", "runs": [{"text": "主体焦点", "emphasis": False}]},
            "annotation": {"kind": "annotation", "targetId": "subject-art", "anchorId": "focus", "radius": 18, "labelId": "anchor-label"},
        },
        "objects": [
            {"id": "subject-node", "slot": "subject", "kind": "image"},
            {"id": "anchor-label-node", "slot": "anchor-label", "kind": "text"},
            {"id": "annotation-node", "slot": "annotation", "kind": "annotation"},
        ],
        "beats": [{"id": "beat-1", "narration_only": True}],
        "assets": [{"id": "subject-art", "role": "subject", "render_owner": "image_asset", "need": "主体插画", "slot": "subject"}],
    }


def test_compile_resolves_explicit_annotation_asset_and_slot_aliases(annotation_alias_plan):
    catalog = load_template_catalog(ROOT)
    plan = annotation_alias_plan
    resolutions = []

    scene, _ = production.compile_plan(
        plan, {"slide_id": "token-test"}, catalog, resolutions,
    )

    annotation = next(node for node in scene["nodes"] if node["type"] == "annotation")
    assert annotation["targetId"] == "subject-node"
    assert annotation["labelId"] == "anchor-label-node"
    assert resolutions == [{
        "annotation_id": "annotation-node",
        "target": {"requested": "subject-art", "resolved": "subject-node"},
        "label": {"requested": "anchor-label", "resolved": "anchor-label-node"},
        "basis": "explicit asset/slot identity with matching image anchor",
    }]


@pytest.mark.parametrize("field,value,code", [
    ("targetId", "unknown-figure", "ANNOTATION_TARGET_UNRESOLVED"),
    ("targetId", "focus", "ANNOTATION_TARGET_UNRESOLVED"),
    ("labelId", "unknown-label", "ANNOTATION_LABEL_UNRESOLVED"),
    ("labelId", "card-1", "ANNOTATION_LABEL_UNRESOLVED"),
])
def test_compile_rejects_unknown_annotation_alias_even_with_one_image_and_label(
    annotation_alias_plan, field, value, code,
):
    annotation_alias_plan["slots"]["annotation"][field] = value
    with pytest.raises(HtmlReviewError) as error:
        production.compile_plan(annotation_alias_plan, {}, load_template_catalog(ROOT))
    assert error.value.code == code


def test_manual_merge_keeps_title_and_private_anchor(tmp_path, monkeypatch):
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
    manual = editor.read_json(editor.edit_path(tmp_path, scene['id']))
    result = editor.merge_manual_edits(scene, None, manual)
    assert result['conflicts'] == []
    assert result['scene']['nodes'][0]['title'] == '人工保留标题'
    assert next(n for n in result['scene']['nodes'] if n['id'] == image['id'])['assetRef'] == next(n for n in edited['nodes'] if n['id'] == image['id'])['assetRef']
    assert editor.edit_path(tmp_path, scene['id']).is_file()


def test_manual_merge_conflict_preserves_current_scene(tmp_path, monkeypatch):
    scene, contract, folder, inspected, deps = prepare(tmp_path, monkeypatch)
    changed = copy.deepcopy(scene)
    changed['nodes'][0]['title'] = '人工标题'
    editor.save_editor(tmp_path, scene['id'], changed, None, 1)
    before = store.load_scene_with_revision(tmp_path, scene['id'])
    broken = copy.deepcopy(scene)
    broken['nodes'] = broken['nodes'][1:]
    manual = editor.read_json(editor.edit_path(tmp_path, scene['id']))
    result = editor.merge_manual_edits(broken, None, manual)
    assert result['conflicts'][0]['code'] == 'MANUAL_TARGET_CONFLICT'
    assert store.load_scene_with_revision(tmp_path, scene['id']) == before
    assert not inspected


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
