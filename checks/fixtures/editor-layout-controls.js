// Synthetic fixture controls only; this script is never loaded by the application.
(function () {
  const url = '/api/projects/isolated/html-visual/condensation/editor';
  const controls = document.createElement('section'), result = document.createElement('pre');
  controls.setAttribute('aria-label', '隔离回归控制');
  controls.setAttribute('aria-busy', 'false');
  result.id = 'fixture-result'; result.style.maxHeight = '240px'; result.style.overflow = 'auto';
  async function report() {
    result.textContent = '读取中';
    const doc = await API.get(url);
    result.textContent = JSON.stringify({ revision: doc.revision, audio_revision: doc.audio_revision, version: doc.scene.version,
      nodes: doc.scene.nodes.map(n => ({ id: n.id, type: n.type, title: n.title, presentation: n.presentation,
        targetId: n.targetId, anchorId: n.anchorId, labelId: n.labelId, assetRef: n.assetRef })),
      motion: doc.scene.motion, initialVisibleIds: doc.scene.initialVisibleIds,
      binding: doc.binding, manual: doc.manual ? { protected_paths: doc.manual.protected_paths,
        last_origin: doc.manual.last_origin } : null }, null, 2);
  }
  for (const [name, action] of [
    ['读取服务端场景', report],
    ['延迟下一次预览', () => API.post('/fixture/delay-preview', {})],
    ['替换同长测试配音', () => API.post('/fixture/replace-audio', {})],
    ['模拟配音时序变化', () => API.post('/fixture/retime-audio', {})],
    ['模拟并发修改', async () => {
      const doc = await API.get(url);
      doc.scene.nodes.find(n => n.type === 'header').title = `并发演示版本 ${doc.revision}`;
      await API.put(url, { scene: doc.scene, binding: doc.binding, anchor_overrides: {}, expected_revision: doc.revision });
      await report();
    }],
    ['重开编辑器', () => HtmlSceneEditor.open(document.getElementById('host'), 'isolated', 'condensation')],
    ['关闭编辑器', () => { HtmlSceneEditor.close(); document.getElementById('host').replaceChildren(); }],
  ]) {
    const button = document.createElement('button'); button.textContent = name; button.type = 'button';
    button.onclick = async () => {
      controls.setAttribute('aria-busy', 'true');
      try { await action(); } catch (error) { result.textContent = error.message; }
      finally { controls.setAttribute('aria-busy', 'false'); }
    };
    controls.append(button);
  }
  controls.append(result); document.body.append(controls);
})();
