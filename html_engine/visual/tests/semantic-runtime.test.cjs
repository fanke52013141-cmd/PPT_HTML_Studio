"use strict";
const assert = require("node:assert/strict"),fs = require("node:fs"),path = require("node:path");
const {pathToFileURL} = require("node:url"),{chromium} = require("playwright");
const {compile} = require("../compiler.cjs");
const visual = path.resolve(__dirname,".."),catalog = require("../generated/catalog.json");
async function main() {
  const sample = JSON.parse(fs.readFileSync(path.join(visual,"scenes/condensation.json"),"utf8"));
  const target = sample.nodes.find(n => n.type === "image").id;
  sample.version = "0.6.0";sample.initialVisibleIds=sample.nodes.filter(n=>n.id!==target).map(n=>n.id);
  sample.motion = [{actionId:"subject-enter",targetId:target,type:"enter",startMs:1000,durationMs:400,offsetX:0,offsetY:12},
                   {actionId:"subject-emphasis-1",targetId:target,type:"emphasize",startMs:3000,durationMs:400},
                   {actionId:"subject-emphasis-2",targetId:target,type:"emphasize",startMs:5000,durationMs:400}];
  compile(sample,catalog);
  const duplicate=structuredClone(sample);duplicate.motion[2].actionId=duplicate.motion[1].actionId;
  assert.throws(()=>compile(duplicate,catalog),/DUPLICATE_ACTION_ID/);
  const overlap=structuredClone(sample);overlap.motion[2].startMs=3100;
  assert.throws(()=>compile(overlap,catalog),/ACTION_WINDOW_OVERLAP/);
  const legacy=structuredClone(sample);legacy.version="0.5.0";
  assert.throws(()=>compile(legacy,catalog),/INVALID_VISUAL_DEFINITION/);
  const browser=await chromium.launch({headless:true,executablePath:require("../../tools/browser-runtime.cjs").resolveBrowser(chromium)});
  try {
    const page=await browser.newPage({viewport:{width:1648,height:1200}});
    await page.goto(pathToFileURL(path.join(visual,"preview/index.html")).href);
    await page.waitForFunction(()=>window.visualPlayer?.ready);
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),sample),true);
    const state=async ms=>page.evaluate(({ms,id})=>{window.visualPlayer.seek(ms);const e=document.querySelector(`[data-object-id="${id}"]`);return {opacity:Number(e.style.opacity),transform:e.style.transform};},{ms,id:target});
    assert.equal((await state(0)).opacity,0);assert.equal((await state(1200)).opacity,0.5);assert.equal((await state(1400)).opacity,1);
    for(const ms of [3200,5200]) assert.ok((await state(ms)).transform.includes("-8"));
    assert.ok(!(await state(4800)).transform.includes("-8"));
    const initial=await page.evaluate(ids=>ids.map(id=>Number(document.querySelector(`[data-object-id="${id}"]`).style.opacity)),sample.initialVisibleIds.filter(id=>sample.nodes.find(n=>n.id===id).type!=="annotation"));
    assert.ok(initial.every(value=>value===1));
    await state(5200);const pixels=await page.locator(".visual-stage").screenshot();
    for(const ms of [0,3200,100,4800,1400]) await state(ms);
    await state(5200);assert.deepEqual(await page.locator(".visual-stage").screenshot(),pixels);
    console.log(JSON.stringify({checks:8,status:"passed",scope:"initial visibility, repeated emphasis, identity, version, overlap and seek determinism"}));
  }finally{await browser.close();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
