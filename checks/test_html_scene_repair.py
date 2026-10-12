import json
from pathlib import Path
import pytest
import html_scene_editing as edit
import html_scene_repair as repair
import html_visual_store as store

ROOT = Path(__file__).resolve().parents[1]


def test_repair_prompt_defines_required_operation_fields(page):
    run, scene = page
    prompts = repair.build_repair_prompts(
        edit.load_editor(run, scene["id"]), "调整标题", ["headline"], {}
    )
    payload = json.loads(prompts["user_prompt"])
    samples = {op["kind"]: op for op in payload["operation_examples"]}
    assert samples["set_text_style"]["part"] == "text"
    assert samples["set_motion"]["action"] == "enter"
    assert "set_text_style必须提供part" in prompts["system_prompt"]
    assert "set_motion与set_binding必须提供action" in prompts["system_prompt"]


def test_repair_model_gets_snapshot_frames_and_all_issues_not_full_trace(page):
    run, scene = page
    report = {"frames": [{"timeMs": i * 250, "geometry": {"id": "same"}} for i in range(71)],
              "screenshots": [{"timeMs": t, "file": "image.png"} for t in (0, 8750, 17500)],
              "issues": [{"timeMs": 1500, "code": "OVERLAP"}], "passed": False}
    original = json.dumps(report)
    prompts = repair.build_repair_prompts(edit.load_editor(run, scene["id"]), "检查", ["headline"], report)
    value = json.loads(prompts["user_prompt"])["temporal_report"]
    assert value["sampledFrameCount"] == 71
    assert [f["timeMs"] for f in value["frames"]] == [0, 8750, 17500]
    assert value["issues"] == report["issues"]
    assert json.dumps(report) == original
    summary = {"frame_count": 80, "issues": [], "reference_geometry": {}}
    prompts = repair.build_repair_prompts(edit.load_editor(run, scene["id"]), "检查", ["headline"], summary)
    result = json.loads(prompts["user_prompt"])["temporal_report"]
    assert result["sampledFrameCount"] == 80 and "frames" not in result


@pytest.fixture
def page(tmp_path):
    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/condensation.json").read_text(
            encoding="utf-8"
        )
    )
    scene["themeRef"]["id"] = "neutral-baseline"
    store.save_scene(tmp_path, scene["id"], scene, 0)
    (tmp_path / "planning/visual_contract.json").write_text(
        json.dumps(
            {
                "slides": [
                    {
                        "slide_id": scene["id"],
                        "narration_beats": [{"id": "b1", "text": "测试"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return tmp_path, scene


def req(**kw):
    return {
        "expected_revision": 1,
        "source": "human",
        "scope": ["headline"],
        "time_range_ms": [1500, 1700],
        "operations": [
            {
                "targetId": "headline",
                "kind": "set_text_style",
                "part": "text",
                "values": {"fontSizePx": 28},
            },
            {
                "targetId": "headline",
                "kind": "set_presentation",
                "values": {"offsetX": 20},
            },
        ],
        **kw,
    }


def test_candidate_reopen_noop_conflict_and_protection(page):
    run, scene = page
    c = repair.preview_repair(run, scene["id"], req())
    assert c["review"]["passed"] and c["scene"]["version"] == "0.5.0"
    assert store.load_scene(run, scene["id"]) == scene
    result = repair.save_repair(
        run, scene["id"], {**req(), "candidate_key": c["candidate_key"]}
    )
    assert result["changed"]
    doc = edit.load_editor(run, scene["id"])
    assert doc["scene"]["nodes"][1]["presentation"]["offsetX"] == 20
    c2 = repair.preview_repair(run, scene["id"], req(expected_revision=2))
    assert (
        repair.save_repair(
            run,
            scene["id"],
            {**req(expected_revision=2), "candidate_key": c2["candidate_key"]},
        )["changed"]
        is False
    )
    with pytest.raises(store.HtmlVisualConflict):
        repair.candidate(run, scene["id"], req())
    with pytest.raises(edit.SceneEditError, match="AI不能覆盖"):
        repair.candidate(
            run,
            scene["id"],
            req(
                expected_revision=2,
                source="ai",
                operations=[
                    {
                        "targetId": "headline",
                        "kind": "set_text_style",
                        "part": "text",
                        "values": {"fontSizePx": 25},
                    }
                ],
            ),
        )


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "set_presentation", "values": {"offsetX": -400}},
        {"kind": "set_text_style", "part": "body", "values": {"fontSizePx": 25}},
        {"kind": "set_text_style", "part": "text", "values": {"fontSizePx": 100}},
        {"kind": "set_presentation", "values": {"color": "red"}},
    ],
)
def test_invalid_no_write(page, change):
    run, scene = page
    with pytest.raises(edit.SceneEditError):
        repair.candidate(
            run, scene["id"], req(operations=[{"targetId": "headline", **change}])
        )
    assert store.load_scene(run, scene["id"]) == scene


def test_scope_and_key_do_not_expand(page):
    run, scene = page
    with pytest.raises(edit.SceneEditError, match="越过"):
        repair.candidate(run, scene["id"], req(scope=["card-1"]))
    with pytest.raises(edit.SceneEditError, match="变化"):
        repair.save_repair(run, scene["id"], {**req(), "candidate_key": "0" * 64})
    assert store.load_scene(run, scene["id"]) == scene


def test_temporal_intermediate_collision_and_repair(page):
    run, scene = page
    action = next(
        a for a in scene["motion"] if a["targetId"] == "card-2" and a["type"] == "enter"
    )
    action["offsetY"] = -100
    edit.save_editor(run, scene["id"], scene, None, 1)
    interval = [action["startMs"], action["startMs"] + action["durationMs"]]
    request = {
        "expected_revision": 2,
        "time_range_ms": interval,
        "step_ms": 16,
        "overlap_pairs": [["card-1", "card-2"]],
    }
    report = repair.evidence(run, scene["id"], request)
    assert not report["passed"] and any(
        i["code"] == "TEMPORAL_OVERLAP" for i in report["issues"]
    )
    fixed = repair.preview_repair(
        run,
        scene["id"],
        {
            **request,
            "source": "human",
            "scope": ["card-2"],
            "operations": [
                {
                    "targetId": "card-2",
                    "kind": "set_motion",
                    "action": "enter",
                    "values": {"offsetY": 0},
                }
            ],
        },
    )
    assert fixed["review"]["passed"]


def test_bounded_model_uses_actual_screenshots_and_retries(page):
    run, scene = page
    calls = []

    def generate(**kw):
        calls.append(kw)
        assert kw["image_paths"] and all(Path(p).is_file() for p in kw["image_paths"])
        if len(calls) == 1:
            return {
                "status": "candidate",
                "operations": [
                    {
                        "targetId": "headline",
                        "kind": "set_text_style",
                        "part": "text",
                        "values": {"fontSizePx": 200},
                    }
                ],
            }
        return {
            "status": "candidate",
            "operations": [
                {
                    "targetId": "headline",
                    "kind": "set_text_style",
                    "part": "text",
                    "values": {"fontSizePx": 28},
                }
            ],
        }

    r = repair.generate_repair(
        run,
        scene["id"],
        {
            "expected_revision": 1,
            "instruction": "字号小一点",
            "scope": ["headline"],
            "time_range_ms": [1500, 1700],
            "step_ms": 250,
            "overlap_pairs": [],
        },
        generate,
    )
    assert r["review"]["passed"] and len(calls) == 2
    assert "previous_output" in json.loads(calls[1]["user_prompt"])
    assert store.load_scene(run, scene["id"]) == scene


def test_old_version_cannot_smuggle_override(page):
    run, scene = page
    scene["nodes"][1]["presentation"] = {"offsetX": 10}
    with pytest.raises(edit.SceneEditError):
        edit.save_editor(run, scene["id"], scene, None, 1)


def test_font_overflow_is_rejected_before_save(page):
    run, scene = page
    request = req(
        operations=[
            {
                "targetId": "headline",
                "kind": "set_text_style",
                "part": "text",
                "values": {"fontSizePx": 80},
            }
        ]
    )
    with pytest.raises(edit.SceneEditError):
        repair.preview_repair(run, scene["id"], request)
    assert store.load_scene(run, scene["id"]) == scene


def test_ai_corrections_can_be_refined_without_unlocking_manual_fields(page):
    run, scene = page
    c = repair.candidate(run, scene["id"], req(source="ai"))
    edit.save_editor(run, scene["id"], c["scene"], c["binding"], 1, origin="ai")
    assert (
        edit.manual_protected_paths(edit.load_editor(run, scene["id"])["manual"]) == []
    )
    refined = repair.candidate(
        run,
        scene["id"],
        req(
            expected_revision=2,
            source="ai",
            operations=[
                {
                    "targetId": "headline",
                    "kind": "set_text_style",
                    "part": "text",
                    "values": {"fontSizePx": 26},
                }
            ],
        ),
    )
    assert (
        refined["scene"]["nodes"][1]["presentation"]["typography"]["text"]["fontSizePx"]
        == 26
    )
    human = refined["scene"]
    edit.save_editor(run, scene["id"], human, refined["binding"], 2)
    with pytest.raises(edit.SceneEditError, match="AI不能覆盖"):
        repair.candidate(run, scene["id"], req(expected_revision=3, source="ai"))


def test_typography_change_remeasures_wrapping(page):
    run, scene = page
    body = req(
        scope=["intro"],
        operations=[
            {"targetId": "intro", "kind": "set_presentation", "values": {"width": 250}},
            {
                "targetId": "intro",
                "kind": "set_text_style",
                "part": "text",
                "values": {"fontSizePx": 18, "lineHeight": 1.2},
            },
        ],
    )
    c = repair.preview_repair(run, scene["id"], body)
    assert c["review"]["passed"]
    assert c["review"]["text_measurements"]["intro"]["lines"] == 2
    assert c["review"]["reference_geometry"]["intro"]["box"]["width"] == 250
