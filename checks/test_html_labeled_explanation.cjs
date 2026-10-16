"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require("../html_engine/node_modules/playwright");
const {compile} = require("../html_engine/visual/compiler.cjs");
const root = path.resolve(__dirname,".."), read = p => JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const scene = read("html_engine/visual/fixtures/labeled-explanation/scene.json"), catalog = read("html_engine/visual/generated/catalog.json");
(async()=>{
  const registry=read("html_engine/visual/catalog/catalog.json").productionCapabilities;
  assert.equal(registry.find(v=>v.id==="runtime-layout:science-explanation-v1").version,"0.2.0");
  assert.equal(registry.find(v=>v.id==="runtime-layout:science-explanation-v1@0.3.0").version,"0.3.0");
  compile(scene,catalog);
  const legacy=read("html_engine/visual/scenes/condensation.json");
  assert.equal(compile(legacy,catalog).layout.version,"0.2.0");
  assert.equal(compile(scene,catalog).layout.version,"0.3.0");
  const wrong=structuredClone(scene);wrong.templateRef=legacy.templateRef;
  assert.throws(()=>compile(wrong,catalog),/TEMPLATE_LAYOUT_MISMATCH/);
  const invented=structuredClone(scene);invented.nodes[0].presentation={variant:"figure-caption-top"};
  assert.throws(()=>compile(invented,catalog),/UNSUPPORTED_PRESENTATION_VARIANT/);
  const browser=await chromium.launch({headless:true,executablePath:require("../html_engine/tools/browser-runtime.cjs").resolveBrowser(chromium)});
  try {
    const page=await browser.newPage({viewport:{width:1656,height:1200}}),errors=[];
    page.on("pageerror",e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root,"html_engine/visual/preview/index.html")).href);
    await page.waitForFunction(()=>window.visualPlayer?.ready);
    const current=structuredClone(scene);
    current.nodes.find(n=>n.id==="headline").runs=[{text:"普通文字 ",emphasis:false},{text:"重点文字",emphasis:true}];
    const apply=async s=>assert.equal(await page.evaluate(v=>window.visualPlayer.apply(v),s),true,await page.locator("#status").innerText());
    await apply(current);await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);
    const evidence=await page.evaluate(()=>{
      const node=id=>document.querySelector(`[data-object-id="${id}"]`),rect=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
      const head=node("headline"),fig=node("figure"),sum=node("summary"),note=fig.querySelector(".v-figure-note"),term=sum.querySelector(".v-term"),takeaway=sum.querySelector(".v-takeaway");
      return {weights:[...head.querySelectorAll("span")].map(el=>getComputedStyle(el).fontWeight),headline:head.textContent,
        labels:Array.from({length:6},(_,i)=>({backend:node(`marker-${i+1}`).dataset.backend,text:node(`marker-${i+1}`).textContent,z:getComputedStyle(node(`marker-${i+1}`)).zIndex})),
        note:rect(note),subject:rect(node("subject")),tagRadius:getComputedStyle(fig.querySelector(".v-figure-tag")).borderRadius,
        resultColumn:!!term.parentElement.classList.contains("v-result-column"),term:rect(term),takeaway:rect(takeaway),chip:getComputedStyle(takeaway).borderRadius,
        arrow:node("relation-1").querySelector("path").getAttribute("d")};
    });
    assert.deepEqual(evidence.weights,["400","700"]);assert.equal(evidence.headline,"普通文字 重点文字");
    assert(evidence.labels.every(l=>l.backend!=="image" && l.text && +l.z>2));
    assert(evidence.note.y+evidence.note.h<evidence.subject.y);assert.equal(evidence.tagRadius,"999px");
    assert(evidence.resultColumn);assert(evidence.term.y<evidence.takeaway.y);assert.equal(evidence.chip,"999px");assert(evidence.arrow.includes(" V 6"));
    const image=await page.locator(".visual-stage").screenshot();
    await page.evaluate(()=>window.visualPlayer.seek(500));await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);
    assert(image.equals(await page.locator(".visual-stage").screenshot()));
    const tooLong=structuredClone(current);tooLong.nodes.find(n=>n.id==="marker-1").runs=[{text:"W".repeat(120),emphasis:false}];
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),tooLong),false);assert.match(await page.locator("#status").innerText(),/CONTENT_CAPACITY_EXCEEDED/);
    const tooShort=structuredClone(current);tooShort.nodes.find(n=>n.id==="summary").presentation.height=109;
    assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),tooShort),false);
    assert.match(await page.locator("#status").innerText(),/CONTENT_CAPACITY_EXCEEDED/);
    await apply(legacy);await page.evaluate(t=>window.visualPlayer.seek(t),legacy.durationMs);
    assert.equal(await page.locator(".v-result-column").count(),0);assert.deepEqual(errors,[]);
    const out=path.join(root,"outputs/labeled-explanation-20261015");fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,"capabilities.png"),image);
    fs.writeFileSync(path.join(out,"engineering.json"),JSON.stringify({status:"passed",evidence,visualApproval:"pending",model:false},null,2));
    console.log(JSON.stringify({passed:true,labels:6,relations:3,oldLayoutPreserved:true,model:false}));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
