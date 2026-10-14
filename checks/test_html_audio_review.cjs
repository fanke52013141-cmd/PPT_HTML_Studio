'use strict';
const fs=require('fs'),assert=require('assert'),{chromium}=require('../html_engine/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:require('../html_engine/tools/browser-runtime.cjs').resolveBrowser(chromium)});
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://audio.test/**',route=>{
   const url=route.request().url();
   const body=url.endsWith('/player.js')?'window.visualPlayer={apply:async()=>true,pause:()=>{},seek:t=>window.lastSeek=t};':'';
   route.fulfill({contentType:url.endsWith('.js')?'text/javascript':'text/html',body:url==='http://audio.test/'?'<div id="step-panel-6"></div>':body});
  });
  await page.goto('http://audio.test/');
  await page.evaluate(()=>{
   window.calls=[];window.qaMounts=[];window.stale=false;
   window.HtmlSemanticQA={close(){},mount:async(host,p,s)=>{qaMounts.push(s);host.textContent='QA '+s;}};
   window.API={get:async url=>{
    calls.push(url);
    if(url.endsWith('/result'))return {contract:{slides:[{slide_id:'one',main_title:'第一页'},{slide_id:'two'}]}};
    if(url.endsWith('/audio-status'))return {slides:['one','two'].map(slide_id=>({slide_id,audio_exists:true,stale}))};
    return {scene:{},binding:{},revision:3};
   },post:async(url,payload)=>{calls.push({url,payload});return {clock:'audio_timeline',scene:{beats:[{startMs:1250,endMs:2500,text:'实际句子'}]},resources:{}};}};
  });
  await page.addScriptTag({content:fs.readFileSync('static/html_audio_review.js','utf8')});
  await page.evaluate(()=>HtmlAudioReview.mount({id:'p',visual_backend:'html'}));
  assert.equal(await page.locator('audio').count(),1);
  await page.evaluate(()=>{
   const a=document.querySelector('audio');Object.defineProperty(a,'currentTime',{value:1.8,writable:true});a.dispatchEvent(new Event('timeupdate'));
  });
  assert.equal(await page.locator('iframe').evaluate(f=>f.contentWindow.lastSeek),1800);
  await page.getByRole('button',{name:'1. 实际句子'}).click();
  assert.equal(await page.locator('iframe').evaluate(f=>f.contentWindow.lastSeek),1250);
  assert.equal(await page.getByRole('button',{name:'1. 实际句子'}).getAttribute('aria-current'),'true');
  await page.evaluate(()=>{window.paused=0;document.querySelector('audio').pause=()=>paused++;});
  await page.getByLabel('同步试听页面').selectOption('two');
  await page.waitForFunction(()=>qaMounts.includes('two'));
  assert.equal(await page.evaluate(()=>paused),1);
  await page.evaluate(()=>{stale=true;});
  await page.getByRole('button',{name:'刷新试听与核验'}).click();
  await page.waitForFunction(()=>document.querySelector('[role="status"]').textContent.includes('有效配音'));
  assert.equal(await page.locator('audio').count(),0);
  assert((await page.evaluate(()=>calls.filter(c=>typeof c==='object'))).every(c=>c.url.endsWith('/editor/preview')));
  await page.evaluate(()=>HtmlAudioReview.mount({id:'image',visual_backend:'image'}));
  assert(await page.locator('#html-audio-review').isHidden());assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,checks:['actual audio clock','sentence seek','page switch pauses','stale audio blocked','no generation or approval','image separation'],transport:'isolated fixture; shared runtime separately verified'}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
