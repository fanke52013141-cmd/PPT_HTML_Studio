"""A03 compile/bind contract, actual player frames and retained speech timing."""
from __future__ import annotations

import json
import subprocess

import pytest

from html_audio_binder import AudioBindingError, bind_scene_to_audio
from html_production_service import compile_plan
from test_html_object_decomposition import decomposition_plan, normalize
from test_html_narration_semantics import CATALOG, CONTRACT_SLIDE as SOURCE, ROOT

CONTRACT_SLIDE = {**SOURCE, "slide_id": "slide-001"}


def compiled():
    plan = decomposition_plan()
    plan["slide_id"] = "slide-001"
    # Same-object repeated emphasis must retain two independent identities.
    for index, beat in enumerate(plan["beats"]):
        beat["actions"].append({"actionKey": f"emphasize-{index}", "objectId": beat["targets"][0]["objectId"],
                                "type": "emphasize", "expectedState": {"visible": True, "meaning": beat["visualIntent"]}})
    plan = normalize(plan, CONTRACT_SLIDE)
    return compile_plan(plan, CONTRACT_SLIDE, CATALOG)


def timeline():
    return {"audio_content_duration_sec": 8.2, "segments": [
        {"id": b["id"], "start": start, "end": end, "text": b["spoken_text"]}
        for b, start, end in zip(CONTRACT_SLIDE["narration_beats"], (0.8, 4.1), (3.7, 8.0), strict=True)]}


def test_compile_and_bind_uses_explicit_state_and_independent_ids():
    scene, binding = compiled()
    assert scene["version"] == "0.6.0" and binding["version"] == "0.2.0"
    assert scene["nodeStates"]["header"] == {"role": "context", "initialVisible": True}
    assert not any(a["targetId"] == "header" for a in scene["motion"])
    bound = bind_scene_to_audio(scene, timeline(), binding)
    assert bound["durationMs"] == 8200  # Last subtitle ends at 8000; tail remains.
    assert bound["motion"][0]["startMs"] == 800
    assert bound["motion"][1]["startMs"] == 1300
    assert len({a["actionId"] for a in bound["motion"]}) == len(bound["motion"])
    assert scene["durationMs"] != bound["durationMs"]
    assert bind_scene_to_audio(bound, timeline(), binding) == bound  # Offsets only once.
    from html_scene_editing import _compile, _validate_binding
    _compile(bound, [])
    _validate_binding(binding, scene, CONTRACT_SLIDE["narration_beats"])


@pytest.mark.parametrize("change,code", [
    (lambda s,t,b: b["actions"].pop(next(iter(b["actions"]))), "AUDIO_BINDING_INCOMPLETE"),
    (lambda s,t,b: b["actions"][next(iter(b["actions"]))].update(offsetMs=5000), "AUDIO_OFFSET_OVERFLOW"),
    (lambda s,t,b: b["actions"][next(iter(b["actions"]))].update(beatId="gone"), "AUDIO_BINDING_INVALID"),
    (lambda s,t,b: t["segments"][0].update(text="被改写的讲稿"), "AUDIO_NARRATION_CHANGED"),
    (lambda s,t,b: t["segments"][0].update(id="gone"), "AUDIO_BEAT_MISSING"),
    (lambda s,t,b: t.update(audio_content_duration_sec=7), "AUDIO_BEAT_OVERFLOW"),
    (lambda s,t,b: s["motion"][1].update(actionId=s["motion"][0]["actionId"]), "AUDIO_BINDING_INCOMPLETE"),
])
def test_new_binding_fails_instead_of_scaling_or_silent_clipping(change, code):
    scene, binding = compiled()
    audio = timeline()
    change(scene, audio, binding)
    with pytest.raises(AudioBindingError) as rejected:
        bind_scene_to_audio(scene, audio, binding)
    assert rejected.value.code == code


def test_missing_binding_and_editor_missing_mapping_block():
    scene, binding = compiled()
    with pytest.raises(AudioBindingError):
        bind_scene_to_audio(scene, timeline())
    from html_scene_editing import _validate_binding, SceneEditError
    with pytest.raises(SceneEditError):
        _validate_binding(None, scene, CONTRACT_SLIDE["narration_beats"])
    binding["actions"].pop(next(iter(binding["actions"])))
    with pytest.raises(SceneEditError):
        _validate_binding(binding, scene, CONTRACT_SLIDE["narration_beats"])


def test_repeated_emphasis_same_target_across_beats_compiles_and_binds():
    plan = decomposition_plan()
    plan["slide_id"] = "slide-001"
    target = {"objectId": "stat-1", "role": "instructional", "meaning": "重复说明冰点"}
    plan["beats"][0]["actions"].append({"actionKey": "first-focus", "objectId": "stat-1", "type": "emphasize",
                                        "expectedState": {"visible": True, "meaning": "强调冰点"}})
    plan["beats"][1]["targets"].append(target)
    plan["beats"][1]["actions"].append({"actionKey": "second-focus", "objectId": "stat-1", "type": "emphasize",
                                        "expectedState": {"visible": True, "meaning": "再次强调冰点"}})
    scene, binding = compile_plan(normalize(plan, CONTRACT_SLIDE), CONTRACT_SLIDE, CATALOG)
    bound = bind_scene_to_audio(scene, timeline(), binding)
    actions = [a for a in bound["motion"] if a["targetId"] == "stat-1" and a["type"] == "emphasize"]
    assert [a["startMs"] for a in actions] == [1300, 4100]
    from html_scene_editing import _compile
    _compile(bound, [])


def test_actual_player_seek_states_and_repeat_emphasis(tmp_path):
    scene, binding = compiled()
    scene = bind_scene_to_audio(scene, timeline(), binding)
    source = tmp_path / "scene.json"
    source.write_text(json.dumps(scene), encoding="utf-8")
    result = subprocess.run(["node", "visual/tests/semantic-actions.cjs", str(source), str(tmp_path)],
                            cwd=ROOT / "html_engine", capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "frames.json").read_text(encoding="utf-8"))
    assert report["initialContextVisible"] and report["instructionHiddenBeforeSpeech"]
    assert report["seekRepeatEqual"]
    assert len(report["frames"]) == 6


def real_timing_plan(page, *, return_plan=False):
    plan = decomposition_plan()
    plan["slide_id"] = page["slide_id"]
    plan["slots"]["header"]["title"] = "语块时间绑定工程验证"
    plan["slots"]["summary"] = {"kind": "summary", "from": {"text": "原句", "tone": "blue"},
                                "to": {"text": "动作", "tone": "green"}, "term": "对应", "takeaway": "仅验证时序，语义待审"}
    plan["beats"] = []
    for index, beat in enumerate(page["narration_beats"]):
        oid = f"stat-{index + 1}" if index < 3 else "stat-1"
        if index < 3:
            plan["slots"][oid]["runs"][0]["text"] = beat["spoken_text"]
        plan["beats"].append({"id": beat["id"], "visualIntent": "工程验证逐句时间；实际语义另审",
                              "targets": [{"objectId": oid, "role": "instructional", "meaning": "原句文字对象"}],
                              "actions": [{"actionKey": f"timing-{index}", "objectId": oid,
                                           "type": "enter" if index < 3 else "emphasize",
                                           "expectedState": {"visible": True, "meaning": "工程取帧检查"}}]})
        if index == 0:
            plan["beats"][-1]["actions"].append({"actionKey": "first-focus", "objectId": oid, "type": "emphasize",
                                                  "expectedState": {"visible": True, "meaning": "首次强调验证"}})
    from test_html_object_decomposition import add_definitions
    add_definitions(plan)
    source = {"slide_id": page["slide_id"], "narration_beats": page["narration_beats"]}
    frozen = normalize(plan, source, budget=0)
    scene, binding = compile_plan(frozen, source, CATALOG)
    return (frozen, scene, binding) if return_plan else (scene, binding)


def test_all_twenty_real_provider_beats_bind_without_tts_or_proportional_fallback(tmp_path):
    fixture = json.loads((ROOT / "checks/fixtures/a03-real-s08-timings.json").read_text(encoding="utf-8"))
    count = 0
    for page in fixture["pages"]:
        scene, binding = real_timing_plan(page)
        bound = bind_scene_to_audio(scene, page["audio_timeline"], binding)
        assert bound["durationMs"] == round(page["audio_timeline"]["audio_content_duration_sec"] * 1000)
        windows = {}
        for b in page["audio_timeline"]["segments"]:
            start, end = round(b["start"] * 1000), round(b["end"] * 1000)
            prior = windows.get(b["beat_id"], (start, end))
            windows[b["beat_id"]] = (min(start, prior[0]), max(end, prior[1]))
        for action in bound["motion"]:
            start, end = windows[binding["actions"][action["actionId"]]["beatId"]]
            assert start <= action["startMs"] < action["startMs"] + action["durationMs"] <= end
        from html_scene_editing import _compile
        _compile(bound, [])
        count += len(binding["narration"])
    assert count == 20
    page = fixture["pages"][-1]
    scene, binding = real_timing_plan(page)
    bound = bind_scene_to_audio(scene, page["audio_timeline"], binding)
    path = tmp_path / "real-bound.json"
    path.write_text(json.dumps(bound), encoding="utf-8")
    result = subprocess.run(["node", "visual/tests/semantic-actions.cjs", str(path), str(tmp_path)],
                            cwd=ROOT / "html_engine", capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stderr
    assert len(json.loads((tmp_path / "frames.json").read_text())["frames"]) == 12


def test_editor_save_reopen_protection_uses_action_ids_and_source_text(tmp_path, monkeypatch):
    import html_scene_editing as editor
    import html_visual_store as store
    scene, binding = compiled()
    store.save_scene(tmp_path, scene["id"], scene, 0)
    path = tmp_path / "planning/visual_contract.json"
    path.write_text(json.dumps({"slides": [CONTRACT_SLIDE]}), encoding="utf-8")
    editor.binding_path(tmp_path, scene["id"]).write_text(json.dumps(binding), encoding="utf-8")
    assert editor.load_editor(tmp_path, scene["id"])["binding"]["version"] == "0.2.0"
    changed = json.loads(json.dumps(scene))
    changed["motion"][1]["durationMs"] = 350
    saved = editor.save_editor(tmp_path, scene["id"], changed, binding, 1)
    assert saved["changed"]
    reopened = editor.load_editor(tmp_path, scene["id"])
    assert reopened["scene"]["version"] == "0.6.0"
    assert reopened["scene"]["motion"][1]["actionId"] == scene["motion"][1]["actionId"]
    assert reopened["scene"]["motion"][1]["durationMs"] == 350
    protected = editor.protected_edit_paths(scene, changed, "scene")
    assert any(scene["motion"][1]["actionId"] in parts for parts in protected)
    source = json.loads(json.dumps(CONTRACT_SLIDE))
    source["narration_beats"][0]["spoken_text"] = "改变讲稿但保留ID"
    with pytest.raises(editor.SceneEditError, match="当前讲稿"):
        editor._validate_binding(binding, scene, source["narration_beats"])


def test_annotation_waits_for_dependencies_and_short_beats_reject(tmp_path):
    from test_html_object_decomposition import image_plan, normalize as normalize_image
    plan, source = image_plan("generate")
    plan["slide_id"] = "slide-001"
    source["slide_id"] = "slide-001"
    # Move image/label from context to same spoken beat: binder schedules
    # annotation after both enter windows, not at an earlier default time.
    for oid in ("subject", "anchor-label"):
        definition = next(d for d in plan["objectSemantics"] if d["objectId"] == oid)
        definition.update(role="instructional", initialState={"visible": False})
        definition.pop("initiallyVisibleReason", None)
        beat = plan["beats"][3]
        beat["targets"].insert(0, {"objectId": oid, "role": "instructional", "meaning": "标注主体/标签"})
        beat["actions"].insert(0, {"actionKey": f"{oid}-enter", "objectId": oid, "type": "enter",
                                   "expectedState": {"visible": True, "meaning": "进入具体主体/标签"}})
    scene, binding = compile_plan(normalize_image(plan, source), source, CATALOG)
    audio = {"audio_content_duration_sec": 15.2, "segments": [{"id": b["id"], "start": i*3,
              "end": (i+1)*3, "text": b["spoken_text"]} for i,b in enumerate(source["narration_beats"])]}
    bound = bind_scene_to_audio(scene, audio, binding)
    annotation = next(a for a in bound["motion"] if a["targetId"] == "annotation")
    assert annotation["startMs"] == 9500
    for oid in ("subject", "anchor-label"):
        action = next(a for a in bound["motion"] if a["targetId"] == oid)
        assert annotation["startMs"] >= action["startMs"] + action["durationMs"]
    audio["segments"][3]["end"] = 9.4
    with pytest.raises(AudioBindingError):
        bind_scene_to_audio(scene, audio, binding)


def test_output_runner_records_real_binding_and_cannot_enable_legacy_fallback(tmp_path):
    from html_render_runner import HtmlRenderRunner, HtmlRenderRunnerDependencies, HtmlRenderError
    scene, binding = compiled()
    work = tmp_path / "work"
    work.mkdir()
    binding_path = tmp_path / f"binding-{scene['id']}.json"
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    runner = HtmlRenderRunner(HtmlRenderRunnerDependencies(ROOT, lambda run: [scene["id"]], allow_legacy_unbound=True))
    result = runner._bound_scene_path(work, scene, timeline(), scene["id"])
    assert json.loads(result.read_text(encoding="utf-8"))["motion"][0]["startMs"] == 800
    metadata = json.loads((work / binding_path.name).read_text(encoding="utf-8"))
    assert metadata["mode"] == "beat_action_ids" and metadata["timeScale"] is None
    binding_path.unlink()
    with pytest.raises(HtmlRenderError, match="actionId"):
        runner._bound_scene_path(work, scene, timeline(), scene["id"])


def test_repair_selects_one_repeated_action_by_identity(tmp_path, monkeypatch):
    import html_scene_repair as repair
    import html_scene_editing as editor
    scene, binding = compiled()
    first = next(a for a in scene["motion"] if a["type"] == "emphasize")
    second = {**first, "actionId": "act-repeated", "startMs": first["startMs"] + 600}
    scene["motion"].append(second)
    binding["actions"][second["actionId"]] = dict(binding["actions"][first["actionId"]])
    doc = {"scene": scene, "binding": binding, "resources": [], "manual": None}
    request = {"expected_revision": 1, "source": "human", "operations": [{"kind": "set_binding",
               "targetId": first["targetId"], "action": "emphasize", "values": {"offsetMs": 200}}]}
    with pytest.raises(editor.SceneEditError) as rejected:
        repair.candidate_from_document(tmp_path, scene["id"], request, doc)
    assert rejected.value.code == "REPAIR_ACTION_AMBIGUOUS"
    monkeypatch.setattr(editor, "preview_editor", lambda run, slide, scene, binding: {"scene": scene})
    request["operations"][0]["actionId"] = second["actionId"]
    result = repair.candidate_from_document(tmp_path, scene["id"], request, doc)
    assert result["scene"]["version"] == "0.6.0"
    assert result["binding"]["actions"][second["actionId"]]["offsetMs"] == 200
    assert result["binding"]["actions"][first["actionId"]]["offsetMs"] == 0
