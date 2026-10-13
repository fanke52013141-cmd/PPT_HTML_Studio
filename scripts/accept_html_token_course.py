"""S08 real Token course, isolated settings reads and review-only deliverables.

Each paid stage is explicit. No author/voice approval or formal publication.
"""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(data);temporary.replace(path)


def settings_readonly(path):
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as db:
        return dict(db.execute('SELECT key,value FROM settings'))


def emit(stage,**facts):
    print(json.dumps({'stage':stage,**facts},ensure_ascii=False),flush=True)


def seed_assets(run):
    from html_asset_service import inspect_asset_bytes
    assets=[]
    for identity,source in [('token-brain','brain-v1.png'),('token-core','core-v1.png')]:
        original=ROOT/'html_engine/courses/token/visual-v2/assets'/source
        payload=original.read_bytes();facts=inspect_asset_bytes(payload)
        destination=run/'planning/html_visual/assets'/source
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(payload)
        assets.append({'id':identity,'version':'0.1.0','file':destination.relative_to(run).as_posix(),
            'sha256':hashlib.sha256(payload).hexdigest(),'size':{'width':facts['width'],'height':facts['height']},
            'alpha_bbox':facts['alpha_bbox'],'has_transparency':facts['has_transparency'],
            'anchors':[{'id':'focus','x':facts['width']//2,'y':facts['height']//2}],
            'source':'existing_token_visual_v2_asset; reused exact bytes'})
    write(run/'planning/html_visual/resources.json',{'assets':assets})


def generate(output,run,course,settings,*,continue_pending=False,disable_thinking=False):
    from database import init_db,SessionLocal,Project,LocalJob
    from project_model_binding_service import FrozenModel,FrozenProjectModels
    from html_visual_review_service import HtmlReviewDependencies
    from html_workflow_jobs import HtmlWorkflowJobs
    from html_task_store import task_view,_job
    import json_llm_service as llm
    from html_build_snapshot import digest,json_bytes
    init_db()
    harness=Path(__file__).read_bytes();harness_hash=hashlib.sha256(harness).hexdigest()
    archive=output/'harness-sources'/f'{harness_hash}.py';archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(harness)
    binding=FrozenModel(settings.get('llm_provider') or 'openai_compatible',settings['llm_model'],settings['llm_base_url'],settings['llm_api_key'],'global_read_only',None,
        digest(json_bytes({'model':settings['llm_model'],'endpoint':settings['llm_base_url'],'max_tokens':4096,'disable_thinking':disable_thinking})),max_tokens=4096)
    frozen=FrozenProjectModels(0,binding,FrozenModel('reuse_only','existing_assets',None,'','explicit_existing',None,'existing',error='New images disabled for this experiment'))
    attempts=json.loads((output/'http-attempts.json').read_text(encoding='utf-8')) if (output/'http-attempts.json').exists() else []
    factory=llm.get_openai_client
    def client_factory(**kwargs):
        client=factory(**kwargs);original=client.chat.completions.create
        def create(**request):
            if disable_thinking:
                if settings['llm_model']!='doubao-seed-2-1-turbo-260628':raise ValueError('S08_THINKING_MODE_NOT_VERIFIED_FOR_MODEL')
                request['extra_body']={'thinking':{'type':'disabled'}}
            if len(attempts)>=30:raise ValueError('S08_HTTP_BUDGET_EXHAUSTED')
            record={'attempt':len(attempts)+1,'success':False,'usage':None,
                    'messages_sha256':digest(json_bytes(request['messages'])),'vendor_options':request.get('extra_body'),
                    'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
            attempts.append(record);write(output/'http-attempts.json',attempts);start=time.monotonic()
            try:
                response=original(**request);record['success']=True
                if response.usage:record['usage']={name:getattr(response.usage,name,None) for name in ('prompt_tokens','completion_tokens','total_tokens')}
                return response
            finally:
                record['elapsed_seconds']=round(time.monotonic()-start,3);write(output/'http-attempts.json',attempts)
        client.chat.completions.create=create;return client
    llm.get_openai_client=client_factory
    generator=partial(llm.generate_json_with_configured_llm,temperature=0,request_timeout=180,max_tokens_default=4096,max_tokens_limit=4096)
    def no_image(*args,**kwargs):raise ValueError('S08_NEW_IMAGE_NOT_AUTHORED')
    class Immediate:
        def submit(self,function,*args):return function(*args)
    deps=HtmlReviewDependencies(ROOT,generator)
    jobs=HtmlWorkflowJobs(SessionLocal,deps,provider=no_image,executor=Immediate(),freeze_models=lambda _:frozen)
    if not continue_pending:
        seed_assets(run);write(run/'planning/visual_contract.json',course)
    db=SessionLocal()
    try:
        project=db.get(Project,run.name)
        if project is None:
            project=Project(id=run.name,name=course['title'],account_id='default',visual_backend='html',run_dir=str(run))
            db.add(project);db.commit()
        results=[task_view(job,run) for job in db.query(LocalJob).filter(LocalJob.project_id==project.id,LocalJob.job_type=='html_plan_generate').order_by(LocalJob.created_at).all()] if continue_pending else []
        requested={task['slide_id'] for task in results}
        for slide in course['slides']:
            if slide['slide_id'] in requested:
                emit('original_request_preserved',slide=slide['slide_id']);continue
            emit('generating',slide=slide['slide_id'])
            task=jobs.submit(db,project,slide);db.expire_all()
            task=task_view(_job(db,task['id']),run)
            results.append(task);write(output/'production-tasks.json',results)
            if task['status']!='succeeded':raise ValueError('S08_PRODUCTION_FAILED:'+slide['slide_id'])
            emit('generated',slide=slide['slide_id'],job=task['id'],status=task['status'])
        write(output/'generation-summary.json',{'model':binding.summary(),'vendor_options':{'thinking':{'type':'disabled'}} if disable_thinking else None,'http_attempts':len(attempts),'cost':None,'task_ids':[t['id'] for t in results],'human_scene_patches':0,'completed_pages':sum(t['status']=='succeeded' for t in results),'total_pages':len(course['slides'])})
    finally:db.close()


def review_pages(output,run,course):
    from html_visual_store import _read_revision
    from html_build_snapshot import create_render_snapshot
    from html_snapshot_review import review_snapshot
    results=[]
    for slide in course['slides']:
        identity=slide['slide_id'];emit('qa',slide=identity)
        if not (run/f'planning/html_visual/scene-{identity}.json').is_file():
            results.append({'slide_id':identity,'title':slide['title'],'status':'production_pending'});write(output/'page-reviews.json',results);continue
        snapshot=create_render_snapshot(run,identity,repo_root=ROOT,expected_revision=_read_revision(run)['revision'])
        static=review_snapshot(snapshot['path'],output_dir=output/'qa'/identity)
        temporal=review_snapshot(snapshot['path'],output_dir=output/'qa'/identity,temporal={'sampling_mode':'output_frames','fps':30,'overlap_policy':'registered'})
        result={'slide_id':identity,'title':slide['title'],'snapshot':snapshot,'html':static['html'],
                'static':static,'temporal':temporal}
        results.append(result);write(output/'page-reviews.json',results)
        emit('qa_complete',slide=identity,static=static['report']['checks']['engineering'],temporal=temporal['report']['checks']['engineering'])


def synthesize(output,run,course,settings):
    from tts_provider_service import TtsProviderDependencies,configure_tts_provider_dependencies,normalize_tts_provider,configured_tts_api_key,configured_tts_secret_key,provider_tts_command,provider_tts_environment
    from scripts.media_tools import resolve_media_tool
    configure_tts_provider_dependencies(TtsProviderDependencies(get_setting=lambda key,default=None:settings.get(key,default),write_project_log=lambda *args,**kwargs:None))
    provider=normalize_tts_provider(settings.get('tts_provider'));key=configured_tts_api_key(provider);secret=configured_tts_secret_key(provider)
    if not key:raise ValueError('S08_TTS_CREDENTIAL_MISSING')
    records=json.loads((output/'audio-requests.json').read_text(encoding='utf-8')) if (output/'audio-requests.json').exists() else []
    if records:raise ValueError('S08_AUDIO_STAGE_ALREADY_REQUESTED; inspect outcomes before retry')
    env=provider_tts_environment(key,secret)
    for tool in ['ffmpeg','ffprobe']:env[tool.upper()+'_BIN']=str(resolve_media_tool(tool,ROOT))
    for slide in course['slides']:
        identity=slide['slide_id'];folder=run/'slides'/identity;folder.mkdir(parents=True,exist_ok=True)
        text='\n'.join(beat['spoken_text'] for beat in slide['narration_beats'])
        (folder/'tts_text.txt').write_bytes(text.encode('utf-8'))
        record={'slide_id':identity,'state':'intent','input_sha256':hashlib.sha256(text.encode()).hexdigest(),'provider':provider,'model':settings.get('tts_model'),'cost':None}
        records.append(record);write(output/'audio-requests.json',records);emit('tts',slide=identity)
        command=provider_tts_command(provider=provider,text_file=str(folder/'tts_text.txt'),out_audio=str(folder/'voice.mp3'),out_meta=str(folder/'tts_metadata.json'),out_srt=str(folder/'subtitles.srt'),out_timeline=str(folder/'audio_timeline.json'),slide_id=identity,
            endpoint=settings.get('tts_endpoint',''),region=settings.get('tts_region',''),model=settings.get('tts_model',''),voice_id=settings.get('tts_voice_id',''),clone_voice_id=settings.get('tts_clone_voice_id',''),provider_extra=settings.get('tts_provider_extra',''),speed=settings.get('tts_speed','1'),volume=settings.get('tts_volume','1'),pitch=settings.get('tts_pitch','0'))
        try:
            response=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=300)
            if response.returncode:raise ValueError('S08_TTS_FAILED')
            record['state']='returned';record['audio_sha256']=hashlib.sha256((folder/'voice.mp3').read_bytes()).hexdigest()
        except Exception:
            record['state']='unknown';write(output/'audio-requests.json',records);raise
        write(output/'audio-requests.json',records);emit('tts_complete',slide=identity)


def audio_review(output,run,course):
    from narration_audio_service import NarrationAudioDependencies,configure_narration_audio_dependencies,rewrite_audio_timeline_by_beats
    from scripts.media_tools import probe_media_duration_sec
    from visual_contract_service import dedupe_narration_beats,read_contract_slide_ids
    from pipeline_lifecycle import read_json_file,write_json_atomic
    from html_audio_binder import bind_scene_to_audio
    from html_visual_store import _read_revision
    from html_scene_repair import evidence
    configure_narration_audio_dependencies(NarrationAudioDependencies(dedupe_narration_beats,probe_media_duration_sec,read_contract_slide_ids,read_json_file,write_json_atomic,ROOT))
    results=[]
    for slide in course['slides']:
        identity=slide['slide_id'];folder=run/'slides'/identity
        if not (run/f'planning/html_visual/scene-{identity}.json').is_file():
            results.append({'slide_id':identity,'status':'production_pending','audio':str(folder/'voice.mp3')});write(output/'audio-review.json',results);continue
        rewrite_audio_timeline_by_beats(str(folder/'audio_timeline.json'),identity,slide['narration_beats'])
        timeline=json.loads((folder/'audio_timeline.json').read_text(encoding='utf-8'))
        scene=json.loads((run/f'planning/html_visual/scene-{identity}.json').read_text(encoding='utf-8'))
        binding=json.loads((run/f'planning/html_visual/binding-{identity}.json').read_text(encoding='utf-8'))
        try:
            bound=bind_scene_to_audio(scene,timeline,binding)
            destination=output/'audio-review'/identity;destination.mkdir(parents=True,exist_ok=True)
            write(destination/'bound-scene.json',bound)
            report=evidence(run,identity,{'expected_revision':_read_revision(run)['revision'],'sampling_mode':'output_frames','fps':30,'overlap_policy':'registered'},preview={'scene':bound,'clock':'unconfirmed_audio_review'})
            result={'slide_id':identity,'status':'review_only','scene':str(destination/'bound-scene.json'),'audio':str(folder/'voice.mp3'),'timeline_source':timeline.get('timing_source'),'qa':report,'audio_confirmation':'pending_user_listening'}
        except Exception as exc:
            result={'slide_id':identity,'status':'needs_alignment','code':getattr(exc,'code',type(exc).__name__),'audio':str(folder/'voice.mp3'),'audio_confirmation':'pending_user_listening'}
        results.append(result);write(output/'audio-review.json',results);emit('audio_review',slide=identity,status=result['status'])


def render_review(output,run,course):
    from scripts.media_tools import resolve_media_tool
    from html_pptx_snapshot import build_snapshot_pptx
    from html_build_snapshot import create_render_snapshot
    from html_snapshot_review import review_snapshot
    import shutil
    reviews=json.loads((output/'page-reviews.json').read_text(encoding='utf-8'))
    reviews=[item for item in reviews if item.get('snapshot')]
    if not reviews:raise ValueError('S08_REVIEW_SCENES_MISSING')
    images=[next(Path(r['static']['report_path']).parent.glob('end-frame.png')) for r in reviews]
    prefix='token-review-only' if len(reviews)==len(course['slides']) else 'token-partial-review-only'
    pptx=output/(prefix+'.pptx')
    build_snapshot_pptx([{'timeMs':0,'label':r['slide_id']+':review_only'} for r in reviews],images,pptx)
    audio=json.loads((output/'audio-review.json').read_text(encoding='utf-8'))
    segments=[];env=os.environ.copy();env['HPS_HTML_RESOURCES']=str(run/'planning/html_visual/resources.json')
    for tool in ['ffmpeg','ffprobe']:env[tool.upper()+'_BIN']=str(resolve_media_tool(tool,ROOT))
    for item in audio:
        if item['status']=='production_pending':continue
        if item['status']!='review_only' or not item['qa']['passed']:raise ValueError('S08_AUDIO_OR_DYNAMIC_REVIEW_BLOCKED')
        target=output/'audio-review'/item['slide_id']/'review-only.mp4';emit('render_review',slide=item['slide_id'])
        # Separate review inputs freeze the actual bound scene. No confirmation
        # or author source is changed, and formal export gates are not invoked.
        review_run=output/'bound-review-inputs'/item['slide_id']
        scene_dir=review_run/'planning/html_visual';scene_dir.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(item['scene'],scene_dir/f"scene-{item['slide_id']}.json")
        resource=run/'planning/html_visual/resources.json'
        shutil.copyfile(resource,scene_dir/'resources.json')
        for asset in json.loads(resource.read_text(encoding='utf-8'))['assets']:
            destination=review_run/asset['file'];destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(run/asset['file'],destination)
        snapshot=create_render_snapshot(review_run,item['slide_id'],repo_root=ROOT)
        check=review_snapshot(snapshot['path'],output_dir=output/'bound-review-qa'/item['slide_id'],temporal={'sampling_mode':'output_frames','fps':30,'overlap_policy':'registered'})
        if not check['validation']['valid'] or check['report']['checks']['engineering']!='passed':raise ValueError('S08_BOUND_SNAPSHOT_QA_FAILED')
        write(output/'audio-review'/item['slide_id']/'render-input.json',{'snapshot':snapshot,'qa':check,'clock_semantics':'unconfirmed_audio_review','approval_granted':False})
        env['HPS_HTML_SNAPSHOT']=snapshot['path']
        response=subprocess.run(['node',str(ROOT/'html_engine/tools/export-slide-video.cjs'),str(Path(snapshot['path'])/'input/scene.json'),item['audio'],str(target),'30'],cwd=ROOT,env=env,capture_output=True,timeout=600)
        if response.returncode:raise ValueError('S08_REVIEW_RENDER_FAILED')
        segments.append(target)
    concat=output/'review-concat.txt';concat.write_bytes(''.join("file '"+str(p).replace('\\','/').replace("'","'\\''")+"'\n" for p in segments).encode('utf-8'))
    video=output/(prefix+'.mp4')
    response=subprocess.run([env['FFMPEG_BIN'],'-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(video)],capture_output=True,timeout=90)
    decode=subprocess.run([env['FFMPEG_BIN'],'-v','error','-i',str(video),'-map','0:v','-map','0:a','-f','null','-'],capture_output=True,timeout=180) if not response.returncode else response
    if response.returncode or decode.returncode:raise ValueError('S08_REVIEW_MEDIA_FAILED')
    write(output/'media-review.json',{'status':'review_only' if len(reviews)==len(course['slides']) else 'partial_review_only','pages':[r['slide_id'] for r in reviews],'expected_pages':len(course['slides']),'video':str(video),'pptx':str(pptx),'complete_decode':'passed','visual_approval':'pending_user_review','audio_confirmation':'pending_user_listening','formally_published':False})


def build_review_index(output,run,course):
    from html import escape
    output=Path(output);run=Path(run)
    def link(path):return escape(os.path.relpath(Path(path),output).replace('\\','/'),quote=True)
    task_file=output/'html-production-tasks.json'
    if not task_file.exists():task_file=output/'production-tasks.json'
    tasks={t.get('slide_id') or (t.get('result') or {}).get('scene',{}).get('id'):t for t in json.loads(task_file.read_text(encoding='utf-8'))}
    reviews={r['slide_id']:r for r in json.loads((output/'page-reviews.json').read_text(encoding='utf-8'))}
    audio={r['slide_id']:r for r in json.loads((output/'audio-review.json').read_text(encoding='utf-8'))} if (output/'audio-review.json').exists() else {}
    resource_file=run/'planning/html_visual/resources.json'
    resources={a['id']:a for a in json.loads(resource_file.read_text(encoding='utf-8')).get('assets',[])} if resource_file.exists() else {}
    cards=[]
    for slide in course['slides']:
        identity=slide['slide_id'];task=tasks.get(identity,{});result=task.get('result') or {};review=reviews.get(identity,{});audio_item=audio.get(identity,{})
        design_key=result.get('design_candidate_key');reference=run/'planning/html_visual/candidates'/identity/'designs'/str(design_key)/'design-reference.png' if design_key else None
        scene_path=run/'planning/html_visual'/f'scene-{identity}.json';asset_path=None
        if scene_path.exists():
            scene=json.loads(scene_path.read_text(encoding='utf-8'))
            asset_ref=next((n.get('assetRef',{}).get('id') for n in scene.get('nodes',[]) if n.get('type')=='image'),None)
            if asset_ref in resources:asset_path=run/resources[asset_ref]['file']
        screenshot=Path(review['static']['report_path']).parent/'end-frame.png' if review.get('static',{}).get('report_path') else None
        qa_static=(review.get('static') or {}).get('report',{}).get('checks',{}).get('engineering','未运行')
        qa_temporal=(review.get('temporal') or {}).get('report',{}).get('checks',{}).get('engineering','未运行')
        page=f'<article><header><div><span class="eyebrow">{escape(identity.upper())}</span><h2>{escape(slide["title"])}</h2></div><span class="pill">HTML：{escape(task.get("status","缺失"))}</span></header>'
        page+=f'<p class="checks">静态 QA：{escape(qa_static)} · 30 fps 输出帧 QA：{escape(qa_temporal)} · 音频：{escape(audio_item.get("status","未绑定"))}</p>'
        page+='<div class="compare">'
        page+='<figure><figcaption>图像模型设计参考</figcaption>'+ (f'<a href="{link(reference)}"><img src="{link(reference)}" alt="{escape(identity)} 设计参考"></a>' if reference and reference.exists() else '<p>未找到设计参考</p>')+'</figure>'
        page+='<figure><figcaption>实际 HTML 渲染终态</figcaption>'+ (f'<a href="{link(screenshot)}"><img src="{link(screenshot)}" alt="{escape(identity)} 实际渲染"></a>' if screenshot and screenshot.exists() else '<p>未找到终态截图</p>')+'</figure></div>'
        if asset_path and asset_path.exists():page+=f'<p><a href="{link(asset_path)}">查看本页独立生成插图</a></p>'
        if review.get('html'):page+=f'<p><a href="{link(review["html"])}">打开本页实际 HTML 预览</a></p>'
        if audio_item.get('audio'):page+=f'<audio controls preload="none" src="{link(audio_item["audio"])}"></audio><p class="muted">配音仅完成绑定与工程校验，尚未人工听审。</p>'
        page+='</article>';cards.append(page)
    media=json.loads((output/'media-review.json').read_text(encoding='utf-8')) if (output/'media-review.json').exists() else {}
    video=f'<video controls preload="metadata" src="{link(media["video"])}"></video><p><a href="{link(media["pptx"])}">下载五页截图版 PPTX（审阅用）</a></p>' if media.get('video') and Path(media['video']).exists() else ''
    media_status=media.get('complete_decode','未生成')
    total=len(course['slides'])
    produced=sum(tasks.get(s['slide_id'],{}).get('status')=='succeeded' for s in course['slides'])
    static_passed=sum((r.get('static') or {}).get('report',{}).get('checks',{}).get('engineering')=='passed' for r in reviews.values())
    temporal_passed=sum((r.get('temporal') or {}).get('report',{}).get('checks',{}).get('engineering')=='passed' for r in reviews.values())
    bound=sum(a.get('status')=='review_only' for a in audio.values())
    metrics=''.join(f'<span class="metric">{escape(label)}：{value} / {total}</span>' for label,value in [('HTML 生产',produced),('静态 QA',static_passed),('30 fps QA',temporal_passed),('配音绑定',bound)])
    metrics+=f'<span class="metric">视频解码：{escape(media_status)}</span>'
    sheet=output/'qa/five-page-contact-sheet.png'
    evidence=['summary.json','handoff.md','html-production-tasks.json','page-reviews.json','audio-review.json','audio-reuse.json','media-review.json','native-http-requests.json']
    links=' · '.join(f'<a href="{link(output/name)}">{escape(name)}</a>' for name in evidence if (output/name).exists())
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Token 科普课程 · S08 审阅</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f4f5f7;color:#222;font:15px/1.65 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1240px;margin:auto;padding:36px 28px 72px}h1{font-size:34px;line-height:1.2;margin:0}h2{font-size:23px;margin:0}p{margin:12px 0}.hero{padding:28px 30px;background:#fff;border-radius:18px}.flag{margin-top:20px;padding:17px 20px;background:#fff2d8;border-radius:12px}.metrics{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}.pill,.metric{background:#f0f1f2;border-radius:999px;padding:7px 12px;font-size:13px}.contact{width:100%;height:auto;margin:22px 0;border-radius:12px}article{background:#fff;margin:22px 0;padding:24px;border-radius:16px}article header{display:flex;align-items:center;justify-content:space-between;gap:16px}.eyebrow{color:#666;font-size:12px;letter-spacing:.08em}.checks,.muted{color:#666;font-size:13px}.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}figure{margin:0;min-width:0}figcaption{font-size:13px;color:#555;margin:0 0 8px}figure img{display:block;width:100%;height:auto;border:1px solid #e8e8e8;border-radius:10px}video{display:block;width:100%;margin-top:18px;border-radius:12px}audio{width:100%;margin-top:6px}a{color:#2355a4}section.evidence{background:#fff;padding:24px;border-radius:16px;margin-top:24px}.fine{font-size:13px;color:#555}@media(max-width:760px){main{padding:18px}.compare{grid-template-columns:1fr}article{padding:17px}}
    </style><main><section class="hero"><h1>Token 科普课程 · S08 真实课程验收</h1><p>本目录保留本次生成结果和每页的设计参考、实际渲染、插图及 QA 记录，供逐页核对。</p><div class="metrics">'''+metrics+'''</div><div class="flag"><strong>本页为工程审阅材料。</strong>技术 QA 验证结构、布局容量、动态输出帧和媒体链路，不验证讲稿、画面与动画的逐语块语义一致性。请对照设计参考、实际画面与配音检查对应关系；任务成功不等于课程批准。人工设计和音频批准以项目记录为准。</div></section>'''
    if sheet.exists():html+=f'<img class="contact" src="{link(sheet)}" alt="五页实际终态总览">'
    html+='<h2>逐页对照</h2>'+''.join(cards)
    html+='<section class="evidence"><h2>整课审阅媒体</h2>'+video+f'<p class="fine">媒体状态：{escape(media.get("status","未生成"))}；完整解码：{escape(str(media.get("complete_decode","未运行")))}；人工视觉批准：待审；配音听审：待听；正式发布：否。</p><p>{links}</p></section></main></html>'
    (output/'index.html').write_text(html,encoding='utf-8')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--settings-db',type=Path,default=ROOT/'data/projects.db')
    parser.add_argument('--stage',choices=['generate','continue-pending','qa','audio','audio-review','render-review','index'],required=True)
    parser.add_argument('--live',action='store_true');parser.add_argument('--disable-thinking',action='store_true');args=parser.parse_args(argv)
    course=json.loads((ROOT/'checks/fixtures/html/token-five-page.json').read_text(encoding='utf-8'))
    if args.stage in {'generate','continue-pending','audio'} and not args.live:
        emit('dry_run',target=args.stage,pages=len(course['slides']),paid_calls=False);return 0
    output=args.out.resolve();settings=settings_readonly(args.settings_db)
    run=output/'runs/token-s08'
    if args.stage=='generate' and output.exists():raise ValueError('S08_DIRECTORY_EXISTS; original paid requests must not be repeated')
    if args.stage!='generate' and not (output/'production-tasks.json').exists():raise ValueError('S08_GENERATION_REQUIRED')
    output.mkdir(parents=True,exist_ok=True)
    os.environ['PPT_STUDIO_DB_PATH']=str(output/'experiment.db');os.environ['PPT_STUDIO_RUNS_DIR']=str(output/'runs')
    if args.stage in {'generate','continue-pending'}:
        if args.stage=='continue-pending' and json.loads((output/'course-input.json').read_text(encoding='utf-8'))!=course:
            raise ValueError('S08_INPUT_CHANGED; cannot continue original experiment')
        write(output/'course-input.json',course);generate(output,run,course,settings,continue_pending=args.stage=='continue-pending',disable_thinking=args.disable_thinking)
    elif args.stage=='qa':review_pages(output,run,course)
    elif args.stage=='audio':synthesize(output,run,course,settings)
    elif args.stage=='audio-review':audio_review(output,run,course)
    elif args.stage=='render-review':render_review(output,run,course)
    else:build_review_index(output,run,course)
    emit('stage_complete',target=args.stage,output=str(output));return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        # Provider exceptions may contain credentials; only stable codes reach stdout.
        emit('failed',error_type=type(error).__name__,code=str(error) if isinstance(error,ValueError) and str(error).startswith('S08_') else 'S08_STAGE_FAILED')
        raise SystemExit(1)
