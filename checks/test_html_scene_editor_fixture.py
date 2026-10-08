"""Isolated browser fixture server, never the application service or database."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


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

    scene = json.loads(
        (root / "html_engine/visual/scenes/condensation.json").read_text(
            encoding="utf-8"
        )
    )
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

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, data, status=200, mime="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(
                data
                if isinstance(data, bytes)
                else json.dumps(data, ensure_ascii=False).encode()
            )

        def do_GET(self):
            if self.path == "/":
                return self.send(
                    b'<link rel="stylesheet" href="/static/html_scene_edit.css"><div id="host"></div><script>function showToast() {}</script><script src="/static/api_client.js"></script><script src="/static/html_scene_editor.js"></script><script>HtmlSceneEditor.open(document.getElementById("host"),"isolated","condensation")</script>',
                    mime="text/html; charset=utf-8",
                )
            files = {
                f"/static/{name}": root / "static" / name
                for name in [
                    "api_client.js",
                    "html_scene_editor.js",
                    "html_scene_edit.css",
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
            self.send({}, 404)

        def do_PUT(self):
            self.mutate(False)

        def do_POST(self):
            self.mutate(True)

        def mutate(self, preview):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                with project_artifact_lock(run):
                    result = (
                        edit.preview_editor(
                            run,
                            "condensation",
                            payload["scene"],
                            payload["binding"],
                            payload.get("anchor_overrides"),
                        )
                        if preview
                        else edit.save_editor(run, "condensation", **payload)
                    )
                self.send(result)
            except store.HtmlVisualConflict as e:
                self.send({"detail": str(e)}, 409)
            except Exception as e:
                self.send({"detail": str(e)}, 422)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    print(json.dumps({"port": server.server_port}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
