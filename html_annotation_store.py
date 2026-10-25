"""Versioned evaluation labels, separate from author scenes and visual approvals."""
import copy
import json
import re
from pathlib import Path
from PIL import Image
from artifact_fingerprint import sha256_file,sha256_json
from html_acceptance_criteria import safe
from html_reference_localization import mapped_reference_targets,MappedLocations
from html_paired_evaluation import checked,validate_dataset
from pipeline_lifecycle import project_artifact_lock,write_json_atomic


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def directory(run,dataset_id):
    if not re.fullmatch('[a-z][a-z0-9-]{0,63}',dataset_id):raise ValueError('DATASET_ID_INVALID')
    return safe(run,'planning/html_visual/evaluation/datasets/'+dataset_id)


def load(run,dataset_id):
    folder=directory(run,dataset_id);data=read(safe(folder,'dataset.json'))
    ids=[c['id'] for c in data['cases']]
    if not ids or len(ids)>40 or len(ids)!=len(set(ids)):raise ValueError('DATASET_CASES_INVALID')
    for case in data['cases']:
        for field in ('reference','scene'):checked(folder,case[field])
    return folder,data


def mapping_from_gold(gold):
    rows=[]
    for target,truth in gold['targets'].items():
        parts=[]
        for part,regions in truth['parts'].items():
            regions=[{'text':r['text'],'box':dict(zip(('xPx','yPx','widthPx','heightPx'),
                (r['box'][0],r['box'][1],r['box'][2]-r['box'][0],r['box'][3]-r['box'][1])))} for r in regions if r.get('box')]
            parts.append({'partId':part,'status':'located' if regions else truth['status'],'regions':regions})
        box=truth.get('container')
        rows.append({'targetId':target,'status':truth['status'],'identity_evidence':None,
            'container_presence':'present' if box else 'absent' if truth['status']!='ambiguous' else 'uncertain',
            'container_box':dict(zip(('xPx','yPx','widthPx','heightPx'),(box[0],box[1],box[2]-box[0],box[3]-box[1]))) if box else None,
            'part_regions':parts})
    return {'targets':rows}


def case_view(run,dataset_id,case_id):
    folder,data=load(run,dataset_id)
    case=next((c for c in data['cases'] if c['id']==case_id),None)
    if case is None:raise ValueError('DATASET_CASE_NOT_FOUND')
    reference=checked(folder,case['reference']);scene=read(checked(folder,case['scene']))
    with Image.open(reference) as image:size=list(image.size)
    identity=sha256_json({'case':{k:case[k] for k in ('id','course_id','split','reference','scene')},'label_version':data['label_version']})
    annotation_dir=safe(folder,'annotations/'+case_id)
    pointer=safe(folder,'annotations/'+case_id+'/annotation-current.json')
    if pointer.exists():
        current=read(pointer)
        revision=current['revision']
        if type(revision) is not int or revision<1:raise ValueError('ANNOTATION_REVISION_INVALID')
        state=read(safe(folder,'annotations/'+case_id+'/annotation-versions/'+str(revision)+'.json'))
        if sha256_json(state)!=current['sha256'] or state['source_sha256']!=identity:raise ValueError('ANNOTATION_SOURCE_STALE')
    else:
        state={'revision':0,'source_sha256':identity,'status':'draft','annotator':None,
               'mapping':mapping_from_gold(read(checked(folder,case['gold']))),'review':None}
        for target in mapped_reference_targets(scene):
            row=next(r for r in state['mapping']['targets'] if r['targetId']==target['targetId'])
            known={p['partId'] for p in row['part_regions']}
            row['part_regions'] += [{'partId':p['partId'],'status':row['status'],'regions':[]}
                                   for p in target['text_parts'] if p['partId'] not in known]
    return {'folder':folder,'dataset':data,'case':case,'reference':reference,'scene':scene,'image_size':size,
            'targets':mapped_reference_targets(scene),'state':state,'annotation_dir':annotation_dir}


def validate_mapping(packet,mapping,*,complete=False):
    value=MappedLocations.model_validate(mapping).model_dump();rows=value['targets']
    expected={t['targetId']:{p['partId'] for p in t['text_parts']} for t in packet['targets']}
    if len(rows)!=len(expected) or {r['targetId'] for r in rows}!=set(expected):raise ValueError('ANNOTATION_TARGETS_INCOMPLETE')
    for row in rows:
        if len(row['part_regions'])!=len(expected[row['targetId']]) or {p['partId'] for p in row['part_regions']}!=expected[row['targetId']]:
            raise ValueError('ANNOTATION_PARTS_INCOMPLETE')
        boxes=[r['box'] for part in row['part_regions'] for r in part['regions']]
        if row['container_box']:boxes.append(row['container_box'])
        for box in boxes:
            if box['xPx']+box['widthPx']>packet['image_size'][0] or box['yPx']+box['heightPx']>packet['image_size'][1]:
                raise ValueError('ANNOTATION_BOX_OUT_OF_BOUNDS')
        if complete:
            if row['status']=='ambiguous' or row['container_presence']=='uncertain':raise ValueError('ANNOTATION_UNRESOLVED')
            if (row['container_presence']=='present')!=bool(row['container_box']):raise ValueError('ANNOTATION_CONTAINER_CONTRADICTION')
            if row['status']=='not_found' and (boxes or row['container_presence']!='absent' or
                any(p['status']!='not_found' for p in row['part_regions'])):raise ValueError('ANNOTATION_ABSENCE_CONTRADICTION')
            if row['status']=='located' and (not (row['identity_evidence'] or '').strip() or
                any(p['status']!='located' or not p['regions'] for p in row['part_regions'])):
                raise ValueError('ANNOTATION_TEXT_INCOMPLETE')
    return value


def _commit(packet,state):
    from account_context import get_current_account_id
    state['actor_account_id']=get_current_account_id()
    folder=packet['annotation_dir']
    version=safe(packet['folder'],(folder.relative_to(packet['folder'])/'annotation-versions'/f'{state["revision"]}.json').as_posix())
    if version.exists():raise ValueError('ANNOTATION_VERSION_ALREADY_EXISTS')
    write_json_atomic(version,state)
    write_json_atomic(safe(packet['folder'],(folder.relative_to(packet['folder'])/'annotation-current.json').as_posix()),{'revision':state['revision'],'sha256':sha256_json(state)})


def save_labels(run,command):
    with project_artifact_lock(run):
        packet=case_view(run,command['dataset_id'],command['case_id']);state=packet['state']
        if state['revision']!=command['expected_revision'] or state['source_sha256']!=command['source_sha256']:
            raise ValueError('ANNOTATION_REVISION_OR_SOURCE_CONFLICT')
        if not command['annotator'].strip():raise ValueError('ANNOTATOR_REQUIRED')
        value=validate_mapping(packet,command['mapping'])
        state={'revision':state['revision']+1,'source_sha256':state['source_sha256'],'status':'draft',
               'annotator':command['annotator'].strip(),'mapping':value,'review':None}
        _commit(packet,state)
        return state


def review_labels(run,command):
    with project_artifact_lock(run):
        packet=case_view(run,command['dataset_id'],command['case_id']);state=copy.deepcopy(packet['state'])
        if state['revision']!=command['expected_revision'] or state['source_sha256']!=command['source_sha256']:
            raise ValueError('ANNOTATION_REVISION_OR_SOURCE_CONFLICT')
        reviewer=command['reviewer'].strip()
        if len(command['note'].strip())<8:raise ValueError('ANNOTATION_REVIEW_NOTE_REQUIRED')
        if not reviewer or reviewer.casefold()==(state['annotator'] or '').casefold():raise ValueError('INDEPENDENT_REVIEWER_REQUIRED')
        if state['status']!='draft' or not state['annotator']:raise ValueError('ANNOTATION_DRAFT_REQUIRED')
        if command['decision']=='accept':validate_mapping(packet,state['mapping'],complete=True)
        state.update(revision=state['revision']+1,status='reviewed' if command['decision']=='accept' else 'changes_requested',
            review={'reviewer':reviewer,'decision':command['decision'],'note':command['note'],'draft_revision':state['revision']})
        # Gold is immutable per reviewed revision. Future draft saves retain it.
        if command['decision']=='accept':
            gold={'label_version':packet['dataset']['label_version'],'authority':'independent_human_labels',
                'annotated_by':state['annotator'],'reviewed_by':reviewer,
                'reference_sha256':packet['case']['reference']['sha256'],'targets':{}}
            def rect(b):return [b['xPx'],b['yPx'],b['xPx']+b['widthPx'],b['yPx']+b['heightPx']]
            for row in state['mapping']['targets']:
                gold['targets'][row['targetId']]={'status':row['status'],'container':rect(row['container_box']) if row['container_box'] else None,
                    'parts':{p['partId']:[{'text':r['text'],'box':rect(r['box'])} for r in p['regions']] for p in row['part_regions']}}
            name=safe(packet['folder'],(packet['annotation_dir'].relative_to(packet['folder'])/'annotation-versions'/f'gold-{state["revision"]}.json').as_posix())
            write_json_atomic(name,gold)
            data=copy.deepcopy(packet['dataset'])
            target=next(c for c in data['cases'] if c['id']==command['case_id'])
            target['gold']={'path':name.relative_to(packet['folder']).as_posix(),'sha256':sha256_file(name)}
            # Incomplete other pages are allowed; scoring checks the whole set.
            write_json_atomic(packet['folder']/'dataset.json',data)
        _commit(packet,state)
        return state


def sealed_dataset(run,dataset_id):
    folder,data=load(run,dataset_id)
    for case in data['cases']:
        if case_view(run,dataset_id,case['id'])['state']['status']!='reviewed':raise ValueError('DATASET_HAS_UNREVIEWED_DRAFTS')
    validate_dataset(data,folder)
    return folder,data


def create_dataset(run,command,repo):
    from html_design_candidates import current_design,candidate_directory
    from html_visual_store import scene_path
    from scripts.prepare_reconstruction_dataset import prepare
    with project_artifact_lock(run):
        contracts=read(Path(run)/'planning/visual_contract.json')['slides'];cases=[]
        for sample in command['samples']:
            contract=next((c for c in contracts if c['slide_id']==sample['slide_id']),None)
            if not contract:raise ValueError('PAGE_NOT_FOUND')
            design=current_design(run_dir=run,contract=contract,repo_root=repo)['design']
            if not design or design['stale']:raise ValueError('CURRENT_DESIGN_REQUIRED')
            reference=candidate_directory(run,sample['slide_id'],design['key'])/'design-reference.png'
            case_id='page-'+sha256_json(sample['slide_id'])[:16]
            cases.append({'id':case_id,'course_id':sample['course_id'],'split':sample['split'],
                'reference':reference.relative_to(Path(run)).as_posix(),'scene':scene_path(run,sample['slide_id']).relative_to(Path(run)).as_posix()})
        return prepare({'label_version':'human-reference/1','cases':cases},Path(run),directory(run,command['dataset_id']))
