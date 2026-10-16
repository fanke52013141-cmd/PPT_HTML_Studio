"""Archived input integrity and no accidental paid retry in the live evaluator."""
import json

import pytest

from artifact_fingerprint import sha256_file, sha256_json
from scripts.evaluate_html_design_review import freeze_inputs, main, report_scene_hash


@pytest.mark.parametrize("damage", [None, "image", "scene", "report"])
def test_replay_verifies_archived_bytes_and_scenes_before_creating_output(tmp_path, monkeypatch, damage):
    from pipeline_lifecycle import write_json_atomic as write
    import html_production_service
    import html_storyboard_planning
    scene = {"id": "s", "nodes": [{"id": "label", "type": "text"}]}
    monkeypatch.setattr(html_production_service, "compile_plan", lambda *_: (scene, {}))
    monkeypatch.setattr(html_storyboard_planning, "load_template_catalog", lambda *_: {})
    source, design, recon, understanding, out = [tmp_path / n for n in ("source", "design", "recon", "understanding", "out")]
    design.mkdir()
    (recon / "0").mkdir(parents=True)
    (design / "design-reference.png").write_bytes(b"frozen source")
    (recon / "0/candidate.png").write_bytes(b"frozen screenshot")
    write(design / "candidate.json", {"slide_id": "s", "plan": {}, "image_sha256": sha256_file(design / "design-reference.png")})
    write(source / "planning/visual_contract.json", {"slides": [{"slide_id": "s"}]})
    write(source / "planning/project_model_binding.json", {"bindings": {}})
    write(understanding / "result.json", {"scene_sha256": sha256_json(scene)})
    write(recon / "allocation-capacity-repair.json", {"scene": scene})
    write(recon / "0/fidelity/request.json", {"user_prompt": json.dumps({"objects": scene["nodes"]})})
    write(recon / "0/fidelity/result.json", {"scene_sha256": sha256_json(scene),
          "screenshot_sha256": sha256_file(recon / "0/candidate.png")})
    write(recon / "0/strict-review.json", {"scene_sha256": "damaged" if damage == "report" else report_scene_hash(scene)})
    if damage == "image":
        (recon / "0/candidate.png").write_bytes(b"replaced")
    if damage == "scene":
        write(recon / "allocation-capacity-repair.json", {"scene": {**scene, "id": "other"}})
    if damage:
        with pytest.raises(ValueError, match="ARCHIVED_.*MISMATCH"):
            freeze_inputs(source, design, recon, understanding, out)
        assert not out.exists()
    else:
        run, original, final, _, evidence = freeze_inputs(source, design, recon, understanding, out)
        assert original == final == scene
        assert sha256_file(run / "candidate.png") == evidence["screenshot_sha256"]
        with pytest.raises(ValueError, match="OUTPUT_MUST_BE_NEW"):
            freeze_inputs(source, design, recon, understanding, out)


def test_live_replay_rejects_existing_output_before_reading_configuration(tmp_path):
    with pytest.raises(ValueError, match="OUTPUT_MUST_BE_NEW"):
        main(["--source-run", "absent", "--design-folder", "absent", "--reconstruction", "absent",
              "--understanding", "absent", "--out", str(tmp_path), "--live"])
