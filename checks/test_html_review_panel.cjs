"use strict";
const fs=require("fs"),path=require("path"),assert=require("assert");
const {chromium}=require("../html_engine/node_modules/playwright");
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.HPS_CHROME||"C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe"});
 try{
  const page=await browser.newPage(); const errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  await page.setContent('<nav><li data-step="3">导航</li></nav><main id="step-panel-3"></main>');
  await page.evaluate(()=>{
   window.calls=[];window.mutations=0;
   window.PPTStudio={runtime:{state:{currentProject:{id:"p1",visual_backend:"html"},slides:[{slide_id:"s1"},{slide_id:"s2"}],activeSlideIndex:0}}};
   window.API={post:async(url)=>{calls.push(url);if(url.endsWith("produce"))return{task:{id:"t1",status:"queued"}};return{approval:{}};},get:async(url)=>{calls.push(url);
    if(url.endsWith('model-connections'))return {connections:[]};
    if(url.endsWith('model-binding'))return {revision:0,bindings:{text:{mode:'legacy'},image:{mode:'inherit'}},effective:{text:{provider:'fixture',model:'text',source:'global',ready:true},image:{provider:'fixture',model:'image',source:'global',ready:true}}};
    return{task:{status:"succeeded",result:{review:{passed:true}}}};}};
   new MutationObserver(records=>{mutations+=records.length}).observe(document.body,{subtree:true,childList:true,characterData:true});
  });
  await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,"../static/project_model_binding.js"),"utf8")});
  await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,"../static/html_review_panel.js"),"utf8")});
  await page.evaluate(()=>HtmlReviewPanel.refresh());
  assert.equal(await page.locator("#step-panel-3 #html-review-panel-section").count(),1);
  assert.equal(await page.locator("li #html-review-panel-section").count(),0);
  assert.equal(await page.getByLabel('文字模型来源').count(),0);
  await page.locator('[data-action="models"]').click();
  await page.getByLabel('文字模型来源').waitFor();
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p1/model-binding'));
  await page.locator('[data-action="produce"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('静态检查通过'));
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p1/html-review/s1/produce'));
  await page.evaluate(()=>{PPTStudio.runtime.state.activeSlideIndex=1;HtmlReviewPanel.refresh();});
  await page.locator('[data-action="approve"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-html-status]').textContent.includes('已批准'));
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p1/html-review/s2/approve'));
  const count=await page.evaluate(()=>mutations);
  await page.evaluate(()=>{for(let i=0;i<100;i++)HtmlReviewPanel.refresh();});
  assert.equal(await page.evaluate(()=>mutations),count);
  await page.evaluate(()=>{PPTStudio.runtime.state.currentProject={id:'p2',visual_backend:'html'};HtmlReviewPanel.refresh();});
  assert.equal(await page.getByLabel('文字模型来源').count(),0);
  assert.equal(await page.locator('[data-html-models]').isHidden(),true);
  await page.locator('[data-action="models"]').click();
  await page.getByLabel('文字模型来源').waitFor();
  assert((await page.evaluate(()=>calls)).includes('/api/projects/p2/model-binding'));
  await page.evaluate(()=>{PPTStudio.runtime.state.currentProject.visual_backend='image';HtmlReviewPanel.refresh();});
  assert.equal(await page.locator('#html-review-panel-section').isHidden(),true);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({checks:11,errors,correctPanel:true,stableRefresh:true,modelProjectIsolation:true}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
