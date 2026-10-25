"""Explicit same-project asset reuse; exact bytes, metadata and authored ownership."""
import copy
import json
from pathlib import Path
from html_asset_reuse_models import ReuseAssetBinding
from artifact_fingerprint import sha256_file
from html_asset_service import inspect_asset_bytes
from html_build_snapshot import safe_file
from html_visual_review_service import HtmlReviewError


def available(run_dir):
    run=Path(run_dir).resolve()
    path=run/'planning/html_visual/resources.json'
    resources=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'assets':[]}
    pages={}
    for file in sorted((run/'planning/html_visual').glob('scene-*.json'))[:2000]:
        scene=json.loads(file.read_text(encoding='utf-8'))
        for node in scene.get('nodes',[]):
            ref=node.get('assetRef')
            if ref:pages.setdefault((ref['id'],ref['version']),set()).add(scene['id'])
    rows=[]
    for asset in resources.get('assets',[]):
        if (asset['id'],asset['version']) not in pages:continue
        try:
            verified=verify(run,asset)
            rows.append({'id':asset['id'],'version':asset['version'],'sha256':asset['sha256'],
                'size':verified['size'],'alpha_bbox':verified['alpha_bbox'],
                'description':asset.get('need',asset['id']),'source_pages':sorted(pages[(asset['id'],asset['version'])]),
                'visual_approval':'not_transferred'})
        except (ValueError,OSError):
            continue  # Unusable records are not offered; explicit use still fails closed.
    return rows


def verify(run, asset):
    file=safe_file(run,asset['file'].replace('\\','/'))
    if sha256_file(file)!=asset['sha256']:
        raise ValueError('ASSET_REUSE_HASH_MISMATCH')
    facts=inspect_asset_bytes(file.read_bytes())
    if (asset.get('size')!={'width':facts['width'],'height':facts['height']}
        or asset.get('alpha_bbox')!=facts['alpha_bbox'] or facts['fully_transparent']):
        raise ValueError('ASSET_REUSE_METADATA_MISMATCH')
    if any(type(a.get('x')) is not int or type(a.get('y')) is not int or
           not 0<=a['x']<facts['width'] or not 0<=a['y']<facts['height'] for a in asset.get('anchors',[])):
        raise ValueError('ASSET_REUSE_ANCHOR_INVALID')
    return asset


def resolve(run_dir, bindings):
    run=Path(run_dir).resolve()
    resources=json.loads((run/'planning/html_visual/resources.json').read_text(encoding='utf-8'))
    offered={(a['id'],a['version'],a['sha256']) for a in available(run)}
    result={}
    for raw in bindings:
        binding=ReuseAssetBinding.model_validate(raw).model_dump()
        key=tuple(binding[k] for k in ('id','version','sha256'))
        if key not in offered or binding['slot'] in result:
            raise HtmlReviewError('素材不属于当前项目可复用清单，或槽位重复',code='ASSET_REUSE_IDENTITY_INVALID',status_code=409)
        matches=[a for a in resources['assets'] if a['id']==binding['id'] and a['version']==binding['version']]
        if len(matches)!=1:raise ValueError('ASSET_REUSE_IDENTITY_AMBIGUOUS')
        result[binding['slot']]=verify(run,matches[0])
    return result


def bind_plan(plan, bindings, run_dir):
    result=copy.deepcopy(plan)
    assets=resolve(run_dir,bindings)
    for slot,asset in assets.items():
        content=result['slots'].get(slot)
        need=next((a for a in result['assets'] if a.get('slot')==slot and a.get('render_owner')=='image_asset'),None)
        if not content or content.get('kind')!='image' or not need:
            raise HtmlReviewError('所选槽位不是计划中的独立图片对象',code='ASSET_REUSE_SLOT_INVALID',status_code=409)
        if content.get('anchorId') and content['anchorId'] not in {a['id'] for a in asset.get('anchors',[])}:
            raise HtmlReviewError('素材缺少所需命名锚点',code='ASSET_REUSE_ANCHOR_MISMATCH',status_code=409)
        old=need['id'];need['id']=asset['id']
        content['assetRef']={'id':asset['id'],'version':asset['version']}
        for value in result['slots'].values():
            if value.get('kind')=='annotation' and value.get('targetId')==old:value['targetId']=asset['id']
    result['reused_asset_refs']=[ReuseAssetBinding.model_validate(b).model_dump() for b in bindings]
    return result
