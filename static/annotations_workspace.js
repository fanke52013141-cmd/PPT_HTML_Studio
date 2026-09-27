// 勾画标注工作区(可见步骤 10):项目/页面生命周期、三栏渲染、选中联动、
// 自动保存与冲突处理。纯逻辑在 annotations_core.js;画布交互与属性编辑在
// annotations_editor.js;本模块不实现业务算法,只做编排与渲染。

const ANNOTATIONS_WS = {
  projectId: '',
  slideIds: [],
  activeIndex: 0,
  summary: null,
  settingsRevision: 0,
  page: { slide_id: '', revision: 0, items: [] },
  pendingOps: [],
  saveTimer: null,
  saveInFlight: false,
  saveGeneration: 0,
  histories: {},
  selectedAnnotationId: null,
  loading: false,
};

function annotationsApiBase(projectId = ANNOTATIONS_WS.projectId) {
  return `/api/projects/${projectId}/annotations`;
}

// ------------------------------------------------------------ 项目生命周期

function resetAnnotationsProjectState() {
  ++ANNOTATIONS_WS.saveGeneration;
  clearTimeout(ANNOTATIONS_WS.saveTimer);
  ANNOTATIONS_WS.saveTimer = null;
  ANNOTATIONS_WS.pendingOps = [];
  ANNOTATIONS_WS.saveInFlight = false;
  ANNOTATIONS_WS.histories = {};
  ANNOTATIONS_WS.projectId = '';
  ANNOTATIONS_WS.slideIds = [];
  ANNOTATIONS_WS.summary = null;
  ANNOTATIONS_WS.page = { slide_id: '', revision: 0, items: [] };
  ANNOTATIONS_WS.selectedAnnotationId = null;
  window.__annotationsEnabled = false;
  renderAnnotationSaveStatus('idle');
}

async function flushAnnotationsSave() {
  if (!ANNOTATIONS_WS.projectId || !ANNOTATIONS_WS.page.slide_id) return;
  if (ANNOTATIONS_WS.saveInFlight || !ANNOTATIONS_WS.pendingOps.length) {
    return;
  }
  clearTimeout(ANNOTATIONS_WS.saveTimer);
  ANNOTATIONS_WS.saveTimer = null;
  const generation = ++ANNOTATIONS_WS.saveGeneration;
  const operations = ANNOTATIONS_WS.pendingOps;
  ANNOTATIONS_WS.pendingOps = [];
  const slideId = ANNOTATIONS_WS.page.slide_id;
  const expectedRevision = ANNOTATIONS_WS.page.revision;
  ANNOTATIONS_WS.saveInFlight = true;
  renderAnnotationSaveStatus('saving');
  try {
    const res = await API.patch(
      `${annotationsApiBase()}/slides/${encodeURIComponent(slideId)}`,
      { expected_revision: expectedRevision, operations },
      { silent: true }
    );
    if (generation !== ANNOTATIONS_WS.saveGeneration || ANNOTATIONS_WS.page.slide_id !== slideId) return;
    ANNOTATIONS_WS.page.revision = res.revision;
    ANNOTATIONS_WS.page.items = res.items;
    ANNOTATIONS_WS.saveInFlight = false;
    renderAnnotationSaveStatus('saved');
    // 服务端条目已替换本地临时 id;选中态失效时就近改选最后一项,
    // 并同步刷新属性编辑器与讲稿高亮
    const selectionMissing = !(res.items || []).some(entry => entry.annotation_id === ANNOTATIONS_WS.selectedAnnotationId);
    if (selectionMissing) {
      ANNOTATIONS_WS.selectedAnnotationId = (res.items || []).length
        ? res.items[res.items.length - 1].annotation_id
        : null;
    }
    renderAnnotationItems();
    renderAnnotationOverlay();
    renderAnnotationNarrationHighlights();
    if (typeof renderAnnotationItemEditor === 'function') renderAnnotationItemEditor();
    refreshAnnotationsStepFlag();
    return;
  } catch (error) {
    ANNOTATIONS_WS.saveInFlight = false;
    // 失败保留本地编辑并把操作放回队首,供重试或重载后合并
    ANNOTATIONS_WS.pendingOps = [...operations, ...ANNOTATIONS_WS.pendingOps];
    const failure = AnnotationsCore.classifyPatchFailure(error.status, error.body);
    if (failure.kind === 'revision_conflict') {
      renderAnnotationSaveStatus('conflict', failure.message);
      showToast(failure.message);
    } else if (failure.kind === 'validation_failed') {
      renderAnnotationSaveStatus('invalid');
      const first = failure.issues?.[0];
      showToast(first ? `保存被拒绝:${first.path} ${first.message}` : failure.message);
    } else {
      renderAnnotationSaveStatus('error', failure.message);
      showToast(failure.message);
    }
    throw error;
  } finally {
    if (generation === ANNOTATIONS_WS.saveGeneration) {
      ANNOTATIONS_WS.saveInFlight = false;
    }
  }
}

function queueAnnotationSave(operationOrList) {
  const operations = Array.isArray(operationOrList) ? operationOrList : [operationOrList];
  if (!operations.length) return;
  ANNOTATIONS_WS.pendingOps.push(...operations.filter(Boolean));
  renderAnnotationSaveStatus('pending');
  clearTimeout(ANNOTATIONS_WS.saveTimer);
  ANNOTATIONS_WS.saveTimer = setTimeout(() => {
    flushAnnotationsSave().catch(() => {});
  }, 700);
}

// ------------------------------------------------------------ 数据加载

async function loadStep10Data() {
  const projectId = state.currentProject?.id;
  if (!projectId) return;
  resetAnnotationsProjectState();
  ANNOTATIONS_WS.projectId = projectId;
  ANNOTATIONS_WS.loading = true;
  try {
    await reloadAnnotationsSummary();
    if (ANNOTATIONS_WS.slideIds.length) {
      await selectAnnotationPage(0);
    }
  } finally {
    ANNOTATIONS_WS.loading = false;
  }
}

async function reloadAnnotationsSummary() {
  const summary = await API.get(annotationsApiBase());
  ANNOTATIONS_WS.summary = summary;
  ANNOTATIONS_WS.settingsRevision = summary?.settings?.revision || 0;
  ANNOTATIONS_WS.slideIds = (summary?.slides || []).map(item => item.slide_id);
  const enabledToggle = document.getElementById('annotation-enabled-toggle');
  if (enabledToggle) enabledToggle.checked = summary?.settings?.enabled === true;
  refreshAnnotationsStepFlag();
}

function refreshAnnotationsStepFlag() {
  const enabled = ANNOTATIONS_WS.summary?.settings?.enabled === true;
  const moduleState = ANNOTATIONS_WS.summary?.module_state || 'not_started';
  const changed = window.__annotationsEnabled !== enabled || window.__annotationModuleState !== moduleState;
  window.__annotationsEnabled = enabled;
  window.__annotationModuleState = moduleState;
  if (changed && state.currentProject && typeof updateStepperUI === 'function') {
    updateStepperUI(state.currentStep, state.currentProject.step_status || {});
  }
}

function refreshAnnotationModuleState() {
  refreshAnnotationsStepFlag();
}

async function setAnnotationDecision(decision) {
  const projectId = ANNOTATIONS_WS.projectId;
  if (!projectId) return;
  try {
    const res = await API.put(`${annotationsApiBase()}/settings`, {
      expected_revision: ANNOTATIONS_WS.settingsRevision,
      enabled: ANNOTATIONS_WS.summary?.settings?.enabled === true,
      decision,
    }, { silent: true });
    ANNOTATIONS_WS.settingsRevision = res.revision;
    if (ANNOTATIONS_WS.summary?.settings) {
      ANNOTATIONS_WS.summary.settings.decision = res.decision;
      ANNOTATIONS_WS.summary.settings.revision = res.revision;
    }
    refreshAnnotationModuleState();
    showToast(decision === 'no_annotations' ? '已记录:本项目不添加勾画。' : '已恢复勾画决策。');
  } catch (error) {
    showToast(error.message || '决策保存失败');
  }
}

async function selectAnnotationPage(index) {
  await flushAnnotationsSave().catch(() => {});
  const slideId = ANNOTATIONS_WS.slideIds[index];
  if (!slideId) return;
  ANNOTATIONS_WS.activeIndex = index;
  ANNOTATIONS_WS.selectedAnnotationId = null;
  const page = await API.get(`${annotationsApiBase()}/slides/${encodeURIComponent(slideId)}`);
  ANNOTATIONS_WS.page = {
    slide_id: slideId,
    revision: page.revision || 0,
    items: page.items || [],
    narration: page.narration || { beats: [] },
    imageHash: page.image?.hash || null,
    aiSnapshot: page.ai_suggestion_snapshot || null,
  };
  if (!ANNOTATIONS_WS.histories[slideId]) {
    ANNOTATIONS_WS.histories[slideId] = AnnotationsCore.createPageHistory();
  }
  renderAnnotationWorkspace();
  await loadAnnotationCandidates();
}

// ------------------------------------------------------------ 渲染

function renderAnnotationWorkspace() {
  renderAnnotationMissingState();
  if (annotationPrerequisitesBlocked()) return;
  renderAnnotationThumbnails();
  renderAnnotationNarration();
  renderAnnotationItems();
  renderAnnotationOverlay();
  renderAnnotationItemEditor();
}

function annotationPrerequisitesBlocked() {
  const page = ANNOTATIONS_WS.page;
  return !page.imageHash || !(page.narration?.beats?.length);
}

function renderAnnotationMissingState() {
  const missing = document.getElementById('annotation-missing-state');
  const body = document.getElementById('annotation-workspace-body');
  if (!missing || !body) return;
  const blocked = annotationPrerequisitesBlocked();
  missing.style.display = blocked ? 'block' : 'none';
  body.style.display = blocked ? 'none' : 'block';
  if (!blocked) return;
  const reasons = [];
  if (!ANNOTATIONS_WS.page.imageHash) reasons.push('当前页面还没有图片');
  if (!(ANNOTATIONS_WS.page.narration?.beats?.length)) reasons.push('当前页面还没有有效讲稿');
  const reason = document.getElementById('annotation-missing-reason');
  if (reason) reason.textContent = `${reasons.join(';')}。补齐后即可编辑勾画。`;
}

function renderAnnotationThumbnails() {
  const strip = document.getElementById('annotation-thumb-strip');
  if (!strip) return;
  strip.innerHTML = '';
  const summaryBySlide = new Map((ANNOTATIONS_WS.summary?.slides || []).map(item => [item.slide_id, item]));
  ANNOTATIONS_WS.slideIds.forEach((slideId, index) => {
    const counts = summaryBySlide.get(slideId)?.counts || { total: 0 };
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `annotation-thumb${index === ANNOTATIONS_WS.activeIndex ? ' active' : ''}`;
    item.dataset.slideId = slideId;
    const img = document.createElement('img');
    img.src = `/api/projects/${ANNOTATIONS_WS.projectId}/slides/${encodeURIComponent(slideId)}/image`;
    img.alt = slideId;
    const badge = document.createElement('span');
    badge.className = 'annotation-thumb-badge';
    badge.textContent = counts.total ? String(counts.total) : '';
    item.appendChild(img);
    item.appendChild(badge);
    item.addEventListener('click', () => {
      if (index !== ANNOTATIONS_WS.activeIndex) {
        selectAnnotationPage(index).catch(() => showToast('页面加载失败,请重试。'));
      }
    });
    strip.appendChild(item);
  });
}

function annotationNarrationBeatHtml(beat) {
  const spoken = String(beat.spoken_text || '');
  return `<div class="annotation-beat" data-beat-id="${escHtml(beat.beat_id || '')}" data-spoken="${escHtml(spoken)}">
    <div class="annotation-beat-text">${escHtml(spoken)}</div>
  </div>`;
}

function renderAnnotationNarration() {
  const container = document.getElementById('annotation-narration-beats');
  if (!container) return;
  const beats = ANNOTATIONS_WS.page.narration?.beats || [];
  container.innerHTML = beats.map(annotationNarrationBeatHtml).join('');
  container.querySelectorAll('.annotation-beat').forEach(node => {
    node.addEventListener('mouseup', handleAnnotationNarrationSelection);
  });
  renderAnnotationNarrationHighlights();
}

function renderAnnotationNarrationHighlights() {
  const container = document.getElementById('annotation-narration-beats');
  if (!container) return;
  const beats = ANNOTATIONS_WS.page.narration?.beats || [];
  const items = ANNOTATIONS_WS.page.items || [];
  container.querySelectorAll('.annotation-beat').forEach(node => {
    const beat = beats.find(entry => entry.beat_id === node.dataset.beatId);
    if (!beat) return;
    const spoken = String(beat.spoken_text || '');
    const marks = [];
    for (let i = 0; i < spoken.length; i += 1) {
      marks.push(null);
    }
    items.forEach((item, itemIndex) => {
      const anchor = item.anchor;
      if (!anchor || anchor.beat_id !== beat.beat_id) return;
      const utf16Start = AnnotationsCore.codepointIndexToUtf16Index(spoken, anchor.range?.[0] ?? 0);
      const utf16End = AnnotationsCore.codepointIndexToUtf16Index(spoken, anchor.range?.[1] ?? 0);
      for (let i = utf16Start; i < utf16End && i < marks.length; i += 1) {
        marks[i] = itemIndex;
      }
    });
    let html = '';
    let index = 0;
    while (index < marks.length) {
      const owner = marks[index];
      if (owner === null) {
        let end = index;
        while (end < marks.length && marks[end] === null) end += 1;
        html += escHtml(spoken.slice(index, end));
        index = end;
      } else {
        let end = index;
        while (end < marks.length && marks[end] === owner) end += 1;
        const selected = ANNOTATIONS_WS.selectedAnnotationId === items[owner].annotation_id;
        html += `<mark class="annotation-anchor-mark${selected ? ' selected' : ''}" data-owner="${escHtml(items[owner].annotation_id)}">${escHtml(spoken.slice(index, end))}</mark>`;
        index = end;
      }
    }
    node.querySelector('.annotation-beat-text').innerHTML = html || '<span class="annotation-beat-empty">(空语块)</span>';
  });
  container.querySelectorAll('.annotation-anchor-mark').forEach(mark => {
    mark.addEventListener('click', () => {
      selectAnnotationItem(mark.dataset.owner);
    });
  });
}

function handleAnnotationNarrationSelection(event) {
  const selection = window.getSelection();
  const node = event.currentTarget;
  const spoken = node.dataset.spoken || '';
  if (!selection || !selection.rangeCount || !spoken) return;
  const text = selection.toString();
  if (!text.trim()) return;
  const range = selection.getRangeAt(0);
  const measure = document.createElement('span');
  const host = node.querySelector('.annotation-beat-text');
  if (!host || !host.contains(range.commonAncestorContainer)) return;
  measure.innerHTML = '&nbsp;';
  const probeStart = document.createRange();
  probeStart.selectNodeContents(host);
  probeStart.setEnd(range.startContainer, range.startOffset);
  const utf16Start = probeStart.toString().length;
  const utf16End = utf16Start + text.length;
  const anchor = AnnotationsCore.buildAnchor(node.dataset.beatId, spoken, utf16Start, utf16End);
  if (typeof window.annotationNarrationAnchorPicked === 'function') {
    window.annotationNarrationAnchorPicked(anchor);
  }
}

function annotationStatusChips(item) {
  const labels = AnnotationsCore.STATUS_LABELS;
  return `<span class="annotation-chip content-${escHtml(item.status?.content || 'draft')}">${escHtml(labels.content[item.status?.content] || '未知')}</span>
    <span class="annotation-chip spatial-${escHtml(item.status?.spatial || 'valid')}">${escHtml(labels.spatial[item.status?.spatial] || '')}</span>
    <span class="annotation-chip temporal-${escHtml(item.status?.temporal || 'awaiting_audio')}">${escHtml(labels.temporal[item.status?.temporal] || '')}</span>`;
}

function renderAnnotationItems() {
  const container = document.getElementById('annotation-items');
  if (!container) return;
  const items = ANNOTATIONS_WS.page.items || [];
  if (!items.length) {
    container.innerHTML = '<div class="annotation-items-empty">暂无标注。在画布上框选区域,或在讲稿中选中短语后点击"关联讲稿"。</div>';
    return;
  }
  container.innerHTML = items.map((item, index) => {
    const selected = item.annotation_id === ANNOTATIONS_WS.selectedAnnotationId;
    const quote = item.anchor?.quote || '(未关联讲稿)';
    const lockBadge = item.protection?.locked ? '<span class="annotation-chip locked">🔒 已锁定</span>' : '';
    const disabledBadge = item.status?.content === 'disabled' ? '<span class="annotation-chip disabled-chip">已禁用</span>' : '';
    return `<div class="annotation-card${selected ? ' selected' : ''}${item.status?.content === 'disabled' ? ' is-disabled' : ''}"
        data-annotation-id="${escHtml(item.annotation_id)}" tabindex="0" role="button">
      <div class="annotation-card-title">${escHtml(AnnotationsCore.annotationCardLabel(item, index))}${lockBadge}${disabledBadge}</div>
      <div class="annotation-card-quote">"${escHtml(quote)}"</div>
      <div class="annotation-card-status">${annotationStatusChips(item)}</div>
    </div>`;
  }).join('');
  container.querySelectorAll('.annotation-card').forEach(card => {
    card.addEventListener('click', () => selectAnnotationItem(card.dataset.annotationId));
    card.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectAnnotationItem(card.dataset.annotationId);
      }
    });
  });
}

function selectAnnotationItem(annotationId) {
  ANNOTATIONS_WS.selectedAnnotationId = annotationId;
  renderAnnotationItems();
  renderAnnotationOverlay();
  renderAnnotationNarrationHighlights();
  renderAnnotationItemEditor();
  if (typeof window.annotationSelectionChanged === 'function') {
    window.annotationSelectionChanged(annotationId);
  }
}

function renderAnnotationSaveStatus(mode, message = '') {
  const node = document.getElementById('annotation-save-status');
  if (!node) return;
  const map = {
    idle: '',
    pending: '待保存…',
    saving: '保存中…',
    saved: '已保存',
    conflict: '版本冲突,待处理',
    invalid: '内容被拒绝,待修改',
    error: '保存失败,待重试',
  };
  node.dataset.state = mode;
  node.textContent = message || map[mode] || '';
  node.style.display = mode === 'idle' ? 'none' : 'inline-block';
}

// ------------------------------------------------------------ 设置开关

async function setAnnotationsEnabled(enabled) {
  const projectId = ANNOTATIONS_WS.projectId;
  if (!projectId) return;
  try {
    const res = await API.put(`${annotationsApiBase()}/settings`, {
      expected_revision: ANNOTATIONS_WS.settingsRevision,
      enabled: enabled === true,
    }, { silent: true });
    ANNOTATIONS_WS.settingsRevision = res.revision;
    if (ANNOTATIONS_WS.summary?.settings) {
      ANNOTATIONS_WS.summary.settings.enabled = res.enabled;
      ANNOTATIONS_WS.summary.settings.revision = res.revision;
    }
    refreshAnnotationsStepFlag();
    showToast(enabled ? '已在视频中启用勾画;导出前需逐页确认标注。' : '已关闭视频勾画;草稿会保留。');
  } catch (error) {
    const failure = AnnotationsCore.classifyPatchFailure(error.status, error.body);
    if (failure.kind === 'revision_conflict') {
      showToast('设置已被其他窗口修改,正在重新加载。');
      await reloadAnnotationsSummary();
    } else {
      showToast(failure.message);
    }
    const enabledToggle = document.getElementById('annotation-enabled-toggle');
    if (enabledToggle) enabledToggle.checked = ANNOTATIONS_WS.summary?.settings?.enabled === true;
  }
}

// ------------------------------------------------------------ 显式桥接

window.loadStep10Data = loadStep10Data;
window.resetAnnotationsProjectState = resetAnnotationsProjectState;
window.flushAnnotationsSave = flushAnnotationsSave;
window.queueAnnotationSave = queueAnnotationSave;
window.reloadAnnotationsSummary = reloadAnnotationsSummary;
window.setAnnotationsEnabled = setAnnotationsEnabled;
window.selectAnnotationPage = selectAnnotationPage;
window.selectAnnotationItem = selectAnnotationItem;
window.refreshAnnotationModuleState = refreshAnnotationModuleState;
window.setAnnotationDecision = setAnnotationDecision;
window.ANNOTATIONS_WS = ANNOTATIONS_WS;

// ------------------------------------------------------------ W3: 文字候选与 AI 规划

ANNOTATIONS_WS.jobTimer = null;
ANNOTATIONS_WS.candidates = [];

function stopAnnotationJobPolling() {
  clearTimeout(ANNOTATIONS_WS.jobTimer);
  ANNOTATIONS_WS.jobTimer = null;
}

// 重置项目状态时一并停止任务轮询(挂在既有复位函数之后)
const _resetAnnotationsBase = resetAnnotationsProjectState;
resetAnnotationsProjectState = function () {
  stopAnnotationJobPolling();
  ANNOTATIONS_WS.candidates = [];
  _resetAnnotationsBase();
};

async function submitAnnotationJob(operation) {
  const projectId = ANNOTATIONS_WS.projectId;
  if (!projectId) return;
  const requestKey = `${operation}-${projectId}-${ANNOTATIONS_WS.page.slide_id}-${Date.now()}`;
  const body = {
    operation,
    slide_ids: ANNOTATIONS_WS.page.slide_id ? [ANNOTATIONS_WS.page.slide_id] : undefined,
    request_key: requestKey,
  };
  let res;
  try {
    res = await API.post(`${annotationsApiBase()}/jobs`, body, { silent: true });
  } catch (error) {
    showToast(error.message || '任务提交失败');
    return;
  }
  renderAnnotationJobProgress(operation, res.job_id, 'queued', 0);
  pollAnnotationJob(res.job_id, operation);
}

function pollAnnotationJob(jobId, operation) {
  stopAnnotationJobPolling();
  const tick = async () => {
    let job;
    try {
      job = await API.get(`${annotationsApiBase()}/jobs/${encodeURIComponent(jobId)}`, { silent: true });
    } catch (error) {
      renderAnnotationJobProgress(operation, jobId, 'error', 0, error.message);
      return;
    }
    renderAnnotationJobProgress(operation, jobId, job.status, job.progress, job.error);
    if (job.status === 'succeeded') {
      if (operation === 'detect_text') {
        await loadAnnotationCandidates();
        showToast('文字识别完成;可点选候选生成文字标注。');
      } else if (operation === 'plan') {
        await selectAnnotationPage(ANNOTATIONS_WS.activeIndex); // 重载页面拿到 AI 条目
        showToast('AI 重点已生成,均为待确认草稿。');
      }
      return;
    }
    if (job.status === 'running' || job.status === 'queued') {
      ANNOTATIONS_WS.jobTimer = setTimeout(tick, 1200);
    }
  };
  ANNOTATIONS_WS.jobTimer = setTimeout(tick, 800);
}

function renderAnnotationJobProgress(operation, jobId, status, progress, error) {
  const node = document.getElementById('annotation-job-status');
  if (!node) return;
  const label = operation === 'detect_text' ? '文字识别' : 'AI 生成重点';
  if (status === 'succeeded') {
    node.style.display = 'none';
    node.textContent = '';
    return;
  }
  node.style.display = 'inline-block';
  if (status === 'failed' || status === 'error') {
    node.dataset.state = 'error';
    node.textContent = `${label}失败:${error || '请重试'}`;
    return;
  }
  node.dataset.state = 'saving';
  node.textContent = `${label}中… ${Math.round(progress || 0)}%`;
}

async function loadAnnotationCandidates() {
  const slideId = ANNOTATIONS_WS.page.slide_id;
  if (!slideId) return;
  try {
    const res = await API.get(`${annotationsApiBase()}/slides/${encodeURIComponent(slideId)}/text-layout`, { silent: true });
    ANNOTATIONS_WS.candidates = res.candidates || [];
    ANNOTATIONS_WS.layoutRevision = res.layout_revision || 0;
  } catch (error) {
    ANNOTATIONS_WS.candidates = [];
  }
  renderAnnotationCandidates();
}

function renderAnnotationCandidates() {
  const container = document.getElementById('annotation-candidates');
  if (!container) return;
  const candidates = ANNOTATIONS_WS.candidates || [];
  if (!candidates.length) {
    container.innerHTML = '<div class="annotation-items-empty">尚未识别文字。点击"识别文字"后可点选候选。</div>';
    return;
  }
  container.innerHTML = candidates.map(candidate => {
    const granularityTag = candidate.granularity === 'line' ? '<span class="annotation-chip">整行</span>' : '';
    return `<button type="button" class="annotation-candidate" data-token-id="${escHtml(candidate.token_id)}" title="${escHtml(candidate.text)}">
      <span class="annotation-candidate-text">${escHtml(candidate.text)}</span>${granularityTag}
    </button>`;
  }).join('');
  container.querySelectorAll('.annotation-candidate').forEach(node => {
    node.addEventListener('click', () => addAnnotationFromCandidate(node.dataset.tokenId));
  });
}

function addAnnotationFromCandidate(tokenId) {
  const candidate = (ANNOTATIONS_WS.candidates || []).find(entry => entry.token_id === tokenId);
  if (!candidate) return;
  const defaults = ANNOTATIONS_WS.summary?.settings?.defaults || {};
  const polygon = candidate.polygon;
  if (!polygon || polygon.length !== 4) {
    showToast('该候选缺少有效几何,请重新识别文字。');
    return;
  }
  pushAnnotationHistory();
  const item = {
    target: {
      kind: 'text',
      layout_revision: ANNOTATIONS_WS.layoutRevision || 1,
      token_ids: [tokenId],
      polygons: [polygon],
      quote: candidate.text,
      granularity: candidate.granularity || 'char',
      mask_group_ids: [],
    },
    anchor: null,
    style: {
      type: defaults.type || 'ellipse',
      color: defaults.color || '#F46A38',
      opacity: Number(defaults.opacity ?? 0.85),
      width: Number(defaults.width || 5),
      padding: Number(defaults.padding || 8),
      seed: Math.floor(Math.random() * 2147483647),
    },
    timing: {
      trigger_mode: 'anchor_start',
      offset_sec: 0,
      draw_duration_sec: Number(defaults.draw_duration_sec || 0.6),
      hold_mode: 'beat_end',
      exit_duration_sec: Number(defaults.exit_duration_sec || 0.15),
    },
  };
  ANNOTATIONS_WS.page.items.push({ ...item, annotation_id: `local_${Date.now()}` });
  queueAnnotationSave(AnnotationsCore.buildAddOperation(item));
  renderAnnotationItems();
  renderAnnotationOverlay();
  const lastIndex = ANNOTATIONS_WS.page.items.length - 1;
  selectAnnotationItem(ANNOTATIONS_WS.page.items[lastIndex].annotation_id);
  showToast('已添加文字标注;到讲稿中选中短语完成关联。');
}

window.submitAnnotationJob = submitAnnotationJob;
window.loadAnnotationCandidates = loadAnnotationCandidates;
