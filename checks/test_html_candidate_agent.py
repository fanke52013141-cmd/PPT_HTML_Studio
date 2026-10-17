"""Candidate-only repair evidence; injected model, real graph/browser/editor."""

import copy
import json
from pathlib import Path

import pytest

from html_candidate_agent import repair_candidate


def test_geometry_constraints_keep_width_and_include_motion_safe_zone():
    from html_candidate_agent import _geometry_constraints
    node = {'id':'summary','slot':'summary','presentation':{'variant':'summary-arrow-overlay'}}
    scene = {'motion':[{'targetId':'summary','offsetY':12}]}
    layout = {'slots':{'summary':{'box':{'x':58,'y':660,'width':1477,'height':110}}}}
    result = _geometry_constraints(node,scene,layout,[{'id':'summary-arrow-overlay','minWidth':900,'minHeight':170}])
    assert result['suggestedPresentation'] == {'width':1477,'height':170,'offsetX':0,'offsetY':-42}
    assert result['feasible']
from html_visual_review_service import (
    HtmlReviewDependencies,
    HtmlReviewError,
    review_scene,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def draft(tmp_path):
    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/condensation.json").read_text(
            encoding="utf-8"
        )
    )
    scene["themeRef"]["id"] = "neutral-baseline"
    scene["version"] = "0.5.0"
    node = next(n for n in scene["nodes"] if n["id"] == "headline")
    node["presentation"] = {"typography": {"text": {"fontSizePx": 80}}}
    directory = tmp_path / "planning"
    directory.mkdir()
    (directory / "visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": scene["id"], "narration_beats": []}]}),
        encoding="utf-8",
    )
    return tmp_path, scene


def patch():
    return {
        "action": "patch",
        "operations": [
            {
                "targetId": "headline",
                "kind": "set_text_style",
                "part": "text",
                "values": {"fontSizePx": 28},
            }
        ],
    }


def test_summary_panel_long_state_uses_available_width_without_font_shrink(draft):
    run, scene = draft
    next(n for n in scene['nodes'] if n['id']=='headline')['presentation']['typography']['text']['fontSizePx'] = 28
    scene['version'] = '0.7.0'
    scene['initialVisibleIds'] = [n['id'] for n in scene['nodes']]
    scene['motion'] = []
    summary = next(n for n in scene['nodes'] if n['type']=='summary')
    summary['from']['text'] = '下级机关'
    summary['to']['text'] = '市地级以上'
    summary['term'] = '公开遴选'
    summary['presentation'] = {'variant':'summary-panel', 'width':1477}
    report = review_scene(scene, run_dir=run, deps=HtmlReviewDependencies(ROOT, lambda **kw: {}))
    assert report['passed'], report.get('message')
    assert 'typography' not in summary['presentation']


def test_summary_overflow_diagnostic_names_internal_parts(draft):
    run, scene = draft
    summary = next(n for n in scene['nodes'] if n['type']=='summary')
    # Legacy flow remains strict when its content really exceeds the slot.
    summary['term'] = '字' * 24
    report = review_scene(scene, run_dir=run, deps=HtmlReviewDependencies(ROOT, lambda **kw: {}), diagnostic=True)
    issue = next(i for i in report['capacityIssues'] if i['target']==summary['id'])
    assert {p['part'] for p in issue['internalParts']} == {'from','to','term','takeaway'}
    assert all('paddingX' in p and 'clientWidth' in p for p in issue['internalParts'])


def test_unsaved_capacity_failure_real_screenshot_agent_and_strict_recheck(draft):
    run, scene = draft
    original = copy.deepcopy(scene)
    calls = []

    def model(**kw):
        import inspect
        from json_llm_service import _generate_json_with_configured_llm

        inspect.signature(_generate_json_with_configured_llm).bind(**kw)
        calls.append(kw)
        assert kw['request_timeout'] == 180
        assert kw['reasoning_effort_override'] == 'low'
        assert json.loads(kw['user_prompt'])['previousDecisions'] == []
        node = next(n for n in json.loads(kw['user_prompt'])['nodes'] if n['id'] == 'headline')
        assert node['presentationSizeEditable']
        # Line/scroll-only failures have no canvas box trigger: do not invent a size hint.
        assert isinstance(node['capacitySizeHint'], dict)
        assert Path(kw["image_paths"][0]).read_bytes().startswith(b"\x89PNG")
        assert json.loads(kw["user_prompt"])["diagnostic"]["capacityIssues"]
        return patch()

    deps = HtmlReviewDependencies(ROOT, model)
    assert not review_scene(scene, run_dir=run, deps=deps)["passed"]
    diagnosis = review_scene(scene, run_dir=run, deps=deps, diagnostic=True)
    assert not diagnosis["passed"] and diagnosis["diagnosticOnly"]
    issue = diagnosis["capacityIssues"][0]
    assert issue["triggers"]
    assert issue["effectiveLimits"]["width"] > 0
    assert all(trigger["actual"] > trigger["limit"] + trigger["tolerance"] for trigger in issue["triggers"])
    result = repair_candidate(scene, None, run_dir=run, deps=deps)
    assert result["report"]["passed"] and len(calls) == 1
    assert result["summary"]["framework"] == "LangGraph"
    assert scene == original
    assert not list((run / "planning/html_visual").glob("scene-*.json"))
    assert result["scene"]["beats"] == original["beats"]
    assert result["scene"]["motion"] == original["motion"]


def test_manual_protection_and_budget_preserve_original(draft):
    run, scene = draft
    original = copy.deepcopy(scene)
    calls = []

    def model(**kw):
        calls.append(kw)
        return patch()

    manual = {
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
    }
    with pytest.raises(HtmlReviewError, match="未通过"):
        repair_candidate(
            scene,
            None,
            run_dir=run,
            deps=HtmlReviewDependencies(ROOT, model),
            manual=manual,
            max_rounds=2,
        )
    assert len(calls) == 2 and scene == original
    record = next(
        (run / "planning/html_visual/candidates").rglob("operation-error.json")
    )
    assert (
        json.loads(record.read_text(encoding="utf-8"))["code"]
        == "MANUAL_FIELD_PROTECTED"
    )


def test_stop_and_noncapacity_failure_do_not_save(draft):
    run, scene = draft
    calls = []

    def model(**kw):
        calls.append(kw)
        return {"action": "stop", "message": "需要换模板，超出允许范围"}

    deps = HtmlReviewDependencies(ROOT, model)
    with pytest.raises(HtmlReviewError):
        repair_candidate(scene, None, run_dir=run, deps=deps)
    assert len(calls) == 1


def test_noncapacity_failure_does_not_call_model(draft):
    run, scene = draft
    def model(**_):
        pytest.fail("noncapacity failures must not call the model")
    deps = HtmlReviewDependencies(ROOT, model)
    broken = copy.deepcopy(scene)
    broken["nodes"][0]["unregistered"] = True
    diagnostic = review_scene(broken, run_dir=run, deps=deps, diagnostic=True)
    assert not diagnostic["passed"] and not diagnostic.get("capacityIssues")
    with pytest.raises(HtmlReviewError):
        repair_candidate(broken, None, run_dir=run, deps=deps)


def test_fault_injected_improving_but_unfixed_capacity_stops_at_budget(draft, monkeypatch):
    from PIL import Image
    run, scene = draft
    original = copy.deepcopy(scene)
    screenshot = run / "capacity-fixture.png"
    Image.new("RGB", (64, 64), "white").save(screenshot)
    calls, events = [], []
    def review(current, **_):
        node = next(n for n in current["nodes"] if n["id"] == "headline")
        size = node["presentation"]["typography"]["text"]["fontSizePx"]
        return {"passed": False, "message": "CONTENT_CAPACITY_EXCEEDED: fixture",
                "capacityIssues": [{"target": "headline", "available": 40, "measured": size}],
                "screenshot": "capacity-fixture.png"}
    def apply(_run, _slide, request, document):
        updated = copy.deepcopy(document["scene"])
        node = next(n for n in updated["nodes"] if n["id"] == "headline")
        node["presentation"]["typography"]["text"]["fontSizePx"] = request["operations"][0]["values"]["fontSizePx"]
        return {"scene": updated, "binding": document["binding"]}
    def model(**_):
        calls.append(1)
        return {"action": "patch", "operations": [{"targetId": "headline", "kind": "set_text_style",
            "part": "text", "values": {"fontSizePx": 80 - 10 * len(calls)}}]}
    monkeypatch.setattr("html_candidate_agent.review_scene", review)
    monkeypatch.setattr("html_candidate_agent.candidate_from_document", apply)
    monkeypatch.setattr("html_candidate_agent.editor.resources", lambda *_: {})
    with pytest.raises(HtmlReviewError):
        repair_candidate(scene, None, run_dir=run, deps=HtmlReviewDependencies(ROOT, model),
                         max_rounds=2, progress=events.append)
    assert len(calls) == 2 and scene == original
    action = events[-1]["next_action"]
    assert action["reason"] == "budget_exhausted" and action["automatic_retry"] is False
    result = json.loads(next((run / "planning/html_visual/candidates").glob("*/layout-agent/*/result.json")).read_text(encoding="utf-8"))
    assert result["next_action"] == action and result["passed"] is False
