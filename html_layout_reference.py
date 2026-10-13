"""Deterministic slot guide: an attachment, never a generated design or approval."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

from artifact_fingerprint import sha256_file, sha256_json
from pipeline_lifecycle import write_json_atomic


def attach_layout_guide(directory):
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if any(entry.get("type") == "layout-guide" for entry in manifest["attachments"]):
        return  # verify_package checks cached guide bytes before model use.
    content = json.loads((directory / manifest["exactContent"]["path"]).read_text(encoding="utf-8"))
    geometry = content["layoutGeometry"]
    canvas = geometry["canvas"]
    scale = 1280 / canvas["width"]
    image = Image.new("RGB", (1280, round(canvas["height"] * scale)), "white")
    draw = ImageDraw.Draw(image)
    # Parent figure and full-canvas annotations would hide the actual object regions.
    for index, (slot, box) in enumerate(geometry["slots"].items()):
        if slot in {"annotation", "figure"}:
            continue
        x, y, w, h = (box[key] * scale for key in ("x", "y", "width", "height"))
        draw.rectangle((x, y, x + w, y + h), fill="#f4f4f4", outline="#777777", width=2)
        draw.text((x + 6, y + 6), f"{index + 1}: {slot}", fill="#333333")
    bottom = round(canvas["contentBottom"] * scale)
    draw.line((0, bottom, image.width, bottom), fill="#999999", width=2)
    draw.text((12, bottom + 12), "SUBTITLE RESERVE - KEEP EMPTY", fill="#555555")
    path = directory / "layout-guide.png"
    image.save(path)
    entry = {"path": path.name, "sha256": sha256_file(path), "size": path.stat().st_size}
    manifest["files"].append(entry)
    manifest["attachments"].append({"path": path.name, "sha256": entry["sha256"],
                                    "width": image.width, "height": image.height,
                                    "type": "layout-guide"})
    manifest["cacheKey"] = sha256_json({"original": manifest["cacheKey"], "layoutGuide": entry["sha256"]})
    manifest["manifestSha256"] = sha256_json({key: value for key, value in manifest.items() if key != "manifestSha256"})
    write_json_atomic(manifest_path, manifest)
