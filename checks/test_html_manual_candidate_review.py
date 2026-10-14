from pathlib import Path
from types import SimpleNamespace

import pytest

import html_manual_candidate_review as review


def test_unknown_candidate_requires_current_failed_original(monkeypatch, tmp_path):
    job = SimpleNamespace(id="html-original", job_type="html_plan_generate", status="failed")
    monkeypatch.setattr(review, "task_view", lambda _job, _run: {
        "slide_id": "slide_001", "input_state": "stale", "stages": {},
    })
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_TASK_NOT_CURRENT"):
        review.inspect_candidate(job, tmp_path, "slide_001", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_human_decision_is_immutable_and_does_not_change_original_job(monkeypatch, tmp_path):
    job = SimpleNamespace(id="html-original", job_type="html_plan_generate", status="failed")
    path = Path(tmp_path) / "review.json"
    packet = {"key": "a" * 64, "job_id": job.id, "source_revision": 0,
              "scene_sha256": "b" * 64, "design_sha256": "c" * 64,
              "preview_sha256": "d" * 64, "engineering": "failed", "decision": None,
              "_decision_path": path}
    monkeypatch.setattr(review, "inspect_candidate", lambda *_args: {
        **packet, "decision": review._json(path) if path.is_file() else None,
    })
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_DECISION_INVALID"):
        review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                key=packet["key"], decision="accept", note="short")
    result = review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                     key=packet["key"], decision="reject", note="标注框遮挡主体，尚不可接受")
    assert result["decision"]["decision"] == "reject"
    assert result["decision"]["author_saved"] is False
    assert result["decision"]["model_fidelity"] == "unknown"
    assert job.status == "failed"
    assert review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                   key=packet["key"], decision="reject", note="标注框遮挡主体，尚不可接受") == result
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_ALREADY_DECIDED"):
        review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                key=packet["key"], decision="accept", note="现在决定接受此候选")


def test_engineering_failure_cannot_be_accepted(monkeypatch, tmp_path):
    job = SimpleNamespace(id="html-original", job_type="html_plan_generate", status="failed")
    monkeypatch.setattr(review, "inspect_candidate", lambda *_args: {
        "key": "a" * 64, "decision": None, "engineering": "failed",
    })
    with pytest.raises(review.ManualCandidateError, match="CANDIDATE_ENGINEERING_FAILED"):
        review.decide_candidate(job, tmp_path, "slide_001", tmp_path,
                                key="a" * 64, decision="accept", note="这份候选可以接受")
    assert list(tmp_path.iterdir()) == []
