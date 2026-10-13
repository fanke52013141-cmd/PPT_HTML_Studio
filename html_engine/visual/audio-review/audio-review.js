"use strict";
(async () => {
  while (!window.visualPlayer?.ready) await new Promise(resolve => setTimeout(resolve, 25));
  const data = window.AudioReviewData, audio = document.getElementById("audio");
  const $ = id => document.getElementById(id);
  let frame = 0, requestedSeek = null;
  const buttons = [];
  $("review-note").textContent = data.note;
  const render = ms => {
    ms = Math.max(0, Math.min(window.visualPlayer.scene.durationMs, ms));
    window.visualPlayer.seek(ms);
    buttons.forEach(({button,beat}) => button.classList.toggle("active", ms >= beat.startMs && ms < beat.endMs));
  };
  const seek = ms => {
    requestedSeek = ms;
    audio.pause(); window.visualPlayer.pause(); render(ms);
    audio.currentTime = Math.min(ms/1000, Number.isFinite(audio.duration) ? audio.duration : ms/1000);
  };
  const tick = () => {
    render(audio.currentTime * 1000);
    if (!audio.paused && !audio.ended) frame = requestAnimationFrame(tick);
  };
  for (const [index,beat] of data.beats.entries()) {
    const button = document.createElement("button"), label = document.createElement("span");
    label.textContent = `${String(index+1).padStart(2,"0")} · ${(beat.startMs/1000).toFixed(1)}—${(beat.endMs/1000).toFixed(1)} s`;
    button.append(label,document.createTextNode(beat.spoken_text));
    button.onclick = () => { seek(beat.startMs); audio.play().catch(() => {$("status").textContent="请点击音频播放按钮。";}); };
    buttons.push({button,beat}); $("beats").append(button);
  }
  $("play").onclick = () => audio.paused ? audio.play() : audio.pause();
  $("end").onclick = () => seek(window.visualPlayer.scene.durationMs);
  $("seek").oninput = () => seek(Number($("seek").value));
  audio.onplay = () => {window.visualPlayer.pause(); cancelAnimationFrame(frame); $("play").textContent="暂停"; tick();};
  audio.onpause = () => {cancelAnimationFrame(frame); $("play").textContent="播放"; render(requestedSeek ?? audio.currentTime*1000);};
  audio.onseeked = () => {render(requestedSeek ?? audio.currentTime*1000);requestedSeek=null;};
  audio.onended = () => {cancelAnimationFrame(frame); render(window.visualPlayer.scene.durationMs); $("play").textContent="播放";};
  audio.onerror = () => {$("status").textContent="音频无法加载，请检查本地音频文件。";};
  window.audioReview = {seek,render,beats:data.beats,audio,ready:true};
  render(0);
})().catch(error => {document.getElementById("status").textContent=error.message;});
