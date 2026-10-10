"""Review regressions: real renderer/storage/HTTP/task/export, isolated providers."""

import copy
import io
import json
from pathlib import Path
import time
import uuid

import pytest
from PIL import Image, ImageDraw
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import SessionLocal, Project
from repository_paths import RUNS_DIR
from html_production_service import produce_scene
from html_visual_review_service import (
    HtmlReviewDependencies,
    approve_scene,
    approval_status,
)
from html_visual_store import load_scene_with_revision

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def plan_for(scene, slide_id):
    objects = [
        {"id": n["id"], "slot": n["slot"], "kind": n["type"]} for n in scene["nodes"]
    ]
    slots = {
        n["slot"]: {
            "kind": n["type"],
            **{k: v for k, v in n.items() if k not in ("type", "id", "slot")},
        }
        for n in scene["nodes"]
    }
    beats = [
        {
            "id": f"{slide_id}-beat-{i}",
            "target": {"objectId": obj["id"], "action": "enter"},
        }
        for i, obj in enumerate(objects)
    ]
    assets = [
        {
            "id": n["assetRef"]["id"],
            "slot": n["slot"],
            "role": "科学主体",
            "need": "独立科普主体，透明底",
            "render_owner": "image_asset",
        }
        for n in scene["nodes"]
        if n["type"] == "image"
    ]
    return {
        "slide_id": slide_id,
        "templateRef": scene["templateRef"],
        "slots": slots,
        "objects": objects,
        "beats": beats,
        "assets": assets,
    }, {
        "slide_id": slide_id,
        "narration_beats": [
            {"id": b["id"], "spoken_text": "观察这一变化。"} for b in beats
        ],
    }


def test_five_page_production_uses_three_templates_and_real_assets(tmp_path):
    calls = []
    measurements = []
    for i, name in enumerate(
        [
            "water-facts",
            "condensation",
            "evaporation-process",
            "evaporation",
            "water-facts",
        ]
    ):
        source = json.loads(
            (ROOT / f"html_engine/visual/scenes/{name}.json").read_text(
                encoding="utf-8"
            )
        )
        plan, contract = plan_for(source, f"course-{i}")

        def provider(prompt, **kwargs):
            calls.append(kwargs)
            assert kwargs["reference_paths"] and all(
                Path(p).is_file() for p in kwargs["reference_paths"]
            )
            # Provider boundary is stubbed; PNG/resource loading and rendering are real.
            image = Image.new("RGBA", (128, 128))
            ImageDraw.Draw(image).ellipse((16, 16, 112, 112), fill="#aaccee")
            buffer = io.BytesIO()
            image.save(buffer, "PNG")
            return buffer.getvalue()

        deps = HtmlReviewDependencies(
            repo_root=ROOT, json_generator=lambda **kw: copy.deepcopy(plan)
        )
        started = time.perf_counter()
        result = produce_scene(contract, run_dir=tmp_path, deps=deps, provider=provider)
        measurements.append(
            {
                "slide": contract["slide_id"],
                "seconds": round(time.perf_counter() - started, 3),
                "template": result["scene"]["templateRef"]["id"],
            }
        )
        assert result["review"]["passed"]
        if name == "evaporation-process":
            frozen = json.loads(
                (
                    tmp_path
                    / f"planning/html_visual/candidates/{contract['slide_id']}/freeze.json"
                ).read_text(encoding="utf-8")
            )
            assert len(frozen["keyframes"]) == 3 and all(
                (tmp_path / f["file"]).is_file() for f in frozen["keyframes"]
            )

        assert (
            load_scene_with_revision(tmp_path, contract["slide_id"])["scene"]
            == result["scene"]
        )
        binding = json.loads(
            (
                tmp_path / f"planning/html_visual/binding-{contract['slide_id']}.json"
            ).read_text(encoding="utf-8")
        )
        assert len(binding["actions"]) == len(contract["narration_beats"])
    assert len({m["template"] for m in measurements}) == 3
    assert sum(c["size"] == "1536x1024" for c in calls) == 3
    assert (
        sum(c["size"] == "1024x1024" for c in calls) == 2
    )  # identical source need/ref bytes reuse one asset
    assert all(c["transparent_background"] for c in calls if c["size"] == "1024x1024")
    write(
        tmp_path / "production-benchmark.json",
        {"provider": "stub; renderer real", "pages": measurements},
    )


def test_web_save_account_revision_and_approval_guard(tmp_path, monkeypatch):
    import html_visual_routes as visual
    import html_visual_review_routes as review

    monkeypatch.setattr(
        review,
        "_dependencies",
        review.HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **kw: {}),
    )

    db = SessionLocal()
    pid = "accept-" + uuid.uuid4().hex[:8]
    run = Path(RUNS_DIR) / pid
    db.add(
        Project(
            id=pid,
            name="验收",
            account_id="default",
            visual_backend="html",
            run_dir=str(run),
        )
    )
    db.commit()
    app = FastAPI()
    app.include_router(visual.router)
    app.include_router(review.router)
    app.dependency_overrides[visual._get_db] = lambda: db
    app.dependency_overrides[review._get_db] = lambda: db
    source = json.loads(
        (ROOT / "html_engine/visual/scenes/water-facts.json").read_text(
            encoding="utf-8"
        )
    )
    source["id"] = "s1"
    write(run / "planning/visual_contract.json", {"slides": [{"slide_id": "s1"}]})
    with TestClient(app) as client:
        url = f"/api/projects/{pid}/html-visual/s1"
        first = client.put(url, json={"scene": source, "expected_revision": 0})
        assert first.status_code == 200, first.text
        assert (
            client.put(url, json={"scene": source, "expected_revision": 1}).json()[
                "changed"
            ]
            is False
        )
        assert (
            client.put(url, json={"scene": source, "expected_revision": 0}).status_code
            == 409
        )
        status = client.get(f"/api/projects/{pid}/html-visual/status").json()
        assert status["ready"] is False
        candidate = copy.deepcopy(source)
        candidate["name"] = "未保存修改"
        assert (
            client.post(
                f"/api/projects/{pid}/html-review/s1/approve", json={"scene": candidate}
            ).status_code
            == 409
        )
        from account_context import account_scope

        with account_scope("other"):
            with pytest.raises(Exception) as exc:
                visual._html_project(pid, db)
            assert exc.value.status_code == 404
    db.close()


def test_beat_binding_reacts_to_sentence_timing_not_total_length():
    from html_audio_binder import bind_scene_to_audio

    scene = {
        "durationMs": 10000,
        "motion": [
            {"targetId": "n", "type": "enter", "startMs": 5000, "durationMs": 500}
        ],
    }
    binding = {
        "format": "hps.html.motion_binding",
        "version": "0.1.0",
        "mode": "beat_ids",
        "actions": {"n:enter": {"beatId": "b2", "edge": "start", "offsetMs": 0}},
    }
    times = []
    for start in (1, 8):
        timeline = {
            "audio_content_duration_sec": 10,
            "segments": [{"id": "b2", "start": start, "end": 9, "text": "第二句"}],
        }
        times.append(
            bind_scene_to_audio(scene, timeline, binding)["motion"][0]["startMs"]
        )
    assert times == [1000, 8000]


def test_cancel_rejects_late_success():
    import html_task_store as tasks

    db = SessionLocal()
    task = tasks.submit_task(
        db,
        project_id="accept",
        task_type="html_plan_generate",
        submission_key=uuid.uuid4().hex,
    )
    tasks.mark_running(db, task["id"])
    tasks.cancel_task(db, task["id"])
    with pytest.raises(tasks.HtmlTaskError):
        tasks.mark_succeeded(db, task["id"], {})
    assert tasks.mark_failed(db, task["id"], "late")["status"] == "cancelled"
    db.close()


def test_approval_changes_when_binding_changes_and_ignores_unrelated_assets(tmp_path):
    from html_input_manifest import resolved_scene_inputs

    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/water-facts.json").read_text(
            encoding="utf-8"
        )
    )
    deps = HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **kw: {})
    approve_scene(scene, run_dir=tmp_path, deps=deps)
    assert approval_status(scene, run_dir=tmp_path, deps=deps, slide_id=scene["id"])[
        "valid"
    ]
    write(
        tmp_path / f"planning/html_visual/binding-{scene['id']}.json", {"actions": {}}
    )
    assert not approval_status(
        scene, run_dir=tmp_path, deps=deps, slide_id=scene["id"]
    )["valid"]
    assert not approval_status(None, run_dir=tmp_path, deps=deps, slide_id=scene["id"])[
        "valid"
    ]
    digest = resolved_scene_inputs(scene, tmp_path, ROOT)["digest"]
    write(
        tmp_path / "planning/html_visual/resources.json",
        {"assets": [{"id": "unrelated", "file": "missing.png"}]},
    )
    assert digest == resolved_scene_inputs(scene, tmp_path, ROOT)["digest"]


def test_pptx_real_job_registers_downloadable_artifact():
    from pptx_service import PptxExportService, PptxServiceDependencies
    from html_visual_store import save_scene
    from database import LocalJob

    pid = "pptx-accept-" + uuid.uuid4().hex[:8]
    run = Path(RUNS_DIR) / pid
    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/water-facts.json").read_text(
            encoding="utf-8"
        )
    )
    scene["id"] = "s1"
    write(run / "planning/visual_contract.json", {"slides": [{"slide_id": "s1"}]})
    save_scene(run, "s1", scene, 0)

    class Capture:
        def submit(self, *args):
            self.args = args

    service = PptxExportService(
        PptxServiceDependencies(SessionLocal, Path(RUNS_DIR), Capture(), ROOT)
    )
    db = SessionLocal()
    db.add(
        Project(
            id=pid,
            name="快照导出验收",
            account_id="default",
            visual_backend="html",
            run_dir=str(run),
        )
    )
    db.commit()
    assert service.readiness(db, pid)["ready"] is False
    approve_scene(
        scene,
        run_dir=run,
        deps=HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **kw: {}),
    )
    created = service.create_export(db, pid)
    assert created["job"]["id"] and not created.get("immediate")
    service.run_job(created["job"]["id"])
    db.expire_all()
    job = db.query(LocalJob).filter(LocalJob.id == created["job"]["id"]).one()
    assert job.status == "succeeded", job.error
    path, artifact = service.download_export(db, pid, job.result_artifact_id)
    assert path.is_file() and artifact.id
    assert service.list_exports(db, pid)["artifacts"]
    service.delete_export(db, pid, artifact.id)
    assert not path.exists()
    db.close()


def test_production_job_runs_and_persists_result():
    from html_workflow_jobs import HtmlWorkflowJobs
    from database import LocalJob

    pid = "job-accept-" + uuid.uuid4().hex[:8]
    run = Path(RUNS_DIR) / pid
    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/water-facts.json").read_text(
            encoding="utf-8"
        )
    )
    plan, contract = plan_for(scene, "s1")
    write(run / "planning/visual_contract.json", {"slides": [contract]})
    db = SessionLocal()
    project = Project(
        id=pid,
        name="生产任务验收",
        account_id="default",
        visual_backend="html",
        run_dir=str(run),
    )
    db.add(project)
    db.commit()

    class Capture:
        def submit(self, *args):
            self.args = args

    capture = Capture()
    jobs = HtmlWorkflowJobs(
        SessionLocal,
        HtmlReviewDependencies(
            repo_root=ROOT, json_generator=lambda **kw: copy.deepcopy(plan)
        ),
        executor=capture,
    )
    task = jobs.submit(db, project, contract)
    assert jobs.submit(db, project, contract)["reused"]
    capture.args[0](*capture.args[1:])
    db.expire_all()
    job = db.query(LocalJob).filter(LocalJob.id == task["id"]).one()
    assert job.status == "succeeded", job.error
    assert job.get_payload()["result"]["review"]["passed"]
    db.close()


def test_html_edit_invalidates_both_output_fingerprints(tmp_path):
    from artifact_fingerprint import (
        render_input_fingerprint,
        presentation_input_fingerprint,
    )

    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/water-facts.json").read_text(
            encoding="utf-8"
        )
    )
    write(
        tmp_path / "planning/visual_contract.json",
        {"slides": [{"slide_id": scene["id"]}]},
    )
    path = tmp_path / f"planning/html_visual/scene-{scene['id']}.json"
    write(path, scene)
    before = [
        render_input_fingerprint(tmp_path,visual_settings={},pipeline_version="html-review")["digest"],
        presentation_input_fingerprint(tmp_path)["digest"],
    ]
    scene["name"] = "发生了编辑"
    write(path, scene)
    after = [
        render_input_fingerprint(tmp_path,visual_settings={},pipeline_version="html-review")["digest"],
        presentation_input_fingerprint(tmp_path)["digest"],
    ]
    assert all(a != b for a, b in zip(before, after))


def test_dom_range_handles_multiple_runs_and_emoji(tmp_path):
    import subprocess

    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/condensation.json").read_text(
            encoding="utf-8"
        )
    )
    node = next(n for n in scene["nodes"] if n["id"] == "headline")
    node["runs"] = [
        {"text": "水💧", "emphasis": False},
        {"text": "的变化", "emphasis": True},
    ]
    write(tmp_path / "scene.json", scene)
    write(tmp_path / "range.json", {"nodeId": "headline", "start": 1, "end": 4})
    subprocess.run(
        [
            "node",
            str(ROOT / "html_engine/tools/review-scene.cjs"),
            str(tmp_path / "scene.json"),
            str(tmp_path / "report.json"),
            str(tmp_path / "shot.png"),
            str(tmp_path / "range.json"),
        ],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["passed"] and report["textRange"]["selectedText"] == "💧的变"
    assert report["textRange"]["canvasRects"]


def test_late_old_attempt_cannot_complete_a_retry():
    import html_task_store as tasks

    db = SessionLocal()
    first = tasks.submit_task(
        db,
        project_id="retry-accept",
        task_type="html_plan_generate",
        submission_key=uuid.uuid4().hex,
    )
    tasks.mark_running(db, first["id"], expected_attempt=1)
    tasks.cancel_task(db, first["id"])
    retry = tasks.submit_task(
        db,
        project_id="retry-accept",
        task_type="html_plan_generate",
        submission_key=first["submission_key"],
    )
    assert retry["attempt"] == 2
    tasks.mark_running(db, retry["id"], expected_attempt=2)
    with pytest.raises(tasks.HtmlTaskError):
        tasks.mark_succeeded(db, first["id"], {}, expected_attempt=1)
    assert (
        tasks.mark_failed(db, first["id"], "old error", expected_attempt=1)["status"]
        == "running"
    )
    tasks.mark_succeeded(db, retry["id"], {"ok": True}, expected_attempt=2)
    db.close()
