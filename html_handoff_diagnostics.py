"""Original shared-player diagnosis and bounded feedback, never save eligibility."""
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import uuid
import zipfile

import html_scene_editing as editor
import html_visual_store as store

ROOT = Path(__file__).resolve().parent


def diagnose(run, slide, scene, binding, revision, audio):
    directory = Path(run) / store.SCENE_DIR / "handoff-diagnostics" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    try:
        preview = editor.preview_editor(run, slide, scene, binding, expected_revision=revision, expected_audio_revision=audio)
        source = directory / "scene.json"
        source.write_text(json.dumps(preview["scene"], ensure_ascii=False), encoding="utf-8")
        env = {**os.environ, "HPS_CANDIDATE_DIAGNOSTIC": "1"}
        env.pop("HPS_HTML_RESOURCES", None)
        resources = Path(run) / store.SCENE_DIR / "resources.json"
        if resources.is_file():
            env["HPS_HTML_RESOURCES"] = str(resources.resolve())
        process = subprocess.run(["node", str(ROOT / "html_engine/tools/review-scene.cjs"), str(source),
                                  str(directory / "report.json"), str(directory / "frame.png")],
                                 cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
        report = editor.read_json(directory / "report.json", {})
        if not report or process.returncode:
            return {"passed": False, "diagnosticOnly": True, "issues": [], "unavailable": "original_diagnostic_failed"}
        shots = []
        if (directory / "frame.png").is_file():
            shots.append({"timeMs": scene["durationMs"], "file": (directory / "frame.png").relative_to(run).as_posix()})
        return {"passed": False, "diagnosticOnly": True, "issues": report.get("capacityIssues", []),
                "capacity_measurements": report.get("capacityMeasurements", {}), "screenshots": shots,
                "message": report.get("message"), "not_run": ["sampled_overlap", "human_approval", "audio_sync"]}
    except (editor.SceneEditError, OSError, ValueError, subprocess.SubprocessError) as exc:
        return {"passed": False, "diagnosticOnly": True, "issues": [], "unavailable": str(exc)[:1200]}


def pictures(run, shots):
    root = Path(run).resolve()
    images = []
    for shot in shots[:3]:
        path = (root / shot["file"]).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        images.append({"timeMs": shot["timeMs"], "image": "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()})
    return images


def feedback_bundle(run, feedback, diagnostic=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("system-feedback.json", json.dumps(feedback, ensure_ascii=False, indent=2))
        archive.writestr("READ-ME.md", "# 原系统真实反馈\n保持原task_id与原始输入，修订完整候选后重新运行官方预检。\n诊断图不等于检查通过；仅按当前任务约定轮数执行，不保存/批准或扩大范围。\n")
        if diagnostic:
            archive.writestr("candidate-diagnostics.json", json.dumps(diagnostic, ensure_ascii=False, indent=2))
            for index, shot in enumerate(pictures(run, diagnostic.get("screenshots", []))):
                archive.writestr(f"diagnostic-only-{index}-{shot['timeMs']}.png", base64.b64decode(shot["image"].split(",", 1)[1]))
    return base64.b64encode(buffer.getvalue()).decode()
