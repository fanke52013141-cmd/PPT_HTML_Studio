/* Render the requested static review artifact and record its actual DOM/resources. */
const fs=require('fs');
const path=require('path');
const {pathToFileURL}=require('url');
const {chromium}=require('playwright');
const crypto=require('crypto');
(async()=>{
  const out=path.resolve(process.argv[2]);
  const browser=await chromium.launch({headless:true,executablePath:'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe'});
  const evidence={kind:'actual static browser rendering',errors:[],audioGenerated:false};
  try{
    const page=await browser.newPage({viewport:{width:1600,height:900},deviceScaleFactor:1});
    page.on('pageerror',e=>evidence.errors.push(e.message));
    await page.goto(pathToFileURL(path.join(out,'html-effect.html')).href+'?view=raw');
    await page.waitForFunction(()=>window.reconstructionReady||window.reconstructionError);
    if(await page.evaluate(()=>window.reconstructionError))throw new Error(await page.evaluate(()=>window.reconstructionError));
    evidence.browser=browser.version();
    evidence.dom=await page.evaluate(()=>({objects:[...document.querySelectorAll('[data-object-id]')].map(node=>({id:node.dataset.objectId,kind:node.dataset.kind,text:node.innerText,visibleMapping:node.dataset.visibleMapping?JSON.parse(node.dataset.visibleMapping):undefined})),images:[...document.querySelectorAll('#stage img')].map(img=>({complete:img.complete,width:img.naturalWidth,height:img.naturalHeight})),fontReady:document.fonts.check('24px "Microsoft YaHei"'),background:getComputedStyle(document.querySelector('#stage')).backgroundColor,audioNodes:document.querySelectorAll('audio,video').length}));
    await page.locator('#stage').screenshot({path:path.join(out,'html-effect.png')});
    await page.goto(pathToFileURL(path.join(out,'html-effect.html')).href);
    await page.waitForFunction(()=>window.reconstructionReady);
    await page.screenshot({path:path.join(out,'review-page.png')});
    await page.getByRole('button',{name:'滑动对照'}).click();
    await page.screenshot({path:path.join(out,'comparison.png')});
    await page.getByRole('button',{name:'实际 HTML',exact:true}).click();
    await page.locator('#hide-illustrations').check();
    await page.screenshot({path:path.join(out,'code-only.png')});
    evidence.screenshots=['html-effect.png','review-page.png','comparison.png','code-only.png'].map(file=>({file,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(out,file))).digest('hex')}));
    evidence.status=evidence.errors.length?'render_errors':'rendered';
    fs.writeFileSync(path.join(out,'browser-evidence.json'),JSON.stringify(evidence,null,2));
    console.log(JSON.stringify({status:evidence.status,objects:evidence.dom.objects.length,images:evidence.dom.images.length,fontReady:evidence.dom.fontReady,audioNodes:evidence.dom.audioNodes,errors:evidence.errors}));
  }finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
