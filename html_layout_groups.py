"""Position-only packing inferred from registered, non-overlapping slot rows.

No font/content/size/relationship changes. The editor protection and original
whole-scene temporal QA remain mandatory after every proposed transaction.
"""
from __future__ import annotations


def registered_row_candidates(scene, layout, affected):
    nodes = scene['nodes']
    boxes = {n['id']: layout['slots'][n['slot']]['box'] for n in nodes}
    cards = [n for n in nodes if n['type'] == 'card']
    groups = []
    if 2 <= len(cards) <= 4:
        groups.append(cards)
    images = [n for n in nodes if n['type'] == 'image']
    texts = [n for n in nodes if n['type'] in ('text', 'card')]
    # A mixed row requires explicit same-row, disjoint registered regions.
    for image in images:
        for text in texts:
            if abs(boxes[image['id']]['y'] - boxes[text['id']]['y']) <= 1:
                groups.append([image, text])
    proposals = []
    for group in groups:
        if not affected.intersection(n['id'] for n in group):
            continue
        rows = []
        for node in sorted(group, key=lambda n: (boxes[n['id']]['y'], boxes[n['id']]['x'], n['id'])):
            box = boxes[node['id']]
            if not rows or abs(box['y']-boxes[rows[-1][0]['id']]['y']) > 1:
                rows.append([])
            rows[-1].append(node)
        # Vertical-only columns are handled by the existing column policy.
        if all(len(row) == 1 for row in rows):
            continue
        valid = True
        for i, row in enumerate(rows):
            for left, right in zip(row, row[1:]):
                a, b = boxes[left['id']], boxes[right['id']]
                if a['x'] + a['width'] > b['x']:
                    valid = False
            if i and max(boxes[n['id']]['y']+boxes[n['id']]['height'] for n in rows[i-1]) > boxes[row[0]['id']]['y']:
                valid = False
        if not valid:
            continue
        operations, previous_bottom = [], None
        for row in rows:
            y = max(boxes[n['id']]['y']+n.get('presentation', {}).get('offsetY', 0) for n in row)
            if previous_bottom is not None:
                y = max(y, previous_bottom + 12)
            right_edge, bottom = None, y
            for node in row:
                box, p = boxes[node['id']], node.get('presentation', {})
                x = box['x']+p.get('offsetX', 0)
                if right_edge is not None:
                    x = max(x, right_edge + 12)
                w, h = p.get('width', box['width']), p.get('height', box['height'])
                if x < 0 or x+w > 1600 or y < 0 or y+h > 800 or abs(x-box['x']) > 400 or abs(y-box['y']) > 400:
                    valid = False
                values = {k: round(v, 3) for k, v, old in (
                    ('offsetX', x-box['x'], p.get('offsetX', 0)),
                    ('offsetY', y-box['y'], p.get('offsetY', 0))) if v != old}
                if values:
                    operations.append({'targetId': node['id'], 'kind': 'set_presentation', 'values': values})
                right_edge, bottom = x+w, max(bottom, y+h)
            previous_bottom = bottom
        if valid and operations:
            proposals.append(operations)
    expanded=[]
    for operations in proposals:
        expanded.append(operations)
        moves={o['targetId']:o['values'] for o in operations}
        bottom=max((boxes[n['id']]['y']+moves.get(n['id'],{}).get('offsetY',n.get('presentation',{}).get('offsetY',0))
                    +n.get('presentation',{}).get('height',boxes[n['id']]['height']) for n in cards),default=0)
        summaries=[n for n in nodes if n['type']=='summary' and boxes[n['id']]['y']>=
                   max((boxes[c['id']]['y']+boxes[c['id']]['height'] for c in cards),default=800)]
        for summary in summaries[:1]:
            box=boxes[summary['id']];p=summary.get('presentation',{})
            y=max(box['y']+p.get('offsetY',0),bottom+12)
            if y!=box['y']+p.get('offsetY',0) and y+p.get('height',box['height'])<=800 and abs(y-box['y'])<=400:
                combined=operations+[{'targetId':summary['id'],'kind':'set_presentation','values':{'offsetY':round(y-box['y'],3)}}]
                if len({o['targetId'] for o in combined})<=4:expanded.insert(0,combined)
    return expanded + mixed_layout_candidates(scene, layout, affected)


def mixed_layout_candidates(scene, layout, affected):
    """Separate originally disjoint image/text regions along their original axis.

    Staggered baselines are allowed; existing image frames, anchors, neighboring
    text and animated positions are still checked by the full original QA.
    Both one-object alternatives are offered rather than blindly pushing the
    image out of its registered container.
    """
    boxes = {n['id']:layout['slots'][n['slot']]['box'] for n in scene['nodes']}
    images = [n for n in scene['nodes'] if n['type'] in ('image','figure')]
    texts = [n for n in scene['nodes'] if n['type'] in ('text','card')]
    proposals = []
    for image in images:
        for text in texts:
            if not affected.intersection((image['id'], text['id'])):
                continue
            a, b = boxes[image['id']], boxes[text['id']]
            horizontal = min(a['y']+a['height'], b['y']+b['height']) > max(a['y'], b['y'])
            vertical = min(a['x']+a['width'], b['x']+b['width']) > max(a['x'], b['x'])
            if horizontal and (a['x']+a['width'] <= b['x'] or b['x']+b['width'] <= a['x']):
                axis, size, offset = 'x', 'width', 'offsetX'
            elif vertical and (a['y']+a['height'] <= b['y'] or b['y']+b['height'] <= a['y']):
                axis, size, offset = 'y', 'height', 'offsetY'
            else:
                continue  # Overlapping decorations/containers are not a pair.
            first, second = sorted((image,text), key=lambda n:boxes[n['id']][axis])
            def current(node, key, shift):
                return boxes[node['id']][key]+node.get('presentation', {}).get(shift,0)
            start = current(first,axis,offset)
            end = start+first.get('presentation',{}).get(size,boxes[first['id']][size])
            next_start = current(second,axis,offset)
            # Only actual intersection on both axes needs displacement.
            other, other_size, other_offset = ('y','height','offsetY') if axis=='x' else ('x','width','offsetX')
            other_ends = [current(n,other,other_offset)+n.get('presentation',{}).get(other_size,boxes[n['id']][other_size]) for n in (first,second)]
            if end <= next_start or min(other_ends) <= max(current(n,other,other_offset) for n in (first,second)):
                continue
            delta = end-next_start+12
            for node, shift in ((first,-delta),(second,delta)):
                p = node.get('presentation',{})
                value = p.get(offset,0)+shift
                x = boxes[node['id']]['x']+(value if axis=='x' else p.get('offsetX',0))
                y = boxes[node['id']]['y']+(value if axis=='y' else p.get('offsetY',0))
                if (abs(value)>400 or x<0 or y<0 or x+p.get('width',boxes[node['id']]['width'])>1600
                    or y+p.get('height',boxes[node['id']]['height'])>800):
                    continue
                proposals.append([{'targetId':node['id'],'kind':'set_presentation','values':{offset:round(value,3)}}])
    return proposals
