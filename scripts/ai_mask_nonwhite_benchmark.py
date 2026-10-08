"""Non-white background AI Mask fixtures and scoring; detector-only, offline.

The frozen white-background validation set (docs/ai-mask-optimization/validation)
assumes a pure #FFFFFF canvas, which is exactly the assumption this benchmark
removes.  Every case here draws the same kind of header/cards content over a
configured non-white background color, and ground truth is defined as "pixels
that differ from that background" instead of "pixels that differ from white".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SIZE = (1920, 1080)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def font(size):
    for name in ("C:/Windows/Fonts/msyh.ttc", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    raise RuntimeError("Install Microsoft YaHei or DejaVuSans before generating fixtures")


CASES = [
    # case_id, description, background, groups, gap
    ("12_beige_cards", "米色底上的三张彩色卡片", (242, 236, 227), 3, 48),
    ("13_gray_dense", "浅灰底上的 15 张小卡片", (233, 233, 233), 15, 12),
    ("14_tint_pale", "淡蓝底上的浅色卡片", (234, 241, 247), 3, 48),
]


def _draw_case(case_id, bg, count, gap):
    image = Image.new("RGB", SIZE, bg)
    labels = np.zeros((SIZE[1], SIZE[0]), np.uint16)
    groups = []

    def add(gid, name, draw_fn):
        layer = Image.new("RGB", SIZE, bg)
        draw_fn(ImageDraw.Draw(layer))
        pixels = np.asarray(layer)
        mask = np.any(pixels != np.asarray(bg, np.uint8), axis=2)
        if np.any(mask & (labels != 0)):
            raise ValueError(f"Overlapping fixture ownership in {case_id}/{gid}")
        labels[mask] = gid
        image.paste(layer, (0, 0), Image.fromarray(mask.astype("uint8") * 255))
        groups.append({"id": f"group_{gid:03d}", "narration": name})

    def header(d):
        d.text((90, 70), "数据如何变成决策", font=font(54), fill="#26334a")
    add(1, "标题与页面框架先出现", header)

    cols = 5 if count == 15 else 3
    rows = 3 if count == 15 else 1
    width = (1720 - (cols - 1) * gap) // cols
    height = 175 if rows == 3 else 430
    for i in range(count):
        x = 100 + (i % cols) * (width + gap)
        y = 270 + (i // cols) * 205
        name = f"步骤 {i + 1}：" + ("采集数据", "清洗数据", "分析结果")[i % 3]

        def card(d, x=x, y=y, i=i, name=name):
            pale = case_id == "14_tint_pale"
            fill = "#F7FAFC" if pale else ("#e5f3ff", "#fff0df", "#e8f5e9")[i % 3]
            d.rounded_rectangle((x, y, x + width - 1, y + height), 22,
                                fill=fill, outline="#668099", width=2)
            d.text((x + 20, y + 20), name, font=font(24 if rows == 3 else 32), fill="#253047")
            d.text((x + 20, y + 65), "输入 → 处理 → 输出", font=font(21 if rows == 3 else 28), fill="#435467")
            if rows == 1:
                d.ellipse((x + 45, y + 140, x + 145, y + 240), outline="#5382a1", width=5)
                d.rectangle((x + 175, y + 175, x + 255, y + 255), fill="#efbe73")
                d.line((x + 40, y + 315, x + width - 40, y + 315), fill="#768b99", width=2)
                d.text((x + 20, y + 340), "完整区域同步出现", font=font(27), fill="#435467")
        add(i + 2, name, card)
    return image, labels, groups


def generate(root):
    if (root / "cases").exists():
        raise ValueError("cases already exists; choose a new output directory to preserve fixtures")
    for case_id, title, bg, count, gap in CASES:
        folder = root / "cases" / case_id
        folder.mkdir(parents=True)
        image, labels, groups = _draw_case(case_id, bg, count, gap)
        image.save(folder / "image.png")
        Image.fromarray(labels).save(folder / "labels.png")
        for gid in range(1, len(groups) + 1):
            Image.fromarray((labels == gid).astype("uint8") * 255).save(folder / f"group_{gid:03d}.png")
        write_json(folder / "groups.json", {
            "case_id": case_id, "description": title, "background": list(bg), "groups": groups,
            "policy": "Visible pixels differing from the configured background only.",
            "image_sha256": hashlib.sha256((folder / "image.png").read_bytes()).hexdigest()})
    write_json(root / "dataset.json", {"version": 1, "size": SIZE, "cases": [c[0] for c in CASES],
                 "font": "Microsoft YaHei preferred; keep delivered PNGs fixed across machines"})
    print(f"generated {len(CASES)} cases under {root / 'cases'}")


def _bg_of(case):
    return np.asarray(json.loads((case / "groups.json").read_text(encoding="utf-8"))["background"], np.uint8)


def score_case(case, prediction):
    metadata = json.loads((case / "groups.json").read_text(encoding="utf-8"))
    if hashlib.sha256((case / "image.png").read_bytes()).hexdigest() != metadata["image_sha256"]:
        raise ValueError(f"Fixture image changed: {case}")
    bg = _bg_of(case)
    gt = np.asarray(Image.open(case / "labels.png"))
    source = np.asarray(Image.open(case / "image.png").convert("RGB"))
    foreground = gt != 0
    if not np.array_equal(foreground, np.any(source != bg, axis=2)):
        raise ValueError("Ground-truth foreground does not match source pixels")
    groups = metadata["groups"]
    masks = []
    for group in groups:
        path = prediction / (group["id"] + ".png")
        if path.exists():
            with Image.open(path) as im:
                if im.size != SIZE or im.mode != "L":
                    raise ValueError(f"Expected 1920x1080 grayscale binary mask: {path}")
                masks.append(np.asarray(im) != 0)
        else:
            masks.append(np.zeros((SIZE[1], SIZE[0]), bool))
    counts = np.zeros(gt.shape, np.uint16)
    rows = []
    for index, (group, mask) in enumerate(zip(groups, masks), 1):
        truth = gt == index
        selected = mask & foreground
        tp = int(np.count_nonzero(selected & truth))
        fp = int(np.count_nonzero(selected & ~truth))
        fn = int(np.count_nonzero(truth & ~selected))
        rows.append({"id": group["id"], "iou": tp / max(1, tp + fp + fn),
                     "precision": tp / max(1, tp + fp), "recall": tp / max(1, tp + fn)})
        counts += mask.astype(np.uint16)
    missing = foreground & (counts == 0)
    pale = foreground & (source.min(axis=2) >= 245)
    coverage = 1 - np.count_nonzero(missing) / max(1, np.count_nonzero(foreground))
    overlap = int(np.count_nonzero(foreground & (counts > 1)))
    passed = coverage >= .995 and overlap == 0 and all(r["precision"] >= .99 and r["recall"] >= .99 for r in rows)
    return {"case_id": case.name, "passed": bool(passed), "macro_iou": float(np.mean([r["iou"] for r in rows])),
            "coverage": coverage, "overlap_foreground_pixels": overlap,
            "pale_recall": None if not pale.any() else float(np.count_nonzero(pale & (counts > 0)) / np.count_nonzero(pale)),
            "groups": rows}


def score(root, prediction, report):
    cases = [root / "cases" / name for name in json.loads((root / "dataset.json").read_text())["cases"]]
    rows = [score_case(case, prediction / case.name) for case in cases]
    result = {"passed": all(r["passed"] for r in rows), "cases": rows,
              "note": "Non-white background set: foreground = pixels differing from the case background."}
    write_json(report, result)
    print(json.dumps({"passed": result["passed"], "cases": [{k: r[k] for k in ("case_id", "passed", "macro_iou", "coverage")} for r in rows]}, indent=2))
    return result


def baseline(root, output, background_mode, fine_grained=False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ai_mask_component_detection import detect_elements
    settings = dict(white_threshold=245, color_tolerance=12, closing_radius=6,
                    add_border=2, connectivity=8, min_element_area=120, component_padding_px=12,
                    background_mode=background_mode)
    if fine_grained:
        settings.update(fine_grained_detection=True, pale_support_threshold=254,
                        enclosed_support_max_area_px=20000)
    timings = []
    names = json.loads((root / "dataset.json").read_text())["cases"]
    for name in names:
        case = root / "cases" / name
        dest = output / name
        dest.mkdir(parents=True, exist_ok=True)
        gt = np.asarray(Image.open(case / "labels.png"))
        groups = json.loads((case / "groups.json").read_text(encoding="utf-8"))["groups"]
        masks = [np.zeros(gt.shape, np.uint8) for _ in groups]
        with tempfile.TemporaryDirectory(prefix="mask_bench_") as temp:
            started = time.perf_counter()
            payload = detect_elements(case / "image.png", Path(temp), settings)
            elapsed = time.perf_counter() - started
        elements = payload["elements"] + payload["residual_elements"]
        for element in elements:
            votes = np.zeros(len(groups) + 1, np.int64)
            runs = element["mask_rle"]["runs"]
            for y, x1, x2 in runs:
                votes += np.bincount(gt[y, x1:x2], minlength=len(votes))
            votes[0] = 0
            if votes.max() == 0:
                continue
            owner = int(votes.argmax()) - 1
            for y, x1, x2 in runs:
                masks[owner][y, x1:x2] = 255
        for group, mask in zip(groups, masks):
            Image.fromarray(mask).save(dest / (group["id"] + ".png"))
        timings.append({"case_id": name, "detector_cold_seconds": elapsed, "components": len(elements),
                        "detector_version": payload.get("version"),
                        "adaptive_background": payload.get("adaptive_background")})
        print(name, round(elapsed, 3), "seconds", flush=True)
    write_json(output / "timings.json", {"python": sys.version, "platform": platform.platform(),
               "settings": settings, "scope": "Detector only, cold cache", "cases": timings})
    score(root, output, output / "report.json")


def selftest(root):
    with tempfile.TemporaryDirectory(prefix="mask_score_test_") as temp:
        base = Path(temp)
        case = root / "cases" / "12_beige_cards"
        names = [g["id"] for g in json.loads((case / "groups.json").read_text(encoding="utf-8"))["groups"]]
        for name in names:
            (base / f"{name}.png").write_bytes((case / f"{name}.png").read_bytes())
        assert score_case(case, base)["passed"]
        first, second = (base / f"{names[1]}.png").read_bytes(), (base / f"{names[2]}.png").read_bytes()
        (base / f"{names[1]}.png").write_bytes(second)
        (base / f"{names[2]}.png").write_bytes(first)
        swapped = score_case(case, base)
        assert not swapped["passed"] and swapped["coverage"] == 1
        combined = np.maximum(np.asarray(Image.open(base / f"{names[1]}.png")), np.asarray(Image.open(base / f"{names[2]}.png")))
        Image.fromarray(combined).save(base / f"{names[1]}.png")
        assert score_case(case, base)["overlap_foreground_pixels"] > 0
        (base / f"{names[1]}.png").write_bytes(first)
        (base / f"{names[2]}.png").unlink()
        assert score_case(case, base)["coverage"] < 1
    print("PASS: exact / swapped ownership / overlap / missing group")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "score", "baseline", "selftest"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--background-mode", choices=["white", "auto"], default="white")
    parser.add_argument("--fine-grained", action="store_true")
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.root)
    elif args.command == "selftest":
        selftest(args.root)
    else:
        if args.output is None:
            parser.error("--output is required for baseline/score")
        if args.command == "baseline":
            if args.output.exists():
                parser.error("baseline output already exists; use a new directory")
            baseline(args.root, args.output, args.background_mode, fine_grained=args.fine_grained)
        else:
            result = score(args.root, args.output, args.output / "report.json")
            sys.exit(0 if result["passed"] else 1)
