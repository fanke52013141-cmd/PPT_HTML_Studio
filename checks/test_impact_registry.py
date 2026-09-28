"""Keep the central invalidation reasons registered as the pipeline evolves."""

import ast
from pathlib import Path

from impact_registry import IMPACT_RULES
from invalidation_service import InvalidationReport


def test_every_literal_invalidation_reason_is_registered() -> None:
    source = Path(__file__).resolve().parents[1] / "invalidation_service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    reasons = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "InvalidationReport":
            continue
        for keyword in node.keywords:
            if keyword.arg == "reason":
                reasons.update(
                    child.value
                    for child in ast.walk(keyword.value)
                    if isinstance(child, ast.Constant) and isinstance(child.value, str)
                )
    assert reasons <= set(IMPACT_RULES)
    assert {"annotation_changed", "digital_human_changed"} <= set(IMPACT_RULES)


def test_unregistered_impact_cannot_be_reported() -> None:
    try:
        InvalidationReport(reason="unregistered-change", affected_steps=(8,))
    except ValueError as exc:
        assert "Unregistered downstream impact" in str(exc)
    else:
        raise AssertionError("An unregistered invalidation was accepted")


def test_every_literal_recorded_impact_is_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    for source in root.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "record_impact":
                continue
            for keyword in node.keywords:
                if keyword.arg == "reason" and isinstance(keyword.value, ast.Constant):
                    assert keyword.value.value in IMPACT_RULES, (source.name, keyword.value.value)
