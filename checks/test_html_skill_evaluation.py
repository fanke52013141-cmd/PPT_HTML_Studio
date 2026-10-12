"""Experiment orchestration tests; stub repair here, real graph/browser in Agent tests."""

import copy
import json
from pathlib import Path

import pytest

import html_skill_evaluation as evaluation

ROOT = Path(__file__).resolve().parents[1]


def fake_repair(scene, binding, *, run_dir, deps, prompt_mode, **kwargs):
    image = run_dir / "same.png"
    image.write_bytes(b"identical fixed image bytes")
    deps.json_generator(
        system_prompt=prompt_mode,
        user_prompt=json.dumps(scene, sort_keys=True),
        schema_hint="fixed",
        run_dir=str(run_dir),
        artifact_prefix="fixture",
        image_paths=[str(image)],
    )
    return {
        "scene": copy.deepcopy(scene),
        "report": {"passed": True},
        "summary": {"audit": "fixture-audit"},
    }


def test_ab_ba_same_inputs_and_no_manual_scene_edits(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, "repair_candidate", fake_repair)
    modes = []

    def generator(**kwargs):
        modes.append(kwargs["system_prompt"])
        return {"action": "stop", "message": "fixture"}

    cases = evaluation.fixed_cases(ROOT)[:2]
    before = copy.deepcopy(cases)
    result = evaluation.evaluate_pairs(
        ROOT,
        tmp_path / "experiment",
        generator,
        model_identity={"model": "fixture"},
        cases=cases,
    )
    assert modes == ["legacy_prompt", "runtime_skill", "runtime_skill", "legacy_prompt"]
    assert cases == before
    assert all(c["same_first_model_input"] for c in result["comparability"])
    assert all(
        a["manual_scene_edits"] == 0 and a["cost"] is None for a in result["arms"]
    )
    assert result["real_model"] == "not_tested"
    with pytest.raises(ValueError, match="DIRECTORY_EXISTS"):
        evaluation.evaluate_pairs(
            ROOT,
            tmp_path / "experiment",
            generator,
            model_identity={"model": "fixture"},
        )


def test_failure_is_kept_not_rerolled_or_selected_away(tmp_path, monkeypatch):
    def repair(*args, prompt_mode, **kwargs):
        if prompt_mode == "runtime_skill":
            raise ValueError("failed arm; must not retry")
        return fake_repair(*args, prompt_mode=prompt_mode, **kwargs)

    monkeypatch.setattr(evaluation, "repair_candidate", repair)
    result = evaluation.evaluate_pairs(
        ROOT,
        tmp_path / "experiment",
        lambda **kw: {},
        model_identity={"model": "fixture"},
        cases=evaluation.fixed_cases(ROOT)[:1],
    )
    assert len(result["arms"]) == 2
    assert not result["arms"][1]["engineering_passed"]
    assert result["arms"][1]["error"]["type"] == "ValueError"
    assert result["metrics"]["runtime_skill"]["manual_intervention_required"] == 1
    assert not result["comparability"][0]["same_first_model_input"]


def test_live_script_preflight_reads_settings_without_mutation(tmp_path):
    import importlib.util
    import sqlite3

    spec = importlib.util.spec_from_file_location(
        "s06_eval", ROOT / "scripts/evaluate_html_runtime_skills.py"
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    path = tmp_path / "settings.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE settings(key TEXT, value TEXT)")
        db.executemany(
            "INSERT INTO settings VALUES(?,?)",
            [
                ("llm_model", "fixture"),
                ("llm_base_url", "https://example.invalid"),
                ("llm_api_key", "not-a-live-key"),
            ],
        )
    before = path.read_bytes()
    assert script.read_text_connection(path)["llm_model"] == "fixture"
    assert before == path.read_bytes()
    assert "server" not in script.__dict__
