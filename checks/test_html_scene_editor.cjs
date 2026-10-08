"use strict";
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
const {spawn}=require('child_process');
const {chromium}=require('../html_engine/node_modules/playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),run=fs.mkdtempSync(path.join(os.tmpdir(),'hps-editor-browser-'));
 const child=spawn(path.join(root,'.venv/Scripts/python.exe'),[path.join(__dirname,'test_html_scene_editor_fixture.py'),run],{cwd:root,windowsHide:true});
 let stderr='';child.stderr.on('data',d=>stderr+=d);
 let browser;
 try{
  const port=await new Promise((resolve,reject)=>{
   let text='';const timer=setTimeout(()=>reject(Error('fixture startup timeout '+stderr)),20000);
   child.stdout.on('data',d=>{text+=d;try{const value=JSON.parse(text.trim());clearTimeout(timer);resolve(value.port);}catch{}});
   child.on('exit',code=>{clearTimeout(timer);reject(Error(`fixture exit ${code}: ${stderr}`));});
  });
  browser=await chromium.launch({headless:true,executablePath:process.env.HPS_CHROME||'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'});
  const page=await browser.newPage({viewport:{width:1500,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const url=`http://127.0.0.1:${port}`;
  await page.goto(url);
  await page.waitForFunction(()=>document.querySelector('[data-editor-status]')?.textContent.includes('修订 1'));
  const frame=()=>page.frames().find(f=>f.url()==='about:srcdoc');
  await frame().locator('[data-object-id="header"]').click();
  await page.locator('[data-field="title"]').fill('浏览器人工标题');
  await page.locator('[data-field="title"]').blur();
  await page.locator('[data-beat="enter"]').selectOption('b2');
  await page.locator('[data-field="binding.enter.offsetMs"]').fill('120');await page.locator('[data-field="binding.enter.offsetMs"]').blur();
  await page.getByRole('button',{name:'添加 emphasize',exact:true}).click();
  await page.locator('[data-field="emphasize.startMs"]').fill('8000');await page.locator('[data-field="emphasize.startMs"]').blur();
  await page.getByRole('button',{name:'校验预览',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-editor-status]').textContent.includes('修订 1'));
  await page.getByRole('button',{name:'保存修改',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-editor-status]').textContent.includes('已保存'));
  await page.locator('[data-object="subject"]').click();
  await page.locator('[data-field="assetRef"]').selectOption('test-blue');
  await page.getByRole('button',{name:'校验预览',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-editor-status]').textContent.includes('修订 2'));
  const img=frame().locator('[data-object-id="subject"] img');
  const anchorErrors=[];
  for(const width of [1500,1200,900]){
   await page.setViewportSize({width,height:1100});
   await page.getByRole('button',{name:'在图中定位',exact:true}).click();
   const box=await img.boundingBox();await page.mouse.click(box.x+box.width*.55,box.y+box.height*.6);
   const x=Number(await page.locator('[data-anchor="0.x"]').inputValue()),y=Number(await page.locator('[data-anchor="0.y"]').inputValue());
   anchorErrors.push(Math.max(Math.abs(x-.55)*300,Math.abs(y-.6)*400));
  }
  assert(anchorErrors.every(e=>e<=1),JSON.stringify(anchorErrors));
  await page.getByRole('button',{name:'保存修改',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-editor-status]').textContent.includes('已保存'));
  const saved=await (await page.request.get(url+'/api/projects/isolated/html-visual/condensation/editor')).json();
  assert.equal(saved.scene.nodes.find(n=>n.id==='header').title,'浏览器人工标题');
  assert.equal(saved.binding.actions['header:enter'].beatId,'b2');
  assert(saved.scene.nodes.find(n=>n.type==='image').assetRef.id.startsWith('edit-'));
  assert(saved.resources.assets.some(a=>a.id==='test-green'));
  await page.setViewportSize({width:1500,height:1100});
  await page.screenshot({path:path.join(root,'docs/plans/html-backend-development/scene-editor-evidence.png'),fullPage:true});
  await page.reload();await page.waitForFunction(()=>document.querySelector('[data-editor-status]')?.textContent.includes('修订 3'));
  await page.locator('[data-object="header"]').click();assert.equal(await page.locator('[data-field="title"]').inputValue(),'浏览器人工标题');
  // Pixel reproducibility at the export canvas scale avoids fractional CSS
  // compositing differences; pointer accuracy above covers scaled previews.
  await page.evaluate(()=>{const f=document.querySelector('iframe');f.style.width='1600px';f.style.height='900px';});
  await frame().waitForFunction(()=>document.getElementById('viewport').clientWidth===1600);
  const hashes=[],reports=[];
  for(const t of [9000,1000,9000]){
   await page.getByRole('spinbutton',{name:'跳转毫秒'}).fill(String(t));await page.getByRole('spinbutton',{name:'跳转毫秒'}).blur();
   await frame().waitForFunction(t=>visualPlayer.timeMs===t,t);
   await page.evaluate(()=>window.scrollTo(0,0));
   const shot=await frame().locator('.visual-stage').screenshot();
   reports.push(await frame().evaluate(()=>({geometry:visualPlayer.seek(visualPlayer.timeMs),html:document.getElementById('viewport').innerHTML})));
   hashes.push(require('crypto').createHash('sha256').update(shot).digest('hex'));
  }
  assert.deepEqual(reports[0],reports[2]);
  assert.equal(hashes[0],hashes[2]);
  await frame().evaluate(()=>{
   const node=document.querySelector('[data-object-id="headline"] span').firstChild;
   const range=document.createRange();range.setStart(node,0);range.setEnd(node,3);
   getSelection().removeAllRanges();getSelection().addRange(range);
  });
  await page.getByRole('button',{name:'读取画面文字选区',exact:true}).click();
  const textRange=JSON.parse(await page.locator('[data-editor-status]').textContent());
  assert.equal(textRange.kind,'text_range');assert.equal(textRange.start,0);assert.equal(textRange.end,3);assert(textRange.rects[0].width>0);
  await page.locator('[data-field="title"]').fill('保留冲突草稿');await page.locator('[data-field="title"]').blur();
  const concurrent=structuredClone(saved);concurrent.scene.nodes.find(n=>n.id==='header').title='服务器并发版本';
  const response=await page.request.put(url+'/api/projects/isolated/html-visual/condensation/editor',{data:{scene:concurrent.scene,binding:concurrent.binding,expected_revision:3,anchor_overrides:{}}});assert.equal(response.status(),200);
  await page.getByRole('button',{name:'保存修改',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-editor-status]').textContent.includes('修订冲突'));
  assert.equal(await page.locator('[data-field="title"]').inputValue(),'保留冲突草稿');
  await page.getByRole('button',{name:'比较服务器版本',exact:true}).click();await page.waitForFunction(()=>document.querySelector('pre').textContent.includes('服务器并发版本'));
  await page.evaluate(()=>HtmlSceneEditor.open(document.getElementById('host'),'isolated','condensation'));
  assert.equal(await page.locator('[data-field="title"]').inputValue(),'保留冲突草稿');
  assert.deepEqual(errors,[]);
  const evidence={passed:true,realBrowser:true,isolatedFixture:true,realSharedPlayer:true,saveReopen:true,conflictDraftRetained:true,anchorErrors,seekDeterministic:true,seekPixelScale:1600,errors};
  fs.writeFileSync(path.join(root,'docs/plans/html-backend-development/scene-editor-browser-evidence.json'),JSON.stringify(evidence,null,2));
  console.log(JSON.stringify(evidence));
 }finally{if(browser)await browser.close();child.kill();await new Promise(r=>child.once('exit',r));fs.rmSync(run,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
