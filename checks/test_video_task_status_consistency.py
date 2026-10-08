"""视频任务内存状态与持久任务状态的一致性回归。

历史缺陷（2026-09-26 审查 N3）：worker 领取任务后只调 _set_task_stage
（stage + 持久层 running），内存 status 永远停留在创建时的 "queued"——
整个渲染期间 render_status 返回 "queued"，前端始终显示"排队中"，
elapsed 的 rendering 分支永不命中，且 _prune_tasks_locked 的运行中
保护集合恒为空，活动任务同样可能被逐出内存。
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from database import utc_now_naive
from remotion_runner import RemotionRenderResult
from video_contracts import VideoRenderConfig
from video_render_service import (
    VideoRenderDependencies,
    VideoRenderService,
)


def _config(tmp_path: Path) -> VideoRenderConfig:
    return VideoRenderConfig(
        repo_root=tmp_path,
        runs_root=tmp_path,
        pipeline_version="test-pipeline",
        reveal_visual_lead_sec=0.2,
        bind_timeout_sec=1,
        build_props_timeout_sec=1,
        npm_install_timeout_sec=1,
        render_timeout_sec=1,
        color_process_timeout_sec=1,
    )


class _RecordingJobStore:
    """记录 update 调用并支持预置 get 返回值的 job_store 替身。"""

    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.get_result = None

    def update(self, _job_id, **kwargs):
        self.updates.append(kwargs)
        return None

    def get(self, _job_id, project_id=None):
        return self.get_result


def _build_service(tmp_path: Path, output_path: Path, job_store) -> tuple:
    project = SimpleNamespace(
        id="project-test",
        run_dir=str(tmp_path),
        created_at=utc_now_naive() - timedelta(hours=1),
    )
    commits: list[bool] = []

    class FakeDb:
        def query(self, *_args):
            return self

        def filter(self, *_args):
            return self

        def first(self):
            return project

        def commit(self):
            commits.append(True)

        def close(self):
            return None

    class FakeArtifacts:
        def project_video_dir(self, _project):
            return output_path.parent

        def current_render_input_fingerprint(self, _project):
            return {"digest": "fingerprint"}

        def visual_settings(self, _project):
            return {
                "video_background": "#FEFDF9",
                "subtitle_style": {"font_size": 48},
            }

        def record_rendered_video(self, _db, _project, _path, _filename, **_kwargs):
            return SimpleNamespace(id="artifact-test")

        def video_item(self, _project, path, *_args):
            return {"filename": Path(path).name}

        def list_video_items(self, _project):
            return [{"filename": output_path.name}]

    status_during_run: list[str] = []

    class FakeRunner:
        def run(self, _project, *, output_dir, set_stage):
            assert output_dir == output_path.parent
            status_during_run.append(service._tasks["task-test"]["status"])
            set_stage("rendering")
            return RemotionRenderResult(
                output_path=output_path,
                output_filename=output_path.name,
                color_validation={"ok": True},
            )

    service = VideoRenderService(
        VideoRenderDependencies(
            session_factory=FakeDb,
            artifact_service=FakeArtifacts(),
            remotion_runner=FakeRunner(),
            config=_config(tmp_path),
        )
    )
    service.job_store = job_store
    return service, project, status_during_run, commits


def _seed_queued_task(service: VideoRenderService, project_id: str) -> None:
    service._tasks["task-test"] = {
        "task_id": "task-test",
        "project_id": project_id,
        "status": "queued",
        "stage": "validating",
        "started_at": 0.0,
        "finished_at": None,
        "elapsed_sec": 0.0,
        "error": None,
        "video": None,
        "videos": None,
        "output_filename": None,
    }


def test_worker_flips_memory_status_to_rendering_and_persists_running(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "videos" / "render_test.mp4"
    output_path.parent.mkdir()
    output_path.write_bytes(b"video")
    job_store = _RecordingJobStore()
    service, project, status_during_run, commits = _build_service(
        tmp_path, output_path, job_store
    )
    _seed_queued_task(service, project.id)
    monkeypatch.setattr(
        "video_render_service.invalidation_service.complete_stage",
        lambda value, stage: None,
    )

    service.run_render_job(project.id, "task-test")

    # 渲染执行期间内存状态必须是 rendering（而非创建时的 queued）
    assert status_during_run == ["rendering"]
    # 持久层必须收到 running
    assert any(
        update.get("status") == "running" for update in job_store.updates
    )
    assert service._tasks["task-test"]["status"] == "success"
    assert commits == [True]


def test_prune_preserves_queued_and_running_tasks(tmp_path: Path) -> None:
    output_path = tmp_path / "videos" / "render_test.mp4"
    output_path.parent.mkdir()
    output_path.write_bytes(b"video")
    service, project, _status, _commits = _build_service(
        tmp_path, output_path, _RecordingJobStore()
    )

    base = {
        "task_id": "",
        "project_id": project.id,
        "stage": "completed",
        "started_at": 0.0,
        "finished_at": None,
        "elapsed_sec": 1.0,
        "error": None,
        "video": None,
        "videos": None,
        "output_filename": None,
    }
    service._tasks["task-queued"] = {
        **base, "task_id": "task-queued", "status": "queued",
    }
    service._tasks["task-rendering"] = {
        **base, "task_id": "task-rendering", "status": "rendering",
    }
    for index in range(50):
        service._tasks[f"task-done-{index:02d}"] = {
            **base,
            "task_id": f"task-done-{index:02d}",
            "status": "success",
            "finished_at": float(index),
        }

    with service._tasks_lock:
        service._prune_tasks_locked()

    assert "task-queued" in service._tasks
    assert "task-rendering" in service._tasks
    # 50 个终态 + 2 个活动 = 52 > 50：为保住 2 个活动任务，最老的 2 个终态
    # 被逐出，其余终态与全部活动任务保留在 50 上限内
    assert "task-done-00" not in service._tasks
    assert "task-done-01" not in service._tasks
    assert "task-done-02" in service._tasks
    assert "task-done-49" in service._tasks
    assert len(service._tasks) == 50


def test_render_status_prefers_persistent_terminal_over_stale_memory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "videos" / "render_test.mp4"
    output_path.parent.mkdir()
    output_path.write_bytes(b"video")
    job_store = _RecordingJobStore()
    service, project, _status, _commits = _build_service(
        tmp_path, output_path, job_store
    )
    _seed_queued_task(service, project.id)
    started = utc_now_naive() - timedelta(minutes=2)
    finished = utc_now_naive() - timedelta(minutes=1)
    job_store.get_result = SimpleNamespace(
        id="task-test",
        project_id=project.id,
        status="succeeded",
        stage="completed",
        progress=100,
        error=None,
        started_at=started,
        created_at=started,
        finished_at=finished,
        result_artifact_id="artifact-x",
        payload_json="{}",
        get_payload=lambda: {},
    )
    monkeypatch.setattr(
        service,
        "get_project",
        lambda _db, _project_id: project,
    )
    monkeypatch.setattr(
        service,
        "list_video_items",
        lambda _project: [],
    )

    class NullDb:
        def close(self):
            return None

    result = service.render_status(NullDb(), project.id)

    # 内存快照仍是 queued，但持久层已是终态：查询必须以持久任务为准
    assert result["status"] == "success"
    assert result["task_id"] == "task-test"
