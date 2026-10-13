"use strict";
// Actual browser and production UI; isolated fixture transport, no paid calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('../html_engine/node_modules/playwright');
const {resolveBrowser} = require('../html_engine/tools/browser-runtime.cjs');
(async () => {
  const browser = await chromium.launch({headless:true,executablePath:resolveBrowser(chromium)});
  const errors=[];
  try {
    const page=await browser.newPage({viewport:{width:1200,height:1000}});
    page.on('pageerror',error=>errors.push(error.message));
    await page.setContent('<div id="step-panel-3"></div>');
    for(const file of ['style.css','stitch.css','html_scene_edit.css']) await page.addStyleTag({path:path.resolve(__dirname,'../static',file)});
    await page.evaluate(() => {
      window.PPTStudio={runtime:{state:{currentProject:{id:'first',visual_backend:'html'},slides:[{slide_id:'s1',title:'冷杯测试'}],activeSlideIndex:0}}};
      window.calls=[];
      window.currentTask={id:'original',slide_id:'s1',type:'html_plan_generate',status:'interrupted',attempt:1,stage:'compile',input_state:'current',snapshot_id:'frozen-input',recovery:{can_resume:true},progress:{repair_round:1,max_rounds:3,runtime_skill:{skills:[{id:'candidate-layout-repair',version:'0.1.0'}]},reused_stages:['image:original']}};
      window.design=null;
      window.API={
        get:async url=>{
          if(url.includes('/design/current')) return {design:window.design};
          if(url.endsWith('/task/current') && PPTStudio.runtime.state.currentProject.id!=='first') return {task:null};
          if(url.endsWith('/html-visual/status')) return {workflow:{tasks:PPTStudio.runtime.state.currentProject.id==='first'?[currentTask]:[]}};
          if(window.lateTask) return await new Promise(resolve=>{window.releaseLate=()=>resolve({task:{...currentTask,error:'OLD PROJECT ERROR'}});});
          if(currentTask.status==='running') currentTask={...currentTask,status:'failed',error:'布局仍需调整',recovery:{can_resume:true}};
          return {task:currentTask};
        },
        post:async(url,body)=>{calls.push({url,body});currentTask={...currentTask,status:'running',stage:'review',recovery:{can_resume:false}};return {task:currentTask};},
      };
    });
    await page.addScriptTag({path:path.resolve(__dirname,'../static/html_review_panel.js')});
    await page.evaluate(()=>HtmlReviewPanel.refresh());
    await page.waitForFunction(()=>document.querySelector('[data-html-task]').textContent.includes('candidate-layout-repair'));
    assert(await page.locator('[data-action="resume"]').isVisible());
    assert.match(await page.locator('[data-html-task]').textContent(),/已复用 1/);
    const out=path.resolve(__dirname,'../outputs/s07-validation');fs.mkdirSync(out,{recursive:true});
    await page.screenshot({path:path.join(out,'task-recovery.png'),fullPage:true});
    await page.locator('[data-action="resume"]').click();
    await page.waitForFunction(()=>document.querySelector('[data-html-task]').textContent.includes('布局仍需调整'));
    assert.deepEqual(await page.evaluate(()=>calls),[{url:'/api/projects/first/html-review/tasks/original/resume',body:{}}]);
    // A late task read cannot replace the newly selected project's state.
    await page.evaluate(()=>{
      window.lateTask=true;currentTask={...currentTask,status:'running'};
      document.querySelector('#html-review-panel-section').dataset.context='';HtmlReviewPanel.refresh();
    });
    await page.waitForFunction(()=>Boolean(window.releaseLate));
    await page.evaluate(()=>{PPTStudio.runtime.state.currentProject={id:'second',visual_backend:'html'};HtmlReviewPanel.refresh();releaseLate();});
    await page.waitForTimeout(1200);
    assert.equal(await page.locator('[data-html-task]').textContent(),'');
    assert(await page.locator('[data-action="resume"]').isHidden());
    assert(!(await page.locator('[data-html-status]').textContent()).includes('OLD PROJECT ERROR'));
    // Restore an old succeeded task without calling it the current delivery.
    await page.evaluate(()=>{
      window.lateTask=false;currentTask={...currentTask,status:'succeeded',input_state:'stale',error:null,recovery:{can_resume:false},result:{review:{passed:true}}};
      PPTStudio.runtime.state.currentProject={id:'first',visual_backend:'html'};HtmlReviewPanel.refresh();
    });
    await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('旧任务'));
    assert(await page.locator('[data-html-preview]').isHidden());
    // Render real output cards for current/historical HTML and preserve image labels.
    await page.setContent('<button id="step8-btn-render"></button><div id="step8-video-list"></div><div id="step8-result-box"></div><div id="step8-pptx-result-box"></div><div id="step8-pptx-list"></div>');
    for(const file of ['style.css','stitch.css','html_scene_edit.css']) await page.addStyleTag({path:path.resolve(__dirname,'../static',file)});
    await page.evaluate(()=>{
      window.state={currentProject:{id:'first',visual_backend:'html'}};
      window.escHtml=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
      window.formatArtifactBytes=()=> '1 KB';window.formatProjectTotalElapsed=()=>'';
      window.items=[{id:'old',artifact_state:'stale',historical:true,url:'',exists:true,export_evidence:{snapshot_id:'course-old',pages:[{slide_id:'s1',reused:true}]}},{id:'new',artifact_state:'current',url:'',exists:true,export_evidence:{snapshot_id:'course-new',pages:[{slide_id:'s1',reused:false}]}}];
    });
    await page.addScriptTag({path:path.resolve(__dirname,'../static/output_render.js')});
    await page.evaluate(()=>{showStep8VideoResult(items);showStep8PptxResults(items);});
    const text=await page.locator('#step8-video-list').textContent();
    assert.match(text,/历史候选/);assert.match(text,/当前有效交付/);assert.match(text,/course-new/);
    assert(!text.includes('Mask'));
    await page.screenshot({path:path.join(out,'delivery-state.png'),fullPage:true});
    await page.evaluate(()=>{state.currentProject.visual_backend='image';showStep8VideoResult([items[1]]);});
    assert.match(await page.locator('#step8-video-list').textContent(),/精确 RLE Mask/);
    assert.deepEqual(errors,[]);
    console.log('S07 browser: persisted recovery, original retry, late response isolation, stale success, current/historical HTML and image compatibility passed');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
