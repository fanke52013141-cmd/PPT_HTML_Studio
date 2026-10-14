"""S02 failure injection: recovery, paid boundaries and attempt fencing."""
from pathlib import Path
import uuid
import pytest

from database import SessionLocal
from html_build_snapshot import create_generation_snapshot
from html_production_stages import ProductionStages
import html_task_store as store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def stage(tmp_path):
    snapshot = create_generation_snapshot(tmp_path, {"slide_id": "s1"}, repo_root=ROOT)
    db = SessionLocal()
    project_id = "stages-" + uuid.uuid4().hex
    task = store.submit_task(db, project_id=project_id, task_type="html_plan_generate",
                             submission_key=snapshot["snapshot_id"],
                             payload={"snapshot_id": snapshot["snapshot_id"]})
    store.mark_running(db, task["id"], expected_attempt=1)
    value = ProductionStages(db, task["id"], 1, tmp_path, snapshot["snapshot_id"], ROOT)
    yield value
    db.close()


def restart(stage):
    store.mark_failed(stage.db, stage.job_id, "injected interruption", expected_attempt=stage.attempt)
    job = store._job(stage.db, stage.job_id)
    task = store.submit_task(stage.db, project_id=job.project_id, task_type=job.job_type,
                             submission_key=job.get_payload()["submission_key"])
    store.mark_running(stage.db, stage.job_id, expected_attempt=task["attempt"])
    return ProductionStages(stage.db, stage.job_id, task["attempt"], stage.run, stage.snapshot_id, ROOT)


def test_returned_response_reused_across_attempts(stage):
    calls = []
    fn = lambda **kw: calls.append(kw) or {"plan": True}
    assert stage.wrap(fn, "json")(user_prompt="fixed") == {"plan": True}
    recovered = restart(stage)
    assert recovered.wrap(fn, "json")(user_prompt="fixed") == {"plan": True}
    assert len(calls) == 1
    with pytest.raises(store.HtmlTaskError):
        stage.record("late", {"bad": True})


def test_deleted_result_is_not_reused_or_rerequested(stage):
    calls = []
    fn = lambda **kw: calls.append(1) or {"plan": True}
    stage.wrap(fn, "json")()
    job = store._job(stage.db, stage.job_id)
    record = next(iter(job.get_payload()["production_stages"].values()))
    (stage.run / record["file"]).unlink()
    recovered = restart(stage)
    with pytest.raises(store.HtmlTaskError, match="STAGE_ARTIFACT_INVALID"):
        recovered.wrap(fn, "json")()
    assert len(calls) == 1


def test_unknown_provider_outcome_blocks_resubmission(stage):
    def timeout(**kw):
        raise TimeoutError("unknown provider outcome")
    with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        stage.wrap(timeout, "json")()
    with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        restart(stage)


def test_unknown_outcome_is_recorded_even_when_source_changes_in_flight(stage, monkeypatch):
    def timeout(**_kwargs):
        monkeypatch.setattr(stage, "verify_inputs", lambda **_kw: (_ for _ in ()).throw(store.HtmlTaskError("source changed")))
        raise TimeoutError("private provider message")
    with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        stage.wrap(timeout, "json")()
    record = next(iter(store._job(stage.db, stage.job_id).get_payload()["production_stages"].values()))
    assert record["state"] == "unknown" and record["error_class"] == "TimeoutError"
    assert "private provider message" not in str(record)


def test_returned_response_is_sealed_but_not_executed_after_source_change(stage, monkeypatch):
    def returned(**_kwargs):
        monkeypatch.setattr(stage, "verify_inputs", lambda **_kw: (_ for _ in ()).throw(store.HtmlTaskError("source changed")))
        return {"complete": True}
    with pytest.raises(store.HtmlTaskError, match="source changed"):
        stage.wrap(returned, "json")()
    record = next(iter(store._job(stage.db, stage.job_id).get_payload()["production_stages"].values()))
    assert record["state"] == "returned" and (stage.run / record["file"]).is_file()


def test_cancelled_snapshot_task_is_not_restarted(stage):
    store.cancel_task(stage.db, stage.job_id)
    with pytest.raises(store.HtmlTaskError):
        stage.record("late", {})
    job = store._job(stage.db, stage.job_id)
    with pytest.raises(store.HtmlTaskError, match="已取消"):
        store.submit_task(stage.db, project_id=job.project_id, task_type=job.job_type,
                          submission_key=job.get_payload()["submission_key"])


def test_corrupt_snapshot_blocks_model_before_call(stage):
    (stage.folder / "input/contract.json").write_text("{}", encoding="utf-8")
    calls = []
    with pytest.raises(ValueError):
        stage.wrap(lambda **kw: calls.append(1) or {}, "json")()
    assert calls == []


def test_budget_survives_recovery(stage):
    stage.MAX_CALLS = 1
    stage.wrap(lambda **kw: {}, "json")(user_prompt="a")
    recovered = restart(stage)
    recovered.MAX_CALLS = 1
    with pytest.raises(store.HtmlTaskError, match="预算"):
        recovered.wrap(lambda **kw: {}, "json")(user_prompt="b")


def test_image_response_is_reused_after_restart(stage):
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new("RGBA", (64, 64), (0, 0, 0, 255)).save(buf, format="PNG")
    calls = []
    fn = lambda *args, **kw: calls.append(1) or buf.getvalue()
    assert stage.wrap(fn, "image")("subject") == buf.getvalue()
    recovered = restart(stage)
    assert recovered.wrap(fn, "image")("subject") == buf.getvalue()
    assert len(calls) == 1
