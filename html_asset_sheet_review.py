"""Explicit identity/edge review gates and additive resource acceptance."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from html_asset_sheet import HtmlAssetSheetError, _identifier, _decode, _validate, extract_asset_sheet
from html_asset_sheet_store import _json_bytes
from html_visual_store import SCENE_DIR, HtmlVisualConflict, _atomic_write_bytes
from pipeline_lifecycle import project_artifact_lock


def _read(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else copy.deepcopy(default)


def _candidate(run_dir, sheet_id, request_key):
    _identifier(sheet_id)
    if not isinstance(request_key, str) or not re.fullmatch(r'[0-9a-f]{64}', request_key):
        raise HtmlAssetSheetError('SHEET_HASH', '候选请求摘要不合法')
    root = Path(run_dir).resolve()
    directory = root / SCENE_DIR / 'asset-sheets' / sheet_id / request_key
    if not directory.resolve().is_relative_to(root):
        raise HtmlAssetSheetError('SHEET_PATH_ESCAPE', '候选路径越界')
    def payload(name):
        path = directory / name
        if not path.resolve().is_relative_to(directory.resolve()):
            raise HtmlAssetSheetError('SHEET_PATH_ESCAPE', '候选文件路径越界')
        return path.read_bytes()
    try:
        if not (directory / 'spec.json').is_file():
            raise HtmlAssetSheetError('SHEET_CANDIDATE_MISSING', '素材候选不存在')
        spec = json.loads(payload('spec.json'))
        source = payload('source.png')
        _validate(spec, _decode(source).size)
        masks = {s['id']: payload(f'mask-{s["id"]}.png')
                 for s in spec['slots'] if s['method'] == 'mask' and (directory / f'mask-{s["id"]}.png').is_file()}
        result = extract_asset_sheet(source, spec, masks=masks)
        manifest = result['manifest']
        if manifest['sheet_id'] != sheet_id or manifest['request_key'] != request_key:
            raise HtmlAssetSheetError('SHEET_CANDIDATE_CORRUPT', '候选身份或请求摘要不符')
        if payload('extraction.json') != _json_bytes(manifest):
            raise HtmlAssetSheetError('SHEET_CANDIDATE_CORRUPT', '候选提取记录不符')
        for asset_id, data in result['images'].items():
            if payload(f'asset-{asset_id}.png') != data:
                raise HtmlAssetSheetError('SHEET_CANDIDATE_CORRUPT', '候选素材字节不符')
            if len(data) > 8*1024*1024:
                raise HtmlAssetSheetError('SHEET_ASSET_BYTE_BUDGET', '独立素材超过现有渲染器8MiB预算')
        expected_files = {'source.png': source, 'spec.json': _json_bytes(spec),
                          'extraction.json': _json_bytes(manifest)}
        expected_files.update({f'mask-{key}.png': data for key, data in masks.items()})
        expected_files.update({f'asset-{key}.png': data for key, data in result['images'].items()})
        seal = {'format': 'hps.html.asset_sheet.candidate', 'version': '0.1.0',
                'request_key': request_key,
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in expected_files.items()}}
        if payload('candidate.json') != _json_bytes(seal):
            raise HtmlAssetSheetError('SHEET_CANDIDATE_CORRUPT', '候选文件摘要清单不符')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HtmlAssetSheetError('SHEET_CANDIDATE_CORRUPT', '素材候选记录损坏') from exc
    return root, directory, manifest


def _revision(value):
    if type(value) is not int or value < 0:
        raise HtmlAssetSheetError('SHEET_REVIEW_REVISION', '审阅修订须为非负整数')


def review_candidate(run_dir, sheet_id, request_key, asset_id, *, identity, edge, note='', expected_revision):
    _revision(expected_revision)
    if identity not in ('approved', 'rejected') or edge not in ('approved', 'rejected') or not isinstance(note, str) or len(note) > 1000:
        raise HtmlAssetSheetError('SHEET_REVIEW_FIELDS', '身份和边缘结论须为approved/rejected，备注最多1000字')
    with project_artifact_lock(run_dir):
        root, directory, manifest = _candidate(run_dir, sheet_id, request_key)
        if not any(a['id'] == asset_id for a in manifest['assets']):
            raise HtmlAssetSheetError('SHEET_ASSET_MISSING', '该对象未产生有效候选')
        path = directory / 'reviews.json'
        state = _read(path, {'revision': 0, 'decisions': {}})
        _revision(state.get('revision'))
        if state['revision'] != expected_revision:
            raise HtmlVisualConflict(expected_revision, state['revision'])
        decision = {'identity': identity, 'edge': edge, 'note': note}
        if state['decisions'].get(asset_id) == decision:
            return {**state, 'changed': False}
        accepted = _read(directory / 'accepted.json', {})
        if asset_id in accepted:
            raise HtmlAssetSheetError('SHEET_ACCEPTED_LOCKED', '已接受素材的审阅不可改写，请创建新候选')
        state['decisions'][asset_id] = decision
        state['revision'] += 1
        _atomic_write_bytes(path, _json_bytes(state))
        return {**state, 'changed': True}


def accept_candidate(run_dir, sheet_id, request_key, asset_id, *, expected_revision):
    _revision(expected_revision)
    with project_artifact_lock(run_dir):
        root, directory, manifest = _candidate(run_dir, sheet_id, request_key)
        state = _read(directory / 'reviews.json', {'revision': 0, 'decisions': {}})
        _revision(state.get('revision'))
        if state['revision'] != expected_revision:
            raise HtmlVisualConflict(expected_revision, state['revision'])
        decision = state['decisions'].get(asset_id, {})
        if decision.get('identity') != 'approved' or decision.get('edge') != 'approved':
            raise HtmlAssetSheetError('SHEET_REVIEW_REQUIRED', '需先逐对象批准身份和边缘')
        asset = next((a for a in manifest['assets'] if a['id'] == asset_id), None)
        if asset is None:
            raise HtmlAssetSheetError('SHEET_ASSET_MISSING', '素材候选无有效对象')
        entry = {**asset, 'file': str((directory / f'asset-{asset_id}.png').relative_to(root)).replace('\\', '/'),
                 'status': 'accepted', 'identity_review': 'approved', 'edge_review': 'approved',
                 'request_key': request_key, 'review': decision}
        resources_path, accepted_path = root / SCENE_DIR / 'resources.json', directory / 'accepted.json'
        resources = _read(resources_path, {'assets': []})
        existing = next((a for a in resources['assets'] if a['id'] == asset_id), None)
        accepted = _read(accepted_path, {})
        if existing is not None:
            if existing == entry and accepted.get(asset_id) == hashlib.sha256(_json_bytes(entry)).hexdigest():
                return {'changed': False, 'asset': entry}
            raise HtmlAssetSheetError('SHEET_RESOURCE_CONFLICT', '同名资源已存在，不能覆盖人工或旧有效资源')
        previous = {p: p.read_bytes() if p.is_file() else None for p in (resources_path, accepted_path)}
        try:
            resources['assets'].append(entry)
            accepted[asset_id] = hashlib.sha256(_json_bytes(entry)).hexdigest()
            _atomic_write_bytes(resources_path, _json_bytes(resources))
            _atomic_write_bytes(accepted_path, _json_bytes(accepted))
        except Exception:
            for path, data in previous.items():
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write_bytes(path, data)
            raise
        return {'changed': True, 'asset': entry}
