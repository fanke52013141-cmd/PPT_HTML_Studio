"use strict";
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const {chromium} = require('playwright');
const {compile} = require('../compiler.cjs');
const root = path.resolve(__dirname, '..');
const read = p => JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
async function main() {
  const scene = read('fixtures/presentation-details/source-scene.json');
  scene.version = '0.7.0';
  for (const n of scene.nodes.filter(n=>n.slot.startsWith('stat-')))
    n.presentation={variant:'text-card-stacked',height:136,typography:{text:{fontSizePx:20,lineHeight:1.3,align:'left'}}};
  const summary = scene.nodes.find(n=>n.type==='summary');
  summary.presentation={variant:'summary-arrow-overlay',height:210,offsetY:-100};
  compile(scene, read('generated/catalog.json'));
  const bad = structuredClone(scene);
  bad.nodes.find(n=>n.slot==='stat-1').runs=[{text:'没有分隔符',emphasis:false}];
  assert.throws(()=>compile(bad,read('generated/catalog.json')),/PRESENTATION_LABEL_REQUIRED/);
  const browser = await chromium.launch({headless:true,executablePath:require('../../tools/browser-runtime.cjs').resolveBrowser(chromium)});
  try {
    const page=await browser.newPage({viewport:{width:1648,height:1200}});
    await page.goto(pathToFileURL(path.join(root,'preview/index.html')).href);
    await page.waitForFunction(()=>window.visualPlayer?.ready);
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),scene),true,await page.locator('#status').innerText());
    await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);
    const facts=await page.evaluate(()=>{
      const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}};
      const node=document.querySelector('[data-object-id="stat-input"]');
      const flow=document.querySelector('.v-flow');
      return {label:box(node.querySelector('.v-stacked-label')),body:box(node.querySelector('.v-stacked-body')),
        text:node.querySelector('.v-panel-copy').textContent,term:box(flow.querySelector('.v-term')),
        arrow:box(flow.querySelector('svg')),paintedArrowWidth:flow.querySelector('svg path').getBBox().width,
        takeaway:box(document.querySelector('.v-takeaway')),flow:box(flow)};
    });
    assert(facts.body.y>=facts.label.bottom-1);
    assert.equal(facts.text,scene.nodes.find(n=>n.id==='stat-input').runs.map(r=>r.text).join(''));
    assert(facts.term.x<facts.arrow.right && facts.term.right>facts.arrow.x);
    assert(facts.term.y<facts.arrow.bottom && facts.term.bottom>facts.arrow.y);
    assert(facts.paintedArrowWidth>550,'painted arrow path must extend beyond the overlaid term, not just a wide SVG box');
    assert(facts.takeaway.y>=facts.flow.bottom);
    const shot=await page.locator('.visual-stage').screenshot();
    await page.evaluate(t=>window.visualPlayer.seek(t),500);
    await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);
    assert(shot.equals(await page.locator('.visual-stage').screenshot()),'new variants seek determinism');
    const tooShort=structuredClone(scene);
    tooShort.nodes.find(n=>n.type==='summary').presentation.height=100;
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),tooShort),false);
    assert.match(await page.locator('#status').innerText(),/CONTENT_CAPACITY_EXCEEDED/);
    const tooLong=structuredClone(scene);
    tooLong.nodes.find(n=>n.slot==='stat-1').runs=[{text:'标签：'+ '过长正文'.repeat(40),emphasis:false}];
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),tooLong),false);
    console.log('stacked/relation: 9 checks passed (characters, structure, overlay, painted arrow, below-flow, seek, delimiter, min-size, overflow)');
  } finally {await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
