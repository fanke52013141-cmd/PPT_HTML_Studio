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


def test_measured_call_and_restart_reuse_are_distinct(stage):
    from html_build_snapshot import json_bytes
    calls = []
    kwargs = {"user_prompt": "private instruction", "artifact_prefix": "html_scene_plan_s1"}
    fn = lambda **kw: calls.append(kw) or {"plan": True}
    stage.wrap(fn, "json")(**kwargs)
    first = store._job_to_dict(store._job(stage.db, stage.job_id))
    metrics = next(iter(first["stages"].values()))["metrics"]
    assert metrics["role"] == "planning" and metrics["adapter_calls"] == 1
    assert metrics["adapter_input_bytes"] == len(json_bytes({"args": (), "kwargs": kwargs}))
    assert metrics["output_bytes"] == len(json_bytes({"plan": True})) and metrics["elapsed_ms"] >= 0
    assert "private instruction" not in str(metrics) and metrics["usage"] is None
    recovered = restart(stage)
    recovered.wrap(fn, "json")(**kwargs)
    result = store._job_to_dict(store._job(stage.db, stage.job_id))["execution"]
    assert result["measured_adapter_calls"] == 1 and result["recorded_reuses"] == 1
    assert result["elapsed_ms"] == metrics["elapsed_ms"] and calls == [kwargs]


def test_unfinished_intent_does_not_claim_a_measured_adapter_call(stage):
    class AbruptExit(BaseException):
        pass
    def interrupted(**_):
        raise AbruptExit()
    with pytest.raises(AbruptExit):
        stage.wrap(interrupted, "json")()
    task = store._job_to_dict(store._job(stage.db, stage.job_id))
    assert next(iter(task["stages"].values()))["state"] == "intent"
    assert task["execution"]["measured_adapter_calls"] == 0
    assert task["execution"]["unmeasured_requests"] == task["execution"]["untimed_requests"] == 1


def test_unknown_elapsed_does_not_persist_provider_error_or_invent_usage(stage):
    def timeout(**_):
        raise TimeoutError("private provider message")
    with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        stage.wrap(timeout, "json")()
    task = store._job_to_dict(store._job(stage.db, stage.job_id))
    assert task["execution"]["measured_adapter_calls"] == 1
    assert task["execution"]["usage"] is task["execution"]["cost"] is None
    assert "private provider message" not in str(task["stages"])


def test_budget_stop_is_persistent_without_an_extra_provider_call(stage):
    stage.MAX_CALLS = 1
    calls = []
    stage.wrap(lambda **kw: calls.append(1) or {}, "json")(user_prompt="first")
    with pytest.raises(store.HtmlTaskError, match="预算"):
        stage.wrap(lambda **kw: calls.append(1) or {}, "json")(user_prompt="second")
    action = store._job_to_dict(store._job(stage.db, stage.job_id))["progress"]["next_action"]
    assert action["reason"] == "external_call_budget_exhausted" and not action["automatic_retry"]
    assert calls == [1]


@pytest.mark.parametrize("explicit,expected", [(600, 600), (45, 45), (None, 1800)])
def test_streaming_honors_explicit_stage_deadline_without_changing_model_parameters(stage, explicit, expected):
    calls = []
    def generator(**kw):
        calls.append(kw)
        return {"status": "complete"}
    generator.supports_stream_progress = True
    options = {"user_prompt": "fixed", "max_tokens_limit": 64000, "temperature": 1.0}
    if explicit is not None:
        options["request_timeout"] = explicit
    stage.wrap(generator, "json")(**options)
    assert len(calls) == 1 and calls[0]["request_timeout"] == expected and calls[0]["stream_output"] is True
    assert calls[0]["max_tokens_limit"] == 64000 and calls[0]["temperature"] == 1.0
    assert "reasoning_effort" not in calls[0]
    task = store._job_to_dict(store._job(stage.db, stage.job_id))
    assert next(iter(task["stages"].values()))["metrics"]["request_timeout_seconds"] == expected


def test_stream_failure_routes_to_verification_and_blocks_resend(stage):
    calls = []
    def generator(**kw):
        calls.append(1)
        kw["on_stream_progress"]({"state": "failed", "failure_reason": "read_timeout",
            "elapsed_seconds": 281, "last_chunk_seconds": 156, "silence_seconds": 125,
            "total_timeout_seconds": 1800, "read_timeout_seconds": 120})
        raise RuntimeError("private provider detail")
    generator.supports_stream_progress = True
    wrapped = stage.wrap(generator, "json")
    with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        wrapped(artifact_prefix="html_scene_plan_s1", request_timeout=1800)
    task = store._job_to_dict(store._job(stage.db, stage.job_id))
    assert task["progress"]["next_action"] == {"stage": "planning", "reason": "read_timeout",
        "routes": ["provider_verification"], "automatic_retry": False}
    assert task["recovery"]["requires_verification"] and not task["recovery"]["can_resume"]
    with pytest.raises(store.HtmlTaskError, match="EXTERNAL_OUTCOME_UNKNOWN"):
        wrapped(artifact_prefix="html_scene_plan_s1", request_timeout=1800)
    assert calls == [1] and "private provider detail" not in str(task)
