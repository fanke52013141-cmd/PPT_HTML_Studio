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


def test_candidate_budget_covers_multiple_parts_and_families():
    import json
    scene = document()
    node = next(n for n in scene['nodes'] if n['id'] == 'card-1')
    node['presentation'] = {'typography': {
        'title': {'fontSizePx': 80}, 'body': {'fontSizePx': 72}}}
    catalog = json.loads((ROOT/'html_engine/visual/generated/catalog.json').read_text(encoding='utf-8'))
    report = {'capacityIssues': [{'target': 'card-1', 'triggers': []}]}
    operations = capacity.capacity_candidates(scene, capacity._layout_for(scene, catalog), report, catalog, ['card-1'])
    assert len(operations) <= capacity.MAX_CANDIDATES
    for part in ('title', 'body'):
        assert any(op[0].get('part') == part and 'fontSizePx' in op[0]['values'] for op in operations)
        assert any(op[0].get('part') == part and 'lineHeight' in op[0]['values'] for op in operations)
    assert all(op[0]['values'].get('fontSizePx', 24) >= 24 for op in operations)


def test_candidate_order_independent_of_diagnostic_order():
    import json
    scene = document()
    for node in scene['nodes']:
        if node['id'] in ('card-1', 'card-2'):
            node['presentation'] = {'typography': {'body': {'fontSizePx': 48}}}
    catalog = json.loads((ROOT/'html_engine/visual/generated/catalog.json').read_text(encoding='utf-8'))
    issues = [{'target': key, 'triggers': []} for key in ('card-1', 'card-2')]
    def candidates(rows):
        return capacity.capacity_candidates(scene, capacity._layout_for(scene, catalog),
                                            {'capacityIssues': rows}, catalog, ['card-1', 'card-2'])
    assert candidates(issues) == candidates(list(reversed(issues)))


def test_three_targets_accumulate_without_losing_prior_repairs(tmp_path, monkeypatch):
    scene = document()
    keys = [n['id'] for n in scene['nodes'][:3]]
    for node in scene['nodes'][:3]: node['presentation'] = {'height': 100}
    def review(candidate, **kwargs):
        issues = [{'target': n['id'], 'triggers': []} for n in candidate['nodes'][:3]
                  if n['presentation']['height'] != 200]
        return {'passed': not issues, 'capacityIssues': issues, 'geometry_preflight': {'passed': not issues}}
    monkeypatch.setattr(capacity, 'review_scene', review)
    monkeypatch.setattr(capacity, 'capacity_candidates', lambda scene, layout, report, catalog, scope:
        [[{'targetId': scope[0], 'kind': 'set_presentation', 'values': {'height': 200}}]])
    original = copy.deepcopy(scene)
    result = capacity.solve_capacity_candidate(scene, None, run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT, lambda **kw: {}))
    assert result['summary']['status'] == 'candidate'
    assert {op['targetId'] for op in result['summary']['attempts'][-1]['operations']} == set(keys)
    assert result['summary']['provider_calls'] == 0 and scene == original
