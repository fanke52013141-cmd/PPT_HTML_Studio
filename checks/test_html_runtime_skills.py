"""Trusted loader, all annotated routes and actual outgoing Agent requests."""

import copy
import json
from pathlib import Path
import shutil

import pytest

from html_runtime_skills import (
    load_runtime_skill,
    RuntimeSkillError,
    route_task,
    PACKAGE,
    REGISTRY,
)
from html_build_snapshot import digest, create_generation_snapshot, verify_snapshot
from html_candidate_agent import repair_candidate, SYSTEM_PROMPT, PROMPT_VERSION
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError
from test_html_candidate_agent import draft as draft, patch

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / ".agents/skills/produce-editable-html/evaluation/cases.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture
def registry(tmp_path):
    root = tmp_path / "repo"
    for name in [
        REGISTRY,
        PACKAGE + "candidate-layout-repair-0.1.0.md",
        PACKAGE + "layout-evidence-0.1.0.md",
    ]:
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    return root


def edit_registry(root, transform):
    path = root / REGISTRY
    value = json.loads(path.read_text(encoding="utf-8"))
    transform(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize(
    "case", CASES["trigger_cases"] + CASES["behavior_cases"], ids=lambda c: c["id"]
)
def test_all_annotated_case_routes(case):
    routed = route_task(case["facts"])
    assert routed["route"] == case["expected_route"]
    assert bool(routed["runtime_stage"]) == (
        case["expected_route"] == "candidate_repair"
    )
    if routed["runtime_stage"]:
        assert load_runtime_skill(
            ROOT, stage=routed["runtime_stage"], mode="runtime_skill"
        ).identity["loaded"]


def test_default_and_exact_reference_identity(registry):
    legacy = load_runtime_skill(registry, mode="legacy_prompt")
    assert legacy.fragment == "" and not legacy.identity["loaded"]
    active = load_runtime_skill(registry, mode="runtime_skill")
    assert "{{" not in active.fragment and "槽位尺寸" in active.fragment
    assert active.identity["skills"][0]["id"] == "candidate-layout-repair"
    assert (
        digest(active.fragment.encode())
        == active.identity["skills"][0]["content_sha256"]
    )
    assert active.identity["selection_id"] != legacy.identity["selection_id"]
    with pytest.raises(RuntimeSkillError):
        load_runtime_skill(registry, stage="saved_repair", mode="runtime_skill")
    with pytest.raises(RuntimeSkillError):
        load_runtime_skill(registry, mode="user_document")


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v.update(version="99.0.0"),
        lambda v: v["skills"][0].update(output_contract="unrestricted-code"),
        lambda v: v["skills"][0]["body"].update(path="data/credentials.json"),
        lambda v: v["skills"][0]["body"].update(path=PACKAGE + "../../../../README.md"),
        lambda v: v["skills"][0]["body"].update(sha256="0" * 64),
        lambda v: v["skills"][0].update(references={}),
    ],
)
def test_bad_registry_never_falls_back(registry, change):
    edit_registry(registry, change)
    with pytest.raises(RuntimeSkillError):
        load_runtime_skill(registry)


def test_missing_tampered_and_unregistered_reference_rejected(registry):
    selected = load_runtime_skill(registry, mode="runtime_skill")
    body = registry / PACKAGE / "candidate-layout-repair-0.1.0.md"
    body.write_text(
        body.read_text(encoding="utf-8") + "\n[external](https://example.com/)",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeSkillError, match="CHANGED"):
        selected.verify()
    edit_registry(
        registry,
        lambda v: v["skills"][0]["body"].update(sha256=digest(body.read_bytes())),
    )
    with pytest.raises(RuntimeSkillError, match="UNREGISTERED"):
        load_runtime_skill(registry)
    body.unlink()
    with pytest.raises(RuntimeSkillError):
        load_runtime_skill(registry)


def test_new_published_content_changes_selection_identity(registry):
    before = load_runtime_skill(registry, mode="runtime_skill")
    body = registry / PACKAGE / "candidate-layout-repair-0.1.0.md"
    body.write_text(body.read_text(encoding="utf-8") + "\n新版策略。", encoding="utf-8")
    edit_registry(
        registry,
        lambda v: v["skills"][0].update(
            version="0.1.1",
            body={
                "path": str(body.relative_to(registry)).replace("\\", "/"),
                "sha256": digest(body.read_bytes()),
            },
        ),
    )
    after = load_runtime_skill(registry, mode="runtime_skill")
    assert before.identity["selection_id"] != after.identity["selection_id"]
    assert (
        before.identity["skills"][0]["content_sha256"]
        != after.identity["skills"][0]["content_sha256"]
    )


@pytest.mark.parametrize("mode", ["legacy_prompt", "runtime_skill"])
def test_actual_outgoing_prompt_identity_and_code_gate(draft, mode):
    run, scene = draft
    original = copy.deepcopy(scene)
    calls = []

    def model(
        *,
        system_prompt,
        user_prompt,
        schema_hint,
        run_dir,
        artifact_prefix,
        image_paths,
    ):
        calls.append(system_prompt)
        if mode == "legacy_prompt":
            assert system_prompt == SYSTEM_PROMPT
        else:
            assert (
                system_prompt.startswith(SYSTEM_PROMPT)
                and "受控排版修复策略" in system_prompt
            )
        assert (
            "最多20操作" in system_prompt
            and "publicParts" in user_prompt
            and schema_hint
        )
        return patch()

    result = repair_candidate(
        scene,
        None,
        run_dir=run,
        deps=HtmlReviewDependencies(ROOT, model),
        prompt_mode=mode,
    )
    summary = result["summary"]
    request = json.loads(
        next((run / summary["audit"]).rglob("request.json")).read_text(encoding="utf-8")
    )
    assert request["system_prompt"] == calls[0]
    assert (
        request["prompt_sha256"]
        == summary["prompt_sha256"]
        == digest(calls[0].encode("utf-8"))
    )
    assert request["runtime_skill"] == summary["runtime_skill"]
    assert summary["runtime_skill"]["loaded"] == (mode == "runtime_skill")
    assert (summary["prompt_version"] == PROMPT_VERSION) == (mode == "legacy_prompt")
    assert scene == original and not list(
        (run / "planning/html_visual").glob("scene-*.json")
    )


def test_skill_cannot_authorize_text_changes_or_manual_overwrite(draft):
    run, scene = draft
    for response, manual in [
        (
            {
                "action": "patch",
                "operations": [
                    {
                        "targetId": "headline",
                        "kind": "set_text",
                        "values": {"text": "delete original"},
                    }
                ],
            },
            None,
        ),
        (
            patch(),
            {
                "protected_paths": [
                    [
                        "scene",
                        "nodes",
                        "headline",
                        "presentation",
                        "typography",
                        "text",
                        "fontSizePx",
                    ]
                ]
            },
        ),
    ]:
        with pytest.raises(HtmlReviewError):
            repair_candidate(
                scene,
                None,
                run_dir=run,
                deps=HtmlReviewDependencies(ROOT, lambda **kw: response),
                prompt_mode="runtime_skill",
                manual=manual,
                max_rounds=1,
            )
    assert not list((run / "planning/html_visual").glob("scene-*.json"))


def test_generation_snapshot_contains_actual_skill_closure(tmp_path):
    snap = create_generation_snapshot(tmp_path, {"slide_id": "s1", "visual_groups": []})
    manifest = verify_snapshot(snap["path"])
    paths = {e["path"] for e in manifest["files"]}
    assert "source/html_runtime_skills.py" in paths
    assert "source/" + REGISTRY in paths
    assert all(
        "source/" + record["path"] in paths for record in load_runtime_skill(ROOT).files
    )


def test_skill_hash_change_between_validation_and_capture_blocks_snapshot(
    tmp_path, monkeypatch
):
    from html_build_snapshot import SnapshotError

    monkeypatch.setattr(
        "html_runtime_skills.runtime_source_files",
        lambda root: [{"path": REGISTRY, "sha256": "0" * 64}],
    )
    with pytest.raises(SnapshotError, match="SKILL_SOURCE_CHANGED"):
        create_generation_snapshot(tmp_path, {"slide_id": "s1", "visual_groups": []})
    assert not (tmp_path / "planning/html_visual/builds").exists()


def test_deleted_loaded_fragment_has_clear_changed_error(registry):
    selected = load_runtime_skill(registry)
    (registry / PACKAGE / "candidate-layout-repair-0.1.0.md").unlink()
    with pytest.raises(RuntimeSkillError, match="CHANGED_DURING_RUN"):
        selected.verify()


def test_portable_runtime_has_no_codex_directory_dependency(registry):
    assert not (registry / ".agents").exists()
    assert load_runtime_skill(registry, mode="runtime_skill").identity["loaded"]
