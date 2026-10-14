'use strict';
const fs=require('fs'),assert=require('assert'),{chromium}=require('../html_engine/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:require('../html_engine/tools/browser-runtime.cjs').resolveBrowser(chromium)});
 try{
  const page=await browser.newPage();await page.setContent('<div id="step-panel-8"><button id="step8-btn-render">生成 MP4</button><div id="step8-error-box"></div></div>');
  await page.evaluate(()=>{
   window.state={currentProject:{id:'html',visual_backend:'html'}};window.workspaceNavigationVersion=1;window.targetStep=null;
   window.isCurrentWorkspaceProject=id=>state.currentProject.id===id;window.navigateToStep=step=>targetStep=step;
   window.PPTFlow={visibleStepLabel:step=>({3:'设计图生成',5:'HTML 还原与动画',6:'配音与同步',9:'数字人讲解'})[step]};
   window.ready=false;window.reason='SCENE_MISSING';window.window.HtmlWorkflowState={load:async()=>({states:{3:'pending'},response:{workflow:{stages:[{id:'review_and_output',targets:{mp4_video:{ready,issues:ready?[]:[{code:reason,slide_id:'one',message:'missing'}]}}}]}}})};
  });
  await page.addScriptTag({content:fs.readFileSync('static/output_render.js','utf8')});
  await page.evaluate(()=>refreshStep8HtmlReadiness());
  assert(await page.locator('#step8-btn-render').isDisabled());
  await page.getByRole('button',{name:'去设计图生成',exact:true}).click();assert.equal(await page.evaluate(()=>targetStep),3);
  await page.evaluate(()=>{reason='SEMANTIC_QA_REQUIRED';});await page.evaluate(()=>refreshStep8HtmlReadiness());
  await page.getByRole('button',{name:'去配音与同步',exact:true}).click();assert.equal(await page.evaluate(()=>targetStep),6);
  await page.evaluate(()=>{ready=true;});await page.evaluate(()=>refreshStep8HtmlReadiness());assert.equal(await page.locator('#step8-btn-render').isDisabled(),false);
  await page.evaluate(()=>{HtmlWorkflowState.load=async()=>{throw Error('offline');};});await page.evaluate(()=>refreshStep8HtmlReadiness());assert(await page.locator('#step8-btn-render').isDisabled());
  await page.evaluate(()=>{state.currentProject={id:'image',visual_backend:'image'};});await page.evaluate(()=>refreshStep8HtmlReadiness());
  assert(await page.locator('#html-output-readiness').isHidden());assert.equal(await page.locator('#step8-btn-render').isDisabled(),false);
  console.log('HTML output prerequisites, action routing, unreadable blocks and image restore passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
