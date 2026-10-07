(() => {
  'use strict';
  const $=id=>document.getElementById(id),d=ScienceDefinition,smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)},q=(t,start,length)=>smooth((t-start)/length);
  let ready=false,time=0,playing=false,last=0,raf=0;
  const paths=['target','leader','phase-arrow'].map(id=>{const e=$(id),length=e.getTotalLength();e.style.strokeDasharray=length;return {e,length}});
  new ResizeObserver(()=>$('stage').style.transform=`scale($('frame').clientWidth/1600)`).observe($('frame'));
  function font(value){const n=Number(value);if(!Number.isInteger(n)||n<20||n>44)throw new RangeError('字幕字号范围20—44px');const c=document.createElement('canvas').getContext('2d');c.font=`${n}px Microsoft YaHei`;if(d.beats.some(b=>c.measureText(b.text).width>1440))throw new Error('字幕过长，需缩小或拆分');$('subtitle').style.fontSize=n+'px';$('font').value=n;$('font-value').textContent=n+' px'}
  function renderAt(ms){if(!ready)throw new Error('Resources not ready');if(!Number.isFinite(ms)||ms<0||ms>d.durationMs)throw new RangeError('Invalid scene time');time=ms;const reduced=$('reduce').checked;
    const show=(id,start,length,offset=0)=>{const x=q(ms,start,length);$(id).style.opacity=x;$(id).style.transform=`translateY(${reduced?0:(1-x)*offset}px)`};
    show('title',0,850,12);show('lead',300,850,8);show('cup',500,1300,24);[2000,5000,8500].forEach((s,i)=>show('step-'+i,s,850,14));show('phase',10500,850,8);show('callout',12500,650);show('conclusion',14000,850,8);
    paths.forEach(({e,length},i)=>{const p=q(ms,i===2?10800:12000+(i*300),i===2?1000:1200);e.style.strokeDashoffset=length*(1-p);e.style.opacity=p>0?1:0});
    $('subtitle').textContent=d.beats.find(b=>ms>=b.start&&ms<b.end)?.text||d.beats.at(-1).text;$('seek').value=ms;$('clock').textContent=`${(ms/1000).toFixed(1)} / 18 s`;return ms;
  }
  function pause(){playing=false;cancelAnimationFrame(raf)}
  function tick(now){if(!playing)return;const next=Math.min(d.durationMs,time+Math.max(0,now-last));last=Math.max(last,now);renderAt(next);if(next>=d.durationMs){pause();return}raf=requestAnimationFrame(tick)}
  function play(){if(!ready)return;pause();renderAt(0);playing=true;last=performance.now();raf=requestAnimationFrame(tick)}
  $('play').onclick=play;$('pause').onclick=pause;$('reset').onclick=()=>{pause();renderAt(0)};$('seek').oninput=()=>{pause();renderAt(Number($('seek').value))};$('reduce').onchange=()=>renderAt(time);$('font').oninput=()=>{try{font($('font').value)}catch(e){$('status').textContent=e.message;$('font').value=parseInt($('subtitle').style.fontSize)}};document.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});
  window.scienceScene={renderAt,pause,play,setSubtitleFont:font,get time(){return time},get playing(){return playing}};
  window.scienceReady=(async()=>{await document.fonts.ready;await $('cup').decode();font(32);ready=true;$('play').disabled=$('reset').disabled=$('seek').disabled=false;renderAt(d.durationMs);$('status').textContent='准备完成 · 18秒无声预演 · 一张复用插画，其余为CSS/SVG可控对象';})();scienceReady.catch(e=>$('status').textContent='准备失败：'+e.message);
})();
