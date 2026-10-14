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
    return {semantic_qa:qa};
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
  await page.getByRole('button',{name:'人工签收语义结果'}).click();assert.equal(await page.evaluate(()=>decisions.length),0);
  await page.getByLabel('语义人工审阅说明').fill('checked actual evidence');
  await page.getByRole('button',{name:'人工签收语义结果'}).click();assert.equal(await page.evaluate(()=>decisions[0].decision),'approved');
  await page.getByRole('button',{name:'开始逐句语义 QA'}).click();
  await page.waitForFunction(()=>polls===1);assert(await page.evaluate(()=>network.some(u=>u.endsWith('/semantic/submit'))));
  await page.evaluate(()=>{qa.semantic='failed';});await page.getByRole('button',{name:'刷新语义结果'}).click();
  assert(await page.getByRole('button',{name:'人工签收语义结果'}).isDisabled());
  await page.evaluate(()=>HtmlSemanticQA.close());assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,checks:['source text','triplet frames','explicit human note','separate audio status','persistent task poll','failed semantics cannot approve'],transport:'stub browser; real supplier evaluated separately'}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
