from scripts.diagnose_repair_stages import next_stage_allowed, probe_valid


def test_probe_results_are_strict_and_do_not_accept_self_reported_pass():
    assert probe_valid('minimal_json', {'ok': True}, -10)
    for value in ({'ok': 1}, {'ok': 'true'}, {'ok': True, 'passed': True}, []):
        assert not probe_valid('minimal_json', value, -10)
    assert probe_valid('single_image', {'minimum_tick': -10.0}, -10)
    for value in ({'minimum_tick': '-10'}, {'minimum_tick': True}, {'minimum_tick': 0}):
        assert not probe_valid('single_image', value, -10)


def test_stage_gate_requires_two_real_passes_without_unknown_results():
    assert next_stage_allowed([{'passed': True}, {'passed': True}])
    assert not next_stage_allowed([{'passed': True}])
    assert not next_stage_allowed([{'passed': True}, {'passed': False}])
    assert not next_stage_allowed([{'passed': True}, {'passed': True, 'unknown_outcome': True}])
