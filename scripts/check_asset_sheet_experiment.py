"""Verify an experimental PNG with the existing strict asset-sheet extractor.

No network, application imports, database access, background repair or approval.
Outputs are written to a new directory so earlier evidence stays immutable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from html_asset_sheet import extract_asset_sheet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument('--clean-alpha', action='store_true', help='Opt into threshold=1 detached-noise cleanup with a 2-pixel guard and 2% budget.')
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output directory must be new; select a versioned sibling.")
    payload = args.image.read_bytes()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    spec["source_sha256"] = hashlib.sha256(payload).hexdigest()
    if args.clean_alpha:
        for slot in spec['slots']:
            slot['alpha_cleanup'] = {'threshold': 1, 'guard_radius': 2, 'max_removed_fraction': .02}
    result = extract_asset_sheet(payload, spec)
    args.out.mkdir(parents=True)
    (args.out / "source.png").write_bytes(payload)
    (args.out / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "extraction.json").write_text(json.dumps(result["manifest"], ensure_ascii=False, indent=2), encoding="utf-8")
    for asset_id, png in result["images"].items():
        (args.out / f"asset-{asset_id}.png").write_bytes(png)
    print(json.dumps(result["manifest"], ensure_ascii=False, indent=2))
    return 0 if len(result["images"]) == len(spec["slots"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
