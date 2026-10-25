"""Real Chromium checks for production reference correction and explicit reuse controls."""
from pathlib import Path
from runtime_support import run_subprocess_killable

ROOT=Path(__file__).resolve().parents[1]


def test_reference_panel_submit_continue_clear_and_explicit_assets(tmp_path):
    script=tmp_path/'panel.cjs'
    script.write_text(r'''
const path=require('node:path'),fs=require('node:fs');
const root=process.argv[2],out=process.argv[3];
const {chromium}=require(path.join(root,'html_engine/node_modules/playwright'));
const {captureLaunchOptions}=require(path.join(root,'html_engine/tools/browser-runtime.cjs'));
(async()=>{const browser=await chromium.launch(captureLaunchOptions(chromium));try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent('<section id="host"><div class="html-workspace-toolbar"></div><div><div data-html-task></div></div></section>');
 await page.evaluate(()=>{window.calls=[];window.API={get:async url=>url.endsWith('/reusable-assets')?{assets:[{id:'asset-one',version:'1.0.0',sha256:'b'.repeat(64),description:'subject',source_pages:['first'],size:{width:100,height:80}}]}:{reference:{key:'a'.repeat(64),unresolved_targets:['title'],workbench_url:'about:blank',continuation_design_key:'design-one'}},post:async(url,body)=>{calls.push({url,body});return {task:{id:'review-one',status:'succeeded',result:{review:{result:{status:'pass'}},reference_review_key:'c'.repeat(64)}}};}};});
 for(const file of ['html_reference_panel.js','html_asset_reuse.js'])await page.addScriptTag({path:path.join(root,'static',file)});
 await page.evaluate(async()=>{window.ctx={project:{id:'project-one'},slideId:'second'};await HtmlReferenceReview.refresh(document.querySelector('#host'),ctx,{id:'failed-one',status:'failed',progress:{reference_workbench:{}}},()=>true);HtmlAssetReuse.mount(document.querySelector('#host'),ctx);});
 await page.getByRole('button',{name:'打开定位复核',exact:true}).click();
 if(await page.locator('iframe').getAttribute('sandbox')!=='allow-scripts allow-downloads')throw Error('Unsafe workbench sandbox');
 await page.locator('input[type=file]').setInputFiles({name:'correction.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({session_sha256:'a'.repeat(64),mapping:{targets:[]}}))});
 await page.getByRole('button',{name:'提交修正，继续审核',exact:true}).click();
 await page.getByRole('button',{name:'复用原设计继续还原',exact:true}).click();
 const calls=await page.evaluate(()=>window.calls);
 if(!calls[0].url.endsWith('/reference/failed-one/resume')||calls[1].body.design_candidate_key!=='design-one'||calls[1].body.reference_review_key!=='c'.repeat(64))throw Error('Wrong continuation identity');
 await page.locator('summary').click();await page.getByRole('button',{name:'读取可复用素材'}).click();
 await page.getByLabel('已有素材').selectOption('0');
 const selected=await page.evaluate(()=>HtmlAssetReuse.selection(document.querySelector('#host')));
 if(selected.length!==1||selected[0].slot!=='subject'||selected[0].sha256!=='b'.repeat(64))throw Error('Missing explicit asset identity');
 await page.evaluate(()=>{HtmlReferenceReview.clear(document.querySelector('#host'));HtmlAssetReuse.mount(document.querySelector('#host'),{project:{id:'other'},slideId:'third'});});
 if(await page.locator('[data-reference-review]').isVisible()||await page.locator('iframe').getAttribute('src'))throw Error('Old project panel retained');
 if((await page.evaluate(()=>HtmlAssetReuse.selection(document.querySelector('#host')))).length)throw Error('Selection leaked across projects');
 if(errors.length)throw Error(errors.join('\n'));
 await page.screenshot({path:path.join(out,'panel.png'),fullPage:true});
 fs.writeFileSync(path.join(out,'panel-check.json'),JSON.stringify({passed:true,provider_calls:0,continuation:true,project_isolation:true,sandbox:true}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
''',encoding='utf-8')
    result=run_subprocess_killable(['node',str(script),str(ROOT),str(tmp_path)],cwd=str(ROOT),
        capture_output=True,text=True,encoding='utf-8',errors='replace',timeout_sec=60)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
