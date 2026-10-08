'use strict';
const fs=require('fs'), assert=require('assert');
const {chromium}=require('../html_engine/node_modules/playwright');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.HPS_CHROME});
  try{
    const page=await browser.newPage(), errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.setContent('<main id="panel"></main>');
    await page.addStyleTag({content:fs.readFileSync('static/html_asset_sheets.css','utf8')});
    await page.evaluate(()=>{
      window.calls=[]; window.conflict=false; window.produced=false; window.saved=null; window.accepted=false;
      window.taskType = 'html_asset_sheet_generate'; window.failedObject = false; window.taskResult = null; window.secondCandidate = false;
      const asset={id:'one',need:'<img src=x onerror=alert(1)>测试配图',anchors:[],processing:{alpha_cleanup:{removed_pixels:9}}};
      window.API={
        get:async url=>{calls.push(['GET',url]);
          if(url.includes('/tasks/'))return {task:{id:'task-one',type:taskType,result:taskResult,status:window.cancelled?'cancelled':window.slow?'running':'succeeded'}};
          if(url.endsWith('html-asset-sheets'))return {data:{candidates:produced?[{sheet_id:'board',request_key:'a'.repeat(64)},...(secondCandidate?[{sheet_id:'board',request_key:'b'.repeat(64)}]:[])]:[],task:window.restoreTask?{id:'task-one',type:taskType,status:window.cancelled?'cancelled':'running'}:null}};
          return {data:{revision:saved?1:0,decisions:saved?{one:saved}:{},accepted:accepted?{one:true}:{},manifest:{assets:[asset],failures:failedObject?[{asset_id:'failed-one',message:'裁边失败'}]:[]},advisory:{findings:{one:{action:'accept_candidate',reason:'<img src=x onerror=alert(1)>主体可用'}}}}};
        },
        post:async(url,payload)=>{calls.push(['POST',url,payload]);
          if(url.endsWith('/cancel')){window.cancelled=true;return {task:{status:'cancelled'}};}
          if(url.endsWith('/assess') || url.endsWith('/retry')){
            taskType=url.endsWith('/assess')?'html_asset_sheet_assess':'html_asset_sheet_retry';
            taskResult=url.endsWith('/assess')?{sheet_id:'board',request_key:url.split('/').at(-2)}:null;
            return {data:{task:{id:'task-one',type:taskType,status:'queued'}}};
          }
          if(url.endsWith('generate')){produced=true;return {data:{task:{id:'task-one',status:'queued'}}};}
          accepted=true;return {data:{changed:true}};
        },
        put:async(url,payload)=>{calls.push(['PUT',url,payload]);
          if(conflict){const error=new Error('conflict');error.status=409;throw error;}
          saved=payload;return {data:{revision:1,decisions:{one:payload}}};
        }
      };
    });
    await page.addScriptTag({content:fs.readFileSync('static/html_asset_sheets.js','utf8')});
    await page.evaluate(()=>HtmlAssetSheets.open(document.querySelector('main'),{id:'p1',visual_backend:'html'}));
    await page.getByLabel('配图需求').fill('杯子\n水滴');
    await page.getByText('清理透明背景中的微弱残留（保留主体边缘）',{exact:true}).locator('input').check();
    await page.getByRole('button',{name:'生成配图',exact:true}).click();
    await page.getByRole('button',{name:'保存审阅'}).waitFor();
    const request=await page.evaluate(()=>calls.find(c=>c[1].endsWith('/generate'))[2]);
    assert.equal(request.plan.slots.length,2);
    assert.deepEqual(request.plan.slots[1].rect,[768,0,768,1024]);
    assert.deepEqual(request.plan.slots[0].alpha_cleanup,{threshold:1,guard_radius:2,max_removed_fraction:0.02});
    assert.equal(await page.getByText('已清理9个微透明残留像素，请核对细节。',{exact:true}).count(),1);
    assert.equal(await page.locator('.html-sheet-card p img').count(),0);
    assert.equal(await page.getByText('对象内容正确',{exact:true}).locator('input').isChecked(),false);
    await page.getByRole('button',{name:'AI检查配图',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[role=status]').textContent.includes('AI检查已完成'));
    assert.equal(await page.getByText('对象内容正确',{exact:true}).locator('input').isChecked(),false);
    await page.getByLabel('重新生成需求 one').fill('杯子，不要光芒');
    await page.getByRole('button',{name:'仅重新生成这个对象',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[role=status]').textContent.includes('配图已生成'));
    const retryRequest=await page.evaluate(()=>calls.find(c=>c[1].endsWith('/one/retry'))[2]);
    assert.deepEqual(retryRequest,{expected_revision:0,need:'杯子，不要光芒'});
    await page.evaluate(()=>{window.failedObject=true;});
    await page.getByRole('button',{name:'刷新候选',exact:true}).click();
    await page.getByRole('button',{name:'重试失败对象 failed-one',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[role=status]').textContent.includes('配图已生成'));
    assert((await page.evaluate(()=>calls)).some(c=>c[1].endsWith('/failed-one/retry') && c[2].expected_revision===0));
    await page.evaluate(()=>{window.failedObject=false;});
    await page.evaluate(()=>{window.secondCandidate=true;});
    await page.getByRole('button',{name:'刷新候选',exact:true}).click();
    await page.getByLabel('素材候选版本').selectOption('a'.repeat(64));
    await page.getByRole('button',{name:'AI检查配图',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[role=status]').textContent.includes('AI检查已完成'));
    assert.equal(await page.getByLabel('素材候选版本').inputValue(),'a'.repeat(64));
    await page.evaluate(()=>{window.secondCandidate=false;});
    const accept=page.getByRole('button',{name:'加入可用素材'});
    assert.equal(await accept.isDisabled(),true);
    await page.getByText('对象内容正确',{exact:true}).locator('input').check();
    await page.getByText('轮廓完整、背景与边缘可用',{exact:true}).locator('input').check();
    assert.equal(await accept.isDisabled(),true);
    await page.getByRole('button',{name:'保存审阅'}).click();
    await page.waitForFunction(()=>document.querySelector('[role=status]').textContent==='审阅已保存。');
    assert.equal(await accept.isEnabled(),true);
    await accept.click();
    await page.getByRole('button',{name:'已加入素材'}).waitFor();
    assert.equal(await page.getByRole('button',{name:'保存审阅'}).isDisabled(),true);
    assert.equal(await page.getByRole('button',{name:'仅重新生成这个对象',exact:true}).isDisabled(),true);
    assert.equal(await page.locator('.html-sheet-card h4 img').count(),0);
    await page.evaluate(()=>{accepted=false; conflict=true; HtmlAssetSheets.close();});
    await page.evaluate(()=>HtmlAssetSheets.open(document.querySelector('main'),{id:'p1',visual_backend:'html'}));
    await page.getByText('对象内容正确',{exact:true}).locator('input').uncheck();
    await page.getByRole('button',{name:'保存审阅'}).click();
    await page.waitForFunction(()=>document.querySelector('[role=status]').textContent.includes('本地选择已保留'));
    assert.equal(await page.getByText('对象内容正确',{exact:true}).locator('input').isChecked(),false);
    await page.evaluate(()=>{HtmlAssetSheets.close();produced=false;});
    await page.evaluate(()=>HtmlAssetSheets.open(document.querySelector('main'),{id:'p2',visual_backend:'html'}));
    assert.equal(await page.locator('.html-sheet-card').count(),0);
    assert((await page.evaluate(()=>calls)).some(c=>c[1]==='/api/projects/p2/html-asset-sheets'));
    await page.evaluate(()=>{HtmlAssetSheets.close();window.restoreTask=true;window.slow=true;window.cancelled=false;HtmlAssetSheets.open(document.querySelector('main'),{id:'p2',visual_backend:'html'});});
    await page.getByRole('button',{name:'停止生成'}).waitFor();
    await page.getByRole('button',{name:'停止生成'}).click();
    await page.waitForFunction(()=>document.querySelector('[role=status]').textContent.includes('已请求停止'));
    assert((await page.evaluate(()=>calls)).some(c=>c[1]==='/api/projects/p2/html-review/tasks/task-one/cancel'));
    await page.evaluate(()=>HtmlAssetSheets.open(document.querySelector('main'),{id:'p3',visual_backend:'image'}));
    assert.equal(await page.locator('.html-asset-sheets').count(),0);
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({passed:true,checks:['generate/poll','cleanup opt-in','advisory text/XSS/manual gates','AI task','single retry','failed-object retry','old-candidate assessment retained','accepted retry locked','gates','review/accept','locked','XSS','409 draft','project isolation','reload task','stop','image hidden'],pageErrors:errors}));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
