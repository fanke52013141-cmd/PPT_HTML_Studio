"""Single-object plans from verified immutable parent sheets."""
import copy
from artifact_fingerprint import sha256_json
from html_asset_sheet import HtmlAssetSheetError
from html_asset_sheet_review import _candidate, _read, _revision
from html_visual_store import HtmlVisualConflict
from html_asset_sheet_generation import validate_plan
from pipeline_lifecycle import project_artifact_lock

PROMPT_VERSION = 'html-sheet-single-retry/0.1.0'


def prepare_retry(run_dir, sheet_id, request_key, asset_id, *, expected_revision, need=None, direction='V05'):
    _revision(expected_revision)
    with project_artifact_lock(run_dir):
        _, directory, _ = _candidate(run_dir, sheet_id, request_key)
        from json import loads
        spec = loads((directory / 'spec.json').read_text(encoding='utf-8'))
        slot = next((s for s in spec['slots'] if s['asset_id'] == asset_id), None)
        if slot is None:
            raise HtmlAssetSheetError('SHEET_ASSET_MISSING', '原候选没有声明该对象')
        state = _read(directory / 'reviews.json', {'revision': 0, 'decisions': {}})
        _revision(state.get('revision'))
        if state['revision'] != expected_revision:
            raise HtmlVisualConflict(expected_revision, state['revision'])
        if asset_id in _read(directory / 'accepted.json', {}):
            raise HtmlAssetSheetError('SHEET_ACCEPTED_LOCKED', '已接受对象不能重试，请保留已有素材')
        chosen_need = slot['need'] if need is None else need
        if not isinstance(chosen_need, str) or not chosen_need.strip() or len(chosen_need) > 1000:
            raise HtmlAssetSheetError('SHEET_SEMANTICS', '对象需求须为1–1000字')
        seed = {'parent': request_key, 'asset_id': asset_id, 'need': chosen_need,
                'direction': direction, 'retry_prompt_version': PROMPT_VERSION}
        plan = {'format': 'hps.html.asset_sheet.plan', 'version': '0.1.0',
                'id': 'retry_' + sha256_json(seed)[:32], 'width': 1024, 'height': 1024,
                'direction': direction, 'slots': [{**copy.deepcopy(slot), 'id': 'single',
                    'need': chosen_need, 'rect': [0, 0, 1024, 1024], 'anchors': []}]}
        # Old board-pixel anchors cannot be projected onto regenerated geometry.
        validate_plan(plan)
        return plan, directory / 'source.png'
