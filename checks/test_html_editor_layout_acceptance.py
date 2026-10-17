"""0.7 editor service acceptance; browser gestures are a separate cua suite."""

import copy
import json
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def editor_service():
    with tempfile.TemporaryDirectory(prefix="hps-editor-browser-") as run:
        with tempfile.TemporaryFile(mode="w+b") as errors:
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "checks/test_html_scene_editor_fixture.py"), run, "--presentation"],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=errors, text=True,
            )
            ready = queue.Queue()
            threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True).start()
            try:
                try:
                    line = ready.get(timeout=30)
                except queue.Empty:
                    pytest.fail("isolated editor fixture did not start within 30s")
                if not line:
                    errors.seek(0)
                    pytest.fail(errors.read().decode("utf-8", errors="replace"))
                base = f'http://127.0.0.1:{json.loads(line)["port"]}'

                def request(method="GET", payload=None, suffix=""):
                    data = None if payload is None else json.dumps(payload).encode()
                    req = Request(base + "/api/projects/isolated/html-visual/condensation/editor" + suffix,
                                  data=data, method=method, headers={"Content-Type": "application/json"})
                    with urlopen(req, timeout=30) as response:
                        return json.load(response)

                yield request
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                process.stdout.close()


def test_07_preview_save_reopen_preserves_variants_semantics_and_protection(editor_service):
    request = editor_service
    before = request()
    assert before["scene"]["version"] == "0.7.0"
    candidate = copy.deepcopy(before["scene"])
    header = next(n for n in candidate["nodes"] if n["id"] == "header")
    assert header["presentation"]["variant"] == "header-badge"
    assert next(n for n in candidate["nodes"] if n["id"] == "headline")["presentation"]["variant"] == "text-emphasis-bold"
    header["presentation"].update(offsetX=14, offsetY=8)
    for node in candidate["nodes"]:
        if node["id"] in ("card-1", "card-2"):
            node["presentation"] = {"offsetX": 12, "offsetY": 6}
    payload = {"scene": candidate, "binding": before["binding"], "anchor_overrides": {},
               "expected_revision": before["revision"]}
    preview = request("POST", payload, "/preview")
    assert preview["clock"] == "audio_timeline"
    assert preview["scene"]["version"] == "0.7.0"
    assert request()["revision"] == before["revision"]  # preview cannot write
    saved = request("PUT", payload)
    reopened = request()
    assert saved["changed"] and reopened["revision"] == before["revision"] + 1
    assert reopened["scene"] == candidate
    assert reopened["binding"] == before["binding"]
    for key in ("motion", "initialVisibleIds", "beats"):
        assert reopened["scene"][key] == before["scene"][key]
    assert reopened["manual"]["protected_paths"]
    payload["expected_revision"] = reopened["revision"]
    assert request("PUT", payload)["changed"] is False
    assert request()["revision"] == reopened["revision"]
    payload["expected_revision"] = before["revision"]
    for method, suffix in [("POST", "/preview"), ("PUT", "")]:
        with pytest.raises(HTTPError) as conflict:
            request(method, payload, suffix)
        assert conflict.value.code == 409
    assert request()["scene"] == candidate
