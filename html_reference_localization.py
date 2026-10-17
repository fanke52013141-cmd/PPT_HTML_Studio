"""Independent reference-image localization; no candidate geometry input."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field

from artifact_fingerprint import sha256_file, sha256_json
from pipeline_lifecycle import write_json_atomic
from html_visual_review_service import HtmlReviewError


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class ReferenceBox(Strict):
    x: int = Field(ge=0,le=1000)
    y: int = Field(ge=0,le=1000)
    width: int = Field(gt=0,le=1000)
    height: int = Field(gt=0,le=1000)


class LocatedTarget(Strict):
    targetId: str
    status: Literal['located','not_found','ambiguous']
    box: ReferenceBox | None
    identity_evidence: str = Field(min_length=1,max_length=300)
    visible_text: str = Field(max_length=300)


class ReferenceLocations(Strict):
    targets: list[LocatedTarget] = Field(max_length=40)


class PixelBox(Strict):
    xPx: int = Field(ge=0)
    yPx: int = Field(ge=0)
    widthPx: int = Field(gt=0)
    heightPx: int = Field(gt=0)


class PixelTarget(Strict):
    targetId: str
    status: Literal['located','not_found','ambiguous']
    box: PixelBox | None
    identity_evidence: str = Field(min_length=1,max_length=300)
    visible_text: str | None = Field(max_length=300)


class PixelLocations(Strict):
    targets: list[PixelTarget] = Field(max_length=40)


class RegionTarget(Strict):
    targetId: str
    status: Literal['located','not_found','ambiguous']
    container_box: PixelBox | None
    text_boxes: list[PixelBox] = Field(max_length=12)
    identity_evidence: str = Field(min_length=1,max_length=300)
    visible_text: str | None = Field(max_length=300)


class RegionLocations(Strict):
    targets: list[RegionTarget] = Field(max_length=40)


class ContainerTarget(RegionTarget):
    container_presence: Literal['present','absent','uncertain']
    identity_evidence: str | None = Field(default=None,max_length=300)


class ContainerLocations(Strict):
    targets: list[ContainerTarget] = Field(max_length=40)


class TextRegion(Strict):
    text: str = Field(min_length=1, max_length=300)
    box: PixelBox


class PartRegion(Strict):
    partId: str
    status: Literal['located','not_found','ambiguous']
    regions: list[TextRegion] = Field(max_length=12)


class MappedTarget(Strict):
    targetId: str
    status: Literal['located','not_found','ambiguous']
    container_presence: Literal['present','absent','uncertain']
    container_box: PixelBox | None
    identity_evidence: str | None = Field(default=None,max_length=300)
    part_regions: list[PartRegion] = Field(max_length=40)


class MappedLocations(Strict):
    targets: list[MappedTarget] = Field(max_length=40)


def text_parts(identity):
    """Stable content paths only; no layout coordinates or inferred OCR."""
    result=[]
    def append(path,value):
        if isinstance(value,str) and value.strip():result.append({'partId':path,'text':value})
    for key in ('number','text','title','description','heading','term','takeaway','label'):
        append(key,identity.get(key))
    for index,run in enumerate(identity.get('runs',[])):
        append(f'runs/{index}',run.get('text'))
    for key in ('from','to'):
        value=identity.get(key)
        append(key+'/text' if isinstance(value,dict) else key,value.get('text') if isinstance(value,dict) else value)
    return result


def reference_targets(scene):
    # Intentionally excludes layout, presentation, actions and HTML geometry.
    fields = ('number','text','runs','title','description','heading','from','to','term','takeaway','label','role')
    return [{'targetId':n['id'],'type':n['type'],
             'region_scope':('complete_card' if n['type']=='card' or n.get('presentation',{}).get('variant','').startswith('text-card-')
                             else 'title_and_number' if n['type']=='header' else 'complete_relation_module' if n['type']=='summary' else 'visible_content'),
             'identity':{k:n[k] for k in fields if k in n}} for n in scene['nodes']]


def mapped_reference_targets(scene):
    return [dict(t,text_parts=text_parts(t['identity'])) for t in reference_targets(scene)]


def validate_mapped_locations(response,targets,image_size):
    """Require every content part, then reuse the existing geometry contract.

    This checks declarations, not whether transcriptions match image pixels.
    Missing/different reference text is rejected rather than copied from input.
    """
    import re
    parsed=MappedLocations.model_validate(response).model_dump()
    expected={t['targetId']:t for t in targets}
    converted=[]
    for row in parsed['targets']:
        if row['targetId'] not in expected:raise ValueError('REFERENCE_LOCALIZATION_INCOMPLETE')
        parts={p['partId']:p['text'] for p in expected[row['targetId']]['text_parts']}
        reported=[p['partId'] for p in row['part_regions']]
        if len(reported)!=len(set(reported)) or set(reported)!=set(parts):
            raise ValueError('REFERENCE_LOCALIZATION_PARTS_INCOMPLETE')
        boxes=[];transcripts=[]
        for part in row['part_regions']:
            located=part['status']=='located'
            if located != bool(part['regions']):raise ValueError('REFERENCE_LOCALIZATION_PART_STATUS_CONTRADICTION')
            if row['status']!='located' and part['regions']:
                raise ValueError('REFERENCE_LOCALIZATION_STATUS_CONTRADICTION')
            if row['status']=='located' and not located:
                raise ValueError('REFERENCE_LOCALIZATION_TEXT_PART_UNLOCATED')
            if located:
                transcript=''.join(r['text'] for r in part['regions'])
                compact=lambda value:re.sub(r'\s+','',value)
                if compact(transcript)!=compact(parts[part['partId']]):
                    raise ValueError('REFERENCE_LOCALIZATION_TEXT_PART_MISMATCH')
                # One identical region cannot stand for two dispersed parts.
                for region in part['regions']:
                    if region['box'] in boxes:raise ValueError('REFERENCE_LOCALIZATION_DUPLICATE_TEXT_BOX')
                    boxes.append(region['box'])
                transcripts.append(transcript)
        converted.append({k:v for k,v in row.items() if k!='part_regions'} |
                         {'text_boxes':boxes,'visible_text':' '.join(transcripts) or None})
    result=validate_region_locations({'targets':converted},targets,image_size,require_container_presence=True)
    for row,original in zip(result['targets'],parsed['targets']):row['part_regions']=original['part_regions']
    return result


def validate_locations(response, targets):
    result = ReferenceLocations.model_validate(response)
    expected = {t['targetId'] for t in targets}
    actual = [t.targetId for t in result.targets]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:
        raise ValueError('REFERENCE_LOCALIZATION_INCOMPLETE')
    for item in result.targets:
        if not item.identity_evidence.strip():
            raise ValueError('REFERENCE_LOCALIZATION_MISSING_IDENTITY')
        if (item.status=='located') != (item.box is not None):
            raise ValueError('REFERENCE_LOCALIZATION_STATUS_CONTRADICTION')
        if item.box and (item.box.x+item.box.width>1000 or item.box.y+item.box.height>1000):
            raise ValueError('REFERENCE_LOCALIZATION_OUT_OF_BOUNDS')
    return result.model_dump()


def validate_pixel_locations(response, targets, image_size):
    result=PixelLocations.model_validate(response)
    actual=[t.targetId for t in result.targets]
    if len(actual)!=len(set(actual)) or set(actual)!={t['targetId'] for t in targets}:
        raise ValueError('REFERENCE_LOCALIZATION_INCOMPLETE')
    for item in result.targets:
        if not item.identity_evidence.strip():raise ValueError('REFERENCE_LOCALIZATION_MISSING_IDENTITY')
        if (item.status=='located') != (item.box is not None):raise ValueError('REFERENCE_LOCALIZATION_STATUS_CONTRADICTION')
        if item.box and (item.box.xPx+item.box.widthPx>image_size[0] or item.box.yPx+item.box.heightPx>image_size[1]):
            raise ValueError('REFERENCE_LOCALIZATION_OUT_OF_BOUNDS')
        if item.status=='located':
            target=next(t for t in targets if t['targetId']==item.targetId)
            if target['type'] in ('text','header','card','summary','label','badge') and not (item.visible_text or '').strip():
                raise ValueError('REFERENCE_LOCALIZATION_MISSING_VISIBLE_TEXT')
        elif item.status=='not_found' and item.visible_text not in (None,''):
            raise ValueError('REFERENCE_LOCALIZATION_ABSENCE_TEXT_CONTRADICTION')
    return result.model_dump()


def validate_region_locations(response, targets, image_size, *, require_container_presence=False):
    """Select the declared scope, never infer text bounds from the background."""
    parsed=(ContainerLocations if require_container_presence else RegionLocations).model_validate(response)
    actual=[t.targetId for t in parsed.targets]
    expected={t['targetId']:t for t in targets}
    if len(actual)!=len(set(actual)) or set(actual)!=set(expected):
        raise ValueError('REFERENCE_LOCALIZATION_INCOMPLETE')
    result=parsed.model_dump()
    text_types=('text','header','card','summary','label','badge')
    for item in result['targets']:
        if not (item['identity_evidence'] or '').strip() and not (require_container_presence and item['status']=='not_found'):
            raise ValueError('REFERENCE_LOCALIZATION_MISSING_IDENTITY')
        container=item['container_box'];lines=item['text_boxes'];target=expected[item['targetId']]
        if require_container_presence:
            presence=item['container_presence']
            if item['status']=='located' and presence=='uncertain':
                raise ValueError('REFERENCE_LOCALIZATION_CONTAINER_UNCERTAIN')
            if (presence=='present') != (container is not None):
                raise ValueError('REFERENCE_LOCALIZATION_CONTAINER_CONTRADICTION')
            if item['status']=='not_found' and presence!='absent':
                raise ValueError('REFERENCE_LOCALIZATION_CONTAINER_CONTRADICTION')
        for box in ([container] if container else [])+lines:
            if box['xPx']+box['widthPx']>image_size[0] or box['yPx']+box['heightPx']>image_size[1]:
                raise ValueError('REFERENCE_LOCALIZATION_OUT_OF_BOUNDS')
        if item['status']!='located':
            if container or lines:raise ValueError('REFERENCE_LOCALIZATION_STATUS_CONTRADICTION')
            if item['status']=='not_found' and item['visible_text'] not in (None,''):
                raise ValueError('REFERENCE_LOCALIZATION_ABSENCE_TEXT_CONTRADICTION')
            item.update(box=None,selected_source=None)
            continue
        if target['type'] in text_types and (not lines or not (item['visible_text'] or '').strip()):
            raise ValueError('REFERENCE_LOCALIZATION_MISSING_TEXT_REGION')
        if container and any(b['xPx']<container['xPx'] or b['yPx']<container['yPx'] or
                             b['xPx']+b['widthPx']>container['xPx']+container['widthPx'] or
                             b['yPx']+b['heightPx']>container['yPx']+container['heightPx'] for b in lines):
            raise ValueError('REFERENCE_LOCALIZATION_TEXT_OUTSIDE_CONTAINER')
        use_container=target['region_scope'] in ('complete_card','complete_relation_module') or target['type'] not in text_types
        if use_container:
            if container is None:raise ValueError('REFERENCE_LOCALIZATION_MISSING_CONTAINER')
            selected=container;source='container_box'
        else:
            left=min(b['xPx'] for b in lines);top=min(b['yPx'] for b in lines)
            right=max(b['xPx']+b['widthPx'] for b in lines);bottom=max(b['yPx']+b['heightPx'] for b in lines)
            selected={'xPx':left,'yPx':top,'widthPx':right-left,'heightPx':bottom-top};source='text_envelope'
        item.update(box=selected,selected_source=source)
    return result


def localize_reference(scene, reference, *, folder, run_dir, deps, checkpoint=lambda:None):
    from html_design_agent import decision
    folder, run = Path(folder).resolve(), Path(run_dir).resolve()
    reference=Path(reference).resolve()
    if not folder.is_relative_to(run) or not reference.is_relative_to(run) or not reference.is_file():
        raise HtmlReviewError('参考定位证据路径无效',code='DESIGN_AGENT_IMAGE_INVALID')
    targets = mapped_reference_targets(scene)
    reference_hash=sha256_file(reference)
    with Image.open(reference) as image:image_size=list(image.size)
    payload = {'reference_targets':targets,'box_coordinates':'original_image_pixels', 'image_size':image_size,
               'task':'Find each identity in the reference image independently; no HTML position is supplied.'}
    scene_hash = sha256_json(scene)
    response, skill = decision('design_reference_localization',payload,[reference],folder=folder,
                               run_dir=run,deps=deps,checkpoint=checkpoint)
    try:
        result = validate_mapped_locations(response,targets,image_size)
    except ValueError as error:
        write_json_atomic(folder/'diagnostic.json',{'code':'REFERENCE_LOCALIZATION_INVALID','message':str(error)[:1200]})
        raise HtmlReviewError('参考定位输出无效，未签发可用区域',code='REFERENCE_LOCALIZATION_INVALID') from error
    if scene_hash != sha256_json(scene):
        raise HtmlReviewError('参考定位对象已变化',code='DESIGN_STALE')
    with Image.open(reference) as image:
        from html_text_edge_verification import verify_text_edges
        edge_verification=verify_text_edges(image,result)
        overlay = image.convert('RGB'); draw=ImageDraw.Draw(overlay)
        for index,item in enumerate(result['targets']):
            if item['status']!='located':continue
            b=item['box']
            rect=(b['xPx'],b['yPx'],b['xPx']+b['widthPx'],b['yPx']+b['heightPx'])
            crop=folder/f'target-{index+1}.png';image.crop(rect).save(crop)
            item.update(pixel_box=list(rect),crop=crop.name,crop_sha256=sha256_file(crop))
            draw.rectangle(rect,outline='red',width=2);draw.text((rect[0]+2,rect[1]+2),str(index+1),fill='red')
        overlay.save(folder/'regions.png')
    if sha256_file(reference)!=reference_hash:
        raise HtmlReviewError('参考定位原图已变化',code='DESIGN_STALE')
    record={'result':result,'runtime_skill':skill,'scene_sha256':scene_hash,
            'edge_verification':edge_verification,
            'reference_sha256':reference_hash,'targets_sha256':sha256_json(targets), 'image_size':image_size,
            'box_coordinates':'original_image_pixels',
            'located':sum(t['status']=='located' for t in result['targets']),
            'quality':'model_proposed_unverified','human_approval':'pending','candidate_geometry_supplied':False}
    from html_text_edge_report import write_text_edge_report
    record['edge_report'] = write_text_edge_report(reference, record, folder/'text-edges.html')
    write_json_atomic(folder/'result.json',record)
    return record
