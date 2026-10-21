"""Real browser import/export/save regression with a dedicated fixture data root."""
import os
from pathlib import Path
import subprocess
import sys


def test_external_handoff_buttons_and_save_boundary(tmp_path):
    run = tmp_path / "hps-editor-browser-external"
    run.mkdir()
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    # CI installs dependencies globally and has no repository .venv.
    env["PPT_STUDIO_PYTHON"] = sys.executable
    result = subprocess.run(["node", str(root / "checks/test_html_external_handoff.browser.cjs"), str(run)],
                            cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (run / "browser-report.json").is_file()
