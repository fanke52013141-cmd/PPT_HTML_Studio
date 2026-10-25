"""Run seven local engineering gates and verify their exact source/evidence.

No provider calls. This scoped ledger does not certify the original 69 ACs,
real-model quality, aesthetics, production approval or deployment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from artifact_fingerprint import sha256_file  # noqa: E402
from pipeline_lifecycle import write_json_atomic  # noqa: E402

GATES = {
    'O7-01': ['checks/test_html_candidate_capacity_solver.py', 'checks/test_html_search_scheduling.py',
              'checks/test_html_saved_layout_repair.py','checks/test_html_reconstruction_diagnostics.py'],
    'O7-02': ['checks/test_html_page_budget.py','checks/test_html_json_observer.py','checks/test_json_llm_transport.py'],
    'O7-03': ['checks/test_html_optimization_acceptance.py','checks/test_html_acceptance_reconciliation.py',
              'checks/test_html_acceptance_criteria.py','checks/test_html_paired_evaluation.py',
              'checks/test_html_annotation_store.py','checks/test_html_evaluation_execution.py'],
    'O7-04': ['checks/test_html_linked_layout.py', 'checks/test_html_layout_groups.py','checks/test_html_p0p2_layouts.py',
              'checks/test_html_followup_layouts.py'],
    'O7-05': ['checks/test_html_design_feasibility.py'],
    'O7-06': ['checks/test_html_reference_workbench.py', 'checks/test_html_independent_review.py',
              'checks/test_html_reference_replay.py', 'checks/test_html_reference_workbench_ui.py',
              'checks/test_html_reference_api.py','checks/test_html_reference_continuation.py','checks/test_html_p0p2_panel.py',
              'checks/test_html_reference_inline_ui.py','checks/test_html_evaluation_api.py',
              'checks/test_html_evaluation_browser.py','checks/test_html_evaluation_creation.py'],
    'O7-07': ['checks/test_html_review_cache.py', 'checks/test_html_asset_service.py', 'checks/test_html_asset_geometry.py',
              'checks/test_html_asset_reuse.py',
              'checks/test_html_e_production.py::test_explicit_cross_page_resource_survives_design_checkpoint_without_subject_call'],
}
EXPECTED_CASES = {
    'capacity': {'normal':'unchanged', 'two-cards':'candidate', 'budget':'budget_exhausted', 'protected':'needs_revision'},
    'linked': {'three-cards-summary':'candidate', 'point-routing':'candidate', 'protected-column':'needs_revision',
               'staggered-frame':'candidate', 'grid-rows':'candidate', 'protected-grid':'needs_revision'},
}


def junit_passed(path):
    cases = list(ET.parse(path).getroot().iter('testcase'))
    return bool(cases) and all(not any(c.find(k) is not None for k in ('failure', 'error', 'skipped')) for c in cases)


def safe_path(root, name):
    path = (root/name).resolve()
    if not isinstance(name, str) or Path(name).is_absolute() or not path.is_relative_to(root) or path == root:
        raise ValueError('EVIDENCE_PATH_INVALID')
    return path


def validate_bundle(directory, repo=ROOT):
    root, repo = Path(directory).resolve(), Path(repo).resolve()
    errors = []
    try:
        manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('format') != 'hps.optimization7.acceptance/0.1.0':
            raise ValueError('MANIFEST_VERSION_INVALID')
        if not manifest.get('sources') or not manifest.get('files'):
            raise ValueError('EVIDENCE_INCOMPLETE')
        if manifest.get('sources_changed_during_run'):
            errors.append('SOURCES_CHANGED_DURING_RUN')
        for section, base in (('files', root), ('sources', repo)):
            for name, digest in manifest[section].items():
                path = safe_path(base, name)
                if not path.is_file() or sha256_file(path) != digest:
                    errors.append(section + ': missing or changed ' + name)
        gates = manifest.get('gates', {})
        if set(gates) != set(GATES):
            errors.append('REQUIRED_GATES_INCOMPLETE')
        for key, gate in gates.items():
            if gate.get('status') != 'passed' or gate.get('provenance') != 'offline_engineering_tests':
                errors.append(key+': NOT_PASSED')
            path = safe_path(root, gate['junit'])
            if gate['junit'] not in manifest['files'] or not junit_passed(path):
                errors.append(key+': REQUIRED_TEST_NOT_PASSED')
        for name in ('capacity', 'linked'):
            relative = f'{name}/summary.json'
            summary = json.loads(safe_path(root, relative).read_text(encoding='utf-8'))
            if (relative not in manifest['files'] or summary.get('passed') is not True
                or summary.get('provenance') != 'controlled_fixture' or not summary.get('cases')
                or any(c.get('passed') is not True for c in summary['cases'])):
                errors.append(name+': BROWSER_FIXTURES_NOT_PASSED')
            cases = summary.get('cases', [])
            if (len(cases) != len(EXPECTED_CASES[name])
                or {c.get('case') for c in cases} != set(EXPECTED_CASES[name])):
                errors.append(name+': REQUIRED_BROWSER_CASES_INCOMPLETE')
            for case in summary.get('cases', []):
                status = case.get('actual_status', case.get('summary', {}).get('status'))
                if status != EXPECTED_CASES[name].get(case.get('case')):
                    errors.append(name+'/'+str(case.get('case'))+': UNEXPECTED_OUTCOME')
                if status not in ('candidate', 'unchanged'):
                    continue
                complete = False
                for raw_path in (root/name/case['case']).rglob('report.json'):
                    raw = json.loads(raw_path.read_text(encoding='utf-8'))
                    coverage, frames = raw.get('coverage', {}), raw.get('frames', [])
                    if (raw_path.relative_to(root).as_posix() in manifest['files']
                        and raw.get('passed') is True and not raw.get('issues') and not raw.get('pageErrors')
                        and coverage.get('frame_complete') is True and coverage.get('mode') == 'output_frames'
                        and coverage.get('fps') == 30 and bool(frames)
                        and isinstance(coverage.get('rangeMs'), list) and len(coverage['rangeMs']) == 2
                        and [f.get('timeMs') for f in frames] == coverage.get('times')):
                        complete = True
                if not complete:
                    errors.append(name+'/'+case['case']+': FULL_TEMPORAL_EVIDENCE_MISSING')
        if manifest.get('real_model_quality') != 'not_run' or manifest.get('human_visual_acceptance') != 'pending':
            errors.append('ACCEPTANCE_BOUNDARY_INVALID')
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        errors.append(str(exc))
    return {'passed': not errors, 'errors': errors}


def source_manifest():
    sources = list(ROOT.glob('html_*.py')) + list((ROOT/'checks').glob('test_html_*.py'))
    sources += [Path(__file__), ROOT/'scripts/benchmark_candidate_capacity.py',
                ROOT/'scripts/benchmark_linked_layout.py', ROOT/'config/html_runtime_skills.json']
    sources += list((ROOT/'config/html_runtime_skills').glob('*.md'))
    sources += list((ROOT/'html_engine/tools').glob('*.cjs')) + list((ROOT/'html_engine/visual').rglob('*.cjs'))
    sources += [ROOT/'html_engine/package.json']
    sources += [ROOT/'html_engine/visual/preview/player.js', ROOT/'html_engine/visual/generated/catalog.json']
    sources += list((ROOT/'checks/fixtures').rglob('*.json'))
    sources += list((ROOT/'checks/fixtures/reconstruction-pairs').rglob('*.png'))
    sources += [ROOT/'scripts/verify_reconstruction_criteria.py',ROOT/'scripts/evaluate_reconstruction_pairs.py',
                ROOT/'scripts/prepare_reconstruction_dataset.py',ROOT/'scripts/score_html_reference_localization.py',
                ROOT/'config/html_acceptance_criteria.json']
    sources += [ROOT/'json_llm_transport.py',ROOT/'json_llm_service.py',ROOT/'checks/test_json_llm_transport.py']
    sources += [ROOT/'checks/html_design_agent_fixture.py', ROOT/'checks/conftest.py']
    sources += list((ROOT/'html_engine/visual').glob('**/*.json'))
    sources += list((ROOT/'static').glob('html_*.js'))
    sources += [ROOT/'static/index.html', ROOT/'agent_contract/capabilities.py',ROOT/'agent_contract/versions.py',
                ROOT/'agent_api/routes.py', ROOT/'scripts/reconcile_reconstruction_acceptance.py']
    sources += [ROOT/'mcp_server/tools.py',ROOT/'agent_client/client.py',ROOT/'cli/pptctl.py',
                ROOT/'checks/test_frontend_quality.js',ROOT/'static/editor_ui/canvas-manifest.json',
                ROOT/'static/editor_ui/timeline-manifest.json',ROOT/'docs/contracts/html-presentation/contract-index.json']
    sources += list((ROOT/'checks/agent').glob('test_html_*.py'))
    return {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in sources if p.is_file()}


def run(output, *, original_plan=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    initial_sources = source_manifest()
    env = dict(os.environ)
    temp = output/'tmp'
    temp.mkdir()
    env.update(TEMP=str(temp), TMP=str(temp), PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    gates = {}
    for key, tests in GATES.items():
        junit = key+'.xml'
        base = ROOT/'outputs'/('q7'+uuid.uuid4().hex[:5])
        command = [sys.executable, '-m', 'pytest', *tests, '-q', f'--basetemp={base}', f'--junitxml={output/junit}']
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
        (output/(key+'.log')).write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
        passed = result.returncode == 0 and (output/junit).is_file() and junit_passed(output/junit)
        gates[key] = {'status': 'passed' if passed else 'failed', 'junit': junit,
                      'provenance': 'offline_engineering_tests', 'command': command}
        print(key, gates[key]['status'], flush=True)
    for script, name in (('benchmark_candidate_capacity.py', 'capacity'), ('benchmark_linked_layout.py', 'linked')):
        result = subprocess.run([sys.executable, str(ROOT/'scripts'/script), '--output', str(output/name)],
            cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
        (output/(name+'.log')).write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
    manifest = {'format': 'hps.optimization7.acceptance/0.1.0', 'gates': gates,
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sources': initial_sources, 'sources_changed_during_run': initial_sources != source_manifest(),
        'real_model_quality': 'not_run', 'human_visual_acceptance': 'pending', 'deployment': 'not_run'}
    if original_plan:
        plan = json.loads(Path(original_plan).read_text(encoding='utf-8'))
        manifest['original_acceptance'] = {i: {'status':'not_run', 'reason':'not certified by this scoped runner'}
            for task in plan['tasks'] for i in task['acceptance_ids']}
    manifest['files'] = {p.relative_to(output).as_posix(): sha256_file(p) for p in output.rglob('*')
                         if p.is_file() and not p.is_relative_to(temp)}
    write_json_atomic(output/'manifest.json', manifest)
    result = validate_bundle(output)
    write_json_atomic(output/'verification.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--output', type=Path)
    action.add_argument('--verify', type=Path)
    parser.add_argument('--original-plan', type=Path)
    args = parser.parse_args()
    result = validate_bundle(args.verify) if args.verify else run(args.output, original_plan=args.original_plan)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
