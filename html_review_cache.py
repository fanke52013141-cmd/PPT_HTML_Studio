"""Task-local exact-input review reuse with immutable screenshot evidence.

No cached approval, fuzzy matching, provider results or cross-task reuse.
Every hit verifies the captured files; changed inputs or corruption rerender.
"""
from __future__ import annotations

import copy
from functools import wraps
import os
from pathlib import Path

from artifact_fingerprint import sha256_file, sha256_json
from html_input_manifest import resolved_scene_inputs
from html_page_budget import current_budget


def cached_review(function):
    @wraps(function)
    def execute(scene, *, run_dir, deps, diagnostic=False, preflight_dir=None):
        budget = current_budget()
        if budget is None or not scene.get('templateRef'):
            return function(scene, run_dir=run_dir, deps=deps, diagnostic=diagnostic, preflight_dir=preflight_dir)
        budget.check(final=preflight_dir is not None and not diagnostic)
        root, run = Path(deps.repo_root), Path(run_dir).resolve()
        sources = [root/'html_visual_review_service.py', root/'html_review_cache.py', root/deps.review_script]
        sources += list((root/'html_engine/tools').glob('*.cjs')) + list((root/'html_engine/visual').glob('*.cjs'))
        def identity():
            return sha256_json({'inputs': resolved_scene_inputs(scene, run, root),
                'sources': {str(p.relative_to(root)): sha256_file(p) for p in sources},
                'diagnostic': diagnostic, 'temporal': preflight_dir is not None,
                'node': deps.node_bin, 'environment_sha256': sha256_json(dict(os.environ))})
        key = identity()
        cached = budget.review_cache.get(key)
        if cached and all(p.is_file() and sha256_file(p) == digest for p, digest in cached['files'].items()):
            budget.events.append({'kind': 'review_cache_hit', 'key': key})
            return copy.deepcopy(cached['report'])
        report = function(scene, run_dir=run, deps=deps, diagnostic=diagnostic, preflight_dir=preflight_dir)
        if key != identity():
            return report  # Original callers still enforce freshness before adoption.
        screenshot = (run/report.get('screenshot', 'missing')).resolve()
        if not screenshot.is_relative_to(run) or not screenshot.is_file():
            return report
        folder = run/'planning/html_visual/review-cache'/key
        folder.mkdir(parents=True, exist_ok=True)
        stable = folder/'render.png'
        stable.write_bytes(screenshot.read_bytes())
        report = {**report, 'screenshot': stable.relative_to(run).as_posix()}
        files = {stable: sha256_file(stable)}
        audit = report.get('geometry_preflight', {}).get('audit')
        if audit:
            path = (run/audit/'report.json').resolve()
            if not path.is_relative_to(run) or not path.is_file():
                return report
            files[path] = sha256_file(path)
        budget.review_cache[key] = {'report': copy.deepcopy(report), 'files': files}
        return report
    return execute
