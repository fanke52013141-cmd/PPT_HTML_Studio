from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import html_course_pipeline as course_pipeline
import one_click_orchestrator as one_click
from tts_artifacts import artifact_paths, build_confirmation_payload


def _write_audio_artifacts(run_dir: Path, slide_id: str = "slide_001") -> None:
    paths = artifact_paths(run_dir, slide_id)
    for key in ("text", "audio", "metadata", "srt", "timeline"):
        path = paths[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{key}-content", encoding="utf-8")


def test_automatic_technical_confirmation_does_not_unlock_html_course(tmp_path: Path) -> None:
    from tts_artifacts import confirmation_path

    _write_audio_artifacts(tmp_path)
    confirmation_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    confirmation_path(tmp_path).write_text(json.dumps(build_confirmation_payload(
        tmp_path, ["slide_001"], confirmation_mode="automatic_technical",
    )), encoding="utf-8")

    confirmed, reason = course_pipeline._audio_mode(tmp_path, ["slide_001"])
    assert confirmed is False
    assert reason == "automatic_technical"

    confirmation_path(tmp_path).write_text(json.dumps(build_confirmation_payload(
        tmp_path, ["slide_001"], confirmation_mode="user_reviewed",
    )), encoding="utf-8")
    confirmed, reason = course_pipeline._audio_mode(tmp_path, ["slide_001"])
    assert confirmed is True
    assert reason == "user_reviewed"


def test_course_cost_ledger_records_returned_receipts_without_inventing_amounts() -> None:
    course: dict = {}
    course_pipeline._record_cost(course, {
        "job_id": "job-one", "returned_stage_result_count": 2,
    })
    course_pipeline._record_cost(course, {
        "job_id": "job-two", "returned_stage_result_count": 1,
    })

    assert course["cost"]["state"] == "provider_cost_not_reported"
    assert course["cost"]["amount"] is None
    assert course["cost"]["returned_stage_result_count"] == 3
    assert course["cost"]["jobs"]["job-one"]["returned_stage_result_count"] == 2
    assert "TTS" in course["cost"]["scope"]


def test_html_pause_and_failure_keep_nested_course_lifecycle_current(tmp_path: Path) -> None:
    project = SimpleNamespace(id="html-project", run_dir=str(tmp_path))
    status = one_click._initial_status(project.id, "run-a")
    status.update({"workflow_type": "html_course", "html_course": {
        "status": "running", "history": [],
    }})
    one_click._PAUSE_REQUESTS.add(project.id)
    try:
        assert one_click._pause_at_stage_boundary(project, status, project.id)
    finally:
        one_click._PAUSE_REQUESTS.discard(project.id)

    assert status["status"] == "paused"
    assert status["html_course"]["status"] == "paused"
    assert status["html_course"]["history"][-1]["event"] == "user_pause"

    status["html_course"]["status"] = "running"
    one_click._fail_stage(project, status, "tts", "人工试听确认缺失")
    assert status["html_course"]["status"] == "paused"
    assert status["html_course"]["history"][-1]["event"] == "stage_blocked"
