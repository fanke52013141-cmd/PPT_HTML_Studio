"""Annotation edits report only real output-composition impacts."""
from __future__ import annotations

import sys
from contextlib import nullcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_service import AnnotationService, AnnotationServiceDependencies
from annotation_store import AnnotationStore, AnnotationStoreDependencies
from pipeline_lifecycle import write_json_atomic
from project_impact_service import list_impacts


class _Project:
    id = "annotation-impact"

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = str(run_dir)
        self.current_step = 8
        self._statuses = {"8": "completed"}

    def get_step_status(self):
        return dict(self._statuses)

    def set_step_status(self, statuses):
        self._statuses = dict(statuses)


def _service(tmp_path: Path) -> tuple[AnnotationService, _Project]:
    project = _Project(tmp_path)
    store = AnnotationStore(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))
    service = AnnotationService(
        AnnotationServiceDependencies(
            store=store,
            lock_for=lambda _project: nullcontext(),
            now_iso=lambda: "2026-09-28T00:00:00Z",
        )
    )
    service._project_or_404 = lambda _db, _project_id: project
    service._run_dir = lambda _project: str(tmp_path)
    service._slide_ids_or_404 = lambda _project: ["slide_001"]
    service._image_hash = lambda _project, _slide_id: "a" * 64
    service._narration_hash = lambda _project, _slide_id: "b" * 64
    service._read_beats = lambda _project, _slide_id: []
    (tmp_path / "slides" / "slide_001").mkdir(parents=True)
    return service, project


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
    "timing": {"trigger_mode": "manual", "manual_start_sec": 0.5, "offset_sec": 0.0, "draw_duration_sec": 0.6, "hold_mode": "slide_end", "exit_duration_sec": 0.15},
}


def test_unchanged_settings_do_not_create_an_output_impact(tmp_path: Path) -> None:
    service, project = _service(tmp_path)

    unchanged = service.update_settings(None, project.id, {"expected_revision": 0, "enabled": False})

    assert unchanged["revision"] == 0
    assert list_impacts(tmp_path) == []
    assert project.get_step_status()["8"] == "completed"

    changed = service.update_settings(None, project.id, {"expected_revision": 0, "enabled": True})

    assert changed["revision"] == 1
    assert project.get_step_status()["8"] == "pending_reconfirmation"
    assert list_impacts(tmp_path)[0]["id"] == "annotation_changed:slide_001"

    repeated = service.update_settings(None, project.id, {"expected_revision": 1, "enabled": True})

    assert repeated["revision"] == 1
    assert len(list_impacts(tmp_path)) == 1


def test_annotation_edit_and_confirmation_only_invalidate_output_when_changed(tmp_path: Path) -> None:
    service, project = _service(tmp_path)
    old_video = tmp_path / "outputs" / "existing.mp4"
    old_video.parent.mkdir(parents=True)
    old_video.write_bytes(b"previous video stays available")

    created = service.patch_slide(
        None,
        project.id,
        "slide_001",
        {"expected_revision": 0, "operations": [{"op": "add", "item": REGION_ITEM}]},
    )

    assert created["revision"] == 1
    assert project.get_step_status()["8"] == "pending_reconfirmation"
    assert old_video.read_bytes() == b"previous video stays available"

    same_update = service.patch_slide(
        None,
        project.id,
        "slide_001",
        {
            "expected_revision": 1,
            "operations": [{"op": "update", "annotation_id": "ann_001", "patch": {"style": REGION_ITEM["style"]}}],
        },
    )

    assert same_update["revision"] == 1

    write_json_atomic(tmp_path / "slides" / "slide_001" / "audio_timeline.json", {"duration_sec": 3.0, "segments": [{"id": "slide_001_beat_001", "start": 0, "end": 3}]})
    confirmed = service.confirm_slide(None, project.id, "slide_001", {"expected_revision": 1})
    assert confirmed["revision"] == 2

    repeated_confirmation = service.confirm_slide(None, project.id, "slide_001", {"expected_revision": 2})
    assert repeated_confirmation["revision"] == 2
    assert len(list_impacts(tmp_path)) == 1
