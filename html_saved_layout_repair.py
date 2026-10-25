"""Saved-page adapter around the original unsaved layout solver and candidate guard."""
import copy
from pathlib import Path
from html_linked_layout import solve_production_layout
from html_visual_review_service import HtmlReviewDependencies
import html_scene_editing as editor
import html_scene_repair as repair

INSTRUCTION='仅修复所选对象的容量、遮挡和关联布局；保留原文、关系、动作与人工保护。'


def operations_between(before, after):
    operations=[]
    old={n['id']:n for n in before['nodes']}
    for node in after['nodes']:
        previous=old[node['id']]
        p,q=previous.get('presentation',{}),node.get('presentation',{})
        if q.get('variant') and (q.get('variant')!=p.get('variant') or node.get('icon')!=previous.get('icon')):
            values={'variant':q['variant']}
            if node.get('icon')!=previous.get('icon'):values['icon']=node['icon']
            operations.append({'targetId':node['id'],'kind':'set_variant','values':values})
        values={k:q[k] for k in ('offsetX','offsetY','width','height') if k in q and q[k]!=p.get(k)}
        if values:operations.append({'targetId':node['id'],'kind':'set_presentation','values':values})
        for part,style in q.get('typography',{}).items():
            changes={k:v for k,v in style.items() if v!=p.get('typography',{}).get(part,{}).get(k)}
            if changes:operations.append({'targetId':node['id'],'kind':'set_text_style','part':part,'values':changes})
        points={side:node[side]['point'] for side in ('from','to') if node.get(side,{}).get('point')
                and node[side]['point']!=previous.get(side,{}).get('point')}
        if points:operations.append({'targetId':node['id'],'kind':'set_endpoint_point','values':points})
    return operations


def generate(run, slide, request):
    doc=repair._revision(run,slide,request['expected_revision'])
    original=copy.deepcopy(doc)
    audio=request.get('expected_audio_revision') or editor.audio_revision(run,slide)
    editor._check_audio_revision(run,slide,audio)
    result=solve_production_layout(doc['scene'],doc['binding'],run_dir=run,
        deps=HtmlReviewDependencies(Path(__file__).resolve().parent,lambda **kw:None),
        manual=doc['manual'],beats=doc.get('beats'),allowed_scope=request['scope'])
    if editor.load_editor(run,slide)!=original:
        raise editor.SceneEditError('REPAIR_SOURCE_CHANGED','原页面已变化')
    editor._check_audio_revision(run,slide,audio)
    path={'strategy':'layout_first','origin':'shared_layout_solver','summary':result['summary']}
    if result['summary']['status']!='candidate':
        return {'status':result['summary']['status'],'reason':result['summary']['reason'],
                'review':result['report'],'repair_path':path,'changes':[]}
    operations=operations_between(doc['scene'],result['scene'])
    body={k:v for k,v in request.items() if k in repair.TemporalRequest.model_fields}
    body.update(operations=operations,scope=request['scope'],source='ai',expected_audio_revision=audio,
                sampling_mode='output_frames',overlap_policy='registered',fps=30,time_range_ms=None)
    candidate=repair.preview_repair(run,slide,body)
    return {**candidate,'repair_path':path,'changes':operations}
