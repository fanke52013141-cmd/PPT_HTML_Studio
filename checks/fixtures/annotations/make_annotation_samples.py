# -*- coding: utf-8 -*-
"""生成勾画标注模块 OCR 评测的冻结合成样本。

确定性绘制:固定文本、固定字体、固定坐标,任何机器重跑得到字节一致的图。
真值文件记录每行文本的精确绘制包围盒,供后续自动选点/定位评测使用;
评测输入端不得读取真值文件。

字体依赖 Windows 自带的 msyh.ttc 与 arial.ttf;生成产物已提交到本目录,
测试无需重新生成。重新生成命令:

    python checks/fixtures/annotations/make_annotation_samples.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 1920, 1080
HERE = Path(__file__).resolve().parent

# (文本, 字体, 左上角坐标, 颜色)
STANDARD_LINES = [
    ("2026年秋季课程报名说明", ("msyh", 64), (120, 100), "#1F2937"),
    ("报名截止时间:9月30日 18:00", ("msyh", 40), (120, 300), "#111827"),
    ("面向对象:全体在校本科生与研究生", ("msyh", 40), (120, 380), "#111827"),
    ("通过率预计提升 23.5%,满意度 96%", ("msyh", 40), (120, 460), "#111827"),
    ("Online registration opens on Sep 1st", ("arial", 36), (120, 560), "#374151"),
    ("Registration Fee: 250 CNY per student", ("arial", 36), (120, 640), "#374151"),
    ("扫码进入报名系统", ("msyh", 40), (150, 790), "#B91C1C"),
]

# 数字/日期/百分比密度样本:勾画首期最典型的圈画目标
NUMBERS_LINES = [
    ("Q3 营收 1,284.6 万元", ("msyh", 44), (140, 120), "#111827"),
    ("同比增长 18.7%", ("msyh", 44), (140, 240), "#111827"),
    ("截止 2026-12-31 23:59:59", ("arial", 38), (140, 360), "#1F2937"),
    ("ROI = 312%,回收周期 9 个月", ("msyh", 44), (140, 480), "#111827"),
    ("预算上限 RMB 88,000(含税 6%)", ("msyh", 44), (140, 600), "#111827"),
    ("Version 2.0.1 build 20260927", ("arial", 30), (140, 720), "#6B7280"),
]

FONT_PATHS = {
    "msyh": "C:/Windows/Fonts/msyh.ttc",
    "arial": "C:/Windows/Fonts/arial.ttf",
}


def _font(spec):
    name, size = spec
    return ImageFont.truetype(FONT_PATHS[name], size)


def build_sample(lines, out_png, truth_key):
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    truth = []
    for text, spec, (x, y), color in lines:
        font = _font(spec)
        box = draw.textbbox((x, y), text, font=font)
        draw.text((x, y), text, font=font, fill=color)
        truth.append({
            "text": text,
            "box": [box[0], box[1], box[2], box[3]],  # left, top, right, bottom
            "font": spec[0],
            "font_size": spec[1],
        })
    img.save(out_png)
    return truth


def main() -> None:
    samples = {
        "sample_slide.png": (STANDARD_LINES, "standard"),
        "sample_numbers.png": (NUMBERS_LINES, "numbers"),
    }
    truth_doc = {"canvas": [CANVAS_W, CANVAS_H], "samples": {}}
    for png_name, (lines, kind) in samples.items():
        out = HERE / png_name
        truth = build_sample(lines, out, kind)
        truth_doc["samples"][png_name] = truth
        print(f"saved {out.name}: {len(truth)} truth lines")
    (HERE / "samples_truth.json").write_text(
        json.dumps(truth_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("saved samples_truth.json")


if __name__ == "__main__":
    main()
