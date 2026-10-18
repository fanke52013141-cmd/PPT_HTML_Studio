"""Conservative pixel evidence at proposed text edges; never OCR or box repair.

Only foreground connected across the original boundary is considered. Detached
icons/lines are not absorbed. A quiet edge does not establish text completeness.
"""
from __future__ import annotations

from collections import deque

import numpy as np

POLICY = 'reference-text-edge/0.1.0'
MAX_WINDOW_PIXELS = 500_000
MAX_COMPONENT_PIXELS = 100_000
MAX_BOUNDARY_COMPONENTS = 64


def _rect(box):
    return [box['xPx'],box['yPx'],box['xPx']+box['widthPx'],box['yPx']+box['heightPx']]


def _intersects(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]


def inspect_text_edge(image, box, *, container=None, neighbours=()):
    """Inspect a single original-image pixel box without changing it.

    Pixel thresholds are diagnostic policy, independent of benchmark gold.
    Returns possible_clip / uncertain / no_detected_clip, never 'passed'.
    """
    width,height=image.size
    values=[box.get(k) for k in ('xPx','yPx','widthPx','heightPx')]
    if any(type(v) is not int for v in values) or min(values[:2])<0 or min(values[2:])<=0:
        raise ValueError('TEXT_EDGE_INVALID_BOX')
    rect=_rect(box);x0,y0,x1,y1=rect
    if x1>width or y1>height:raise ValueError('TEXT_EDGE_INVALID_BOX')
    margin=max(4,min(32,round(box['heightPx']*.35)))
    window=[max(0,x0-margin),max(0,y0-margin),min(width,x1+margin),min(height,y1+margin)]
    reasons=[]
    if window[0]==x0 or window[1]==y0 or window[2]==x1 or window[3]==y1:
        reasons.append('image_edge_unobservable')
    if container:
        if not (container[0]<=x0<x1<=container[2] and container[1]<=y0<y1<=container[3]):
            raise ValueError('TEXT_EDGE_OUTSIDE_CONTAINER')
        # Do not use the declared container to crop away potentially clipped ink.
        if min(x0-container[0],y0-container[1],container[2]-x1,container[3]-y1)<margin:
            reasons.append('container_edge_nearby')
    base={'box':dict(box),'window':window,'margin_pixels':margin,'components':[],
          'identity_verified':False,'box_changed':False}
    if (window[2]-window[0])*(window[3]-window[1])>MAX_WINDOW_PIXELS:
        return base|{'status':'uncertain','reasons':['window_budget_exceeded']}
    crop=image.crop(window)
    if 'A' in crop.getbands() and crop.getchannel('A').getextrema()[0]<255:
        return base|{'status':'uncertain','reasons':reasons+['transparent_background']}
    pixels=np.asarray(crop.convert('RGB'),dtype=np.int16)
    # Dominant quantized colour is a local flat-background hypothesis, not a
    # white-background assumption. Nonuniform/low-contrast evidence abstains.
    bins=(pixels//16).astype(np.int32)
    keys=bins[:,:,0]*256+bins[:,:,1]*16+bins[:,:,2]
    counts=np.bincount(keys.ravel(),minlength=4096);dominant=int(counts.argmax())
    background=np.median(pixels[keys==dominant],axis=0)
    distance=np.max(np.abs(pixels-background),axis=2)
    uniform=float(np.mean(distance<=16))
    base.update(background_rgb=[int(v) for v in background],background_fraction=round(uniform,4))
    if uniform<.55:
        return base|{'status':'uncertain','reasons':reasons+['nonuniform_background']}
    ink=distance>=32
    left,top,right,bottom=x0-window[0],y0-window[1],x1-window[0],y1-window[1]
    inside=ink[top:bottom,left:right]
    density=float(np.mean(inside))
    if density<.005 or density>.65:
        return base|{'status':'uncertain','reasons':reasons+['insufficient_or_dense_foreground']}
    boundary=np.zeros_like(ink)
    boundary[top,left:right]=True;boundary[bottom-1,left:right]=True
    boundary[top:bottom,left]=True;boundary[top:bottom,right-1]=True
    seeds=np.argwhere(ink & boundary);seen=np.zeros_like(ink)
    suspicious=[];noise=False;component_count=0
    for sy,sx in seeds:
        sy,sx=int(sy),int(sx)
        if seen[sy,sx]:continue
        component_count+=1
        if component_count>MAX_BOUNDARY_COMPONENTS:
            return base|{'status':'uncertain','reasons':reasons+['boundary_component_budget_exceeded']}
        queue=deque([(sy,sx)]);seen[sy,sx]=True
        count=outside=0;minx=maxx=sx;miny=maxy=sy;sides=set()
        while queue:
            y,x=queue.popleft();count+=1
            if count>MAX_COMPONENT_PIXELS:
                return base|{'status':'uncertain','reasons':reasons+['component_budget_exceeded']}
            minx=min(minx,x);maxx=max(maxx,x);miny=min(miny,y);maxy=max(maxy,y)
            if x<left or y<top or x>=right or y>=bottom:
                outside+=1
                if x<left:sides.add('left')
                if x>=right:sides.add('right')
                if y<top:sides.add('top')
                if y>=bottom:sides.add('bottom')
            for dy,dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
                ny,nx=y+dy,x+dx
                if 0<=ny<ink.shape[0] and 0<=nx<ink.shape[1] and ink[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx]=True;queue.append((ny,nx))
        if not outside:
            noise=True # Ink touches a boundary; absence of strong outside pixels is inconclusive.
            continue
        if count-outside<3 or outside<2:
            noise=True;continue
        component=[minx+window[0],miny+window[1],maxx+1+window[0],maxy+1+window[1]]
        cw,ch=component[2]-component[0],component[3]-component[1]
        uncertain=[]
        if minx==0 or miny==0 or maxx==ink.shape[1]-1 or maxy==ink.shape[0]-1:
            uncertain.append('component_leaves_window')
        if cw>2*box['heightPx'] and ch<=max(3,.18*box['heightPx']):
            uncertain.append('rule_or_underline')
        if count/(cw*ch)>.7 and cw*ch>.4*box['heightPx']**2:
            uncertain.append('dense_shape_or_icon')
        if container and not (container[0]<=component[0] and container[1]<=component[1] and
                              component[2]<=container[2] and component[3]<=container[3]):
            uncertain.append('component_outside_container')
        if any(_intersects(component,other) for other in neighbours):
            uncertain.append('neighbour_region_intersection')
        entry={'ink_bounds':component,'foreground_pixels':count,'outside_pixels':outside,
               'sides':sorted(sides),'uncertainties':uncertain}
        base['components'].append(entry)
        if uncertain:reasons.extend(uncertain)
        else:suspicious.append(entry)
    if suspicious and not reasons:
        return base|{'status':'possible_clip','reasons':['connected_ink_crosses_box']}
    if suspicious:reasons.append('connected_ink_crosses_box_with_ambiguity')
    if noise:reasons.append('ink_touches_boundary')
    return base|{'status':'uncertain' if reasons else 'no_detected_clip','reasons':sorted(set(reasons))}


def verify_text_edges(image, result):
    """Attachable diagnostic over validated model regions; preserve result exactly."""
    regions=[]
    for target in result['targets']:
        if target['status']!='located':continue
        for part in target.get('part_regions',[]):
            for index,region in enumerate(part['regions']):
                regions.append((target,part['partId'],index,region['box']))
    rows=[]
    for target,part,index,box in regions:
        neighbours=[_rect(other) for _,_,_,other in regions if other is not box]
        container=_rect(target['container_box']) if target.get('container_box') else None
        checked=inspect_text_edge(image,box,container=container,neighbours=neighbours)
        rows.append({'targetId':target['targetId'],'partId':part,'region_index':index}|checked)
    counts={status:sum(r['status']==status for r in rows)
            for status in ('possible_clip','uncertain','no_detected_clip')}
    return {'policy':POLICY,'status':'needs_review' if counts['possible_clip'] else
            'uncertain' if counts['uncertain'] or not rows else 'no_detected_clip',
            'counts':counts,'regions':rows,'automatic_review_eligible':False,
            'identity_verified':False,'boxes_changed':False,
            'limit':'Connected pixels are not OCR; detached missing glyphs and wrong identity may remain undetected.'}
