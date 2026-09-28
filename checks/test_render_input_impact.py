import json

from artifact_fingerprint import render_input_fingerprint


def _fingerprint(run_dir):
    return render_input_fingerprint(run_dir, visual_settings={}, pipeline_version="v6")


def test_annotation_timeline_changes_make_video_stale(tmp_path):
    planning = tmp_path / "planning"
    slide = tmp_path / "slides" / "slide_001"
    planning.mkdir()
    slide.mkdir(parents=True)
    (planning / "visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": "slide_001"}]}), encoding="utf-8"
    )
    timeline = slide / "annotation_timeline.json"
    timeline.write_text('{"events":[]}', encoding="utf-8")
    before = _fingerprint(tmp_path)["digest"]
    timeline.write_text('{"events":[{"x":1}]}', encoding="utf-8")
    assert _fingerprint(tmp_path)["digest"] != before


def test_non_render_digital_human_fields_do_not_stale_video(tmp_path):
    planning = tmp_path / "planning"
    planning.mkdir()
    config = planning / "digital_human.json"
    value = {"enabled": True, "mode": "upload", "shape": "circle", "avatar_id": "a"}
    config.write_text(json.dumps(value), encoding="utf-8")
    before = _fingerprint(tmp_path)["digest"]
    value["avatar_id"] = "b"
    value["sync_mode"] = "accurate"
    value["slides"] = {"slide_001": {"status": "done"}}
    config.write_text(json.dumps(value), encoding="utf-8")
    assert _fingerprint(tmp_path)["digest"] == before
    value["shape"] = "rect"
    config.write_text(json.dumps(value), encoding="utf-8")
    assert _fingerprint(tmp_path)["digest"] != before
