import copy

from checks.test_html_candidate_capacity_solver import ROOT, document
import html_capacity_repair as capacity
from html_visual_review_service import HtmlReviewDependencies


def test_duplicate_and_noop_candidates_do_not_consume_search_quota(tmp_path, monkeypatch):
    scene = document()
    scene['nodes'][0]['presentation'] = {'height': 100}
    def review(candidate, **kwargs):
        fixed = candidate['nodes'][0]['presentation']['height'] == 200
        return {'passed': fixed, 'capacityIssues': [] if fixed else [{'target':'header', 'triggers':[]}],
                'geometry_preflight': {'passed': fixed}}
    monkeypatch.setattr(capacity, 'review_scene', review)
    op = lambda value: [{'targetId':'header','kind':'set_presentation','values':{'height':value}}]
    monkeypatch.setattr(capacity, 'capacity_candidates', lambda *a: [op(100)]*5+[op(200)])
    original = copy.deepcopy(scene)
    result = capacity.solve_capacity_candidate(scene, None, run_dir=tmp_path, deps=HtmlReviewDependencies(ROOT, lambda **kw: {}))
    assert result['summary']['status'] == 'candidate'
    assert result['summary']['measured_states'] == 3
    assert scene == original


def test_net_patch_merges_properties_but_keeps_parts_separate():
    operations = [{'targetId':'a','kind':'set_text_style','part':'body','values':{'fontSizePx':32,'lineHeight':1.2}},
                  {'targetId':'a','kind':'set_text_style','part':'title','values':{'fontSizePx':40}}]
    operations += [{'targetId':'a','kind':'set_text_style','part':'body','values':{'fontSizePx':size}} for size in range(31, 23, -1)]
    before = copy.deepcopy(operations)
    net = capacity.net_operations(operations)
    assert len(net) == 2 and net[0]['values'] == {'fontSizePx':24,'lineHeight':1.2}
    assert operations == before
