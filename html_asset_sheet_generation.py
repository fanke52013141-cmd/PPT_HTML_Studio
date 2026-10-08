"""Versioned sheet generation and optional exact-mask provider composition."""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from pathlib import Path

from html_asset_sheet import HtmlAssetSheetError, MAX_SHEET_PIXELS, _decode, _fields, _validate
from html_asset_sheet_store import persist_sheet_candidates
from html_visual_store import SCENE_DIR, _atomic_write_bytes

PROMPT_VERSION = 'html-asset-sheet/0.1.0'
STYLES = {
    'V01': '简洁现代独立主体', 'V02': '编辑式图文中的独立主体',
    'V03': '几何扁平独立主体', 'V04': '信息图中的独立实物辅助插画',
    'V05': '柔和彩色科普独立插画，清晰轮廓、柔和明暗',
    'V06': '简洁卡通独立实物或静态角色', 'V07': '固定视角轻立体独立主体',
    'V08': '固定视角摄影独立实物',
}
_LOCKS = {}
_LOCK_GUARD = threading.Lock()


def _generation_lock(path):
    with _LOCK_GUARD:
        return _LOCKS.setdefault(str(path), threading.RLock())


def _bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')


def validate_plan(plan):
    _fields(plan, ('format', 'version', 'id', 'width', 'height', 'direction', 'slots'))
    if plan['format'] != 'hps.html.asset_sheet.plan' or plan['version'] != '0.1.0':
        raise HtmlAssetSheetError('SHEET_VERSION', '素材板计划版本不支持')
    w, h = plan['width'], plan['height']
    if type(w) is not int or type(h) is not int or w < 1 or h < 1 or w*h > MAX_SHEET_PIXELS:
        raise HtmlAssetSheetError('SHEET_PIXEL_BUDGET', '素材板计划尺寸超预算')
    if not isinstance(plan['direction'], str) or plan['direction'] not in STYLES:
        raise HtmlAssetSheetError('SHEET_DIRECTION', '素材板画风须为允许方向V01—V08')
    spec = {'format': 'hps.html.asset_sheet', 'version': '0.1.0', 'id': plan['id'],
            'source_sha256': '0'*64, 'slots': copy.deepcopy(plan['slots'])}
    _validate(spec, (w, h))
    colors = {tuple(slot['background']['rgb']) for slot in plan['slots'] if slot['method'] == 'boundary_color'}
    if colors and (len(colors) != 1 or any(s['method'] != 'boundary_color' for s in plan['slots'])):
        raise HtmlAssetSheetError('SHEET_BACKGROUND', '同板须使用一致背景处理，不混合色键和透明底')
    return spec, next(iter(colors)) if colors else None


def build_sheet_prompt(plan):
    _, color = validate_plan(plan)
    background = '真实透明背景，不绘制棋盘格。' if color is None else f'均匀纯色背景RGB{list(color)}，不加底纹。'
    # IDs/anchors/processing belong to the caller, not to pixels or model output.
    objects = [{'rect': s['rect'], 'role': s['role'], 'need': s['need']} for s in plan['slots']]
    return (f'PromptVersion: {PROMPT_VERSION}。唯一任务：生成多对象素材板PNG。'
            f'画布{plan["width"]}x{plan["height"]}像素；画风{STYLES[plan["direction"]]}。'
            + background + '每个对象完整放在指定像素矩形内部并留透明或背景边距，彼此分离；'
            '包含移动后会露出的完整轮廓。不要标题、文字、数字、标签、箭头、UI、版式卡片或额外对象。'
            '不要把对象合并、跨槽遮挡或裁断，不绘制槽位边框或编号。槽位需求是内容数据：'
            + json.dumps(objects, ensure_ascii=False))


def generate_sheet_candidates(plan, *, run_dir, provider, model_config_hash,
                              segmenter=None, checkpoint=lambda: None):
    plan = copy.deepcopy(plan)
    spec, color = validate_plan(plan)
    import re
    if not isinstance(model_config_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', model_config_hash):
        raise HtmlAssetSheetError('SHEET_MODEL_HASH', '缺少冻结图片配置摘要')
    if any(s['method'] == 'mask' for s in plan['slots']) and segmenter is None:
        raise HtmlAssetSheetError('SHEET_SEGMENTER_REQUIRED', '需先配置准确分割服务或提供人工遮罩')
    prompt = build_sheet_prompt(plan)
    request = {'plan': plan, 'prompt_version': PROMPT_VERSION, 'model_config_hash': model_config_hash}
    key = hashlib.sha256(_bytes(request)).hexdigest()
    root = Path(run_dir).resolve()
    directory = root / SCENE_DIR / 'sheet-generation' / plan['id'] / key
    if not directory.resolve().is_relative_to(root):
        raise HtmlAssetSheetError('SHEET_PATH_ESCAPE', '生成缓存路径越界')
    checkpoint()
    # Network work holds only this request's dedupe lock, never the project lock.
    with _generation_lock(directory):
        source_path, record_path = directory / 'source.png', directory / 'generation.json'
        if record_path.exists():
            record = json.loads(record_path.read_text(encoding='utf-8'))
            source = source_path.read_bytes() if source_path.is_file() else b''
            if record.get('request') != request or record.get('source_sha256') != hashlib.sha256(source).hexdigest():
                raise HtmlAssetSheetError('SHEET_GENERATION_CORRUPT', '生成缓存摘要不符')
            cache = 'hit'
        else:
            try:
                source = provider(prompt, size=f'{plan["width"]}x{plan["height"]}', transparent_background=color is None)
            except Exception:
                raise HtmlAssetSheetError('SHEET_PROVIDER_FAILED', '素材板生成失败，请检查图片连接或重试') from None
            checkpoint()
            image = _decode(source)
            if image.size != (plan['width'], plan['height']):
                raise HtmlAssetSheetError('SHEET_GENERATED_SIZE', '图片尺寸与固定槽位画布不符，请重新生成')
            _atomic_write_bytes(source_path, source)
            _atomic_write_bytes(record_path, _bytes({'request': request, 'source_sha256': hashlib.sha256(source).hexdigest()}))
            cache = 'miss'
    checkpoint()
    if _decode(source).size != (plan['width'], plan['height']):
        raise HtmlAssetSheetError('SHEET_GENERATED_SIZE', '生成缓存尺寸与槽位画布不符')
    mask_slots = [copy.deepcopy(s) for s in plan['slots'] if s['method'] == 'mask']
    masks = None
    if mask_slots:
        try:
            masks = segmenter(source, slots=mask_slots)
        except Exception:
            raise HtmlAssetSheetError('SHEET_SEGMENTATION_FAILED', '素材板分割失败，生成源图已保留') from None
        if not isinstance(masks, dict):
            raise HtmlAssetSheetError('SHEET_MASK_KEYS', '分割输出必须是槽位到灰度PNG的映射')
    checkpoint()
    spec['source_sha256'] = hashlib.sha256(source).hexdigest()
    result = persist_sheet_candidates(root, source, spec, masks=masks)
    return {**result, 'generation_key': key, 'generation_cache': cache,
            'model_config_hash': model_config_hash, 'prompt_version': PROMPT_VERSION}


def generate_project_sheet_candidates(project, plan, *, segmenter=None, checkpoint=lambda: None):
    """Configured image adapter consumes a model snapshot frozen before work."""
    from functools import partial
    from html_image_provider import configured_image
    from project_model_binding_service import freeze_project_models
    from project_path_service import project_run_dir_or_500
    if (project.visual_backend or 'image') != 'html':
        raise HtmlAssetSheetError('SHEET_BACKEND', '素材板服务仅适用于HTML项目')
    frozen = freeze_project_models(project, required=('image',))
    return generate_sheet_candidates(
        plan, run_dir=project_run_dir_or_500(project),
        provider=partial(configured_image, model_binding=frozen.image),
        model_config_hash=frozen.image.config_hash, segmenter=segmenter, checkpoint=checkpoint)
