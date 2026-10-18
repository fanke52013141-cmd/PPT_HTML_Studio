"use strict";
// A04 samples the same production player; no alternate scene composition.
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),{pathToFileURL}=require("node:url");
const {chromium}=require("playwright");
const [input,output]=process.argv.slice(2);
(async()=>{
 const spec=JSON.parse(fs.readFileSync(input,"utf8"));
 if(!spec.beats.length || spec.beats.length>40)throw Error("SEMANTIC_FRAME_BUDGET");
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch(require("./browser-runtime.cjs").captureLaunchOptions(chromium));
 try {
  const page=await browser.newPage({viewport:{width:1656,height:1200}}),errors=[];
  page.on("pageerror",e=>errors.push(e.name));
  await page.goto(pathToFileURL(path.resolve(__dirname,"../visual/preview/index.html")).href);
  await page.waitForFunction(()=>window.visualPlayer?.ready);
  await page.addStyleTag({content:"main{max-width:1648px}"});
  const assets=require("./project-resources.cjs").loadProjectResources();
  if(!await page.evaluate(async v=>window.visualPlayer.apply(v.scene,v.assets),{scene:spec.bound_scene,assets}))throw Error(await page.locator("#status").innerText());
  const frames=[],issues=[];
  for(const [index,beat] of spec.beats.entries())for(const [frameIndex,timeMs] of beat.times.entries()){
   if(!Number.isFinite(timeMs)||timeMs<0||timeMs>=spec.bound_scene.durationMs)throw Error("SEMANTIC_FRAME_TIME");
   const data=await page.evaluate(t=>{
    const result=window.visualPlayer.seek(t),stage=document.querySelector(".visual-stage").getBoundingClientRect(),scale=stage.width/1600,visible={},boxes={};
    for(const el of document.querySelectorAll("[data-object-id]")){
     const style=getComputedStyle(el),r=el.getBoundingClientRect();
     visible[el.dataset.objectId]=style.display==="none"||style.visibility==="hidden"?0:Number(style.opacity);
     boxes[el.dataset.objectId]={x:(r.x-stage.x)/scale,y:(r.y-stage.y)/scale,width:r.width/scale,height:r.height/scale};
    }
    return {timeMs:result.timeMs,visible,boxes};
   },timeMs);
   for(const [id,b]of Object.entries(data.boxes))if(data.visible[id]>0.01&&(b.x < -1||b.y < -1||b.x+b.width>1601||b.y+b.height>801))issues.push({code:"SEMANTIC_SAFE_ZONE",targetId:id,timeMs});
   const file=`beat-${index}-${frameIndex}.png`;await page.locator(".visual-stage").screenshot({path:path.join(output,file)});
   frames.push({...data,beatId:beat.id,frameIndex,file,sha256:crypto.createHash("sha256").update(fs.readFileSync(path.join(output,file))).digest("hex")});
  }
  fs.writeFileSync(path.join(output,"frames.json"),JSON.stringify({frames,issues,pageErrors:errors,passed:!issues.length&&!errors.length,browserVersion:browser.version()},null,2));
 }finally{await browser.close();}
})().catch(e=>{fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,"error.json"),JSON.stringify({code:"SEMANTIC_RENDER_FAILED",message:e.message}));process.exitCode=1;});
