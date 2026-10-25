"""Real Chromium interaction with the self-contained correction artifact."""
import json

from checks.test_html_reference_workbench import ROOT, session
from runtime_support import run_subprocess_killable


def test_structured_correction_import_zoom_and_download_real_browser(tmp_path):
    _,folder,_=session(tmp_path)
    script=tmp_path/'workbench-ui.cjs'
    script.write_text(r'''
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const root=process.argv[2],folder=process.argv[3];
const {chromium}=require(path.join(root,'html_engine/node_modules/playwright'));
const {captureLaunchOptions}=require(path.join(root,'html_engine/tools/browser-runtime.cjs'));
(async()=>{
 const browser=await chromium.launch(captureLaunchOptions(chromium));
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(folder,'index.html')).href);
  if(!((await page.locator('#expected').textContent()).includes('alpha')))throw Error('Missing exact source');
  await page.locator('#transcript').fill('alpha');await page.locator('#identity').fill('Manually checked against reference');
  for(const [id,value]of Object.entries({xPx:700,yPx:50,widthPx:100,heightPx:16}))await page.locator('#'+id).fill(String(value));
  await page.locator('#apply').click();
  if(await page.locator('.box').count()!==1)throw Error('No form overlay');
  const corrected=JSON.parse(await page.locator('#mapping').inputValue());
  if(corrected.mapping.targets[0].part_regions[0].regions[0].text!=='alpha')throw Error('Form did not update correction');
  await page.locator('#widthPx').fill('900');await page.locator('#apply').click();
  if(!(await page.locator('#status').textContent()).includes('整数像素'))throw Error('Out-of-bounds box accepted');
  if(JSON.stringify(JSON.parse(await page.locator('#mapping').inputValue()))!==JSON.stringify(corrected))throw Error('Invalid form changed mapping');
  await page.locator('#zoom').selectOption('200');
  if(await page.locator('#reference').evaluate(n=>n.style.width)!=='200%')throw Error('Zoom not applied');
  const downloadPromise=page.waitForEvent('download');await page.locator('#download').click();
  const download=await downloadPromise;await download.saveAs(path.join(folder,'downloaded.json'));
  if(JSON.stringify(JSON.parse(fs.readFileSync(path.join(folder,'downloaded.json'),'utf8')))!==JSON.stringify(corrected))throw Error('Download differs');
  const bad=structuredClone(corrected);bad.session_sha256='wrong';
  fs.writeFileSync(path.join(folder,'wrong-session.json'),JSON.stringify(bad));
  await page.locator('#import').setInputFiles(path.join(folder,'wrong-session.json'));
  await page.waitForFunction(()=>document.getElementById('status').textContent.includes('其他会话'));
  if(JSON.stringify(JSON.parse(await page.locator('#mapping').inputValue()))!==JSON.stringify(corrected))throw Error('Bad import changed mapping');
  await page.locator('#import').setInputFiles(path.join(folder,'downloaded.json'));
  await page.waitForFunction(()=>document.getElementById('status').textContent.includes('预览已更新'));
  await page.locator('#zoom').selectOption('100');
  await page.screenshot({path:path.join(folder,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile overflow '+JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('*')].filter(n=>n.getBoundingClientRect().right>innerWidth+1).map(n=>({tag:n.tagName,id:n.id,width:n.getBoundingClientRect().width,right:n.getBoundingClientRect().right})))));
  await page.screenshot({path:path.join(folder,'mobile.png'),fullPage:true});
  if(errors.length)throw Error(errors.join('\n'));
  fs.writeFileSync(path.join(folder,'ui-check.json'),JSON.stringify({passed:true,form:true,import:true,download:true,zoom:true,invalid_box:true,wrong_session:true,mobile:true,page_errors:errors,provider_calls:0}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
''',encoding='utf-8')
    result=run_subprocess_killable(['node',str(script),str(ROOT),str(folder)],cwd=str(ROOT),
        capture_output=True,text=True,encoding='utf-8',errors='replace',timeout_sec=60)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert json.loads((folder/'ui-check.json').read_text(encoding='utf-8'))['passed']


def test_embedded_identity_text_cannot_close_script_element(tmp_path):
    from html_reference_workbench_ui import render_workbench
    from PIL import Image
    image=tmp_path/'image.png';Image.new('RGB',(10,10)).save(image)
    correction={'session_sha256':'x','mapping':{'targets':[]},'note':'</script><img src=x onerror=alert(1)>'}
    rendered=render_workbench(image,image,correction,[10,10],[])
    assert '</script><img' not in rendered
    assert r'\u003c/script>' in rendered
