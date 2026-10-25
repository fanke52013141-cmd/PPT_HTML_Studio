"""One cooperative budget for a page, including nested repair and review stages.

No transport retry or cancellation claims: an in-flight provider may finish,
but its late result cannot advance production. Contexts are task/thread local.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from functools import wraps
from pathlib import Path
import time
import uuid

from pipeline_lifecycle import write_json_atomic

_CURRENT = ContextVar("html_page_budget", default=None)
_FINAL = ContextVar("html_final_review", default=False)


class PageBudgetExceeded(ValueError):
    code = "PAGE_BUDGET_EXHAUSTED"
    status_code = 422


@dataclass
class PageBudget:
    seconds: float = 900
    browser_limit: int = 80
    model_limit: int = 12
    final_reserve_seconds: float = 20
    clock: object = time.monotonic
    started: float = field(init=False)
    browser_calls: int = 0
    model_calls: int = 0
    events: list = field(default_factory=list)
    review_cache: dict = field(default_factory=dict)

    def __post_init__(self):
        import math
        if (type(self.seconds) not in (int, float) or not math.isfinite(self.seconds)
            or not 0 < self.seconds <= 7200
            or type(self.final_reserve_seconds) not in (int, float)
            or not math.isfinite(self.final_reserve_seconds)
            or not 0 <= self.final_reserve_seconds < self.seconds
            or any(type(v) is not int or not 1 <= v <= 256 for v in (self.browser_limit, self.model_limit))):
            raise ValueError("Invalid page budget")
        self.started = self.clock()

    def remaining(self, *, final=False):
        reserve = 0 if final else self.final_reserve_seconds
        return max(0, self.seconds - (self.clock() - self.started) - reserve)

    def check(self, *, final=False):
        if self.remaining(final=final) <= 0:
            raise PageBudgetExceeded("整页共享预算已耗尽，保留证据等待处理")

    def claim(self, kind, stage, *, final=False):
        self.check(final=final)
        count = getattr(self, kind + "_calls")
        # Keep two subprocess slots for the final static + temporal review.
        limit = getattr(self, kind + "_limit") - (2 if kind == "browser" and not final else 0)
        if count >= limit:
            raise PageBudgetExceeded("整页共享调用预算已耗尽：" + kind)
        setattr(self, kind + "_calls", count + 1)
        self.events.append({"kind": kind, "stage": str(stage)[:120], "final": final,
                            "remaining_seconds": round(self.remaining(final=final), 3)})

    def snapshot(self):
        return {"version": "page-budget/0.1.0", "elapsed_seconds": round(self.clock()-self.started, 3),
                "seconds": self.seconds, "browser_limit": self.browser_limit, "model_limit": self.model_limit,
                "browser_calls": self.browser_calls, "model_calls": self.model_calls,
                "final_reserve_seconds": self.final_reserve_seconds, "events": self.events}


def current_budget():
    return _CURRENT.get()


def page_budgeted(function):
    """Direct entry points share one budget; nested calls never reset it."""
    @wraps(function)
    def execute(*args, **kwargs):
        if args and isinstance(args[0], dict) and 'id' in args[0]:
            from html_visual_store import validate_slide_id
            validate_slide_id(args[0]['id'])
        if current_budget() is not None:
            return function(*args, **kwargs)
        budget = PageBudget()
        deps = kwargs["deps"]

        def runner(*a, **kw):
            final = _FINAL.get()
            budget.claim("browser", "subprocess", final=final)
            kw["timeout_sec"] = min(kw.get("timeout_sec", budget.seconds), budget.remaining(final=final))
            result = deps.run_subprocess_bounded(*a, **kw)
            budget.check(final=final)
            return result

        def generator(original):
            def call(**kw):
                budget.claim("model", kw.get("artifact_prefix", "json"))
                kw["request_timeout"] = min(kw.get("request_timeout", budget.seconds), budget.remaining())
                result = original(**kw)
                budget.check()
                return result
            return call

        kwargs["deps"] = replace(deps, run_subprocess_bounded=runner,
            json_generator=generator(deps.json_generator),
            planning_generator=generator(deps.planning_generator) if deps.planning_generator else None)
        if kwargs.get('provider') is not None:
            provider = kwargs['provider']
            def image_provider(*a, **kw):
                budget.claim('model', 'image_provider')
                result = provider(*a, **kw)
                budget.check()
                return result
            kwargs['provider'] = image_provider
        checkpoint = kwargs.get("checkpoint", lambda: None)
        def checked():
            checkpoint()
            # Reserve restricts new work; completed final evidence may still
            # return during the reserve window before the absolute deadline.
            budget.check(final=True)
        kwargs["checkpoint"] = checked
        outcome = "interrupted"
        token = _CURRENT.set(budget)
        try:
            result = function(*args, **kwargs)
            budget.check(final=True)
            outcome = "completed"
            return result
        except PageBudgetExceeded:
            outcome = "budget_exhausted"
            raise
        finally:
            try:
                folder = Path(kwargs["run_dir"]) / "planning/html_visual/page-budgets"
                write_json_atomic(folder / (uuid.uuid4().hex + ".json"), {**budget.snapshot(), "outcome": outcome})
            finally:
                _CURRENT.reset(token)
    return execute


def final_review(function):
    @wraps(function)
    def execute(*args, **kwargs):
        token = _FINAL.set(kwargs.get("preflight_dir") is not None and not kwargs.get("diagnostic", False))
        try:
            return function(*args, **kwargs)
        finally:
            _FINAL.reset(token)
    return execute
