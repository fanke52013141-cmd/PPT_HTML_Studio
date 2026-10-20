"use strict";
// Actual DOM geometry regression: transparent full-canvas arrow carrier is not paint.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {chromium} = require('../html_engine/node_modules/playwright');
const {checkTemporalPage} = require('../html_engine/tools/temporal-review.cjs');

(async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'html-temporal-vector-'));
  const browser = await chromium.launch(require('../html_engine/tools/browser-runtime.cjs').captureLaunchOptions(chromium));
  try {
    const page = await browser.newPage({viewport: {width: 1000, height: 600}});
    await page.setContent(`<div class="visual-stage" style="position:relative;width:1600px;height:900px;transform:scale(.5);transform-origin:top left">
      <div data-object-id="card" style="position:absolute;left:500px;top:400px;width:200px;height:100px"></div>
      <div data-object-id="arrow" style="position:absolute;left:0;top:0;width:1600px;height:800px">
        <svg width="1600" height="800"><path d="M100 100 H300 L290 90 M300 100 L290 110" stroke="black" fill="none"/></svg>
      </div></div>`);
    await page.evaluate(() => { window.visualPlayer = {seek: t => ({timeMs:t})}; });
    const scene = {durationMs:1000, motion:[], nodes:[{id:'card',type:'card'}, {id:'arrow',type:'arrow'}]};
    const spec = {time_range_ms:[1000,1000], overlap_pairs:[['card','arrow']], clock:'author'};
    const run = async () => checkTemporalPage(page,scene,spec,directory,{});
    let report = await run();
    assert(report.passed, JSON.stringify(report.issues));
    assert(Math.abs(report.frames[0].boxes.arrow.width - 200) < 0.01);
    assert.deepEqual(report.overlapPairs,[['card','arrow']]);
    await page.locator('path').evaluate(el => el.setAttribute('d','M450 420 H700 L690 410 M700 420 L690 430'));
    report = await run();
    assert(report.issues.some(i => i.code === 'TEMPORAL_OVERLAP'));
    await page.locator('path').evaluate(el => el.setAttribute('d','M100 810 H300 L290 800 M300 810 L290 820'));
    report = await run();
    assert(report.issues.some(i => i.code === 'TEMPORAL_SAFE_ZONE' && i.targets.includes('arrow')));
    // A diagonal's empty bounding-box area must not be mistaken for painted line.
    await page.locator('[data-object-id="card"]').evaluate(el => Object.assign(el.style,{left:'100px',top:'600px',width:'100px',height:'80px'}));
    await page.locator('path').evaluate(el => el.setAttribute('d','M50 50L750 750'));
    report=await run();assert(report.passed,JSON.stringify(report.issues));
    // The same relation may enter its declared chart target, but may not cross text there.
    scene.nodes[1].from={objectId:'source'};scene.nodes[1].to={objectId:'card'};
    await page.locator('[data-object-id="card"]').evaluate(el => Object.assign(el.style,{left:'500px',top:'400px',width:'200px',height:'100px'}));
    await page.locator('path').evaluate(el => el.setAttribute('d','M450 420L650 420 M640 415L650 420L640 425'));
    await page.evaluate(() => {window.visualPlayer.seek=t=>({timeMs:t,geometry:{arrow:{from:{x:450,y:420},to:{x:650,y:420}}}});});
    report=await run();assert(report.passed);assert(report.relationContacts.length===1);
    assert.deepEqual(report.overlapPairs,[['card','arrow']]);assert.deepEqual(report.overlapExclusions,[]);
    await page.locator('[data-object-id="card"]').evaluate(el => {
      el.innerHTML='<span style="position:absolute;left:40px;top:4px;font:24px Arial">READ ME</span>';
    });
    report=await run();assert(report.issues.some(i=>i.measured.reason==='stroke_crosses_text'));
    // Declaring another endpoint cannot excuse collision with this card.
    scene.nodes[1].to.objectId='somewhere-else';
    await page.locator('[data-object-id="card"]').evaluate(el=>{el.textContent='';});
    report=await run();assert(report.issues.some(i=>i.measured.reason==='stroke_crosses_object'));
    console.log('Vector DOM geometry: carrier ignored, actual crossing and safe-zone violations retained at 0.5x scale');
  } finally {
    await browser.close();
    fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error => { console.error(error); process.exitCode=1; });
