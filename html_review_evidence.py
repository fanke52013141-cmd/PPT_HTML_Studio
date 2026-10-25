"""Bounded local comparison windows; never claim reference object localization."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from artifact_fingerprint import sha256_file, sha256_json
from pipeline_lifecycle import write_json_atomic


def comparison_evidence(scene, reference, screenshot, report, *, folder):
    """At most two PNG sheets within the shared adapter's four-image budget.

    Geometry is in the renderer's 1600x900 coordinates. Reference windows
    use the same normalized coordinates, NOT a detected reference box. The
    full reference must resolve displaced, absent or ambiguous objects.
    """
    folder = Path(folder)
    if len(scene['nodes']) > 40:
        raise ValueError('LOCAL_REVIEW_OBJECT_BUDGET_EXCEEDED')
    folder.mkdir(parents=True, exist_ok=True)
    entries, crops = [], []
    with Image.open(reference) as ref, Image.open(screenshot) as shot:
        ref, shot = ref.convert('RGB'), shot.convert('RGB')
        comparable = all(abs(im.width / im.height - 16 / 9) < 0.02 for im in (ref, shot))
        for index, node in enumerate(scene['nodes']):
            box = report.get('geometry', {}).get(node['id'], {}).get('box')
            entry = {'targetId': node['id'], 'status': 'unavailable',
                     'reason': 'missing_or_invalid_geometry', 'source_box': box}
            entries.append(entry)
            values = [box.get(k) for k in ('x', 'y', 'width', 'height')] if isinstance(box, dict) else []
            if not comparable:
                entry['reason'] = 'canvas_aspect_mismatch'
                continue
            if len(values) != 4 or any(type(v) not in (float, int) or not math.isfinite(v) for v in values):
                entry['source_box'] = None
                continue
            x, y, w, h = values
            if w <= 0 or h <= 0 or x < 0 or y < 0 or x+w > 1600.01 or y+h > 900.01:
                continue
            pad_x, pad_y = max(24, w * 0.12), max(16, h * 0.12)
            window = (max(0, x-pad_x)/1600, max(0, y-pad_y)/900,
                      min(1600, x+w+pad_x)/1600, min(900, y+h+pad_y)/900)
            pair, rects = [], []
            for im in (ref, shot):
                rect = (math.floor(window[0]*im.width), math.floor(window[1]*im.height),
                        math.ceil(window[2]*im.width), math.ceil(window[3]*im.height))
                pair.append(im.crop(rect)); rects.append(list(rect))
            entry.update(status='window_available', reason=None, normalized_window=list(window),
                         reference_pixels=rects[0], current_pixels=rects[1],
                         reference_localization='unverified_same_coordinate_window', label=index+1)
            crops.append((entry, pair))
        paths = []
        # Even forty objects fit two <4M-pixel sheets. No extra model call.
        per_sheet = max(1, math.ceil(len(crops)/2))
        row_height = min(300, 3_900_000 // (1280 * per_sheet))
        for start in range(0, len(crops), per_sheet):
            rows = crops[start:start+per_sheet]
            sheet = Image.new('RGB', (1280, row_height*len(rows)), '#eeeeee')
            draw = ImageDraw.Draw(sheet)
            for row, (entry, pair) in enumerate(rows):
                top = row * row_height
                entry.update(image_index=3+len(paths), row=row+1)
                for column, crop in enumerate(pair):
                    left = column*640
                    draw.text((left+8, top+4), f"{entry['label']} / {'REFERENCE WINDOW' if column == 0 else 'CURRENT HTML'}", fill='black')
                    thumb = ImageOps.contain(crop, (624, row_height-32), Image.Resampling.LANCZOS)
                    sheet.paste(thumb, (left+8+(624-thumb.width)//2, top+26+(row_height-32-thumb.height)//2))
            path = folder / f'comparison-{len(paths)+1}.png'
            sheet.save(path)
            paths.append(path)
    manifest = {'version': '0.1.0', 'scene_sha256': sha256_json(scene),
                'reference_sha256': sha256_file(reference), 'screenshot_sha256': sha256_file(screenshot),
                'coordinate_system': 'renderer_1600x900',
                'reference_localization': 'unverified_same_coordinate_window',
                'status': 'complete_windows' if len(crops) == len(entries) else 'partial_windows',
                'targets': entries,
                'sheets': [{'image_index': i+3, 'path': p.name, 'sha256': sha256_file(p)} for i, p in enumerate(paths)]}
    write_json_atomic(folder/'manifest.json', manifest)
    return manifest, paths


def localized_comparison_evidence(scene, reference, screenshot, report, localization, *, folder):
    """Pair independently located reference boxes with actual HTML object boxes.

    Locations remain model observations, never author coordinates or approval.
    At most eight pairs/two sheets supplement the two full images.
    """
    from html_reference_localization import mapped_reference_targets, validate_mapped_locations
    expected = {t['targetId']: t for t in mapped_reference_targets(scene)}
    if (localization.get('scene_sha256') != sha256_json(scene)
        or localization.get('reference_sha256') != sha256_file(reference)
        or localization.get('candidate_geometry_supplied') is not False):
        raise ValueError('REFERENCE_COMPARISON_SOURCE_MISMATCH')
    rows = localization['result']['targets']
    if any(r.get('targetId') not in expected for r in rows):
        raise ValueError('REFERENCE_COMPARISON_TARGETS_MISMATCH')
    keys = ('targetId', 'status', 'container_presence', 'container_box', 'identity_evidence', 'part_regions')
    targets = [expected[r['targetId']] for r in rows]
    with Image.open(reference) as source:
        size = list(source.size)
    if (size != localization.get('image_size')
        or sha256_json(targets) != localization.get('targets_sha256')):
        raise ValueError('REFERENCE_COMPARISON_TARGETS_MISMATCH')
    validated = validate_mapped_locations({'targets': [{k: r[k] for k in keys} for r in rows]}, targets, size)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    entries, pairs, paths = [], [], []
    priority = {target for issue in report.get('geometry_preflight', {}).get('issues', [])
                for target in issue.get('targets', [])}
    pair_candidates = []
    with Image.open(reference) as ref, Image.open(screenshot) as shot:
        ref, shot = ref.convert('RGB'), shot.convert('RGB')
        for row in validated['targets']:
            entry = {'targetId': row['targetId'], 'status': row['status'],
                     'reference_source': row.get('selected_source'), 'html_scope': 'actual_object_box',
                     'quality': 'model_proposed_unverified'}
            entries.append(entry)
            if row['status'] != 'located':
                continue
            box = row['box']
            current = report.get('geometry', {}).get(row['targetId'], {}).get('box')
            if not current or any(type(current.get(k)) not in (float, int) or not math.isfinite(current[k]) for k in ('x','y','width','height')):
                entry['status'] = 'html_geometry_unavailable'
                continue
            x,y,w,h = (current[k] for k in ('x','y','width','height'))
            if w <= 0 or h <= 0 or x < 0 or y < 0 or x+w > 1600.01 or y+h > 900.01:
                entry['status'] = 'html_geometry_unavailable'
                continue
            a = [box['xPx'], box['yPx'], box['xPx']+box['widthPx'], box['yPx']+box['heightPx']]
            b = [math.floor(x*shot.width/1600), math.floor(y*shot.height/900),
                 math.ceil((x+w)*shot.width/1600), math.ceil((y+h)*shot.height/900)]
            entry.update(reference_pixels=a, current_pixels=b,
                         center_delta_normalized={'x': (x+w/2)/1600-(box['xPx']+box['widthPx']/2)/ref.width,
                                                  'y': (y+h/2)/900-(box['yPx']+box['heightPx']/2)/ref.height},
                         part_ids=[p['partId'] for p in row['part_regions']])
            displacement = sum(abs(v) for v in entry['center_delta_normalized'].values())
            pair_candidates.append(((row['targetId'] not in priority, -displacement, row['targetId']), entry, a, b))
        for index, (_, entry, a, b) in enumerate(sorted(pair_candidates, key=lambda item: item[0])):
            if index < 8:
                pairs.append((entry, [ref.crop(a), shot.crop(b)]))
            else:
                entry['sheet_status'] = 'not_selected_full_images_remain_available'
        for start in range(0, len(pairs), 4):
            selected = pairs[start:start+4]
            sheet = Image.new('RGB', (1280, len(selected)*260), '#eeeeee')
            draw = ImageDraw.Draw(sheet)
            for i, (entry, crops) in enumerate(selected):
                entry.update(image_index=3+len(paths), row=i+1)
                for j, crop in enumerate(crops):
                    draw.text((j*640+8,i*260+4), f"{start+i+1}: {'REFERENCE' if j==0 else 'HTML'}", fill='black')
                    thumb = ImageOps.contain(crop, (624,224), Image.Resampling.LANCZOS)
                    sheet.paste(thumb, (j*640+8+(624-thumb.width)//2,i*260+28+(224-thumb.height)//2))
            path = folder / f'localized-{len(paths)+1}.png'
            sheet.save(path)
            paths.append(path)
    manifest = {'version':'0.2.0', 'scene_sha256':sha256_json(scene),
                'reference_sha256':sha256_file(reference),'screenshot_sha256':sha256_file(screenshot),
                'reference_localization':'independent_model_observation', 'automatic_geometry_apply':False,
                'selection_policy':'geometry_issues_then_normalized_displacement_then_identity',
                'unresolved_targets':[e['targetId'] for e in entries if e['status']!='located'],
                'targets':entries, 'sheets':[{'path':p.name,'sha256':sha256_file(p)} for p in paths]}
    write_json_atomic(folder/'manifest.json',manifest)
    return manifest, paths
