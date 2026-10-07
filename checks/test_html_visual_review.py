"""C04: compile & static review service — model plan generation (stubbed),
real browser review, approval binding and invalidation (AC06/AC07/AC04)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import html_visual_review_service as review
from html_design_brief import build_design_brief, load_effect_registry
from html_storyboard_planning import load_template_catalog
from route_inventory import iter_effective_routes
import server

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCENE = REPO_ROOT / "html_engine" / "visual" / "scenes" / "water-facts.json"

CONTRACT_SLIDE = {
    "slide_id": "slide_001",
    "visual_groups": [],
    "narration_beats": [
        {"id": "slide_001_beat_001", "spoken_text": "标准大气压下，水在0摄氏度结冰。"},
        {"id": "slide_001_beat_002", "spoken_text": "液态水放热凝固成冰。"},
    ],
}


def deps(tmp_path: Path, responses: list) -> tuple:
    calls: list[dict] = []

    def generator(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    return (
        review.HtmlReviewDependencies(
            repo_root=REPO_ROOT,
            json_generator=generator,
        ),
        calls,
    )


def model_plan() -> dict:
    return {
        "slide_id": "slide_001",
        "templateRef": {"id": "data-relation-v1", "version": "0.1.0"},
        "slots": {
            "header": {"kind": "header", "number": "01", "title": "水的关键温度"},
            "stat-1": {"kind": "text", "runs": [{"text": "0°C 冰点", "emphasis": False}]},
            "stat-2": {"kind": "text", "runs": [{"text": "4°C 密度最大", "emphasis": False}]},
            "stat-3": {"kind": "text", "runs": [{"text": "100°C 沸点", "emphasis": False}]},
            "summary": {
                "kind": "summary",
                "from": {"text": "液态水", "tone": "blue"},
                "to": {"text": "固态冰", "tone": "green"},
                "term": "凝固",
                "takeaway": "放热结冰",
            },
        },
        "objects": [
            {"id": "header", "slot": "header", "kind": "header"},
            {"id": "stat-1", "slot": "stat-1", "kind": "text"},
            {"id": "stat-2", "slot": "stat-2", "kind": "text"},
            {"id": "stat-3", "slot": "stat-3", "kind": "text"},
            {"id": "summary", "slot": "summary", "kind": "summary"},
        ],
        "beats": [
            {"id": "slide_001_beat_001", "target": {"objectId": "stat-1", "action": "enter"}},
            {"id": "slide_001_beat_002", "target": {"objectId": "summary", "action": "enter"}},
        ],
        "assets": [{"id": "copy", "role": "文字", "render_owner": "code"}],
    }


def test_plan_generation_records_ac06_context_and_ac07_evidence(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    service, calls = deps(tmp_path, [model_plan()])
    plan = review.generate_scene_plan(
        CONTRACT_SLIDE,
        run_dir=run_dir,
        repo_root=REPO_ROOT,
        json_generator=service.json_generator,
    )
    assert plan["slide_id"] == "slide_001"
    assert len(calls) == 1
    # AC06: the request context enumerated registered capabilities only.
    sent = calls[0]
    assert "data-relation-v1" in sent["system_prompt"]
    assert "未注册" in sent["system_prompt"] or "不得使用未列出" in sent["system_prompt"]
    record = json.loads(
        (run_dir / "planning/html_visual/records/plan-slide_001.json").read_text(
            encoding="utf-8"
        )
    )
    context = record["request_context"]
    assert len(context["catalog_sha256"]) == 64
    assert len(context["effect_registry_sha256"]) == 64
    assert record["attempts"][0]["accepted"] is True
    assert record["accepted"] is True
    # AC07: the beat→action map is part of the saved evidence.
    assert record["plan_evidence"]["beat_map"] == {
        "slide_001_beat_001": {"objectId": "stat-1", "action": "enter"},
        "slide_001_beat_002": {"objectId": "summary", "action": "enter"},
    }


def test_plan_generation_repairs_once_then_saves_diagnostics(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    bad = model_plan()
    bad["templateRef"] = {"id": "not-registered", "version": "0.1.0"}
    service, calls = deps(tmp_path, [bad, model_plan()])
    plan = review.generate_scene_plan(
        CONTRACT_SLIDE,
        run_dir=run_dir,
        repo_root=REPO_ROOT,
        json_generator=service.json_generator,
    )
    assert plan["templateRef"]["id"] == "data-relation-v1"
    assert len(calls) == 2
    assert "未通过校验" in calls[1]["system_prompt"]

    service2, calls2 = deps(tmp_path, [bad, bad])
    with pytest.raises(review.HtmlReviewError) as rejected:
        review.generate_scene_plan(
            CONTRACT_SLIDE,
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            json_generator=service2.json_generator,
        )
    assert rejected.value.status_code == 422
    assert len(calls2) == 2
    record = json.loads(
        (run_dir / "planning/html_visual/records/plan-slide_001.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["accepted"] is False
    assert record["attempts"][-1]["diagnostic_code"] == "TEMPLATE_UNREGISTERED"


@pytest.fixture(scope="module")
def real_scene() -> dict:
    return json.loads(ENGINE_SCENE.read_text(encoding="utf-8"))


def test_real_browser_review_passes_registered_scene(tmp_path, real_scene) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    service, _ = deps(tmp_path, [])
    report = review.review_scene(
        real_scene, run_dir=run_dir, deps=service
    )
    assert report["passed"] is True
    assert report["measuredObjects"] > 0
    assert (run_dir / report["screenshot"]).is_file()


def test_real_browser_review_reports_capacity_failure_with_object_id(
    tmp_path, real_scene
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    broken = json.loads(json.dumps(real_scene))
    for node in broken["nodes"]:
        if node.get("type") == "text" and node.get("role") == "body":
            node["runs"][0]["text"] = "超长内容" * 60
    service, _ = deps(tmp_path, [])
    report = review.review_scene(broken, run_dir=run_dir, deps=service)
    assert report["passed"] is False
    assert "CONTENT_CAPACITY_EXCEEDED" in report["message"]


def test_approval_binds_hashes_and_invalidates_on_change(
    tmp_path, real_scene
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    service, _ = deps(tmp_path, [])
    approval = review.approve_scene(
        real_scene, run_dir=run_dir, deps=service
    )
    assert approval["scene_sha256"]
    status = review.approval_status(
        real_scene, run_dir=run_dir, deps=service, slide_id=real_scene["id"]
    )
    assert status["valid"] is True

    edited = json.loads(json.dumps(real_scene))
    edited["name"] = "改名"
    status = review.approval_status(
        edited, run_dir=run_dir, deps=service, slide_id=real_scene["id"]
    )
    assert status["valid"] is False and status["reason"] == "scene_changed"

    themed = json.loads(json.dumps(real_scene))
    themed["themeRef"]["id"] = "neutral-science"
    status = review.approval_status(
        themed, run_dir=run_dir, deps=service, slide_id=real_scene["id"]
    )
    assert status["reason"] == "theme_changed"

    # Failed review cannot be approved.
    broken = json.loads(json.dumps(real_scene))
    for node in broken["nodes"]:
        if node.get("type") == "text" and node.get("role") == "body":
            node["runs"][0]["text"] = "超长内容" * 60
    with pytest.raises(review.HtmlReviewError) as blocked:
        review.approve_scene(broken, run_dir=run_dir, deps=service)
    assert blocked.value.status_code == 409


def test_review_routes_registered_and_gated() -> None:
    paths = {route.path for route in iter_effective_routes(server.app)}
    assert {
        "/api/projects/{project_id}/html-review/{slide_id}/plan/generate",
        "/api/projects/{project_id}/html-review/{slide_id}/review",
        "/api/projects/{project_id}/html-review/{slide_id}/approve",
        "/api/projects/{project_id}/html-review/{slide_id}/approval",
    } <= paths
    routes_source = Path(
        server.__file__
    ).parent.joinpath("html_visual_review_routes.py").read_text(encoding="utf-8")
    assert "仅适用于 HTML 后端项目" in routes_source
    assert "import server" not in routes_source
