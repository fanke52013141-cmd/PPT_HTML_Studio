"""B01: project-level visual_backend selection (html-backend plan).

Covers the migration backfill, create-time validation (image/html,
guided+16:9 only for the HTML backend), summary exposure, and the
initial-release rule that an existing project cannot switch backend.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from database import Base
from database_migrations import run_migrations
from project_service import (
    ProjectCreate,
    ProjectDependencies,
    ProjectService,
    ProjectUpdate,
)


def _service(tmp_path: Path) -> tuple[ProjectService, sessionmaker]:
    engine = create_engine(f"sqlite:///{tmp_path / 'projects.db'}")
    Base.metadata.create_all(engine)
    return (
        ProjectService(
            ProjectDependencies(
                runs_root=tmp_path / "runs",
                project_audio_confirmed=lambda _project: False,
            )
        ),
        sessionmaker(bind=engine),
    )


def test_visual_backend_migration_backfills_image(tmp_path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'legacy.db'}",
        connect_args={"check_same_thread": False},
    )
    assert run_migrations(engine) == [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    ]
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO projects (id, name, run_dir) "
                "VALUES ('legacy', '旧项目', 'runs/legacy')"
            )
        )
        row = conn.execute(
            text("SELECT visual_backend FROM projects WHERE id = 'legacy'")
        ).scalar_one()
    assert row == "image"


def test_html_backend_requires_guided_and_landscape(tmp_path: Path) -> None:
    service, factory = _service(tmp_path)
    db = factory()
    try:
        with pytest.raises(HTTPException) as one_click:
            service.create(
                ProjectCreate(
                    name="One-click html",
                    production_mode="one_click",
                    visual_backend="html",
                ),
                db,
            )
        assert one_click.value.status_code == 400
        with pytest.raises(HTTPException) as portrait:
            service.create(
                ProjectCreate(
                    name="Portrait html",
                    canvas_profile="9:16",
                    visual_backend="html",
                ),
                db,
            )
        assert portrait.value.status_code == 400
        with pytest.raises(HTTPException) as invalid:
            service.create(
                ProjectCreate(name="Bad backend", visual_backend="webgl"),
                db,
            )
        assert invalid.value.status_code == 400
    finally:
        db.close()


def test_html_project_roundtrip_and_summary(tmp_path: Path) -> None:
    service, factory = _service(tmp_path)
    db = factory()
    try:
        created = service.create(
            ProjectCreate(name="HTML 课程", visual_backend="html"),
            db,
        )
        assert created["project"]["visual_backend"] == "html"
        listed = service.list(db)
        assert listed[0]["visual_backend"] == "html"
        detail = service.get(created["project"]["id"], db)
        assert detail["visual_backend"] == "html"

        # Same-value write is an explicit confirmation, not a switch.
        confirmed = service.update(
            created["project"]["id"],
            ProjectUpdate(visual_backend="html"),
            db,
        )
        assert confirmed["project"]["visual_backend"] == "html"

        with pytest.raises(HTTPException) as switched:
            service.update(
                created["project"]["id"],
                ProjectUpdate(visual_backend="image"),
                db,
            )
        assert switched.value.status_code == 400
    finally:
        db.close()


def test_image_project_remains_default_backend(tmp_path: Path) -> None:
    service, factory = _service(tmp_path)
    db = factory()
    try:
        created = service.create(ProjectCreate(name="图片项目"), db)
        assert created["project"]["visual_backend"] == "image"
    finally:
        db.close()
