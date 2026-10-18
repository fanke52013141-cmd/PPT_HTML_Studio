"use strict";
const assert=require("node:assert/strict"),fs=require("fs"),path=require("path");
const {pathToFileURL}=require("url");
const {chromium}=require("../html_engine/node_modules/playwright");
const {compile}=require("../html_engine/visual/compiler.cjs");
const root=path.resolve(__dirname,".."),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const catalog=read("html_engine/visual/generated/catalog.json");
const scene=read("html_engine/visual/scenes/condensation.json");
scene.version="0.7.0";scene.initialVisibleIds=[];
scene.motion.forEach((a,i)=>a.actionId=`action-${i}`);
const original=structuredClone(scene),node=id=>scene.nodes.find(n=>n.id===id);
node("figure").presentation={variant:"figure-frame-top"};
node("annotation").presentation={variant:"annotation-dashed"};
delete node("summary").heading;
node("summary").presentation={variant:"summary-strip-divided",height:110};
compile(scene,catalog);
for(const n of scene.nodes) {
  const before=original.nodes.find(v=>v.id===n.id);
  assert.deepEqual(Object.fromEntries(Object.entries(n).filter(([k])=>k!=="presentation"&&k!=="heading")),
    Object.fromEntries(Object.entries(before).filter(([k])=>k!=="presentation"&&k!=="heading")));
}
assert.deepEqual(scene.motion,original.motion);
for(const [key,value] of [["offsetX",1],["width",120],["typography",{}],["icon","check"]]) {
  const bad=structuredClone(scene);bad.nodes.find(n=>n.type==="annotation").presentation[key]=value;
  assert.throws(()=>compile(bad,catalog));
}
const bad=structuredClone(scene);bad.nodes.find(n=>n.type==="summary").heading={text:"Extra",icon:"check"};
assert.throws(()=>compile(bad,catalog),/PRESENTATION_HEADING_UNSUPPORTED/);
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:require("../html_engine/tools/browser-runtime.cjs").resolveBrowser(chromium)});
 try {
  const page=await browser.newPage({viewport:{width:1656,height:1200}}),errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(root,"html_engine/visual/preview/index.html")).href);
  await page.waitForFunction(()=>window.visualPlayer?.ready);
  assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),scene),true,await page.locator("#status").innerText());
  await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);
  const facts=await page.evaluate(()=>{
   const n=id=>document.querySelector(`[data-object-id="${id}"]`),a=n("annotation").querySelector("svg"),term=n("summary").querySelector(".v-term");
   return {frame:getComputedStyle(n("figure")).borderTopWidth,tag:n("figure").querySelector(".v-figure-tag").style.top,
     ring:a.children[0].getAttribute("stroke-dasharray"),leader:a.children[1].style.strokeDasharray,
     head:a.children[2].getAttribute("d"),left:getComputedStyle(term).borderLeftWidth,right:getComputedStyle(term).borderRightWidth,
     term:term.textContent,child:term.parentElement.dataset.objectId};
  });
  assert.equal(facts.frame,"1px");assert.equal(facts.tag,"18px");assert.equal(facts.ring,"6 5");assert.deepEqual(facts.leader.match(/\d+/g),["6","5"]);
  assert.match(facts.head,/L/);assert.equal(facts.left,"1px");assert.equal(facts.right,"1px");
  assert.equal(facts.term,node("summary").term);assert.equal(facts.child,"summary");
  const first=await page.locator(".visual-stage").screenshot();
  for(const t of [12400,300,12700,9000,scene.durationMs]) await page.evaluate(t=>window.visualPlayer.seek(t),t);
  assert(first.equals(await page.locator(".visual-stage").screenshot()));
  const small=structuredClone(scene);small.nodes.find(n=>n.type==="summary").presentation.height=89;
  assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),small),false);
  const overflow=structuredClone(scene);overflow.nodes.find(n=>n.type==="summary").takeaway="W".repeat(40);
  assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),overflow),false);
  assert.equal(await page.evaluate(s=>window.visualPlayer.apply(s),original),true);
  await page.evaluate(t=>window.visualPlayer.seek(t),scene.durationMs);
  assert.equal(await page.locator('[data-object-id="annotation"] circle').getAttribute("stroke-dasharray"),null);
  assert.deepEqual(errors,[]);
  const folder=process.env.HPS_TEST_OUTPUT_DIR||path.join(root,"outputs/framed-relations-2026-10-18");fs.mkdirSync(folder,{recursive:true});
  fs.writeFileSync(path.join(folder,"engineering.png"),first);
  fs.writeFileSync(path.join(folder,"engineering.json"),JSON.stringify({passed:true,facts,model:false,humanApproval:"pending"},null,2));
  console.log(JSON.stringify({passed:true,facts}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
