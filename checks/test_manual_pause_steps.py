"""Tests for the manual-pause-steps orchestrator logic and project service fields."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the project root is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from one_click_orchestrator import (
    _MANUAL_PAUSE_BEFORE_STAGE,
    _pause_for_manual_step,
    _overall_progress,
    pause_one_click,
)


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------

def test_manual_pause_mapping_covers_configurable_modules() -> None:
    """Every creation-config pause option must map to a real pipeline stage."""
    assert set(_MANUAL_PAUSE_BEFORE_STAGE.keys()) == {
        "storyboard", "images", "ai_mask", "narration", "tts",
        "annotation", "digital_human", "render",
    }
    for module in ("storyboard", "images", "ai_mask", "narration", "tts"):
        assert _MANUAL_PAUSE_BEFORE_STAGE[module] == module
    # 勾画标注与数字人是渲染前的手动模块，与「作品输出」共用渲染前暂停点。
    assert _MANUAL_PAUSE_BEFORE_STAGE["annotation"] == "render"
    assert _MANUAL_PAUSE_BEFORE_STAGE["digital_human"] == "render"
    assert _MANUAL_PAUSE_BEFORE_STAGE["render"] == "render"


# ---------------------------------------------------------------------------
# _pause_for_manual_step
# ---------------------------------------------------------------------------

def _make_project(pause_steps: list[str]) -> MagicMock:
    proj = MagicMock()
    proj.manual_pause_steps = json.dumps(pause_steps)
    return proj


def test_pause_returns_false_when_no_pause_steps() -> None:
    project = _make_project([])
    status: dict = {}
    assert _pause_for_manual_step(project, status, "mask_assets") is False
    assert status.get("status") is None  # unchanged


def test_pause_returns_false_when_stage_not_matched() -> None:
    project = _make_project(["mask"])
    status: dict = {"stages": []}
    # "narration" module maps to "narration" stage, not "images"
    assert _pause_for_manual_step(project, status, "images") is False


@patch("one_click_orchestrator._save_status")
def test_legacy_mask_pause_is_ignored_by_one_click(mock_save: MagicMock) -> None:
    project = _make_project(["mask"])
    status: dict = {"stages": []}
    result = _pause_for_manual_step(project, status, "mask_assets")
    assert result is False
    mock_save.assert_not_called()


@patch("one_click_orchestrator._save_status")
def test_pause_sets_waiting_for_user_on_narration(mock_save: MagicMock) -> None:
    project = _make_project(["narration"])
    status: dict = {"stages": []}
    result = _pause_for_manual_step(project, status, "narration")
    assert result is True
    assert status["status"] == "waiting_for_user"
    assert status["manual_pause_module"] == "narration"
    mock_save.assert_called_once()


@patch("one_click_orchestrator._save_status")
def test_pause_sets_waiting_for_user_on_digital_human(mock_save: MagicMock) -> None:
    project = _make_project(["digital_human"])
    status: dict = {"stages": []}
    # 数字人讲解与作品输出共用渲染前暂停点。
    result = _pause_for_manual_step(project, status, "render")
    assert result is True
    assert status["status"] == "waiting_for_user"
    assert status["manual_pause_module"] == "digital_human"
    mock_save.assert_called_once()


@patch("one_click_orchestrator._save_status")
def test_pause_sets_waiting_for_user_on_annotation(mock_save: MagicMock) -> None:
    project = _make_project(["annotation"])
    status: dict = {"stages": []}
    result = _pause_for_manual_step(project, status, "render")
    assert result is True
    assert status["manual_pause_module"] == "annotation"
    mock_save.assert_called_once()


def test_pause_skipped_stage_keeps_flow_moving() -> None:
    """已完成、将被跳过的阶段不再触发暂停（没有新内容需要人工处理）。"""
    project = _make_project(["storyboard"])
    status: dict = {"stages": []}
    assert _pause_for_manual_step(project, status, "storyboard", lambda stage: False) is False
    assert status.get("status") is None  # unchanged


@patch("one_click_orchestrator._save_status")
def test_pause_sets_waiting_for_user_on_tts(mock_save: MagicMock) -> None:
    project = _make_project(["tts"])
    status: dict = {"stages": []}
    result = _pause_for_manual_step(project, status, "tts")
    assert result is True
    assert status["status"] == "waiting_for_user"
    assert status["manual_pause_module"] == "tts"
    mock_save.assert_called_once()


@patch("one_click_orchestrator._save_status")
def test_pause_with_multiple_modules_only_triggers_matching_one(mock_save: MagicMock) -> None:
    project = _make_project(["mask", "narration", "digital_human"])
    status: dict = {"stages": []}
    # Legacy Mask pauses are retained in imported packages but ignored by
    # one-click; narration remains a valid manual stop.
    assert _pause_for_manual_step(project, status, "mask_assets") is False
    assert _pause_for_manual_step(project, status, "narration") is True
    assert status["manual_pause_module"] == "narration"
    mock_save.assert_called_once()


def test_pause_handles_invalid_json_gracefully() -> None:
    project = MagicMock()
    project.manual_pause_steps = "not valid json"
    status: dict = {}
    assert _pause_for_manual_step(project, status, "mask_assets") is False


def test_pause_handles_none_field_gracefully() -> None:
    project = MagicMock()
    project.manual_pause_steps = None
    status: dict = {}
    assert _pause_for_manual_step(project, status, "mask_assets") is False


# ---------------------------------------------------------------------------
# _overall_progress
# ---------------------------------------------------------------------------

def test_overall_progress_empty_stages() -> None:
    assert _overall_progress({"stages": []}) == 0.0
    assert _overall_progress({}) == 0.0


def test_overall_progress_all_done() -> None:
    stages = [{"status": "done"} for _ in range(10)]
    assert _overall_progress({"stages": stages}) == 1.0


def test_overall_progress_half_done() -> None:
    stages = [{"status": "done"} for _ in range(5)] + [
        {"status": "pending"} for _ in range(5)
    ]
    assert _overall_progress({"stages": stages}) == 0.5


def test_overall_progress_supports_legacy_completed_status() -> None:
    stages = [{"status": "completed"} for _ in range(2)] + [{"status": "pending"}]
    assert _overall_progress({"stages": stages}) == round(2 / 3, 4)


# ---------------------------------------------------------------------------
# pause_one_click (integration-ish)
# ---------------------------------------------------------------------------

def test_pause_one_click_on_idle_project_returns_status() -> None:
    """When no thread is running, pause should just confirm current status."""
    from one_click_orchestrator import _RUNNING

    project = MagicMock()
    project.id = "test-idle"
    project.manual_pause_steps = "[]"

    # Ensure no thread is registered.
    _RUNNING.pop("test-idle", None)

    # We need to mock _status_for_project since it reads from disk.
    import one_click_orchestrator as orch

    original = orch._status_for_project
    orch._status_for_project = lambda p, pid: {"status": "paused", "stages": []}
    try:
        result = pause_one_click(project)
        assert result["success"] is True
        assert result["status"]["status"] == "paused"
    finally:
        orch._status_for_project = original
