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
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from annotation_contracts import DEFAULT_CANVAS  # noqa: E402
from annotation_store import AnnotationStore, AnnotationStoreDependencies  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from project_storage import slide_dir as slide_dir_fn  # noqa: E402


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_canvas(run_dir: Path) -> tuple[int, int]:
    profile_path = run_dir / "planning" / "canvas_profile.json"
    try:
        profile = _read_json(profile_path)
        width, height = int(profile["width"]), int(profile["height"])
        if width > 0 and height > 0:
            return width, height
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        pass
    return DEFAULT_CANVAS


def build_slide_timeline(run_dir: Path, slide_id: str) -> tuple[dict, list]:
    from annotation_build import compile_slide
    store = AnnotationStore(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))
    canvas = _read_canvas(run_dir)
    page = store.read_page(str(run_dir), slide_id, canvas=canvas)
    if page is None:
        return {"events": [], "needs_review": []}, []
    if any(i.status.content not in ("confirmed", "disabled") for i in page.items):
        raise SystemExit("存在未确认条目，先完成确认门禁")
    return compile_slide(Path(slide_dir_fn(str(run_dir), slide_id)), page, canvas=canvas), []


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
