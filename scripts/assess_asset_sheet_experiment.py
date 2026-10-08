"""Explicit opt-in multimodal advisory CLI; credentials remain process-local."""
import argparse
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from html_asset_sheet import HtmlAssetSheetError
from html_asset_sheet_assessment import assess_candidates, configured_vision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--sheet-id', required=True)
    parser.add_argument('--request-key', required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--model', required=True)
    parser.add_argument('--base-url', default='https://api.openai.com/v1')
    parser.add_argument('--api-key-env', default='OPENAI_API_KEY')
    args = parser.parse_args()
    key = os.environ.get(args.api_key_env)
    if not key:
        print(f'未配置环境变量 {args.api_key_env}，未发送模型请求。')
        return 2
    model_hash = hashlib.sha256(json.dumps({'model': args.model, 'endpoint': args.base_url}, sort_keys=True).encode()).hexdigest()
    binding = SimpleNamespace(model=args.model, endpoint=args.base_url, api_key=key, require_ready=lambda: None)
    try:
        result = assess_candidates(args.run_dir, args.sheet_id, args.request_key,
            provider=partial(configured_vision, model_binding=binding), model_hash=model_hash,
            reference_bytes=args.reference.read_bytes() if args.reference else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (HtmlAssetSheetError, OSError):
        print('素材审阅失败，请检查候选、模型连接或重试；未批准或发布素材。')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
