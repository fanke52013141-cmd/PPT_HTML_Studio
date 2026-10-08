# -*- coding: utf-8 -*-
"""annotation_store 持久化测试:原子写、损坏诊断、revision 语义、写失败保护。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_contracts import (  # noqa: E402
    AnnotationItem,
    AnnotationPage,
    AnnotationSettings,
    default_annotation_settings,
)
from annotation_store import (  # noqa: E402
    AnnotationStore,
    AnnotationStoreDependencies,
    AnnotationStoreError,
)
from pipeline_lifecycle import write_json_atomic  # noqa: E402

CANVAS = (1920, 1080)


def _make_store(writer=write_json_atomic) -> AnnotationStore:
    return AnnotationStore(AnnotationStoreDependencies(write_json_atomic=writer))


def _settings(revision: int = 1, enabled: bool = False) -> AnnotationSettings:
    base = default_annotation_settings()
    return AnnotationSettings(revision=revision, enabled=enabled, defaults=base.defaults, updated_at="2026-09-27T00:00:00Z")


def _page(revision: int = 1) -> AnnotationPage:
    return AnnotationPage(slide_id="slide_001", revision=revision, items=(), ai_suggestion_snapshot=None, updated_at="ts")


def test_missing_files_mean_unused(tmp_path: Path):
    store = _make_store()
    assert store.read_settings(str(tmp_path)) is None
    assert store.read_page(str(tmp_path), "slide_001", canvas=CANVAS) is None


def test_settings_round_trip(tmp_path: Path):
    store = _make_store()
    store.write_settings(str(tmp_path), _settings(revision=3, enabled=True))
    loaded = store.read_settings(str(tmp_path))
    assert loaded is not None
    assert loaded.revision == 3 and loaded.enabled is True
    assert (tmp_path / "planning" / "annotation_settings.json").exists()


def test_page_round_trip_with_items(tmp_path: Path):
    store = _make_store()
    item_payload = {
        "annotation_id": "ann_001",
        "target": {"kind": "region", "layout_revision": None, "token_ids": [], "polygons": [[[10, 10], [100, 10], [100, 60], [10, 60]]], "quote": None, "granularity": "region", "mask_group_ids": []},
        "anchor": None,
        "style": {"type": "underline", "color": "#123456", "opacity": 0.5, "width": 4, "padding": 2, "seed": 7},
        "timing": {"trigger_mode": "anchor_start", "offset_sec": 0.0, "draw_duration_sec": 0.4, "hold_mode": "beat_end", "exit_duration_sec": 0.1},
        "status": {"content": "draft", "spatial": "valid", "temporal": "awaiting_audio"},
        "protection": {"source": "manual", "modified_fields": [], "locked": False},
        "inputs": {"image_hash": None, "narration_hash": None, "audio_hash": None},
    }
    issues = []
    item = AnnotationItem.from_payload(item_payload, issues, canvas=CANVAS)
    assert item is not None and not issues
    page = AnnotationPage(slide_id="slide_001", revision=5, items=(item,))
    store.write_page(str(tmp_path), "slide_001", page)

    loaded = store.read_page(str(tmp_path), "slide_001", canvas=CANVAS)
    assert loaded is not None
    assert loaded.revision == 5
    assert loaded.items[0].style.color == "#123456"
    # 写出的 JSON 不允许 NaN/Infinity(allow_nan 默认 True 的 json.dumps 会放行,
    # 契约层已拒绝;这里验证存储写出的字节可被严格解析器读回)
    raw = (tmp_path / "slides" / "slide_001" / "annotations.json").read_text(encoding="utf-8")
    json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def test_corrupt_json_is_diagnostic_not_empty_success(tmp_path: Path):
    store = _make_store()
    settings_path = tmp_path / "planning" / "annotation_settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{ not-json", encoding="utf-8")
    with pytest.raises(AnnotationStoreError) as excinfo:
        store.read_settings(str(tmp_path))
    assert excinfo.value.code == "corrupt"
    assert "annotation_settings.json" in str(excinfo.value.path)

    page_path = tmp_path / "slides" / "slide_001" / "annotations.json"
    page_path.parent.mkdir(parents=True)
    page_path.write_text("[]", encoding="utf-8")
    with pytest.raises(AnnotationStoreError) as page_exc:
        store.read_page(str(tmp_path), "slide_001", canvas=CANVAS)
    assert page_exc.value.code == "schema"


def test_schema_version_mismatch_rejected(tmp_path: Path):
    store = _make_store()
    settings_path = tmp_path / "planning" / "annotation_settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"schema_version": 99, "revision": 1, "enabled": False}), encoding="utf-8")
    with pytest.raises(AnnotationStoreError) as excinfo:
        store.read_settings(str(tmp_path))
    assert excinfo.value.code == "schema"


def test_write_failure_keeps_original_intact(tmp_path: Path):
    store = _make_store()
    store.write_settings(str(tmp_path), _settings(revision=1, enabled=False))
    original = (tmp_path / "planning" / "annotation_settings.json").read_text(encoding="utf-8")

    def failing_writer(path, payload):
        raise RuntimeError("disk on fire")

    broken_store = _make_store(writer=failing_writer)
    with pytest.raises(AnnotationStoreError) as excinfo:
        broken_store.write_settings(str(tmp_path), _settings(revision=2, enabled=True))
    assert excinfo.value.code == "io"
    # 原文件原封不动——失败绝不半写
    assert (tmp_path / "planning" / "annotation_settings.json").read_text(encoding="utf-8") == original


def test_unsafe_slide_id_rejected(tmp_path: Path):
    store = _make_store()
    with pytest.raises(Exception):
        store.page_path(str(tmp_path), "../escape")
