# -*- coding: utf-8 -*-
"""生成新旧笔迹 A/B 对比页(R2 验收)。

数据源:隔离 run 中真实百度 OCR 的字框(slides/slide_001/text_layout.json)。
- 旧版:第一轮的规则椭圆公式(整体缩放,无局部形态);
- 新版:annotation_geometry v2 手写模板 + 共享采样器渲染的轮廓。

产物输出到 docs/annotation-validation/round2-samples/,用浏览器实际打开
截图作为验收证据;HTML 仅引用 production 的 annotation_playback.js 副本,
保证"看到的就是导出的"。
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from annotation_geometry import FragmentInput, GeometryInputV2, build_strokes_v2  # noqa: E402
from annotation_target_resolver import resolve_phrase_target  # noqa: E402

RUN_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT_DIR = REPO_ROOT / "docs" / "annotation-validation" / "round2-samples"
SAMPLE_IMAGE = REPO_ROOT / "checks" / "fixtures" / "annotations" / "sample_slide.png"


def _load_layout() -> dict:
    layout_path = RUN_DIR / "slides" / "slide_001" / "text_layout.json" if RUN_DIR else None
    if layout_path and layout_path.exists():
        return json.loads(layout_path.read_text(encoding="utf-8-sig"))
    raise SystemExit(f"缺少 text_layout.json({layout_path});先在隔离服务上运行 detect_text")


def _find_tokens(layout: dict, phrase: str) -> list[str]:
    """按文本流定位短语 token(含跨词)。"""
    from annotation_text_layout import candidate_tokens

    candidates = candidate_tokens(layout)
    stream = [(c["token_id"], c["text"]) for c in candidates if c["granularity"] == "char"]
    joined = "".join(text for _, text in stream)
    start = joined.find(phrase)
    if start < 0:
        return []
    return [stream[start + i][0] for i in range(len(phrase))]


def _old_ellipse(points_box, pad=8.0, steps=72):
    """第一轮的规则椭圆(整体缩放,无局部形态)——作为 A/B 的旧版基准。"""
    xs = [p[0] for p in points_box]
    ys = [p[1] for p in points_box]
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    cx, cy = (left + right) / 2, (top + bottom) / 2
    rx, ry = (right - left) / 2 + pad, (bottom - top) / 2 + pad
    return [
        (round(cx + math.cos(i / steps * math.tau) * rx, 2),
         round(cy + math.sin(i / steps * math.tau) * ry, 2))
        for i in range(steps + 1)
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    layout = _load_layout()
    targets = {
        "日期": "月30日",
        "百分比": "23.5",
    }
    cases = []
    for label, phrase in targets.items():
        token_ids = _find_tokens(layout, phrase)
        if not token_ids:
            print(f"skip {label}: 未找到 {phrase}")
            continue
        resolution = resolve_phrase_target(layout=layout, token_ids=token_ids)
        fragment = resolution["fragments"][0]
        polygons = tuple(tuple((p[0], p[1]) for p in poly) for poly in fragment["polygons"])
        box = [p for poly in fragment["polygons"] for p in poly]
        # 新版:三个种子(换一种笔迹)
        variants = []
        for seed in (1382, 9021, 557):
            strokes = build_strokes_v2(GeometryInputV2(fragments=(
                FragmentInput(polygons=polygons, style_type="ellipse", width=5, padding=8, seed=seed),
            )))
            variants.append({"seed": seed, "stroke": strokes[0]})
        cases.append({
            "label": label,
            "phrase": phrase,
            "box": [min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box)],
            "old": _old_ellipse(box),
            "new": variants,
            "token_count": len(token_ids),
        })

    # 横线对比:长句 "Online registration opens on Sep 1st" 所在行
    underline_tokens = _find_tokens(layout, "Online")
    if underline_tokens:
        resolution = resolve_phrase_target(layout=layout, token_ids=underline_tokens)
        fragment = resolution["fragments"][0]
        polygons = tuple(tuple((p[0], p[1]) for p in poly) for poly in fragment["polygons"])
        box = [p for poly in fragment["polygons"] for p in poly]
        new_stroke = build_strokes_v2(GeometryInputV2(fragments=(
            FragmentInput(polygons=polygons, style_type="underline", width=4, padding=6, seed=88),
        )))[0]
        cases.append({
            "label": "横线",
            "phrase": "Online",
            "box": [min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box)],
            "old": None,
            "new": [{"seed": 88, "stroke": new_stroke}],
            "token_count": len(underline_tokens),
        })

    (OUT_DIR / "ab-strokes-data.js").write_text(
        "window.AB_DATA = " + json.dumps(cases, ensure_ascii=False) + ";",
        encoding="utf-8",
    )
    shutil.copy(REPO_ROOT / "static" / "annotation_playback.js", OUT_DIR / "annotation_playback.js")
    shutil.copy(REPO_ROOT / "static" / "annotations_core.js", OUT_DIR / "annotations_core.js")
    html = _build_html()
    (OUT_DIR / "ab-compare.html").write_text(html, encoding="utf-8")
    shutil.copy(SAMPLE_IMAGE, OUT_DIR / "sample_slide.png")
    print(f"A/B page written to {OUT_DIR / 'ab-compare.html'}")
    for case in cases:
        print(f"  case: {case['label']} ({case['phrase']}) tokens={case['token_count']}")


def _build_html() -> str:
    return """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>勾画笔迹 A/B 对比(R2)</title>
<style>
  body { font-family: "Microsoft YaHei", sans-serif; background: #f3f4f6; margin: 0; padding: 16px; }
  h1 { font-size: 20px; } h2 { font-size: 15px; margin: 8px 0 4px; }
  .card { background: #fff; border-radius: 12px; padding: 12px; margin-bottom: 16px; }
  .row { display: flex; gap: 12px; flex-wrap: wrap; }
  .panel { flex: 1 1 320px; }
  .frame { position: relative; width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
  .frame img, .frame svg { display: block; width: 100%; height: auto; }
  .frame svg { position: absolute; inset: 0; }
  .tag { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; margin-bottom: 4px; }
  .old { background: #fee2e2; color: #991b1b; }
  .new { background: #dcfce7; color: #166534; }
</style>
</head>
<body>
<h1>勾画笔迹 A/B 对比 — 冻结样本真实 OCR 字框</h1>
<div id="root"></div>
<script src="annotation_playback.js"></script>
<script src="ab-strokes-data.js"></script>
<script>
function outlineD(stroke, progress) {
  // 编辑态 = 绘制完成:progress=1;经由与导出完全相同的采样器
  const ev = { annotation_id: 'x', start_sec: 0, draw_end_sec: 1, hold_end_sec: 1, exit_end_sec: 1,
               style: { color: '#F46A38', opacity: 0.85, width: 5 }, strokes: [stroke] };
  const shapes = AnnotationsPlayback.renderScene([ev], 0.5, 30);
  return shapes.length ? shapes[0] : null;
}
function midD(stroke) {
  const ev = { annotation_id: 'x', start_sec: 0, draw_end_sec: 1, hold_end_sec: 1, exit_end_sec: 1,
               style: { color: '#F46A38', opacity: 0.85, width: 5 }, strokes: [stroke] };
  // 半程:用 strokeProgress 语义直接取局部进度 0.55
  const shapes = AnnotationsPlayback.renderScene(
    [{ ...ev, start_sec: 0, draw_end_sec: 0.55, hold_end_sec: 0.55, exit_end_sec: 0.55 }], 0.5, 30);
  return shapes.length ? shapes[0] : null;
}
function svgFor(view, items) {
  // 画布 1920x1080,按面板裁剪目标附近区域
  const [cx, cy] = view.center, half = view.half;
  const vb = `${cx - half} ${cy - half * 9 / 16} ${half * 2} ${half * 2 * 9 / 16}`;
  return `<svg viewBox="${vb}" xmlns="http://www.w3.org/2000/svg">
    ${items.join('\\n')}
  </svg>`;
}
const root = document.getElementById('root');
for (const c of AB_DATA) {
  const [x1, y1, x2, y2] = c.box;
  const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
  const half = Math.max(320, (x2 - x1) * 1.1);
  const view = { center: [cx, cy], half };
  const sections = [];

  // 旧版规则椭圆
  if (c.old) {
    const d = 'M ' + c.old.map(p => p.join(' ')).join(' L ');
    sections.push(['旧版:规则椭圆(整体缩放)', 'old', `<path d="${d}" fill="none" stroke="#F46A38" stroke-width="5" stroke-linecap="round"/>`]);
  }
  // 新版:完整 + 半程 + 换笔迹
  c.new.forEach((variant, index) => {
    const full = outlineD(variant.stroke, 1);
    const mid = midD(variant.stroke);
    const label = index === 0 ? '新版:手写模板 + 笔宽曲线(完成)' : `新版:换一种笔迹(seed ${variant.seed})`;
    sections.push([label, 'new', full ? `<path d="${full.d}" fill="${full.closed ? '#F46A38' : 'none'}" fill-opacity="${full.closed ? 0.06 : 0}" stroke="#F46A38" stroke-width="2.6" stroke-linejoin="round"/>` : '']);
    if (index === 0 && mid) {
      sections.push(['新版:行笔半程(笔尖推进)', 'new', `<path d="${mid.d}" fill="${mid.closed ? '#F46A38' : 'none'}" fill-opacity="${mid.closed ? 0.06 : 0}" stroke="#F46A38" stroke-width="2.6" stroke-linejoin="round"/>`]);
    }
  });

  const wrap = document.createElement('div');
  wrap.className = 'card';
  wrap.innerHTML = `<h2>${c.label} — "${c.phrase}"(${c.token_count} 个字框)</h2>
    <div class="row">` +
    sections.map(([tag, cls, content]) =>
      `<div class="panel"><span class="tag ${cls}">${tag}</span>
       <div class="frame"><img src="sample_slide.png"><svg viewBox="0 0 1920 1080" style="position:absolute;inset:0;width:100%;height:100%">
         <g>${content}</g></svg></div></div>`).join('') +
    `</div>`;
  root.appendChild(wrap);
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
