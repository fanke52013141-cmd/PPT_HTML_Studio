from __future__ import annotations

import ast
from scripts.run_checks import ROOT, standalone_python_checks


def test_converted_script_checks_are_collected_by_pytest():
    discovered = set(standalone_python_checks())
    for name in ("test_audio_confirmation.py", "test_video_speed.py"):
        path = ROOT / "checks" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert any(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in tree.body)
        assert path not in discovered
