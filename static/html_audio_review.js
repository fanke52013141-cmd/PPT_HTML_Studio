/* Audio owns the preview clock; this module never generates or approves. */
(function () {
  'use strict';
  let epoch=0, active=null;
  const selectedPages=new Map();
  const node=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
  function close() {
    epoch++;
    if(active){active.audio?.pause();cancelAnimationFrame(active.raf);active=null;}
    window.HtmlSemanticQA?.close();
  }
  function invalidate(message) {
    close();
    const host=document.getElementById('html-audio-review');
    if(!host||host.hidden)return;
    const notice=host.querySelector('[role="status"]');
    if(notice)notice.textContent=message||'旁白已变化，保存并生成当前音频后再试听。';
    host.querySelectorAll('audio').forEach(audio=>audio.removeAttribute('src'));
    host.querySelectorAll('button').forEach(button=>button.disabled=true);
  }
  async function mount(project) {
    close();
    const panel=document.getElementById('step-panel-6');
    let host=document.getElementById('html-audio-review');
    if(project?.visual_backend!=='html'){if(host)host.hidden=true;return;}
    if(!host){host=node('section');host.id='html-audio-review';panel.insertBefore(host,document.getElementById('step6-beats-list'));}
    host.hidden=false;host.replaceChildren();
    const token=epoch;
    host.append(node('h3','画面与配音同步试听'),node('p','选择页面，试听真实配音并检查动画；完成逐句核验后人工签收。'));
    const select=node('select');select.setAttribute('aria-label','同步试听页面');
    const reload=node('button','刷新试听与核验');reload.type='button';
    const toolbar=node('div');toolbar.className='html-audio-toolbar';toolbar.append(select,reload);
    const content=node('div');content.className='html-audio-content';host.append(toolbar,content);
    try {
      const result=await API.get(`/api/projects/${encodeURIComponent(project.id)}/steps/2/result`);
      if(token!==epoch)return;
      const slides=result.contract?.slides||[];
      for(const [i,s]of slides.entries()) {const o=node('option',`第 ${i+1} 页 · ${s.main_title||s.title||'未命名页面'}`);o.value=s.slide_id||s.id;select.append(o);}
      if(slides.some(s=>(s.slide_id||s.id)===selectedPages.get(project.id)))select.value=selectedPages.get(project.id);
      let pageVersion=0;
      async function loadPage() {
        const version=++pageVersion;
        if(active){active.audio?.pause();cancelAnimationFrame(active.raf);active=null;}
        window.HtmlSemanticQA?.close();content.replaceChildren();
        const sid=select.value;
        const message=node('p',sid?'正在读取当前画面和音频…':'请先完成分镜规划。');message.setAttribute('role','status');content.append(message);
        if(!sid)return;
        const current=()=>token===epoch&&version===pageVersion;
        const qa=node('div');qa.className='html-audio-qa';content.append(qa);
        let needsAudio=false;
        try {
          const base=`/api/projects/${encodeURIComponent(project.id)}`;
          const [doc,audios]=await Promise.all([
            API.get(`${base}/html-visual/${encodeURIComponent(sid)}/editor`,{silent:true}),
            API.get(`${base}/steps/7/audio-status`,{silent:true})]);
          if(!current())return;
          const audioStatus=audios.slides?.find(s=>s.slide_id===sid);
          if(!audioStatus?.audio_exists||audioStatus.stale||audioStatus.voice_config_stale){needsAudio=true;throw Error('请先生成当前页面的有效配音，再进行同步试听。');}
          const preview=await API.post(`${base}/html-visual/${encodeURIComponent(sid)}/editor/preview`,{
            scene:doc.scene,binding:doc.binding,expected_revision:doc.revision,anchor_overrides:doc.anchor_overrides||{}});
          if(!current())return;
          if(preview.clock!=='audio_timeline'){needsAudio=true;throw Error('尚无有效音频时间轴，请先完成配音。');}
          const frame=node('iframe');frame.title='当前音频绑定画面';frame.style.cssText='width:100%;aspect-ratio:16/9;border:0';
          const loaded=new Promise((resolve,reject)=>{frame.onload=resolve;frame.onerror=()=>reject(Error('共享播放器加载失败'));});
          frame.srcdoc='<!doctype html><meta charset="utf-8"><style>body{margin:0}.runtime-controls{display:none}</style><div id="viewport"></div><div class="runtime-controls"><select id="scene"></select><select id="theme"></select><textarea id="definition"></textarea><button id="apply"></button><button id="play"></button><button id="end"></button><input id="seek"><span id="time"></span><input id="font" value="32"><span id="font-value"></span><input type="checkbox" id="reduced"><p id="status"></p></div><script src="/api/html-scene-editor/runtime/data.js"></script><script src="/api/html-scene-editor/runtime/player.js"></script>';
          content.insertBefore(frame,qa);await loaded;if(!current())return;
          const player=frame.contentWindow.visualPlayer;
          if(!player||!await player.apply(preview.scene,preview.resources))throw Error('当前画面未通过播放器检查。');
          if(!current())return;
          const audio=node('audio');audio.controls=true;audio.preload='metadata';audio.setAttribute('aria-label','画面同步配音');audio.src=`${base}/slides/${encodeURIComponent(sid)}/audio?t=${Date.now()}`;
          const sentences=node('div');sentences.className='html-audio-sentences';content.insertBefore(audio,qa);content.insertBefore(sentences,qa);
          const playback={audio,raf:0};active=playback;
          const beats=preview.scene.beats||[];
          const buttons=beats.map((beat,i)=>{
            const b=node('button',`${i+1}. ${beat.text}`);b.type='button';
            b.onclick=()=>{audio.currentTime=beat.startMs/1000;sync();};sentences.append(b);return b;
          });
          let highlighted=-1;
          function sync(){
            if(!current())return;
            if(player.playing)player.pause();const time=audio.currentTime*1000;player.seek(time);
            const next=beats.findIndex(beat=>time>=beat.startMs&&time<beat.endMs);
            if(next!==highlighted){
              buttons[highlighted]?.removeAttribute('aria-current');
              buttons[next]?.setAttribute('aria-current','true');highlighted=next;
            }
          }
          function tick(){sync();if(current()&&!audio.paused&&!audio.ended)playback.raf=requestAnimationFrame(tick);}
          audio.addEventListener('play',()=>{panel.querySelectorAll('audio').forEach(other=>{if(other!==audio)other.pause();});cancelAnimationFrame(playback.raf);tick();});
          for(const event of ['timeupdate','seeked','pause','ended'])audio.addEventListener(event,sync);
          audio.addEventListener('error',()=>{if(current())message.textContent='音频加载失败，请刷新本页音频状态后再试听。';});
          message.textContent='音频驱动画面；点击句子可定位，拖动音频进度可检查对应动画。试听不代表已经签收。';sync();
        }catch(error){if(current()){
          message.textContent=`暂不能联播：${error.message}`;
          const go=node('button',needsAudio?'查看旁白与音频操作':'去完成本页 HTML 画面');go.type='button';content.insertBefore(go,qa);
          go.onclick=async()=>{
            if(needsAudio){document.getElementById('step6-btn-init')?.scrollIntoView({block:'nearest'});return;}
            await window.navigateToStep?.(5);
            const runtime=window.PPTStudio?.runtime?.state;
            if(runtime?.currentProject?.id!==project.id||runtime.currentStep!==5)return;
            const index=runtime.slides.findIndex(slide=>(slide.slide_id||slide.id)===sid);
            if(index>=0){runtime.activeSlideIndex=index;window.HtmlReviewPanel?.refresh();}
          };
        }}
        if(current())await window.HtmlSemanticQA?.mount(qa,project,sid);
      }
      select.onchange=()=>{selectedPages.set(project.id,select.value);loadPage();};reload.onclick=()=>loadPage();await loadPage();
    }catch(error){if(token===epoch)content.textContent=`读取失败：${error.message}`;}
  }
  window.HtmlAudioReview={mount,close,invalidate};
})();
