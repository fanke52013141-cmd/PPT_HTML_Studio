# -*- coding: utf-8 -*-
"""project_or_404 账号隔离回归(R5-001/R5-002):

helper 必须按当前账号过滤,跨创作用户的项目 ID 统一 404;
62d5052 新增的复用确认端点同样经 helper 受保护。
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from account_context import account_scope  # noqa: E402
from database import Account, Project, SessionLocal  # noqa: E402
from project_path_service import project_or_404  # noqa: E402
from repository_paths import RUNS_DIR  # noqa: E402


def _make_project(account_id: str) -> str:
    project_id = "iso" + uuid.uuid4().hex[:12]
    run_root = Path(RUNS_DIR) / project_id
    (run_root / "planning").mkdir(parents=True)
    (run_root / "planning" / "visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": "slide_001"}]}), encoding="utf-8"
    )
    db = SessionLocal()
    try:
        if account_id != "default":
            db.merge(Account(id=account_id, name=account_id, status="active"))
        db.merge(Project(id=project_id, name="iso", run_dir=str(run_root), account_id=account_id))
        db.commit()
    finally:
        db.close()
    return project_id


def _drop_project(project_id: str) -> None:
    db = SessionLocal()
    try:
        db.query(Project).filter(Project.id == project_id).delete()
        db.query(Account).filter(Account.id.like("iso%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_helper_scopes_project_to_current_account() -> None:
    project_a = _make_project("default")
    account_b = "iso_acct_" + uuid.uuid4().hex[:8]
    project_b = _make_project(account_b)
    try:
        # default 上下文:B 账号项目不可见
        with pytest.raises(HTTPException) as exc:
            project_or_404(SessionLocal(), project_b)
        assert exc.value.status_code == 404
        assert project_or_404(SessionLocal(), project_a).id == project_a

        # B 账号上下文:只看到自己的项目
        with account_scope(account_b):
            assert project_or_404(SessionLocal(), project_b).id == project_b
            with pytest.raises(HTTPException):
                project_or_404(SessionLocal(), project_a)
    finally:
        _drop_project(project_a)
        _drop_project(project_b)


def test_reuse_storyboard_endpoint_is_account_scoped(tmp_path) -> None:
    from types import SimpleNamespace

    import project_routes

    account_b = "iso_acct_" + uuid.uuid4().hex[:8]
    project_b = _make_project(account_b)
    try:
        # 用真实路由函数 + 真实 DB:default 上下文访问 B 的项目必须 404
        db = SessionLocal()
        try:
            with pytest.raises(HTTPException) as exc:
                project_routes.confirm_storyboard_reuse(
                    project_b,
                    {"source_version": "x", "article_sha256": "x", "contract_sha256": "x"},
                    db,
                )
            assert exc.value.status_code == 404
            with pytest.raises(HTTPException):
                project_routes.preview_storyboard_reuse(project_b, db)
        finally:
            db.close()
    finally:
        _drop_project(project_b)
