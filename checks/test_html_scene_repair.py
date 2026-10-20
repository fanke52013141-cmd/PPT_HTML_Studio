import json
from pathlib import Path
import pytest
import html_scene_editing as edit
import html_scene_repair as repair
import html_visual_store as store

ROOT = Path(__file__).resolve().parents[1]


def test_repair_rejects_stale_audio_before_candidate_or_evidence(page, monkeypatch):
    run, scene = page
    doc = edit.load_editor(run, scene['id'])
    request = {'expected_revision': doc['revision'], 'expected_audio_revision': 'f'*64,
               'operations': [{'targetId': 'headline', 'kind': 'set_presentation', 'values': {'offsetX': 1}}]}
    with pytest.raises(edit.SceneEditError) as caught:
        repair.candidate(run, scene['id'], request)
    assert caught.value.code == 'AUDIO_REVISION_CONFLICT'
    with pytest.raises(edit.SceneEditError, match='配音产物已变化'):
        repair.evidence(run, scene['id'], request)


def test_audio_change_invalidates_candidate_key_without_scene_revision_change(page, monkeypatch):
    run, scene = page
    doc = edit.load_editor(run, scene['id'])
    request = {'expected_revision': doc['revision'], 'operations': [
        {'targetId': 'headline', 'kind': 'set_presentation', 'values': {'offsetX': 1}}]}
    before = repair.candidate(run, scene['id'], request)
    original = edit.preview_editor
    def changed(*args, **kwargs):
        return {**original(*args, **kwargs), 'audio_revision': 'e'*64}
    monkeypatch.setattr(edit, 'preview_editor', changed)
    after = repair.candidate(run, scene['id'], request)
    assert before['candidate_key'] != after['candidate_key']
    assert edit.load_editor(run, scene['id'])['revision'] == doc['revision']


def test_save_rechecks_audio_after_temporal_work(page, monkeypatch):
    run, scene = page
    doc = edit.load_editor(run, scene['id'])
    request = {'expected_revision': doc['revision'], 'operations': [
        {'targetId': 'headline', 'kind': 'set_presentation', 'values': {'offsetX': 1}}]}
    candidate = repair.candidate(run, scene['id'], request)
    original_hash = edit.audio_revision
    def evidence_with_audio_change(*args, **kwargs):
        monkeypatch.setattr(edit, 'audio_revision', lambda *a: 'd'*64)
        return {'passed': True}
    monkeypatch.setattr(repair, 'evidence', evidence_with_audio_change)
    with pytest.raises(edit.SceneEditError, match='配音产物已变化'):
        repair.save_repair(run, scene['id'], {**request, 'candidate_key': candidate['candidate_key']})
    monkeypatch.setattr(edit, 'audio_revision', original_hash)
    assert edit.load_editor(run, scene['id']) == doc


def test_unknown_operation_field_reports_exact_keys_without_accepting_alias(page):
    run, scene = page
    before = edit.load_editor(run, scene['id'])
    request = {'expected_revision': before['revision'], 'source': 'ai', 'operations': [
        {'targetId': 'headline', 'kind': 'set_variant', 'values': {'variantId': 'text-card-outline'}}]}
    with pytest.raises(edit.SceneEditError) as caught:
        repair.candidate(run, scene['id'], request)
    assert caught.value.code == 'REPAIR_FIELDS'
    assert 'variantId' in str(caught.value) and '允许字段: variant, icon' in str(caught.value)
    assert edit.load_editor(run, scene['id']) == before


def test_annotation_variant_cannot_override_manual_protection_or_edit_geometry(page, monkeypatch):
    run, scene = page
    doc = edit.load_editor(run, scene['id'])
    doc['scene']['version'] = '0.7.0'
    doc['manual'] = {'protected_paths': [['scene', 'nodes', 'annotation', 'presentation', 'variant']]}
    def unexpected(*args, **kwargs):
        pytest.fail('Rejected annotation edit reached preview')
    monkeypatch.setattr(edit, 'preview_editor', unexpected)
    request = {'expected_revision': doc['revision'], 'source': 'ai', 'operations': [
        {'targetId': 'annotation', 'kind': 'set_variant', 'values': {'variant': 'annotation-dashed'}}]}
    with pytest.raises(edit.SceneEditError, match='AI不能覆盖'):
        repair.candidate_from_document(run, scene['id'], request, doc)
    doc['manual'] = None
    request['operations'][0] = {'targetId': 'annotation', 'kind': 'set_presentation', 'values': {'offsetX': 1}}
    with pytest.raises(edit.SceneEditError, match='圈注空间不能单独覆盖'):
        repair.candidate_from_document(run, scene['id'], request, doc)


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


def test_repair_prompt_scopes_protected_leaves_actions_and_historical_ancestors(page):
    run, scene = page
    doc = edit.load_editor(run, scene["id"])
    doc["manual"] = {"protected_paths": [
        ["scene", "nodes", "headline", "presentation", "offsetX"],
        ["scene", "nodes", "card-1", "presentation"],
        ["binding", "actions", "headline:enter", "offsetMs"],
        ["binding", "actions", "card-1:enter"],
        ["scene", "nodes"],
        ["scene", "motion", "headline:enter", "durationMs"],
    ]}
    prompts = repair.build_repair_prompts(doc, "只改标题", ["headline"], {})
    paths = json.loads(prompts["user_prompt"])["protected_paths"]
    assert paths == [doc["manual"]["protected_paths"][i] for i in (0, 2, 4, 5)]
    assert "祖先路径保护整个子树" in prompts["system_prompt"]
    assert "needs_input或unsupported" in prompts["system_prompt"]
    doc["manual"] = None
    assert json.loads(repair.build_repair_prompts(doc, "调整", ["headline"], {})["user_prompt"])["protected_paths"] == []


def test_repair_model_gets_snapshot_frames_and_all_issues_not_full_trace(page):
    run, scene = page
    report = {"frames": [{"timeMs": i * 250, "geometry": {"id": "same"}} for i in range(71)],
              "screenshots": [{"timeMs": t, "file": "image.png"} for t in (0, 8750, 17500)],
              "issues": [{"timeMs": 1500, "code": "OVERLAP"}], "passed": False,
              "motion_activity": {"status": "warning", "limits": "schedule only"}}
    original = json.dumps(report)
    prompts = repair.build_repair_prompts(edit.load_editor(run, scene["id"]), "检查", ["headline"], report)
    value = json.loads(prompts["user_prompt"])["temporal_report"]
    assert value["sampledFrameCount"] == 71
    assert [f["timeMs"] for f in value["frames"]] == [0, 8750, 17500]
    assert value["issues"] == report["issues"]
    assert value['motion_activity'] == report['motion_activity']
    assert 'html-repair-0.3.4' in prompts['system_prompt']
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


def test_ai_candidate_uses_shared_leaf_guard_and_reports_the_protected_path(page):
    run, scene = page
    scene["version"] = "0.5.0"
    scene["nodes"][0]["presentation"] = {"offsetX": 20}
    edit.save_editor(run, scene["id"], scene, None, 1)
    request = req(expected_revision=2, source="ai", scope=["header"], operations=[
        {"targetId": "header", "kind": "set_presentation", "values": {"width": 1400}}])
    candidate = repair.candidate(run, scene["id"], request)
    assert candidate["scene"]["nodes"][0]["presentation"] == {"offsetX": 20, "width": 1400}
    request["operations"][0]["values"] = {"offsetX": 30}
    with pytest.raises(edit.SceneEditError) as conflict:
        repair.candidate(run, scene["id"], request)
    assert conflict.value.code == "MANUAL_FIELD_PROTECTED"
    assert "scene/nodes/header/presentation/offsetX" in str(conflict.value)
    assert edit.load_editor(run, scene["id"])["revision"] == 2


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


def test_feedback_refreshes_candidate_measurements_images_and_preserves_original_targets(page, monkeypatch):
    run, scene = page
    before = edit.load_editor(run, scene['id'])
    for name in ('original.png', 'candidate.png'):
        (run / name).write_bytes(b'isolated attachment')

    def report(file, time, measured):
        return {'passed': False, 'screenshots': [{'timeMs': time, 'file': file}],
                'reference_geometry': {'headline': {'x': measured}},
                'issues': [{'code': 'TEMPORAL_OVERLAP', 'targets': ['headline', 'card-1'],
                            'timeMs': time, 'measured': {'reason': 'stroke_crosses_text', 'distance': measured}}]}

    monkeypatch.setattr(repair, 'evidence', lambda *a, **kw: report('original.png', 100, 10))
    calls = []

    def preview(*args):
        result = repair.candidate(*args)
        result['review'] = report('candidate.png', 200, 20) if len(calls) == 1 else {'passed': True, 'issues': []}
        return result

    monkeypatch.setattr(repair, 'preview_repair', preview)

    def generate(**kw):
        assert kw['stream_output'] is True
        kw['on_stream_progress']({'state': 'thinking', 'reasoning_chars': 10})
        payload = json.loads(kw['user_prompt'])
        calls.append(payload)
        if len(calls) == 2:
            assert payload['evaluation_basis'] == 'previous_candidate'
            assert payload['temporal_report']['reference_geometry']['headline']['x'] == 20
            assert payload['image_context'] == [{'timeMs': 200}]
            assert kw['image_paths'] == [str((run / 'candidate.png').resolve())]
            assert payload['targets'] == [n for n in scene['nodes'] if n['id'] == 'headline']
            assert [n['id'] for n in payload['read_only_context']] == ['card-1']
        return {'status': 'candidate', 'operations': [
            {'targetId': 'headline', 'kind': 'set_presentation', 'values': {'offsetX': len(calls)}}]}

    generate.supports_stream_progress = True

    result = repair.generate_repair(run, scene['id'], {
        'expected_revision': before['revision'], 'scope': ['headline'], 'instruction': '局部修复'}, generate)
    assert result['review']['passed'] and len(calls) == 2
    assert edit.load_editor(run, scene['id']) == before
    records = json.loads((run / store.SCENE_DIR / 'records' / f"repair-{scene['id']}.json").read_text(encoding='utf-8'))
    assert [a['evaluation_basis'] for a in records['attempts']] == ['original', 'previous_candidate']


@pytest.mark.parametrize('mode', ['unchanged', 'timeout', 'unsupported'])
def test_feedback_stops_without_save_or_unknown_request_replay(page, monkeypatch, mode):
    run, scene = page
    before = edit.load_editor(run, scene['id'])
    report = {'passed': False, 'issues': [{'code': 'TEMPORAL_OVERLAP', 'targets': ['headline', 'card-1'],
                                          'timeMs': 100, 'measured': {'overlap': True}}]}
    monkeypatch.setattr(repair, 'evidence', lambda *a, **kw: report)
    def preview(*args):
        return {**repair.candidate(*args), 'review': report}
    monkeypatch.setattr(repair, 'preview_repair', preview)
    calls = []
    def generate(**kw):
        calls.append(kw)
        if mode == 'timeout':
            raise TimeoutError('secret-provider-message')
        if mode == 'unsupported':
            return {'status': 'unsupported', 'message': '需要重新规划'}
        return {'status': 'candidate', 'operations': [
            {'targetId': 'headline', 'kind': 'set_presentation', 'values': {'offsetX': 1}}]}
    request = {'expected_revision': before['revision'], 'scope': ['headline'], 'instruction': '局部修复'}
    if mode == 'timeout':
        with pytest.raises(TimeoutError):
            repair.generate_repair(run, scene['id'], request, generate)
        records = (run / store.SCENE_DIR / 'records' / f"repair-{scene['id']}.json").read_text(encoding='utf-8')
        assert 'secret-provider-message' not in records and 'unverified' in records
    else:
        result = repair.generate_repair(run, scene['id'], request, generate)
        assert result.get('stop_reason') == 'unchanged_measurements' if mode == 'unchanged' else result['status'] == 'unsupported'
    assert len(calls) == 1 and edit.load_editor(run, scene['id']) == before


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
