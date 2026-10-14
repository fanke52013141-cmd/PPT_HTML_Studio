"use strict";
// Normal application DOM with explicit local HTTP doubles; no paid providers.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('../html_engine/node_modules/playwright');
const root=path.resolve(__dirname,'../static');
(async()=>{
 const server=http.createServer((req,res)=>{
  const file=path.resolve(root,new URL(req.url,'http://localhost').pathname.replace(/^\//,'')||'index.html');
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.writeHead(404).end();return;}
  res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,executablePath:require('../html_engine/tools/browser-runtime.cjs').resolveBrowser(chromium)});
 try{
  const page=await browser.newPage();const creates=[],loads=[],errors=[],mutations=[];
  page.on('pageerror',e=>errors.push(e.message));
  const project={id:'html-entry-fixture',name:'fixture',visual_backend:'html',ai_mode:'manual',current_step:3,step_status:{}};
  await page.route('**/api/**',async route=>{
   const req=route.request(),url=new URL(req.url());loads.push(url.pathname);
   if(req.method()!=='GET')mutations.push({method:req.method(),path:url.pathname});
   let result={success:true,projects:[],accounts:[],packages:[],configs:[],settings:{},active:false};
   if(url.pathname==='/api/projects'&&req.method()==='POST'){creates.push(req.postDataJSON());result={success:true,project};}
   else if(url.pathname==='/api/projects')result=[];
   else if(url.pathname==='/api/projects/html-entry-fixture')result=project;
   else if(url.pathname.endsWith('/steps/2/result'))result={success:true,contract:{slides:[]}};
   await route.fulfill({json:result});
  });
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction(()=>document.getElementById('modal-create')?.querySelector('#input-project-article'));
  await page.evaluate(()=>{document.getElementById('modal-create').style.display='flex';});
  await page.locator('#input-project-name').fill('HTML fixture');
  await page.locator('[data-profile-option="ai_mode"][data-value="manual"]').click();
  await page.locator('[data-profile-option="canvas_profile"][data-value="portrait_9_16"]').click();
  await page.locator('#input-project-visual-backend').selectOption('html');
  assert.equal(await page.locator('[data-profile-option="canvas_profile"].active').getAttribute('data-value'),'landscape_16_9');
  await page.locator('[data-profile-option="canvas_profile"][data-value="portrait_9_16"]').click();
  await page.locator('#btn-create-submit').click();
  assert.equal(creates.length,0);
  await page.locator('[data-profile-option="canvas_profile"][data-value="landscape_16_9"]').click();
  await page.locator('#btn-create-submit').click();
  await page.waitForFunction(()=>document.body.classList.contains('workspace-open'));
  await page.waitForFunction(()=>document.querySelector('.step-item[data-step="5"]')?.textContent.includes('HTML 还原与动画'));
  assert.equal(creates.length,1);assert.equal(creates[0].visual_backend,'html');
  assert.equal(creates[0].canvas_profile,'landscape_16_9');
  assert.match(await page.locator('.step-item[data-step="5"]').innerText(),/HTML 还原与动画/);
  assert.match(await page.locator('.step-item[data-step="3"]').innerText(),/设计图生成/);
  assert.equal(await page.locator('.step-item[data-step="10"]').isVisible(),false);
  assert.equal(await page.locator('#step-panel-3 .step3-toolbar-row').isVisible(),false);
  const from=loads.length;
  await page.locator('.step-item[data-step="5"]').click();
  await page.locator('#step-panel-5 #html-review-panel-section').waitFor();
  assert.equal(await page.evaluate(()=>PPTStudio.runtime.state.currentStep),5);
  assert.equal(await page.locator('#step-panel-5 .step5-mask-header').isVisible(),false);
  assert.equal(await page.locator('[data-action="produce"]').isVisible(),false);
  assert.equal(await page.locator('[data-action="edit"]').isVisible(),true);
  await page.setViewportSize({width:768,height:900});
  assert.equal(await page.evaluate(()=>document.body.getBoundingClientRect().width <= innerWidth),true);
  assert.equal(await page.evaluate(()=>{
    const host=document.getElementById('workspace-main');return host.scrollWidth<=host.clientWidth+1;
  }),true);
  await page.setViewportSize({width:420,height:900});
  assert.equal(await page.evaluate(()=>document.body.getBoundingClientRect().width <= innerWidth),true);
  await page.setViewportSize({width:1280,height:900});
  assert.equal(loads.slice(from).some(u=>/\/steps\/(3|5)\//.test(u)),false);
  const beforeNavigation=mutations.slice();
  project.ai_mode='auto';
  for(const step of [1,2,3,5,6,9,8]) {
   await page.locator(`.step-item[data-step="${step}"]`).click();
   await page.locator(`#step-panel-${step}`).waitFor({state:'visible'});
   if(step===6)await page.locator('#html-audio-review').waitFor({state:'visible'});
   if(step===8)await page.locator('#html-output-readiness').waitFor({state:'visible'});
   for(const width of [1280,768,420]) {
    await page.setViewportSize({width,height:900});
    assert.equal(await page.evaluate(()=>document.body.scrollWidth<=innerWidth+1),true,`body overflow step ${step} width ${width}`);
    assert.equal(await page.evaluate(()=>{const main=document.getElementById('workspace-main');return main.scrollWidth<=main.clientWidth+1;}),true,`main overflow step ${step} width ${width}`);
    if(width===420)assert.equal(await page.evaluate(()=>{
      const header=document.querySelector('header.app-header').getBoundingClientRect(),project=document.getElementById('project-info-header').getBoundingClientRect();
      return project.bottom<=header.bottom+1;
    }),true,'project identity must not overlap the step rail');
    const titleBounds=await page.evaluate(step=>{
      const main=document.getElementById('workspace-main').getBoundingClientRect();
      return Array.from(document.querySelectorAll(`#step-panel-${step} h2`)).filter(e=>e.getBoundingClientRect().height>0).map(e=>{const r=e.getBoundingClientRect(),p=e.parentElement;return {valid:r.left>=main.left-1&&r.right<=main.right+1,title:r.toJSON(),main:main.toJSON(),parent:p.getBoundingClientRect().toJSON(),parentClass:p.className,wrap:getComputedStyle(p).flexWrap};});
    },step);
    assert(titleBounds.every(item=>item.valid),`titles clipped step ${step} width ${width}: ${JSON.stringify(titleBounds)}`);
   }
   if(step===6)assert.equal(await page.locator('#step6-btn-init').isVisible(),true);
   if(step===8)assert.equal(await page.locator('#step8-btn-render').isDisabled(),true);
  }
  await page.setViewportSize({width:1280,height:900});
  assert.deepEqual(mutations,beforeNavigation,'navigation must not generate or approve');
  await page.evaluate(()=>exitWorkspace());
  assert.equal(await page.evaluate(()=>PPTFlow.visibleStepLabel(5)),'AI Mask 标注');
  project.visual_backend='image';
  await page.evaluate(()=>enterWorkspace('html-entry-fixture'));
  await page.locator('#step-panel-3 .step3-toolbar-row').waitFor();
  assert.equal(await page.locator('.step-item[data-step="10"]').isVisible(),true);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,checks:['HTML request identity','default image retained','16:9 selection','invalid combination blocks POST','HTML sidebar labels','seven panels at 1280/768/420','narration initialization visible','output prerequisites block','navigation has no generation or approvals','no raster stage requests','image flow restored']}));
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
