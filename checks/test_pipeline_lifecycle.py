import tempfile
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline_lifecycle import (
    clear_all_reveal_artifacts,
    clear_audio_confirmation,
    clear_slide_reveal_artifacts,
    mark_downstream_pending,
    mark_selected_stale,
)


def _write(path: Path, content: str = "generated") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_slide_cleanup_is_scoped() -> None:
    with tempfile.TemporaryDirectory() as value:
        run_dir = Path(value)
        slide_one = run_dir / "slides" / "slide_001"
        slide_two = run_dir / "slides" / "slide_002"
        for filename in ("scene.json", "animation_timeline.json", "reveal_report.json"):
            _write(slide_one / filename)
            _write(slide_two / filename)
        _write(slide_one / "assets" / "layer.png")
        _write(slide_two / "assets" / "layer.png")
        _write(slide_one / "visual_draft.png")
        _write(run_dir / "remotion_props.json")

        clear_slide_reveal_artifacts(run_dir, "slide_001")

        assert (slide_one / "visual_draft.png").exists()
        assert not (slide_one / "assets").exists()
        assert not (slide_one / "scene.json").exists()
        assert (slide_two / "assets" / "layer.png").exists()
        assert (slide_two / "scene.json").exists()
        assert not (run_dir / "remotion_props.json").exists()


def test_project_reveal_cleanup_keeps_sources() -> None:
    with tempfile.TemporaryDirectory() as value:
        run_dir = Path(value)
        for slide_id in ("slide_001", "slide_002"):
            slide_dir = run_dir / "slides" / slide_id
            _write(slide_dir / "scene.json")
            _write(slide_dir / "assets" / "layer.png")
            _write(slide_dir / "visual_draft.png")
            _write(slide_dir / "voice.mp3")
        _write(run_dir / "remotion_props.json")

        clear_all_reveal_artifacts(run_dir, ("slide_001", "slide_002"))

        for slide_id in ("slide_001", "slide_002"):
            slide_dir = run_dir / "slides" / slide_id
            assert (slide_dir / "visual_draft.png").exists()
            assert (slide_dir / "voice.mp3").exists()
            assert not (slide_dir / "scene.json").exists()
            assert not (slide_dir / "assets").exists()


def test_audio_confirmation_cleanup_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as value:
        run_dir = Path(value)
        confirmation = run_dir / "planning" / "audio_confirmed.json"
        _write(confirmation, "{}")
        assert clear_audio_confirmation(run_dir) is True
        assert clear_audio_confirmation(run_dir) is False


def test_status_transitions_preserve_stale_distinction() -> None:
    statuses = {
        "3": "completed",
        "4": "completed",
        "5": "in_progress",
        "6": "pending_reconfirmation",
        "7": "pending",
        "8": "completed",
    }
    mark_downstream_pending(statuses, from_step=4)
    assert statuses == {
        "3": "completed",
        "4": "pending_reconfirmation",
        "5": "pending",
        "6": "pending",
        "7": "pending",
        "8": "pending_reconfirmation",
    }

    selected = {"5": "completed", "8": "in_progress", "7": "completed"}
    mark_selected_stale(selected, (5, 8))
    assert selected == {"5": "pending_reconfirmation", "8": "pending", "7": "completed"}


if __name__ == "__main__":
    test_slide_cleanup_is_scoped()
    test_project_reveal_cleanup_keeps_sources()
    test_audio_confirmation_cleanup_is_idempotent()
    test_status_transitions_preserve_stale_distinction()
    print("pipeline lifecycle checks passed")


# ---------------------------------------------------------------------------
# write_json_atomic 原子性保证回归
#
# 历史缺陷：os.replace 连续失败四次后退化为对目标文件的原地直写兜底，
# 截断窗口重新出现且调用方无从得知原子性已被放弃。契约：原子替换持续
# 失败时保留原目标文件、清理临时文件并向上抛出带原因的异常。
# ---------------------------------------------------------------------------

import json as _json  # noqa: E402
import threading as _threading  # noqa: E402

import pytest  # noqa: E402

from pipeline_lifecycle import write_json_atomic  # noqa: E402


def test_write_json_atomic_normal_path_replaces_and_leaves_no_temp(tmp_path, monkeypatch) -> None:
    target = tmp_path / "artifact.json"
    monkeypatch.setattr("pipeline_lifecycle.time.sleep", lambda _s: None)

    write_json_atomic(target, {"value": 1, "list": [1, 2, 3]})

    assert _json.loads(target.read_text(encoding="utf-8")) == {"value": 1, "list": [1, 2, 3]}
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_json_atomic_never_falls_back_to_direct_write(tmp_path, monkeypatch) -> None:
    target = tmp_path / "artifact.json"
    original = {"keeper": True}
    target.write_text(_json.dumps(original), encoding="utf-8")

    failures = {"count": 0}

    def failing_replace(_src, _dst):
        failures["count"] += 1
        raise OSError(28, "simulated persistent replace failure")

    monkeypatch.setattr("pipeline_lifecycle.os.replace", failing_replace)
    monkeypatch.setattr("pipeline_lifecycle.time.sleep", lambda _s: None)

    with pytest.raises(RuntimeError) as excinfo:
        write_json_atomic(target, {"new": "payload"})

    assert "artifact.json" in str(excinfo.value), "error must name the target path"
    assert excinfo.value.__cause__ is not None, "original OSError must be chained"
    assert failures["count"] == 4, "must exhaust the four bounded attempts"
    # 原目标文件字节级保留
    assert _json.loads(target.read_text(encoding="utf-8")) == original
    # 临时文件全部清理
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_json_atomic_concurrent_writers_produce_one_complete_payload(tmp_path) -> None:
    target = tmp_path / "artifact.json"
    payloads = [
        {"writer": index, "blob": [index] * 4000}
        for index in range(6)
    ]
    start = _threading.Barrier(len(payloads))
    errors: list[Exception] = []

    def writer(payload) -> None:
        try:
            start.wait()
            for _ in range(6):
                write_json_atomic(target, payload)
        except Exception as exc:  # noqa: BLE001 - 汇集线程失败
            errors.append(exc)

    threads = [_threading.Thread(target=writer, args=(payload,)) for payload in payloads]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    final = _json.loads(target.read_text(encoding="utf-8"))
    assert final in payloads, "final content must be exactly one complete write, never truncated or mixed"
