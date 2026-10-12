"""Conditional registration and final-after-composition verification at the worker boundary."""

from types import SimpleNamespace

import pytest

from html_render_runner import HtmlRenderResult
from test_video_task_status_consistency import (
    _build_service,
    _RecordingJobStore,
    _seed_queued_task,
)


@pytest.mark.parametrize("historical", [False, True])
def test_frozen_video_registers_history_without_current_override(
    tmp_path, monkeypatch, historical
):
    videos = tmp_path / "videos"
    videos.mkdir()
    legacy = tmp_path / "out.mp4"
    legacy.write_bytes(b"prior approved output")
    work = tmp_path / "planning/html_visual/export-work/video-owned"
    work.mkdir(parents=True)
    candidate = work / "candidate.mp4"
    candidate.write_bytes(b"validated candidate")
    other = work.parent / "video-other"
    other.mkdir()
    (other / "keep.txt").write_text("another run")
    service, project, _, commits = _build_service(
        tmp_path, videos / candidate.name, _RecordingJobStore()
    )
    service.dependencies.session_factory.refresh = lambda self, project: None
    project.visual_backend = "html"
    current = {
        "digest": "current",
        "visual_settings": service.artifacts.visual_settings(project),
    }
    frozen = {**current, "digest": "previous" if historical else "current"}
    service.artifacts.current_render_input_fingerprint = lambda project: current
    evidence = {
        "snapshot_id": "test-course",
        "runtime": {},
        "fingerprint": frozen,
        "frozen_run_dir": str(tmp_path / "frozen-run"),
        "course_path": "test-course",
        "work_dir": str(work),
        "validation": {"fps": 30, "frames": 30},
    }
    result = HtmlRenderResult(candidate, candidate.name, {}, (), {}, evidence)
    html_runner = SimpleNamespace(run=lambda *args, **kwargs: result)
    object.__setattr__(service.dependencies, "html_runner", html_runner)
    registrations, completions, defaults, composite_inputs = [], [], [], []

    def register(db, project, path, filename, **kwargs):
        registrations.append(kwargs)
        assert path.parent == videos and path.read_bytes() == b"validated candidate"
        return SimpleNamespace(id="frozen-artifact")

    service.artifacts.record_rendered_video = register
    service.artifacts.publish_default = lambda project, path: defaults.append(path)
    service._apply_digital_human_composite = lambda project, result, task: (
        composite_inputs.append(project.run_dir) or result,
        True,
    )
    monkeypatch.setattr("html_export_snapshot.verify_course", lambda folder: {})
    monkeypatch.setattr(
        "html_export_snapshot.verify_runtime_identity", lambda identity: None
    )
    checks = []

    def final_check(runner, path, fps, frames):
        checks.append(path)
        assert composite_inputs  # must follow the last composite
        return {}, {"full_decode": "passed"}

    monkeypatch.setattr("html_frozen_video.validate_video", final_check)
    monkeypatch.setattr(
        "video_render_service.invalidation_service.complete_stage",
        lambda *args: completions.append(args),
    )
    _seed_queued_task(service, project.id)
    service.run_render_job(project.id, "task-test")
    assert service._tasks["task-test"]["status"] == "success"
    assert registrations[0]["make_current"] is False  # default swap is after DB commit
    assert registrations[0]["render_fingerprint"] == frozen
    assert registrations[0]["render_metadata"]["historical"] is historical
    assert bool(defaults) is (not historical) and bool(completions) is (not historical)
    assert checks == [candidate]
    assert composite_inputs == [evidence["frozen_run_dir"]]
    assert not work.exists() and (other / "keep.txt").exists()
    assert legacy.read_bytes() == b"prior approved output"


def test_corrupt_final_composite_is_not_registered(tmp_path, monkeypatch):
    work = tmp_path / "planning/html_visual/export-work/video-owned"
    work.mkdir(parents=True)
    candidate = work / "candidate.mp4"
    candidate.write_bytes(b"corrupt composite")
    legacy = tmp_path / "out.mp4"
    legacy.write_bytes(b"old")
    service, project, _, _ = _build_service(
        tmp_path, tmp_path / "videos/candidate.mp4", _RecordingJobStore()
    )
    service.dependencies.session_factory.refresh = lambda self, project: None
    project.visual_backend = "html"
    result = HtmlRenderResult(
        candidate,
        candidate.name,
        {},
        (),
        {},
        {
            "fingerprint": {"digest": "old"},
            "frozen_run_dir": "frozen",
            "course_path": "course",
            "work_dir": str(work),
            "validation": {"fps": 30, "frames": 30},
        },
    )
    object.__setattr__(
        service.dependencies,
        "html_runner",
        SimpleNamespace(run=lambda *args, **kwargs: result),
    )
    service._apply_digital_human_composite = lambda *args: (result, True)
    service.artifacts.record_rendered_video = lambda *args, **kwargs: pytest.fail(
        "bad file registered"
    )
    monkeypatch.setattr(
        "html_frozen_video.validate_video",
        lambda *args: (_ for _ in ()).throw(ValueError("decode failed")),
    )
    _seed_queued_task(service, project.id)
    service.run_render_job(project.id, "task-test")
    assert service._tasks["task-test"]["status"] == "error"
    assert legacy.read_bytes() == b"old" and not work.exists()


def test_history_artifact_is_persisted_without_changing_default(tmp_path):
    from database import Base, Project, ArtifactRecord
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from video_artifact_service import VideoArtifactService, VideoArtifactDependencies

    engine = create_engine(f"sqlite:///{tmp_path / 'artifacts.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    run = tmp_path / "p"
    (run / "videos").mkdir(parents=True)
    project = Project(
        id="p",
        account_id="default",
        name="fixture",
        run_dir=str(run),
        visual_backend="html",
    )
    db.add(project)
    db.commit()
    candidate = run / "videos/historical.mp4"
    candidate.write_bytes(
        b"verified old version"
    )  # registry test; media validation is covered separately
    legacy = run / "out.mp4"
    legacy.write_bytes(b"current default")
    service = VideoArtifactService(
        VideoArtifactDependencies(
            tmp_path,
            "test",
            60,
            lambda p: {},
            lambda *args: "",
            lambda *args: {},
            lambda name: name,
        )
    )
    artifact = service.record_rendered_video(
        db,
        project,
        candidate,
        candidate.name,
        render_metadata={"historical": True},
        render_fingerprint={"digest": "old"},
        make_current=False,
    )
    db.commit()
    stored = db.query(ArtifactRecord).filter_by(id=artifact.id).one()
    assert stored.get_source_fingerprint() == {"digest": "old"}
    assert stored.get_metadata()["historical"] is True
    assert legacy.read_bytes() == b"current default"
    db.close()


def test_pptx_old_result_is_history_and_does_not_complete_current_stage(
    tmp_path, monkeypatch
):
    import json
    from database import Base, Project, LocalJob, ArtifactRecord
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from artifact_fingerprint import presentation_input_fingerprint
    from pptx_service import PptxExportService, PptxServiceDependencies

    engine = create_engine(f"sqlite:///{tmp_path / 'jobs.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    run = tmp_path / "p"
    (run / "planning").mkdir(parents=True)
    contract = run / "planning/visual_contract.json"
    contract.write_text(json.dumps({"slides": [{"slide_id": "s1"}]}), encoding="utf-8")
    frozen = presentation_input_fingerprint(run)
    db = sessions()
    db.add(
        Project(
            id="p",
            account_id="default",
            name="fixture",
            run_dir=str(run),
            visual_backend="html",
        )
    )
    db.add(
        LocalJob(
            id="j",
            project_id="p",
            job_type="pptx_export",
            status="queued",
            stage="queued",
            progress=0,
            payload_json=json.dumps(
                {
                    "filename": "old.pptx",
                    "mode": "html_snapshot",
                    "input_digest": frozen["digest"],
                    "account_id": "default",
                }
            ),
        )
    )
    db.commit()
    service = PptxExportService(
        PptxServiceDependencies(session_factory=sessions, runs_root=tmp_path)
    )
    service._project_export_readiness = lambda project: (None, {"ready": True})

    def export(*args):
        contract.write_text(
            json.dumps({"slides": [{"slide_id": "s2"}]}), encoding="utf-8"
        )
        output = run / "presentations/old.pptx"
        output.parent.mkdir()
        output.write_bytes(b"valid mocked archive")
        return {
            "path": str(output),
            "filename": output.name,
            "size_bytes": output.stat().st_size,
            "fingerprint": frozen,
            "metadata": {"content_mode": "html_snapshot"},
        }

    service._export_html_snapshots = export
    monkeypatch.setattr(
        "pptx_service.invalidation_service.complete_stage",
        lambda *args: pytest.fail("old input completed current stage"),
    )
    service.run_job("j")
    db.expire_all()
    job = db.query(LocalJob).filter_by(id="j").one()
    assert job.status == "succeeded"
    artifact = db.query(ArtifactRecord).filter_by(id=job.result_artifact_id).one()
    assert (
        artifact.get_source_fingerprint() == frozen
        and artifact.get_metadata()["historical"] is True
    )
    db.close()


def test_succeeded_task_reuse_rechecks_final_file_and_exporter(tmp_path, monkeypatch):
    import json
    from html_build_snapshot import fresh_hash

    path = tmp_path / "videos/result.mp4"
    path.parent.mkdir()
    path.write_bytes(b"verified media")
    service, project, _, _ = _build_service(tmp_path, path, _RecordingJobStore())
    service.dependencies.session_factory.refresh = lambda self, project: None
    project.visual_backend = "html"
    service.project_video_file = lambda *args: path
    sidecar = path.with_suffix(".render.json")
    service.artifacts.video_metadata_path = lambda p: sidecar
    tool = tmp_path / "html_engine/tools/export-slide-video.cjs"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"fixed exporter")
    manifest = {
        "files": [{"path": "tools/export-slide-video.cjs", "sha256": fresh_hash(tool)}]
    }
    metadata = {
        "export_evidence": {
            "snapshot_id": "fixture",
            "runtime": {},
            "fingerprint": {"digest": "fingerprint"},
            "validation": {"fps": 30, "frames": 30},
            "final_validation": {"sha256": fresh_hash(path)},
        }
    }
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr("html_export_snapshot.verify_course", lambda folder: manifest)
    monkeypatch.setattr(
        "html_export_snapshot.verify_runtime_identity", lambda identity: None
    )
    decodes = []
    monkeypatch.setattr(
        "html_frozen_video.validate_video", lambda *args: decodes.append(True)
    )
    job = SimpleNamespace(
        status="succeeded", get_payload=lambda: {"output_filename": path.name}
    )
    assert service._can_reuse_submission(project, job)
    assert decodes == [True]
    path.write_bytes(b"corrupt middle")
    assert not service._can_reuse_submission(project, job)
    assert decodes == [True]
    path.write_bytes(b"verified media")
    tool.write_bytes(b"new exporter")
    assert not service._can_reuse_submission(project, job)
    tool.write_bytes(b"fixed exporter")
    monkeypatch.setattr(
        "html_frozen_video.validate_video",
        lambda *args: (_ for _ in ()).throw(ValueError("corrupt decode")),
    )
    assert not service._can_reuse_submission(project, job)
