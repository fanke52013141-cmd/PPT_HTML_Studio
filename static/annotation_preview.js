// Formal audio + Reveal + ink preview. Uses the exact Remotion video component.
const ANNOTATION_PREVIEW = { prepared: null, loading: null, generation: 0 };

async function loadAnnotationPlayer() {
  if (window.AnnotationPlayer) return;
  if (!ANNOTATION_PREVIEW.loading) {
    ANNOTATION_PREVIEW.loading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = '/annotation_player.bundle.js?v=20261006.1';
      script.onload = resolve;
      script.onerror = () => { ANNOTATION_PREVIEW.loading = null; reject(new Error('预览播放器加载失败')); };
      document.head.appendChild(script);
    });
  }
  await ANNOTATION_PREVIEW.loading;
}

function annotationPrepareError(error) {
  const reasons = {
    anchor_unresolved: '无法准确定位所选词，请在右侧试听并设置起笔点，或运行音频定位。',
    target_not_ready: '讲到所选内容时，画面目标尚未出现。请提前该内容的出现时间。',
    target_visibility_unresolved: '无法确定目标何时出现，请检查区域与 Mask 内容组的对应关系。',
    insufficient_draw_window: '页尾没有足够时间完整绘制，请缩短笔迹或提前起笔。',
    audio_timeline_missing: '本页没有音频时间轴，请先生成音频。',
    text_layout_missing: '文字布局缺失，请重新识别文字。',
    ink_build_failed: '墨迹生成失败，请重试。',
  };
  const items = error?.body?.detail?.items || [];
  if (items.length) return items.map(item => `${item.annotation_id || '本页'}：${reasons[item.reason] || item.reason}`).join('\n');
  return error.message || '预览准备失败';
}

async function prepareAnnotationPreview() {
  await flushAnnotationsSave();
  if (ANNOTATIONS_WS.pendingOps.length || ANNOTATIONS_WS.failedOps.length || ANNOTATIONS_WS.conflict) {
    throw new Error('请先处理未保存的编辑。');
  }
  const projectId = ANNOTATIONS_WS.projectId;
  const slideId = ANNOTATIONS_WS.page.slide_id;
  const revision = ANNOTATIONS_WS.page.revision;
  const result = await API.post(`${annotationsApiBase(projectId)}/slides/${encodeURIComponent(slideId)}/prepare`,
    {expected_revision: revision}, {silent: true});
  if (projectId !== ANNOTATIONS_WS.projectId || slideId !== ANNOTATIONS_WS.page.slide_id
      || revision !== ANNOTATIONS_WS.page.revision || ANNOTATIONS_WS.pendingOps.length) {
    throw new Error('页面已经更新，请重新预览。');
  }
  ANNOTATION_PREVIEW.prepared = {projectId, slideId, revision, result};
  return ANNOTATION_PREVIEW.prepared;
}

async function showAnnotationSyncPreview() {
  const generation = ++ANNOTATION_PREVIEW.generation;
  try {
    const prepared = await prepareAnnotationPreview();
    await loadAnnotationPlayer();
    if (generation !== ANNOTATION_PREVIEW.generation) return;
    const {projectId, slideId, result} = prepared;
    const base = `${annotationsApiBase(projectId)}/slides/${encodeURIComponent(slideId)}`;
    const absolute = value => new URL(value, window.location.origin).href;
    const scene = JSON.parse(JSON.stringify(result.scene));
    const assetUrl = asset => absolute(`${base}/scene-asset?asset=${encodeURIComponent(asset)}`);
    scene.layers.forEach(layer => {layer.asset = assetUrl(layer.asset);});
    if (scene.canvas.background_asset) scene.canvas.background_asset = assetUrl(scene.canvas.background_asset);
    const timeline = JSON.parse(JSON.stringify(result.timeline));
    timeline.events.forEach(event => event.strokes.forEach((stroke, index) => {
      const ink = stroke.ink;
      ink.frames = Array.from({length: ink.frame_count}, (_, frame) => absolute(
        `${base}/ink/${timeline.build_id}/${event.annotation_id}/${index}/${frame}`));
    }));
    let dialog = document.getElementById('annotation-sync-preview');
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'annotation-sync-preview';
      dialog.className = 'annotation-sync-preview';
      dialog.innerHTML = '<div class="annotation-pane-title">音频与勾画同步预览</div><div id="annotation-player-root"></div>'
        + '<p>拖动进度检查：目标出现后，讲到关联内容时开始勾画。</p><button type="button" class="secondary">关闭预览</button>';
      dialog.querySelector('button').onclick = () => dialog.close();
      dialog.addEventListener('close', () => window.AnnotationPlayer?.stop());
      document.body.appendChild(dialog);
    }
    const [width, height] = timeline.canvas;
    window.AnnotationPlayer.mount(document.getElementById('annotation-player-root'), {
      slides: [{slide_id: slideId, start_sec: 0, duration_sec: timeline.slide_duration_sec,
        scene, audio_timeline: result.audio_timeline, animation_timeline: result.animation_timeline,
        audio_file: absolute(result.audio_url), annotation_timeline: timeline}],
    }, timeline.fps, timeline.slide_duration_sec, width, height);
    if (!dialog.open) dialog.showModal();
  } catch (error) {
    showToast(annotationPrepareError(error));
  }
}

function stopAnnotationSyncPreview() {
  ++ANNOTATION_PREVIEW.generation;
  window.AnnotationPlayer?.stop();
  document.getElementById('annotation-sync-preview')?.close();
}

window.showAnnotationSyncPreview = showAnnotationSyncPreview;
window.stopAnnotationSyncPreview = stopAnnotationSyncPreview;
