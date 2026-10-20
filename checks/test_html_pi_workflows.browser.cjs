'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require('../html_engine/node_modules/playwright');
const {captureLaunchOptions}=require('../html_engine/tools/browser-runtime.cjs');
(async()=>{
  const browser=await chromium.launch(captureLaunchOptions(chromium));
  try{
    const page=await browser.newPage();
    await page.route('http://127.0.0.1:18199/**',route=>route.fulfill({contentType:'text/html; charset=utf-8',body:'<meta charset="utf-8"><textarea id="step1-topic-input">真实主题</textarea><button data-pi-workflow="article">Pi文章候选</button>'}));
    await page.goto('http://127.0.0.1:18199/');
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.evaluate(()=>{
      window.PPTStudio={runtime:{state:{currentProject:{id:'project',visual_backend:'html'}}}};
      window.calls=[];window.attempt=0;
      window.API={post:async(url,body)=>{
        calls.push({url,body});
        if(++attempt===1)throw Object.assign(Error('请求状态未知，请恢复同一任务'),{status:504});
        return{job_id:'fixed-job'};
      },get:async()=>({job_id:'fixed-job',status:'succeeded',progress:100,can_cancel:false,usage:{model_calls:1},
        result:{task_type:'article.generate',candidate:{content:'# 真实文章\n\n候选正文'},saved:false}})};
    });
    await page.addScriptTag({path:path.resolve(__dirname,'../static/html_pi_workflows.js')});
    await page.addStyleTag({path:path.resolve(__dirname,'../static/html_pi_workflows.css')});
    await page.click('[data-pi-workflow]');
    assert.equal(await page.locator('[data-input]').inputValue(),'真实主题');
    await page.click('[data-start]');
    await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('未知'));
    assert(await page.locator('[data-start]').isDisabled());
    await page.click('[data-close]');
    await page.click('[data-pi-workflow]');
    assert(await page.locator('[data-start]').isDisabled());
    await page.click('[data-restore]');
    await page.waitForFunction(()=>!document.querySelector('[data-download]').hidden);
    const calls=await page.evaluate(()=>window.calls);
    assert.equal(calls.length,2);
    assert.deepEqual(calls[0].body,calls[1].body);
    assert.equal(calls[0].body.task.task_type,'article.generate');
    assert.equal(calls[0].body.delivery_policy,'candidate');
    assert((await page.locator('[data-result]').textContent()).includes('候选正文'));
    assert(await page.locator('[data-cancel]').isDisabled());
    assert.deepEqual(errors,[]);
    await page.screenshot({path:path.resolve(__dirname,'../outputs/pi-m45-workflow-ui.png')});
    await page.click('[data-close]');
    await page.addScriptTag({path:path.resolve(__dirname,'../static/html_pi_agent.js')});
    await page.evaluate(()=>{
      window.savedReloads=0;
      const host=document.createElement('section');document.body.append(host);
      window.API={post:async()=>({job_id:'auto-save-job'}),get:async()=>({job_id:'auto-save-job',status:'succeeded',progress:100,
        can_cancel:false,usage:{candidate_rounds:1},result:{saved:true,saved_revision:2}})};
      let owner;
      const options={getContext:()=>({projectId:'project',slideId:'slide_001'}),isCurrent:()=>true,getTask:()=>({}),
        onResult:()=>{throw Error('Saved results must reload the author, not display an old candidate');},
        onSaved:async()=>{savedReloads++;owner.destroy();owner=HtmlPiAgent.mount(host,options);}};
      owner=HtmlPiAgent.mount(host,options);
    });
    await page.locator('[data-pi-agent] input[type=checkbox]').check();
    await page.getByRole('button',{name:'开始 AI 修改',exact:true}).click();
    await page.waitForFunction(()=>window.savedReloads===1);
    await page.waitForFunction(()=>document.querySelector('[data-pi-agent] [role=status]').textContent.includes('版本 2'));
    assert.equal(await page.evaluate(()=>savedReloads),1);
    assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('html-pi-job:project:slide_001')).saved_revision),2);
    assert.deepEqual(errors,[]);
    console.log('Pi workflow UI: fixed input, unknown request recovery, same idempotency, candidate rendering and download passed');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
