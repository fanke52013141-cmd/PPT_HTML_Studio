"""Persist immutable extraction candidates; never publish project resources."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from pipeline_lifecycle import project_artifact_lock
from html_asset_sheet import HtmlAssetSheetError, extract_asset_sheet
from html_visual_store import SCENE_DIR


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')


def persist_sheet_candidates(run_dir, source_bytes, specification, *, masks=None):
    """A complete candidate directory becomes visible with one directory rename.

    Cache reuse verifies every expected byte. Corruption fails loudly and does
    not overwrite a candidate that may already have review evidence attached.
    No scene revision, approval, audio, DB or resources manifest is changed.
    """
    if masks is not None and (not isinstance(masks, dict) or any(not isinstance(data, bytes) for data in masks.values())):
        raise HtmlAssetSheetError('SHEET_MASK_FORMAT', '候选存储仅接受PNG字节遮罩')
    result = extract_asset_sheet(source_bytes, specification, masks=masks)
    manifest = result['manifest']
    files = {'source.png': source_bytes, 'spec.json': _json_bytes(specification),
             'extraction.json': _json_bytes(manifest)}
    files.update({f'asset-{key}.png': data for key, data in result['images'].items()})
    files.update({f'mask-{key}.png': data for key, data in (masks or {}).items()})
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    seal = {'format': 'hps.html.asset_sheet.candidate', 'version': '0.1.0',
            'request_key': manifest['request_key'], 'files': hashes}
    files['candidate.json'] = _json_bytes(seal)
    root = Path(run_dir).resolve()
    parent = root / SCENE_DIR / 'asset-sheets' / manifest['sheet_id']
    destination = parent / manifest['request_key']
    if not destination.resolve().is_relative_to(root):
        raise HtmlAssetSheetError('SHEET_PATH_ESCAPE', '素材候选路径越界')
    with project_artifact_lock(root):
        cache = destination.exists()
        if cache:
            for name, data in files.items():
                path = destination / name
                if not path.is_file() or path.read_bytes() != data:
                    raise HtmlAssetSheetError('SHEET_CANDIDATE_CORRUPT', '素材候选字节或追溯记录损坏')
        else:
            parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.candidate-', dir=parent) as staging:
                stage = Path(staging)
                for name, data in files.items():
                    (stage / name).write_bytes(data)
                stage.rename(destination)
    return {'manifest': manifest, 'directory': str(destination.relative_to(root)).replace('\\', '/'),
            'cache': 'hit' if cache else 'miss', 'candidate': seal}
