"""A03 stable actions, source-bound audio and compatible editor behavior."""
import copy
import json
from pathlib import Path

import pytest

from checks.test_html_semantic_plan import semantic_plan, normalize, CONTRACT_SLIDE
from html_production_service import compile_plan
from html_storyboard_planning import load_template_catalog
from html_audio_binder import bind_scene_to_audio, AudioBindingError
from html_scene_editing import _validate_binding, protected_edit_paths, merge_manual_edits

ROOT = Path(__file__).resolve().parents[1]


def setup():
    contract = copy.deepcopy(CONTRACT_SLIDE)
    plan = normalize(semantic_plan(contract),contract)
    scene, binding = compile_plan(plan, contract, load_template_catalog(ROOT))
    timeline = {"duration_sec": len(plan["beats"]) * 2,
                "timing_source": "test_only", "segments": [
                    {"id": b["id"], "text": b["spoken_text"], "start": i * 2, "end": (i + 1) * 2}
                    for i, b in enumerate(plan["beats"])]}
    return plan, scene, binding, timeline


def test_many_actions_and_repeated_emphasis_keep_identity_and_real_windows():
    plan, scene, binding, timeline = setup()
    bound = bind_scene_to_audio(scene, timeline, binding)
    assert set(bound["initialVisibleIds"]) == {o["id"] for o in plan["objects"] if o["initialVisible"]}
    assert not any(a["targetId"] in bound["initialVisibleIds"] for a in bound["motion"])
    for i, beat in enumerate(plan["beats"]):
        actions = [a for a in bound["motion"] if binding["actions"][a["actionId"]]["beatId"] == beat["id"]]
        assert len(actions) == 2 and all(a["startMs"] == i * 2000 for a in actions)
        assert [a["actionId"] for a in actions] == [a["actionId"] for a in beat["actions"]]


@pytest.mark.parametrize("change,code", [
    (lambda t: t["segments"][0].update(text="Different narration"), "AUDIO_TEXT_MISMATCH"),
    (lambda t: t["segments"][0].update(id=t["segments"][1]["id"]), "AUDIO_BEAT_DUPLICATE"),
    (lambda t: t["segments"][0].update(start=0.5,end=0.5), "AUDIO_TIMESTAMP_INVALID"),
])
def test_wrong_audio_is_blocked(change, code):
    _, scene, binding, timeline = setup(); change(timeline)
    with pytest.raises(AudioBindingError) as caught:
        bind_scene_to_audio(scene, timeline, binding)
    assert caught.value.code == code


def test_split_subtitles_cover_exact_words_in_order_and_hash_is_required():
    _, scene, binding, timeline = setup()
    first = timeline["segments"][0]; text = first["text"]; cut = len(text)//2
    timeline["segments"][0:1] = [dict(first,id="part-a",beat_id=first["id"],text=text[:cut],end=1),
                                 dict(first,id="part-b",beat_id=first["id"],text=text[cut:],start=1)]
    bind_scene_to_audio(scene,timeline,binding)
    binding["sourceBeats"][0]["spoken_text_sha256"] = "0"*64
    with pytest.raises(AudioBindingError, match="source"):
        bind_scene_to_audio(scene,timeline,binding)


def test_short_audio_clamps_duration_but_rejects_out_of_beat_offset():
    _, scene, binding, timeline = setup()
    timeline["segments"][0]["end"] = 0.2
    bound = bind_scene_to_audio(scene,timeline,binding)
    assert bound["motion"][0]["durationMs"] == 200
    binding["actions"][scene["motion"][0]["actionId"]]["offsetMs"] = 300
    with pytest.raises(AudioBindingError) as caught:
        bind_scene_to_audio(scene,timeline,binding)
    assert caught.value.code == "AUDIO_ACTION_WINDOW"


def test_current_editor_checks_original_text_and_protects_repeated_action_ids():
    _, scene, binding, _ = setup()
    _validate_binding(binding,scene,CONTRACT_SLIDE["narration_beats"])
    modified = copy.deepcopy(scene); modified["motion"][-1]["durationMs"] = 400
    paths = protected_edit_paths(scene,modified,"scene")
    identity = modified["motion"][-1]["actionId"]
    assert ["scene","motion",identity,"durationMs"] in paths
    merged = merge_manual_edits(scene,binding,{"base_scene":scene,"scene":modified,"base_binding":binding,"binding":binding})
    assert merged["scene"]["motion"][-1]["durationMs"] == 400 and not merged["conflicts"]
    beats = copy.deepcopy(CONTRACT_SLIDE["narration_beats"]); beats[0]["spoken_text"] = "Changed"
    from html_scene_editing import SceneEditError
    with pytest.raises(SceneEditError):
        _validate_binding(binding,scene,beats)


def test_actual_model_result_can_compile_without_plan_edits():
    record = json.loads((ROOT/"docs/plans/html-backend-development/evidence/a02-model-smoke-2026-10-13.json").read_text(encoding="utf-8"))
    plan = record["plan"]
    contract = {"slide_id":plan["slide_id"],"narration_beats":[{"id":b["id"],"spoken_text":b["spoken_text"]} for b in plan["beats"]]}
    original = copy.deepcopy(plan)
    scene,binding = compile_plan(plan,contract,load_template_catalog(ROOT))
    assert plan == original and len(scene["motion"]) == 5
    assert scene["initialVisibleIds"] == ["header"] and len(binding["sourceBeats"]) == 4


def test_new_schema_requires_action_identity_and_rejects_legacy_upgrade_fields():
    from html_scene_editing import _compile
    _, scene, _, _ = setup()
    catalog = json.loads((ROOT/"html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    _compile(scene,catalog["assets"])
    scene["motion"][0].pop("actionId")
    from html_scene_editing import SceneEditError
    with pytest.raises(SceneEditError):
        _compile(scene,catalog["assets"])


def test_semantic_plan_runs_through_actual_production_service(tmp_path):
    from html_production_service import produce_scene
    from html_visual_review_service import HtmlReviewDependencies
    record = json.loads((ROOT/"docs/plans/html-backend-development/evidence/a02-model-smoke-2026-10-13.json").read_text(encoding="utf-8"))
    plan = record["plan"]
    contract = {"slide_id":plan["slide_id"],"narration_beats":[{"id":b["id"],"spoken_text":b["spoken_text"]} for b in plan["beats"]]}
    calls = []
    def generator(**kwargs):
        calls.append(kwargs)
        from checks.html_design_agent_fixture import response_for
        result = response_for(kwargs)
        if result is not None:
            return result
        if kwargs.get("artifact_prefix", "").startswith("design-reconstruct-"):
            return {"status":"unchanged","message":"fixture only; visual approval remains pending"}
        return copy.deepcopy(plan)
    from checks.test_html_e_production import png
    deps = HtmlReviewDependencies(ROOT,generator)
    first = produce_scene(contract,run_dir=tmp_path,deps=deps,provider=lambda *a,**kw:png(),options={"plan_version":"0.2.0"})
    assert first["stage"] == "design_review"
    result = produce_scene(contract,run_dir=tmp_path,deps=deps,options={"plan_version":"0.2.0","design_candidate_key":first["design"]["key"]})
    assert result["saved"]["changed"] and len(calls) == 4
    stored = json.loads((tmp_path/f"planning/html_visual/scene-{plan['slide_id']}.json").read_text(encoding="utf-8"))
    binding = json.loads((tmp_path/f"planning/html_visual/binding-{plan['slide_id']}.json").read_text(encoding="utf-8"))
    assert stored["version"] == "0.6.0" and binding["version"] == "0.2.0"
    assert len(stored["motion"]) == 5


def test_repeated_action_edit_requires_exact_identity(tmp_path):
    from html_scene_repair import candidate_from_document
    from html_scene_editing import SceneEditError
    _, scene, binding, _ = setup()
    folder=tmp_path/"planning";folder.mkdir()
    (folder/"visual_contract.json").write_text(json.dumps({"slides":[CONTRACT_SLIDE]}),encoding="utf-8")
    doc={"scene":scene,"binding":binding,"revision":0,"manual":None,"beats":CONTRACT_SLIDE["narration_beats"],"resources":{"assets":[],"pack":{}}}
    action=scene["motion"][-2]
    operation={"targetId":action["targetId"],"kind":"set_motion","action":"emphasize","values":{"durationMs":400}}
    request={"expected_revision":0,"operations":[operation]}
    with pytest.raises(SceneEditError) as caught:
        candidate_from_document(tmp_path,scene["id"],request,doc)
    assert caught.value.code=="REPAIR_ACTION_AMBIGUOUS"
    operation["actionId"]=action["actionId"]
    result=candidate_from_document(tmp_path,scene["id"],request,doc)
    assert result["scene"]["version"]=="0.6.0"
    assert next(a for a in result["scene"]["motion"] if a["actionId"]==action["actionId"])["durationMs"]==400
