"use strict";
// Verify the actual delivered page and its audio, not a test double.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),{pathToFileURL}=require("node:url");
const {chromium}=require("playwright");
async function main(){
  const directory=path.resolve(process.argv[2]),scene=JSON.parse(fs.readFileSync(path.join(directory,"bound-scene.json"),"utf8"));
  const browser=await chromium.launch(require("./browser-runtime.cjs").captureLaunchOptions(chromium));
  const evidence={status:"passed",checks:[],frames:[],errors:[]};
  try{
    const page=await browser.newPage({viewport:{width:1680,height:1100}});
    page.on("pageerror",e=>evidence.errors.push(e.message));
    await page.goto(pathToFileURL(path.join(directory,"preview/index.html")).href);
    await page.waitForFunction(()=>window.audioReview?.ready && document.getElementById("audio").readyState>=2);
    assert.equal(await page.locator("#beats button").count(),4);
    evidence.checks.push("audio decoded and beat navigation loaded");
    for(const ms of [0,...new Set(scene.motion.map(a=>a.startMs+500)),scene.durationMs]){
      await page.evaluate(ms=>window.audioReview.seek(ms),ms);
      await page.waitForFunction(ms=>Math.abs(window.visualPlayer.timeMs-ms)<1,ms);
      const state=await page.evaluate(()=>Object.fromEntries([...document.querySelectorAll("[data-object-id]")].map(e=>[e.dataset.objectId,Number(e.style.opacity)])));
      for(const node of scene.nodes){
        const enter=scene.motion.find(a=>a.targetId===node.id && a.type==="enter");
        const expected=scene.initialVisibleIds.includes(node.id) || (enter && ms>=enter.startMs+enter.durationMs);
        if(expected) assert.equal(state[node.id],1);
        else if(!enter || ms<=enter.startMs) assert.equal(state[node.id],0);
      }
      const name=`frame-${ms}.png`;await page.locator(".visual-stage").screenshot({path:path.join(directory,name)});
      evidence.frames.push({timeMs:ms,file:name,visible:state});
    }
    evidence.checks.push("actual initial, beat, parallel actions and final visibility");
    await page.locator("#beats button").nth(1).click();
    await page.waitForFunction(()=>!document.getElementById("audio").paused && window.visualPlayer.timeMs>4000);
    const state=await page.evaluate(()=>({audioMs:window.audioReview.audio.currentTime*1000,frameMs:window.visualPlayer.timeMs,playing:window.visualPlayer.playing}));
    assert.ok(Math.abs(state.audioMs-state.frameMs)<120);assert.equal(state.playing,false);
    await page.evaluate(()=>window.audioReview.audio.pause());
    evidence.checks.push("real audio playback drives shared frame clock");evidence.clock=state;
    assert.deepEqual(evidence.errors,[]);
  }finally{await browser.close();}
  fs.writeFileSync(path.join(directory,"browser-review.json"),JSON.stringify(evidence,null,2));console.log(JSON.stringify({status:evidence.status,checks:evidence.checks.length,frames:evidence.frames.length}));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
