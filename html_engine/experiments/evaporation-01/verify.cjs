const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');const {chromium}=require('../../node_modules/playwright');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{const browser=await chromium.launch({executablePath:process.env.HPS_CHROME});const errors=[];try{
  const page=await browser.newPage({viewport:{width:1648,height:1180},deviceScaleFactor:1});page.on('pageerror',e=>errors.push(e.message));
  fs.mkdirSync(path.join(__dirname,'evidence'),{recursive:true});
  await page.goto(pathToFileURL(path.join(__dirname,'reuse.html')).href);await page.evaluate(()=>reuseReady);
  const bounds=await page.evaluate(()=>reuseEffects.map(fx=>{const e=fx.element,r=document.createRange();r.selectNodeContents(e);return {type:e.dataset.effect,overflow:e.classList.contains('flat-paper')&&r.getBoundingClientRect().width>e.clientWidth,geometry:fx.geometry()};}));assert.ok(bounds.every(x=>!x.overflow));
  const rejects=await page.evaluate(()=>{const cases=[['wrong',{}],['paper',{text:'超过十二个字的标签应该被拒绝掉'}],['flow',{count:25}],['arrow',{stroke:9}],['sun',{width:50}],['text',{fontSize:12}]];return cases.map(([type,p])=>{try{FlatEffects.mount(document.body,type,p);return false}catch{return true}})});assert.ok(rejects.every(Boolean));
  await page.screenshot({path:path.join(__dirname,'evidence/reuse.png'),fullPage:true});
  const total=await page.evaluate(()=>reuseEffects.length);assert.equal(total,14);
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);await page.evaluate(()=>evapReady);
  const times=[0,3000,7000,12000,16000,19999],frames=[];
  for(const t of times){await page.evaluate(t=>evap.renderAt(t),t);const buffer=await page.locator('#frame').screenshot();await page.evaluate(()=>evap.renderAt(0));await page.evaluate(t=>evap.renderAt(t),t);assert.equal(hash(buffer),hash(await page.locator('#frame').screenshot()));fs.writeFileSync(path.join(__dirname,'evidence',t+'.png'),buffer);frames.push({time:t,sha256:hash(buffer)});}
  const geometry=await page.evaluate(()=>['title','sun','particles','direction','term','state','explanation','beaker'].map(id=>({id,...evap.geometry(id)})));assert.equal(geometry.find(o=>o.id==='particles').particles.length,6);
  const overflows=await page.evaluate(()=>[...document.querySelectorAll('.flat-text,.flat-paper')].map(e=>{const r=document.createRange();r.selectNodeContents(e);const a=r.getBoundingClientRect(),b=e.getBoundingClientRect();return {id:e.dataset.effect,overflow:a.width>b.width+2||a.height>b.height+2}}).filter(x=>x.overflow));assert.deepEqual(overflows,[]);
  await page.locator('#play').click();await page.waitForTimeout(650);assert.ok(await page.evaluate(()=>evap.time>300&&evap.playing));await page.locator('#pause').click();const paused=await page.evaluate(()=>evap.time);await page.waitForTimeout(200);assert.equal(await page.evaluate(()=>evap.time),paused);
  await page.locator('#seek').fill('17000');await page.locator('#seek').dispatchEvent('input');assert.equal(await page.evaluate(()=>evap.time),17000);
  const subtitleChecks=await page.evaluate(()=>{
    evap.renderAt(19999);const layer=document.querySelector('#subtitle-layer'), content=document.querySelector('#content-layer');
    const before=JSON.stringify(evap.geometry('state'));const results=[];
    for(const size of [20,32,44]){evap.setSubtitleFont(size);for(const beat of EvapDefinition.beats){evap.renderAt(beat.startMs);const a=layer.getBoundingClientRect(), b=document.querySelector('.caption').getBoundingClientRect();results.push(b.top>=a.top&&b.bottom<=a.bottom&&b.left>=a.left&&b.right<=a.right);}}
    evap.setSubtitleFont(32);evap.renderAt(19999);
    const edge=layer.getBoundingClientRect().top;
    const clear=[...content.children].every(e=>e.getBoundingClientRect().bottom<=edge+1);
    const invalid=[19,45].every(n=>{try{evap.setSubtitleFont(n);return false}catch{return true}});
    return {fontsFit:results.every(Boolean),contentClear:clear,invalidRejected:invalid,layoutStable:before===JSON.stringify(evap.geometry('state')),zoneHeight:layer.offsetHeight};
  });assert.deepEqual(subtitleChecks,{fontsFit:true,contentClear:true,invalidRejected:true,layoutStable:true,zoneHeight:100});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'evidence/verification.json'),JSON.stringify({libraryVersion:'0.1.0',sceneRevision:2,subtitleChecks,reuseInstances:total,rejectedInvalidCases:rejects.length,frames,geometry,textBounds:'passed',seekOrderPixels:'passed',actualPlaybackAdvances:'passed',pause:'passed',scrub:'passed',pageErrors:errors,browser:browser.version(),userVisualApproval:'pending'},null,2)+'\n');console.log('14 reuse variants, 6 invalid cases, 6 deterministic frames, actual playback/pause/scrub passed.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
