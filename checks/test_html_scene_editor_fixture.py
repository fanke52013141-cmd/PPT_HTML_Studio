"""Isolated browser fixture server, never the application service or database."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def fixture_scene(*, semantic=False, presentation=False):
    root = Path(__file__).resolve().parents[1]
    scene = json.loads((root / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    if semantic or presentation:
        scene["version"] = "0.7.0" if presentation else "0.6.0"
        scene["initialVisibleIds"] = []
        for index, action in enumerate(scene["motion"]):
            action["actionId"] = f"fixture-action-{index}"
    if presentation:
        scene["nodes"][0]["presentation"] = {"variant": "header-badge"}
        next(n for n in scene["nodes"] if n["id"] == "headline")["presentation"] = {"variant": "text-emphasis-bold"}
    return scene


def main():
    import hashlib
    import os
    import io
    from PIL import Image

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    run = Path(sys.argv[1]).resolve()
    # The caller supplies a freshly-created OS temporary directory.
    if not run.name.startswith("hps-editor-browser-"):
        raise ValueError("isolated temporary fixture path required")
    os.environ["PPT_STUDIO_DB_PATH"] = str(run / "unused.db")
    os.environ["PPT_STUDIO_RUNS_DIR"] = str(run / "runs")
    import html_scene_editing as edit
    import html_visual_store as store
    from pipeline_lifecycle import project_artifact_lock

    presentation = "--presentation" in sys.argv[2:]
    no_audio = "--no-audio" in sys.argv[2:]
    semantic = "--semantic" in sys.argv[2:] or presentation
    scene = fixture_scene(semantic=semantic, presentation=presentation)
    store.save_scene(run, scene["id"], scene, 0)
    (run / "planning/visual_contract.json").write_text(
        json.dumps(
            {
                "slides": [
                    {
                        "slide_id": scene["id"],
                        "narration_beats": [
                            {"id": f"b{i}", "text": f"句子 {i}"} for i in range(1, 4)
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assets = []
    for name, color in [("test-blue", "blue"), ("test-green", "green")]:
        img = Image.new("RGBA", (300, 400), (0, 0, 0, 0))
        img.paste(color, (25, 25, 275, 375))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()
        file = f"planning/html_visual/{name}.png"
        (run / file).write_bytes(data)
        assets.append(
            {
                "id": name,
                "version": "0.1.0",
                "file": file,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": [300, 400],
                "alpha_bbox": [25, 25, 275, 375],
                "anchors": [{"id": "focus", "x": 150, "y": 200}],
            }
        )
    (run / "planning/html_visual/resources.json").write_text(
        json.dumps({"assets": assets}), encoding="utf-8"
    )
    timeline = run / "slides/condensation/audio_timeline.json"
    timeline.parent.mkdir(parents=True)
    timeline.write_text(
        json.dumps(
            {
                "duration_sec": 18,
                "segments": [
                    {
                        "id": f"b{i + 1}",
                        "start": i * 6,
                        "end": (i + 1) * 6,
                        "text": f"句子 {i + 1}",
                    }
                    for i in range(3)
                ],
            }
        ),
        encoding="utf-8",
    )
    # Synthetic silent audio for clock integration, never real-provider evidence.
    if no_audio:
        timeline.unlink()
    if semantic:
        binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_ids",
                   "sourceBeats": [{"id": f"b{i}", "spoken_text": f"句子 {i}",
                                    "spoken_text_sha256": hashlib.sha256(f"句子 {i}".encode()).hexdigest()}
                                   for i in range(1, 4)], "actions": {}}
        for action in scene["motion"]:
            index = min(2, int(action["startMs"] // 6000))
            binding["actions"][action["actionId"]] = {"beatId": f"b{index+1}", "edge": "start",
                                                       "offsetMs": int(action["startMs"] - index * 6000)}
        (run / "planning/html_visual/binding-condensation.json").write_text(json.dumps(binding), encoding="utf-8")
    import wave
    audio_buffer = io.BytesIO()
    with wave.open(audio_buffer, "wb") as audio_file:
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(8000)
        audio_file.writeframes(b"\0\0" * (18 * 8000))
    audio_path = run / "slides/condensation/voice.mp3"
    if not no_audio:
        audio_path.write_bytes(audio_buffer.getvalue())
    real_audio = "--real-audio-run" in sys.argv[2:]
    if real_audio:
        import shutil
        source = Path(sys.argv[sys.argv.index("--real-audio-run") + 1]).resolve()
        original_id = "freezing-water"
        scene = json.loads((source / f"planning/html_visual/scene-{original_id}.json").read_text(encoding="utf-8"))
        scene["id"] = "condensation"  # Only fixture routing ID changes; original run is read-only.
        store.save_scene(run, "condensation", scene, 1)
        shutil.copy2(source / f"planning/html_visual/binding-{original_id}.json", run / "planning/html_visual/binding-condensation.json")
        for name in ["voice.mp3", "audio_timeline.json", "tts_text.txt", "tts_metadata.json", "subtitles.srt"]:
            shutil.copy2(source / "slides" / original_id / name, run / "slides/condensation" / name)
        beats = json.loads((source / "slides" / original_id / "narration_beats.json").read_text(encoding="utf-8"))["beats"]
        (run / "planning/visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": "condensation", "narration_beats": beats}]}), encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, data, status=200, mime="application/json", headers=None):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/stress-test":
                return self.send((root / "checks/fixtures/editor-stress.html").read_bytes(), mime="text/html; charset=utf-8")
            if self.path == "/adapter-test":
                return self.send((root / "checks/fixtures/editor-adapter-p0.html").read_bytes(),
                                 mime="text/html; charset=utf-8")
            if self.path == "/audio-test":
                return self.send(
                    b'<div id="step-panel-6"><h2>Isolated audio clock fixture</h2><div id="step6-beats-list"></div></div><script>function showToast(){};window.HtmlSemanticQA={close(){},mount:async()=>{}};</script><script src="/static/api_client.js"></script><script src="/static/html_audio_review.js"></script><script>HtmlAudioReview.mount({id:"isolated",visual_backend:"html"})</script>',
                    mime="text/html; charset=utf-8",
                )
            if self.path.endswith("/steps/2/result"):
                return self.send({"contract": {"slides": [{"slide_id": "condensation", "main_title": "Synthetic clock fixture"}]}})
            if self.path.endswith("/steps/7/audio-status"):
                return self.send({"slides": [{"slide_id": "condensation", "audio_exists": not no_audio, "stale": False}]})
            if self.path.split("?")[0].endswith("/slides/condensation/audio"):
                data = audio_path.read_bytes()
                audio_mime = "audio/mpeg" if real_audio else "audio/wav"
                request_range = self.headers.get("Range")
                if request_range:
                    import re
                    match = re.fullmatch(r"bytes=(\d+)-(\d*)", request_range)
                    if not match or int(match[1]) >= len(data):
                        return self.send(b"", 416, headers={"Content-Range": f"bytes */{len(data)}"})
                    start, end = int(match[1]), min(int(match[2]) if match[2] else len(data)-1, len(data)-1)
                    return self.send(data[start:end+1], 206, audio_mime,
                                     {"Accept-Ranges": "bytes", "Content-Range": f"bytes {start}-{end}/{len(data)}"})
                return self.send(data, mime=audio_mime, headers={"Accept-Ranges": "bytes"})
            if self.path == "/":
                return self.send(
                    b'<link rel="stylesheet" href="/static/html_scene_edit.css"><link rel="stylesheet" href="/static/html_workflow.css"><div id="host"></div><script>function showToast() {}</script><script src="/static/api_client.js"></script><script src="/static/html_editor_canvas.js"></script><script src="/static/html_editor_timeline_bridge.js"></script><script src="/static/html_handoff_workbench.js"></script><script src="/static/html_external_handoff.js"></script><script src="/static/html_scene_editor.js"></script><script src="/fixtures/editor-layout-controls.js"></script><script>HtmlSceneEditor.open(document.getElementById("host"),"isolated","condensation")</script>',
                    mime="text/html; charset=utf-8",
                )
            files = {
                f"/static/{name}": root / "static" / name
                for name in [
                    "api_client.js",
                    "html_scene_editor.js",
                    "html_editor_canvas.js",
                    "html_editor_timeline_bridge.js",
                    "html_scene_edit.css",
                    "html_audio_review.js",
                    "html_external_handoff.js",
                    "html_handoff_workbench.js",
                    "html_workflow.css",
                ]
            }
            files.update(
                {
                    f"/api/html-scene-editor/runtime/{name}": root
                    / "html_engine/visual/preview"
                    / name
                    for name in ["player.js", "data.js"]
                }
            )
            for name in ["editor.js", "editor.css", "editor.js.LEGAL.txt", "manifest.json", "canvas.js", "canvas.js.LEGAL.txt", "timeline.js", "timeline.css", "timeline.js.LEGAL.txt"]:
                files[f"/static/editor_ui/{name}"] = root / "static/editor_ui" / name
            files["/fixtures/editor-adapter-p0.js"] = root / "checks/fixtures/editor-adapter-p0.js"
            files["/fixtures/editor-layout-controls.js"] = root / "checks/fixtures/editor-layout-controls.js"
            files["/fixtures/editor-stress.js"] = root / "checks/fixtures/editor-stress.js"
            if self.path in files:
                return self.send(
                    files[self.path].read_bytes(),
                    mime="text/css"
                    if self.path.endswith(".css")
                    else "application/javascript",
                )
            if self.path.endswith("/editor"):
                with project_artifact_lock(run):
                    return self.send(edit.load_editor(run, "condensation"))
            if "/handoff/" in self.path and self.path.endswith("/bundle"):
                import html_external_handoff as handoff
                path = handoff.bundle_path(run, "isolated", "condensation", self.path.split("/")[-2])
                return self.send(path.read_bytes(), mime="application/zip")
            self.send({}, 404)

        def do_PUT(self):
            self.mutate(False)

        def do_POST(self):
            if "/handoff/" in self.path:
                import html_external_handoff as handoff
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                try:
                    with project_artifact_lock(run):
                        mode = self.path.rsplit("/", 1)[-1]
                        if mode == "export":
                            result = handoff.export_bundle(run, "isolated", "condensation", payload)
                            result["download_url"] = f"/api/projects/isolated/html-visual/condensation/handoff/{result['task']['task_id']}/bundle"
                        elif mode == "preview":
                            result = handoff.import_preview(run, "isolated", "condensation", payload)
                        else:
                            result = handoff.save_result(run, "isolated", "condensation", payload)
                    return self.send(result)
                except Exception as error:
                    return self.send({"detail": {"message": str(error), "code": getattr(error, "code", "INVALID")}},
                                     getattr(error, "status_code", 422))
            if self.path == "/fixture/retime-audio" and not real_audio:
                current = json.loads(timeline.read_text(encoding="utf-8"))
                for segment in current["segments"]:
                    segment["start"] *= 1.25; segment["end"] *= 1.25
                current["duration_sec"] *= 1.25
                data = io.BytesIO()
                with wave.open(data, "wb") as output:
                    output.setnchannels(1); output.setsampwidth(2); output.setframerate(8000)
                    output.writeframes(b"\0\0" * round(current["duration_sec"] * 8000))
                with project_artifact_lock(run):
                    timeline.write_text(json.dumps(current), encoding="utf-8")
                    audio_path.write_bytes(data.getvalue())
                return self.send({"retimed": True, "factor": 1.25})
            if self.path == "/fixture/replace-audio" and not real_audio:
                data = bytearray(audio_path.read_bytes()); data[-1] ^= 1; audio_path.write_bytes(data)
                return self.send({"replaced": True, "same_duration": True})
            if self.path == "/fixture/delay-preview":
                self.server.delay_next_preview = True
                return self.send({"delay_ms": 500})
            self.mutate(True)

        def mutate(self, preview):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if preview and getattr(self.server, "delay_next_preview", False):
                self.server.delay_next_preview = False
                import time
                time.sleep(0.5)  # Deterministic late-response lifecycle fixture, no provider.
            try:
                with project_artifact_lock(run):
                    result = (
                        edit.preview_editor(
                            run,
                            "condensation",
                            payload["scene"],
                            payload["binding"],
                            payload.get("anchor_overrides"),
                            expected_revision=payload["expected_revision"],
                            expected_audio_revision=payload.get("expected_audio_revision"),
                        )
                        if preview
                        else edit.save_editor(run, "condensation", **payload)
                    )
                self.send(result)
            except store.HtmlVisualConflict as e:
                self.send({"detail": str(e)}, 409)
            except Exception as e:
                code = getattr(e, "code", "VALIDATION_ERROR")
                self.send({"detail": {"code": code, "message": str(e)}}, 409 if code == "AUDIO_REVISION_CONFLICT" else 422)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    print(json.dumps({"port": server.server_port}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
