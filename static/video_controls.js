// Shared video tools; native and composition previews keep their playback engines.
(function(){
  const audioNodes = new WeakMap();
  let audioContext;
  async function amplify(media, amount){
    audioContext ||= new AudioContext();
    await audioContext.resume();
    for(const node of media){
      let gain = audioNodes.get(node);
      if(!gain){const source=audioContext.createMediaElementSource(node);gain=audioContext.createGain();source.connect(gain);gain.connect(audioContext.destination);audioNodes.set(node,gain);}
      gain.gain.value=amount;
    }
  }
  window.attachVideoTools=function(host, adapter){
    if(!host) return;
    if(host.querySelector(':scope > .shared-video-tools')) return;
    const tools=document.createElement('div');tools.className='shared-video-tools';
    tools.innerHTML='<label>倍速 <select aria-label="播放倍速"><option>0.5</option><option selected>1</option><option>1.25</option><option>1.5</option><option>2</option></select></label><label>音量增强 <select aria-label="音量增强"><option value="1">100%</option><option value="1.5">150%</option><option value="2">200%</option></select></label><button type="button">全屏</button><button type="button">画中画</button>';
    const selects=tools.querySelectorAll('select');
    selects[0].onchange=()=>adapter.rate(Number(selects[0].value));
    selects[1].onchange=()=>amplify(adapter.media(),Number(selects[1].value)).catch(e=>showToast('音量增强不可用：'+e.message));
    const buttons=tools.querySelectorAll('button');
    buttons[0].onclick=()=>host.requestFullscreen().catch(e=>showToast(e.message));
    buttons[1].onclick=async()=>{
      try{
        const video=adapter.media().find(n=>n.tagName==='VIDEO');
        if(video&&document.pictureInPictureEnabled){await video.requestPictureInPicture();return;}
        if(!window.documentPictureInPicture){showToast('当前浏览器不支持此预览的画中画');return;}
        const pip=await window.documentPictureInPicture.requestWindow({width:800,height:500});
        document.querySelectorAll('style,link[rel=stylesheet]').forEach(style=>pip.document.head.append(style.cloneNode(true)));
        const marker=document.createComment('player');host.before(marker);pip.document.body.style.margin='0';pip.document.body.append(host);
        pip.addEventListener('pagehide',()=>{marker.replaceWith(host);});
      }catch(e){showToast('画中画不可用：'+e.message);}
    };
    if(adapter.download){const link=document.createElement('a');link.textContent='下载视频';link.href=adapter.download;link.download='video.mp4';tools.append(link);}
    host.append(tools);
  };
  function decorate(){document.querySelectorAll('.step8-video-list video').forEach(video=>{
    const host=video.parentElement;
    if(!host.querySelector('.shared-video-transport')){
      host.classList.add('shared-video-player');
      video.controls=false;
      const transport=document.createElement('div');transport.className='shared-video-transport';
      transport.innerHTML='<button type="button" aria-label="播放">▶</button><button type="button" aria-label="静音">♪</button><span>0:00 / 0:00</span><input type="range" aria-label="视频进度" min="0" max="1000" value="0">';
      const [play,mute]=transport.querySelectorAll('button');
      const range=transport.querySelector('input'),clock=transport.querySelector('span');
      play.onclick=()=>video.paused?video.play().catch(e=>showToast(e.message)):video.pause();
      mute.onclick=()=>{video.muted=!video.muted;mute.textContent=video.muted?'静音':'♪';};
      range.oninput=()=>{if(Number.isFinite(video.duration)) video.currentTime=Number(range.value)/1000*video.duration;};
      const time=n=>`${Math.floor((n||0)/60)}:${String(Math.floor((n||0)%60)).padStart(2,'0')}`;
      const update=()=>{play.textContent=video.paused?'▶':'Ⅱ';play.setAttribute('aria-label',video.paused?'播放':'暂停');clock.textContent=`${time(video.currentTime)} / ${time(video.duration)}`;range.value=video.duration?String(video.currentTime/video.duration*1000):'0';};
      ['timeupdate','loadedmetadata','play','pause','ended'].forEach(name=>video.addEventListener(name,update));
      host.append(transport);
    }
    attachVideoTools(host,{rate:n=>video.playbackRate=n,media:()=>[video],download:video.currentSrc||video.src});
  });}
  document.addEventListener('DOMContentLoaded',()=>{decorate();new MutationObserver(decorate).observe(document.body,{childList:true,subtree:true});});
})();
