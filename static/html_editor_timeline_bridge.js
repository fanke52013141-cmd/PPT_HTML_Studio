// Owns timeline UI and its audio clock. Author transactions stay in HtmlSceneEditor.
(function () {
  'use strict';
  let bundle;
  function loadBundle() {
    if (window.HtmlEditorTimeline) return Promise.resolve();
    if (!bundle) bundle = new Promise((resolve, reject) => {
      const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = '/static/editor_ui/timeline.css';
      const script = document.createElement('script'); script.src = '/static/editor_ui/timeline.js';
      script.onload = resolve; script.onerror = () => { bundle = null; script.remove(); css.remove(); reject(Error('动作时间轴未加载')); };
      document.head.append(css, script);
    });
    return bundle;
  }
  async function create({ host, frame, projectId, slideId, getDocument, onEdit, onSelect, onClock, onPlay, onError, onValidateAudio }) {
    await loadBundle();
    let disposed = false, pending = false, layout = false, blocked = false, approvedPlay = false, validation = 0, raf = 0, preview = null, selected = [];
    const audio = document.createElement('audio'), status = document.createElement('p'), tracks = document.createElement('div');
    audio.controls = true; audio.preload = 'metadata'; audio.setAttribute('aria-label', '编辑器同步配音');
    status.setAttribute('role', 'status'); status.dataset.timelineStatus = '';
    tracks.dataset.editorTimeline = ''; host.append(status, audio, tracks);
    const base = `/api/projects/${encodeURIComponent(projectId)}`;
    let available = false;
    try {
      const result = await API.get(`${base}/steps/7/audio-status`, { silent: true });
      const item = result.slides?.find(s => s.slide_id === slideId);
      available = !!item?.audio_exists && !item.stale && !item.voice_config_stale;
    } catch (_) { /* Explicit read-only author preview below. */ }
    audio.hidden = !available;
    let mediaRevision = getDocument().audio_revision;
    const mediaUrl = () => `${base}/slides/${encodeURIComponent(slideId)}/audio?revision=${encodeURIComponent(mediaRevision || '')}`;
    if (available) audio.src = mediaUrl();
    const player = () => frame.contentWindow?.visualPlayer;
    const hasAudio = () => !blocked && available && preview?.clock === 'audio_timeline';
    function pause() { validation++; audio.pause(); player()?.pause(); cancelAnimationFrame(raf); raf = 0; }
    function sync() {
      if (disposed || !preview || layout || blocked) return;
      const p = player();
      const ms = hasAudio() ? Math.min(audio.currentTime * 1000, preview.scene.durationMs) : p.timeMs;
      if (hasAudio()) { p.pause(); p.seek(ms); }
      widget.setTime(ms); onClock(ms);
    }
    function tick() { sync(); if (!disposed && (hasAudio() ? !audio.paused && !audio.ended : player()?.playing)) raf = requestAnimationFrame(tick); }
    function seek(ms, exitLayout = true) {
      if (!preview || disposed || !Number.isFinite(ms)) return;
      pause(); if (exitLayout) onPlay();
      ms = Math.max(0, Math.min(ms, preview.scene.durationMs));
      if (hasAudio()) audio.currentTime = ms / 1000;
      player().seek(ms); widget.setTime(ms); onClock(ms);
    }
    const reasons = { beat_end: '语块末尾裁短', audio_end: '音频末尾裁短', next_action: '后续动作裁短' };
    function rows() {
      if (!preview) return [];
      const doc = getDocument(), timing = preview.timing;
      const beatRow = { id: 'sentences', actions: (timing?.beats || preview.scene.beats.map((b, i) => ({ ...b, beatId: String(i) }))).map(b =>
        ({ id: `beat:${b.beatId}`, start: b.startMs / 1000, end: b.endMs / 1000, effectId: 'none', movable: false, flexible: false,
          label: `${b.beatId} · ${b.text}`, description: '只读讲稿语块' })) };
      return [beatRow, ...doc.scene.nodes.map(n => ({ id: n.id, actions: preview.scene.motion.filter(a => a.targetId === n.id).map(a => {
        const id = a.actionId || `${a.targetId}:${a.type}`, info = timing?.actions.find(v => v.id === id);
        const canEdit = hasAudio() && !!info?.editable && !pending;
        return { id, start: a.startMs / 1000, end: (a.startMs + a.durationMs) / 1000, effectId: 'none',
          movable: canEdit, flexible: canEdit, selected: selected.includes(n.id),
          label: `${n.id} · ${a.type} · ${a.durationMs}ms`,
          description: `作者 ${info?.authorDurationMs ?? a.durationMs}ms；生效 ${a.durationMs}ms${info?.clippedBy.length ? '；' + info.clippedBy.map(r => reasons[r]).join('、') : ''}` };
      }) }))];
    }
    function refresh() { if (!disposed) widget.update(rows()); }
    function invalidate(message = '配音产物已变化；草稿已保留，请刷新配音与时序。') {
      blocked = true; approvedPlay = false; pause(); audio.removeAttribute('src'); audio.load();
      status.textContent = message; refresh();
    }
    async function startAudio() {
      pause(); const request = validation;
      try {
        await onValidateAudio(mediaRevision);
        if (disposed || request !== validation) return;
        approvedPlay = true; await audio.play();
      } catch (error) { approvedPlay = false; if (!disposed) { invalidate(error.message); onError(error); } }
    }
    function checkDuration() {
      if (hasAudio() && Number.isFinite(audio.duration) && Math.abs(audio.duration * 1000 - (preview.timing?.mediaDurationMs ?? preview.scene.durationMs)) > 250) {
        pause(); available = false;
        status.textContent = '配音与时间轴时长不一致；已停止联播，动作只读，请重新对齐音频。'; refresh();
      }
    }
    const widget = HtmlEditorTimeline.mountTimeline(tracks, { rows: [], onSeek: seek, onSelect: id => {
      const action = getDocument().scene.motion.find(a => (a.actionId || `${a.targetId}:${a.type}`) === id);
      if (action) onSelect(action.targetId);
    }, onGestureStart: pause, onEdit: async event => {
      if (disposed || pending) return;
      pause(); pending = true;
      try {
        if (!hasAudio()) throw Error('需要有效配音及语块时间轴才能编辑动作');
        const doc = getDocument();
        const candidate = HtmlEditorTimeline.timelineEdit(doc.scene, doc.binding, preview.timing, event.action.id,
          event.start * 1000, event.end * 1000, event.resize);
        if (JSON.stringify(candidate.scene) !== JSON.stringify(doc.scene) || JSON.stringify(candidate.binding) !== JSON.stringify(doc.binding))
          await onEdit(candidate);
      } catch (error) { if (!disposed) onError(error); }
      finally { pending = false; refresh(); }
    } });
    const listeners = [];
    function listen(event, action) { audio.addEventListener(event, action); listeners.push([event, action]); }
    listen('play', () => {
      if (!hasAudio()) { audio.pause(); return; }
      if (!approvedPlay) { audio.pause(); startAudio(); return; }
      approvedPlay = false; onPlay(); player().pause(); cancelAnimationFrame(raf); tick();
    });
    listen('loadedmetadata', checkDuration);
    for (const event of ['timeupdate', 'seeked', 'pause', 'ended']) listen(event, sync);
    listen('error', () => { if (blocked || disposed) return; pause(); available = false; status.textContent = '配音加载失败；动作只读，请刷新配音与时序。'; refresh(); });
    return { pause, seek, invalidate,
      async reloadAudio() {
        pause(); const result = await API.get(`${base}/steps/7/audio-status`, { silent: true });
        if (disposed) return;
        const item = result.slides?.find(s => s.slide_id === slideId);
        available = !!item?.audio_exists && !item.stale && !item.voice_config_stale;
        blocked = false; audio.hidden = !available;
        mediaRevision = getDocument().audio_revision;
        if (available) audio.src = mediaUrl(); else { audio.removeAttribute('src'); audio.load(); }
        if (preview) this.setPreview(preview);
      },
      setLayout(value) { layout = value; if (layout) pause(); },
      async play(restart = false) {
        if (!preview || disposed) return;
        if (blocked) throw Error('配音产物已变化，请刷新配音与时序后播放');
        if (!restart && (hasAudio() ? !audio.paused : player().playing)) { pause(); return; }
        onPlay(); if (restart || player().timeMs >= preview.scene.durationMs) seek(0);
        if (hasAudio()) { await startAudio(); }
        else { player().play(); cancelAnimationFrame(raf); tick(); }
      },
      setPreview(value) {
        pause(); preview = value;
        if (available && value.audio_revision !== mediaRevision) { invalidate(); return; }
        status.textContent = hasAudio() ? '配音驱动画面和游标；拖动调原句偏移，拉伸调时长。讲稿只读；裁短原因见动作提示。' : '无有效配音：预览时钟，动作轨道只读。请先生成有效配音，再刷新配音与时序。';
        checkDuration(); refresh();
      },
      select(ids) { selected = ids; refresh(); },
      destroy() {
        if (disposed) return;
        disposed = true; pause(); for (const [event, action] of listeners) audio.removeEventListener(event, action);
        audio.removeAttribute('src'); audio.load(); widget.destroy(); host.replaceChildren();
      },
    };
  }
  window.HtmlEditorTimelineBridge = { create };
})();
