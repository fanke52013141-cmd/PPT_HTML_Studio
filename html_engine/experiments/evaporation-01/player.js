(() => {
  'use strict';
  const stage=document.querySelector('#stage'),frame=document.querySelector('#frame'),definition=window.EvapDefinition;
  const effects=new Map();
  function put(id,type,x,y,params){const host=document.createElement('div');host.className='object';host.style.left=x+'px';host.style.top=y+'px';stage.append(host);const fx=FlatEffects.mount(host,type,{...params,id});effects.set(id,fx);return fx;}
  put('title','text',100,60,{text:definition.title,width:1380,height:100,fontSize:62,bold:true,accent:'蒸发'});
  put('subtitle','text',104,165,{text:'不需要沸腾，也可以蒸发',width:1100,height:70,fontSize:28});
  put('sun','sun',135,265,{width:235,height:225});
  put('particles','flow',585,265,{width:360,height:285,count:6,seed:17});
  put('direction','arrow',1020,360,{width:180,height:160});
  put('term','paper',1200,392,{text:'蒸发',width:230,height:95,fontSize:44});
  put('state','mark',515,669,{text:'液态 → 气态',width:540,height:126,fontSize:43});
  put('explanation','text',510,800,{text:'水变成水蒸气，进入空气。',accent:'水蒸气',width:710,height:70,fontSize:28});
  const asset=document.createElement('img');asset.className='beaker';asset.src='assets/beaker.png';asset.alt='独立手绘烧杯插画，半杯蓝色水';stage.insertBefore(asset,stage.children[3]);
  const hint=document.createElement('div');hint.className='hint';hint.textContent='蓝点表示过程方向\n数量不是实测';hint.style.whiteSpace='pre-line';stage.append(hint);
  const caption=document.createElement('div');caption.className='caption';stage.append(caption);
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
  document.querySelector('#play').onclick=play;document.querySelector('#pause').onclick=pause;document.querySelector('#reset').onclick=()=>{pause();renderAt(0)};seek.oninput=()=>{pause();renderAt(Number(seek.value))};document.querySelector('#reduce').onchange=()=>renderAt(time);document.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});
  new ResizeObserver(()=>stage.style.transform=`scale(${frame.clientWidth/1600})`).observe(frame);
  window.evap={renderAt,pause,play,get playing(){return playing},get time(){return time},geometry:id=>id==='beaker'?asset.getBoundingClientRect().toJSON():effects.get(id).geometry()};
  window.evapReady=(async()=>{await document.fonts.ready;await asset.decode();const probe=document.createElement('canvas').getContext('2d');probe.font='32px monospace';const w=probe.measureText('蒸发Wim').width;probe.font='32px "Microsoft YaHei",monospace';if(probe.measureText('蒸发Wim').width===w)throw new Error('Microsoft YaHei missing');ready=true;document.querySelectorAll('#play,#reset,#seek').forEach(e=>e.disabled=false);renderAt(19999);status.textContent='准备完成 · 点击播放，或拖动时间条查看过程';})();window.evapReady.catch(e=>status.textContent='准备失败：'+e.message);
})();
