// Bounded overlap candidates. The original services own rendering, checks and save.
(function () {
  'use strict';
  if (window.HtmlLocalRepair) return;
  const goal = '仅调整所选对象的位置与尺寸，解决箭头穿过文字；保留文字、关系、样式、动画和人工保护字段。';
  const el = (tag, text = '', attributes = {}) => Object.assign(document.createElement(tag), {textContent: text, ...attributes});
  function mount(host, options) {
    const box = el('details'); box.dataset.localRepair = '';
    box.append(el('summary', '箭头与文字避让'), el('p', '先保存草稿，再选择1至4个文字或卡片对象。优先尝试几何避让；无可行候选时使用当前文字模型。只调整位置与尺寸。'));
    const generate = el('button', '生成避让候选', {type: 'button'});
    const save = el('button', '保存避让候选', {type: 'button', disabled: true});
    const discard = el('button', '放弃避让候选', {type: 'button', disabled: true});
    const status = el('p', '候选不会自动保存；检查通过也不代表审美批准。'); status.setAttribute('role', 'status');
    const content = el('div');
    const strategy=el('select');strategy.setAttribute('aria-label','修复策略');
    for(const [value,label] of [['geometry_first','箭头文字避让'],['layout_first','容量与关联布局（不调用模型）']])strategy.append(el('option',label,{value}));
    box.append(strategy, generate, save, discard, status, content); host.append(box);
    let dead = false, busy = false, candidate = null, signature = null;
    const current = () => !dead && box.isConnected && options.isCurrent();
    const stamp = ctx => JSON.stringify([ctx.projectId, ctx.slideId, ctx.doc.revision, ctx.doc.audio_revision, ctx.saved, ctx.doc.scene, ctx.doc.binding]);
    const url = ctx => `/api/projects/${encodeURIComponent(ctx.projectId)}/html-visual/${encodeURIComponent(ctx.slideId)}/repair`;
    function clear() { candidate = null; signature = null; content.replaceChildren(); save.disabled = true; discard.disabled = true; }
    function comparison(data) {
      const grid = el('div'); grid.className = 'html-local-repair-comparison';
      for (const [key, title] of [['before', '修改前'], ['after', '候选效果']]) {
        const column = el('section'); column.append(el('h4', title));
        const shots = data?.[key] || [];
        if (!shots.length) column.append(el('p', '本次未提供截图。'));
        for (const shot of shots) {
          if (typeof shot.image !== 'string' || !shot.image.startsWith('data:image/png;base64,')) continue;
          const figure = el('figure'), image = el('img', '', {src: shot.image, alt: `${title} ${shot.timeMs}毫秒`});
          figure.append(image, el('figcaption', `${shot.timeMs}毫秒（原播放器检查截图）`)); column.append(figure);
        }
        grid.append(column);
      }
      content.append(grid);
    }
    function show(result, ctx) {
      const path = result.repair_path || {};
      content.append(el('p', `来源：${['geometry','shared_layout_solver'].includes(path.origin) ? '几何试算（未调用模型）' : '模型修复'}；几何检查${path.geometry_attempts || 0}次，耗时${path.geometry_seconds ?? '—'}秒。`));
      if (path.fallback_reason) content.append(el('p', path.fallback_reason));
      content.append(el('p', `范围：${ctx.scope.join('、')}；基于页面修订 ${ctx.doc.revision}。`));
      const review = result.review;
      if (review) content.append(el('p', `整页检查：${review.passed ? '通过' : '未通过'}；${review.frame_count ?? '—'}个检查时刻；${review.issues?.length ?? 0}项问题。`));
      for(const issue of review?.diagnostics?.issues || []) content.append(el('p',`${issue.targets.join('、')||'整页'} · ${issue.code}：${issue.action_label}`));
      const names = {offsetX: '水平偏移', offsetY: '垂直偏移', width: '宽度', height: '高度'};
      const list = el('ul');
      for (const change of result.changes || []) list.append(el('li', change.kind
        ? `${change.targetId} · ${change.kind}：${JSON.stringify(change.values)}`
        : `${change.targetId} · ${names[change.parameter] || change.parameter}：${change.before ?? '自动（槽位）'} → ${change.after}px`));
      content.append(list); comparison(result.comparison);
      if (result.candidate_key && result.request && review?.passed === true) {
        candidate = result; signature = stamp(ctx); save.disabled = false; discard.disabled = false;
        status.textContent = '候选检查通过，尚未保存。请核对截图和参数，再点击保存避让候选。';
      } else status.textContent = result.message || '没有可保存的候选，原页面未修改。';
    }
    async function run(action) {
      if (!current() || busy || !options.canStart()) return;
      busy = true; options.setBusy(true);
      try { await action(); }
      catch (error) {
        if (current()) { clear(); status.textContent = `操作未完成：${error.message}。候选已清除；请先核对页面状态。请求超时不代表服务器已取消，请勿连续重试。`; }
      } finally {
        busy = false;
        if (current()) options.setBusy(false);
      }
    }
    generate.onclick = () => run(async () => {
      clear(); const ctx = options.getContext();
      if (!ctx.saved || ctx.scope.length < 1 || ctx.scope.length > 4) {
        status.textContent = '请先保存草稿，并选择1至4个对象。'; return;
      }
      const before = stamp(ctx);
      status.textContent = '正在试算并检查整页；无可行几何候选时将继续模型修复，可能需要数分钟。原页面尚未保存修改。';
      const result = await API.post(`${url(ctx)}/generate`, {
        expected_revision: ctx.doc.revision, expected_audio_revision: ctx.doc.audio_revision,
        scope: ctx.scope, instruction: strategy.value==='layout_first'?'仅修复所选对象的容量、遮挡和关联布局；保留原文、关系、动作与人工保护。':goal, strategy: strategy.value,
        overlap_policy: 'registered', sampling_mode: 'output_frames', fps: 30,
      }, {timeoutMs: 1200000, silent: true});
      if (!current()) return;
      if (before !== stamp(options.getContext())) { clear(); status.textContent = '页面已变化，候选已丢弃，请基于当前页面重新生成。'; return; }
      show(result, ctx);
    });
    save.onclick = () => run(async () => {
      const ctx = options.getContext();
      if (!candidate || signature !== stamp(ctx)) { clear(); status.textContent = '页面或配音已变化，请重新生成候选。'; return; }
      const result = await API.post(`${url(ctx)}/save`, {...candidate.request, candidate_key: candidate.candidate_key}, {timeoutMs: 180000, silent: true});
      if (!current()) return;
      clear(); status.textContent = '避让候选已保存，可通过读取保存版本预览恢复。';
      if (result.changed) await options.onSaved();
    });
    discard.onclick = () => { if (!busy) { clear(); status.textContent = '候选已放弃，原页面未修改。'; } };
    return {destroy() { dead = true; clear(); box.remove(); }};
  }
  window.HtmlLocalRepair = {mount};
})();
