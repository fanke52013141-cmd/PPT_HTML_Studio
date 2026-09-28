"""Replacing an image preserves the previous user image in the project run."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

import ai_provider_service as provider
import image_workflow_service as workflow


def test_archive_current_slide_image_preserves_source_and_provenance(tmp_path: Path) -> None:
    slide = tmp_path / "slides" / "slide_001"
    slide.mkdir(parents=True)
    (slide / "visual_draft.png").write_bytes(b"previous-image")
    (slide / "visual_provenance.json").write_text('{"source":"upload"}', encoding="utf-8")
    project = SimpleNamespace(run_dir=str(tmp_path))

    archive = workflow.archive_current_slide_image(project, "slide_001")

    assert archive is not None
    assert archive.parent == tmp_path / "recovery" / "images"
    assert (archive / "visual_draft.png").read_bytes() == b"previous-image"
    assert (archive / "visual_provenance.json").read_text(encoding="utf-8") == '{"source":"upload"}'
    assert (slide / "visual_draft.png").read_bytes() == b"previous-image"


def test_applying_identical_candidate_keeps_downstream_state(tmp_path: Path, monkeypatch) -> None:
    slide = tmp_path / "slides" / "slide_001"
    slide.mkdir(parents=True)
    (slide / "visual_draft.png").write_bytes(b"same-image")
    (slide / "visual_candidate.png").write_bytes(b"same-image")
    project = SimpleNamespace(run_dir=str(tmp_path))
    invalidations = []
    monkeypatch.setattr(workflow, "project_or_404", lambda *_: project)
    monkeypatch.setattr(
        workflow,
        "current_slide_file_or_404",
        lambda _project, _slide_id, filename: str(slide / filename),
    )
    monkeypatch.setattr(workflow, "rename_mask_source_pair", lambda *_: None)
    monkeypatch.setattr(workflow, "promote_candidate_provenance", lambda *_: None)
    monkeypatch.setattr(workflow, "mark_slide_image_changed", lambda *_: invalidations.append(True))
    monkeypatch.setattr(workflow, "reveal_lock_for", lambda _project: workflow.invalidation_service.project_artifact_lock(tmp_path))

    result = workflow.apply_slide_candidate(
        "project", {"slide_id": "slide_001"}, object()
    )

    assert result["success"] is True
    assert invalidations == []
    assert not (tmp_path / "recovery" / "images").exists()


def _png(color: str, *, center: str | None = None, metadata: str = "") -> bytes:
    image = Image.new("RGB", (32, 18), color)
    if center:
        image.paste(center, (10, 5, 22, 13))
    output = BytesIO()
    image.save(output, format="PNG")
    # Different upload bytes must still become the same normalized canvas.
    return output.getvalue() + metadata.encode("utf-8")


def _upload(content: bytes) -> SimpleNamespace:
    return SimpleNamespace(
        content_type="image/png",
        filename="replacement.png",
        file=BytesIO(content),
    )


def _prepare_upload_test(
    tmp_path: Path,
    monkeypatch,
    current: bytes,
) -> tuple[SimpleNamespace, Path, list[bool], list[dict]]:
    slide = tmp_path / "slides" / "slide_001"
    slide.mkdir(parents=True)
    image_path = slide / "visual_draft.png"
    provider.process_and_save_image(
        current,
        str(image_path),
        target_width=32,
        target_height=18,
        raw_save_path=str(workflow.mask_source_raw_path(image_path)),
    )
    workflow.seal_mask_source_pair(image_path)
    project = SimpleNamespace(run_dir=str(tmp_path))
    invalidations: list[bool] = []
    provenance_writes: list[dict] = []
    monkeypatch.setattr(workflow, "project_or_404", lambda *_: project)
    monkeypatch.setattr(
        workflow,
        "current_slide_file_or_404",
        lambda _project, _slide_id, filename: str(slide / filename),
    )
    monkeypatch.setattr(
        workflow,
        "get_project_canvas",
        lambda _project: {"width": 32, "height": 18},
    )
    monkeypatch.setattr(
        workflow,
        "_enforce_project_subtitle_safe_zone",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        workflow,
        "process_and_save_image",
        provider.process_and_save_image,
    )
    monkeypatch.setattr(
        workflow,
        "mark_slide_image_changed",
        lambda *_args: invalidations.append(True),
    )
    monkeypatch.setattr(workflow, "reveal_lock_for", lambda _project: workflow.invalidation_service.project_artifact_lock(tmp_path))
    monkeypatch.setattr(
        workflow,
        "write_visual_provenance",
        lambda *_args, **kwargs: provenance_writes.append(kwargs),
    )
    return project, image_path, invalidations, provenance_writes


def test_upload_with_same_normalized_canvas_preserves_downstream_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project, image_path, invalidations, provenance_writes = _prepare_upload_test(
        tmp_path, monkeypatch, _png("white")
    )
    original_master = image_path.read_bytes()
    original_raw = workflow.mask_source_raw_path(image_path).read_bytes()

    result = workflow.upload_slide_image(
        "project", "slide_001", _upload(_png("white", metadata="padding")), object()
    )

    assert result["success"] is True
    assert result["unchanged"] is True
    assert image_path.read_bytes() == original_master
    assert workflow.mask_source_raw_path(image_path).read_bytes() == original_raw
    assert invalidations == []
    assert provenance_writes == []
    assert not (Path(project.run_dir) / "recovery" / "images").exists()


def test_upload_with_changed_normalized_canvas_archives_and_invalidates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project, image_path, invalidations, provenance_writes = _prepare_upload_test(
        tmp_path, monkeypatch, _png("white")
    )
    original_master = image_path.read_bytes()

    result = workflow.upload_slide_image(
        "project", "slide_001", _upload(_png("white", center="black")), object()
    )

    archives = list((Path(project.run_dir) / "recovery" / "images").iterdir())
    assert result["success"] is True
    assert "unchanged" not in result
    assert image_path.read_bytes() != original_master
    assert len(archives) == 1
    assert (archives[0] / "visual_draft.png").read_bytes() == original_master
    assert invalidations == [True]
    assert len(provenance_writes) == 1


def test_upload_with_changed_active_raw_pair_invalidates_even_when_master_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project, image_path, invalidations, provenance_writes = _prepare_upload_test(
        tmp_path, monkeypatch, _png("white")
    )
    raw_path = workflow.mask_source_raw_path(image_path)
    raw_path.write_bytes(_png("white", center="black"))
    workflow.seal_mask_source_pair(image_path)
    previous_raw = raw_path.read_bytes()

    result = workflow.upload_slide_image(
        "project", "slide_001", _upload(_png("white")), object()
    )

    archives = list((Path(project.run_dir) / "recovery" / "images").iterdir())
    assert result["success"] is True
    assert "unchanged" not in result
    assert raw_path.read_bytes() != previous_raw
    assert (archives[0] / "visual_draft.raw.png").read_bytes() == previous_raw
    assert invalidations == [True]
    assert len(provenance_writes) == 1
