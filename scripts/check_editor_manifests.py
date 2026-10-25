#!/usr/bin/env python3
"""Fail when sealed editor build manifests no longer match their sources.

A commit that touches `static/index.html` or `editor_ui/` sources without
rebuilding leaves the committed manifests stale and breaks every editor
snapshot check (EDITOR_BUILD_SOURCE_CHANGED) on every machine. Rebuild with
the official tool instead of editing manifests by hand: `cd editor_ui && npm run build`.

Manifest path bases differ per format (build.mjs): the editor_ui build manifest
records paths relative to `editor_ui/` (sources) and `static/editor_ui/` (bundled
files); the canvas/timeline production manifests record repository-root paths.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# format -> {section: base directory for recorded paths}
PATH_BASES = {
    "hps.editor_ui.build": {"sources": ROOT / "editor_ui", "files": ROOT / "static" / "editor_ui"},
    "hps.editor_canvas.build": {"sources": ROOT, "files": ROOT},
    "hps.editor_timeline.build": {"sources": ROOT, "files": ROOT},
}


def _expected_digest(record) -> str | None:
    if isinstance(record, str):
        return record
    if isinstance(record, dict):
        return record.get("sha256")
    return None


def main() -> int:
    stale: list[str] = []
    for manifest_path in sorted((ROOT / "static" / "editor_ui").glob("*manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bases = PATH_BASES.get(manifest.get("format"))
        if not bases:
            continue  # Only guard manifests with a known path layout.
        for section, base in bases.items():
            records = manifest.get(section)
            if not isinstance(records, dict):
                continue
            for relative, record in records.items():
                source = base / relative
                if not source.is_file():
                    stale.append(f"{manifest_path.name}: {relative} missing")
                    continue
                data = source.read_bytes()
                expected = _expected_digest(record)
                if expected and hashlib.sha256(data).hexdigest() != expected:
                    stale.append(f"{manifest_path.name}: {relative} changed")
    if stale:
        print("Editor build manifests are stale:", file=sys.stderr)
        for item in stale:
            print(f"  - {item}", file=sys.stderr)
        print("Rebuild from source: cd editor_ui && npm run build", file=sys.stderr)
        return 1
    print("editor build manifests are fresh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
