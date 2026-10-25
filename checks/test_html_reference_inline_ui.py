"""Real parent/sandbox drag correction, explicit original POST and message guards."""
from checks.test_html_reference_workbench import session,ROOT
from runtime_support import run_subprocess_killable


def test_drag_apply_and_submit_without_json_and_reject_wrong_channels(tmp_path):
    _,folder,_=session(tmp_path)
    script=tmp_path/'inline.cjs'
    script.write_text(r'''
const path=require('node:path'),fs=require('node:fs');const root=process.argv[2],folder=process.argv[3];
const {chromium}=require(path.join(root,'html_engine/node_modules/playwright'));
const {captureLaunchOptions}=require(path.join(root,'html_engine/tools/browser-runtime.cjs'));
(async()=>{const browser=await chromium.launch(captureLaunchOptions(chromium));try{
 const page=await browser.newPage({viewport:{width:1500,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const correction=JSON.parse(fs.readFileSync(path.join(folder,'correction.json'),'utf8'));
 await page.route('http://127.0.0.1:9999/**',route=>route.fulfill({contentType:'text/html',body:route.request().url().endsWith('/workbench')?fs.readFileSync(path.join(folder,'index.html'),'utf8'):'<section id="host"><div><div data-html-task></div></div></section>'}));
 await page.goto('http://127.0.0.1:9999/');
 await page.evaluate(c=>{window.calls=[];window.API={get:async()=>({reference:{key:c.session_sha256,unresolved_targets:['caption'],workbench_url:'/workbench'}}),post:async(url,body)=>{calls.push({url,body});return {task:{id:'review',status:'succeeded',result:{review:{result:{status:'pass'}}}}};}};},correction);
 await page.addScriptTag({path:path.join(root,'static/html_reference_panel.js')});
 await page.evaluate(()=>HtmlReferenceReview.refresh(document.querySelector('#host'),{project:{id:'p'},slideId:'s'},{id:'original',status:'failed',progress:{reference_workbench:{}}},()=>true));
 await page.getByRole('button',{name:'打开定位复核',exact:true}).click();
 const frame=page.frameLocator('iframe');await frame.locator('#use-correction').waitFor({state:'visible'});
 const submit=page.getByRole('button',{name:'提交修正，继续审核',exact:true});
 await page.evaluate(c=>window.postMessage({type:'ppt-reference-correction',nonce:'forged',session:c.session_sha256,correction:c},'*'),correction);
 if(!await submit.isDisabled())throw Error('Foreign source accepted');
 await frame.locator('body').evaluate((_,c)=>parent.postMessage({type:'ppt-reference-correction',nonce:'wrong',session:c.session_sha256,correction:c},'*'),correction);
 if(!await submit.isDisabled())throw Error('Wrong nonce accepted');
 await frame.locator('body').evaluate((_,c)=>parent.postMessage({type:'ppt-reference-correction',...channel,session:'wrong-session',correction:c},'*'),correction);
 if(!await submit.isDisabled())throw Error('Wrong session accepted');
 await frame.locator('#transcript').fill('alpha');await frame.locator('#identity').fill('Checked exact alpha against reference');
 const bounds=await frame.locator('#reference').boundingBox();
 const size=await frame.locator('#data').evaluate(n=>JSON.parse(n.textContent).size);
 const x=bounds.x+bounds.width*700/size[0],y=bounds.y+bounds.height*50/size[1];
 await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+bounds.width*100/size[0],y+bounds.height*16/size[1],{steps:4});await page.mouse.up();
 if(Math.abs(Number(await frame.locator('#xPx').inputValue())-700)>1)throw Error('Drag pixel conversion wrong');
 await frame.locator('#apply').click();await frame.locator('#use-correction').click();
 await submit.waitFor({state:'visible'});await submit.click();
 const calls=await page.evaluate(()=>window.calls);
 if(calls.length!==1||!calls[0].url.endsWith('/reference/original/resume')||calls[0].body.mapping.targets[0].part_regions[0].regions[0].text!=='alpha')throw Error('Wrong production correction payload');
 await page.screenshot({path:path.join(folder,'inline-panel.png'),fullPage:true});
 await frame.locator('body').evaluate(()=>{window.oldChannel={...channel};});
 await page.evaluate(()=>HtmlReferenceReview.refresh(document.querySelector('#host'),{project:{id:'p2'},slideId:'s2'},{id:'original2',status:'failed',progress:{reference_workbench:{}}},()=>true));
 await page.getByRole('button',{name:'打开定位复核',exact:true}).click();
 await frame.locator('#use-correction').waitFor({state:'visible'});
 await page.evaluate(c=>window.dispatchEvent(new MessageEvent('message',{source:document.querySelector('iframe').contentWindow,data:{type:'ppt-reference-correction',nonce:'old-nonce',session:c.session_sha256,correction:c}})),correction);
 if(!await submit.isDisabled())throw Error('Stale message survived project switch');
 await page.evaluate(()=>HtmlReferenceReview.clear(document.querySelector('#host')));
 if(await page.locator('[data-reference-review]').isVisible())throw Error('Panel survived context clear');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(folder,'inline-check.json'),JSON.stringify({passed:true,drag:true,submit:true,no_json_file:true,foreign_source_rejected:true,wrong_nonce_rejected:true,provider_calls:0}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
''',encoding='utf-8')
    result=run_subprocess_killable(['node',str(script),str(ROOT),str(folder)],cwd=str(ROOT),
        capture_output=True,text=True,encoding='utf-8',errors='replace',timeout_sec=60)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
