import json
from pathlib import Path
import html_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]


def probe(spec):
    return {"browser": True, "font": True, "scene_passed": True, "executable": "test-browser"}


def test_existing_assets_still_require_full_design_image(tmp_path):
    report = preflight.inspect_html_preflight("generate_existing", output_dir=tmp_path,
        model_readiness={"text": True, "image": False}, probe=probe)
    assert not report["ready"]
    assert not report["provider_connection_tested"]
    assert any(c["code"] == "IMAGE_MODEL_CONFIGURED" and not c["passed"] for c in report["checks"])
    assert not {"AUDIO_CONFIRMED", "FFMPEG"} & {c["code"] for c in report["checks"]}


def test_new_images_require_config_and_static_does_not(tmp_path):
    a = preflight.inspect_html_preflight("generate_new_images", output_dir=tmp_path,
        model_readiness={"text": True}, probe=probe)
    assert not a["ready"]
    assert any(c["code"] == "IMAGE_MODEL_CONFIGURED" and not c["passed"] for c in a["checks"])
    assert preflight.inspect_html_preflight("static_html", output_dir=tmp_path, probe=probe)["ready"]


def test_font_failure_and_space_budget_block(tmp_path):
    report = preflight.inspect_html_preflight("snapshot_pptx", scene={"id": "test"},
        output_dir=tmp_path, min_free_bytes=10**30,
        probe=lambda _: {"browser": True, "font": False, "scene_passed": True})
    failures = {c["code"] for c in report["checks"] if not c["passed"]}
    assert {"FONT", "DISK_SPACE"} <= failures
    assert not list(tmp_path.iterdir())


def test_invalid_scene_and_missing_output_rejected(tmp_path):
    report = preflight.inspect_html_preflight("static_html", scene={"themeRef": {"id": "../bad"}},
        output_dir=tmp_path / "absent", probe=probe)
    assert not report["ready"]
    assert not (tmp_path / "absent").exists()


def test_video_requires_real_confirmation_and_no_server_import(tmp_path):
    import sys
    original = sys.modules.get("server")
    report = preflight.inspect_html_preflight("video", output_dir=tmp_path, probe=probe)
    assert not report["ready"]
    assert any(c["code"] == "AUDIO_CONFIRMED" and not c["passed"] for c in report["checks"])
    assert sys.modules.get("server") is original


def test_fresh_process_never_imports_composition_root():
    import subprocess, sys
    program = "import html_preflight,sys; html_preflight.inspect_html_preflight('video',probe=lambda s: {'browser':True,'font':True}); assert 'server' not in sys.modules; assert 'database' not in sys.modules"
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", program], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr


def test_video_confirmation_uses_current_whole_slide_set(tmp_path, monkeypatch):
    import tts_artifacts, html_creation_workflow
    planning = tmp_path / "planning"
    planning.mkdir()
    (planning / "visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": "one"}, {"slide_id": "two"}]}))
    called = []
    def confirmation(run, ids):
        called.append(ids)
        return {"confirmed": True}
    monkeypatch.setattr(tts_artifacts, "confirmation_status", confirmation)
    monkeypatch.setattr(html_creation_workflow, "_validate_slide_binding", lambda *args: [])
    report = preflight.inspect_html_preflight("video", run_dir=tmp_path, scene={"id": "one"}, probe=probe)
    assert called == [["one", "two"]]
    assert next(c for c in report["checks"] if c["code"] == "AUDIO_CONFIRMED")["passed"]
    assert not report["approval_granted"]


def test_real_browser_and_registered_font():
    report = preflight.inspect_html_preflight("static_html")
    assert report["ready"], report


def test_real_font_absence_blocks(tmp_path, monkeypatch):
    import shutil
    theme_root = tmp_path / "repo/html_engine/visual/themes"
    theme_root.mkdir(parents=True)
    # Copy only runtime prerequisites: prove local font failure with actual browser.
    shutil.copytree(ROOT / "html_engine/tools", tmp_path / "repo/html_engine/tools")
    shutil.copytree(ROOT / "html_engine/visual/preview", theme_root.parent / "preview")
    shutil.copytree(ROOT / "html_engine/visual/generated", theme_root.parent / "generated")
    shutil.copy(ROOT / "html_engine/visual/schema.json", theme_root.parent / "schema.json")
    monkeypatch.setenv("NODE_PATH", str(ROOT / "html_engine/node_modules"))
    (theme_root / "neutral-baseline.json").write_text(json.dumps({"font": {"family": "HPSMissingFont012345"}}))
    report = preflight.inspect_html_preflight("static_html", repo_root=tmp_path / "repo")
    assert any(c["code"] == "FONT" and not c["passed"] for c in report["checks"])
    assert any(c["code"] == "BROWSER" and c["passed"] for c in report["checks"])


def test_secret_input_cli_not_echoed(tmp_path):
    import subprocess, sys
    request = tmp_path / "config.json"
    request.write_text(json.dumps({"api_key": "secret-never-print"}))
    result = subprocess.run([sys.executable, "-X", "utf8", "scripts/ppt_studio_doctor.py", "--html-target", "static_html",
        "--model-readiness", str(request), "--json"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 1
    assert "secret-never-print" not in result.stdout + result.stderr
    assert json.loads(result.stdout)["checks"][0]["code"] == "REQUEST_INVALID"
