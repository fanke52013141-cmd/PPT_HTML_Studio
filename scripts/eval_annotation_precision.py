# -*- coding: utf-8 -*-
"""勾画精准度三轮对比评测(R3)。

在冻结样本(真实百度 OCR 字框 + 真实绘制背景)上,对同一批目标分别按
三轮实现渲染并计算栅格精准度指标:

- V0 第一轮:每个字符框一个规则椭圆(第一轮 planner/geometry 的真实行为);
- V1 第二轮:短语合并 + 手写模板轮廓(SVG 观感,均匀线宽);
- V2 第三轮:短语合并 + 手写模板 + 压力笔宽 + 墨迹纹理(栅格位图)。

指标:
- enclosure_rate  包围率(目标框周界被笔迹包住的比例,≥0.9 为完整包围)
- intrusion_rate  压字率(笔迹墨迹落入目标文字框内,越低越好)
- neighbor_rate   误圈邻词率(笔迹落入同行其他文字框内,应≈0)
- centroid_offset 偏心距(px,越低越好)

用法:python scripts/eval_annotation_precision.py
输出:docs/annotation-validation/round3-samples/(JSON + HTML + PNG)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from PIL import Image

from annotation_geometry import FragmentInput, GeometryInputV2, build_strokes_v2  # noqa: E402
from annotation_ink import InkRequest, render_stroke_rgba, precision_metrics  # noqa: E402
from annotation_target_resolver import compute_side_pads, resolve_phrase_target  # noqa: E402
from annotation_text_layout import candidate_tokens  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "checks" / "fixtures" / "annotations"
OUT_DIR = REPO_ROOT / "docs" / "annotation-validation" / "round3-samples"
CANVAS = (1920, 1080)


def _phrase_tokens(layout: dict, phrase: str) -> list[str]:
    cands = [c for c in candidate_tokens(layout) if c["granularity"] == "char"]
    stream = [(c["token_id"], c["text"]) for c in cands]
    joined = "".join(t for _, t in stream)
    idx = joined.find(phrase)
    if idx < 0:
        return []
    return [stream[idx + i][0] for i in range(len(phrase))]


def _v1_ellipse(polygons, pad=8.0, steps=72):
    """第一轮规则椭圆公式(逐字符框一个椭圆)。"""
    ellipses = []
    for poly in polygons:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        rx, ry = (max(xs) - min(xs)) / 2 + pad, (max(ys) - min(ys)) / 2 + pad
        ellipses.append([
            (cx + math.cos(i / steps * math.tau) * rx, cy + math.sin(i / steps * math.tau) * ry)
            for i in range(steps + 1)
        ])
    return ellipses


def _boxes_of(polygons):
    boxes = []
    for poly in polygons:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def _raster_polyline(points, width, canvas, texture_seed=None):
    """把折线以固定宽度栅格化(第一/二轮观感的公平渲染载体)。"""
    request = InkRequest(
        points=tuple(map(tuple, points)),
        width_profile=tuple([1.0] * len(points)),
        canvas=canvas,
        base_width=width,
        texture=texture_seed is not None,
        seed=texture_seed or 1,
    )
    return render_stroke_rgba(request)


def _raster_ellipse(points, width, canvas):
    return _raster_polyline(points, width, canvas, texture_seed=None)


def _build_cases(layout: dict) -> list[dict]:
    cases = []
    for label, phrase, style in (
        ("日期圈注", "9月30日", "ellipse"),
        ("百分比圈注", "23.5", "ellipse"),
        ("英文横线", "Online", "underline"),
    ):
        token_ids = _phrase_tokens(layout, phrase)
        if not token_ids:
            continue
        resolution = resolve_phrase_target(layout=layout, token_ids=token_ids)
        fragment = resolution["fragments"][0]
        polygons = tuple(tuple((p[0], p[1]) for p in poly) for poly in fragment["polygons"])
        # 邻词:同行未选中的字符框
        selected = set(fragment["token_ids"])
        neighbors = []
        for cand in candidate_tokens(layout):
            if cand["granularity"] != "char" or cand["token_id"] in selected:
                continue
            if cand.get("line_id") == fragment["line_id"]:
                xs = [p[0] for p in cand["polygon"]]
                ys = [p[1] for p in cand["polygon"]]
                neighbors.append((min(xs), min(ys), max(xs), max(ys)))
        cases.append({
            "label": label,
            "phrase": phrase,
            "style": style,
            "polygons": polygons,
            "targets": _boxes_of(polygons),
            "neighbors": neighbors,
            "token_count": len(token_ids),
            "line_id": fragment["line_id"],
            "selected": set(fragment["token_ids"]),
        })
    return cases


def _render_variants(case: dict, layout: dict) -> dict:
    polygons = case["polygons"]

    # 邻词感知留白(方案 4.3):按同行邻词间隙收紧左右留白
    frag_dict = {"line_id": case["line_id"], "polygons": [list(map(list, poly)) for poly in polygons]}
    pad_left, pad_right = compute_side_pads(layout, frag_dict, case["selected"])
    if case["style"] == "underline":
        pad_left = min(pad_left, 4.0) if pad_left is not None else None
        pad_right = min(pad_right, 4.0) if pad_right is not None else None

    fragment = FragmentInput(
        polygons=polygons, style_type=case["style"], width=5, padding=8, seed=1382,
        pad_left=pad_left, pad_right=pad_right,
    )
    v2_strokes = build_strokes_v2(GeometryInputV2(fragments=(fragment,)))

    # V0 第一轮(真实行为):逐字符独立图形(v1 geometry 对每个 polygon 独立出笔)
    v0 = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    for poly in polygons:
        poly_list = [list(map(list, poly))]
        if case["style"] == "ellipse":
            for ellipse in _v1_ellipse(poly_list):
                v0.alpha_composite(_raster_ellipse(ellipse, 5, CANVAS))
        else:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            y = max(ys) + 8 + 2.5
            v0.alpha_composite(_raster_polyline([(min(xs) - 4, y), (max(xs) + 4, y)], 5, CANVAS))
    # V1 第二轮:合并短语 + 手写轮廓,均匀线宽(矢量观感)
    v1 = _raster_polyline(v2_strokes[0]["points"], 5, CANVAS, texture_seed=None)
    # V2 第三轮:完整墨迹(压力 + 纹理 + 洇墨)
    v2 = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    for stroke in v2_strokes:
        request = InkRequest(
            points=tuple(map(tuple, stroke["points"])),
            width_profile=tuple(stroke["width_profile"]),
            canvas=CANVAS,
            base_width=5.0,
            seed=1382,
            closed=stroke.get("closed", False),
        )
        v2.alpha_composite(render_stroke_rgba(request))
    return {"V0": v0, "V1": v1, "V2": v2}


def _metrics_for_style(case: dict, image: Image.Image) -> dict:
    """样式感知指标:椭圆测包围;横线测贴基线 + 横向覆盖 + 压字。"""
    if case["style"] == "ellipse":
        return precision_metrics(image, target_boxes=case["targets"], neighbor_boxes=case["neighbors"])
    import numpy

    alpha = image.split()[-1]
    mask = numpy.array(alpha) > 40
    total = int(mask.sum())
    ys, xs = numpy.nonzero(mask)
    x0 = min(b[0] for b in case["targets"])
    x1 = max(b[2] for b in case["targets"])
    bottom = max(b[3] for b in case["targets"])
    covered = 0
    steps = 60
    for i in range(steps):
        px = int(x0 + (x1 - x0) * i / (steps - 1))
        if total and mask[:, max(0, px - 2):px + 3].any():
            covered += 1
    coverage_x = covered / steps if total else 0.0
    baseline_ok = float(((ys >= bottom - 2) & (ys <= bottom + 16)).sum()) / total if total else 0.0
    intr_mask = numpy.zeros_like(mask)
    for bx0, by0, bx1, by1 in case["targets"]:
        intr_mask[int(by0):int(by1), int(bx0):int(bx1)] = True
    intrusion = int((mask & intr_mask).sum()) / total if total else 0.0
    nb = 0.0
    if total:
        nbm = numpy.zeros_like(mask)
        for bx0, by0, bx1, by1 in case["neighbors"]:
            nbm[int(by0):int(by1), int(bx0):int(bx1)] = True
        nb = int((mask & nbm).sum()) / total
    return {
        "coverage_x": round(coverage_x, 3),
        "baseline_rate": round(baseline_ok, 3),
        "intrusion_rate": round(intrusion, 4),
        "neighbor_rate": round(nb, 4),
        "ink_pixels": total,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    layout = json.loads((FIXTURE_DIR / "sample_slide_layout.json").read_text(encoding="utf-8"))
    background = Image.open(FIXTURE_DIR / "sample_slide.png").convert("RGBA")
    cases = _build_cases(layout)

    report = {"ink_version": "annotation_ink_v1", "cases": []}
    for index, case in enumerate(cases):
        variants = _render_variants(case, layout)
        crop = _crop_for(case["targets"])
        entry = {
            "label": case["label"],
            "phrase": case["phrase"],
            "token_count": case["token_count"],
            "style": case["style"],
            "variants": {},
        }
        for name, image in variants.items():
            metrics = _metrics_for_style(case, image)
            entry["variants"][name] = metrics
            # 合成裁剪图:背景 + 墨迹
            region = background.crop(crop)
            overlay = image.crop(crop)
            region.alpha_composite(overlay)
            region.convert("RGB").save(OUT_DIR / f"case{index + 1}-{name}.png")
        entry["crop"] = list(crop)
        report["cases"].append(entry)
        def fmt(m):
            if "enclosure_rate" in m:
                return (
                    f"enc={m['enclosure_rate']:.2f} intr={m['intrusion_rate']:.3f}"
                    f" nb={m['neighbor_rate']:.3f} off={m['centroid_offset_px']:.1f}"
                )
            return (
                f"cov={m['coverage_x']:.2f} base={m['baseline_rate']:.2f}"
                f" intr={m['intrusion_rate']:.3f} nb={m['neighbor_rate']:.3f}"
            )

        print(f"[{case['label']}] " + " | ".join(
            f"{name}: {fmt(m)}" for name, m in entry["variants"].items()
        ))

    (OUT_DIR / "precision-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("saved:", OUT_DIR / "precision-report.json")
    return 0


def _crop_for(targets):
    xs = []
    ys = []
    for x0, y0, x1, y1 in targets:
        xs.extend([x0, x1])
        ys.extend([y0, y1])
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    half = max(300, (max(xs) - min(xs)) * 1.25)
    vh = half * 2 * 9 / 16
    return (
        max(0, int(cx - half)),
        max(0, int(cy - vh / 2)),
        min(CANVAS[0], int(cx + half)),
        min(CANVAS[1], int(cy + vh / 2)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
