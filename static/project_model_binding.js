/* HTML project settings. Explicit mount; shared transport; no DOM observers. */
(function () {
  'use strict';
  let epoch = 0;
  function node(tag, text, className) {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  function summaryText(summary) {
    const sources = {global: '系统设置', creation_config: '创作包', fixed: '项目固定'};
    return `当前：${summary.provider} / ${summary.model || '未配置'} · 来源 ${sources[summary.source] || summary.source}${summary.ready ? '' : ' · ' + summary.error}`;
  }
  async function mount(container, project) {
    const ticket = ++epoch;
    container.replaceChildren();
    if (!project || project.visual_backend !== 'html') return;
    const panel = node('section', '', 'project-model-binding');
    container.append(panel);
    panel.append(node('h3', '项目生成模型'));
    panel.append(node('p', '继承会跟随系统设置；固定绑定保留选定配置。修改仅影响后续生成，已启动任务保持原配置。'));
    const status = node('p', '正在读取模型配置…');
    status.setAttribute('role', 'status');
    panel.append(status);
    const url = `/api/projects/${encodeURIComponent(project.id)}/model-binding`;
    let config, connections;
    try {
      [config, connections] = await Promise.all([API.get(url), API.get('/api/model-connections')]);
    } catch (err) { if (ticket === epoch) status.textContent = err.message; return; }
    if (ticket !== epoch) return;
    const controls = {};
    for (const kind of ['text', 'image']) {
      const group = node('fieldset');
      group.append(node('legend', kind === 'text' ? '文字模型' : '图片模型'));
      const select = node('select');
      select.setAttribute('aria-label', kind === 'text' ? '文字模型来源' : '图片模型来源');
      const add = (value, label) => { const option = node('option', label); option.value = value; select.append(option); };
      const binding = config.bindings[kind];
      add('legacy', '沿用创作包 / 系统设置');
      add('inherit', '继承系统设置');
      for (const item of connections.connections.filter(item => item.kind === kind && item.state === 'active')) {
        add(item.id, `固定：${item.name} · ${item.revision.model}`);
      }
      if (binding.mode === 'fixed' && !Array.from(select.options).some(item => item.value === binding.connection_id)) {
        add(binding.connection_id, `固定：${config.effective[kind].model}（保留的连接）`);
      }
      select.value = binding.mode === 'fixed' ? binding.connection_id : binding.mode;
      const summary = config.effective[kind];
      const summaryNode = node('p', summaryText(summary));
      group.append(select, summaryNode);
      const label = node('label');
      const rebind = node('input'); rebind.type = 'checkbox';
      rebind.setAttribute('aria-label', kind === 'text' ? '重新固定文字模型' : '重新固定图片模型');
      label.append(rebind, document.createTextNode('重新固定为该连接的当前配置'));
      group.append(label); panel.append(group);
      controls[kind] = {select, rebind, summaryNode};
    }
    const save = node('button', '保存模型配置', 'btn btn-primary'); save.type = 'button';
    const reload = node('button', '重新读取配置', 'btn'); reload.type = 'button';
    reload.addEventListener('click', () => mount(container, project));
    save.addEventListener('click', async () => {
      const payload = {expected_revision: config.revision};
      for (const kind of ['text', 'image']) {
        const {select, rebind} = controls[kind];
        payload[kind] = ['inherit', 'legacy'].includes(select.value) ? {mode: select.value} : {mode: 'fixed', connection_id: select.value, rebind: rebind.checked};
      }
      save.disabled = true;
      for (const control of Object.values(controls)) {control.select.disabled = true; control.rebind.disabled = true;}
      try {
        const result = await API.put(url, payload);
        if (ticket !== epoch) return;
        config.revision = result.revision;
        for (const control of Object.values(controls)) control.rebind.checked = false;
        status.textContent = result.changed ? '已保存，将用于后续生成。' : '配置未变化。';
        try {
          const latest = await API.get(url);
          if (ticket !== epoch) return;
          for (const kind of ['text', 'image']) controls[kind].summaryNode.textContent = summaryText(latest.effective[kind]);
        } catch (_) {
          if (ticket === epoch) status.textContent = '配置已保存，摘要读取失败，请重新读取配置。';
        }
      } catch (err) {
        if (ticket === epoch) status.textContent = err.status === 409 ? '配置已被其他操作修改。本地选择已保留，请记录选择后重新读取配置。' : err.message;
      } finally { if (ticket === epoch) {
        save.disabled = false;
        for (const control of Object.values(controls)) {control.select.disabled = false; control.rebind.disabled = false;}
      } }
    });
    panel.append(save, reload);
    status.textContent = '本页不显示或保存明文凭据。';
  }
  window.ProjectModelBinding = {mount};
}());
