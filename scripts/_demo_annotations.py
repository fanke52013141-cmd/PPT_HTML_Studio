# -*- coding: utf-8 -*-
"""演示数据准备:三条真实字框标注 → 启用 → 确认(触发墨迹时间轴构建)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

RUN = Path(sys.argv[1])

from annotation_contracts import DEFAULT_CANVAS  # noqa: E402
from annotation_service import (  # noqa: E402
    AnnotationService,
    AnnotationServiceDependencies,
)
from annotation_store import (  # noqa: E402
    AnnotationStore,
    AnnotationStoreDependencies,
)
from annotation_text_layout import candidate_tokens  # noqa: E402
from database import SessionLocal  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402
from project_runtime_service import reveal_lock_for  # noqa: E402

SPOKEN1 = "报名截止时间到9月30日18点,面向全体在校本科生与研究生。"
SPOKEN2 = "通过率预计提升23.5%,满意度达到96%。"


def _tokens_for(layout, phrase):
    cands = [c for c in candidate_tokens(layout) if c["granularity"] == "char"]
    stream = [(c["token_id"], c["text"]) for c in cands]
    joined = "".join(t for _, t in stream)
    idx = joined.find(phrase)
    assert idx >= 0, phrase
    return [stream[idx + i][0] for i in range(len(phrase))]


def _target(layout, phrase, style):
    token_ids = _tokens_for(layout, phrase)
    polygons = []
    for c in candidate_tokens(layout):
        if c["token_id"] in token_ids:
            polygons.append(c["polygon"])
    return {
        "kind": "text",
        "layout_revision": layout["layout_revision"],
        "token_ids": token_ids,
        "polygons": polygons,
        "quote": phrase,
        "granularity": "word",
        "mask_group_ids": [],
    }, token_ids


def _anchor(spoken, phrase):
    start = spoken.find(quote) if (quote := phrase) else -1
    assert start >= 0, quote
    return {
        "beat_id": "slide_001_beat_001" if spoken == SPOKEN1 else "slide_001_beat_002",
        "offset_unit": "unicode_codepoint",
        "range": [start, start + len(quote)],
        "quote": quote,
        "occurrence": 1,
        "context_before": spoken[max(0, start - 6):start],
        "context_after": spoken[start + len(quote):start + len(quote) + 6],
    }


def main() -> None:
    layout = json.loads(
        (RUN / "slides" / "slide_001" / "text_layout.json").read_text(encoding="utf-8")
    )

    # 重置页面,三条标注错峰起笔避免冲突
    (RUN / "slides" / "slide_001" / "annotations.json").unlink(missing_ok=True)
    (RUN / "slides" / "slide_001" / "annotation_timeline.json").unlink(missing_ok=True)
    (RUN / "planning" / "annotation_settings.json").unlink(missing_ok=True)
    (RUN / "slides" / "slide_001" / "annotation_ink").exists() and __import__("shutil").rmtree(
        RUN / "slides" / "slide_001" / "annotation_ink"
    )

    from annotation_text_layout import TextLayoutBuilder, TextLayoutDependencies

    store = AnnotationStore(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))
    layout_builder = TextLayoutBuilder(TextLayoutDependencies(
        write_json_atomic=write_json_atomic,
        read_json_file=lambda path: json.loads(Path(path).read_text(encoding="utf-8-sig")) if Path(path).exists() else None,
        ocr_config_provider=lambda: None,
    ))
    service = AnnotationService(
        AnnotationServiceDependencies(store=store, lock_for=reveal_lock_for, text_layout_builder=layout_builder)
    )
    db = SessionLocal()

    cases = [
        # (画面短语, 样式, 讲稿引用, 锚点语块, offset, seed)
        ("9月30日", "ellipse", "9月30日", SPOKEN1, 0.3, 1382),
        ("Online", "underline", "满意度", SPOKEN2, 0.3, 88),
        ("23.5", "highlighter", "23.5", SPOKEN2, 1.2, 512),
    ]
    revision = 0
    for i, (phrase, style, spoken_quote, spoken, offset, seed) in enumerate(cases):
        target, _ = _target(layout, phrase, style)
        item = {
            "target": target,
            "anchor": _anchor(spoken, spoken_quote),
            "style": {"type": style, "color": "#C43E1C", "opacity": 0.9, "width": 6, "padding": 10, "seed": seed},
            "timing": {
                "trigger_mode": "anchor_start", "offset_sec": offset,
                "draw_duration_sec": 0.8 if style == "ellipse" else 0.6,
                "hold_mode": "beat_end", "exit_duration_sec": 0.2,
            },
        }
        res = service.patch_slide(db, "annoe2e01", "slide_001", {
            "expected_revision": revision,
            "operations": [{"op": "add", "item": item}],
        })
        revision = res["revision"]
        print(f"added {style} '{phrase}' -> ann_00{i + 1} (rev {revision})")

    service.update_settings(db, "annoe2e01", {"expected_revision": 0, "enabled": True})
    confirm = service.confirm_slide(db, "annoe2e01", "slide_001", {"expected_revision": revision})
    print("confirm:", confirm["confirmed"], "confirmed | timeline:", confirm.get("timeline_built"),
          confirm.get("events", ""), confirm.get("timeline_error", ""))
    db.close()


if __name__ == "__main__":
    main()
