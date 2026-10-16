"use strict";
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require('../html_engine/node_modules/playwright');

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:require('../html_engine/tools/browser-runtime.cjs').resolveBrowser(chromium)});
  try {
    const page=await browser.newPage();
    const posts=[]; const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto('about:blank');
    await page.evaluate(()=>{
      document.body.innerHTML='<div id="step-panel-3"></div>';
      window.PPTStudio={runtime:{state:{currentProject:{id:'project-1',visual_backend:'html'},slides:[{slide_id:'slide_001',title:'Token'}],activeSlideIndex:0}}};
      window.API={get:async url=>{
        if(url.endsWith('/task/current'))return {task:{id:'job-1',slide_id:'slide_001',status:'interrupted',stage:'interrupted',attempt:1,input_state:'current',stages:{},recovery:{requires_verification:true},error:'EXTERNAL_OUTCOME_UNKNOWN'}};
        if(url.endsWith('/manual-candidate/job-1'))return {candidate:{key:'abc123',design_url:'/design.png',preview_url:'/preview.png',engineering:'failed',engineering_issues:[{message:'总结面板超过槽位'}],decision:null}};
        if(url.endsWith('/design/current'))return {design:null};
        throw new Error(url);
      },post:async(url,payload)=>{window.__posts.push({url,payload});return {candidate:{decision:{decision:payload.decision,note:payload.note}}};}};
      window.__posts=[];
    });
    await page.addScriptTag({path:path.resolve(__dirname,'../static/html_review_panel.js')});
    await page.evaluate(()=>window.HtmlReviewPanel.refresh());
    await page.locator('[data-html-manual-candidate]:visible').waitFor();
    assert.equal(await page.locator('[data-manual-design]').getAttribute('src'),'/design.png');
    assert.equal(await page.locator('[data-manual-preview]').getAttribute('src'),'/preview.png');
    assert.equal(await page.locator('[data-manual-action="accept"]').isHidden(),true);
    await page.locator('[data-manual-note]').fill('标注框过窄，文字换行影响可读性');
    await page.locator('[data-manual-action="reject"]').click();
    assert.match(await page.locator('[data-manual-decision]').innerText(),/已记录人工驳回/);
    assert.equal(await page.locator('[data-manual-action="accept"]').isHidden(),true);
    posts.push(...await page.evaluate(()=>window.__posts));
    assert.deepEqual(posts,[{url:'/api/projects/project-1/html-review/slide_001/manual-candidate/job-1/decision',payload:{key:'abc123',decision:'reject',note:'标注框过窄，文字换行影响可读性'}}]);
    assert.deepEqual(errors,[]);
    console.log('manual candidate panel passed');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
