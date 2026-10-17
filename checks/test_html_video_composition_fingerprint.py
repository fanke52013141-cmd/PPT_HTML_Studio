from pathlib import Path

from artifact_fingerprint import render_input_fingerprint, presentation_input_fingerprint


def test_composition_source_only_changes_html_video_fingerprint(tmp_path, monkeypatch):
    import artifact_fingerprint as module
    import html_input_manifest

    monkeypatch.setattr(html_input_manifest, 'html_project_inputs', lambda _: {'digest':'scene'})
    original = module.sha256_file
    changed = False

    def file_hash(path):
        if Path(path).name == 'html_render_runner.py':
            return 'changed' if changed else 'original'
        return original(path)

    monkeypatch.setattr(module, 'sha256_file', file_hash)
    before = render_input_fingerprint(tmp_path, visual_settings={}, pipeline_version='test')
    pptx = presentation_input_fingerprint(tmp_path)
    changed = True
    after = render_input_fingerprint(tmp_path, visual_settings={}, pipeline_version='test')
    assert before != after
    assert presentation_input_fingerprint(tmp_path) == pptx
    monkeypatch.setattr(html_input_manifest, 'html_project_inputs', lambda _: None)
    image_before = render_input_fingerprint(tmp_path, visual_settings={}, pipeline_version='test')
    changed = False
    assert render_input_fingerprint(tmp_path, visual_settings={}, pipeline_version='test') == image_before
