from scripts.compare_repair_runners import aggregate, schedule


def test_balanced_order_and_fixed_attempt_budget():
    planned = schedule(2)
    assert len(planned) == 8
    for slide in ('slide_001', 'slide_003'):
        orders = [[arm for s, r, arm in planned if s == slide and r == repeat] for repeat in (1, 2)]
        assert orders[0] == list(reversed(orders[1]))
    assert schedule(1, ['slide_003']) == [('slide_003', 1, 'pi'), ('slide_003', 1, 'legacy')]


def test_failures_and_unrun_pairs_are_not_removed_or_called_comparable():
    records = [{'slide': 'slide_001', 'repeat': 1, 'arm': 'legacy', 'passed': False,
                'elapsed_seconds': 180, 'model_calls': 1, 'first_input_sha256': 'a'},
               {'slide': 'slide_001', 'repeat': 1, 'arm': 'pi', 'passed': True,
                'elapsed_seconds': 20, 'model_calls': 1, 'first_input_sha256': 'b'}]
    result = aggregate(records, schedule(2))
    assert result['metrics']['legacy']['passed'] == 0
    assert result['metrics']['legacy']['attempted_pass_rate'] == 0
    assert result['metrics']['pi']['not_run'] == 3
    assert result['pairs'][0]['completed'] and not result['pairs'][0]['same_first_business_input']
    assert not result['pairs'][1]['completed']
    for row in records:
        row['first_input_sha256'] = None
    assert not aggregate(records, schedule(2))['pairs'][0]['same_first_business_input']
