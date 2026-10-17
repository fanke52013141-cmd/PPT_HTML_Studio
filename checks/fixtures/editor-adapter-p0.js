'use strict';
(async function () {
  const $ = id => document.getElementById(id), frame = $('frame');
  const url = '/api/projects/isolated/html-visual/condensation/editor';
  let doc, resolved, canvas, timeline, disposed = false, busy = false;
  const undo = [], redo = [], operations = [];
  const status = text => { $('status').textContent = text; };
  async function api(method, endpoint, body) {
    const response = await fetch(endpoint, { method, headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined });
    const result = await response.json();
    if (!response.ok) throw Error(`${response.status}: ${result.detail}`);
    return result;
  }
  const player = () => frame.contentWindow.visualPlayer;
  const payload = () => ({ scene: doc.scene, binding: doc.binding, anchor_overrides: doc.anchor_overrides,
    expected_revision: doc.revision });
  function facts() {
    $('facts').textContent = JSON.stringify({ revision: doc.revision, undo: undo.length, redo: redo.length,
      operations, header: doc.scene.nodes.find(n => n.id === 'header').presentation,
      presentations: Object.fromEntries(doc.scene.nodes.filter(n => n.presentation).map(n => [n.id, n.presentation])),
      binding: doc.binding?.actions['header:enter'], action: doc.scene.motion[0],
      clock: 'original visualPlayer; no timeline playback', disposed }, null, 2);
  }
  function destroyCanvas() { canvas?.destroy(); canvas = null; }
  function timelineRows() {
    const action = resolved.scene.motion.find(a => a.targetId === 'header' && a.type === 'enter');
    return [{ id: 'beat', actions: [{ id: '语块 b1（只读）', start: 0, end: 6,
      effectId: 'none', movable: false, flexible: false, disable: true }] },
      { id: 'header', actions: [{ id: 'header:enter', start: action.startMs / 1000,
        end: (action.startMs + action.durationMs) / 1000, effectId: 'none', minStart: 0, maxEnd: 6 }] }];
  }
  async function render() {
    destroyCanvas();
    resolved = await api('POST', `${url}/preview`, payload());
    if (!await player().apply(resolved.scene, resolved.resources))
      throw Error(frame.contentDocument.getElementById('status').textContent);
    player().seek(resolved.scene.durationMs);
    timeline?.update(timelineRows());
    timeline?.setTime(player().timeMs);
    facts();
  }
  async function transaction(mutate) {
    if (busy || disposed) return;
    busy = true;
    const before = structuredClone(doc);
    try {
      mutate(); await render(); undo.push(before); redo.length = 0;
      status('本地预览通过；一个撤销事务，尚未保存'); facts();
    } catch (error) {
      doc = before; await render(); throw error;
    } finally { busy = false; }
  }
  function layout() {
    destroyCanvas();
    player().pause(); player().seek(resolved.scene.durationMs);
    const stage = frame.contentDocument.querySelector('.visual-stage');
    const definition = frame.contentWindow.VisualData.catalog.layouts.find(l => l.id === doc.scene.layoutRef.id);
    canvas = frame.contentWindow.HtmlEditorUI.mountCanvas({ stage, nodes: doc.scene.nodes,
      authorSize: definition.canvas, onSelect: ids => status(`选中：${ids.join('、') || '无'}；多选仅验证选择`),
      onError: error => status(error.message),
      onCommit: async batch => {
        await transaction(() => {
          doc.scene = HtmlEditorUI.applyPresentationOperations(doc.scene, batch);
        });
        operations.push(...batch); layout(); facts();
      } });
    status('布局编辑：点击后拖动；右侧/底部手柄调整尺寸；Shift 多选仅验证选择');
  }
  function mountTimeline() {
    timeline?.destroy();
    timeline = HtmlEditorUI.mountTimeline($('timeline'), { rows: timelineRows(),
      onSelect: id => status(`动作 ${id}`),
      onSeek: ms => {
        destroyCanvas(); player().pause();
        player().seek(Math.max(0, Math.min(resolved.scene.durationMs, ms)));
        timeline.setTime(player().timeMs); status(`原播放器跳转 ${player().timeMs}ms`);
      },
      onEdit: async ({ action, start, end }) => {
        try {
          const effective = resolved.scene.motion.find(a => a.targetId === 'header' && a.type === 'enter');
          const original = doc.scene.motion.find(a => a.targetId === 'header' && a.type === 'enter');
          const patch = HtmlEditorUI.bindingEdit({ action: original, binding: doc.binding.actions[action.id],
            window: { beatId: 'b1', startMs: 0, endMs: 6000 }, effectiveStartMs: effective.startMs,
            startMs: Math.round(start * 1000), endMs: Math.round(end * 1000) });
          await transaction(() => {
            Object.assign(original, patch.action); doc.binding.actions[action.id] = patch.binding;
          });
        } catch (error) { timeline.update(timelineRows()); status(error.message); }
      } });
  }
  async function load() {
    doc = await api('GET', url);
    // Synthetic explicit binding for the existing fixture action. Never production inference.
    doc.binding ||= { format: 'hps.html.motion_binding', version: '0.1.0', mode: 'beat_ids',
      actions: { 'header:enter': { beatId: 'b1', edge: 'start', offsetMs: 0 } } };
    undo.length = redo.length = 0; await render(); mountTimeline(); status(`已读取修订 ${doc.revision}`);
  }
  function command(id, fn) { $(id).onclick = async () => {
    if (busy || disposed) return;
    busy = true;
    try { await fn(); } catch (error) { status(error.message); }
    finally { busy = false; }
  }; }
  frame.srcdoc = `<!doctype html><meta charset="utf-8"><style>body{margin:0}#viewport{width:100%}.runtime-controls{display:none}</style><div id="viewport"></div><div class="runtime-controls"><select id="scene"></select><select id="theme"></select><textarea id="definition"></textarea><button id="apply"></button><button id="play"></button><button id="end"></button><input id="seek"><span id="time"></span><input id="font" value="32"><span id="font-value"></span><input type="checkbox" id="reduced"><p id="status"></p></div><script src="/api/html-scene-editor/runtime/data.js"></script><script src="/api/html-scene-editor/runtime/player.js"></script><script src="/static/editor_ui/editor.js"></script>`;
  await new Promise(resolve => { frame.onload = resolve; });
  await load();
  command('layout', layout);
  for (const [id, from, to] of [['undo', undo, redo], ['redo', redo, undo]]) command(id, async () => {
    if (!from.length) return;
    const before = structuredClone(doc), candidate = from.at(-1);
    doc = structuredClone(candidate);
    try { await render(); from.pop(); to.push(before); facts(); status('撤销/重做已重渲染'); }
    catch (error) { doc = before; await render(); throw error; }
  });
  command('save', async () => { await render(); const result = await api('PUT', url, payload());
    await load(); status(`已保存，修订 ${result.revision}`); });
  command('reload', load);
  command('play', () => { destroyCanvas(); player().playing ? player().pause() : player().play(); });
  command('dispose', () => { clearInterval(poll); destroyCanvas(); timeline.destroy(); player().pause(); disposed = true; facts(); status('组件已销毁；刷新可重新开始'); });
  $('zoom').onchange = () => { frame.style.width = `${1600 * Number($('zoom').value)}px`;
    frame.style.height = `${900 * Number($('zoom').value) + 20}px`; };
  // Observe the existing clock; this callback never advances or plays either engine.
  const poll = setInterval(() => { if (!disposed) timeline?.setTime(player().timeMs); }, 100);
  window.addEventListener('pagehide', () => { clearInterval(poll); destroyCanvas(); timeline?.destroy(); player().pause(); });
})().catch(error => { document.getElementById('status').textContent = error.message; });
