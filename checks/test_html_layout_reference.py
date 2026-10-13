import hashlib

import pytest
from PIL import Image

from html_reference_package import assemble_reference, verify_package, HtmlReviewError
from runtime_support import run_subprocess_killable
from checks.test_html_object_decomposition import normalize, decomposition_plan, brief, ROOT
from scripts.compare_visual_reconstruction import compare


def test_layout_attachment_is_cached_and_tampering_blocks(tmp_path):
    plan = normalize(decomposition_plan())
    kwargs = dict(repo_root=ROOT, directory=tmp_path / "package", runner=run_subprocess_killable)
    first = assemble_reference(plan, brief(plan), **kwargs)
    second = assemble_reference(plan, brief(plan), **kwargs)
    assert first["manifest"]["manifestSha256"] == second["manifest"]["manifestSha256"]
    guide = tmp_path / "package/layout-guide.png"
    assert len([entry for entry in second["manifest"]["attachments"] if entry.get("type") == "layout-guide"]) == 1
    original_hash = hashlib.sha256(guide.read_bytes()).hexdigest()
    assert original_hash in [entry["sha256"] for entry in second["manifest"]["attachments"]]
    guide.write_bytes(guide.read_bytes() + b"corrupt")
    with pytest.raises(HtmlReviewError):
        verify_package(tmp_path / "package")


def test_foreground_metric_does_not_reward_large_white_canvas(tmp_path):
    a, b = Image.new("RGB", (100, 100), "white"), Image.new("RGB", (100, 100), "white")
    from PIL import ImageDraw
    ImageDraw.Draw(a).rectangle((10, 10, 20, 20), fill="black")
    ImageDraw.Draw(b).rectangle((70, 70, 80, 80), fill="black")
    for name, picture in (("a.png", a), ("b.png", b)):
        picture.save(tmp_path / name)
    assert compare(tmp_path / "a.png", tmp_path / "a.png")["foreground_iou"] == 1
    shifted = compare(tmp_path / "a.png", tmp_path / "b.png")
    assert shifted["foreground_iou"] == 0
    assert shifted["foreground_mae"] > 30
