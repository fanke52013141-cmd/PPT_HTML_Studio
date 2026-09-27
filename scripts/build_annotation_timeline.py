# -*- coding: utf-8 -*-
"""勾画标注时间轴构建 CLI(W5,可直接运行的薄入口)。

用法:
    python scripts/build_annotation_timeline.py --run-dir runs/<id> [--slide-id slide_001]

只调用服务层纯构建器(annotation_alignment / annotation_geometry /
annotation_timeline),**不在 import 时导入 server**;产物写入
``slides/<slide_id>/annotation_timeline.json``。已确认门禁由服务层负责,
本 CLI 用于评测复跑与离线验证:仅当页面全部启用条目已确认时才构建。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from annotation_alignment import read_beat_spans  # noqa: E402
from annotation_contracts import AnnotationPage  # noqa: E402
from annotation_geometry import FragmentInput, GeometryInputV2, build_strokes_v2  # noqa: E402
from annotation_store import AnnotationStore, AnnotationStoreDependencies  # noqa: E402
from annotation_target_resolver import resolve_phrase_target  # noqa: E402
from annotation_text_layout import TextLayoutBuilder, TextLayoutDependencies  # noqa: E402
from annotation_timeline import build_annotation_timeline  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from project_storage import slide_dir as slide_dir_fn  # noqa: E402


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read_layout(run_dir: Path, slide_id: str) -> dict | None:
    deps = TextLayoutDependencies(
        write_json_atomic=write_json_atomic,
        read_json_file=lambda path: json.loads(Path(path).read_text(encoding="utf-8-sig")) if Path(path).exists() else None,
        ocr_config_provider=lambda: None,
    )
    builder = TextLayoutBuilder(deps)
    try:
        return builder.load(str(run_dir), slide_id)
    except ValueError:
        return None


def _fragment_items(run_dir: Path, slide_id: str, page: AnnotationPage) -> list:
    """按条目解析片段(R2 短语合并/跨行拆分)并生成 v2 手写笔迹。"""
    layout = _read_layout(run_dir, slide_id)
    items: list = []
    for item in page.items:
        if item.status.content == "disabled":
            continue
        if item.target.kind == "text" and item.target.token_ids:
            if layout is None:
                raise SystemExit(f"页面 {slide_id} 缺少 text_layout.json;先运行文字识别")
            resolution = resolve_phrase_target(
                layout=layout,
                token_ids=list(item.target.token_ids),
                expected_layout_revision=item.target.layout_revision,
            )
            fragments = [
                FragmentInput(
                    polygons=tuple(tuple((p[0], p[1]) for p in poly) for poly in fragment["polygons"]),
                    style_type=item.style.type,
                    width=item.style.width,
                    padding=item.style.padding,
                    seed=item.style.seed,
                )
                for fragment in resolution["fragments"]
            ]
        else:
            fragments = [
                FragmentInput(
                    polygons=(tuple((p[0], p[1]) for p in poly),),
                    style_type=item.style.type,
                    width=item.style.width,
                    padding=item.style.padding,
                    seed=item.style.seed,
                )
                for poly in item.target.polygons
            ]
        strokes = build_strokes_v2(GeometryInputV2(fragments=tuple(fragments)))
        ink_dir_root = Path(slide_dir_fn(str(run_dir), slide_id)) / "annotation_ink" / item.annotation_id
        strokes = _attach_ink(strokes, ink_dir_root, item, annotation_id=item.annotation_id)
        items.append(_ItemWithStrokes(item, strokes))
    return items


def _attach_ink(strokes, ink_dir_root, item, *, annotation_id):
    """为每笔渲染栅格墨迹帧(位图,视频不再走 SVG 路径)。"""
    from annotation_ink import InkRequest, render_and_write

    attached = []
    for index, stroke in enumerate(strokes):
        brush = stroke.get("brush_height")
        request = InkRequest(
            points=tuple(map(tuple, stroke["points"])),
            width_profile=tuple(stroke["width_profile"]),
            canvas=(1920, 1080),
            color=(196, 62, 28),
            base_width=float(brush) if brush else 5.0,
            opacity=item.style.opacity,
            seed=item.style.seed + index * 733,
            closed=stroke.get("closed", False),
        )
        meta = render_and_write(
            request,
            ink_dir_root / f"stroke_{index}",
            draw_duration_sec=item.timing.draw_duration_sec,
        )
        attached.append({**stroke, "ink": meta})
    return attached


def build_slide_timeline(run_dir: Path, slide_id: str) -> tuple[dict, list]:
    store = AnnotationStore(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))
    page = store.read_page(str(run_dir), slide_id, canvas=(1920, 1080))
    if page is None or not page.items:
        raise SystemExit(f"页面 {slide_id} 没有勾画条目;时间轴未构建")

    settings = store.read_settings(str(run_dir))
    if settings is None or not settings.enabled:
        raise SystemExit("项目未启用勾画(enabled=false);时间轴未构建")

    unconfirmed = [i.annotation_id for i in page.items if i.status.content not in ("confirmed", "disabled")]
    if unconfirmed:
        raise SystemExit(f"存在未确认条目:{', '.join(unconfirmed)};先完成确认门禁")

    slide_dir = Path(slide_dir_fn(str(run_dir), slide_id))
    audio_timeline = _read_json(slide_dir / "audio_timeline.json")
    spans, _duration = read_beat_spans(audio_timeline)
    beat_times = {span.beat_id: (span.start_sec, span.end_sec) for span in spans}
    slide_duration = float(audio_timeline.get("audio_content_duration_sec") or audio_timeline.get("duration_sec") or 0.0)

    events_items = _fragment_items(run_dir, slide_id, page)

    payload, issues = build_annotation_timeline(
        slide_id=slide_id,
        items=events_items,
        beat_times=beat_times,
        slide_duration=slide_duration,
        image_hash=_sha256(slide_dir / "visual_draft.png"),
        narration_hash=_sha256(slide_dir / "narration_beats.json"),
        audio_hash=_sha256(slide_dir / "voice.mp3"),
        confirmed_input_hashes={},
    )
    return payload, issues


class _ItemWithStrokes:
    """轻量包装:时间轴构建器读取 item.strokes 之外的全部原字段。"""

    def __init__(self, item, strokes):
        self._item = item
        self.strokes = tuple(strokes)

    def __getattr__(self, name):
        return getattr(self._item, name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build annotation_timeline.json for confirmed annotation pages.")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--slide-id", action="append", required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()

    exit_code = 0
    for slide_id in args.slide_id:
        payload, issues = build_slide_timeline(run_dir, slide_id)
        out = Path(slide_dir_fn(str(run_dir), slide_id)) / "annotation_timeline.json"
        write_json_atomic(out, payload)
        print(f"[ok] {slide_id}: {len(payload['events'])} events, needs_review={len(issues)} -> {out.name}")
        if issues:
            exit_code = 2
            for issue in issues:
                print(f"     needs_review: {issue['annotation_id']} ({issue['reason']})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
