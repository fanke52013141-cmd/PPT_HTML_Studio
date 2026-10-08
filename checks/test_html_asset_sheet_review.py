"""Reviewed candidate -> existing runtime resource contract, without scene writes."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from checks.test_html_asset_sheet import fixture
from html_asset_sheet import HtmlAssetSheetError
from html_asset_sheet_store import persist_sheet_candidates
from html_visual_store import HtmlVisualConflict
import html_asset_sheet_review as review


def prepared(tmp_path):
    source, spec = fixture()
    result = persist_sheet_candidates(tmp_path, source, spec)
    return 'board', result['manifest']['request_key']


def approved(tmp_path, args):
    return review.review_candidate(tmp_path, *args, 'one', identity='approved', edge='approved', expected_revision=0)


def test_review_accept_and_real_renderer_resource_load(tmp_path):
    args = prepared(tmp_path)
    with pytest.raises(HtmlAssetSheetError) as exc:
        review.accept_candidate(tmp_path, *args, 'one', expected_revision=0)
    assert exc.value.code == 'SHEET_REVIEW_REQUIRED'
    state = approved(tmp_path, args)
    assert state['revision'] == 1
    assert review.review_candidate(tmp_path, *args, 'one', identity='approved', edge='approved', expected_revision=1)['changed'] is False
    accepted = review.accept_candidate(tmp_path, *args, 'one', expected_revision=1)
    assert accepted['changed'] is True and accepted['asset']['status'] == 'accepted'
    assert review.accept_candidate(tmp_path, *args, 'one', expected_revision=1)['changed'] is False
    resources = tmp_path / 'planning/html_visual/resources.json'
    command = "const r=require('./html_engine/tools/project-resources.cjs').loadProjectResources();console.log(JSON.stringify(r.assets));"
    result = subprocess.run(['node', '-e', command], cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, 'HPS_HTML_RESOURCES': str(resources)}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    asset = json.loads(result.stdout)[0]
    assert asset['id'] == 'one' and asset['anchors'][0]['x'] == 5/16
    assert asset['alphaBounds'] == {'x':3, 'y':3, 'width':10, 'height':10}
    assert not (tmp_path / 'planning/html_visual/revision.json').exists()
    with pytest.raises(HtmlAssetSheetError) as exc:
        review.review_candidate(tmp_path, *args, 'one', identity='rejected', edge='approved', expected_revision=1)
    assert exc.value.code == 'SHEET_ACCEPTED_LOCKED'


def test_rejection_and_revision_conflict_do_not_register(tmp_path):
    args = prepared(tmp_path)
    review.review_candidate(tmp_path, *args, 'one', identity='approved', edge='rejected', expected_revision=0, note='rough boundary')
    with pytest.raises(HtmlVisualConflict):
        review.review_candidate(tmp_path, *args, 'one', identity='approved', edge='approved', expected_revision=0)
    with pytest.raises(HtmlVisualConflict):
        review.accept_candidate(tmp_path, *args, 'one', expected_revision=0)
    with pytest.raises(HtmlAssetSheetError) as exc:
        review.accept_candidate(tmp_path, *args, 'one', expected_revision=1)
    assert exc.value.code == 'SHEET_REVIEW_REQUIRED'
    assert not (tmp_path / 'planning/html_visual/resources.json').exists()


def test_resource_conflict_keeps_existing_bytes(tmp_path):
    args = prepared(tmp_path)
    approved(tmp_path, args)
    path = tmp_path / 'planning/html_visual/resources.json'
    previous = b'{"assets":[{"id":"one","source":"manual"}]}'
    path.write_bytes(previous)
    with pytest.raises(HtmlAssetSheetError) as exc:
        review.accept_candidate(tmp_path, *args, 'one', expected_revision=1)
    assert exc.value.code == 'SHEET_RESOURCE_CONFLICT'
    assert path.read_bytes() == previous


def test_corrupted_candidate_cannot_be_reviewed(tmp_path):
    args = prepared(tmp_path)
    path = tmp_path / 'planning/html_visual/asset-sheets' / args[0] / args[1]
    (path / 'asset-one.png').write_bytes(b'corrupt')
    with pytest.raises(HtmlAssetSheetError) as exc:
        approved(tmp_path, args)
    assert exc.value.code == 'SHEET_CANDIDATE_CORRUPT'
    assert not (path / 'reviews.json').exists()


def test_accept_write_failure_rolls_back_resources(tmp_path, monkeypatch):
    args = prepared(tmp_path)
    approved(tmp_path, args)
    original = review._atomic_write_bytes
    def fail(path, data):
        if path.name == 'accepted.json':
            raise OSError('interrupted')
        original(path, data)
    monkeypatch.setattr(review, '_atomic_write_bytes', fail)
    with pytest.raises(OSError, match='interrupted'):
        review.accept_candidate(tmp_path, *args, 'one', expected_revision=1)
    assert not (tmp_path / 'planning/html_visual/resources.json').exists()
