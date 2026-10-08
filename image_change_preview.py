"""Read-only inventory and optimistic version for Step 3 image changes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from artifact_fingerprint import sha256_file, sha256_json
from pipeline_lifecycle import REVEAL_FILENAMES, read_json_file
from project_storage import safe_child, slide_dir


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def preview_image_change(run_dir: str | Path, slide_id: str) -> dict[str, Any]:
    """Describe existing assets affected by changing one slide image.

    This function never modifies files.  The version covers source and derived
    inputs so a confirmation cannot silently apply to a newer editor state.
    """
    root = Path(run_dir).resolve()
    slide = slide_dir(root, slide_id)
    image = slide / "visual_draft.png"
    candidate = slide / "visual_candidate.png"
    source_names = (
        "visual_draft.png", "visual_draft.raw.png", "visual_draft.raw.sha256",
        "visual_provenance.json",
    )
    geometry_names = ("text_layout.json", "annotations.json", "annotation_timeline.json")
    cache_names = (*REVEAL_FILENAMES,)
    source = [_relative(root, slide / name) for name in source_names if (slide / name).is_file()]
    geometry = [_relative(root, slide / name) for name in geometry_names if (slide / name).is_file()]
    generated = [_relative(root, slide / name) for name in cache_names if (slide / name).is_file()]
    for name in ("assets", "auto_mask"):
        if (slide / name).exists():
            generated.append(_relative(root, slide / name))
    generated.extend(_relative(root, path) for path in sorted(slide.glob("pptx_reveal_*.png")) if path.is_file())
    props = safe_child(root, "remotion_props.json")
    if props.is_file():
        generated.append(_relative(root, props))

    manifest_path = safe_child(root, "reveal_manifest.json")
    manifest = read_json_file(manifest_path)
    mask_groups = 0
    if isinstance(manifest, dict):
        for entry in manifest.get("slides", []) or []:
            if isinstance(entry, dict) and str(entry.get("slide_id") or "") == slide_id:
                mask_groups = len(entry.get("groups") or [])
                if mask_groups or entry.get("semantic_blocks"):
                    geometry.insert(0, "reveal_manifest.json (该页 Mask 组)")
                break

    output = []
    for folder, suffix in (("videos", ".mp4"), ("presentations", ".pptx")):
        directory = safe_child(root, folder)
        if directory.is_dir():
            output.extend(_relative(root, path) for path in sorted(directory.glob(f"*{suffix}")) if path.is_file())

    version_inputs = {
        "slide_id": slide_id,
        "source": {name: sha256_file(slide / name) for name in source_names},
        "candidate": sha256_file(candidate),
        "geometry": {name: sha256_file(slide / name) for name in geometry_names},
        "mask_slide": next((entry for entry in (manifest.get("slides", []) if isinstance(manifest, dict) else [])
                            if isinstance(entry, dict) and str(entry.get("slide_id") or "") == slide_id), None),
    }
    return {
        "slide_id": slide_id,
        "version": sha256_json(version_inputs),
        "has_image": image.is_file(),
        "mask_groups": mask_groups,
        "archive": source,
        "review": geometry,
        "rebuild": generated,
        "retained_outputs": output,
    }
