"""Intrinsic visible-subject diagnostics; no crop, anchor rewrite or approval."""


def asset_geometry_diagnostics(scene, resources):
    assets = {a['id']: a for a in resources.get('assets', [])}
    rows = []
    for node in scene['nodes']:
        if node['type'] != 'image':
            continue
        asset = assets.get(node.get('assetRef', {}).get('id'))
        row = {'targetId': node['id'], 'assetRef': node.get('assetRef'), 'status': 'not_measured'}
        rows.append(row)
        if not asset or not asset.get('size') or not asset.get('alpha_bbox'):
            continue
        w, h = asset['size']['width'], asset['size']['height']
        x, y, right, bottom = asset['alpha_bbox']
        if not (0 <= x < right <= w and 0 <= y < bottom <= h):
            raise ValueError('ASSET_VISIBLE_BOUNDS_INVALID')
        fraction = (right-x)*(bottom-y)/(w*h)
        row.update(status='measured', sha256=asset.get('sha256'),
            source_size=[w, h], visible_size=[right-x, bottom-y],
            visible_bbox_normalized=[x/w, y/h, right/w, bottom/h],
            visible_area_fraction=round(fraction, 6),
            warnings=['small_visible_subject'] if fraction < 0.1 else [],
            anchors=[{'id': a['id'], 'inside_visible_bbox': x <= a['x'] < right and y <= a['y'] < bottom}
                     for a in asset.get('anchors', [])])
    return {'version': 'asset-visible-geometry/0.1.0', 'targets': rows,
            'automatic_crop': False, 'automatic_anchor_change': False, 'visual_approval': False}
