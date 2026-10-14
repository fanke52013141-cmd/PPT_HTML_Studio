"use strict";
const fs=require("fs"),path=require("path"),assert=require("assert");
const {chromium}=require("../html_engine/node_modules/playwright");
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.HPS_CHROME||"C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe"});
 try{
  const page=await browser.newPage(); const errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  await page.setContent('<nav><li data-step="3">导航</li></nav><main id="step-panel-3"><div class="step3-toolbar-row">旧图片工具</div></main><main id="step-panel-5"><div class="step5-mask-header">旧Mask工具</div></main>');
  await page.addStyleTag({path:path.join(__dirname,'../static/html_workflow.css')});
  await page.addStyleTag({content:'.step3-toolbar-row {display:flex!important}'});
  await page.evaluate(()=>{
   window.calls=[];window.mutations=0;
   window.PPTStudio={runtime:{state:{currentProject:{id:"p1",visual_backend:"html"},slides:[{slide_id:"s1"},{slide_id:"s2"}],activeSlideIndex:0,currentStep:3}}};
   window.API={post:async(url)=>{calls.push(url);if(url.endsWith("produce"))return{task:{id:"t1",status:"queued"}};return{approval:{}};},get:async(url)=>{calls.push(url);
    if(url.endsWith('model-connections'))return {connections:[]};
    if(/\/html-visual\/s[12]$/.test(url))return {scene:{id:'fixture'}};
    if(url.endsWith('model-binding'))return {revision:0,bindings:{text:{mode:'legacy'},image:{mode:'inherit'}},effective:{text:{provider:'fixture',model:'text',source:'global',ready:true},image:{provider:'fixture',model:'image',source:'global',ready:true}}};
    return{task:{status:"succeeded",progress:{model_stream:{state:"completed",elapsed_seconds:7,content_chars:42}},result:{review:{passed:true}}}};}};
   new MutationObserver(records=>{mutations+=records.length}).observe(document.body,{subtree:true,childList:true,characterData:true});
  });
  await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,"../static/project_model_binding.js"),"utf8")});
  await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,"../static/html_review_panel.js"),"utf8")});
  await page.evaluate(()=>HtmlReviewPanel.refresh());
  assert.equal(await page.locator("#step-panel-3 #html-review-panel-section").count(),1);
  assert.equal(await page.locator("li #html-review-panel-section").count(),0);
  assert.equal(await page.locator('.step3-toolbar-row').isVisible(),false);
  assert.equal(await page.locator('[data-action="edit"]').isVisible(),false);
  assert.equal(await page.getByLabel('设计理解与视觉审核模型来源').count(),0);
  await page.locator('[data-action="models"]').click();
  await page.getByLabel('设计理解与视觉审核模型来源').waitFor();
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p1/model-binding'));
  await page.locator('[data-action="produce"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('静态检查通过'));
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p1/html-review/s1/produce'));
  assert.match(await page.locator('[data-html-task]').textContent(),/结果接收完成.*42/);
  await page.evaluate(()=>{PPTStudio.runtime.state.activeSlideIndex=1;PPTStudio.runtime.state.currentStep=5;HtmlReviewPanel.refresh();});
  assert.equal(await page.locator('#step-panel-5 #html-review-panel-section').count(),1);
  assert.equal(await page.locator('[data-action="produce"]').isVisible(),false);
  assert.equal(await page.locator('[data-action="edit"]').isVisible(),true);
  await page.locator('[data-action="approve"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('已批准'));
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p1/html-review/s2/approve'));
  const count=await page.evaluate(()=>mutations);
  await page.evaluate(()=>{for(let i=0;i<100;i++)HtmlReviewPanel.refresh();});
  assert.equal(await page.evaluate(()=>mutations),count);
  await page.evaluate(()=>{PPTStudio.runtime.state.currentProject={id:'p2',visual_backend:'html'};HtmlReviewPanel.refresh();});
  assert.equal(await page.getByLabel('设计理解与视觉审核模型来源').count(),0);
  assert.equal(await page.locator('[data-html-models]').isHidden(),true);
  await page.locator('[data-action="models"]').click();
  await page.getByLabel('设计理解与视觉审核模型来源').waitFor();
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p2/model-binding'));
  await page.evaluate(()=>{PPTStudio.runtime.state.currentProject.visual_backend='image';HtmlReviewPanel.refresh();});
  assert.equal(await page.locator('.step3-toolbar-row').isVisible(),true);
  assert.equal(await page.locator('.step5-mask-header').isVisible(),true);
  assert.equal(await page.locator('#html-review-panel-section').isHidden(),true);
  // Accepting the exact design candidate moves to the page workspace without
  // losing its identity or issuing another design request.
  await page.evaluate(()=>{
   PPTStudio.runtime.state.currentProject={id:'p3',visual_backend:'html'};
   PPTStudio.runtime.state.currentStep=3;
   window.acceptCalls=[];
   window.navigateToStep=async step=>{PPTStudio.runtime.state.currentStep=step;HtmlReviewPanel.refresh();};
   API.get=async url=>url.endsWith('/design/current')?{design:{key:'original-design-key',status:'needs_review',stale:false}}:{task:null};
   API.post=async(url,body)=>{acceptCalls.push({url,body});return {review:{passed:true}};};
   HtmlReviewPanel.refresh();
  });
  await page.locator('[data-html-design]').waitFor();
  assert.equal(await page.locator('[data-action="review"]').isVisible(),false);
  await page.locator('[data-action="accept-design"]').click();
  assert.equal(await page.locator('#step-panel-5 #html-review-panel-section').count(),1);
  assert.equal(await page.evaluate(()=>PPTStudio.runtime.state.currentStep),5);
  const accepts=await page.evaluate(()=>acceptCalls);
  assert.equal(accepts.length,1);
  assert.equal(accepts[0].body.design_candidate_key,'original-design-key');
  assert.match(accepts[0].url,/\/html-review\/s2\/produce$/);
  await page.evaluate(()=>{
   PPTStudio.runtime.state.currentProject={id:'accepted-project',visual_backend:'html'};
   PPTStudio.runtime.state.currentStep=3;
   API.get=async url=>url.endsWith('/design/current')?{design:{key:'accepted-design-key',status:'accepted_for_reconstruction',stale:false}}:{task:null};
   HtmlReviewPanel.refresh();
  });
  await page.waitForFunction(()=>document.querySelector('[data-design-state]').textContent.includes('已确认'));
  assert.equal(await page.locator('[data-html-design]').isVisible(),true);
  assert.equal(await page.locator('[data-action="accept-design"]').isHidden(),true);
  await page.evaluate(()=>{
   const external=document.createElement('button'); external.id='independent-qa-button';external.disabled=true;
   document.querySelector('#html-review-panel-section').append(external);
   PPTStudio.runtime.state.currentStep=5;HtmlReviewPanel.refresh();
   document.querySelector('#html-review-panel-section').dataset.pageReady='true';
   API.post=async()=>({review:{passed:true}});
   document.querySelector('[data-action="review"]').disabled=false;
  });
  await page.locator('[data-action="review"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('静态检查通过'));
  assert.equal(await page.locator('#independent-qa-button').isDisabled(),true);
  await page.evaluate(()=>{
   PPTStudio.runtime.state.currentProject={id:'unknown-project',visual_backend:'html'};
   PPTStudio.runtime.state.currentStep=3;
   API.get=async url=>{
    if(url.endsWith('/task/current'))return {task:{id:'unknown-task',status:'failed',input_state:'current',error:'原请求待核实',recovery:{requires_verification:true}}};
    if(url.includes('/manual-candidate/'))throw Error('无可评审候选');
    if(url.endsWith('/design/current')){await new Promise(r=>setTimeout(r,35));return {design:{key:'unknown-design-key',status:'needs_review',stale:false}};}
    return {task:null};
   };
   HtmlReviewPanel.refresh();
  });
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('不能重复提交'));
  assert.equal(await page.locator('[data-action="accept-design"]').isDisabled(),true);
  assert.equal(await page.locator('[data-action="revise-design"]').isDisabled(),true);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({checks:21,errors,correctPanel:true,stableRefresh:true,modelProjectIsolation:true,workspaceSeparation:true,designIdentityPreserved:true,acceptedDesignVisible:true,independentButtonProtected:true,lateDesignCannotEnableUnknownRequest:true}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
