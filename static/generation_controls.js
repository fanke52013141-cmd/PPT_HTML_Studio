// Shared safe-stop controls for source-owned generation workflows.
// Job persistence and artifact publication remain owned by backend services.
function initGenerationControls() {
  if (initGenerationControls.started) return;
  initGenerationControls.started = true;
  const stages = [
    [2, 'storyboard_script', '演讲稿生成'], [2, 'storyboard_visual', '内容可视化'],
    [5, 'mask', 'AI Mask 标注'], [6, 'tts', '音频生成'], [8, 'video', '视频渲染'],
  ];
  const controls = stages.map(([step, kind, label]) => {
    const panel = document.getElementById(`step-panel-${step}`);
    const box = document.createElement('div');
    box.className = 'workspace-operation-status generation-control';
    box.hidden = true;
    const text = document.createElement('span');
    text.setAttribute('role', 'status');
    const stop = document.createElement('button');
    stop.type = 'button';
    stop.className = 'secondary';
    stop.textContent = '请求停止';
    box.append(text, stop);
    panel?.appendChild(box);
    const item = { panel, kind, label, box, text, stop, operationId: null, projectId: null, pending: false };
    stop.addEventListener('click', async () => {
      if (!item.operationId || item.pending) return;
      const projectId = item.projectId;
      const operationId = item.operationId;
      item.pending = true;
      stop.disabled = true;
      try {
        const result = await API.post(`/api/projects/${projectId}/generation-control/${kind}/stop`, { operation_id: operationId });
        if (item.projectId !== projectId || item.operationId !== operationId) return;
        text.textContent = result.message;
      } catch (error) {
        if (item.projectId === projectId) text.textContent = `请求停止失败：${error.message}。正在重新读取任务状态。`;
      } finally {
        item.pending = false;
      }
    });
    return item;
  });
  let polling = false;
  async function poll() {
    if (polling) return;
    polling = true;
    const projectId = state.currentProject?.id;
    try {
      await Promise.all(controls.map(async item => {
        if (!projectId || !document.body.classList.contains('workspace-open') || !item.panel?.getClientRects().length) {
          item.box.hidden = true;
          return;
        }
        try {
          const result = await API.get(`/api/projects/${projectId}/generation-control/${item.kind}`, { silent: true });
          if (state.currentProject?.id !== projectId) return;
          item.projectId = projectId;
          const wasActive = !!item.operationId;
          item.operationId = result.operation_id;
          if (wasActive && !result.active) document.dispatchEvent(new CustomEvent('generation-finished', { detail: { projectId, kind: item.kind } }));
          item.box.hidden = !result.active;
          item.stop.disabled = item.pending || result.stop_requested;
          item.stop.textContent = result.stop_requested ? '正在停止…' : '请求停止';
          item.text.textContent = result.stop_requested
            ? `${item.label}：已请求停止，当前请求或阶段安全结束后停止。`
            : `${item.label}正在执行。可切换步骤后返回查看；请保持本地服务运行。停止会等待当前请求或阶段结束。`;
        } catch (_) {
          if (item.projectId === projectId && !item.box.hidden) item.text.textContent = '暂时无法读取任务状态，正在重试；请勿重复提交任务。';
        }
      }));
    } finally { polling = false; }
  }
  setInterval(poll, 2000);
  poll();
}
