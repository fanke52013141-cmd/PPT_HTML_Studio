// Unattended jobs only. Original handoff owner displays/imports/saves candidates.
(function () {
  'use strict';
  if (window.HtmlPiAgent) return;
  const element = (tag, text, attrs = {}) => Object.assign(document.createElement(tag), { textContent: text, ...attrs });
  function mount(host, options) {
    const box = element('section', ''), title = element('strong', 'AI 自动修改'), status = element('p', '', { role: 'status' });
    const start = element('button', '开始 AI 修改', { type: 'button' });
    const cancel = element('button', '取消任务', { type: 'button', disabled: true });
    const reconnect = element('button', '恢复任务状态', { type: 'button' });
    box.dataset.piAgent = '';
    const autoSave=element('input','',{type:'checkbox'}),saveLabel=element('label','检查通过后自动另存版本（保留历史，不批准画面）');
    saveLabel.prepend(autoSave);
    box.append(title, element('p', '自动读取资料、看图、检查并修复；可返回候选或在提交时授权另存版本。'),saveLabel, start, cancel, reconnect, status);
    host.insertBefore(box, options.before || null);
    const ctx = options.getContext(), base = `/api/projects/${encodeURIComponent(ctx.projectId)}/html-visual/${encodeURIComponent(ctx.slideId)}/agent/jobs`;
    const key = `html-pi-job:${ctx.projectId}:${ctx.slideId}`;
    let timer = null, destroyed = false, running = false, reference = null;
    const current = () => !destroyed && options.isCurrent() && box.isConnected;
    function remember(value) { reference = value; localStorage.setItem(key, JSON.stringify(value)); }
    function schedule() { if (current()) timer = setTimeout(() => poll().catch(failed), 1500); }
    function failed(error) {
      if (!current()) return;
      if(reference?.pending && [400,404,409,422].includes(error.status)){
        reference=null;localStorage.removeItem(key);
      }
      running = false; start.disabled = !!reference; cancel.disabled = true;
      status.textContent = reference ? `${error.message}；可恢复任务状态，页面断开不会取消后台任务。` : error.message;
    }
    async function poll() {
      clearTimeout(timer);
      if (!current() || !reference) return;
      const job = await API.get(`${base}/${encodeURIComponent(reference.job_id)}`);
      if (!current()) return;
      running = ['queued', 'running'].includes(job.status);
      start.disabled = running; cancel.disabled = !running || job.can_cancel === false;
      status.textContent = running ? `AI 正在${job.status === 'queued' ? '排队' : '执行'} · ${job.progress}% · 已检查 ${job.usage.candidate_rounds} 轮` : '';
      if (running) { schedule(); return; }
      if (job.status === 'succeeded') {
        if(job.result.saved){
          const alreadyLoaded=reference.saved_revision===job.result.saved_revision;
          // Persist consumption before editor reload destroys and remounts this owner.
          if(!alreadyLoaded){remember({...reference,saved_revision:job.result.saved_revision});await options.onSaved?.();}
          if(current())status.textContent=`AI 修改已自动另存版本 ${job.result.saved_revision}，画面批准仍按原流程。`;
          return;
        }
        status.textContent = 'AI 已完成自动检查，正在显示候选…';
        await options.onResult(job.result.preview);
        if (current()) status.textContent = 'AI 修改完成，候选已显示；可以继续人工微调或保存。';
      } else status.textContent = job.error?.message || `任务已${job.status}`;
    }
    start.onclick = async () => {
      if (!current() || running) return;
      start.disabled = true;
      try {
        const task = options.getTask();
        const payload = { idempotency_key: crypto.randomUUID(), task,delivery_policy:autoSave.checked?'save_revision':'candidate' };
        // Retain the key before sending so uncertain HTTP outcomes can be reconciled.
        remember({ pending: payload });
        const job = await API.post(base, payload, { timeoutMs: 15000 });
        remember({ job_id: job.job_id });
        await poll();
      } catch (error) { failed(error); }
    };
    cancel.onclick = async () => {
      if (!reference?.job_id || !current()) return;
      try { await API.post(`${base}/${encodeURIComponent(reference.job_id)}/cancel`, {}); status.textContent = '已请求取消，正在等待安全结束…'; schedule(); }
      catch (error) { failed(error); }
    };
    reconnect.onclick = async () => {
      if (!current()) return;
      try {
        reference = JSON.parse(localStorage.getItem(key) || 'null');
        if (!reference) throw Error('本页尚无 AI 修改任务');
        if (reference.pending) {
          const job = await API.post(base, reference.pending, { timeoutMs: 15000 });
          remember({ job_id: job.job_id });
        }
        await poll();
      } catch (error) { failed(error); }
    };
    try { reference = JSON.parse(localStorage.getItem(key) || 'null'); } catch (_) { reference = null; }
    if (reference?.job_id) schedule();
    return { destroy() { destroyed = true; clearTimeout(timer); box.remove(); } };
  }
  window.HtmlPiAgent = { mount };
})();
