'use strict';
// Real application DOM, isolated HTTP fixtures; no course or provider mutations.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('../html_engine/node_modules/playwright');
const root=path.resolve(__dirname,'../static');
(async()=>{
 const server=http.createServer((req,res)=>{
  const file=path.resolve(root,new URL(req.url,'http://localhost').pathname.slice(1)||'index.html');
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.writeHead(404).end();return;}
  res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,executablePath:require('../html_engine/tools/browser-runtime.cjs').resolveBrowser(chromium)});
 try{
  const page=await browser.newPage(),errors=[],mutations=[];
  page.on('pageerror',e=>errors.push(e.message));
  const text='温度降低时，水分子的运动逐渐减慢。';
  const slide={slide_id:'s1',main_title:'水为什么会结冰？',core_message:text,body_content:[text],visual_groups:[{id:'g1',name:'温度变化',visual_anchor:'温度计与水分子示意',visual_type:'picture'}],narration_beats:[{id:'b1',group_id:'g1',spoken_text:text}]};
  const project={id:'layout-fixture',name:'六步布局 · 隔离测试夹具',visual_backend:'html',ai_mode:'manual',current_step:1,step_status:{'1':'completed','2':'completed'}};
  const illustration='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900"><rect width="1600" height="900" fill="#f7f8fa"/><text x="100" y="220" font-size="60" fill="#20252d">隔离测试设计参考</text><text x="100" y="330" font-size="32" fill="#687180">用于验证预览布局，不代表真实课程结果</text><rect x="100" y="440" width="620" height="230" rx="24" fill="#fff5f0"/><circle cx="1080" cy="540" r="130" fill="#ee5d36"/></svg>');
  await page.route('https://fonts.googleapis.com/**',r=>r.fulfill({contentType:'text/css',body:''}));
  await page.route('**/api/**',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(req.method()!=='GET')mutations.push(url.pathname);
   let value={success:true,projects:[],accounts:[],settings:{},active:false};
   if(url.pathname==='/api/projects')value=[];
   else if(url.pathname.endsWith('/one-click-generate/status'))value={status:{status:'waiting_for_review',active:false}};
   else if(url.pathname==='/api/projects/layout-fixture')value=project;
   else if(url.pathname.endsWith('/steps/1/result'))value={success:true,brief:{title:slide.main_title,content:'# 水为什么会结冰？\n\n'+Array(8).fill(text).join('\n\n')}};
   else if(url.pathname.endsWith('/steps/2/result'))value={success:true,contract:{slides:[slide]}};
   else if(url.pathname.endsWith('/steps/2/script/result'))value={success:true,script_plan:{slides:[{slide_id:'s1',slide_title:slide.main_title,narration:text}]}};
   else if(url.pathname.endsWith('/steps/6/result'))value={success:true,beats:{slides:[{slide_id:'s1',beats:[{beat_id:'b1',spoken_text:text,tts_text:text}]}]}};
   else if(url.pathname.endsWith('/audio-status'))value={success:true,slides:[]};
   else if(url.pathname.endsWith('/html-review/s1/semantic/status'))value={semantic_qa:{required:true,reason:'SEMANTIC_AUDIO_REQUIRED',engineering:'unknown',semantic:'not_evaluated',audio:'not_evaluated',human:'pending'}};
   else if(url.pathname.endsWith('/design/current'))value={design:{key:'fixture-design-key',status:'needs_review',stale:false,image_url:illustration}};
   else if(url.pathname.endsWith('/digital-human/config'))value={success:true,config:{enabled:true,mode:'comfyui',shape:'circle',circle:{cx:.8,cy:.8,r:.1},video:{ox:.5,oy:.5,zoom:1},slides:{}},audio_ready:{},total_slides:1};
   else if(url.pathname.endsWith('/html-visual/s1/editor'))value={scene:{nodes:[]},revision:0};
   await route.fulfill({json:value});
  });
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction(()=>window.PPTStudio?.runtime&&typeof enterWorkspace==='function');
  await page.evaluate(()=>enterWorkspace('layout-fixture'));
  const screenshotRoot=process.env.PPT_UI_QA_OUTPUT;
  if(screenshotRoot)fs.mkdirSync(screenshotRoot,{recursive:true});
  for(const [visible,internal]of [[1,1],[2,2],[3,3],[4,5],[5,6],[6,9]]){
   await page.evaluate(step=>navigateToStep(step),internal);
   await page.locator(`#step-panel-${internal}`).waitFor({state:'visible'});
   if(internal===3)await page.locator('[data-html-design]').waitFor({state:'visible'});
   if(internal===6)await page.locator('.html-audio-qa').waitFor({state:'visible'});
   if(internal===5)for(const action of ['review','approve','edit'])assert(await page.locator(`[data-action="${action}"]`).isDisabled(),'missing page cannot be approved or edited');
   if(internal===9){
    await page.locator('#dh-panel-body').waitFor({state:'visible'});
    assert.equal(await page.locator('#dh-panel-body input[id^="dh-slider-"]').count(),6,'all presenter precision controls retained');
   }
   for(const width of [1600,768,420]){
    await page.setViewportSize({width,height:1000});
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(resolve)));
    const overflow=await page.evaluate(()=>{
     const main=document.getElementById('workspace-main');
     return {body:document.body.scrollWidth>innerWidth+1,main:main.scrollWidth>main.clientWidth+1};
    });
    assert.deepEqual(overflow,{body:false,main:false},`step ${visible}, width ${width}`);
    if(internal===3&&width===1600){
     const rects=await page.locator('.html-design-workbench').evaluate(el=>Array.from(el.children).map(c=>c.getBoundingClientRect().toJSON()));
     assert(rects[0].width>rects[1].width&&rects[1].left>=rects[0].right,'design preview dominates left, decision inspector right');
    }
    if(internal===9&&width===1600){
     const [settings,preview,precision]=await page.locator('.dh-grid > .dh-field').evaluateAll(els=>els.map(e=>e.getBoundingClientRect().toJSON()));
     assert(preview.left<settings.left&&preview.width>settings.width,'presenter preview dominates left');
     assert.equal(precision.left,settings.left,'precision stays with generation settings');
    }
    if(screenshotRoot)await page.screenshot({path:path.join(screenshotRoot,`step-${visible}-${width}.png`)});
   }
  }
  await page.evaluate(()=>exitWorkspace());
  project.ai_mode='auto';
  await page.evaluate(()=>enterWorkspace('layout-fixture'));
  await page.evaluate(()=>navigateToStep(2));
  await page.locator('#step2-script-review').waitFor({state:'visible'});
  for(const width of [1600,768,420]){
   await page.setViewportSize({width,height:1000});
   const [script,visual]=await page.locator('#step2-script-review > .step2-stage').evaluateAll(els=>els.map(e=>e.getBoundingClientRect().toJSON()));
   if(width===1600)assert(visual.left>=script.right,'AI mode keeps script and visual mapping side by side');
   else assert(visual.top>=script.bottom,'AI mode stacks stages on narrow screens');
   assert.equal(await page.evaluate(()=>document.body.scrollWidth>innerWidth+1),false,'AI layout stays in viewport');
   if(screenshotRoot)await page.screenshot({path:path.join(screenshotRoot,`step-2-auto-${width}.png`)});
  }
  assert.deepEqual(mutations,[],'reading and navigating must never create or approve');
  await page.evaluate(()=>exitWorkspace());
  assert.equal(await page.evaluate(()=>document.body.classList.contains('html-workspace')),false);
  project.ai_mode='manual';
  await page.evaluate(()=>enterWorkspace('layout-fixture'));
  await page.evaluate(()=>navigateToStep(2));
  assert.equal(await page.locator('#step2-script-review').isVisible(),false,'CSS cannot reveal AI review in manual mode');
  await page.evaluate(()=>exitWorkspace());
  assert.deepEqual(mutations,[],'mode restoration must remain read only');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,panels:6,widths:[1600,768,420],checks:['populated article/storyboard/design/narration','AI and manual storyboard layouts','design preview and inspector','presenter preview and six precision controls retained','no navigation mutations','image shell restored'],scope:'isolated UI fixtures; not actual course acceptance'}));
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
