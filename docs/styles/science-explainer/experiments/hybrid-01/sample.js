"use strict";
const slide=document.querySelector(".slide");
const original=window.trialContent;
const diagnostic=document.querySelector("#diagnostic");
function fillContent(replacement=false){
  const title=slide.querySelector("h1");
  title.replaceChildren();
  if(replacement){title.textContent="水的两种变化";}else{
    for(const [text,cls] of [["蒸发","pink"],["与",""],["凝结","blue"]]){const span=document.createElement("span");span.textContent=text;span.className=cls;title.append(span);}
  }
  document.querySelector("#subtitle").textContent=original.subtitle.screen;
  for(const item of original.objects){
    const node=slide.querySelector(`[data-object="${item.id}"]`);
    node.querySelector(".figure").src=item.figure;
    node.querySelector("h2").textContent=item.name;
    node.querySelector(".from").textContent=item.from;
    node.querySelector(".to").textContent=item.to;
    node.querySelector(".body").textContent=replacement?(item.id==="left"?"水面上的水，逐渐成为水蒸气。":"空气中的水蒸气，遇冷凝结成水滴。"):item.body;
  }
  slide.querySelector("footer").textContent=original.source.screen;
  requestAnimationFrame(checkCapacity);
}
function checkCapacity(){
  if(document.querySelector(".viewport").clientWidth===0)return [];
  const problems=[];
  for(const [selector,maxLines] of [["h1",1],["#subtitle",1],["h2",1],[".body",2],["footer",1]]){
    for(const el of slide.querySelectorAll(selector)){
      const style=getComputedStyle(el),lineHeight=parseFloat(style.lineHeight);
      if(el.getBoundingClientRect().height/slideScale()>lineHeight*maxLines+1||el.scrollWidth>el.clientWidth+1)problems.push(selector);
    }
  }
  diagnostic.dataset.error=String(problems.length>0);
  diagnostic.textContent=problems.length?`容量超限：${[...new Set(problems)].join("、")}。需调整内容、换模板或分页。`:"独立 PNG 插画 + HTML 文字与 SVG 箭头；工程容量通过，视觉审阅待确认。";
  return problems;
}
function slideScale(){return document.querySelector(".viewport").clientWidth/1920;}
function resize(){const width=document.querySelector(".viewport").clientWidth;if(width>0)slide.style.transform=`scale(${width/1920})`;}
window.setTrialStage=function(stage){if(!["overview","left","both"].includes(stage))throw new Error("Unknown stage");slide.dataset.stage=stage;for(const button of document.querySelectorAll("[data-stage]"))button.setAttribute("aria-pressed",String(button.dataset.stage===stage));};
window.setTrialView=function(view){if(!["html","design","compare"].includes(view))throw new Error("Unknown view");document.querySelector(".panels").dataset.view=view;for(const button of document.querySelectorAll("button[data-view]"))button.setAttribute("aria-pressed",String(button.dataset.view===view));resize();checkCapacity();};
for(const button of document.querySelectorAll("button[data-stage]"))button.addEventListener("click",()=>window.setTrialStage(button.dataset.stage));
for(const button of document.querySelectorAll("button[data-view]"))button.addEventListener("click",()=>window.setTrialView(button.dataset.view));
document.querySelector("#replacement").addEventListener("change",event=>fillContent(event.target.checked));
new ResizeObserver(resize).observe(document.querySelector(".viewport"));
fillContent();window.setTrialStage("both");resize();document.fonts.ready.then(checkCapacity);
