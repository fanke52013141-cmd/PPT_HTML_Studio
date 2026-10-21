import json
import zipfile

import pytest

from scripts.geometry_case_bundle import export_bundle, import_bundle


def source(tmp_path):
    run = tmp_path / 'original'
    visual = run / 'planning/html_visual'
    visual.mkdir(parents=True)
    for path, data in {
        run / 'planning/visual_contract.json': {'slides': []},
        visual / 'scene-slide_001.json': {'id': 'slide_001'},
        visual / 'edits-slide_001.json': {'protected_paths': [['scene', 'nodes', 'label']]},
        visual / 'revision.json': {'revision': 9},
        visual / 'approved-slide_001.json': {'approved': True},
        run / 'planning/project_model_binding.json': {'api_key': 'DO_NOT_TRANSFER'},
    }.items():
        path.write_text(json.dumps(data), encoding='utf-8')
    return run


def test_roundtrip_retains_guards_and_excludes_models_and_approvals(tmp_path):
    run = source(tmp_path)
    bundle = tmp_path / 'case.zip'
    export_bundle(run, bundle, 'course', ['slide_001:label'])
    imported = tmp_path / 'imported'
    result = import_bundle(bundle, imported)
    assert result['cases'] == 1
    assert (imported / 'run/planning/html_visual/revision.json').read_bytes() == (
        run / 'planning/html_visual/revision.json').read_bytes()
    assert not (imported / 'run/planning/project_model_binding.json').exists()
    assert not (imported / 'run/planning/html_visual/approved-slide_001.json').exists()
    assert (imported / 'run/planning/html_visual/edits-slide_001.json').is_file()
    with pytest.raises(ValueError, match='new directory'):
        import_bundle(bundle, imported)
    with pytest.raises(ValueError):
        export_bundle(run, bundle, 'course', ['slide_001:label'])


@pytest.mark.parametrize('change', ['hash', 'traversal', 'credential', 'duplicate'])
def test_untrusted_archive_is_rejected_before_creating_destination(tmp_path, change):
    run = source(tmp_path)
    bundle = tmp_path / 'case.zip'
    export_bundle(run, bundle, 'course', ['slide_001:label'])
    with zipfile.ZipFile(bundle) as z:
        entries = {n: z.read(n) for n in z.namelist()}
    if change == 'hash':
        entries['run/planning/html_visual/scene-slide_001.json'] = b'tampered'
    elif change in ('traversal', 'credential'):
        manifest = json.loads(entries['manifest.json'])
        name = '../outside.json' if change == 'traversal' else 'data/credentials.json'
        manifest['files'][name] = {'bytes': 0, 'sha256': 'bad'}
        entries['run/' + name] = b''
        entries['manifest.json'] = json.dumps(manifest).encode()
    else:
        entries['RUN/planning/html_visual/scene-slide_001.json'] = b'duplicate'
    malicious = tmp_path / 'malicious.zip'
    with zipfile.ZipFile(malicious, 'x') as z:
        for name, data in entries.items():
            z.writestr(name, data)
    destination = tmp_path / 'destination'
    with pytest.raises(ValueError):
        import_bundle(malicious, destination)
    assert not destination.exists()


def test_missing_author_does_not_create_a_bundle(tmp_path):
    run = source(tmp_path)
    bundle = tmp_path / 'missing.zip'
    with pytest.raises(ValueError, match='Missing author'):
        export_bundle(run, bundle, 'course', ['slide_002:label'])
    assert not bundle.exists()
