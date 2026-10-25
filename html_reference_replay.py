"""Exact local review receipts: one dispatch per immutable correction identity.

Exclusive intent creation also fences concurrent processes. An interrupted or
unknown attempt never dispatches again automatically. Completed results are
recorded evidence, not a new assessment by the caller's current model.
"""
import json
from pathlib import Path

from artifact_fingerprint import sha256_file, sha256_json
from pipeline_lifecycle import write_json_atomic


def execute_once(folder, identity, execute, fresh):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    intent = folder/'attempt.json'
    key = sha256_json(identity)
    fresh()
    try:
        with intent.open('x', encoding='utf-8') as stream:
            json.dump({'state':'intent', 'key':key, 'identity':identity}, stream, ensure_ascii=False)
            stream.flush()
    except FileExistsError:
        try:
            receipt = json.loads(intent.read_text(encoding='utf-8'))
            result_path = folder/'completed.json'
            if (receipt.get('key') == key and receipt.get('state') == 'completed'
                and result_path.is_file() and sha256_file(result_path) == receipt.get('result_sha256')):
                result = json.loads(result_path.read_text(encoding='utf-8'))
                fresh()
                return {**result, 'replay_receipt':{'key':key, 'reused':True, 'dispatches_this_call':0}}
        except (OSError, ValueError):
            pass
        raise ValueError('REFERENCE_REVIEW_ALREADY_SUBMITTED_OR_EVIDENCE_INVALID') from None
    try:
        fresh()
        result = execute()
        fresh()
        result_path = folder/'completed.json'
        write_json_atomic(result_path, result)
        write_json_atomic(intent, {'state':'completed', 'key':key, 'identity':identity,
                                  'result_sha256':sha256_file(result_path)})
        return {**result, 'replay_receipt':{'key':key, 'reused':False, 'dispatches_this_call':1}}
    except BaseException:
        # The transport owns outcome classification. This owner only prevents
        # an automatic duplicate after any uncertain/interrupted completion.
        write_json_atomic(intent, {'state':'stopped', 'key':key, 'identity':identity,
                                   'automatic_retry':False})
        raise
