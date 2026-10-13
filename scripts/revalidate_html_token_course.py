"""Actual S08 image-design revalidation, preserving the rejected experiment.

Uses shared production jobs and configured transport in an isolated database.
Stops at the real design checkpoint; never creates user approval.
"""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.accept_html_token_course import write, settings_readonly, emit

VISUALS = [
    '文字进入模型后分成可处理单元：一组透明立体积木与文本流的概念主体，帮助理解Token单位；不冒充具体分词器切分。',
    '同一句话被切成不同粒度单元：完整文本带进入切分器、变为单元的概念主体；上屏中文和关系由代码控制。',
    '输入与输出分别统计：双向文本流穿过处理核心的概念主体，输入和输出身份清楚；不要用纯文字三列代替图解。',
    '上下文窗口容量有限：可见的有限容器承载输入信息，并给输出保留空间的概念主体；不要虚构模型容量数值。',
    '把Token用在必要信息上：去掉重复、保留关键背景的概念主体，有清楚视觉重点；不要把整段旁白堆在屏幕。',
]
DESIGN_DIRECTION = ('以当前内容的知识表达和美感为验收目标。具有清晰的视觉主体、阅读顺序、图文融合与留白；'
    '黑灰白风格，不做软件界面或表单。不要把标题栏、装饰横线、圆角框当作默认构图，避免无语义边框。'
    '准确中文与关系仍由代码控制，独立图片用于概念主体。真实支持能力不足必须报告，不假装自由构图已实现。')


def build_design_index(out):
    from html import escape
    from PIL import Image
    out = Path(out).resolve()
    run = out / 'runs/token-visual-revalidation'
    tasks = json.loads((out / 'production-tasks.json').read_text(encoding='utf-8'))
    course = json.loads((out / 'course-input.json').read_text(encoding='utf-8'))
    titles = {slide['slide_id']: slide['title'] for slide in course['slides']}
    cards, checks = [], []
    for task in tasks:
        identity = task['slide_id']
        design = (task.get('result') or {}).get('design')
        heading = '<h2>' + escape(identity + ' · ' + titles[identity]) + '</h2>'
        if design:
            path = run / design['file']
            with Image.open(path) as picture:
                size = list(picture.size)
            relative = os.path.relpath(path, out).replace('\\', '/')
            cards.append('<section>' + heading + '<img alt="真实生成设计候选" src="' + escape(relative, quote=True) + '"><p>实际尺寸：' + str(size[0]) + ' × ' + str(size[1]) + ' · 设计待审阅 · 尚未生成独立素材与 HTML</p></section>')
            checks.append({'slide_id': identity, 'key': design['key'], 'size': size,
                'size_verified': size == [1280, 720], 'sha256': design['sha256'], 'user_approval': False})
        else:
            cards.append('<section>' + heading + '<p>' + escape(task.get('error') or '没有设计图') + '</p></section>')
    write(out / 'design-file-checks.json', checks)
    html = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Token · Flare 真实设计审阅</title><style>body{background:#f5f5f5;color:#222;font:16px/1.7 system-ui;margin:0}main{max-width:1280px;margin:auto;padding:28px}section{background:white;padding:20px;margin:24px 0;border-radius:12px}img{width:100%;height:auto}h2{font-size:22px}a{color:#2154a5}.status{background:#fff1d6;padding:18px;border-radius:12px}</style><main><h1>Token 科普 · 真实生图设计审阅</h1><p class="status">模型 gpt-image-2.5-flare-vip · quality low · 1K档横屏1280×720。这里展示真实设计图，不是代码截图或完成的HTML。未给予用户视觉批准，完整制作验收尚未通过。</p><p>实际提交了组件参考图片。请检查构图、图文表达、可读性与美感；代码模板还原能力另验，不能用生图成功证明HTML已还原。</p>' + ''.join(cards) + '<p><a href="native-http-requests.json">真实上传/提交/查询记录（无密钥）</a> · <a href="production-tasks.json">生产任务与设计key</a> · <a href="design-file-checks.json">图片实际尺寸和哈希</a></p></main></html>'
    (out / 'index.html').write_bytes(html.encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--continue-unrequested', action='store_true')
    parser.add_argument('--model', default='gpt-image-2.5-flare-vip')
    parser.add_argument('--index-only', action='store_true')
    parser.add_argument('--build-html', action='store_true')
    args = parser.parse_args()
    if args.index_only:
        build_design_index(args.out)
        return
    if not args.live:
        emit('dry_run', pages=5, stage='actual_design', paid_calls=False)
        return
    out = args.out.resolve()
    if out.exists() and not (args.continue_unrequested or args.build_html):
        raise ValueError('REVALIDATION_DIRECTORY_EXISTS; do not repeat paid requests')
    settings = settings_readonly(ROOT / 'data/projects.db')
    for key in ('llm_api_key', 'llm_model', 'image_api_key', 'image_model'):
        if not settings.get(key):
            raise ValueError('REVALIDATION_MODEL_NOT_READY')
    out.mkdir(parents=True, exist_ok=True)
    run = out / 'runs/token-visual-revalidation'
    os.environ['PPT_STUDIO_DB_PATH'] = str(out / 'experiment.db')
    os.environ['PPT_STUDIO_RUNS_DIR'] = str(out / 'runs')
    from database import init_db, SessionLocal, Project, LocalJob
    from html_build_snapshot import digest, json_bytes
    from html_workflow_jobs import HtmlWorkflowJobs
    from html_visual_review_service import HtmlReviewDependencies
    from html_image_provider import configured_image
    from html_task_store import task_view, _job
    from project_model_binding_service import FrozenModel, FrozenProjectModels
    import json_llm_service as llm
    import ai_provider_service as image_transport
    init_db()
    course = json.loads((ROOT / 'checks/fixtures/html/token-five-page.json').read_text(encoding='utf-8'))
    for slide, visual in zip(course['slides'], VISUALS):
        slide['visual_groups'][0]['description'] = (visual + '必须包含一个新独立image_asset并走设计图审阅；'
            '由实际注册能力选择适合的含图片模板，不预选纯文字data-relation。新主体锚点仅使用focus；focus是内部定位字段，不得作为上屏文字或标签。'
            '屏幕仅保留短而准确的关键事实，详细解释在旁白；资产不承载最终中文正文。')
        slide['visual_groups'][0].pop('available_assets', None)
    write(out / 'course-input.json', course)
    write(run / 'planning/visual_contract.json', course)
    harness = Path(__file__).read_bytes()
    write(out / 'experiment-policy.json', {'purpose': 'user-authorized full visual process revalidation',
        'previous_experiment': 's08-token-course-20261012; all unknown requests preserved',
        'design_direction': DESIGN_DIRECTION, 'harness_sha256': hashlib.sha256(harness).hexdigest(),
        'image_generation_enabled': True, 'supplied_assets': False,
        'design_approval': 'pending actual user review', 'formal_output': False})
    archive = out / 'harness-sources' / (hashlib.sha256(harness).hexdigest() + '.py')
    archive.parent.mkdir(exist_ok=True); archive.write_bytes(harness)
    text = FrozenModel(settings.get('llm_provider') or 'openai_compatible', settings['llm_model'],
        settings['llm_base_url'], settings['llm_api_key'], 'global_read_only', None,
        digest(json_bytes({'model': settings['llm_model'], 'thinking': 'disabled', 'timeout': 180})), max_tokens=4096)
    image = FrozenModel(settings.get('image_provider') or 'openai_compatible', settings['image_model'],
        settings['image_base_url'], settings['image_api_key'], 'global_read_only', None,
        digest(json_bytes({'model': settings['image_model'], 'endpoint': settings['image_base_url']})))
    if args.model == 'gpt-image-2.5-flare-vip':
        from project_config_runtime import _api_key_from_secrets
        packages = json.loads((ROOT / 'data/creation_configs.json').read_text(encoding='utf-8'))['packages']
        package = next(p for p in packages.values() if p['name'] == '默认创作配置')
        configuration = package['versions'][str(package['latest_version'])]
        connection_id = configuration['payload']['model_bindings']['image_generation']['connection_id']
        connections = json.loads((ROOT / 'data/model_connections.json').read_text(encoding='utf-8'))['connections']
        connection = connections[connection_id]
        revision = next(r for r in connection['revisions'] if r['revision'] == connection['current_revision'])
        credentials = json.loads((ROOT / 'data/credentials.json').read_text(encoding='utf-8'))['credentials']
        secret = next(v for v in credentials.values() if v['credential_ref'] == revision['credential_ref'])
        image = FrozenModel('toapis', args.model, 'https://api.toapis.cn',
            _api_key_from_secrets(secret['secret_values']), 'default_creation_config_read_only', connection_id,
            digest(json_bytes({'model': args.model, 'endpoint': 'https://api.toapis.cn', 'quality': 'low', 'resolution': '1k'})))
        write(out / 'connection-correction.json', {'old_source': 'legacy global settings',
            'new_source': 'user-specified Flare model; supplied credential matches default creation configuration', 'package_id': package['id'],
            'package_version': package['latest_version'], 'image': image.summary(),
            'original_unknown_request_preserved': True})
    models = FrozenProjectModels(0, text, image)
    calls = json.loads((out / 'calls.json').read_text(encoding='utf-8')) if args.continue_unrequested or args.build_html else []
    # Native ToAPIs uses httpx directly. Record physical upload/submit/poll
    # requests separately from SDK calls; never persist Authorization or URLs.
    import httpx
    native_path = out / 'native-http-requests.json'
    native_requests = json.loads(native_path.read_text(encoding='utf-8')) if (args.continue_unrequested or args.build_html) and native_path.exists() else []
    httpx_original_request = httpx.Client.request
    def native_request(client, method, url, **kwargs):
        parsed = httpx.URL(url)
        if 'toapis.' not in parsed.host:
            return httpx_original_request(client, method, url, **kwargs)
        payload = kwargs.get('json') or {}
        record = {'method': method, 'path': parsed.path, 'state': 'intent',
            'parameters': {key: payload[key] for key in ('model', 'size', 'quality', 'resolution', 'n', 'background') if key in payload},
            'reference_count': len(payload.get('reference_images', [])), 'cost': None}
        native_requests.append(record); write(out / 'native-http-requests.json', native_requests)
        start = time.monotonic()
        try:
            response = httpx_original_request(client, method, url, **kwargs)
            record.update(state='returned', http_status=response.status_code)
            try:
                body = response.json()
                if isinstance(body, dict):
                    for key in ('id', 'status', 'usage'):
                        if key in body: record[key] = body[key]
                    if isinstance(body.get('result'), dict) and body['result'].get('usage'):
                        record['usage'] = body['result']['usage']
                    if response.status_code >= 400:
                        error = body.get('error', body.get('message'))
                        message = error.get('message', '') if isinstance(error, dict) else str(error or '')
                        record['error_message'] = message.replace(image.api_key, '[REDACTED]')[:500]
            except ValueError:
                pass
            return response
        except Exception as error:
            error_message = str(error).replace(image.api_key, '[REDACTED]')
            record.update(state='unknown', error_type=type(error).__name__,
                error_message=error_message[:500], response_received=False)
            raise
        finally:
            record['seconds'] = round(time.monotonic() - start, 3)
            write(out / 'native-http-requests.json', native_requests)
    httpx.Client.request = native_request
    def instrument(factory, kind):
        def create_client(**kwargs):
            client = factory(**kwargs)
            methods = [(client.chat.completions, 'create')] if kind == 'text' else [(client.images, 'edit'), (client.images, 'generate')]
            for owner, name in methods:
                original = getattr(owner, name)
                def call(_original=original, _name=name, **request):
                    if len(calls) >= 20:
                        raise ValueError('REVALIDATION_CALL_BUDGET')
                    if kind == 'text':
                        if text.model != 'doubao-seed-2-1-turbo-260628':
                            raise ValueError('REVALIDATION_TEXT_OPTIONS_UNVERIFIED')
                        request['extra_body'] = {'thinking': {'type': 'disabled'}}
                    record = {'kind': kind, 'method': _name, 'state': 'intent', 'cost': None,
                        'input_sha256': digest(json_bytes(request.get('messages', request.get('prompt', '')))),
                        'reference_count': len(request.get('image', [])) if isinstance(request.get('image'), list) else 0}
                    calls.append(record); write(out / 'calls.json', calls)
                    started = time.monotonic()
                    try:
                        response = _original(**request)
                        record['state'] = 'returned'
                        usage = getattr(response, 'usage', None)
                        record['usage'] = usage.model_dump() if usage and hasattr(usage, 'model_dump') else None
                        return response
                    except Exception as error:
                        record['state'] = 'unknown'
                        record['error_type'] = type(error).__name__
                        record['http_status'] = getattr(error, 'status_code', None)
                        raise
                    finally:
                        record['seconds'] = round(time.monotonic() - started, 3)
                        write(out / 'calls.json', calls)
                setattr(owner, name, call)
            return client
        return create_client
    llm.get_openai_client = instrument(llm.get_openai_client, 'text')
    image_transport.get_openai_client = instrument(image_transport.get_openai_client, 'image')
    generator = partial(llm.generate_json_with_configured_llm, temperature=0, request_timeout=180,
        max_tokens_default=4096, max_tokens_limit=4096)
    class Immediate:
        def submit(self, function, *values):
            return function(*values)
    jobs = HtmlWorkflowJobs(SessionLocal, HtmlReviewDependencies(ROOT, generator), provider=configured_image,
        executor=Immediate(), freeze_models=lambda _: models)
    db = SessionLocal()
    try:
        project = db.get(Project, run.name)
        if project is None:
            project = Project(id=run.name, name=course['title'], account_id='default', visual_backend='html', run_dir=str(run))
            db.add(project); db.commit()
        results = [task_view(job, run) for job in db.query(LocalJob).filter(LocalJob.project_id == project.id).all()]
        requested = {t['slide_id'] for t in results}
        if args.build_html:
            from html_production_service import produce_scene
            from html_design_candidates import candidate_directory
            from html_reference_package import verify_package, design_prompt
            original_tasks = json.loads((out / 'production-tasks.json').read_text(encoding='utf-8'))
            builds = []
            for slide in course['slides']:
                if (run / f"planning/html_visual/scene-{slide['slide_id']}.json").exists():
                    emit('original_saved_scene_preserved', slide=slide['slide_id']); continue
                old = next(t for t in original_tasks if t['slide_id'] == slide['slide_id'])
                old_key = old['result']['design']['key']
                record = json.loads((candidate_directory(run, slide['slide_id'], old_key) / 'candidate.json').read_text(encoding='utf-8'))
                audits = sorted((run / 'planning/html_visual/review').glob(f"html_scene_plan_{slide['slide_id']}-round-*.json"))
                audit = json.loads(audits[-1].read_text(encoding='utf-8'))
                def cached_plan(**request):
                    frozen_prompts = audit['prompts']
                    if request['system_prompt'] != frozen_prompts['system_prompt'] or request['schema_hint'] != frozen_prompts['schema_hint']:
                        raise ValueError('REVALIDATION_ORIGINAL_PROMPT_CHANGED')
                    try:
                        requested_facts = json.loads(request['user_prompt'])
                        frozen_facts = json.loads(frozen_prompts['user_prompt'])
                    except (TypeError, json.JSONDecodeError) as error:
                        raise ValueError('REVALIDATION_ORIGINAL_PROMPT_CHANGED') from error
                    if requested_facts != frozen_facts:
                        raise ValueError('REVALIDATION_ORIGINAL_PROMPT_CHANGED')
                    return audit['response']
                original_request_key = record['candidate']['request_key']
                original_request_path = (run / 'planning/html_visual/candidates' / slide['slide_id']
                    / f"design-{original_request_key}.request.json")
                design_request_receipt = json.loads(original_request_path.read_text(encoding='utf-8'))
                original_design_path = candidate_directory(run, slide['slide_id'], old_key) / 'design-reference.png'
                original_package = verify_package(run / record['reference_package'])
                original_prompt = design_prompt(original_package, instruction=DESIGN_DIRECTION)
                original_reference_hashes = [hashlib.sha256(Path(path).read_bytes()).hexdigest()
                    for path in original_package['references']]
                if (hashlib.sha256(original_design_path.read_bytes()).hexdigest() != record['image_sha256']
                        or design_request_receipt.get('response_sha256') != record['image_sha256']
                        or design_request_receipt.get('reference_sha256') != original_reference_hashes
                        or record['model_summary'] != models.summary()):
                    raise ValueError('REVALIDATION_ORIGINAL_DESIGN_EVIDENCE_INVALID')
                reuse_proof = {'original_request_key': original_request_key,
                    'original_image_sha256': record['image_sha256'],
                    'original_prompt_sha256': hashlib.sha256(original_prompt.encode('utf-8')).hexdigest(),
                    'original_reference_sha256': original_reference_hashes,
                    'model_summary_unchanged': True, 'provider_called_again': False}
                def reuse_exact_design_response(prompt, *, size, reference_paths, transparent_background=False, **unused_options):
                    reference_hashes = [hashlib.sha256(Path(path).read_bytes()).hexdigest()
                        for path in reference_paths]
                    if (prompt != original_prompt or size != design_request_receipt.get('requested_size')
                            or transparent_background != design_request_receipt.get('transparent_background')
                            or reference_hashes != original_reference_hashes):
                        raise ValueError('REVALIDATION_DESIGN_INPUT_CHANGED')
                    reuse_proof['current_prompt_sha256'] = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
                    reuse_proof['current_reference_sha256'] = reference_hashes
                    reuse_proof['exact_model_input_reused'] = True
                    return original_design_path.read_bytes()
                # Regenerate only the local candidate identity after compatible
                # source/revision changes, reusing exact original responses/PNG.
                current = produce_scene(slide, run_dir=run, deps=HtmlReviewDependencies(ROOT, cached_plan),
                    provider=reuse_exact_design_response, model_summary=record['model_summary'],
                    options={'design_instruction': DESIGN_DIRECTION})
                current_record = json.loads((candidate_directory(run, slide['slide_id'], current['design']['key'])
                    / 'candidate.json').read_text(encoding='utf-8'))
                if (current_record['plan'] != record['plan'] or current_record['brief'] != record['brief']
                        or current_record['image_sha256'] != record['image_sha256']):
                    raise ValueError('REVALIDATION_REUSED_DESIGN_CONTENT_MISMATCH')
                current_receipt_path = (run / 'planning/html_visual/candidates' / slide['slide_id']
                    / f"design-{current_record['candidate']['request_key']}.request.json")
                current_receipt = json.loads(current_receipt_path.read_text(encoding='utf-8'))
                current_receipt.update(provider_boundary_called=False,
                    response_reused_from_request_key=original_request_key,
                    exact_prompt_and_reference_hashes_verified=True)
                write(current_receipt_path, current_receipt)
                reuse_proof['current_request_key'] = current_record['candidate']['request_key']
                reuse_proof['candidate_plan_unchanged'] = True
                reuse_proof['candidate_brief_unchanged'] = True
                reuse_proof['image_response_unchanged'] = True
                write(out / 'design-revalidation' / f"{slide['slide_id']}.json", {
                    'original_key': old_key, 'current': current, 'additional_model_calls': 0,
                    'design_response_reuse': reuse_proof,
                    'authorization': 'user explicitly said continue after five design images'})
                emit('asset_and_html_started', slide=slide['slide_id'])
                task = jobs.submit(db, project, slide, options={'design_candidate_key': current['design']['key']})
                db.expire_all(); task = task_view(_job(db, task['id']), run)
                builds.append(task); write(out / 'html-production-tasks.json', builds)
                emit('asset_and_html_result', slide=slide['slide_id'], status=task['status'])
                if task['status'] != 'succeeded': break
            return
        for slide in course['slides']:
            if slide['slide_id'] in requested:
                emit('original_request_preserved', slide=slide['slide_id']); continue
            emit('actual_design_started', slide=slide['slide_id'])
            task = jobs.submit(db, project, slide, options={'design_instruction': DESIGN_DIRECTION})
            db.expire_all(); task = task_view(_job(db, task['id']), run)
            results.append(task); write(out / 'production-tasks.json', results)
            emit('actual_design_result', slide=slide['slide_id'], status=task['status'], task_stage=task.get('result', {}).get('stage') if task.get('result') else None)
            if task['status'] != 'succeeded':
                break
        write(out / 'summary.json', {'models': models.summary(), 'pages_requested': len(results),
            'design_candidates': sum(bool(t.get('result', {}).get('design')) for t in results if t.get('result')),
            'html_generated': 0, 'user_approval': False, 'cost': None})
    finally:
        db.close()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        emit('revalidation_stopped', code='REVALIDATION_FAILED; inspect isolated task evidence')
        raise SystemExit(1)
