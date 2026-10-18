"""Run the registered-structure browser regression in the canonical pytest gate."""
import os
from pathlib import Path
import subprocess
import pytest


@pytest.mark.parametrize('width', [1592, 1600])
def test_registered_structure_browser_regression(tmp_path, width):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ['node', 'checks/test_html_framed_relations.cjs'], cwd=root,
        env={**os.environ, 'HPS_TEST_OUTPUT_DIR': str(tmp_path), 'HPS_TEST_AUTHOR_WIDTH': str(width)},
        capture_output=True, text=True, encoding='utf-8', timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / 'engineering.png').is_file()
