"""Pre-provider text capacity check using real fonts and registered slot boxes.

This diagnostic projection excludes unavailable artwork/relations and never
claims whole-page geometry, artwork feasibility, or aesthetic acceptance.
"""
import copy

from artifact_fingerprint import sha256_json
from html_visual_review_service import review_scene, HtmlReviewError


def check_design_feasibility(scene, *, run_dir, deps):
    projected = copy.deepcopy(scene)
    projected.pop('templateRef', None)
    projected['nodes'] = [n for n in projected['nodes'] if n['type'] not in ('image', 'annotation', 'arrow')]
    ids = {n['id'] for n in projected['nodes']}
    projected['motion'] = [m for m in projected['motion'] if m['targetId'] in ids]
    if 'initialVisibleIds' in projected:
        projected['initialVisibleIds'] = [i for i in projected['initialVisibleIds'] if i in ids]
    if not ids:
        return {'status': 'not_applicable', 'scope': 'text_capacity_projection', 'excluded': [n['id'] for n in scene['nodes']]}
    report = review_scene(projected, run_dir=run_dir, deps=deps, diagnostic=True)
    result = {'status': 'changes_required' if report.get('capacityIssues') else 'passed',
              'scope': 'text_capacity_projection', 'scene_sha256': sha256_json(scene),
              'projected_scene_sha256': sha256_json(projected), 'report': report,
              'excluded': [n['id'] for n in scene['nodes'] if n['id'] not in ids],
              'whole_page_geometry': 'not_checked', 'artwork': 'not_checked', 'human_approval': 'pending'}
    if not report.get('geometry') and not report.get('passed') and not report.get('capacityIssues'):
        raise HtmlReviewError('设计前文字检查未完成', code='DESIGN_FEASIBILITY_INCOMPLETE')
    return result
