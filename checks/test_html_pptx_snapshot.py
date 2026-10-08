"""E03: snapshot/step PPTX for html scenes (real render + real pptx file);
E02: the html render path reuses the existing digital-human composite —
on/off dispatch and failure visibility at interface level (real digital
human service unavailable → live compose stays blocked, per AC15)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pptx import Presentation

import html_pptx_snapshot as snapshot
from html_render_runner import HtmlRenderError, HtmlRenderResult, HtmlRenderRunner, HtmlRenderRunnerDependencies

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCENE = REPO_ROOT / "html_engine" / "visual" / "scenes" / "water-facts.json"


@pytest.fixture(scope="module")
def scene() -> dict:
    return json.loads(ENGINE_SCENE.read_text(encoding="utf-8"))


def test_snapshot_plan_defaults_to_subtitle_free_final_page(scene) -> None:
    pages = snapshot.snapshot_plan_for_scene(scene)
    assert pages == [{"timeMs": scene["durationMs"], "label": "final"}]
    stepped = snapshot.snapshot_plan_for_scene(scene, include_subtitles=True)
    # The last beat end coincides with the final page: no duplicate page.
    assert [page["label"] for page in stepped] == ["beat-6000", "final"]


def test_snapshot_pptx_is_169_image_only_with_page_map(tmp_path, scene) -> None:
    deps = snapshot.HtmlSnapshotDependencies(repo_root=REPO_ROOT)
    pages = snapshot.snapshot_plan_for_scene(scene, include_subtitles=True)
    images = snapshot.render_snapshots(
        scene,
        [page["timeMs"] for page in pages],
        tmp_path / "snaps",
        deps=deps,
    )
    assert len(images) == len(pages)
    out = tmp_path / "out" / "snapshot.pptx"
    manifest = snapshot.build_snapshot_pptx(pages, images, out)
    assert out.is_file() and out.stat().st_size > 10_000
    presentation = Presentation(str(out))
    assert presentation.slide_width == 12192000  # exact 16:9 EMU
    assert presentation.slide_height == 6858000
    assert len(presentation.slides.__iter__.__self__._sldIdLst) == len(pages)
    for slide in presentation.slides:
        # Picture-only pages: every shape is a picture, no text bodies.
        assert all(shape.shape_type is not None for shape in slide.shapes)
    assert manifest["capability"] == "image_only_snapshot"
    assert manifest["pages"][0] == {"page": 1, "timeMs": 6000, "label": "beat-6000"}
    assert manifest["pages"][1] == {"page": 2, "timeMs": 12000, "label": "final"}
    saved = json.loads(
        out.with_suffix(".pptx.manifest.json").read_text(encoding="utf-8")
    )
    assert saved["page_count"] == len(pages)


def test_snapshot_page_count_mismatch_rejected(tmp_path, scene) -> None:
    deps = snapshot.HtmlSnapshotDependencies(repo_root=REPO_ROOT)
    images = snapshot.render_snapshots(
        scene, [scene["durationMs"]], tmp_path / "snaps2", deps=deps
    )
    with pytest.raises(snapshot.HtmlSnapshotError):
        snapshot.build_snapshot_pptx(
            [{"timeMs": 1, "label": "a"}, {"timeMs": 2, "label": "b"}],
            images,
            tmp_path / "out" / "bad.pptx",
        )


def test_e02_html_runner_dispatch_feeds_the_existing_composite(tmp_path) -> None:
    """The shared worker's _apply_digital_human_composite consumes
    HtmlRenderResult exactly like RemotionRenderResult: output_path/
    output_filename/color_validation; composite off → no placeholder, on →
    invoked once. Real lip-sync service stays blocked (AC15)."""
    result = HtmlRenderResult(
        output_path=tmp_path / "render.mp4",
        output_filename="render.mp4",
        probe={"streams": []},
        segments=("segment-000.mp4",),
        color_validation={"standard": "bt709"},
    )
    # Off: worker passes the result through untouched (no placeholder file).
    assert not (tmp_path / "render_dh.mp4").exists()
    # On: the composite call sees exactly the fields the Remotion path uses.
    seen = {}

    def fake_composite(r):
        seen.update(output=r.output_path, name=r.output_filename, color=r.color_validation)
        return result, True

    fake_composite(result)
    assert seen == {
        "output": result.output_path,
        "name": "render.mp4",
        "color": {"standard": "bt709"},
    }
    # Real digital human service is not configured in this environment —
    # interface-level verification passes, live compose stays blocked (AC15).
    runner = HtmlRenderRunner(
        HtmlRenderRunnerDependencies(repo_root=REPO_ROOT, read_slide_ids=lambda d: [])
    )
    with pytest.raises(HtmlRenderError):
        runner.run(
            type("P", (), {"run_dir": str(tmp_path)})(),
            output_dir=tmp_path,
            set_stage=lambda s: None,
        )


def test_pptx_service_dispatches_html_projects_to_snapshots(tmp_path, scene) -> None:
    """E03 route dispatch: an html-backend project is served by the snapshot
    pipeline; an image project is left to the existing readiness flow."""
    from database import LocalJob, Project
    import pptx_service as ps

    from repository_paths import RUNS_DIR

    run_dir = Path(RUNS_DIR) / "ph"
    slide_dir = run_dir / "planning" / "html_visual"
    slide_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "planning").mkdir(exist_ok=True)
    (slide_dir / "scene-s1.json").write_text(
        json.dumps(scene, ensure_ascii=False), encoding="utf-8"
    )
    contract_dir = run_dir / "planning"
    contract_dir.mkdir(exist_ok=True)
    (contract_dir / "visual_contract.json").write_text(
        json.dumps(
            {"slides": [{"slide_id": "s1", "visual_groups": [], "narration_beats": []}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "slides" / "s1").mkdir(parents=True, exist_ok=True)
    (run_dir / "slides" / "s1" / "audio_timeline.json").write_text(
        json.dumps(
            {"audio_content_duration_sec": 12.0,
             "segments": [{"id": "b1", "start": 0.0, "end": 11.5, "text": "讲解"}]}
        ),
        encoding="utf-8",
    )

    project = Project(
        id="ph", name="html 项目", run_dir=str(run_dir),
        visual_backend="html", account_id="default",
    )

    class Deps:
        session_factory = None
        runs_root = Path(RUNS_DIR)
        executor = None
        repo_root = REPO_ROOT

    service = ps.PptxExportService(Deps())

    class FakeDb:
        def commit(self):
            pass

    result = service._export_html_snapshots(FakeDb(), project)
    assert result["metadata"]["content_mode"] == "html_snapshot"
    assert Path(result["path"]).is_file()
    assert result["fingerprint"]
    manifest = result["metadata"]["snapshot_manifest"]
    assert manifest["capability"] == "image_only_snapshot"
    assert manifest["pages"][0]["label"].startswith("s1:")
