/* Offline human input only. No model predictions, network or implicit labels. */
'use strict';
let current=0, runningSince=null, activeMs=0;
const answers=new Map(), el=id=>document.getElementById(id);
const cards=Array.from(document.querySelectorAll('article'));
const clock=()=>performance.now();
function pause(){
  if(runningSince!==null){activeMs+=Math.max(0,clock()-runningSince);runningSince=null;}
  el('timer').textContent=`已暂停，累计 ${(activeMs/1000).toFixed(1)} 秒`;
}
function show(index){
  pause();current=index;
  cards.forEach((card,i)=>{card.hidden=i!==index;});
  document.querySelectorAll('.truth-mark').forEach(mark=>mark.remove());
  const row=answers.get(REVIEW_DATA.samples[index]?.sample_id);
  activeMs=row?.active_review_ms||0;
  el('label').value=row?.label||'';el('notes').value=row?.notes||'';
  ['left','top','right','bottom'].forEach((id,i)=>{el(id).value=row?.truth_bounds?.[i]??'';});
  el('previous').disabled=index===0;el('next').disabled=index>=cards.length-1;
  el('editor').hidden=cards.length===0;
  el('progress').textContent=`已保存 ${answers.size} / ${cards.length} 行；当前 ${cards.length?index+1:0}`;
  el('timer').textContent=activeMs?`已暂停，累计 ${(activeMs/1000).toFixed(1)} 秒`:'尚未开始';
}
el('start').addEventListener('click',()=>{
  if(!document.hidden && document.hasFocus() && runningSince===null){runningSince=clock();el('timer').textContent='正在计时';}
});
el('pause').addEventListener('click',pause);
document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
window.addEventListener('blur',pause);
el('save').addEventListener('click',()=>{
  pause();
  const sample=REVIEW_DATA.samples[current],label=el('label').value;
  if(!sample||!label||activeMs<=0){el('message').textContent='请点击开始，独立核对后选择判断。';return;}
  let bounds=null;
  const raw=['left','top','right','bottom'].map(id=>el(id).value);
  if(label==='clipped'||label==='complete'){
    bounds=raw.map(Number);
    if(raw.some(v=>v.trim()==='')||bounds.some(v=>!Number.isInteger(v))||
       !(0<=bounds[0]&&bounds[0]<bounds[2]&&bounds[2]<=sample.image_size[0]&&
         0<=bounds[1]&&bounds[1]<bounds[3]&&bounds[3]<=sample.image_size[1])){
      el('message').textContent='请填写原图内合法的完整文字墨迹边界。';return;
    }
    const b=sample.proposed_bounds;
    const clipped=!(b[0]<=bounds[0]&&b[1]<=bounds[1]&&bounds[2]<=b[2]&&bounds[3]<=b[3]);
    if(clipped!==(label==='clipped')){el('message').textContent='判断与真值框矛盾，请核对。';return;}
  }else if(raw.some(v=>v.trim()!=='')){
    el('message').textContent='无法判断或身份有误时请清空真值框。';return;
  }
  answers.set(sample.sample_id,{sample_id:sample.sample_id,label,truth_bounds:bounds,
    active_review_ms:Math.round(activeMs),notes:el('notes').value});
  el('message').textContent='已保存到本页内存，请导出后再关闭。';
  show(Math.min(current+1,cards.length-1));
});
el('previous').addEventListener('click',()=>show(Math.max(0,current-1)));
el('next').addEventListener('click',()=>show(Math.min(cards.length-1,current+1)));
el('zoom').addEventListener('change',event=>{
  document.querySelectorAll('svg').forEach(svg=>{
    if(!svg.dataset.width)return;
    svg.setAttribute('width',Number(svg.dataset.width)*Number(event.target.value));
    svg.setAttribute('height',Number(svg.dataset.height)*Number(event.target.value));
  });
});
let downloadUrl=null;
function originalPoint(svg,event){
  const box=svg.getBoundingClientRect();
  return [Number(svg.dataset.originX)+Math.max(0,Math.min(Number(svg.dataset.width),
    (event.clientX-box.left)*Number(svg.dataset.width)/box.width)),
    Number(svg.dataset.originY)+Math.max(0,Math.min(Number(svg.dataset.height),
    (event.clientY-box.top)*Number(svg.dataset.height)/box.height))];
}
document.querySelectorAll('svg[data-origin-x]').forEach(svg=>{
  let origin=null,mark=null;
  const draw=(end)=>{
    const bounds=[Math.floor(Math.min(origin[0],end[0])),Math.floor(Math.min(origin[1],end[1])),
      Math.ceil(Math.max(origin[0],end[0])),Math.ceil(Math.max(origin[1],end[1]))];
    if(!mark||!mark.isConnected){mark=document.createElementNS('http://www.w3.org/2000/svg','rect');
      mark.setAttribute('class','truth-mark');mark.setAttribute('fill','none');mark.setAttribute('stroke','#15803d');
      mark.setAttribute('vector-effect','non-scaling-stroke');mark.setAttribute('pointer-events','none');svg.appendChild(mark);}
    mark.setAttribute('x',bounds[0]-Number(svg.dataset.originX));mark.setAttribute('y',bounds[1]-Number(svg.dataset.originY));
    mark.setAttribute('width',bounds[2]-bounds[0]);mark.setAttribute('height',bounds[3]-bounds[1]);return bounds;
  };
  svg.addEventListener('pointerdown',event=>{
    if(event.button!==0)return;
    if(runningSince===null){el('message').textContent='请先开始计时，再独立拖出文字墨迹边界。';return;}
    origin=originalPoint(svg,event);svg.setPointerCapture(event.pointerId);draw(origin);
  });
  svg.addEventListener('pointermove',event=>{if(origin)draw(originalPoint(svg,event));});
  svg.addEventListener('pointerup',event=>{
    if(!origin)return;
    const bounds=draw(originalPoint(svg,event));origin=null;
    if(bounds[0]<bounds[2]&&bounds[1]<bounds[3]){
      ['left','top','right','bottom'].forEach((id,i)=>{el(id).value=String(bounds[i]);});
      el('message').textContent='已填写人工边界（绿框），请选择判断后保存。';
    }
  });
  svg.addEventListener('pointercancel',()=>{origin=null;});
});
el('export').addEventListener('click',()=>{
  pause();
  if(!el('human').checked||!el('reviewer').value.trim()||!answers.size){
    el('message').textContent='请填写复核者代号、确认本人盲审，并至少保存一行。';return;
  }
  const documentToSave={policy:'text-edge-human-benchmark/0.1.0',
    package_sha256:REVIEW_DATA.package_sha256,reviewer_id:el('reviewer').value.trim(),
    declared_human_blind_review:true,timing_protocol:'foreground_explicit_start/0.1.0',rows:Array.from(answers.values())};
  if(downloadUrl)URL.revokeObjectURL(downloadUrl);
  downloadUrl=URL.createObjectURL(new Blob([JSON.stringify(documentToSave,null,2)+'\n'],{type:'application/json'}));
  const link=el('download');link.href=downloadUrl;link.download='text-edge-human-annotations.json';link.hidden=false;link.click();
  el('message').textContent=`已导出 ${answers.size} / ${cards.length} 行，未保存的当前填写不会进入文件。`;
});
show(0);
