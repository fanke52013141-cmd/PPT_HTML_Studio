// 勾画标注编辑器(可见步骤 10):画布框选、属性编辑、撤销/重做、
// 删除/锁定/禁用。状态与渲染入口在 annotations_workspace.js;
// 服务端操作协议见 annotation_routes(PATCH operations)。

const ANNOTATIONS_ED = {
  regionMode: false,
  regionStart: null,
  regionGhost: null,
  editorTimer: null,
};

// ------------------------------------------------------------ 画布覆盖层

function fallbackStrokeFor(item) {
  // 服务端笔迹缺位时的兜底(仅编辑可见性;导出仍以服务端为准)
  const polygons = item.target?.polygons || [];
  const bounds = AnnotationsCore.polygonBounds(polygons);
  if (!bounds) return [];
  const pad = Number(item.style?.padding || 8);
  const stroke = AnnotationsCore.buildRegionTarget(polygons);
  void stroke;
  if (item.style?.type === 'highlighter') {
    return [{ kind: 'rect', x: bounds.left - pad / 2, y: bounds.top - pad / 2, width: bounds.width + pad, height: bounds.height + pad }];
  }
  const right = bounds.left + bounds.width;
  const bottom = bounds.top + bounds.height;
  if (item.style?.type === 'underline') {
    const y = bottom + pad + Number(item.style?.width || 5) / 2;
    return [{ kind: 'polyline', points: [[bounds.left - pad, y], [(bounds.left + right) / 2, y + 5], [right + pad, y]] }];
  }
  const cx = bounds.left + bounds.width / 2;
  const cy = bounds.top + bounds.height / 2;
  const points = [];
  for (let i = 0; i < 48; i += 1) {
    const angle = (i / 48) * Math.PI * 2;
    points.push([cx + Math.cos(angle) * (bounds.width / 2 + pad), cy + Math.sin(angle) * (bounds.height / 2 + pad)]);
  }
  points.push(points[0]);
  return [{ kind: 'polyline', points }];
}

function renderAnnotationOverlay() {
  const overlay = document.getElementById('annotation-canvas-overlay');
  const image = document.getElementById('annotation-canvas-image');
  if (!overlay || !image) return;
  const geometry = typeof getProjectCanvasGeometry === 'function'
    ? getProjectCanvasGeometry()
    : { width: 1920, height: 1080 };
  overlay.setAttribute('viewBox', `0 0 ${geometry.width} ${geometry.height}`);
  image.src = `/api/projects/${ANNOTATIONS_WS.projectId}/slides/${encodeURIComponent(ANNOTATIONS_WS.page.slide_id)}/image`;
  const items = ANNOTATIONS_WS.page.items || [];
  const shapes = [];
  items.forEach(item => {
    const selected = item.annotation_id === ANNOTATIONS_WS.selectedAnnotationId;
    const polygons = item.target?.polygons || [];
    const bounds = AnnotationsCore.polygonBounds(polygons);
    if (!bounds) return;
    const color = item.style?.color || '#F46A38';
    // 浓度 0% 必须真正不可见(R2 修复:不再钳到 0.05)
    const opacity = Math.max(0, Math.min(1, Number(item.style?.opacity ?? 0.85)));
    const pad = Number(item.style?.padding || 8);
    const disabled = item.status?.content === 'disabled';
    const attrs = disabled ? ' data-disabled="true"' : '';
    if (selected) {
      shapes.push(`<rect class="annotation-select-frame" x="${bounds.left - pad}" y="${bounds.top - pad}" width="${bounds.width + pad * 2}" height="${bounds.height + pad * 2}" fill="none" stroke="#111827" stroke-width="2" stroke-dasharray="10 6" data-owner="${escHtml(item.annotation_id)}" />`);
    }
    // 正式笔迹:服务端派生的 v2 strokes 经共享采样器生成轮廓,
    // 与导出几何完全一致(R2 方案 4.6)。编辑态 = 绘制完成(progress=1)。
    const officialStrokes = item.strokes && item.strokes.length
      ? item.strokes
      : fallbackStrokeFor(item);
    const effectiveEvent = {
      annotation_id: item.annotation_id,
      start_sec: 0,
      draw_end_sec: 1,
      hold_end_sec: 1,
      exit_end_sec: 1,
      style: { ...item.style, color },
      strokes: officialStrokes,
    };
    AnnotationsPlayback.renderScene([effectiveEvent], 0.5, 30).forEach(shape => {
      const owner = ` data-owner="${escHtml(item.annotation_id)}"${attrs}`;
      if (shape.kind === 'path') {
        shapes.push(`<path d="${escHtml(shape.d)}" fill="${shape.closed ? escHtml(color) : 'none'}" fill-opacity="${shape.closed ? Math.min(0.12, opacity * 0.14) : 0}" stroke="${escHtml(color)}" stroke-width="${Math.max(1, Number(item.style?.width || 5) * 0.6)}" stroke-linejoin="round" opacity="${disabled ? opacity * 0.3 : opacity}"${owner} />`);
      } else if (shape.kind === 'polyline') {
        shapes.push(`<path d="${escHtml(shape.d)}" fill="none" stroke="${escHtml(color)}" stroke-width="${shape.strokeWidth}" stroke-linecap="round" stroke-linejoin="round" opacity="${disabled ? opacity * 0.3 : opacity}"${owner} />`);
      } else if (shape.kind === 'rect') {
        shapes.push(`<rect x="${shape.x}" y="${shape.y}" width="${shape.width}" height="${shape.height}" fill="${escHtml(color)}" fill-opacity="${opacity * 0.35}" stroke="none"${owner} />`);
      }
    });
  });
  overlay.innerHTML = shapes.join('');
  overlay.querySelectorAll('[data-owner]').forEach(shape => {
    shape.addEventListener('click', () => selectAnnotationItem(shape.dataset.owner));
  });
}

// ------------------------------------------------------------ 区域框选

function setAnnotationRegionMode(enabled) {
  ANNOTATIONS_ED.regionMode = enabled === true;
  const frame = document.getElementById('annotation-canvas-frame');
  const button = document.getElementById('annotation-btn-region');
  if (frame) frame.classList.toggle('region-mode', ANNOTATIONS_ED.regionMode);
  if (button) button.classList.toggle('active', ANNOTATIONS_ED.regionMode);
}

function handleAnnotationRegionPointerDown(event) {
  if (!ANNOTATIONS_ED.regionMode || event.button !== 0) return;
  event.preventDefault();
  const frame = document.getElementById('annotation-canvas-frame');
  const image = document.getElementById('annotation-canvas-image');
  if (!frame || !image) return;
  const geometry = getProjectCanvasGeometry();
  const point = PPTFlow.mapClientPointToCanvas(event.clientX, event.clientY, image.getBoundingClientRect(), geometry.width, geometry.height);
  ANNOTATIONS_ED.regionStart = point;
  const ghost = document.getElementById('annotation-region-ghost');
  if (ghost) {
    ghost.style.display = 'block';
    ghost.style.left = '0px';
    ghost.style.top = '0px';
    ghost.style.width = '0px';
    ghost.style.height = '0px';
  }
  ANNOTATIONS_ED.regionGhost = ghost;
  frame.setPointerCapture?.(event.pointerId);
}

function handleAnnotationRegionPointerMove(event) {
  if (!ANNOTATIONS_ED.regionMode || !ANNOTATIONS_ED.regionStart) return;
  const image = document.getElementById('annotation-canvas-image');
  const ghost = ANNOTATIONS_ED.regionGhost;
  if (!image || !ghost) return;
  const geometry = getProjectCanvasGeometry();
  const point = PPTFlow.mapClientPointToCanvas(event.clientX, event.clientY, image.getBoundingClientRect(), geometry.width, geometry.height);
  const rect = image.getBoundingClientRect();
  const scaleX = rect.width / geometry.width;
  const scaleY = rect.height / geometry.height;
  const left = Math.min(ANNOTATIONS_ED.regionStart.x, point.x) * scaleX;
  const top = Math.min(ANNOTATIONS_ED.regionStart.y, point.y) * scaleY;
  ghost.style.left = `${left}px`;
  ghost.style.top = `${top}px`;
  ghost.style.width = `${Math.abs(point.x - ANNOTATIONS_ED.regionStart.x) * scaleX}px`;
  ghost.style.height = `${Math.abs(point.y - ANNOTATIONS_ED.regionStart.y) * scaleY}px`;
}

function handleAnnotationRegionPointerUp(event) {
  if (!ANNOTATIONS_ED.regionMode || !ANNOTATIONS_ED.regionStart) return;
  const image = document.getElementById('annotation-canvas-image');
  const ghost = ANNOTATIONS_ED.regionGhost;
  if (ghost) ghost.style.display = 'none';
  ANNOTATIONS_ED.regionGhost = null;
  const start = ANNOTATIONS_ED.regionStart;
  ANNOTATIONS_ED.regionStart = null;
  if (!image) return;
  const geometry = getProjectCanvasGeometry();
  const point = PPTFlow.mapClientPointToCanvas(event.clientX, event.clientY, image.getBoundingClientRect(), geometry.width, geometry.height);
  const polygon = AnnotationsCore.rectangleToPolygon(start, point, geometry);
  if (!polygon) {
    showToast('选区太小,请拖出更大的区域。');
    return;
  }
  addAnnotationRegion(polygon);
}

function addAnnotationRegion(polygon) {
  const defaults = ANNOTATIONS_WS.summary?.settings?.defaults || {};
  const item = {
    target: AnnotationsCore.buildRegionTarget(polygon),
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
  pushAnnotationHistory();
  ANNOTATIONS_WS.page.items.push({ ...item, annotation_id: `local_${Date.now()}` });
  queueAnnotationSave(AnnotationsCore.buildAddOperation(item));
  const lastIndex = ANNOTATIONS_WS.page.items.length - 1;
  renderAnnotationItems();
  renderAnnotationOverlay();
  // 选中新条目(本地临时 id 在保存成功后被服务端 id 替换,此处选最后一项)
  selectAnnotationItem(ANNOTATIONS_WS.page.items[lastIndex].annotation_id);
  showToast('已添加区域标注;可在右侧调整样式,并到讲稿中选中短语关联。');
}

// ------------------------------------------------------------ 讲稿关联

function annotationNarrationAnchorPicked(anchor) {
  const selectedId = ANNOTATIONS_WS.selectedAnnotationId;
  const item = (ANNOTATIONS_WS.page.items || []).find(entry => entry.annotation_id === selectedId);
  if (!item) {
    showToast('请先在列表或画布中选择要关联的标注,再到讲稿中选词。');
    return;
  }
  if (item.target?.kind === 'text' && !item.target?.token_ids?.length) {
    showToast('文字目标需要通过文字候选生成;区域标注可直接关联。');
    return;
  }
  pushAnnotationHistory();
  const index = ANNOTATIONS_WS.page.items.indexOf(item);
  ANNOTATIONS_WS.page.items[index] = { ...item, anchor };
  queueAnnotationSave(AnnotationsCore.buildUpdateOperation(item.annotation_id, { anchor }));
  renderAnnotationItems();
  renderAnnotationNarrationHighlights();
  showToast(`已关联讲稿:"${anchor.quote}"`);
}

// ------------------------------------------------------------ 属性编辑

function annotationSelectedItem() {
  return (ANNOTATIONS_WS.page.items || []).find(
    item => item.annotation_id === ANNOTATIONS_WS.selectedAnnotationId
  );
}

function renderAnnotationItemEditor() {
  const editor = document.getElementById('annotation-item-editor');
  if (!editor) return;
  const item = annotationSelectedItem();
  if (!item) {
    editor.style.display = 'none';
    editor.innerHTML = '';
    return;
  }
  const style = item.style || {};
  const timing = item.timing || {};
  const opacityPercent = AnnotationsCore.opacityToPercent(style.opacity);
  const isDisabled = item.status?.content === 'disabled';
  editor.style.display = 'block';
  editor.innerHTML = `
    <div class="annotation-editor-title">属性 · ${escHtml(item.annotation_id)}</div>
    <label class="annotation-field">样式
      <select id="annotation-edit-style-type">
        <option value="ellipse"${style.type === 'ellipse' ? ' selected' : ''}>手写圈</option>
        <option value="underline"${style.type === 'underline' ? ' selected' : ''}>横线</option>
        <option value="highlighter"${style.type === 'highlighter' ? ' selected' : ''}>荧光笔</option>
      </select>
    </label>
    <label class="annotation-field">颜色
      <input type="color" id="annotation-edit-style-color" value="${escHtml(style.color || '#F46A38')}">
    </label>
    <label class="annotation-field">笔迹浓度 <span id="annotation-edit-opacity-value">${opacityPercent}%</span>
      <input type="range" id="annotation-edit-style-opacity" min="0" max="100" step="5" value="${opacityPercent}">
    </label>
    <label class="annotation-field">粗细(px)
      <input type="number" id="annotation-edit-style-width" min="1" max="40" value="${Number(style.width || 5)}">
    </label>
    <label class="annotation-field">留白(px)
      <input type="number" id="annotation-edit-style-padding" min="0" max="80" value="${Number(style.padding || 8)}">
    </label>
    <label class="annotation-field">提前/延后(秒)
      <input type="number" id="annotation-edit-timing-offset" min="-5" max="5" step="0.05" value="${Number(timing.offset_sec || 0)}">
    </label>
    <label class="annotation-field">绘制时长(秒)
      <input type="number" id="annotation-edit-timing-draw" min="0.05" max="10" step="0.05" value="${Number(timing.draw_duration_sec || 0.6)}">
    </label>
    <label class="annotation-field">保留方式
      <select id="annotation-edit-timing-hold">
        <option value="beat_end"${(timing.hold_mode || 'beat_end') === 'beat_end' ? ' selected' : ''}>到语块结束</option>
        <option value="slide_end"${timing.hold_mode === 'slide_end' ? ' selected' : ''}>到页面结束</option>
        <option value="duration"${timing.hold_mode === 'duration' ? ' selected' : ''}>固定时长</option>
      </select>
    </label>
    <label class="annotation-field hold-duration${timing.hold_mode === 'duration' ? '' : ' hidden'}">保留时长(秒)
      <input type="number" id="annotation-edit-timing-hold-duration" min="0.05" max="120" step="0.1" value="${Number(timing.hold_duration_sec || 3)}">
    </label>
    <label class="annotation-field annotation-lock-field">
      <input type="checkbox" id="annotation-edit-locked"${item.protection?.locked ? ' checked' : ''}>
      锁定(防止 AI 重规划改写)
    </label>
    <div class="annotation-editor-actions">
      <button type="button" id="annotation-btn-toggle-disable" class="secondary compact-action-btn">${isDisabled ? '重新启用' : '禁用此条'}</button>
      <button type="button" id="annotation-btn-delete" class="danger compact-action-btn">删除</button>
    </div>
  `;
  bindAnnotationEditorEvents(item.annotation_id);
}

function queueAnnotationItemPatch(annotationId, patchOrCollector) {
  const item = (ANNOTATIONS_WS.page.items || []).find(entry => entry.annotation_id === annotationId);
  if (!item) return;
  // patch 允许是对象或 (item) => patch 的收集函数(依赖编辑时条目现状)
  const patch = typeof patchOrCollector === 'function' ? patchOrCollector(item) : patchOrCollector;
  if (!patch || typeof patch !== 'object' || !Object.keys(patch).length) return;
  const index = ANNOTATIONS_WS.page.items.indexOf(item);
  ANNOTATIONS_WS.page.items[index] = { ...item, ...patch };
  queueAnnotationSave(AnnotationsCore.buildUpdateOperation(annotationId, patch));
  renderAnnotationItems();
  renderAnnotationOverlay();
  renderAnnotationNarrationHighlights();
}

function scheduleAnnotationStyleCommit(annotationId, collect) {
  clearTimeout(ANNOTATIONS_ED.editorTimer);
  ANNOTATIONS_ED.editorTimer = setTimeout(() => {
    const item = annotationSelectedItem();
    if (!item || item.annotation_id !== annotationId) return;
    pushAnnotationHistory();
    queueAnnotationItemPatch(annotationId, collect(item));
  }, 350);
}

function bindAnnotationEditorEvents(annotationId) {
  const editor = document.getElementById('annotation-item-editor');
  if (!editor) return;

  const styleType = editor.querySelector('#annotation-edit-style-type');
  styleType?.addEventListener('change', () => {
    pushAnnotationHistory();
    queueAnnotationItemPatch(annotationId, item => ({ style: { ...item.style, type: styleType.value } }));
  });

  const color = editor.querySelector('#annotation-edit-style-color');
  color?.addEventListener('change', () => {
    scheduleAnnotationStyleCommit(annotationId, item => ({ style: { ...item.style, color: color.value.toUpperCase() } }));
  });

  const opacity = editor.querySelector('#annotation-edit-style-opacity');
  const opacityValue = editor.querySelector('#annotation-edit-opacity-value');
  opacity?.addEventListener('input', () => {
    if (opacityValue) opacityValue.textContent = `${opacity.value}%`;
  });
  opacity?.addEventListener('change', () => {
    pushAnnotationHistory();
    queueAnnotationItemPatch(annotationId, item => ({
      style: { ...item.style, opacity: AnnotationsCore.percentToOpacity(Number(opacity.value)) },
    }));
  });

  const numberFields = [
    ['#annotation-edit-style-width', 'width'],
    ['#annotation-edit-style-padding', 'padding'],
  ];
  numberFields.forEach(([selector, key]) => {
    const input = editor.querySelector(selector);
    input?.addEventListener('change', () => {
      scheduleAnnotationStyleCommit(annotationId, item => ({
        style: { ...item.style, [key]: Math.max(0, Math.round(Number(input.value) || 0)) },
      }));
    });
  });

  const timingFields = [
    ['#annotation-edit-timing-offset', 'offset_sec', true],
    ['#annotation-edit-timing-draw', 'draw_duration_sec', true],
    ['#annotation-edit-timing-hold-duration', 'hold_duration_sec', true],
  ];
  timingFields.forEach(([selector, key, isFloat]) => {
    const input = editor.querySelector(selector);
    input?.addEventListener('change', () => {
      scheduleAnnotationStyleCommit(annotationId, item => {
        const timing = { ...item.timing };
        timing[key] = isFloat ? Number(input.value) : Math.round(Number(input.value) || 0);
        return { timing };
      });
    });
  });

  const hold = editor.querySelector('#annotation-edit-timing-hold');
  hold?.addEventListener('change', () => {
    const holdDurationField = editor.querySelector('.hold-duration');
    if (holdDurationField) holdDurationField.classList.toggle('hidden', hold.value !== 'duration');
    scheduleAnnotationStyleCommit(annotationId, item => {
      const timing = { ...item.timing, hold_mode: hold.value };
      if (hold.value !== 'duration') delete timing.hold_duration_sec;
      else timing.hold_duration_sec = Number(editor.querySelector('#annotation-edit-timing-hold-duration')?.value || 3);
      return { timing };
    });
  });

  const locked = editor.querySelector('#annotation-edit-locked');
  locked?.addEventListener('change', () => {
    queueAnnotationItemPatch(annotationId, item => ({
      protection: { locked: locked.checked },
    }));
  });

  editor.querySelector('#annotation-btn-toggle-disable')?.addEventListener('click', () => {
    const item = annotationSelectedItem();
    if (!item) return;
    const next = item.status?.content === 'disabled' ? 'draft' : 'disabled';
    pushAnnotationHistory();
    queueAnnotationItemPatch(annotationId, item2 => ({ status: { content: next } }));
  });

  editor.querySelector('#annotation-btn-delete')?.addEventListener('click', () => {
    const item = annotationSelectedItem();
    if (!item) return;
    showCustomConfirm('删除标注', `确定删除 ${item.annotation_id} 吗?可用撤销恢复。`, () => {
      pushAnnotationHistory();
      ANNOTATIONS_WS.page.items = ANNOTATIONS_WS.page.items.filter(entry => entry.annotation_id !== annotationId);
      ANNOTATIONS_WS.selectedAnnotationId = null;
      queueAnnotationSave(AnnotationsCore.buildDeleteOperation(annotationId));
      renderAnnotationItems();
      renderAnnotationOverlay();
      renderAnnotationNarrationHighlights();
      renderAnnotationItemEditor();
    });
  });
}

// ------------------------------------------------------------ 撤销/重做

function pushAnnotationHistory() {
  const slideId = ANNOTATIONS_WS.page.slide_id;
  if (!slideId) return;
  if (!ANNOTATIONS_WS.histories[slideId]) {
    ANNOTATIONS_WS.histories[slideId] = AnnotationsCore.createPageHistory();
  }
  // 快照只保留服务端已认可的结构字段;本地临时 id 的条目原样保留
  ANNOTATIONS_WS.histories[slideId].push(ANNOTATIONS_WS.page.items);
}

function queueSyncAnnotationItems(targetItems) {
  const current = ANNOTATIONS_WS.page.items || [];
  const currentIds = new Set(current.map(item => item.annotation_id));
  const targetIds = new Set(targetItems.map(item => item.annotation_id));
  const operations = [];
  targetItems.forEach(item => {
    if (!currentIds.has(item.annotation_id) && !String(item.annotation_id).startsWith('local_')) {
      const { annotation_id, ...rest } = item;
      void annotation_id;
      operations.push(AnnotationsCore.buildAddOperation(rest));
    }
  });
  current.forEach(item => {
    if (!targetIds.has(item.annotation_id) && !String(item.annotation_id).startsWith('local_')) {
      operations.push(AnnotationsCore.buildDeleteOperation(item.annotation_id));
    }
  });
  targetItems.forEach(item => {
    if (currentIds.has(item.annotation_id)) {
      const before = current.find(entry => entry.annotation_id === item.annotation_id);
      const patch = {};
      if (JSON.stringify(before?.target) !== JSON.stringify(item.target)) patch.target = item.target;
      if (JSON.stringify(before?.anchor) !== JSON.stringify(item.anchor)) patch.anchor = item.anchor;
      if (JSON.stringify(before?.style) !== JSON.stringify(item.style)) patch.style = item.style;
      if (JSON.stringify(before?.timing) !== JSON.stringify(item.timing)) patch.timing = item.timing;
      if (before?.protection?.locked !== item?.protection?.locked) patch.protection = { locked: item.protection?.locked === true };
      const beforeContent = before?.status?.content === 'disabled' ? 'disabled' : 'draft';
      const afterContent = item?.status?.content === 'disabled' ? 'disabled' : 'draft';
      if (beforeContent !== afterContent) patch.status = { content: afterContent };
      if (Object.keys(patch).length) operations.push(AnnotationsCore.buildUpdateOperation(item.annotation_id, patch));
    }
  });
  if (operations.length) queueAnnotationSave(operations);
}

function undoAnnotationEdit() {
  const slideId = ANNOTATIONS_WS.page.slide_id;
  const history = slideId && ANNOTATIONS_WS.histories[slideId];
  if (!history?.canUndo()) return;
  const restored = history.undo(ANNOTATIONS_WS.page.items);
  if (!restored) return;
  ANNOTATIONS_WS.page.items = restored;
  queueSyncAnnotationItems(restored);
  renderAnnotationItems();
  renderAnnotationOverlay();
  renderAnnotationNarrationHighlights();
  renderAnnotationItemEditor();
}

function redoAnnotationEdit() {
  const slideId = ANNOTATIONS_WS.page.slide_id;
  const history = slideId && ANNOTATIONS_WS.histories[slideId];
  if (!history?.canRedo()) return;
  const restored = history.redo(ANNOTATIONS_WS.page.items);
  if (!restored) return;
  ANNOTATIONS_WS.page.items = restored;
  queueSyncAnnotationItems(restored);
  renderAnnotationItems();
  renderAnnotationOverlay();
  renderAnnotationNarrationHighlights();
  renderAnnotationItemEditor();
}

function annotationEditorKeyboardHandler(event) {
  if (!(event.ctrlKey || event.metaKey) || event.key !== 'z') return;
  const target = event.target;
  if (target instanceof HTMLElement && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable)) {
    return; // 输入控件内保留原生撤销
  }
  const panel = document.getElementById('step-panel-10');
  if (!panel || panel.style.display === 'none') return;
  event.preventDefault();
  if (event.shiftKey) redoAnnotationEdit();
  else undoAnnotationEdit();
}

// ------------------------------------------------------------ 桥接

window.renderAnnotationOverlay = renderAnnotationOverlay;
window.renderAnnotationItemEditor = renderAnnotationItemEditor;
window.setAnnotationRegionMode = setAnnotationRegionMode;
window.annotationNarrationAnchorPicked = annotationNarrationAnchorPicked;
window.undoAnnotationEdit = undoAnnotationEdit;
window.redoAnnotationEdit = redoAnnotationEdit;
window.annotationEditorKeyboardHandler = annotationEditorKeyboardHandler;
window.addAnnotationRegion = addAnnotationRegion;
