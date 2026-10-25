"""Sealed evidence checkpoint for explicit continuation of an accepted design.

This is not visual approval or an author save. The continuation applies only
registered static operations and reruns the original strict renderer/QA.
"""
import json
from pathlib import Path
from artifact_fingerprint import sha256_file,sha256_json
from html_build_snapshot import safe_file
from html_reference_workbench import _source
from pipeline_lifecycle import write_json_atomic


def publish(packet, result, run_dir):
    run=Path(run_dir).resolve();folder=packet['folder'];session=packet['session']
    if result.get('execution_mode')!='configured_transport' or result.get('result',{}).get('status')!='pass':
        raise ValueError('REFERENCE_REVIEW_MODE_OR_RESULT_INVALID')
    record={'version':'reference-continuation/0.1.0','session':session,'review':result,
            'session_path':(folder/'session.json').relative_to(run).as_posix(),
            'reference_path':(folder/'reference.png').relative_to(run).as_posix(),
            'screenshot_path':(folder/'current.png').relative_to(run).as_posix(),
            'author_saved':False,'human_approval':'pending'}
    key=sha256_json(record)
    write_json_atomic(run/'planning/html_visual/reference-reviewed'/f'{key}.json',record)
    return key


def load(run_dir,key,repo):
    import re
    run=Path(run_dir).resolve()
    if not isinstance(key,str) or not re.fullmatch('[0-9a-f]{64}',key):raise ValueError('REFERENCE_REVIEW_KEY_INVALID')
    record=json.loads((run/'planning/html_visual/reference-reviewed'/f'{key}.json').read_text(encoding='utf-8'))
    if sha256_json(record)!=key:raise ValueError('REFERENCE_REVIEW_RECEIPT_CHANGED')
    session=record['session']
    if session['source']!=_source(session['scene'],run,repo,session.get('resource_snapshot')):
        raise ValueError('REFERENCE_REVIEW_SOURCE_STALE')
    if json.loads(safe_file(run,record['session_path']).read_text(encoding='utf-8'))!=session:
        raise ValueError('REFERENCE_REVIEW_SESSION_CHANGED')
    for name,hash_key in (('reference_path','reference_sha256'),('screenshot_path','screenshot_sha256')):
        if sha256_file(safe_file(run,record[name]))!=session[hash_key]:raise ValueError('REFERENCE_REVIEW_IMAGE_CHANGED')
    return record


def restore(scene,binding,key,reference,*,run_dir,deps,manual,beats,audit):
    from html_saved_layout_repair import operations_between
    from html_scene_repair import candidate_from_document
    from html_scene_editing import resources
    from html_visual_review_service import review_scene
    record=load(run_dir,key,deps.repo_root);session=record['session'];target=session['scene']
    old={n['id']:n for n in scene['nodes']};new={n['id']:n for n in target['nodes']}
    def content(node):return {k:v for k,v in node.items() if k not in ('presentation','icon')}
    if (set(old)!=set(new) or any(content(old[i])!=content(new[i]) for i in old)
        or any(scene.get(k)!=target.get(k) for k in ('id','motion','beats','layoutRef','themeRef','templateRef'))
        or sha256_file(reference)!=session['reference_sha256']):
        raise ValueError('REFERENCE_REVIEW_CANDIDATE_MISMATCH')
    operations=operations_between(scene,target)
    if operations:
        candidate=candidate_from_document(run_dir,scene['id'],{'expected_revision':0,'source':'ai','operations':operations},
            {'scene':scene,'binding':binding,'manual':manual,'beats':beats,'resources':resources(run_dir)})['scene']
    else:candidate=scene
    if {k:v for k,v in candidate.items() if k!='version'}!={k:v for k,v in target.items() if k!='version'}:
        raise ValueError('REFERENCE_REVIEW_OPERATIONS_INCOMPLETE')
    report=review_scene(candidate,run_dir=run_dir,deps=deps,preflight_dir=audit/'restored-preflight')
    if not report.get('passed') or not report.get('geometry_preflight',{}).get('passed'):
        raise ValueError('REFERENCE_REVIEW_ENGINEERING_REJECTED')
    review=record['review']
    if (review['result']['status']!='pass' or review.get('screenshot_sha256')!=sha256_file(Path(run_dir)/report['screenshot'])
        or review.get('scene_sha256')!=sha256_json(target)):
        raise ValueError('REFERENCE_REVIEW_RENDER_OR_FIDELITY_CHANGED')
    write_json_atomic(audit/'reference-restored.json',{'reference_review_key':key,'operations':operations,
                                                    'report':report,'visual_approval':'pending'})
    return candidate,report,review
