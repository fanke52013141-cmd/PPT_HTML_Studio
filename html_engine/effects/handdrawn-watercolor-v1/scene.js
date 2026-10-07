(() => {
  'use strict';
  const $=id=>document.getElementById(id),frame=$('frame'),scene=$('scene'),status=$('status');
  const effects={
    tag:WatercolorEffects.mount($('tag-host'),'label',{id:'concept-tag',width:315,height:94,text:'蒸发是什么？',fontSize:39,color:'pink'}),
    arrow:WatercolorEffects.mount($('arrow-host'),'arrow',{id:'direction',width:190,height:165,color:'blue'}),
    spark:WatercolorEffects.mount($('spark-host'),'icon',{id:'spark',icon:'spark',width:70,height:70,color:'yellow'}),
    leaf:WatercolorEffects.mount($('leaf-host'),'icon',{id:'leaf',icon:'leaf',width:80,height:90,color:'green'}),
    underline:WatercolorEffects.mount($('underline-host'),'underline',{id:'title-underline',width:630,height:35,color:'yellow'})
  };
  const beats=[
    {start:0,end:2700,caption:'水面很平静，水却一直在慢慢变化。'},
    {start:2700,end:6500,caption:'一部分水会变成水蒸气，进入空气。'},
    {start:6500,end:9500,caption:'液态的水，变成了气态的水蒸气。'},
    {start:9500,end:12001,caption:'这个过程叫蒸发，不需要沸腾。'}
  ];
  const duration=12000,smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x);},progress=(t,start,length)=>smooth((t-start)/length);
  let time=0,ready=false,playing=false,last=0,raf=0;
  const resize=()=>scene.style.transform=`scale(${frame.clientWidth/1600})`;
  new ResizeObserver(resize).observe(frame);resize();
  function setSubtitleFont(value){const size=Number(value);if(!Number.isInteger(size)||size<20||size>44)throw new RangeError('字幕字号范围为 20—44px');const probe=document.createElement('canvas').getContext('2d');probe.font=`${size}px Microsoft YaHei`;for(const beat of beats){if(probe.measureText(beat.caption).width>1440)throw new Error('字幕过长，需拆分或缩小字号');}const el=$('subtitle-zone');el.style.fontSize=size+'px';$('font-size').value=String(size);$('font-value').textContent=size+' px';}
  function renderAt(value){if(!ready)throw new Error('Resources not ready');const t=Number(value);if(!Number.isFinite(t)||t<0||t>duration)throw new RangeError('Invalid time');time=t;
    const alpha=(id,q,offset=0)=>{$(id).style.opacity=String(q);$(id).style.transform=`translateY(${offset*(1-q)}px)`};
    alpha('title',progress(t,0,850),12);alpha('subhead',progress(t,450,850),10);alpha('beaker',progress(t,550,1400),28);
    effects.underline.at(progress(t,900,1050));effects.leaf.at(progress(t,1250,900));effects.spark.at(progress(t,1550,900));
    effects.arrow.at(progress(t,4000,1800));effects.tag.at(progress(t,6100,1300));
    alpha('callout',progress(t,7100,950),12);alpha('small-note',progress(t,8400,800),6);
    $('subtitle-zone').textContent=beats.find(b=>t>=b.start&&t<b.end)?.caption||beats.at(-1).caption;
    $('seek').value=String(t);$('clock').textContent=`${(t/1000).toFixed(1)} / 12 s`;return t;
  }
  function pause(){playing=false;cancelAnimationFrame(raf)}
  function tick(now){if(!playing)return;const next=Math.min(duration,time+Math.max(0,now-last));last=Math.max(last,now);renderAt(next);if(next>=duration){pause();return}raf=requestAnimationFrame(tick)}
  function play(){if(!ready)return;pause();renderAt(0);playing=true;last=performance.now();raf=requestAnimationFrame(tick)}
  $('play').onclick=play;$('pause').onclick=pause;$('reset').onclick=()=>{pause();renderAt(0)};$('seek').oninput=()=>{pause();renderAt(Number($('seek').value))};$('font-size').oninput=()=>{try{setSubtitleFont(Number($('font-size').value));status.textContent='字幕字号已调整';}catch(e){status.textContent=e.message;}};
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});
  window.watercolorScene={renderAt,play,pause,setSubtitleFont,get time(){return time},get playing(){return playing},effects};
  window.watercolorReady=(async()=>{await document.fonts.ready;await $('beaker').decode();setSubtitleFont(32);ready=true;$('play').disabled=$('reset').disabled=$('seek').disabled=false;renderAt(12000);status.textContent='准备完成 · 点击播放，或拖动时间条检查过程';})();window.watercolorReady.catch(e=>status.textContent='准备失败：'+e.message);
})();
