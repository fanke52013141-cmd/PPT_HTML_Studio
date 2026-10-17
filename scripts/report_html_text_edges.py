"""Build an offline read-only edge report from a sealed saved localization record."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='New output directory')
    args = parser.parse_args()
    from artifact_fingerprint import sha256_file
    from html_text_edge_report import write_text_edge_report
    source_hash = sha256_file(args.record)
    record = json.loads(args.record.read_text(encoding='utf-8'))
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = write_text_edge_report(args.reference, record, args.out/'text-edges.html')
    if sha256_file(args.record) != source_hash:
        raise ValueError('TEXT_EDGE_REPORT_RECORD_CHANGED')
    receipt.update(source_record_sha256=source_hash, source_records_changed=0)
    (args.out/'manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
