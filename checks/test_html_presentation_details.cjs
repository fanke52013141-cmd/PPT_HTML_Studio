"use strict";
const assert = require("node:assert/strict"), fs = require("fs"), path = require("path");
const { pathToFileURL } = require("url");
const {chromium} = require("../html_engine/node_modules/playwright");
const {compile} = require("../html_engine/visual/compiler.cjs");
const root = path.resolve(__dirname,".."), read = name => JSON.parse(fs.readFileSync(path.join(root,name),"utf8"));
const scene = read("html_engine/visual/fixtures/presentation-details/scene.json"), original = read("html_engine/visual/fixtures/presentation-details/source-scene.json"), catalog = read("html_engine/visual/generated/catalog.json");
(async()=>{
  compile(scene,catalog);
  assert.deepEqual(scene.motion,original.motion);
  for (const node of scene.nodes) assert.deepEqual(Object.fromEntries(Object.entries(node).filter(([key])=>key!=="presentation")),original.nodes.find(n=>n.id===node.id));
  const reject=(change,code)=>{const s=structuredClone(scene);change(s);assert.throws(()=>compile(s,catalog),new RegExp(code));};
  reject(s=>delete s.nodes.find(n=>n.id==="stat-input").presentation.icon,"PRESENTATION_ICON_REQUIRED");
  reject(s=>s.nodes.find(n=>n.id==="stat-input").runs=[{text:"Missing label separator",emphasis:false}],"PRESENTATION_LABEL_REQUIRED");
  reject(s=>delete s.nodes.find(n=>n.id==="billing-summary").heading,"PRESENTATION_HEADING_REQUIRED");
  reject(s=>s.nodes.find(n=>n.id==="billing-summary").presentation.icon="invented-icon","UNKNOWN_ICON");
  const browser=await chromium.launch({headless:true,executablePath:require("../html_engine/tools/browser-runtime.cjs").resolveBrowser(chromium)});
  try {
    const page=await browser.newPage({viewport:{width:1656,height:1200}}), errors=[];
    page.on("pageerror",e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root,"html_engine/visual/preview/index.html")).href);
    await page.waitForFunction(()=>window.visualPlayer?.ready);
    await page.addStyleTag({content:"main {max-width:1648px;}"});
    const apply=async s=>assert.equal(await page.evaluate(v=>window.visualPlayer.apply(v),s),true,await page.locator("#status").innerText());
    await apply(scene);await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);
    const parts=await page.evaluate(()=>{
      const node=id=>document.querySelector(`[data-object-id="${id}"]`), sum=node("billing-summary"), flow=sum.querySelector(".v-flow");
      return {cardText:node("stat-input").textContent,labelWeight:getComputedStyle(node("stat-input").querySelector('[data-text-role="label"]')).fontWeight,bodyWeight:getComputedStyle(node("stat-input").querySelector('[data-text-role="body"]')).fontWeight,circle:getComputedStyle(node("stat-input").querySelector("span")).borderRadius,circleBackground:getComputedStyle(node("stat-input").querySelector("span")).backgroundColor,summaryBackground:getComputedStyle(sum).backgroundColor,caption:getComputedStyle(node("billing-caption")).textAlign,divider:getComputedStyle(flow).borderRightWidth,connectorWidth:flow.querySelector('[data-connector="relationship"]').getBoundingClientRect().width,summaryText:sum.textContent,checkPaths:sum.querySelector(".v-summary-heading svg").querySelectorAll("path").length};
    });
    assert.equal(parts.cardText,scene.nodes.find(n=>n.id==="stat-input").runs.map(r=>r.text).join(""));
    assert.equal(parts.labelWeight,"700");assert.equal(parts.bodyWeight,"400");assert.equal(parts.circle,"50%");assert.equal(parts.circleBackground,"rgb(238, 238, 238)");assert.equal(parts.summaryBackground,"rgb(244, 244, 244)");assert.equal(parts.caption,"left");assert.equal(parts.divider,"1px");assert(parts.connectorWidth>96);assert(!parts.summaryText.includes("这个过程叫"));assert.equal(parts.checkPaths,1);
    const first=await page.locator(".visual-stage").screenshot();await page.evaluate(()=>window.visualPlayer.seek(1000));await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);assert(first.equals(await page.locator(".visual-stage").screenshot()));
    const out=path.join(root,"outputs/presentation-details-2026-10-14");fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,"final.png"),first);
    const small=structuredClone(scene);small.nodes.find(n=>n.id==="stat-input").presentation.height=100;
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),small),false);assert.match(await page.locator("#status").innerText(),/CONTENT_CAPACITY_EXCEEDED/);
    const overflow=structuredClone(scene);overflow.nodes.find(n=>n.id==="billing-summary").takeaway="W".repeat(40);
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),overflow),false);assert.match(await page.locator("#status").innerText(),/CONTENT_CAPACITY_EXCEEDED/);
    assert.equal(await page.evaluate(()=>window.visualPlayer.scene.id),scene.id);
    // Old variants are still rendered without the new section treatment.
    const old=structuredClone(scene);old.nodes.find(n=>n.id==="billing-summary").presentation={variant:"summary-panel"};
    for(const n of old.nodes.filter(n=>n.type==="text")) if(n.presentation?.variant)n.presentation.variant="text-card-outline";
    await apply(old);assert.equal(await page.locator('[data-connector="relationship"]').count(),0);
    const compact=structuredClone(scene), compactSummary=compact.nodes.find(n=>n.id==="billing-summary");
    compactSummary.presentation={variant:"summary-relationship-compact",icon:"check-plain",height:91};
    compile(compact,catalog);
    await apply(compact);await page.evaluate(t=>window.visualPlayer.seek(t),compact.durationMs);
    assert.equal(await page.locator('[data-connector="relationship"]').count(),1);
    const compactTooShort=structuredClone(compact);
    compactTooShort.nodes.find(n=>n.id==="billing-summary").presentation.height=90;
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),compactTooShort),false);
    assert.match(await page.locator("#status").innerText(),/CONTENT_CAPACITY_EXCEEDED/);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,"engineering-evidence.json"),JSON.stringify({status:"passed",parts,checks:["source/motion preserved","registered minimums and icons","literal label/body weights","subregion overflow rejected","old variants preserved","random seek identical","compact relationship at 91px","compact minimum rejects 90px"],model:false,humanApproval:"pending"},null,2));
    console.log(JSON.stringify({passed:true,checks:8,model:false}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
