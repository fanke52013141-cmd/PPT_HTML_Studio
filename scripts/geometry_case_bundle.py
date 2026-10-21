"""Standalone stdlib-only cross-machine case export/import. Never runs a service.

export --source-run RUN --course-id ID --case SLIDE:OBJECT[,OBJECT] --output FILE.zip
import --bundle FILE.zip --output NEW_DIRECTORY
Only author inputs, manual guards, resources and selected audio are transferred.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

FORMAT = 'hps.geometry.case_bundle/0.1.0'
MAX_FILE = 128 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
MAX_ENTRIES = 5000
ID = re.compile(r'^[a-z0-9][a-z0-9._-]{0,79}$')
AUDIO = {'tts_text.txt', 'voice.mp3', 'tts_metadata.json', 'subtitles.srt', 'audio_timeline.json'}


def document(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse_cases(values):
    cases = []
    for value in values:
        slide, sep, objects = value.partition(':')
        scope = objects.split(',')
        if (not sep or not ID.fullmatch(slide) or not 1 <= len(scope) <= 4 or
                len(set(scope)) != len(scope) or not all(ID.fullmatch(o) for o in scope)):
            raise ValueError('Case must be SLIDE:OBJECT[,OBJECT], one to four objects')
        cases.append({'slide_id': slide, 'scope': scope})
    if not 1 <= len(cases) <= 5 or len({c['slide_id'] for c in cases}) != len(cases):
        raise ValueError('Select one to five distinct slides')
    return cases


def allowed(relative, slides):
    p = PurePosixPath(relative)
    if '\\' in relative or ':' in relative or p.is_absolute() or any(x in ('', '.', '..') for x in relative.split('/')):
        return False
    if relative in ('planning/visual_contract.json', 'planning/html_visual/revision.json',
                    'planning/html_visual/resources.json'):
        return True
    if len(p.parts) == 3 and p.parts[:2] == ('planning', 'html_visual'):
        return any(p.name == f'{prefix}-{s}.json' for prefix in ('scene', 'binding', 'edits') for s in slides)
    if len(p.parts) >= 4 and p.parts[:3] in (('planning', 'html_visual', 'assets'),
                                                            ('planning', 'html_visual', 'editor-assets')):
        return True
    return len(p.parts) == 3 and p.parts[0] == 'slides' and p.parts[1] in slides and p.name in AUDIO


def export_bundle(source, output, course_id, case_values):
    source, output = Path(source).resolve(), Path(output).resolve()
    cases = parse_cases(case_values)
    slides = {c['slide_id'] for c in cases}
    if not ID.fullmatch(course_id) or output.exists() or source == output or source in output.parents:
        raise ValueError('Safe course id and new ZIP outside source run required')
    paths = [source / 'planning/visual_contract.json']
    visual = source / 'planning/html_visual'
    paths += [visual / name for name in ('revision.json', 'resources.json')]
    paths += [visual / f'{prefix}-{s}.json' for s in slides for prefix in ('scene', 'binding', 'edits')]
    paths += [source / 'slides' / s / name for s in slides for name in AUDIO]
    for name in ('assets', 'editor-assets'):
        folder = visual / name
        if folder.is_dir():
            paths += [p for p in folder.rglob('*') if p.is_file()]
    for s in slides:
        if not (visual / f'scene-{s}.json').is_file():
            raise ValueError('Missing author scene: ' + s)
    if not paths[0].is_file():
        raise ValueError('Missing authoritative visual contract')
    files = {}
    total = 0
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(source) or not allowed(relative, slides):
            raise ValueError('Source escapes allowed input boundary')
        size = path.stat().st_size
        total += size
        if size > MAX_FILE or total > MAX_TOTAL or len(files) >= MAX_ENTRIES - 1:
            raise ValueError('Case bundle exceeds transfer budget')
        files[relative] = {'sha256': digest(path.read_bytes()), 'bytes': size}
    manifest = {'format': FORMAT, 'course_id': course_id, 'cases': cases, 'files': files,
                'source_run_name': source.name, 'approvals_transferred': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, identity in files.items():
            data = (source / relative).read_bytes()
            if len(data) != identity['bytes'] or digest(data) != identity['sha256']:
                raise ValueError('Input changed during export; discard incomplete ZIP')
            archive.writestr('run/' + relative, data)
        # A concurrent original edit invalidates the snapshot rather than
        # silently combining different author revisions.
        if any(digest((source / p).read_bytes()) != value['sha256'] for p, value in files.items()):
            raise ValueError('Input changed during export; discard incomplete ZIP')
        archive.writestr('manifest.json', document(manifest))
    return {'output': str(output), 'files': len(files), 'bytes': total, 'sha256': digest(output.read_bytes())}


def import_bundle(bundle, output):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Import requires a new directory; existing data cannot be overwritten')
    with zipfile.ZipFile(bundle) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if (len(entries) > MAX_ENTRIES or len(set(n.casefold() for n in names)) != len(names) or
                sum(e.file_size for e in entries) > MAX_TOTAL or
                any(e.file_size > MAX_FILE or stat.S_ISLNK(e.external_attr >> 16) for e in entries)):
            raise ValueError('Duplicate, symlink or oversized archive')
        if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size > 2 * 1024 * 1024:
            raise ValueError('Missing or oversized manifest')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != FORMAT or not ID.fullmatch(manifest.get('course_id', '')):
            raise ValueError('Unsupported case bundle')
        cases = parse_cases([c['slide_id'] + ':' + ','.join(c['scope']) for c in manifest['cases']])
        slides = {c['slide_id'] for c in cases}
        files = manifest['files']
        if (not isinstance(files, dict) or set(names) != {'manifest.json', *('run/' + p for p in files)}
                or any(not allowed(p, slides) for p in files)
                or any(f'planning/html_visual/scene-{s}.json' not in files for s in slides)
                or 'planning/visual_contract.json' not in files):
            raise ValueError('Unexpected files or incomplete author inputs')
        for relative, identity in files.items():
            data = archive.read('run/' + relative)
            if len(data) != identity['bytes'] or digest(data) != identity['sha256']:
                raise ValueError('Input hash mismatch: ' + relative)
        # Validate all members before creating the isolated destination.
        output.mkdir(parents=True)
        for relative in files:
            path = output / 'run' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read('run/' + relative))
        (output / 'manifest.json').write_bytes(document(manifest))
        spec = {'cases': [{**c, 'id': f'page-{i+1}', 'course_id': manifest['course_id'],
                          'page_id': c['slide_id'], 'source_run': str(output / 'run'),
                          'provenance': 'original',
                          'source_note': 'Exact author inputs imported from hash-verified case bundle; no approvals transferred.'}
                         for i, c in enumerate(cases)]}
        (output / 'cases.json').write_bytes(document(spec))
    return {'output': str(output), 'cases': len(cases), 'spec': str(output / 'cases.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    export = commands.add_parser('export')
    export.add_argument('--source-run', type=Path, required=True)
    export.add_argument('--course-id', required=True)
    export.add_argument('--case', action='append', required=True)
    export.add_argument('--output', type=Path, required=True)
    load = commands.add_parser('import')
    load.add_argument('--bundle', type=Path, required=True)
    load.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = (export_bundle(args.source_run, args.output, args.course_id, args.case) if args.action == 'export'
              else import_bundle(args.bundle, args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
