# -*- coding: utf-8 -*-
"""annotation_routes/service 集成测试:CRUD、revision 冲突、账号隔离、门禁。

使用 conftest 隔离的临时数据库与 runs 目录;服务/存储以生产依赖装配
(真实 write_json_atomic + 项目锁),路由用独立 FastAPI 应用挂载。
"""
from __future__ import annotations

import hashlib
import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from account_context import account_scope  # noqa: E402
from annotation_routes import router  # noqa: E402
from annotation_service import (  # noqa: E402
    AnnotationServiceDependencies,
    configure_annotation_service,
    get_annotation_service,
)
from annotation_store import (  # noqa: E402
    AnnotationStoreDependencies,
    configure_annotation_store,
    get_annotation_store,
)
from database import Project, SessionLocal  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from project_runtime_service import reveal_lock_for  # noqa: E402
from repository_paths import RUNS_DIR  # noqa: E402

SPOKEN = "报名时间到9月30日截止"  # "9月30日" = 码点 [5, 9)


def _make_project(account_id: str = "default") -> tuple[str, Path]:
    from database import Account

    project_id = "ann" + uuid.uuid4().hex[:12]
    run_root = Path(RUNS_DIR) / project_id
    (run_root / "planning").mkdir(parents=True)
    slide_root = run_root / "slides" / "slide_001"
    slide_root.mkdir(parents=True)
    (run_root / "planning" / "visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": "slide_001"}]}), encoding="utf-8"
    )
    (slide_root / "visual_draft.png").write_bytes(b"\x89PNG-fake-bytes")
    (slide_root / "narration_beats.json").write_text(
        json.dumps(
            {"slide_id": "slide_001", "beats": [{"id": "slide_001_beat_001", "spoken_text": SPOKEN}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    db = SessionLocal()
    if account_id != "default":
        db.add(Account(id=account_id, name=account_id, status="active"))
        db.commit()
    # 生产约定:Project.run_dir 存绝对路径(RUNS_DIR / project_id)
    db.add(Project(id=project_id, name="annotation-test", run_dir=str(run_root), account_id=account_id))
    db.commit()
    db.close()
    return project_id, run_root


def _drop_project(project_id: str) -> None:
    db = SessionLocal()
    db.query(Project).filter(Project.id == project_id).delete()
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def client():
    configure_annotation_store(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))
    configure_annotation_service(
        AnnotationServiceDependencies(store=get_annotation_store(), lock_for=reveal_lock_for)
    )
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def project():
    project_id, run_root = _make_project()
    yield project_id, run_root
    _drop_project(project_id)


REGION_ITEM = {
    "target": {
        "kind": "region",
        "layout_revision": None,
        "token_ids": [],
        "polygons": [[[100, 200], [400, 200], [400, 260], [100, 260]]],
        "quote": None,
        "granularity": "region",
        "mask_group_ids": [],
    },
    "style": {"type": "ellipse", "color": "#F46A38", "opacity": 0.85, "width": 5, "padding": 8, "seed": 11},
    "timing": {"trigger_mode": "anchor_start", "offset_sec": 0.0, "draw_duration_sec": 0.6, "hold_mode": "beat_end", "exit_duration_sec": 0.15},
}

TEXT_ITEM = {
    "target": {
        "kind": "text",
        "layout_revision": 1,
        "token_ids": ["token_07"],
        "polygons": [[[800, 400], [960, 400], [960, 445], [800, 445]]],
        "quote": "9月30日",
        "granularity": "word",
        "mask_group_ids": [],
    },
    "anchor": {
        "beat_id": "slide_001_beat_001",
        "offset_unit": "unicode_codepoint",
        "range": [5, 10],
        "quote": "9月30日",
        "occurrence": 1,
        "context_before": "报名时间到",
        "context_after": "截止",
    },
    "style": {"type": "underline", "color": "#1D4ED8", "opacity": 0.7, "width": 4, "padding": 3, "seed": 5},
    "timing": {"trigger_mode": "anchor_start", "offset_sec": -0.1, "draw_duration_sec": 0.5, "hold_mode": "beat_end", "exit_duration_sec": 0.1},
}


# ---------------------------------------------------------------- 基础读取


def test_unknown_project_404(client):
    assert client.get("/api/projects/no-such/annotations").status_code == 404


def test_summary_defaults_and_readiness_unused(client, project):
    project_id, _ = project
    resp = client.get(f"/api/projects/{project_id}/annotations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["settings"]["enabled"] is False
    # 缺设置文件 = 未使用,revision 0;首次 PUT expected_revision=0 创建
    assert body["settings"]["revision"] == 0
    assert body["readiness"]["can_render"] is True
    assert body["slides"] == [{"slide_id": "slide_001", "revision": 0, "counts": {"total": 0, "draft": 0, "confirmed": 0, "disabled": 0}}]


def test_get_slide_returns_narration_and_input_hashes(client, project):
    project_id, run_root = project
    resp = client.get(f"/api/projects/{project_id}/annotations/slides/slide_001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["revision"] == 0 and body["items"] == []
    assert body["narration"]["beats"][0]["beat_id"] == "slide_001_beat_001"
    assert body["narration"]["beats"][0]["spoken_text"] == SPOKEN
    assert body["image"]["hash"] == hashlib.sha256(b"\x89PNG-fake-bytes").hexdigest()
    assert body["layout"] is None


def test_unknown_slide_404(client, project):
    project_id, _ = project
    assert client.get(f"/api/projects/{project_id}/annotations/slides/slide_999").status_code == 404


# ---------------------------------------------------------------- 设置


def test_settings_revision_conflict(client, project):
    project_id, _ = project
    resp = client.put(
        f"/api/projects/{project_id}/annotations/settings",
        json={"expected_revision": 5, "enabled": True},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["current_revision"] == 0


def test_settings_update_creates_and_bumps(client, project):
    project_id, _ = project
    resp = client.put(
        f"/api/projects/{project_id}/annotations/settings",
        json={"expected_revision": 0, "enabled": True},
    )
    assert resp.status_code == 200 and resp.json()["revision"] == 1
    resp = client.put(
        f"/api/projects/{project_id}/annotations/settings",
        json={"expected_revision": 1, "enabled": False, "defaults": {"color": "#123456"}},
    )
    assert resp.status_code == 200 and resp.json()["revision"] == 2
    assert resp.json()["defaults"]["color"] == "#123456"
    summary = client.get(f"/api/projects/{project_id}/annotations").json()
    assert summary["settings"]["revision"] == 2 and summary["settings"]["enabled"] is False


# ---------------------------------------------------------------- 条目编辑


def test_add_region_and_text_items_assign_ids_and_server_inputs(client, project):
    project_id, run_root = project
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["revision"] == 1
    item = body["items"][0]
    assert item["annotation_id"] == "ann_001"
    assert item["protection"]["source"] == "manual"
    assert item["inputs"]["image_hash"] == hashlib.sha256(b"\x89PNG-fake-bytes").hexdigest()
    assert item["status"]["content"] == "draft"

    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 1, "operations": [{"op": "add", "item": TEXT_ITEM}]},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2 and items[1]["annotation_id"] == "ann_002"
    assert items[1]["anchor"]["quote"] == "9月30日"


def test_manual_freehand_is_persisted_and_returned_as_renderable_stroke(client, project):
    project_id, _run_root = project
    manual = json.loads(json.dumps(REGION_ITEM))
    manual["target"]["path_points"] = [[120, 210], [170, 230], [240, 220], [330, 250]]
    manual["timing"] = {
        "trigger_mode": "manual", "manual_start_sec": 0, "offset_sec": 0,
        "draw_duration_sec": 0.6, "hold_mode": "slide_end", "exit_duration_sec": 0.15,
    }
    response = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": manual}]},
    )
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["target"]["path_points"] == manual["target"]["path_points"]
    assert item["strokes"][0]["points"] == manual["target"]["path_points"]
    assert item["strokes"][0]["closed"] is False


def test_manual_freehand_uses_portrait_project_canvas(client, project):
    project_id, run_root = project
    db = SessionLocal()
    db.query(Project).filter(Project.id == project_id).update({"canvas_profile": "portrait_9_16"})
    db.commit()
    db.close()

    manual = json.loads(json.dumps(REGION_ITEM))
    manual["target"]["polygons"] = [[[460, 1660], [620, 1660], [620, 1810], [460, 1810]]]
    manual["target"]["path_points"] = [[480, 1680], [530, 1740], [600, 1790]]
    manual["timing"] = {
        "trigger_mode": "manual", "manual_start_sec": 0, "offset_sec": 0,
        "draw_duration_sec": 0.6, "hold_mode": "slide_end", "exit_duration_sec": 0.15,
    }
    response = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": manual}]},
    )
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["target"]["path_points"] == manual["target"]["path_points"]

    slide_root = run_root / "slides" / "slide_001"
    (slide_root / "audio_timeline.json").write_text(json.dumps({
        "duration_sec": 1.0,
        "audio_content_duration_sec": 1.0,
        "segments": [{"beat_id": "slide_001_beat_001", "start": 0.0, "end": 0.9}],
    }), encoding="utf-8")
    settings = client.put(
        f"/api/projects/{project_id}/annotations/settings",
        json={"expected_revision": 0, "enabled": True},
    )
    assert settings.status_code == 200, settings.text
    confirmation = client.post(
        f"/api/projects/{project_id}/annotations/slides/slide_001/confirm",
        json={"expected_revision": 1},
    )
    assert confirmation.status_code == 200, confirmation.text
    assert confirmation.json()["timeline_built"] is True

    timeline = json.loads((slide_root / "annotation_timeline.json").read_text(encoding="utf-8"))
    event = timeline["events"][0]
    assert timeline["canvas"] == [1080, 1920]
    assert event["strokes"][0]["points"] == manual["target"]["path_points"]
    assert event["strokes"][0]["ink"]["canvas"] == [1080, 1920]


def test_add_text_with_bad_quote_rejected(client, project):
    project_id, _ = project
    bad = json.loads(json.dumps(TEXT_ITEM, ensure_ascii=False))
    bad["anchor"]["quote"] = "十月一日"
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": bad}]},
    )
    assert resp.status_code == 422
    issues = resp.json()["detail"]["issues"]
    assert any(issue["code"] == "quote_mismatch" for issue in issues)


def test_add_text_with_unknown_beat_rejected(client, project):
    project_id, _ = project
    bad = json.loads(json.dumps(TEXT_ITEM, ensure_ascii=False))
    bad["anchor"]["beat_id"] = "slide_001_beat_099"
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": bad}]},
    )
    assert resp.status_code == 422
    assert any(issue["code"] == "unknown_beat" for issue in resp.json()["detail"]["issues"])


def test_page_revision_conflict_returns_409(client, project):
    project_id, _ = project
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 3, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["current_revision"] == 0


def test_update_maintains_modified_fields(client, project):
    project_id, _ = project
    client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={
            "expected_revision": 1,
            "operations": [
                {
                    "op": "update",
                    "annotation_id": "ann_001",
                    "patch": {"style": {**REGION_ITEM["style"], "color": "#00AA00"}},
                }
            ],
        },
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["style"]["color"] == "#00AA00"
    assert "style" in item["protection"]["modified_fields"]


def test_cannot_forge_confirmation_or_protection(client, project):
    project_id, _ = project
    client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={
            "expected_revision": 1,
            "operations": [{"op": "update", "annotation_id": "ann_001", "patch": {"status": {"content": "confirmed"}}}],
        },
    )
    assert resp.status_code == 422
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={
            "expected_revision": 1,
            "operations": [{"op": "update", "annotation_id": "ann_001", "patch": {"protection": {"source": "ai"}}}],
        },
    )
    assert resp.status_code == 422


def test_delete_item(client, project):
    project_id, _ = project
    client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 1, "operations": [{"op": "delete", "annotation_id": "ann_001"}]},
    )
    assert resp.status_code == 200 and resp.json()["items"] == []
    # 删除后文件仍在(revision 3),重开可读
    page = json.loads((project[1] / "slides" / "slide_001" / "annotations.json").read_text(encoding="utf-8"))
    assert page["revision"] == 2 and page["items"] == []


def test_missing_image_blocks_edit(client, project):
    project_id, run_root = project
    (run_root / "slides" / "slide_001" / "visual_draft.png").unlink()
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    assert resp.status_code == 422
    assert "图片" in resp.json()["detail"]


def test_corrupt_page_file_is_500_with_diagnostics(client, project):
    project_id, run_root = project
    page_path = run_root / "slides" / "slide_001" / "annotations.json"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text("{ broken", encoding="utf-8")
    resp = client.get(f"/api/projects/{project_id}/annotations/slides/slide_001")
    assert resp.status_code == 500
    assert "annotations.json" in resp.json()["detail"]


# ---------------------------------------------------------------- 门禁与隔离


def test_readiness_gates_per_handover(client, project):
    project_id, _ = project
    # enabled + 无任何条目 → no_annotations
    client.put(f"/api/projects/{project_id}/annotations/settings", json={"expected_revision": 0, "enabled": True})
    body = client.get(f"/api/projects/{project_id}/annotations").json()
    assert body["readiness"] == {"can_render": False, "reason": "no_annotations", "blocking": []}

    # enabled + 未确认条目 → unconfirmed_items 且逐条列出
    client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    body = client.get(f"/api/projects/{project_id}/annotations").json()
    assert body["readiness"]["can_render"] is False
    assert body["readiness"]["reason"] == "unconfirmed_items"
    assert body["readiness"]["blocking"] == [{"slide_id": "slide_001", "annotation_id": "ann_001", "reason": "unconfirmed"}]

    # 关闭功能 → 恢复可导出,草稿保留
    client.put(f"/api/projects/{project_id}/annotations/settings", json={"expected_revision": 1, "enabled": False})
    body = client.get(f"/api/projects/{project_id}/annotations").json()
    assert body["readiness"]["can_render"] is True
    assert body["slides"][0]["counts"]["draft"] == 1


def test_account_isolation_other_account_gets_404(client, project):
    other_id, _ = _make_project(account_id="acct_other_" + uuid.uuid4().hex[:8])
    try:
        # 默认账号看不到 other 账号的项目
        assert client.get(f"/api/projects/{other_id}/annotations").status_code == 404
    finally:
        _drop_project(other_id)


def test_account_scope_allows_owner(client, project):
    project_id, _ = project
    account = "acct_owner_" + uuid.uuid4().hex[:8]
    owned_id, _ = _make_project(account_id=account)
    try:
        db = SessionLocal()
        try:
            with account_scope(account):
                summary = get_annotation_service().get_summary(db, owned_id)
            assert summary["settings"]["enabled"] is False
        finally:
            db.close()
    finally:
        _drop_project(owned_id)


# ---------------------------------------------------------------- W4: 确认门禁


def test_confirm_gate_flow(client, project):
    project_id, _ = project
    base = f"/api/projects/{project_id}/annotations"
    # 添加区域条目
    client.patch(
        f"{base}/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    # 启用勾画
    client.put(f"{base}/settings", json={"expected_revision": 1, "enabled": True})

    # revision 冲突
    resp = client.post(f"{base}/slides/slide_001/confirm", json={"expected_revision": 99})
    assert resp.status_code == 409

    # 正常确认
    resp = client.post(f"{base}/slides/slide_001/confirm", json={"expected_revision": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["confirmed"] == 1
    assert body["readiness"]["can_render"] is True  # 全部确认后可导出
    # 确认后的条目带输入快照
    detail = client.get(f"{base}/slides/slide_001").json()
    item = detail["items"][0]
    assert item["status"]["content"] == "confirmed"
    assert item["confirmed_inputs"]["image_hash"] == item["inputs"]["image_hash"]

    # 无标注页确认被拒绝
    resp = client.post(f"{base}/slides/slide_001/confirm", json={"expected_revision": 2})
    assert resp.status_code == 200  # 已确认页幂等重确认成功


def test_confirm_requires_explicit_review_acceptance(client, project):
    project_id, run_root = project
    base = f"/api/projects/{project_id}/annotations"
    # 直接写入一条 needs_review 条目(经真实 patch 后手动置状态不可行,走 restore 构造 AI 条目不适用;
    # 这里通过 store 层面构造:添加条目后用 update 把 target 改成 line 粒度不可行 —— 用计划快照恢复路径)
    client.patch(
        f"{base}/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )
    # 人为把 spatial 置为 needs_review(模拟规划器/换图结果)
    page_path = run_root / "slides" / "slide_001" / "annotations.json"
    page = json.loads(page_path.read_text(encoding="utf-8"))
    page["items"][0]["status"]["spatial"] = "needs_review"
    page_path.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")

    # 不带 accepted_review → 422 review_required
    resp = client.post(f"{base}/slides/slide_001/confirm", json={"expected_revision": 1})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "review_required"
    assert detail["items"][0]["reason"] == "needs_review"

    # 显式接受后确认成功
    annotation_id = detail["items"][0]["annotation_id"]
    resp = client.post(
        f"{base}/slides/slide_001/confirm",
        json={"expected_revision": 1, "accepted_review": [annotation_id]},
    )
    assert resp.status_code == 200
    assert resp.json()["confirmed"] == 1


# ---------------------------------------------------------------- R4-004: 确认后编辑


def _manual_item() -> dict:
    item = json.loads(json.dumps(REGION_ITEM))
    item["target"]["path_points"] = [[120, 210], [170, 230], [240, 220], [330, 250]]
    item["timing"] = {
        "trigger_mode": "manual", "manual_start_sec": 0, "offset_sec": 0,
        "draw_duration_sec": 0.6, "hold_mode": "slide_end", "exit_duration_sec": 0.15,
    }
    return item


def _prepare_confirmed_project(client, project):
    """添加手动定时条目并确认,返回 (base, timeline_path, timeline_bytes)。"""
    project_id, run_root = project
    base = f"/api/projects/{project_id}/annotations"
    client.patch(
        f"{base}/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "add", "item": _manual_item()}]},
    )
    (run_root / "slides" / "slide_001" / "audio_timeline.json").write_text(json.dumps({
        "duration_sec": 1.0,
        "audio_content_duration_sec": 1.0,
        "segments": [{"beat_id": "slide_001_beat_001", "start": 0.0, "end": 0.9}],
    }), encoding="utf-8")
    client.put(f"{base}/settings", json={"expected_revision": 0, "enabled": True})
    confirm = client.post(f"{base}/slides/slide_001/confirm", json={"expected_revision": 1})
    assert confirm.status_code == 200 and confirm.json()["timeline_built"] is True, confirm.text
    timeline_path = run_root / "slides" / "slide_001" / "annotation_timeline.json"
    assert timeline_path.is_file()
    return base, timeline_path


def test_editing_confirmed_item_resets_draft_and_invalidates_timeline(client, project):
    base, timeline_path = _prepare_confirmed_project(client, project)
    resp = client.patch(
        f"{base}/slides/slide_001",
        json={
            "expected_revision": 2,
            "operations": [{"op": "update", "annotation_id": "ann_001", "patch": {"style": {"type": "ellipse", "color": "#00AA00", "opacity": 0.85, "width": 5, "padding": 8, "seed": 11}}}],
        },
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item["status"]["content"] == "draft"
    assert item["style"]["color"] == "#00AA00"
    assert not timeline_path.is_file()


def test_same_value_save_keeps_confirmed_state(client, project):
    base, timeline_path = _prepare_confirmed_project(client, project)
    resp = client.patch(
        f"{base}/slides/slide_001",
        json={
            "expected_revision": 2,
            "operations": [{"op": "update", "annotation_id": "ann_001", "patch": {"style": {"type": "ellipse", "color": "#F46A38", "opacity": 0.85, "width": 5, "padding": 8, "seed": 11}}}],
        },
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item["status"]["content"] == "confirmed"
    assert timeline_path.is_file()


def test_lock_toggle_does_not_reset_confirmed_item(client, project):
    base, timeline_path = _prepare_confirmed_project(client, project)
    resp = client.patch(
        f"{base}/slides/slide_001",
        json={
            "expected_revision": 2,
            "operations": [{"op": "update", "annotation_id": "ann_001", "patch": {"protection": {"locked": True}}}],
        },
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item["protection"]["locked"] is True
    assert item["status"]["content"] == "confirmed"
    assert timeline_path.is_file()
