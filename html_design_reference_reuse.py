"""Revalidate a prior design as a new unapproved reference; no provider calls."""
import copy
import json
from pathlib import Path

from artifact_fingerprint import sha256_json, sha256_file
from html_design_candidates import candidate_directory, _revision_matches, save_design, definition_identity
from html_reference_package import verify_package, assemble_reference
from html_visual_review_service import HtmlReviewError


def reuse_design_reference(*, run_dir, contract, key, revision, definitions, model_summary,
                           repo_root, plan_version, checkpoint=lambda: None):
    from html_storyboard_planning import normalize_html_scene_plan, load_template_catalog
    from html_design_brief import build_design_brief, load_effect_registry
    from runtime_support import run_subprocess_killable
    run, root = Path(run_dir), Path(repo_root)
    checkpoint()
    directory = candidate_directory(run, contract['slide_id'], key)
    try:
        record = json.loads((directory / 'candidate.json').read_text(encoding='utf-8'))
        image = directory / 'design-reference.png'
        if (record['format'] != 'hps.html.design_candidate' or record['version'] != '0.1.0'
                or sha256_json(record) != key or sha256_file(image) != record['image_sha256']):
            raise ValueError('candidate integrity')
        package_path = (run / record['reference_package']).resolve()
        if not package_path.is_relative_to(run.resolve()):
            raise ValueError('reference package path')
        package = verify_package(package_path)
        if package['manifest']['manifestSha256'] != record['reference_manifest_sha256']:
            raise ValueError('reference package identity')
        if (record['slide_id'] != contract['slide_id'] or record['contract_sha256'] != sha256_json(contract)
                or record['model_summary'] != model_summary or not _revision_matches(run, record, key, revision)
                or record['plan']['version'] != plan_version):
            raise HtmlReviewError('内容、模型或作者输入已变化，不能复用原设计', status_code=409, code='DESIGN_REFERENCE_INPUT_CHANGED')
        plan = normalize_html_scene_plan(copy.deepcopy(record['plan']), load_template_catalog(root), contract_slide=contract)
        if ({k: v for k, v in plan.items() if k != 'registered'}
                != {k: v for k, v in record['plan'].items() if k != 'registered'}):
            raise HtmlReviewError('当前规则要求计划内容变化，请重新规划', code='DESIGN_REFERENCE_PLAN_CHANGED')
        brief = build_design_brief(plan, theme='neutral-baseline', asset_budget=1,
                                   effect_registry=load_effect_registry(root))
        destination = run / 'planning/html_visual/reference-packages' / sha256_json(
            {'plan': plan, 'brief': brief, 'definitions': definitions, 'source_design': key})
        package = verify_package(destination) if destination.exists() else assemble_reference(
            plan, brief, repo_root=root, directory=destination, runner=run_subprocess_killable)
        package['directory'] = str(destination.relative_to(run))
        checkpoint()
        if definition_identity(root) != definitions:
            raise HtmlReviewError('参考复制期间定义发生变化', status_code=409, code='DESIGN_STALE')
        result = save_design(run_dir=run, contract=contract, revision=revision, definitions=definitions,
            model_summary=model_summary, plan=plan, brief=brief,
            candidate={**copy.deepcopy(record['candidate']), 'source_design_key': key, 'source_image_sha256': record['image_sha256'],
                       'mode': 'reused_reference_pending_review'}, package=package, design_path=image)
        result['reference_reused'] = True
        result['message'] = '原图和计划已核验并复制为新待审参考；没有规划/生图/TTS调用，未接受设计或保存HTML。'
        return result
    except HtmlReviewError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HtmlReviewError('原设计无法安全复用', code='DESIGN_REFERENCE_INVALID') from error
