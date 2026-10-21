"""Image-grounded reconstruction, real renderer and guarded static operations."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from html_design_reconstruction import reconstruct_design
from html_production_service import compile_plan, produce_scene
from html_storyboard_planning import load_template_catalog
from html_visual_review_service import HtmlReviewDependencies, HtmlReviewError

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def case(tmp_path):
    record=json.loads((ROOT/"docs/plans/html-backend-development/evidence/a02-model-smoke-2026-10-13.json").read_text(encoding="utf-8"))
    plan=record["plan"]
    contract={"slide_id":plan["slide_id"],"narration_beats":[{"id":b["id"],"spoken_text":b["spoken_text"]} for b in plan["beats"]]}
    scene,binding=compile_plan(plan,contract,load_template_catalog(ROOT))
    reference=tmp_path/"reference.png";Image.new("RGB",(1280,720),"white").save(reference)
    return tmp_path,scene,binding,reference,contract


def test_pure_code_cannot_skip_design(case):
    run,_,_,_,contract=case
    calls=[]
    with pytest.raises(HtmlReviewError) as caught:
        produce_scene(contract,run_dir=run,deps=HtmlReviewDependencies(ROOT,lambda **kw:calls.append(kw)))
    assert caught.value.code=="DESIGN_PROVIDER_MISSING" and not calls


def test_registered_variants_are_consumed_without_changing_text_or_actions(case):
    run,scene,binding,reference,contract=case;calls=[]
    operations=[{"targetId":"stat-input","kind":"set_variant","values":{"variant":"text-card-outline","icon":"speech"}},
                # Keep the card above billing-caption, whose slot starts at y=440.
                {"targetId":"stat-input","kind":"set_presentation","values":{"height":138}},
                {"targetId":"header","kind":"set_variant","values":{"variant":"header-badge"}},
                {"targetId":"billing-summary","kind":"set_variant","values":{"variant":"summary-panel"}}]
    def generator(**kw):
        from checks.html_design_agent_fixture import response_for
        result = response_for(kw)
        if result is not None:
            return result
        calls.append(kw)
        assert len(kw["image_paths"])==2 and all(Path(p).is_file() for p in kw["image_paths"])
        assert [Path(p).name for p in kw["image_paths"]] == ["reference.png", "current.png"]
        assert "每轮第二张是当前实际HTML截图" in kw["system_prompt"]
        assert kw["request_timeout"] == 600
        assert "thinking" not in kw and "extra_body" not in kw
        assert "text-card-outline" in kw["user_prompt"]
        assert 'values字段名必须为variant' in kw['system_prompt']
        assert 'variantId或variant_id' in kw['system_prompt']
        return {"status":"candidate","operations":operations}
    result=reconstruct_design(scene,binding,reference,run_dir=run,deps=HtmlReviewDependencies(ROOT,generator),beats=contract["narration_beats"])
    assert result["scene"]["version"]=="0.7.0" and result["report"]["passed"]
    assert result["scene"]["motion"]==scene["motion"] and result["binding"]==binding
    for before,after in zip(scene["nodes"],result["scene"]["nodes"]):
        assert before=={k:v for k,v in after.items() if k!="presentation"}
    assert result["summary"]["visual_fidelity"]=="model_pass_pending_user_review" and len(calls)==1
    from artifact_fingerprint import sha256_file
    audit = run / result["summary"]["audit"]
    request = json.loads((audit / "0/request.json").read_text(encoding="utf-8"))
    assert request["image_roles"] == ["design_reference", "current_html_render"]
    assert request["image_sha256"] == [sha256_file(Path(p)) for p in calls[0]["image_paths"]]
    assert request["image_sha256"][0] != request["image_sha256"][1]


def test_transport_unknown_is_not_retried(case):
    run,scene,binding,reference,contract=case;calls=[]
    def generator(**kw):
        from checks.html_design_agent_fixture import response_for
        result = response_for(kw)
        if result is not None:
            return result
        calls.append(kw);raise TimeoutError("fixture unknown")
    with pytest.raises(TimeoutError):
        reconstruct_design(scene,binding,reference,run_dir=run,deps=HtmlReviewDependencies(ROOT,generator),beats=contract["narration_beats"])
    assert len(calls)==1
    assert len(calls[0]["image_paths"]) == 2


def test_reconstruction_cannot_change_motion(case):
    run,scene,binding,reference,contract=case;original=copy.deepcopy(scene);calls=[];events=[]
    def generator(**kw):
        calls.append(kw)
        from checks.html_design_agent_fixture import response_for
        result = response_for(kw)
        if result is not None:
            calls.pop()
            return result
        assert len(kw["image_paths"]) == 2
        assert [Path(p).name for p in kw["image_paths"]] == ["reference.png", "current.png"]
        return {"status":"candidate","operations":[{"targetId":"stat-input","kind":"set_motion","action":"enter","values":{"startMs":0}}]}
    with pytest.raises(HtmlReviewError) as caught:
        reconstruct_design(scene,binding,reference,run_dir=run,deps=HtmlReviewDependencies(ROOT,generator),beats=contract["narration_beats"],progress=events.append)
    assert caught.value.code=="RECONSTRUCTION_REJECTED" and len(calls)==2 and scene==original
    assert events[-1]["next_action"] == {"stage": "reconstruction", "reason": "budget_exhausted",
                                           "routes": ["manual_review"], "automatic_retry": False}


def test_unchanged_cannot_bypass_geometry_or_reach_fidelity(case, monkeypatch):
    import html_design_reconstruction as reconstruction
    run, scene, binding, reference, contract = case
    calls = []
    failure = {"passed": False, "issues": [{"code": "TEMPORAL_OVERLAP",
               "targets": ["stat-input", "billing-caption"], "reason": "stroke_crosses_text"}]}

    def review(current, **kwargs):
        return {"passed": not kwargs.get("preflight_dir"),
                "geometry": {n["id"]: {} for n in scene["nodes"]},
                "screenshot": reference.name,
                **({"code": "GEOMETRY_PREFLIGHT_REJECTED", "geometry_preflight": failure}
                   if kwargs.get("preflight_dir") else {})}

    def generator(**kwargs):
        from checks.html_design_agent_fixture import response_for
        result = response_for(kwargs)
        if result is not None:
            return result
        payload = json.loads(kwargs["user_prompt"])
        assert payload["geometry_preflight"] == failure
        if calls:
            assert payload["diagnostic"]["geometry_preflight"] == failure
        calls.append(kwargs)
        return {"status": "unchanged", "message": "No changes"}

    monkeypatch.setattr(reconstruction, "review_scene", review)
    monkeypatch.setattr(reconstruction, "review_fidelity", lambda *a, **kw: pytest.fail("Failed geometry must precede fidelity"))
    before = copy.deepcopy(scene)
    with pytest.raises(HtmlReviewError) as caught:
        reconstruct_design(scene, binding, reference, run_dir=run,
                           deps=HtmlReviewDependencies(ROOT, generator), beats=contract["narration_beats"])
    assert caught.value.code == "RECONSTRUCTION_REJECTED" and len(calls) == 2
    assert scene == before and not (run / f"planning/html_visual/scene-{scene['id']}.json").exists()
