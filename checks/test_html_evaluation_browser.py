"""Real browser over isolated Web API: labels/review/experiment queue/cancel."""
import socket
import threading
import time
from pathlib import Path
import uvicorn
from checks.test_html_reference_api import api as api
from checks.test_html_annotation_store import dataset_fixture
from runtime_support import run_subprocess_killable

ROOT=Path(__file__).resolve().parents[1]


def test_annotation_workbench_real_browser_and_experiment_queue(api,tmp_path):
    dataset_fixture(api.run)
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(api.client.app,host='127.0.0.1',port=port,log_level='error',lifespan='off'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.02)
    script=tmp_path/'browser.cjs'
    script.write_text(r'''
const fs=require('node:fs'),path=require('node:path');const [root,origin,project,out]=process.argv.slice(2);
const {chromium}=require(path.join(root,'html_engine/node_modules/playwright'));
const {captureLaunchOptions}=require(path.join(root,'html_engine/tools/browser-runtime.cjs'));
(async()=>{const browser=await chromium.launch(captureLaunchOptions(chromium));try{
const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route(origin+'/fixture',r=>r.fulfill({contentType:'text/html',body:'<section id="host"></section>'}));
await page.goto(origin+'/fixture');
await page.evaluate(()=>{window.API={get:async url=>{const r=await fetch(url);const v=await r.json();if(!r.ok)throw Error(v.detail);return v;},post:async(url,body)=>{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw Error(v.detail);return v;}};});
await page.addScriptTag({path:path.join(root,'static/html_evaluation_panel.js')});
await page.evaluate(project=>HtmlEvaluationPanel.mount(document.querySelector('#host'),{project:{id:project},slideId:'s'}),project);
await page.getByText('评测标注与配对实验',{exact:true}).click();await page.getByRole('button',{name:'读取评测数据集',exact:true}).click();
await page.getByLabel('评测数据集').selectOption('labels');
for(const id of ['page-0','page-1']){
await page.getByLabel('标注样本').selectOption(id);await page.getByRole('button',{name:'打开原图标注',exact:true}).click();
const frame=page.frameLocator('iframe');await frame.locator('#use-correction').waitFor({state:'visible'});
await frame.locator('#identity').fill('对照原图逐字核对alpha及完整边界。');await frame.locator('#apply').click();await frame.locator('#use-correction').click();
await page.getByLabel('标注者',{exact:true}).fill('Alice');await page.getByRole('button',{name:'保存标注草稿',exact:true}).click();
await page.locator('[role=status]').filter({hasText:'标注版本 1'}).waitFor();
await page.getByLabel('独立复核者',{exact:true}).fill('Bob');await page.getByLabel('复核依据').fill('逐行核对原图、文字和容器边界。');
await page.getByRole('button',{name:'复核通过并封存',exact:true}).click();
await page.locator('[role=status]').filter({hasText:'标注版本 2 · reviewed'}).waitFor();
}
await page.getByText('运行固定样本配对实验',{exact:true}).click();await page.getByRole('button',{name:'开始配对实验（调用项目模型）',exact:true}).click();
await page.getByRole('button',{name:'停止配对实验',exact:true}).waitFor();
await page.getByRole('button',{name:'停止配对实验',exact:true}).click();
await page.locator('pre').filter({hasText:'cancelled'}).waitFor();
await page.screenshot({path:path.join(out,'annotation-experiment.png'),fullPage:true});
await page.evaluate(()=>HtmlEvaluationPanel.clear(document.querySelector('#host')));
if(await page.locator('iframe').count())throw Error('Context cleanup retained workbench');
if(errors.length)throw Error(errors.join('\n'));
fs.writeFileSync(path.join(out,'browser-check.json'),JSON.stringify({passed:true,saved_two_samples:true,independent_review:true,experiment_queued_and_cancelled:true,provider_calls:0,page_errors:errors}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
''',encoding='utf-8')
    try:
        result=run_subprocess_killable(['node',str(script),str(ROOT),f'http://127.0.0.1:{port}',api.project.id,str(tmp_path)],
            cwd=str(ROOT),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout_sec=90)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
        assert not api.calls
    finally:server.should_exit=True;thread.join(timeout=5)
