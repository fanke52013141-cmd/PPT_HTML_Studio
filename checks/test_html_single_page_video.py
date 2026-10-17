"""Edited page -> gated frozen runner -> decoded frames. Synthetic audio only."""

import json
import math
import shutil
import subprocess
from types import SimpleNamespace

from PIL import Image, ImageChops, ImageStat
import pytest

from test_html_formal_export import ROOT, course as course, runner, write, cleanup
from html_build_snapshot import fresh_hash
from html_export_snapshot import verify_course, page_folder, export_env
from html_visual_review_service import approve_scene, HtmlReviewDependencies
from html_visual_store import save_scene
from html_render_runner import HtmlRenderError
from tts_artifacts import build_confirmation_payload


def test_edited_single_page_video_matches_frozen_preview(course):
    run, ids = course
    slide = ids[0]
    contract_path = run / "planning/visual_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["slides"] = contract["slides"][:1]
    write(contract_path, contract)
    write(run / "planning/audio_confirmed.json", build_confirmation_payload(
        run, [slide], confirmation_mode="test_fixture"))
    author_path = run / f"planning/html_visual/scene-{slide}.json"
    author = json.loads(author_path.read_text(encoding="utf-8"))
    author["version"] = "0.5.0"  # Existing legacy compatibility; no semantic approval claim.
    header = next(n for n in author["nodes"] if n["id"] == "header")
    header["presentation"] = {"offsetX": 14, "offsetY": 8}
    binding_path = run / f"planning/html_visual/binding-{slide}.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    binding["actions"]["header:enter"] = {"beatId": "b1", "edge": "start", "offsetMs": 300}
    write(binding_path, binding)
    save_scene(run, slide, author, 3)
    approve_scene(author, run_dir=run,
                  deps=HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **kw: {}),
                  reviewer="test_fixture")
    source_paths = [author_path, binding_path, *sorted((run / "slides" / slide).iterdir())]
    before = {str(p): fresh_hash(p) for p in source_paths}
    production = runner()
    result = production.run(SimpleNamespace(run_dir=str(run)), output_dir=run / "videos",
                            set_stage=lambda stage: None, fps=30)
    try:
        evidence = result.export_evidence
        frozen = ROOT / evidence["course_path"]
        manifest = verify_course(frozen)
        assert len(manifest["pages"]) == 1
        page = page_folder(frozen, manifest["pages"][0])
        bound = json.loads((page / "input/scene.json").read_text(encoding="utf-8"))
        assert bound["nodes"] == author["nodes"]
        assert next(a for a in bound["motion"] if a["targetId"] == "header")["startMs"] == 300
        assert bound["beats"][0]["text"] == "观察变化。"
        audio_probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_format", "-of", "json",
            str(run / "slides" / slide / "voice.mp3")]))
        expected_frames = math.ceil(max(bound["durationMs"] / 1000,
                                       float(audio_probe["format"]["duration"])) * 30)
        assert evidence["validation"]["frames"] == expected_frames
        assert evidence["validation"]["full_decode"] == "passed"
        # Seek identical encoded frame indices, including entry transition and audio tail.
        indices = sorted({0, 9, 15, 24, expected_frames - 1})
        times = [min(bound["durationMs"], round(i * 1000 / 30)) for i in indices]
        shots = run / "comparison"
        shots.mkdir()
        write(shots / "times.json", times)
        subprocess.run(["node", str(frozen / "tools/export-snapshots.cjs"),
                        str(page / "input/scene.json"), str(shots / "times.json"), str(shots)],
                       env=export_env(ROOT, page, production._media_env()),
                       capture_output=True, check=True, timeout=90)
        comparisons = []
        for index, frame in enumerate(indices):
            decoded = shots / f"decoded-{frame}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(result.output_path),
                            "-vf", f"select=eq(n\\,{frame})", "-frames:v", "1", str(decoded)],
                           capture_output=True, check=True, timeout=30)
            with Image.open(shots / f"snapshot-{index:03d}.png") as preview, Image.open(decoded) as video:
                assert preview.size == video.size == (1600, 900)
                difference = ImageStat.Stat(ImageChops.difference(preview.convert("RGB"), video.convert("RGB")))
                mean_error = sum(difference.mean) / 3
                # H.264/YUV420 is lossy; byte equality would be an invalid expectation.
                assert mean_error < 4, (frame, mean_error)
                comparisons.append({"frame": frame, "time_ms": times[index], "rgb_mean_error": mean_error})
        with Image.open(shots / "snapshot-000.png") as first, Image.open(shots / "snapshot-003.png") as later:
            assert sum(ImageStat.Stat(ImageChops.difference(first.convert("RGB"), later.convert("RGB"))).mean) > 1
        assert before == {str(p): fresh_hash(p) for p in source_paths}
        assert not (run / "videos").exists()  # Runner candidate is private until publication gate.
        old_key = evidence["pages"][0]["cache_key"]
        old_output_hash = fresh_hash(result.output_path)
        header["presentation"]["offsetX"] = 28
        save_scene(run, slide, author, 4)
        with pytest.raises(HtmlRenderError, match="GATES_REQUIRED"):
            production.run(SimpleNamespace(run_dir=str(run)), output_dir=run / "videos",
                           set_stage=lambda stage: None, fps=30)
        assert fresh_hash(result.output_path) == old_output_hash
        # Explicit fixture review only; production never manufactures approval on edit.
        approve_scene(author, run_dir=run,
                      deps=HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **kw: {}),
                      reviewer="test_fixture")
        rebuilt = production.run(SimpleNamespace(run_dir=str(run)), output_dir=run / "videos",
                                 set_stage=lambda stage: None, fps=30)
        try:
            assert rebuilt.export_evidence["pages"][0]["cache_key"] != old_key
            assert rebuilt.export_evidence["pages"][0]["reused"] is False
            assert fresh_hash(rebuilt.output_path) != old_output_hash
        finally:
            cleanup(rebuilt)
        output = ROOT / "outputs/single-page-video/2026-10-17"
        output.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(result.output_path, output / "single-page-fixture.mp4")
        shutil.copyfile(shots / "snapshot-003.png", output / "preview.png")
        shutil.copyfile(shots / f"decoded-{indices[3]}.png", output / "video-frame.png")
        write(output / "evidence.json", {"status": "engineering_passed", "audio": "synthetic silence",
              "scene_version": author["version"], "real_course_acceptance": "not_run",
              "snapshot_id": manifest["snapshot_id"], "validation": evidence["validation"],
              "comparisons": comparisons, "render_source_unchanged": True,
              "edit_invalidates_approval": True, "reapproved_edit_rebuilds_segment": True})
    finally:
        cleanup(result)
