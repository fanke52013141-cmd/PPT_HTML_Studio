// 勾画编辑恢复行为回归:撤销/重做必须产生服务端操作(自比较修复)、
// 本地条目撤销撤下 add、延迟提交的文字候选、逐页确认调用、
// 在飞竞态后的 local id 重映射。真实 workspace/editor 源码在 Node VM 中驱动。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const sandbox = createSandbox();
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root, 'static', 'annotation_playback.js'), 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(path.join(root, 'static', 'annotations_core.js'), 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(path.join(root, 'static', 'annotations_workspace.js'), 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(path.join(root, 'static', 'annotations_editor.js'), 'utf8'), sandbox);

const core = sandbox.AnnotationsCore;
const WS = sandbox.window.ANNOTATIONS_WS;
const run = expr => vm.runInContext(expr, sandbox);
const await0 = () => new Promise(resolve => setImmediate(resolve));

(async () => {
const REGION_TARGET = {
  kind: 'region', layout_revision: null, token_ids: [],
  polygons: [[[100, 200], [400, 200], [400, 260], [100, 260]]],
  quote: null, granularity: 'region', mask_group_ids: [],
};

function setupProject(projectId, slideId, revision = 0) {
  run(`(() => {
    resetAnnotationsProjectState();
    ANNOTATIONS_WS.projectId = ${JSON.stringify(projectId)};
    ANNOTATIONS_WS.page = {
      slide_id: ${JSON.stringify(slideId)}, revision: ${revision}, items: [],
      narration: { beats: [{ beat_id: 'b1', spoken_text: '这是重点内容' }] },
      imageHash: 'a'.repeat(64),
    };
  })()`);
}

function regionItem(id, overrides = {}) {
  return {
    annotation_id: id,
    target: JSON.parse(JSON.stringify(REGION_TARGET)),
    anchor: null,
    style: { type: 'ellipse', color: '#F46A38', opacity: 0.85, width: 5, padding: 8, seed: 1 },
    timing: {
      trigger_mode: 'manual', offset_sec: 0, manual_start_sec: 0,
      draw_duration_sec: 0.6, hold_mode: 'slide_end', exit_duration_sec: 0.15,
    },
    status: { content: 'draft', spatial: 'valid', temporal: 'awaiting_audio' },
    protection: { source: 'manual', modified_fields: [], locked: false },
    ...overrides,
  };
}

// ------------------------------------------------------------ 撤销/重做

// 撤销删除服务端条目:必须重新入队 add(此前数组与自身比较,永远 0 操作)
{
  setupProject('pU', 'slide_001');
  WS.page.items = [regionItem('ann_001')];
  run('pushAnnotationHistory()');
  WS.page.items = []; // 模拟删除后
  run('undoAnnotationEdit()');
  assert.equal(WS.pendingOps.length, 1, '撤销必须重新入队操作');
  assert.equal(WS.pendingOps[0].op, 'add');
  assert.equal(WS.pendingOps[0].item.annotation_id, undefined, '重入队的 add 不得携带服务端 id');
  assert.equal(WS.page.items.length, 1);
  console.log('undo of delete requeues add ok');

  run('redoAnnotationEdit()');
  assert.equal(WS.pendingOps.length, 2, '重做必须重新入队 delete');
  assert.equal(WS.pendingOps[1].op, 'delete');
  assert.equal(WS.pendingOps[1].annotation_id, 'ann_001');
  assert.equal(WS.page.items.length, 0);
  console.log('redo of undo requeues delete ok');
}

// 撤销刚画完(未保存)的本地条目:撤下排队中的 add,而不是发送 delete
{
  setupProject('pL', 'slide_001');
  run('pushAnnotationHistory()');
  const stored = { ...regionItem(''), annotation_id: 'local_42_1' };
  WS.page.items.push(stored);
  const addOp = core.buildAddOperation(stored);
  assert.equal(addOp.__local_id, 'local_42_1', '本地条目的 add 必须携带 __local_id');
  WS.pendingOps.push(addOp);
  run('undoAnnotationEdit()');
  assert.equal(WS.page.items.length, 0, '撤销移除本地条目');
  assert.equal(WS.pendingOps.length, 0, '排队的 add 必须被撤下,不得发送悬空 delete');
  console.log('undo of unsaved local item cancels pending add ok');
}

// 在飞竞态:保存请求在途时撤销本地条目 → delete 先入队,
// flush 成功后由 local id 重映射改写为服务端 id,下一轮 flush 删除服务端条目
{
  setupProject('pR', 'slide_001');
  let releasePatch;
  sandbox.__api.patch = (_url, _payload) => new Promise(resolve => { releasePatch = resolve; });
  const stored = { ...regionItem(''), annotation_id: 'local_7_1' };
  const targetFingerprint = JSON.stringify(stored.target);
  WS.page.items.push(stored);
  WS.pendingOps.push(core.buildAddOperation(stored));
  const flushPromise = run('flushAnnotationsSave()').catch(() => 'should-not-reject');
  // 在飞期间撤销:delete local_7_1 排队(add 已不在队列里)
  run('pushAnnotationHistory()');
  WS.page.items = [];
  WS.pendingOps.push(core.buildDeleteOperation('local_7_1'));
  releasePatch({ revision: 2, items: [{ annotation_id: 'ann_005', target: stored.target }] });
  await flushPromise;
  assert.equal(WS.pendingOps.length, 1, '重映射后应只剩 delete');
  assert.equal(WS.pendingOps[0].annotation_id, 'ann_005', '在飞窗口的 local delete 必须重映射为服务端 id');
  // 下一轮 flush 发送 delete ann_005
  sandbox.__api.patch = async (_url, payload) => {
    assert.equal(payload.operations[0].annotation_id, 'ann_005');
    assert.equal(payload.expected_revision, 2);
    return { revision: 3, items: [] };
  };
  await run('flushAnnotationsSave()').catch(() => { throw new Error('remapped delete must flush cleanly'); });
  assert.equal(WS.page.items.length, 0);
  console.log('in-flight local id remap ok');
}

// ------------------------------------------------------------ 延迟提交的文字候选

// 无锚点时:本地草稿不入队;选中讲稿短语后随 add 一起提交
{
  setupProject('pC', 'slide_001');
  WS.candidates = [{
    token_id: 'tok_0001_0001', text: '重点',
    polygon: [[100, 200], [140, 200], [140, 240], [100, 240]],
    granularity: 'char', layout_revision: 2,
  }];
  WS.layoutRevision = 2;
  run('addAnnotationFromCandidate("tok_0001_0001")');
  assert.equal(WS.page.items.length, 1);
  assert.equal(WS.page.items[0].__deferredAdd, true, '无锚点文字候选必须延迟提交');
  assert.equal(WS.pendingOps.length, 0, '延迟条目不得先发 add(服务端要求锚点)');
  assert.equal(WS.selectedAnnotationId, WS.page.items[0].annotation_id, '延迟条目应被选中以接收锚点');

  const anchor = {
    beat_id: 'b1', offset_unit: 'unicode_codepoint', range: [2, 4],
    quote: '重点', occurrence: 1, context_before: '这是', context_after: '内容',
  };
  run(`annotationNarrationAnchorPicked(${JSON.stringify(anchor)})`);
  assert.equal(WS.pendingOps.length, 1, '锚点就位后必须入队 add');
  assert.equal(WS.pendingOps[0].op, 'add');
  assert.ok(WS.pendingOps[0].__local_id, '延迟条目的 add 必须携带 __local_id');
  assert.ok(WS.pendingOps[0].item.anchor, 'add 必须携带锚点(服务端对文字目标强制要求)');
  assert.ok(!WS.page.items[0].__deferredAdd, '入队后延迟标记必须清除');
  console.log('deferred text candidate commits with anchor ok');
}

// ------------------------------------------------------------ 逐页确认

// 常规确认:POST /confirm、状态本地落账、revision 更新
{
  setupProject('pF', 'slide_001', 3);
  WS.page.items = [regionItem('ann_001')];
  sandbox.__api.post = async (url, payload) => {
    assert.ok(url.endsWith('/annotations/slides/slide_001/confirm'), '确认必须调用 confirm 端点');
    assert.equal(payload.expected_revision, 3);
    assert.equal(payload.accepted_review.length, 0);
    return { slide_id: 'slide_001', revision: 4, confirmed: 1, timeline_built: true, timeline_error: '' };
  };
  await run('confirmAnnotationPage()');
  assert.equal(WS.page.revision, 4, '确认后必须采用服务端 revision');
  assert.equal(WS.page.items[0].status.content, 'confirmed', '确认后条目必须落为 confirmed');
  console.log('page confirm happy path ok');
}

// 复核项:服务端 review_required(UI 预检查未命中,模拟两端状态分歧)
// → 显式接受后带 accepted_review 重发
{
  setupProject('pV', 'slide_001', 1);
  WS.page.items = [regionItem('ann_001')];
  sandbox.__calls.post = [];
  let confirmCalls = 0;
  sandbox.__api.post = async (_url, payload) => {
    confirmCalls += 1;
    if (confirmCalls === 1) {
      assert.equal(payload.accepted_review.length, 0);
      const error = new Error('review required');
      error.status = 422;
      error.body = { detail: { code: 'review_required', items: [{ annotation_id: 'ann_001', reason: 'needs_review' }] } };
      throw error;
    }
    assert.equal(payload.accepted_review.length, 1, '重发必须显式接受复核项');
    assert.equal(payload.accepted_review[0], 'ann_001');
    return { slide_id: 'slide_001', revision: 2, confirmed: 1, timeline_built: false, timeline_error: 'audio_timeline_missing' };
  };
  await run('confirmAnnotationPage()');
  // 重试经 showCustomConfirm 回调触发(火后不理),等微任务排空后再断言
  await await0();
  await await0();
  assert.equal(confirmCalls, 2, 'review_required 必须确认后重发');
  assert.equal(WS.page.items[0].status.content, 'confirmed');
  assert.ok(sandbox.__toasts.some(message => message.includes('音频时间轴')), '时间轴缺失必须给出可操作提示');
  console.log('review_required acceptance ok');
}

console.log('annotation edit recovery checks passed');
})().catch(error => { console.error(error); process.exit(1); });

// ------------------------------------------------------------ VM 环境桩

function createSandbox() {
  const toasts = [];
  const confirms = [];
  const calls = { patch: [], get: [], post: [], put: [] };
  const state = { currentProject: { id: 'pA' }, currentStep: 10, step_status: {} };
  const nodeStub = () => ({
    style: {}, dataset: {}, textContent: '', innerHTML: '', title: '',
    onclick: null, checked: false, value: '', disabled: false,
    setAttribute: () => {}, getAttribute: () => null,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 960, height: 540 }),
    remove: () => {}, append: () => {}, appendChild: () => {},
    querySelectorAll: () => [], querySelector: () => null,
    addEventListener: () => {},
    classList: { toggle: () => {}, add: () => {}, remove: () => {} },
  });
  const document = { getElementById: () => nodeStub(), createElement: () => nodeStub(), createElementNS: () => nodeStub() };
  const windowObj = {};
  const queue = [];
  const sandbox = {
    console,
    setTimeout: (fn, _ms) => { queue.push(fn); return queue.length; },
    clearTimeout: () => {},
    performance,
    Date, Math, JSON, Number, String, Boolean, Array, Object, Promise, Error, Set, Map,
    isNaN, parseInt, parseFloat,
    document,
    window: windowObj,
    state,
    showToast: message => toasts.push(message),
    showCustomConfirm: (_title, _message, onConfirm) => { confirms.push(_title); onConfirm(); },
    escHtml: value => String(value ?? ''),
    updateStepperUI: () => {},
    getProjectCanvasGeometry: () => ({ width: 1920, height: 1080 }),
    PPTFlow: { mapClientPointToCanvas: (_x, _y, _rect, width, height) => ({ x: 0, y: 0, width, height }) },
    selectAnnotationItem: id => { windowObj.ANNOTATIONS_WS.selectedAnnotationId = id; },
    renderAnnotationCandidates: () => {},
    renderAnnotationJobProgress: () => {},
    __api: {},
    __calls: calls,
    __toasts: toasts,
    __confirms: confirms,
    __queue: queue,
  };
  sandbox.API = {
    async patch(url, payload) {
      calls.patch.push({ url, payload });
      const handler = sandbox.__api && sandbox.__api.patch;
      if (!handler) throw new Error('patch handler not set');
      return handler(url, payload);
    },
    async get(url) {
      calls.get.push({ url });
      const handler = sandbox.__api && sandbox.__api.get;
      if (!handler) throw new Error('get handler not set');
      return handler(url);
    },
    async post(url, payload) {
      calls.post.push({ url, payload });
      const handler = sandbox.__api && sandbox.__api.post;
      if (!handler) throw new Error('post handler not set');
      return handler(url, payload);
    },
    async put(url, payload) {
      calls.put.push({ url, payload });
      const handler = sandbox.__api && sandbox.__api.put;
      if (!handler) throw new Error('put handler not set');
      return handler(url, payload);
    },
  };
  return sandbox;
}
