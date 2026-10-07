"""Snapshot & step PPTX export for the HTML backend (E03).

Renders a scene's final state (演示稿快照) or explicit step times (分步
快照) through the shared review bundle and assembles a 16:9 image-only
PPTX. Honest capability labels: pages are pictures — not per-object
editable, not native animation; the manifest records scene/theme hashes
and the page→time mapping. Subtitle inclusion is optional and defaults
to off for presentation snapshots (the narration stays in the video).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

from pptx import Presentation
from pptx.util import Emu

from runtime_support import run_subprocess_killable

SNAPSHOT_SCRIPT = Path("html_engine") / "tools" / "export-snapshots.cjs"


class HtmlSnapshotError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class HtmlSnapshotDependencies:
    repo_root: Path
    run_subprocess_bounded: Callable[..., subprocess.CompletedProcess] = (
        run_subprocess_killable
    )
    node_bin: str = "node"
    stage_timeout_sec: float = 300.0


def render_snapshots(
    scene: Dict[str, Any],
    times_ms: List[int],
    out_dir: Path,
    *,
    deps: HtmlSnapshotDependencies,
) -> List[Path]:
    """Render one PNG per time through the shared preview bundle."""
    if not times_ms:
        raise HtmlSnapshotError("快照时间列表为空")
    work = Path(out_dir)
    work.mkdir(parents=True, exist_ok=True)
    scene_path = work / "snapshot-scene.json"
    times_path = work / "snapshot-times.json"
    scene_path.write_text(json.dumps(scene, ensure_ascii=False), encoding="utf-8")
    times_path.write_text(json.dumps(times_ms), encoding="utf-8")
    result = deps.run_subprocess_bounded(
        [
            deps.node_bin,
            str(deps.repo_root / SNAPSHOT_SCRIPT),
            str(scene_path),
            str(times_path),
            str(work),
        ],
        cwd=str(deps.repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout_sec=deps.stage_timeout_sec,
    )
    if result.returncode != 0:
        raise HtmlSnapshotError(
            "快照渲染失败：" + (result.stderr or "")[-400:]
        )
    paths = [work / f"snapshot-{i:03d}.png" for i in range(len(times_ms))]
    for path in paths:
        if not path.is_file():
            raise HtmlSnapshotError("快照渲染输出缺失")
    return paths


def build_snapshot_pptx(
    pages: List[Dict[str, Any]],
    image_paths: List[Path],
    out_path: Path,
) -> Dict[str, Any]:
    """Assemble the 16:9 picture-only PPTX and its manifest.

    ``pages``: [{timeMs, label}] in order; the manifest states the
    capability boundary (image-only) and the page→time mapping.
    """
    if not pages or len(pages) != len(image_paths):
        raise HtmlSnapshotError("页与快照数量不一致")
    for path in image_paths:
        if not Path(path).is_file():
            raise HtmlSnapshotError(f"快照缺失：{path}")
    presentation = Presentation()
    # Exact 16:9 in EMU (Inches(13.333) rounds off by 305 EMU).
    presentation.slide_width = Emu(12192000)
    presentation.slide_height = Emu(6858000)
    blank = presentation.slide_layouts[6]
    for image_path in image_paths:
        slide = presentation.slides.add_slide(blank)
        slide.shapes.add_picture(
            str(image_path), 0, 0,
            width=presentation.slide_width,
            height=presentation.slide_height,
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(str(out_path))
    manifest = {
        "format": "hps.html.pptx_snapshot",
        "version": "0.1.0",
        "capability": "image_only_snapshot",
        "note": "图片式页面：不可逐对象编辑，不含原生动画；分步快照页与时间一一对应。",
        "page_count": len(pages),
        "pages": [
            {"page": index + 1, "timeMs": page["timeMs"], "label": page.get("label", "")}
            for index, page in enumerate(pages)
        ],
    }
    out_path.with_suffix(".pptx.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def snapshot_plan_for_scene(
    scene: Dict[str, Any], *, include_subtitles: bool = False
) -> List[Dict[str, Any]]:
    """Default page plan: one final-state page; 分步 adds one page per
    narration beat end. Subtitles are rendered by the scene itself only
    when explicitly requested (presentation snapshots default to no
    video subtitles)."""
    duration_ms = int(scene["durationMs"])
    pages = [{"timeMs": duration_ms, "label": "final"}]
    if include_subtitles is False:
        scene = {**scene, "beats": []}
    else:
        for beat in scene.get("beats", []):
            end_ms = int(beat["endMs"])
            # The last beat's end coincides with the final page: skip it.
            if end_ms >= duration_ms:
                continue
            pages.append({"timeMs": end_ms, "label": f"beat-{end_ms}"})
        pages.sort(key=lambda page: page["timeMs"])
    return pages
