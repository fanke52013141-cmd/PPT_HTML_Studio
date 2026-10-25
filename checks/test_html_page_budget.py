from pathlib import Path
import pytest

import html_page_budget as module
from html_page_budget import PageBudget, PageBudgetExceeded, page_budgeted, current_budget, final_review
from html_visual_review_service import HtmlReviewDependencies


def test_nested_stages_share_budget_and_never_retry(tmp_path):
    calls = []
    @page_budgeted
    def child(*, run_dir, deps, checkpoint=lambda: None):
        current_budget().model_limit = 1
        deps.json_generator(artifact_prefix='first')
        deps.json_generator(artifact_prefix='second')
    @page_budgeted
    def parent(*, run_dir, deps, checkpoint=lambda: None):
        identity = current_budget()
        try:
            child(run_dir=run_dir, deps=deps)
        finally:
            assert current_budget() is identity
    with pytest.raises(PageBudgetExceeded):
        parent(run_dir=tmp_path, deps=HtmlReviewDependencies(Path('.'), lambda **kw: calls.append(kw)))
    assert len(calls) == 1
    assert current_budget() is None
    assert len(list((tmp_path/'planning/html_visual/page-budgets').glob('*.json'))) == 1


def test_time_and_browser_reserve_are_only_available_to_final_review():
    now = [0]
    budget = PageBudget(seconds=30, final_reserve_seconds=10, browser_limit=3, clock=lambda:now[0])
    budget.claim('browser','search')
    with pytest.raises(PageBudgetExceeded): budget.claim('browser','search')
    budget.claim('browser','final-static',final=True)
    budget.claim('browser','final-temporal',final=True)
    now[0] = 21
    with pytest.raises(PageBudgetExceeded): budget.check()
    budget.check(final=True)
    now[0] = 31
    with pytest.raises(PageBudgetExceeded): budget.check(final=True)


def test_late_provider_result_cannot_advance(tmp_path, monkeypatch):
    now = [0]
    budget = PageBudget(seconds=30, final_reserve_seconds=5, clock=lambda:now[0])
    monkeypatch.setattr(module, 'PageBudget', lambda:budget)
    calls = []
    def provider(**kw):
        calls.append(kw);now[0]=26
        return {'status':'late'}
    @page_budgeted
    def task(*, run_dir, deps, checkpoint=lambda:None):
        deps.json_generator(request_timeout=600)
        pytest.fail('late result must be rejected')
    with pytest.raises(PageBudgetExceeded):
        task(run_dir=tmp_path,deps=HtmlReviewDependencies(Path('.'),provider))
    assert calls[0]['request_timeout'] == 25


def test_final_context_does_not_leak():
    @final_review
    def review(**kw): return module._FINAL.get()
    assert review(preflight_dir='evidence') is True
    assert review(preflight_dir='evidence',diagnostic=True) is False
    assert module._FINAL.get() is False


def test_invalid_dependency_setup_cannot_leak_budget_context(tmp_path):
    @page_budgeted
    def task(*, run_dir, deps, checkpoint=lambda:None):
        pytest.fail('invalid dependency cannot enter task')
    with pytest.raises(AttributeError): task(run_dir=tmp_path,deps=object())
    assert current_budget() is None
