import json
import pytest
from scripts.reconcile_reconstruction_acceptance import reconcile,ROOT


def test_all_69_criteria_have_explicit_implementation_and_remaining_gap():
    plan=json.loads((ROOT/'docs/plans/html-backend-development/reconstruction-acceptance-plan-v2.json').read_text(encoding='utf-8'))
    result=reconcile(plan)
    assert len(result['criteria'])==69 and result['counts']['passed']==0
    assert all(r['remaining'] and r['required_level'] for r in result['criteria'])
    assert all(r['status']=='not_run' for r in result['criteria'] if r['task_id']=='T10')
    assert set(result['milestones'].values())=={'pending'}
    plan['acceptance'].pop()
    with pytest.raises(ValueError,match='69_CRITERIA'):reconcile(plan)


def test_skipped_or_failed_junit_cannot_be_counted_as_verified(tmp_path):
    plan=json.loads((ROOT/'docs/plans/html-backend-development/reconstruction-acceptance-plan-v2.json').read_text(encoding='utf-8'))
    path=tmp_path/'junit.xml';path.write_text('<testsuite><testcase classname="checks.test_html_asset_reuse" name="bad"><skipped/></testcase></testsuite>')
    result=reconcile(plan,[path])
    assert not any(r['executed_test_modules'] for r in result['criteria'])
