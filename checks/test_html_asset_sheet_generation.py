"""Real candidate storage with controlled image and segmentation adapters."""
import copy
import io
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

import html_asset_sheet_generation as generation
from html_asset_sheet import HtmlAssetSheetError
from checks.test_html_asset_sheet import fixture, png


def plan_fixture(method='source_alpha'):
    source, spec = fixture(method)
    return source, {'format': 'hps.html.asset_sheet.plan', 'version': '0.1.0',
                    'id': 'board', 'width': 32, 'height': 16, 'direction': 'V05', 'slots': spec['slots']}


def test_generation_cached_and_model_change_creates_new_request(tmp_path):
    source, plan = plan_fixture()
    original = copy.deepcopy(plan)
    calls = []
    def provider(prompt, **kw):
        calls.append((prompt, kw))
        return source
    first = generation.generate_sheet_candidates(plan, run_dir=tmp_path, provider=provider, model_config_hash='a'*64)
    second = generation.generate_sheet_candidates(plan, run_dir=tmp_path, provider=provider, model_config_hash='a'*64)
    third = generation.generate_sheet_candidates(plan, run_dir=tmp_path, provider=provider, model_config_hash='b'*64)
    assert first['generation_cache'] == third['generation_cache'] == 'miss'
    assert second['generation_cache'] == 'hit'
    assert first['generation_key'] != third['generation_key']
    assert len(calls) == 2 and plan == original
    assert calls[0][1] == {'size': '32x16', 'transparent_background': True}
    prompt = calls[0][0]
    assert generation.PROMPT_VERSION in prompt
    assert 'asset_id' not in prompt and 'anchors' not in prompt and 'source_sha256' not in prompt
    assert 'one' in prompt and 'two' in prompt
    assert not (tmp_path / 'planning/html_visual/resources.json').exists()


def test_mask_adapter_receives_source_and_partial_failures_are_candidates(tmp_path):
    source, plan = plan_fixture('mask')
    captured = []
    mask = Image.new('L', (32, 16))
    ImageDraw.Draw(mask).rectangle((3, 3, 12, 12), fill=128)
    def segmenter(data, *, slots):
        captured.append((data, slots))
        return {'left': png(mask)}
    result = generation.generate_sheet_candidates(plan, run_dir=tmp_path,
        provider=lambda *a, **kw: source, model_config_hash='a'*64, segmenter=segmenter)
    assert captured[0][0] == source and len(captured[0][1]) == 1
    assert result['manifest']['status'] == 'pending_review'
    asset = Image.open(io.BytesIO((tmp_path / result['directory'] / 'asset-one.png').read_bytes()))
    assert asset.getpixel((5, 5))[3] == 64
    result = generation.generate_sheet_candidates(plan, run_dir=tmp_path,
        provider=lambda *a, **kw: pytest.fail('must reuse generated sheet'), model_config_hash='a'*64,
        segmenter=lambda *a, **kw: {})
    assert result['manifest']['status'] == 'partial'
    assert result['manifest']['failures'][0]['code'] == 'SHEET_MASK_MISSING'


def test_missing_segmenter_fails_before_spending_generation(tmp_path):
    _, plan = plan_fixture('mask')
    with pytest.raises(HtmlAssetSheetError) as exc:
        generation.generate_sheet_candidates(plan, run_dir=tmp_path,
            provider=lambda *a, **kw: pytest.fail('no generation'), model_config_hash='a'*64)
    assert exc.value.code == 'SHEET_SEGMENTER_REQUIRED'


def test_wrong_size_and_provider_error_do_not_publish(tmp_path):
    _, plan = plan_fixture()
    with pytest.raises(HtmlAssetSheetError) as exc:
        generation.generate_sheet_candidates(plan, run_dir=tmp_path,
            provider=lambda *a, **kw: png(Image.new('RGBA', (8, 8))), model_config_hash='a'*64)
    assert exc.value.code == 'SHEET_GENERATED_SIZE'
    def fail(*a, **kw):
        raise RuntimeError('private-key')
    with pytest.raises(HtmlAssetSheetError) as exc:
        generation.generate_sheet_candidates(plan, run_dir=tmp_path, provider=fail, model_config_hash='a'*64)
    assert exc.value.code == 'SHEET_PROVIDER_FAILED' and 'private-key' not in str(exc.value)
    assert not (tmp_path / 'planning/html_visual/asset-sheets').exists()


def test_cache_corruption_fails_without_regeneration(tmp_path):
    source, plan = plan_fixture()
    result = generation.generate_sheet_candidates(plan, run_dir=tmp_path, provider=lambda *a, **kw: source, model_config_hash='a'*64)
    path = tmp_path / 'planning/html_visual/sheet-generation/board' / result['generation_key'] / 'source.png'
    path.write_bytes(b'corrupt')
    with pytest.raises(HtmlAssetSheetError) as exc:
        generation.generate_sheet_candidates(plan, run_dir=tmp_path,
            provider=lambda *a, **kw: pytest.fail('corruption is not a cache miss'), model_config_hash='a'*64)
    assert exc.value.code == 'SHEET_GENERATION_CORRUPT'


def test_cancel_after_provider_keeps_existing_candidates(tmp_path):
    source, plan = plan_fixture()
    checkpoints = []
    def checkpoint():
        checkpoints.append(1)
        if len(checkpoints) == 2:
            raise ValueError('stopped')
    with pytest.raises(ValueError, match='stopped'):
        generation.generate_sheet_candidates(plan, run_dir=tmp_path, provider=lambda *a, **kw: source,
            model_config_hash='a'*64, checkpoint=checkpoint)
    assert not list(tmp_path.rglob('candidate.json'))


def test_project_adapter_uses_frozen_image_without_global_lookup(tmp_path, monkeypatch):
    import project_model_binding_service as binding
    import html_image_provider
    import project_path_service
    source, plan = plan_fixture()
    frozen_image = SimpleNamespace(config_hash='a'*64)
    monkeypatch.setattr(binding, 'freeze_project_models', lambda project, required: SimpleNamespace(image=frozen_image))
    monkeypatch.setattr(project_path_service, 'project_run_dir_or_500', lambda project: tmp_path)
    def provider(*a, **kw):
        assert kw.pop('model_binding') is frozen_image
        return source
    monkeypatch.setattr(html_image_provider, 'configured_image', provider)
    result = generation.generate_project_sheet_candidates(SimpleNamespace(visual_backend='html'), plan)
    assert result['model_config_hash'] == 'a'*64
    with pytest.raises(HtmlAssetSheetError) as exc:
        generation.generate_project_sheet_candidates(SimpleNamespace(visual_backend='image'), plan)
    assert exc.value.code == 'SHEET_BACKEND'


def test_different_background_modes_rejected_and_purecolor_is_explicit():
    _, plan = plan_fixture()
    plan['slots'][0].update(method='boundary_color', background={'rgb':[255,255,255], 'tolerance':0})
    with pytest.raises(HtmlAssetSheetError) as exc:
        generation.build_sheet_prompt(plan)
    assert exc.value.code == 'SHEET_BACKGROUND'
    plan['slots'][1].update(method='boundary_color', background={'rgb':[255,255,255], 'tolerance':0})
    assert 'RGB[255, 255, 255]' in generation.build_sheet_prompt(plan)


@pytest.mark.parametrize('mutation,code', [
    (lambda p: p.update(extra=True), 'SHEET_FIELDS'),
    (lambda p: p.update(width=True), 'SHEET_PIXEL_BUDGET'),
    (lambda p: p.update(direction='watercolor-master'), 'SHEET_DIRECTION'),
    (lambda p: p.update(width=100000, height=100000), 'SHEET_PIXEL_BUDGET'),
    (lambda p: p['slots'][1].update(rect=[8,0,16,16]), 'SHEET_SLOT_OVERLAP'),
])
def test_invalid_plan_fails_before_provider(tmp_path, mutation, code):
    _, plan = plan_fixture()
    mutation(plan)
    with pytest.raises(HtmlAssetSheetError) as exc:
        generation.generate_sheet_candidates(plan, run_dir=tmp_path,
            provider=lambda *a, **kw: pytest.fail('invalid plan cannot spend generation'), model_config_hash='a'*64)
    assert exc.value.code == code
