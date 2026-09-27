# -*- coding: utf-8 -*-
"""构建演示 props 并渲染 MP4(走生产 props 构建器 + 生产 Remotion 组合)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

RUN = Path(sys.argv[1])
OUT_MP4 = Path(sys.argv[2])

from build_remotion_props import (  # noqa: E402
    DEFAULT_REMOTION_PUBLIC_DIR,
    RuntimeAssetStore,
    build_props,
)
from pipeline_lifecycle import write_json_atomic  # noqa: E402

props = build_props(
    RUN.resolve(),
    REPO,
    RuntimeAssetStore(REPO / DEFAULT_REMOTION_PUBLIC_DIR, RUN.name),
    fps=30,
    width=1920,
    height=1080,
)
props_path = RUN / "remotion_props.json"
write_json_atomic(props_path, props)

timeline = props["slides"][0].get("annotation_timeline") or {}
print("props written:", props_path)
print("events:", len(timeline.get("events", [])))
for event in timeline.get("events", []):
    stroke = (event.get("strokes") or [{}])[0]
    ink = stroke.get("ink") or {}
    print(
        " ", event["annotation_id"], event["style"]["type"],
        "ink_frames=", len(ink.get("frames", [])),
    )
print("total_duration_sec:", props["total_duration_sec"])
