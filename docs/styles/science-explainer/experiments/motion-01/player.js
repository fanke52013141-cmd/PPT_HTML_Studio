"use strict";
(() => {
 const stage=document.querySelector(".stage"),world=document.querySelector(".scene-world"),playButton=document.querySelector("#play"),scrub=document.querySelector("#scrub"),status=document.querySelector("#status");
 const {durationMs,evaluate}=window.objectMotion;
 let currentMs=0,playing=false,ready=false,lastClock=0,frameRequest=0;
 const sourceImage=new Image();sourceImage.src="../hybrid-01/condensation-alpha.png";
 const raster=document.querySelector(".raster").getContext("2d",{willReadFrequently:true});
 function renderAt(tMs){
  const state=evaluate(tMs);currentMs=tMs;
  const c=state.camera;
  raster.setTransform(1,0,0,1,0,0);raster.clearRect(0,0,1920,1080);raster.imageSmoothingEnabled=true;raster.imageSmoothingQuality="high";raster.setTransform(c.z,0,0,c.z,960-c.x*c.z,540-c.y*c.z);
  if(sourceImage.complete&&sourceImage.naturalWidth)raster.drawImage(sourceImage,180,275,550,550);
  world.setAttribute("transform",`matrix(${c.z} 0 0 ${c.z} ${960-c.x*c.z} ${540-c.y*c.z})`);
  for(const drop of [...state.drops,{id:"merged-drop",...state.merged}]){
   const node=stage.querySelector(`[data-target="${drop.id}"]`);node.setAttribute("transform",`translate(${drop.x} ${drop.y}) scale(${drop.scale})`);node.setAttribute("opacity",drop.opacity);
  }
  stage.querySelector('[data-target="page.caption"]').textContent=state.caption;
  scrub.value=String(tMs);document.querySelector("#time").textContent=`${(tMs/1000).toFixed(2)} / 12.00 秒`;
  for(const button of document.querySelectorAll("[data-time]"))button.setAttribute("aria-current",String([0,3000,6100,10000][state.phase]===Number(button.dataset.time)));
  return state;
 }
 function pause(){playing=false;cancelAnimationFrame(frameRequest);playButton.textContent="播放";}
 function seek(tMs){pause();return renderAt(tMs);}
 function tick(clock){
  if(!playing)return;
  const direction=Number(document.querySelector("#direction").value),speed=Number(document.querySelector("#speed").value);
  const next=Math.max(0,Math.min(durationMs,currentMs+(clock-lastClock)*speed*direction));lastClock=clock;renderAt(next);
  if((direction>0&&next===durationMs)||(direction<0&&next===0)){pause();return;}frameRequest=requestAnimationFrame(tick);
 }
 function play(){
  if(!ready||playing)return;
  const direction=Number(document.querySelector("#direction").value);
  if(direction>0&&currentMs===durationMs)renderAt(0);if(direction<0&&currentMs===0)renderAt(durationMs);
  playing=true;lastClock=performance.now();playButton.textContent="暂停";frameRequest=requestAnimationFrame(tick);
 }
 playButton.addEventListener("click",()=>playing?pause():play());
 document.querySelector("#restart").addEventListener("click",()=>{seek(0);document.querySelector("#direction").value="1";play();});
 scrub.addEventListener("input",()=>seek(Number(scrub.value)));
 for(const button of document.querySelectorAll("[data-time]"))button.addEventListener("click",()=>seek(Number(button.dataset.time)));
 document.addEventListener("visibilitychange",()=>{if(document.hidden)pause();});
 function resize(){stage.style.transform=`scale(${document.querySelector(".viewport").clientWidth/1920})`;}
 new ResizeObserver(resize).observe(document.querySelector(".viewport"));resize();renderAt(0);
 window.motionTrial={durationMs,renderAt,seek,play,pause,get timeMs(){return currentMs;},get playing(){return playing;}};
 window.motionReady=Promise.all([document.fonts.ready,sourceImage.decode()]).then(()=>{
  ready=true;renderAt(currentMs);for(const element of document.querySelectorAll("button,input"))element.disabled=false;
  status.textContent="素材已就绪。可播放、拖动或倒放；本次为人工测试时间，尚未绑定讲稿音频。";
 }).catch(error=>{status.textContent="素材加载失败，播放与导出已阻断。";status.dataset.error="true";throw error;});
})();
