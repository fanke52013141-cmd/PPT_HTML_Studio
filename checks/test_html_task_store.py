"""F02/AC18: persistent html task store — idempotency, bounded retries,
restart recovery, cancel safety over the shared LocalJob table."""
from __future__ import annotations

import pytest

import html_task_store as store
from database import LocalJob


@pytest.fixture()
def db():
    from database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


import uuid as _uuid


def _submit(db, key, **kwargs):
    return store.submit_task(
        db,
        project_id=kwargs.pop("project_id", "p-" + _uuid.uuid4().hex[:8]),
        task_type=kwargs.pop("task_type", "html_plan_generate"),
        submission_key=key,
        **kwargs,
    )


def test_idempotent_submission_reuses_active_or_succeeded(db) -> None:
    project = "p-idem"
    first = _submit(db, key="plan:slide_001:v3", project_id=project)
    again = _submit(db, key="plan:slide_001:v3", project_id=project)
    assert again["id"] == first["id"] and again["reused"] is True
    store.mark_running(db, first["id"])
    store.mark_succeeded(db, first["id"], {"plan": True})
    succeeded = _submit(db, key="plan:slide_001:v3", project_id=project)
    assert succeeded["id"] == first["id"]
    assert succeeded["status"] == "succeeded"


def test_failed_job_retries_within_budget_then_refuses(db) -> None:
    project = "p-retry"
    job = _submit(db, key="asset:cup:v1", project_id=project, task_type="html_asset_produce")
    store.mark_running(db, job["id"])
    failed = store.mark_failed(db, job["id"], "模型超时")
    assert failed["retryable"] is True
    retried = _submit(db, key="asset:cup:v1", project_id=project, task_type="html_asset_produce")
    assert retried["attempt"] == 2 and retried["retried"] is True
    store.mark_running(db, retried["id"])
    store.mark_failed(db, retried["id"], "再次失败")
    second_retry = _submit(db, key="asset:cup:v1", project_id=project, task_type="html_asset_produce")
    assert second_retry["attempt"] == 3
    store.mark_running(db, second_retry["id"])
    store.mark_failed(db, second_retry["id"], "第三次失败")
    with pytest.raises(store.HtmlTaskError) as exhausted:
        _submit(db, key="asset:cup:v1", project_id=project, task_type="html_asset_produce")
    assert exhausted.value.status_code == 409


def test_restart_marks_active_tasks_interrupted(db) -> None:
    project = "p-recover"
    queued = _submit(db, key="review:s1", project_id=project, task_type="html_review")
    running = _submit(db, key="review:s2", project_id=project, task_type="html_review")
    store.mark_running(db, running["id"])
    recovered = store.recover_interrupted(db)
    assert recovered >= 2
    refreshed = {
        job["submission_key"]: job
        for job in (
            _submit(db, key="review:s1", project_id=project, task_type="html_review"),
            _submit(db, key="review:s2", project_id=project, task_type="html_review"),
        )
    }
    # Interrupted tasks are re-submittable in place (attempt + 1), never
    # duplicated, and never silently re-run without an explicit submit.
    assert refreshed["review:s1"]["reused"] is True
    assert refreshed["review:s1"]["status"] == "queued"
    assert refreshed["review:s1"]["attempt"] == 2


def test_cancel_only_touches_active_tasks(db) -> None:
    active = _submit(db, key="cancel:a", task_type="html_review")
    cancelled = store.cancel_task(db, active["id"])
    assert cancelled["status"] == "cancelled"
    with pytest.raises(store.HtmlTaskError) as terminal:
        store.cancel_task(db, active["id"])
    assert terminal.value.status_code == 409
    # A succeeded result is never overwritten by a late cancel.
    done = _submit(db, key="cancel:b", project_id=active["project_id"], task_type="html_review")
    store.mark_running(db, done["id"])
    store.mark_succeeded(db, done["id"], {"ok": True})
    with pytest.raises(store.HtmlTaskError):
        store.cancel_task(db, done["id"])
    still = db.query(LocalJob).filter(LocalJob.id == done["id"]).first()
    assert still.status == "succeeded"


def test_unknown_task_type_rejected(db) -> None:
    with pytest.raises(store.HtmlTaskError):
        _submit(db, key="x:1", task_type="video_render")
