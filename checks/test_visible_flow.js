const assert = require('node:assert/strict');
const flow = require('../static/flow.js');

assert.equal(flow.normalizeVisibleStep(4), 5);
assert.equal(flow.normalizeVisibleStep(7), 6);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 7, audio_confirmed: false }), 6);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 7, audio_confirmed: true }), 10);
assert.deepEqual(flow.VISIBLE_FLOW_STEPS, [1, 2, 3, 5, 6, 10, 9, 8]);
assert.equal(flow.normalizeVisibleStep(9), 9);
assert.equal(flow.normalizeVisibleStep(10), 10);
assert.equal(flow.getDownstreamEditImpact(9, 8, { 8: 'completed' })?.includes('重新生成'), true);
assert.equal(flow.getDownstreamEditImpact(3, 8, { 5: 'completed' })?.includes('Mask'), true);
assert.equal(flow.getDownstreamEditImpact(8, 9, { 8: 'completed' }), null);
assert.equal(flow.getDownstreamEditImpact(3, 8, {}), null);

// 可选步骤 9（数字人讲解）：启用即完成，未启用始终 pending
assert.equal(flow.getVisibleStepState(9, {}, { digitalHumanEnabled: true }), 'completed');
assert.equal(flow.getVisibleStepState(9, {}, { digitalHumanEnabled: false }), 'pending');
assert.equal(flow.getVisibleStepState(9, {}, {}), 'pending');

// 模块六（勾画标注）：决策态驱动,与 enabled 解耦(R2 方案 3.2)
assert.equal(flow.getVisibleStepState(10, {}, { annotationModuleState: 'confirmed' }), 'completed');
assert.equal(flow.getVisibleStepState(10, {}, { annotationModuleState: 'no_annotations' }), 'completed');
assert.equal(flow.getVisibleStepState(10, {}, { annotationModuleState: 'editing' }), 'in_progress');
assert.equal(flow.getVisibleStepState(10, {}, { annotationModuleState: 'stale' }), 'pending_reconfirmation');
assert.equal(flow.getVisibleStepState(10, {}, { annotationModuleState: 'not_started' }), 'pending');
assert.equal(flow.getVisibleStepState(10, {}, {}), 'pending');
// enabled 打开但未决策 → 仍然 pending(不能开关一开就算完成)
assert.equal(flow.getVisibleStepState(10, {}, { annotationsEnabled: true, annotationModuleState: 'not_started' }), 'pending');
assert.equal(flow.getVisibleStepState(9, {}, { annotationsEnabled: true, digitalHumanEnabled: false }), 'pending');

// 可选数字人未启用时也保留第 7 步，作品输出始终为第 8 步。
let display = flow.displayFlow({ digitalHumanEnabled: false });
assert.deepEqual(display.map(item => [item.displayNumber, item.step]),
  [[1, 1], [2, 2], [3, 3], [4, 5], [5, 6], [6, 10], [7, 9], [8, 8]]);
display = flow.displayFlow({ digitalHumanEnabled: true });
assert.deepEqual(display.map(item => [item.displayNumber, item.step]),
  [[1, 1], [2, 2], [3, 3], [4, 5], [5, 6], [6, 10], [7, 9], [8, 8]]);

assert.deepEqual(
  flow.mapClientPointToCanvas(510, 295, { left: 10, top: 20, width: 1000, height: 562.5 }),
  { x: 960, y: 528 }
);
assert.deepEqual(
  flow.mapClientPointToCanvas(-10, 900, { left: 10, top: 20, width: 1000, height: 562.5 }),
  { x: 0, y: 1080 }
);

const confirmedImages = {
  1: 'completed',
  2: 'completed',
  3: 'completed',
  4: 'completed',
  5: 'pending',
  6: 'pending',
  7: 'pending',
  8: 'pending'
};
assert.equal(flow.getVisibleStepState(3, confirmedImages), 'completed');
assert.equal(flow.isVisibleStepUnlocked(5, confirmedImages, 4), true);

const generatedOnly = { ...confirmedImages, 4: 'pending' };
assert.equal(flow.getVisibleStepState(3, generatedOnly), 'pending');

const audioGenerated = {
  ...confirmedImages,
  5: 'completed',
  6: 'completed',
  7: 'in_progress'
};
assert.equal(
  flow.getVisibleStepState(6, audioGenerated, { audioConfirmed: false }),
  'in_progress'
);
assert.equal(
  flow.isVisibleStepUnlocked(8, audioGenerated, 7, { audioConfirmed: false }),
  false
);

const audioConfirmed = { ...audioGenerated, 7: 'completed' };
assert.equal(
  flow.getVisibleStepState(6, audioConfirmed, { audioConfirmed: true }),
  'completed'
);
assert.equal(
  flow.isVisibleStepUnlocked(8, audioConfirmed, 7, { audioConfirmed: true }),
  true
);
assert.equal(
  flow.isVisibleStepUnlocked(8, audioConfirmed, 7, { audioConfirmed: false }),
  false
);

assert.equal(
  flow.calculateVisibleProgress(audioConfirmed, { audioConfirmed: true }),
  83
);
// 步骤 9 启用后不影响必选步骤进度（分母只含必选步骤）
assert.equal(
  flow.calculateVisibleProgress(audioConfirmed, { audioConfirmed: true, digitalHumanEnabled: true }),
  83
);
// 勾画未进入决策(not_started)不计入分母
assert.equal(
  flow.calculateVisibleProgress(audioConfirmed, { audioConfirmed: true, annotationModuleState: 'not_started' }),
  83
);
// 决策完成(confirmed)计入分母:6/7 → 86
assert.equal(
  flow.calculateVisibleProgress(audioConfirmed, { audioConfirmed: true, annotationModuleState: 'confirmed' }),
  86
);
// 明确不添加也算完成决策
assert.equal(
  flow.calculateVisibleProgress(audioConfirmed, { audioConfirmed: true, annotationModuleState: 'no_annotations' }),
  86
);

// 勾画标注:图片已确认即可进入(不要求 AI Mask/音频);图片未确认则锁定
assert.equal(flow.isVisibleStepUnlocked(10, confirmedImages, 4), true);
assert.equal(flow.isVisibleStepUnlocked(10, { ...confirmedImages, 4: 'pending' }, 3), false);
// 音频未确认时也允许进入勾画(有图即可编辑)
assert.equal(flow.isVisibleStepUnlocked(10, audioGenerated, 5), true);

// 可选步骤未启用不得锁死其后的步骤:未启用勾画时数字人/输出不受影响
assert.equal(
  flow.isVisibleStepUnlocked(9, audioConfirmed, 6, { audioConfirmed: true, annotationsEnabled: false, digitalHumanEnabled: false }),
  true
);
assert.equal(
  flow.isVisibleStepUnlocked(8, audioConfirmed, 6, { audioConfirmed: true, annotationsEnabled: false }),
  true
);

const reassignedImages = flow.moveStep3ImageAssignment([
  { slide_id: 'slide_001', asset: 'image-a' },
  { slide_id: 'slide_002', asset: 'image-b' },
  { slide_id: 'slide_003', asset: 'image-c' }
], 2, 0);
assert.deepEqual(
  reassignedImages.map(item => item.slide_id),
  ['slide_001', 'slide_002', 'slide_003'],
  'storyboard slots must remain fixed'
);
assert.deepEqual(
  reassignedImages.map(item => item.asset),
  ['image-c', 'image-a', 'image-b'],
  'only image assignments should move'
);

// ---------------------------------------------------------------------------
// 发行精简版（六步）：发行功能剖面关闭勾画标注与数字人讲解。
// ---------------------------------------------------------------------------

const light = flow.configureVisibleFlow({ digital_human: false, handwritten_annotations: false });
assert.deepEqual(light.VISIBLE_FLOW_STEPS, [1, 2, 3, 5, 6, 8]);
assert.deepEqual(flow.VISIBLE_FLOW_STEPS, [1, 2, 3, 5, 6, 8], 'module-level flow switches with the profile');
assert.deepEqual(flow.displayFlow().map(item => [item.displayNumber, item.step]),
  [[1, 1], [2, 2], [3, 3], [4, 5], [5, 6], [6, 8]]);

// 音频确认后直达作品输出；旧 9/10 项目按音频确认情况回退，不落入不存在的页面。
assert.equal(flow.resolveProjectVisibleStep({ current_step: 7, audio_confirmed: true }), 8);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 7, audio_confirmed: false }), 6);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 10, audio_confirmed: true }), 8);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 10, audio_confirmed: false }), 6);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 9, audio_confirmed: true }), 8);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 9, audio_confirmed: false }), 6);
// 对禁用步骤的直接导航统一落回作品输出。
assert.equal(flow.normalizeVisibleStep(10), 8);
assert.equal(flow.normalizeVisibleStep(9), 8);
// 内部确认步骤映射保持不变。
assert.equal(flow.normalizeVisibleStep(4), 5);
assert.equal(flow.normalizeVisibleStep(7), 6);

// 有效 flow 的下一步：确认音频(6)后是输出(8)。
assert.equal(flow.nextVisibleStep(6), 8);
assert.equal(flow.nextVisibleStep(8), null);

// 进度分母只含本发行版六个必做步骤；全部完成后为 100。
const lightAllDone = { 1: 'completed', 2: 'completed', 3: 'completed', 4: 'completed', 5: 'completed', 6: 'completed', 7: 'completed', 8: 'completed' };
assert.equal(flow.calculateVisibleProgress(lightAllDone, { audioConfirmed: true }), 100);
assert.equal(flow.calculateVisibleProgress(lightAllDone, { audioConfirmed: false }), 83);
// 禁用步骤的状态不得影响精简版进度计算。
assert.equal(
  flow.calculateVisibleProgress(lightAllDone, { audioConfirmed: true, annotationModuleState: 'confirmed', digitalHumanEnabled: true }),
  100
);

// 解锁链：输出步仍要求内部 TTS(7) 完成 + 音频已确认；对禁用步骤的直接
// 导航映射到输出 8，其解锁状态与输出本身一致。
assert.equal(flow.isVisibleStepUnlocked(8, lightAllDone, 6, { audioConfirmed: true }), true);
assert.equal(flow.isVisibleStepUnlocked(8, audioConfirmed, 6, { audioConfirmed: true }), true);
assert.equal(flow.isVisibleStepUnlocked(8, audioGenerated, 6, { audioConfirmed: false }), false);
assert.equal(flow.isVisibleStepUnlocked(10, confirmedImages, 4), false, 'disabled steps fall back to locked output');
assert.equal(
  flow.isVisibleStepUnlocked(9, audioConfirmed, 6, { audioConfirmed: true }),
  flow.isVisibleStepUnlocked(8, audioConfirmed, 6, { audioConfirmed: true }),
  'disabled-step navigation resolves to the output step'
);

// 编辑影响提示不提及本发行版不存在的下游（勾画/数字人）。
const lightImpact = flow.getDownstreamEditImpact(1, 8, { 2: 'completed' }, {});
assert.equal(lightImpact?.includes('勾画'), false);
assert.equal(lightImpact?.includes('数字人'), false);
assert.equal(flow.getDownstreamEditImpact(6, 8, { 8: 'completed' }, {})?.includes('勾画'), false);

// 回到完整版：无参 configure 恢复环境检测的剖面（Node 下即完整版）。
const restored = flow.configureVisibleFlow();
assert.deepEqual(restored.VISIBLE_FLOW_STEPS, [1, 2, 3, 5, 6, 10, 9, 8]);
assert.equal(flow.nextVisibleStep(6), 10);
assert.equal(flow.resolveProjectVisibleStep({ current_step: 7, audio_confirmed: true }), 10);
assert.deepEqual(flow.VISIBLE_FLOW_STEPS, [1, 2, 3, 5, 6, 10, 9, 8]);

console.log('visible flow checks passed');

// ===== HTML 后端流程分派（B03） =====
flow.configureVisibleFlow(undefined, { visualBackend: 'html' });
assert.equal(flow.resolveVisualBackend({ visual_backend: 'html' }), 'html');
assert.equal(flow.resolveVisualBackend({}), 'image');
assert.equal(flow.visibleStepLabel(5), '场景与对象');
assert.equal(flow.visibleStepLabel(3), '视觉素材');
assert.equal(flow.getVisibleStepState(5, {}, { htmlScenesReady: true }), 'completed');
assert.equal(flow.getVisibleStepState(5, {}, { htmlScenesReady: false }), 'pending');
// HTML 路线不要求 AI Mask 产物：状态仍由底层阶段给出，但不再出现 Mask 标签
assert.equal(flow.VISIBLE_FLOW.find(item => item.step === 5).htmlStage, true);
assert.equal(
  flow.calculateVisibleProgress({}, { htmlScenesReady: true }) >
  flow.calculateVisibleProgress({}, { htmlScenesReady: false }),
  true
);
assert.equal(flow.getDownstreamEditImpact(3, 8, { 4: 'completed' })?.includes('Mask'), true);

// 默认（图片路线）行为完全不变
flow.configureVisibleFlow();
assert.equal(flow.visibleStepLabel(5), 'AI Mask 标注');
assert.equal(flow.visibleStepLabel(3), '图片生成');
assert.equal(flow.getVisibleStepState(5, { 5: 'completed' }, {}), 'completed');
assert.equal(flow.getVisibleStepState(5, {}, { htmlScenesReady: true }), 'pending');

console.log('html backend flow checks passed');
