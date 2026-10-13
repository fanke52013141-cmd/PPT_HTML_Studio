"""Same-target image diagnostics. Metrics are not aesthetic or semantic approval."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def compare(reference, actual):
    target = Image.open(reference).convert("RGB")
    observed = Image.open(actual).convert("RGB").resize(target.size, Image.Resampling.LANCZOS)
    a = np.asarray(target.filter(ImageFilter.GaussianBlur(2)), dtype=float)
    b = np.asarray(observed.filter(ImageFilter.GaussianBlur(2)), dtype=float)
    # Exclude the blank canvas so white backgrounds cannot dominate the score.
    mask_a, mask_b = a.mean(axis=2) < 240, b.mean(axis=2) < 240
    union = mask_a | mask_b
    return {"canvas": list(target.size), "actual_original_size": list(Image.open(actual).size),
            "foreground_mae": float(np.abs(a - b)[union].mean()) if union.any() else 0.0,
            "foreground_iou": float((mask_a & mask_b).sum() / union.sum()) if union.any() else 1.0,
            "reference_sha256": hashlib.sha256(Path(reference).read_bytes()).hexdigest(),
            "actual_sha256": hashlib.sha256(Path(actual).read_bytes()).hexdigest(),
            "meaning": "Spatial/tonal diagnostics only; inspect text, identity, relationships and motion separately."}


def export_comparison(reference, before, after, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = Image.open(reference).convert("RGB")
    panel = Image.new("RGB", (target.width * 3, target.height), "white")
    for index, path in enumerate((reference, before, after)):
        picture = Image.open(path).convert("RGB").resize(target.size, Image.Resampling.LANCZOS)
        panel.paste(picture, (index * target.width, 0))
    panel.save(output / "comparison.png")
    for name, path in (("before", before), ("after", after)):
        actual = Image.open(path).convert("RGB").resize(target.size, Image.Resampling.LANCZOS)
        Image.blend(target, actual, 0.5).save(output / f"overlay-{name}.png")
    results = {name: compare(reference, path) for name, path in (("before", before), ("after", after))}
    (output / "comparison.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("reference", "before", "after", "out"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_comparison(args.reference, args.before, args.after, args.out), indent=2))
