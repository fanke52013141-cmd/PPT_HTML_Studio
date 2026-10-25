"""Seal local course samples and create human-label drafts without model calls."""
import argparse
import json
from pathlib import Path
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from artifact_fingerprint import sha256_file  # noqa:E402
from html_acceptance_criteria import safe  # noqa:E402
from html_reference_localization import mapped_reference_targets  # noqa:E402
from pipeline_lifecycle import write_json_atomic  # noqa:E402


def prepare(spec,source_root,output):
    if output.exists():raise ValueError('DATASET_OUTPUT_ALREADY_EXISTS')
    cases=spec['cases'];ids=[c['id'] for c in cases]
    if not cases or len(cases)>2000 or len(set(ids))!=len(ids):raise ValueError('DATASET_CASES_INVALID')
    courses={};hashes=set();prepared=[]
    for case in cases:
        # IDs become filenames; reject traversal before creating any outputs.
        import re
        if not re.fullmatch('[a-z][a-z0-9-]{0,63}',case['id']):raise ValueError('CASE_ID_INVALID')
        if case['split'] not in ('development','holdout') or not case['course_id']:raise ValueError('SPLIT_INVALID')
        if courses.setdefault(case['course_id'],case['split'])!=case['split']:raise ValueError('COURSE_SPLIT_LEAKAGE')
        ref=safe(source_root,case['reference']);scene_path=safe(source_root,case['scene'])
        with Image.open(ref) as image:
            if image.format!='PNG' or image.width*image.height>16000000:raise ValueError('REFERENCE_FORMAT_OR_SIZE_INVALID')
            image.verify()
        digest=sha256_file(ref)
        if digest in hashes:raise ValueError('DUPLICATE_REFERENCE_LEAKAGE')
        hashes.add(digest)
        scene=json.loads(scene_path.read_text(encoding='utf-8'));targets=mapped_reference_targets(scene)
        if not targets:raise ValueError('NO_LABEL_TARGETS')
        prepared.append((case,ref,scene_path,targets,digest))
    output.mkdir(parents=True)
    entries=[]
    for case,ref,scene,targets,digest in prepared:
        folder=output/case['id'];folder.mkdir()
        (folder/'reference.png').write_bytes(ref.read_bytes());(folder/'scene.json').write_bytes(scene.read_bytes())
        write_json_atomic(folder/'labels.json',{'label_version':spec['label_version'],'authority':'pending_human_labels',
            'reference_sha256':digest,'annotated_by':None,'targets':{t['targetId']:{'status':'ambiguous','container':None,
                'parts':{p['partId']:[{'text':p['text'],'box':None}] for p in t['text_parts']}} for t in targets},
            'instructions':'Check reference only. Enter actual line transcriptions and [left,top,right,bottom] pixel boxes; mark status explicitly. Set authority independent_human_labels only after real annotation. Preserve exact reference hash; never use current HTML geometry as gold.'})
        def record(name):
            path=folder/name;return {'path':path.relative_to(output).as_posix(),'sha256':sha256_file(path)}
        entries.append({**{k:case[k] for k in ('id','course_id','split')},'reference':record('reference.png'),
                        'scene':record('scene.json'),'gold':record('labels.json')})
    dataset={'format':'hps.paired-dataset/0.1.0','label_version':spec['label_version'],
             'provenance':'local_samples_pending_human_labels','cases':entries}
    write_json_atomic(output/'dataset.json',dataset)
    return dataset


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path);parser.add_argument('--source-root',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--seal-labels',type=Path,help='Validate annotated labels and refresh only their hashes')
    args=parser.parse_args()
    if args.seal_labels:
        from html_paired_evaluation import validate_dataset
        path=args.seal_labels.resolve();result=json.loads(path.read_text(encoding='utf-8'))
        for case in result['cases']:
            case['gold']['sha256']=sha256_file(safe(path.parent,case['gold']['path']))
        validate_dataset(result,path.parent)
        write_json_atomic(path,result);print({'labels':'sealed','provider_calls':0});return
    if not all((args.spec,args.source_root,args.output)):parser.error('--spec --source-root --output are required')
    result=prepare(json.loads(args.spec.read_text(encoding='utf-8')),args.source_root,args.output)
    print({'cases':len(result['cases']),'labels':'pending_human_labels','provider_calls':0})


if __name__=='__main__':main()
