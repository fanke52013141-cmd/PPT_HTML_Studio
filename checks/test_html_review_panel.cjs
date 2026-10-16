"use strict";
const fs=require("fs"),path=require("path"),assert=require("assert");
const {chromium}=require("../html_engine/node_modules/playwright");
const {resolveBrowser}=require("../html_engine/tools/browser-runtime.cjs");
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:resolveBrowser(chromium)});
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
    if(url.endsWith('/task/current'))return {task:{id:'unknown-task',status:'failed',input_state:'current',error:'原请求待核实',recovery:{requires_verification:true},progress:{next_action:{reason:'unsupported',routes:['capabilities'],automatic_retry:false}},execution:{measured_adapter_calls:2,recorded_reuses:1,elapsed_ms:2000,unmeasured_requests:1,untimed_requests:1,roles:{planning:{adapter_calls:1,reuses:1,elapsed_ms:2000}}}}};
    if(url.includes('/manual-candidate/'))throw Error('无可评审候选');
    if(url.endsWith('/design/current')){await new Promise(r=>setTimeout(r,35));return {design:{key:'unknown-design-key',status:'needs_review',stale:false}};}
    return {task:null};
   };
   HtmlReviewPanel.refresh();
  });
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('不能重复提交'));
  assert.equal(await page.locator('[data-action="accept-design"]').isDisabled(),true);
  assert.equal(await page.locator('[data-action="revise-design"]').isDisabled(),true);
  assert.match(await page.locator('[data-html-task]').textContent(),/适配器调用 2 次.*结果复用 1 次/);
  assert.match(await page.locator('[data-html-task]').textContent(),/部分旧记录或未完成请求缺少测量/);
  assert.match(await page.locator('[data-html-task]').textContent(),/当前能力不支持.*公共组件能力.*不会自动重试或批准/);
  // An Agent can complete a new candidate without changing the open page.
  // Re-reading must update the image and task gates without any mutation or
  // clearing the user's draft revision note.
  await page.evaluate(()=>{
   PPTStudio.runtime.state.currentProject={id:'external-project',visual_backend:'html'};
   window.externalDesign='old'; window.externalPosts=0;
   API.post=async()=>{externalPosts++;throw Error('unexpected mutation');};
   API.get=async url=>url.endsWith('/task/current')?{task:{id:externalDesign,status:'succeeded',input_state:'current',result:{stage:'design_review',design:{key:externalDesign}}}}:
    url.endsWith('/design/current')?{design:{key:externalDesign,status:'needs_review',stale:false}}:{scene:null};
   HtmlReviewPanel.refresh();
  });
  await page.waitForFunction(()=>document.querySelector('[data-html-design] img').getAttribute('src')?.includes('/old/'));
  await page.getByText('需要调整设计',{exact:true}).click();
  await page.locator('[data-design-instruction]').fill('保留正在填写的修改说明');
  await page.evaluate(async()=>{externalDesign='new';await HtmlReviewPanel.syncCurrent();});
  assert.match(await page.locator('[data-html-design] img').getAttribute('src'),/\/new\//);
  assert.equal(await page.locator('[data-design-instruction]').inputValue(),'保留正在填写的修改说明');
  assert.equal(await page.evaluate(()=>externalPosts),0);
  await page.evaluate(async()=>{
   window.workingGet=API.get;
   API.get=async()=>{throw Error('fixture offline');};
   await HtmlReviewPanel.syncCurrent();
  });
  assert.equal(await page.locator('[data-action="accept-design"]').isDisabled(),true);
  assert.equal(await page.locator('[data-action="approve"]').isDisabled(),true);
  await page.evaluate(async()=>{API.get=workingGet;await HtmlReviewPanel.syncCurrent();});
  assert.equal(await page.locator('[data-action="accept-design"]').isDisabled(),false);
  // Local revision carries the exact source identity; it is not acceptance.
  await page.evaluate(()=>{window.revisionBodies=[];API.post=async(url,body)=>{revisionBodies.push(body);return {message:'fixture revision submitted'};};});
  await page.locator('[data-action="revise-design"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('fixture revision submitted'));
  assert.deepEqual(await page.evaluate(()=>revisionBodies),[{design_candidate_key:'new',design_instruction:'保留正在填写的修改说明',plan_version:'0.2.0'}]);
  // A read started on an old project cannot replace the new project's image.
  await page.evaluate(()=>{
   const original=API.get;
   API.get=url=>url.endsWith('/task/current')?new Promise(resolve=>window.releaseOld=()=>resolve({task:null})):original(url);
   window.oldSync=HtmlReviewPanel.syncCurrent();
  });
  await page.evaluate(()=>{
   PPTStudio.runtime.state.currentProject={id:'new-project',visual_backend:'html'};
   API.get=async url=>url.endsWith('/design/current')?{design:{key:'new-project-design',status:'needs_review',stale:false}}:{task:null};
   HtmlReviewPanel.refresh();
  });
  await page.waitForFunction(()=>document.querySelector('[data-html-design] img').getAttribute('src')?.includes('/new-project-design/'));
  await page.evaluate(async()=>{releaseOld();await oldSync;});
  assert.match(await page.locator('[data-html-design] img').getAttribute('src'),/\/new-project-design\//);
  await page.evaluate(async()=>{
   API.get=async url=>url.endsWith('/design/current')?{design:null}:{task:{id:'read-timeout',status:'failed',input_state:'current',
    recovery:{can_resume:false,requires_verification:true},progress:{
     model_stream:{state:'failed',elapsed_seconds:281,last_chunk_seconds:156,silence_seconds:125,total_timeout_seconds:1800,read_timeout_seconds:120,content_chars:0,failure_reason:'read_timeout'},
     next_action:{reason:'read_timeout',routes:['provider_verification'],automatic_retry:false}}}};
   await HtmlReviewPanel.syncCurrent();
  });
  assert.match(await page.locator('[data-html-task]').textContent(),/读取等待超时/);
  assert.match(await page.locator('[data-html-task]').textContent(),/总预算 1800 秒/);
  assert.match(await page.locator('[data-html-task]').textContent(),/读取等待 120 秒/);
  assert.match(await page.locator('[data-html-task]').textContent(),/无新数据 125 秒/);
  assert.equal(await page.locator('[data-action="resume"]').isHidden(),true);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({errors,correctPanel:true,stableRefresh:true,modelProjectIsolation:true,workspaceSeparation:true,designIdentityPreserved:true,acceptedDesignVisible:true,independentButtonProtected:true,lateDesignCannotEnableUnknownRequest:true,samePageExternalUpdate:true,draftPreserved:true,readFailureBlocksSubmission:true,revisionSourcePreserved:true,lateProjectReadIgnored:true}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
