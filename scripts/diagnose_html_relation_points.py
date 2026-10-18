"""Read-only relation geometry diagnostics against explicitly supplied directions."""
import argparse
import json
import math
from pathlib import Path


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Expected a finite number')
    return value


def box_for(plan, layout, object_id):
    obj = next(o for o in plan['objects'] if o['id'] == object_id)
    box = layout['slots'][obj['slot']]['box']
    if any(number(box[k]) <= 0 for k in ('width', 'height')):
        raise ValueError('Endpoint boxes must have positive dimensions')
    for key in ('x', 'y'):
        number(box[key])
    return box


def absolute(box, point):
    if set(point) != {'x', 'y'} or any(not 0 <= number(point[k]) <= 1 for k in point):
        raise ValueError('Expected normalized point coordinates')
    return (box['x'] + box['width'] * point['x'], box['y'] + box['height'] * point['y'])


def direction(start, end, expected):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx)) if length else None
    error = abs((angle - expected + 180) % 360 - 180) if angle is not None else None
    return {'dx': dx, 'dy': dy, 'length': length, 'angle': angle,
            'angle_error': error, 'passed': length > 1 and error <= 22.5}


def proposed_points(source, target, angle):
    if any(source[k] < target[k] or source[k] + source[size] > target[k] + target[size]
           for k, size in (('x', 'width'), ('y', 'height'))):
        raise ValueError('Radial proposal requires a containing target box')
    origin = (source['x'] + source['width'] / 2, source['y'] + source['height'] / 2)
    vector = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    def limit(box):
        distances = []
        for i, (key, size) in enumerate((('x', 'width'), ('y', 'height'))):
            if abs(vector[i]) > 1e-12:
                edge = box[key] + box[size] if vector[i] > 0 else box[key]
                distances.append((edge - origin[i]) / vector[i])
        return min(distances)
    result = []
    for box, distance in ((source, limit(source) * .6), (target, limit(target) * .96)):
        point = {key: (origin[i] + vector[i] * distance - box[key]) / box[size]
                 for i, (key, size) in enumerate((('x', 'width'), ('y', 'height')))}
        absolute(box, point)  # Reject rather than clamp an invalid proposal.
        result.append(point)
    if not direction(absolute(source, result[0]), absolute(target, result[1]), angle)['passed']:
        raise ValueError('Proposed points do not satisfy the declared direction')
    return {'fromPoint': result[0], 'toPoint': result[1]}


def diagnose(plan, layout, expected):
    if not isinstance(expected, dict) or not expected:
        raise ValueError('Explicit nonempty direction declarations are required')
    objects = {o['id']: o for o in plan['objects']}
    rows = []
    for identity, angle in expected.items():
        angle = number(angle)
        obj = objects[identity]
        if obj['kind'] != 'arrow':
            raise ValueError('Declared direction must refer to an arrow')
        relation = plan['slots'][obj['slot']]
        boxes, points = [], []
        for end in ('from', 'to'):
            endpoint = relation[end]
            if set(endpoint) != {'objectId', 'point'}:
                raise ValueError('Only explicit object-local point endpoints are supported')
            box = box_for(plan, layout, endpoint['objectId'])
            boxes.append(box)
            points.append(absolute(box, endpoint['point']))
        row = {'objectId': identity, 'declared_angle': angle,
               'actual': direction(*points, angle)}
        try:
            row['proposed_points'] = proposed_points(*boxes, angle)
        except ValueError as error:
            row['proposal_unavailable'] = str(error)
        rows.append(row)
    return {'author_saved': False, 'provider_calls': 0, 'geometry_only': True,
            'declarations_are_not_inferred': True, 'relations': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'layout', 'directions', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in (args.plan, args.layout, args.directions)}:
        parser.error('The report cannot overwrite an input')
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))
    result = diagnose(read(args.plan), read(args.layout), read(args.directions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
