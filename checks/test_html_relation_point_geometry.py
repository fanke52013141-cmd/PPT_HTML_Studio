import copy
import math

import pytest

from scripts.diagnose_html_relation_points import absolute, diagnose, direction, proposed_points


SOURCE = {'x':1015, 'y':300, 'width':490, 'height':340}
TARGET = {'x':954, 'y':180, 'width':581, 'height':474}


@pytest.mark.parametrize('angle', [-90, -45, 0, 45, 90, 135, 180, -135])
def test_off_center_nested_boxes_produce_declared_direction(angle):
    points = proposed_points(SOURCE, TARGET, angle)
    start, end = absolute(SOURCE, points['fromPoint']), absolute(TARGET, points['toPoint'])
    result = direction(start, end, angle)
    assert result['passed'] and result['angle_error'] < 1e-8
    assert result['length'] > 20
    # Independent signed dot/cross checks, including vertical and horizontal rays.
    vector = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    assert result['dx'] * vector[0] + result['dy'] * vector[1] > 0
    assert abs(result['dx'] * vector[1] - result['dy'] * vector[0]) < 1e-8


def test_same_local_point_is_not_same_absolute_direction_and_zero_length_fails():
    start, end = absolute(SOURCE, {'x':.5,'y':1}), absolute(TARGET, {'x':.5,'y':1})
    assert not direction(start, end, 90)['passed']
    assert not direction((1,1), (1,1), 0)['passed']
    with pytest.raises(ValueError, match='containing'):
        proposed_points(TARGET, SOURCE, 90)


@pytest.mark.parametrize('bad', [True, float('nan'), float('inf'), '0'])
def test_non_numeric_or_nonfinite_point_rejected(bad):
    with pytest.raises(ValueError):
        absolute(SOURCE, {'x':bad,'y':.5})


def test_diagnostic_keeps_original_plan_and_only_reports_proposals():
    plan = {'objects':[{'id':'subject','kind':'image','slot':'subject'},
                       {'id':'frame','kind':'figure','slot':'frame'},
                       {'id':'relation','kind':'arrow','slot':'relation'}],
            'slots':{'relation':{'from':{'objectId':'subject','point':{'x':.5,'y':1}},
                                 'to':{'objectId':'frame','point':{'x':.5,'y':1}}}}}
    before = copy.deepcopy(plan)
    report = diagnose(plan, {'slots':{'subject':{'box':SOURCE},'frame':{'box':TARGET}}}, {'relation':90})
    assert report['relations'][0]['actual']['passed'] is False
    assert 'proposed_points' in report['relations'][0]
    assert report['author_saved'] is False and report['provider_calls'] == 0
    assert plan == before
    with pytest.raises(ValueError, match='nonempty'):
        diagnose(plan, {}, {})
