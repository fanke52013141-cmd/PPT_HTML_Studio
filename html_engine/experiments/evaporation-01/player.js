(() => {
  'use strict';
  const stage=document.querySelector('#stage'),frame=document.querySelector('#frame'),definition=window.EvapDefinition;
  const zone=definition.subtitleZone;
  const content=document.createElement('div');content.id='content-layer';
  Object.assign(content.style,{position:'absolute',left:'0',top:'0',width:'1600px',height:zone.top+'px',overflow:'hidden'});stage.append(content);
  const effects=new Map();
  function put(id,type,x,y,params){const host=document.createElement('div');host.className='object';host.style.left=x+'px';host.style.top=y+'px';content.append(host);const fx=FlatEffects.mount(host,type,{...params,id});effects.set(id,fx);return fx;}
  put('title','text',100,60,{text:definition.title,width:1380,height:100,fontSize:62,bold:true,accent:'蒸发'});
  put('subtitle','text',104,165,{text:'不需要沸腾，也可以蒸发',width:1100,height:70,fontSize:28});
  put('sun','sun',135,265,{width:235,height:225});
  put('particles','flow',585,265,{width:360,height:285,count:6,seed:17});
  put('direction','arrow',1020,360,{width:180,height:160});
  put('term','paper',1200,392,{text:'蒸发',width:230,height:95,fontSize:44});
  put('state','mark',515,635,{text:'液态 → 气态',width:540,height:126,fontSize:43});
  put('explanation','text',1070,555,{text:'水变成水蒸气，进入空气。',accent:'水蒸气',width:400,height:110,fontSize:28});
  const asset=document.createElement('img');asset.className='beaker';asset.src='assets/beaker.png';asset.alt='独立手绘烧杯插画，半杯蓝色水';content.insertBefore(asset,content.children[3]);
  const hint=document.createElement('div');hint.className='hint';hint.textContent='蓝点表示过程方向\n数量不是实测';hint.style.whiteSpace='pre-line';content.append(hint);
  const captionRegion=document.createElement('div');captionRegion.id='subtitle-layer';
  Object.assign(captionRegion.style,{position:'absolute',left:'0',top:zone.top+'px',width:'1600px',height:zone.height+'px',padding:`${zone.paddingY}px ${zone.paddingX}px`,display:'flex',alignItems:'center',justifyContent:'center',background:FlatEffects.palette.paper});stage.append(captionRegion);
  const caption=document.createElement('div');caption.className='caption';captionRegion.append(caption);
  const fontControl=document.querySelector('#subtitle-size'),fontValue=document.querySelector('#subtitle-size-value');
  fontControl.min=zone.fontMin;fontControl.max=zone.fontMax;
  function setSubtitleFont(size){
    if(!Number.isInteger(size)||size<zone.fontMin||size>zone.fontMax)throw new RangeError('Subtitle font outside supported range');
    const probe=document.createElement('canvas').getContext('2d');probe.font=`${size}px "Microsoft YaHei"`;
    const availableWidth=1600-2*zone.paddingX,availableHeight=zone.height-2*zone.paddingY;
    for(const beat of definition.beats){let lines=1,width=0;for(const ch of beat.caption){const cw=probe.measureText(ch).width;if(width+cw>availableWidth){lines++;width=0;}width+=cw;}if(lines>zone.maxLines||lines*size*1.25>availableHeight)throw new Error('字幕过长，请缩小字号或拆分字幕。');}
    caption.style.fontSize=size+'px';fontControl.value=size;fontValue.textContent=size+' px';
  }
  const seek=document.querySelector('#seek'),clock=document.querySelector('#clock'),status=document.querySelector('#status');
  let time=0,playing=false,ready=false,raf=0,last=0;
  const progress=(t,s,d)=>Math.max(0,Math.min(1,(t-s)/d));
  function renderAt(t){if(!ready)throw new Error('Resources not ready');if(!Number.isFinite(t)||t<0||t>definition.durationMs)throw new RangeError('Time outside scene');time=t;
    const reduced=document.querySelector('#reduce').checked;
    effects.get('title').at(progress(t,0,800));effects.get('subtitle').at(progress(t,500,800));
    effects.get('sun').at(reduced?(t>=1500?1:0):progress(t,1500,1700));
    const entry=progress(t,600,1200);asset.style.opacity=entry;asset.style.transform=`translateY(${reduced?0:(1-entry)*35}px) rotate(${reduced?0:(1-entry)*-3}deg)`;
    effects.get('particles').at(progress(t,4000,6000));hint.style.opacity=progress(t,5500,900);
    effects.get('direction').at(progress(t,10000,1600));effects.get('term').at(reduced?(t>=11500?1:0):progress(t,11500,1500));
    effects.get('state').at(progress(t,14500,1800));effects.get('explanation').at(progress(t,16500,1000));
    caption.textContent=definition.beats.find(b=>t>=b.startMs&&t<b.endMs)?.caption??definition.beats.at(-1).caption;
    seek.value=t;clock.textContent=(t/1000).toFixed(1)+' / 20 s';return {timeMs:t,particles:effects.get('particles').geometry().particles};
  }
  function pause(){playing=false;cancelAnimationFrame(raf);}
  function tick(now){if(!playing)return;const next=Math.min(definition.durationMs,time+Math.max(0,now-last));last=Math.max(last,now);try{renderAt(next);}catch(e){pause();status.textContent='播放失败：'+e.message;return;}if(next>=definition.durationMs){pause();return;}raf=requestAnimationFrame(tick);}
  function play(){if(!ready)return;pause();renderAt(0);playing=true;last=performance.now();status.textContent='正在播放 · 20秒无声过程动画';raf=requestAnimationFrame(tick);}
  document.querySelector('#play').onclick=play;document.querySelector('#pause').onclick=pause;document.querySelector('#reset').onclick=()=>{pause();renderAt(0)};seek.oninput=()=>{pause();renderAt(Number(seek.value))};document.querySelector('#reduce').onchange=()=>renderAt(time);fontControl.oninput=()=>{try{setSubtitleFont(Number(fontControl.value));status.textContent='字幕字号已调整；上方画面布局保持固定。';}catch(e){fontControl.value=Number.parseInt(caption.style.fontSize);status.textContent=e.message;}};document.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});
  new ResizeObserver(()=>stage.style.transform=`scale(${frame.clientWidth/1600})`).observe(frame);
  window.evap={renderAt,pause,play,setSubtitleFont,get subtitleFont(){return Number.parseInt(caption.style.fontSize)},get playing(){return playing},get time(){return time},geometry:id=>id==='beaker'?asset.getBoundingClientRect().toJSON():effects.get(id).geometry()};
  window.evapReady=(async()=>{await document.fonts.ready;await asset.decode();const probe=document.createElement('canvas').getContext('2d');probe.font='32px monospace';const w=probe.measureText('蒸发Wim').width;probe.font='32px "Microsoft YaHei",monospace';if(probe.measureText('蒸发Wim').width===w)throw new Error('Microsoft YaHei missing');setSubtitleFont(zone.fontSize);ready=true;document.querySelectorAll('#play,#reset,#seek,#subtitle-size').forEach(e=>e.disabled=false);renderAt(19999);status.textContent='准备完成 · 点击播放，或拖动时间条查看过程';})();window.evapReady.catch(e=>status.textContent='准备失败：'+e.message);
})();
