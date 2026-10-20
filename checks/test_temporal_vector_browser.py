"""Run the actual DOM vector regression through the canonical pytest suite."""
from pathlib import Path
import subprocess


def test_temporal_vector_geometry_and_registered_policy():
    root = Path(__file__).resolve().parents[1]
    for script in ("test_vector_overlap.cjs", "test_html_temporal_vector_geometry.cjs", "test_html_temporal_policy.cjs"):
        result = subprocess.run(["node", str(root / "checks" / script)], cwd=root,
                                capture_output=True, text=True, encoding="utf-8", timeout=45)
        assert result.returncode == 0, result.stdout + result.stderr
