/* Explicit HTML sheet lifecycle; shared API, persisted tasks and manual review. */
(function () {
  'use strict';
  let epoch = 0;
  const el = (tag, text, cls) => { const item = document.createElement(tag); if (text) item.textContent = text; if (cls) item.className = cls; return item; };
  async function open(container, project) {
    const ticket = ++epoch;
    container.replaceChildren();
    if (project?.visual_backend !== 'html') return;
    const base = `/api/projects/${encodeURIComponent(project.id)}/html-asset-sheets`;
    const panel = el('section', '', 'html-asset-sheets'); container.append(panel);
    panel.append(el('h3', '批量生成配图'));
    panel.append(el('p', '一张素材图生成多个独立配图。逐个检查内容与边缘，通过后加入可用素材。白色或半透明主体建议使用透明背景。'));
    const form = el('div', '', 'html-sheet-form'); panel.append(form);
    const requirements = el('textarea'); requirements.rows = 4;
    requirements.setAttribute('aria-label', '配图需求'); requirements.placeholder = '每行一个配图，例如：\n完整的透明玻璃冷杯，杯外少量水滴\n独立的放大水滴示意';
    const background = el('select'); background.setAttribute('aria-label', '素材背景');
    for (const [value, label] of [['source_alpha', '透明背景'], ['boundary_color', '白色背景（仅适合主体与背景分明的配图）']]) {
      const option = el('option', label); option.value = value; background.append(option);
    }
    const generate = el('button', '生成配图', 'btn btn-primary'); generate.type = 'button';
    const refresh = el('button', '刷新候选', 'btn'); refresh.type = 'button';
    const stop = el('button', '停止生成', 'btn'); stop.type = 'button'; stop.hidden = true;
    const cleanup = el('input'); cleanup.type = 'checkbox';
    const cleanupLabel = el('label'); cleanupLabel.append(cleanup, document.createTextNode('清理透明背景中的微弱残留（保留主体边缘）'));
    form.append(requirements, background, cleanupLabel, generate, refresh, stop);
    const status = el('p', '正在读取…'); status.setAttribute('role', 'status'); panel.append(status);
    const select = el('select'); select.setAttribute('aria-label', '素材候选版本'); panel.append(select);
    const cards = el('div', '', 'html-sheet-cards'); panel.append(cards);
    let task = null, candidates = [], pending = false;
    const alive = () => ticket === epoch && container.isConnected;
    function busy(value) { pending = value; generate.disabled = value; refresh.disabled = value; }
    function candidateUrl(item) { return `${base}/${encodeURIComponent(item.sheet_id)}/${encodeURIComponent(item.request_key)}`; }
    async function submitCandidateAction(item, suffix, body) {
      if (pending) return;
      busy(true);
      try {
        const result = await API.post(candidateUrl(item) + suffix, body);
        if (alive()) await poll(result.data.task, item);
      } catch (error) {
        if (alive()) status.textContent = error.status === 409 ? '候选审阅已变化，请刷新后重新提交。' : error.message;
      } finally { if (alive()) busy(false); }
    }
    async function showCandidate(item) {
      if (!item || pending) return;
      busy(true);
      try {
        const doc = (await API.get(candidateUrl(item))).data;
        if (!alive()) return;
        select.value = item.request_key; cards.replaceChildren();
        const assess = el('button', 'AI检查配图', 'btn'); assess.type = 'button';
        assess.disabled = !doc.manifest.assets.length;
        assess.addEventListener('click', () => submitCandidateAction(item, '/assess', {}));
        cards.append(assess);
        for (const asset of doc.manifest.assets) {
          const card = el('article', '', 'html-sheet-card');
          const image = el('img'); image.alt = asset.need; image.src = `${candidateUrl(item)}/${encodeURIComponent(asset.id)}/image`;
          card.append(image, el('h4', asset.need));
          const advisory = doc.advisory?.findings?.[asset.id];
          if (advisory) {
            const actions = {accept_candidate: '建议审阅后使用', regenerate: '建议重新生成', reextract: '建议重新处理边缘', manual_review: '需人工判断'};
            card.append(el('p', `AI辅助审阅：${actions[advisory.action] || '需人工判断'}。${advisory.reason}`));
          }
          const cleanupInfo = asset.processing?.alpha_cleanup;
          if (cleanupInfo) card.append(el('p', `已清理${cleanupInfo.removed_pixels}个微透明残留像素，请核对细节。`));
          const decision = doc.decisions[asset.id] || {};
          const identity = el('input'); identity.type = 'checkbox'; identity.checked = decision.identity === 'approved';
          const edge = el('input'); edge.type = 'checkbox'; edge.checked = decision.edge === 'approved';
          const first = el('label'); first.append(identity, document.createTextNode('对象内容正确'));
          const second = el('label'); second.append(edge, document.createTextNode('轮廓完整、背景与边缘可用'));
          const note = el('input'); note.type = 'text'; note.maxLength = 1000; note.placeholder = '审阅备注'; note.value = decision.note || '';
          const save = el('button', '保存审阅', 'btn'); save.type = 'button';
          const accept = el('button', doc.accepted[asset.id] ? '已加入素材' : '加入可用素材', 'btn'); accept.type = 'button';
          const locked = !!doc.accepted[asset.id];
          identity.disabled = edge.disabled = note.disabled = save.disabled = locked;
          const updateAccept = () => { accept.disabled = locked || !identity.checked || !edge.checked ||
            doc.decisions[asset.id]?.identity !== 'approved' || doc.decisions[asset.id]?.edge !== 'approved'; };
          identity.addEventListener('change', () => { accept.disabled = true; });
          edge.addEventListener('change', () => { accept.disabled = true; });
          updateAccept();
          save.addEventListener('click', async () => {
            if (pending) return;
            busy(true); save.disabled = true;
            try {
              const result = (await API.put(`${candidateUrl(item)}/${encodeURIComponent(asset.id)}/review`, {
                identity: identity.checked ? 'approved' : 'rejected', edge: edge.checked ? 'approved' : 'rejected',
                note: note.value, expected_revision: doc.revision,
              })).data;
              if (!alive()) return;
              doc.revision = result.revision; doc.decisions = result.decisions;
              status.textContent = '审阅已保存。'; updateAccept();
            } catch (error) { if (alive()) status.textContent = error.status === 409 ? '审阅已被其他操作修改，本地选择已保留。请记录选择后刷新候选。' : error.message; }
            finally { if (alive()) {busy(false); save.disabled = false;} }
          });
          accept.addEventListener('click', async () => {
            if (pending) return;
            busy(true); accept.disabled = true;
            try {
              await API.post(`${candidateUrl(item)}/${encodeURIComponent(asset.id)}/accept`, {expected_revision: doc.revision});
              if (!alive()) return;
              doc.accepted[asset.id] = true; accept.textContent = '已加入素材';
              identity.disabled = edge.disabled = note.disabled = save.disabled = true;
              retry.disabled = retryNeed.disabled = true;
              status.textContent = '已加入可用素材；在对象编辑器中重新打开资源列表后选择。';
            } catch (error) { if (alive()) {status.textContent = error.message; updateAccept();} }
            finally { if (alive()) busy(false); }
          });
          const retryNeed = el('input'); retryNeed.type = 'text'; retryNeed.maxLength = 1000; retryNeed.value = asset.need;
          retryNeed.setAttribute('aria-label', `重新生成需求 ${asset.id}`);
          const retry = el('button', '仅重新生成这个对象', 'btn'); retry.type = 'button';
          retry.disabled = locked; retryNeed.disabled = locked;
          retry.addEventListener('click', () => {
            if (!retryNeed.value.trim()) {status.textContent = '请填写重新生成的对象需求。'; return;}
            submitCandidateAction(item, `/${encodeURIComponent(asset.id)}/retry`, {expected_revision: doc.revision, need: retryNeed.value.trim()});
          });
          card.append(first, second, note, save, accept, retryNeed, retry); cards.append(card);
        }
        for (const failure of doc.manifest.failures) {
          const failed = el('div'); failed.append(el('p', `${failure.asset_id}：${failure.message}`));
          const retry = el('button', `重试失败对象 ${failure.asset_id}`, 'btn'); retry.type = 'button';
          retry.addEventListener('click', () => submitCandidateAction(item, `/${encodeURIComponent(failure.asset_id)}/retry`, {expected_revision: doc.revision}));
          failed.append(retry); cards.append(failed);
        }
        status.textContent = doc.manifest.failures.length ? '部分配图提取失败，可审阅其余候选。' : '请逐个核对配图内容与边缘。';
      } catch (error) { if (alive()) status.textContent = error.message; }
      finally { if (alive()) busy(false); }
    }
    async function poll(value, preferred = null) {
      task = value; busy(true); stop.hidden = false;
      let terminal = '';
      try {
        while (alive() && ['queued', 'running'].includes(task.status)) {
          const operation = task.type === 'html_asset_sheet_assess' ? 'AI检查配图' : task.type === 'html_asset_sheet_retry' ? '单对象重试' : '配图生成';
          status.textContent = task.status === 'queued' ? `${operation}排队中…` : `正在执行${operation}…`;
          await new Promise(resolve => setTimeout(resolve, 700));
          if (!alive()) return;
          task = (await API.get(`/api/projects/${encodeURIComponent(project.id)}/html-review/tasks/${encodeURIComponent(task.id)}`)).task;
        }
        if (!alive()) return;
        if (task.status === 'succeeded' && task.result) {
          const result = task.result.manifest || task.result;
          if (result.sheet_id && result.request_key) preferred = {sheet_id: result.sheet_id, request_key: result.request_key};
        }
        const labels = {cancelled:'已请求停止；进行中的图片请求结束后停止，源图或候选会保留。', interrupted:'上次生成已中断，可以重新提交。', failed:'生成失败，可以重新提交。'};
        terminal = task.status === 'succeeded' ? (task.type === 'html_asset_sheet_assess' ? 'AI检查已完成，请结合建议逐个审阅。' : '配图已生成，请审阅。') : (task.error || labels[task.status] || '任务已结束。');
        status.textContent = terminal;
      } catch (error) { if (alive()) status.textContent = `状态读取失败：${error.message}。请刷新候选以恢复任务。`; }
      finally { if (alive()) {busy(false); stop.hidden = true; task = null;} }
      if (alive()) {await load(false, preferred); if (terminal) status.textContent = terminal;}
    }
    async function load(resume = true, preferred = null) {
      const result = (await API.get(base)).data;
      if (!alive()) return;
      candidates = result.candidates; select.replaceChildren();
      for (const item of candidates) { const option = el('option', `${item.sheet_id} · ${item.request_key.slice(0,8)}`); option.value = item.request_key; select.append(option); }
      if (resume && result.task && ['queued','running'].includes(result.task.status)) { await poll(result.task); return; }
      const completed = result.task?.status === 'succeeded' ? (result.task.result?.manifest || result.task.result) : null;
      const selectedKey = preferred?.request_key || completed?.request_key;
      if (candidates.length) await showCandidate(candidates.find(item => item.request_key === selectedKey) || candidates[candidates.length - 1]);
      else status.textContent = result.task?.error || '填写配图需求后开始生成。';
    }
    select.addEventListener('change', () => { const item = candidates.find(c => c.request_key === select.value); if (item) showCandidate(item); });
    refresh.addEventListener('click', () => load().catch(error => {if (alive()) status.textContent = error.message;}));
    stop.addEventListener('click', async () => {
      if (!task) return;
      stop.disabled = true;
      try { await API.post(`/api/projects/${encodeURIComponent(project.id)}/html-review/tasks/${encodeURIComponent(task.id)}/cancel`, {}); }
      catch (error) {if (alive()) status.textContent = error.message;}
      finally {if (alive()) stop.disabled = false;}
    });
    generate.addEventListener('click', async () => {
      const needs = requirements.value.split('\n').map(v => v.trim()).filter(Boolean);
      if (!needs.length || needs.length > 4 || needs.some(n => n.length > 1000)) {status.textContent = '每行填写一个配图需求，共1至4个，每项不超过1000字。'; return;}
      busy(true);
      try {
        const columns = needs.length === 1 ? 1 : 2, rows = Math.ceil(needs.length / columns);
        const w = 1536 / columns, h = 1024 / rows;
        const method = background.value;
        const slots = needs.map((need, index) => ({id: `slot-${index+1}`, asset_id: `sheet-${Date.now()}-${index+1}`,
          role: '独立主体配图', need, rect: [index % columns*w, Math.floor(index/columns)*h, w, h], method,
          ...(method === 'boundary_color' ? {background: {rgb:[255,255,255], tolerance:16}} : {}),
          ...(method === 'source_alpha' && cleanup.checked ? {alpha_cleanup: {threshold:1, guard_radius:2, max_removed_fraction:0.02}} : {})}));
        const plan = {format:'hps.html.asset_sheet.plan', version:'0.1.0', id:'illustrations', width:1536, height:1024, direction:'V05', slots};
        const result = await API.post(`${base}/generate`, {plan});
        if (alive()) await poll(result.data.task);
      } catch (error) {if (alive()) status.textContent = error.message;}
      finally {if (alive()) busy(false);}
    });
    await load();
  }
  window.HtmlAssetSheets = {open, close() {epoch++;}};
}());
