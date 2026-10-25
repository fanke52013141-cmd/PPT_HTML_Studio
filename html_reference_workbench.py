"""Local correction and replay of reference evidence, never author save/approval."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from artifact_fingerprint import sha256_file, sha256_json
from html_input_manifest import resolved_scene_inputs
from html_reference_localization import mapped_reference_targets, validate_mapped_locations
from pipeline_lifecycle import write_json_atomic
from html_page_budget import page_budgeted

KEYS = ('targetId', 'status', 'container_presence', 'container_box', 'identity_evidence', 'part_regions')


def _source(scene, run, repo, resources=None):
    # Use canonical store paths, including the manual editing owner.
    from html_visual_store import revision_path, scene_path
    from html_scene_editing import edit_path
    from html_runtime_skills import runtime_source_files
    paths = [revision_path(run), scene_path(run, scene['id']), edit_path(run, scene['id'])]
    return {'inputs': resolved_scene_inputs(scene, run, repo, project_resources=resources),
            'runtime': runtime_source_files(Path(repo)),
            'authors': {p.relative_to(run).as_posix(): sha256_file(p) if p.is_file() else None for p in paths},
            'sources': {name: sha256_file(Path(repo)/name) for name in (
                'html_reference_workbench.py', 'html_reference_localization.py', 'html_design_agent.py',
                'html_reference_replay.py', 'html_reference_publication.py', 'html_reference_models.py', 'html_reference_workbench_ui.py', 'html_review_evidence.py', 'config/html_runtime_skills.json')}}


def export_workbench(scene, reference, screenshot, report, localization, *, folder, run_dir,
                     repo_root, manual=None, previous=None):
    run, folder = Path(run_dir).resolve(), Path(folder).resolve()
    reference, screenshot = Path(reference).resolve(), Path(screenshot).resolve()
    if any(not p.is_relative_to(run) for p in (folder, reference, screenshot)):
        raise ValueError('REFERENCE_WORKBENCH_PATH_INVALID')
    folder.mkdir(parents=True, exist_ok=True)
    resource_file=run/'planning/html_visual/resources.json'
    resource_snapshot=json.loads(resource_file.read_text(encoding='utf-8')) if resource_file.is_file() else {'assets':[]}
    # Stable bytes; later reviews may overwrite their own shared screenshot.
    for source, name in ((reference, 'reference.png'), (screenshot, 'current.png')):
        (folder/name).write_bytes(source.read_bytes())
    record = {'version': 'reference-workbench/0.1.0', 'scene': scene, 'report': report,
              'manual': manual, 'previous': previous, 'localization': localization,
              'resource_snapshot':resource_snapshot, 'source': _source(scene, run, repo_root, resource_snapshot),
              'reference_sha256': sha256_file(reference), 'screenshot_sha256': sha256_file(screenshot),
              'original_reference': reference.relative_to(run).as_posix(),
              'human_approval': 'pending', 'author_writes': 0}
    write_json_atomic(folder/'session.json', record)
    mapping = {'targets': [{k: row[k] for k in KEYS} for row in localization['result']['targets']]}
    correction = {'session_sha256': sha256_json(record), 'mapping': mapping}
    write_json_atomic(folder/'correction.json', correction)
    from html_reference_workbench_ui import render_workbench
    html = render_workbench(folder/'reference.png', folder/'current.png', correction, localization['image_size'],
                            mapped_reference_targets(scene))
    (folder/'index.html').write_text(html, encoding='utf-8')
    return {'path': (folder/'index.html').relative_to(run).as_posix(), 'session_sha256': sha256_json(record)}


@page_budgeted
def resume_review(folder, correction, *, run_dir, deps, checkpoint=lambda: None,
                  execution_mode='configured_transport', execution_identity=None):
    from html_design_agent import review_fidelity
    run, folder = Path(run_dir).resolve(), Path(folder).resolve()
    if not folder.is_relative_to(run):
        raise ValueError('REFERENCE_WORKBENCH_PATH_INVALID')
    if execution_mode not in ('configured_transport', 'offline_supplied_response'):
        raise ValueError('REFERENCE_REVIEW_EXECUTION_MODE_INVALID')
    if execution_identity is not None:
        import re
        if not isinstance(execution_identity, str) or not re.fullmatch('[0-9a-f]{64}', execution_identity):
            raise ValueError('REFERENCE_REVIEW_EXECUTION_IDENTITY_INVALID')
    if execution_mode == 'offline_supplied_response' and execution_identity is None:
        raise ValueError('REFERENCE_REVIEW_EXECUTION_IDENTITY_REQUIRED')
    session_file, correction_file = folder/'session.json', Path(correction)
    session_hash, correction_hash = sha256_file(session_file), sha256_file(correction_file)
    session = json.loads(session_file.read_text(encoding='utf-8'))
    correction = json.loads(correction_file.read_text(encoding='utf-8'))
    if set(correction) != {'session_sha256', 'mapping'} or correction['session_sha256'] != sha256_json(session):
        raise ValueError('REFERENCE_WORKBENCH_SESSION_MISMATCH')
    scene, ref, shot = session['scene'], folder/'reference.png', folder/'current.png'
    original_reference = (run/session['original_reference']).resolve()
    if not original_reference.is_relative_to(run):
        raise ValueError('REFERENCE_WORKBENCH_PATH_INVALID')
    def fresh():
        checkpoint()
        if (session['source'] != _source(scene, run, deps.repo_root, session.get('resource_snapshot'))
            or sha256_file(session_file) != session_hash or sha256_file(correction_file) != correction_hash
            or sha256_file(original_reference) != session['reference_sha256']
            or sha256_file(ref) != session['reference_sha256'] or sha256_file(shot) != session['screenshot_sha256']):
            raise ValueError('REFERENCE_WORKBENCH_SOURCE_STALE')
    fresh()
    localization = copy.deepcopy(session['localization'])
    selected = {t['targetId'] for t in localization['result']['targets']}
    targets = [t for t in mapped_reference_targets(scene) if t['targetId'] in selected]
    localization['result'] = validate_mapped_locations(correction['mapping'], targets, localization['image_size'])
    localization['manual_correction'] = {'mapping_sha256': sha256_json(correction['mapping']),
                                         'session_sha256': sha256_json(session), 'visual_approval': False}
    receipt = sha256_json(correction)
    write_json_atomic(folder/'corrections'/f'{receipt}.json', correction)
    # A corrected mapping invalidates all derived edge evidence from the
    # original model observation. Keep that original in session.json only.
    from PIL import Image
    from html_text_edge_verification import verify_text_edges
    from html_text_edge_report import write_text_edge_report
    with Image.open(ref) as image:
        localization['edge_verification'] = verify_text_edges(image, localization['result'])
    localization['edge_report'] = write_text_edge_report(ref, localization,
        folder/'corrections'/f'{receipt}-text-edges.html')
    # The original full checklist and unresolved gate still apply.
    from html_reference_replay import execute_once
    identity = {'correction_sha256':receipt, 'execution_mode':execution_mode,
                'execution_identity':execution_identity}
    replay_folder = folder/'replays'/sha256_json(identity)
    def execute():
        result = review_fidelity(scene, ref, shot, session['report'], None,
            folder=replay_folder, run_dir=run, deps=deps, manual=session['manual'],
            previous=session['previous'], checkpoint=fresh, localized_reference=True,
            localization_override=localization)
        return {**result, 'execution_mode':execution_mode, 'execution_identity':execution_identity}
    return execute_once(replay_folder, identity, execute, fresh)
