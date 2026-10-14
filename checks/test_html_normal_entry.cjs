"use strict";
// Normal application DOM with explicit local HTTP doubles; no paid providers.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('../html_engine/node_modules/playwright');
const root=path.resolve(__dirname,'../static');
(async()=>{
 const server=http.createServer((req,res)=>{
  const file=path.resolve(root,new URL(req.url,'http://localhost').pathname.replace(/^\//,'')||'index.html');
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.writeHead(404).end();return;}
  res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,executablePath:require('../html_engine/tools/browser-runtime.cjs').resolveBrowser(chromium)});
 try{
  const page=await browser.newPage();const creates=[],loads=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const project={id:'html-entry-fixture',name:'fixture',visual_backend:'html',ai_mode:'manual',current_step:3,step_status:{}};
  await page.route('**/api/**',async route=>{
   const req=route.request(),url=new URL(req.url());loads.push(url.pathname);
   let result={success:true,projects:[],accounts:[],packages:[],configs:[],settings:{},active:false};
   if(url.pathname==='/api/projects'&&req.method()==='POST'){creates.push(req.postDataJSON());result={success:true,project};}
   else if(url.pathname==='/api/projects')result=[];
   else if(url.pathname==='/api/projects/html-entry-fixture')result=project;
   else if(url.pathname.endsWith('/steps/2/result'))result={success:true,contract:{slides:[]}};
   await route.fulfill({json:result});
  });
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction(()=>document.getElementById('modal-create')?.querySelector('#input-project-article'));
  await page.evaluate(()=>{document.getElementById('modal-create').style.display='flex';});
  await page.locator('#input-project-name').fill('HTML fixture');
  await page.locator('[data-profile-option="ai_mode"][data-value="manual"]').click();
  await page.locator('[data-profile-option="canvas_profile"][data-value="portrait_9_16"]').click();
  await page.locator('#input-project-visual-backend').selectOption('html');
  assert.equal(await page.locator('[data-profile-option="canvas_profile"].active').getAttribute('data-value'),'landscape_16_9');
  await page.locator('[data-profile-option="canvas_profile"][data-value="portrait_9_16"]').click();
  await page.locator('#btn-create-submit').click();
  assert.equal(creates.length,0);
  await page.locator('[data-profile-option="canvas_profile"][data-value="landscape_16_9"]').click();
  await page.locator('#btn-create-submit').click();
  await page.waitForFunction(()=>document.body.classList.contains('workspace-open'));
  await page.waitForFunction(()=>document.querySelector('.step-item[data-step="5"]')?.textContent.includes('场景与对象'));
  assert.equal(creates.length,1);assert.equal(creates[0].visual_backend,'html');
  assert.equal(creates[0].canvas_profile,'landscape_16_9');
  assert.match(await page.locator('.step-item[data-step="5"]').innerText(),/场景与对象/);
  assert.match(await page.locator('.step-item[data-step="3"]').innerText(),/视觉素材/);
  const from=loads.length;
  await page.evaluate(()=>loadStepData(5));
  assert.equal(loads.slice(from).some(u=>/\/steps\/(3|5)\//.test(u)),false);
  await page.evaluate(()=>exitWorkspace());
  assert.equal(await page.evaluate(()=>PPTFlow.visibleStepLabel(5)),'AI Mask 标注');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,checks:['HTML request identity','default image retained','16:9 selection','invalid combination blocks POST','HTML sidebar labels','no raster stage requests','image flow restored']}));
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
