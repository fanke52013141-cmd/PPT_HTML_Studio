"use strict";
const fs=require("fs"),assert=require("assert"),{chromium}=require("../html_engine/node_modules/playwright");
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:require("../html_engine/tools/browser-runtime.cjs").resolveBrowser(chromium)});
 try {
  const page=await browser.newPage(),errors=[];page.on("pageerror",e=>errors.push(e.message));
  await page.setContent('<main></main>');
  await page.evaluate(()=>{
   window.decisions=[];window.network=[];window.polls=0;
   window.qa={required:true,revision:1,key:"a".repeat(64),engineering:"passed",semantic:"passed",audio:"pending",human:"pending",beats:[{id:"b1",spoken_text:"原句不可替换",times:[0,1000,1999],result:{verdict:"related",evidence:[{frameIndex:2,targetId:"known",observation:"actual evidence"}]}}]};
   window.API={get:async url=>{
    network.push(url);
    if(url.includes('/tasks/'))return {task:{id:"task",status:++polls>0?"succeeded":"running"}};
    return {semantic_qa:qa,task:window.unknownTask?{id:'unknown',status:'failed',recovery:{requires_verification:true}}:null};
   },post:async (url,body)=>{
    network.push(url);
    if(url.endsWith('/submit'))return {task:{id:"task",status:"running",progress:{completed_beats:0,total_beats:1}}};
    decisions.push(body);qa.human=body.decision;return {semantic_qa:qa};
   }};
  });
  await page.addScriptTag({content:fs.readFileSync("static/html_semantic_qa.js","utf8")});
  await page.evaluate(()=>HtmlSemanticQA.mount(document.querySelector('main'),{id:'p'},'s'));
  await page.locator('summary').click();
  assert(await page.locator('main').innerText().then(t=>t.includes('原句不可替换')));
  assert.equal(await page.locator('img').count(),3);
  await page.getByRole('button',{name:'人工签收本页核验'}).click();assert.equal(await page.evaluate(()=>decisions.length),0);
  await page.getByLabel('本页核验说明').fill('checked actual evidence');
  await page.getByRole('button',{name:'人工签收本页核验'}).click();assert.equal(await page.evaluate(()=>decisions[0].decision),'approved');
  await page.getByRole('button',{name:'开始逐句核验'}).click();
  await page.waitForFunction(()=>polls===1);assert(await page.evaluate(()=>network.some(u=>u.endsWith('/semantic/submit'))));
  await page.evaluate(()=>{qa.semantic='failed';});await page.getByRole('button',{name:'刷新核验结果'}).click();
  assert(await page.getByRole('button',{name:'人工签收本页核验'}).isDisabled());
  for(const reason of ['SEMANTIC_SCENE_MISSING','SEMANTIC_AUDIO_REQUIRED','AUDIO_BINDING_STALE']) {
   await page.evaluate(reason=>{qa.reason=reason;},reason);
   await page.getByRole('button',{name:'刷新核验结果'}).click();
   assert(await page.getByRole('button',{name:'开始逐句核验'}).isDisabled());
  }
  await page.evaluate(()=>{qa.reason='semantic_report_missing_or_invalid';});
  await page.getByRole('button',{name:'刷新核验结果'}).click();
  assert.equal(await page.getByRole('button',{name:'开始逐句核验'}).isDisabled(),false);
  await page.evaluate(()=>{window.unknownTask=true;});
  await page.getByRole('button',{name:'刷新核验结果'}).click();
  assert(await page.getByRole('button',{name:'开始逐句核验'}).isDisabled());
  await page.evaluate(()=>HtmlSemanticQA.close());assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,checks:['source text','triplet frames','explicit human note','separate audio status','persistent task poll','failed semantics cannot approve'],transport:'stub browser; real supplier evaluated separately'}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
