// 勾画标注前端纯逻辑测试:UTF-16/码点换算、消歧、几何、撤销栈、操作构造、
// 冲突分类。被测模块 annotations_core.js(UMD,可在 Node 侧 require)。
const assert = require('node:assert/strict');
const core = require('../static/annotations_core.js');

// ------------------------------------------------------------ 文本索引

const MIXED = '开始👨‍👩‍👧报名9月30日截止';
assert.equal(core.utf16LengthToCodepointCount(MIXED, MIXED.length), 16);
assert.equal(MIXED.length, 19); // UTF-16 码元数多于码点数(emoji 家族)
assert.equal(core.codepointSlice(MIXED, 9, 14), '9月30日');
assert.equal(core.codepointIndexToUtf16Index(MIXED, 9), 12);
assert.equal(core.utf16IndexToCodepointIndex(MIXED, 12), 9);
// 双向换算往返一致
for (let cp = 0; cp <= 16; cp += 1) {
  const utf16 = core.codepointIndexToUtf16Index(MIXED, cp);
  assert.equal(core.utf16IndexToCodepointIndex(MIXED, utf16), cp);
}
// 代理对中间位置按所属码点钳制,不产生半个字符
assert.equal(core.utf16IndexToCodepointIndex(MIXED, 3), 2);  // 👨 的低代理位 → 码点 2
assert.equal(core.utf16IndexToCodepointIndex(MIXED, 6), 4);  // 👩 的低代理位 → 码点 4
assert.equal(core.utf16IndexToCodepointIndex(MIXED, 5), 4);  // 👩 的起始位 → 码点 4

// 出现次序消歧:同词多处
assert.equal(core.occurrenceIndexOf('aXbXc', 'X', 1), 1);
assert.equal(core.occurrenceIndexOf('aXbXc', 'X', 3), 2);
assert.equal(core.occurrenceIndexOf('aXbXc', 'Y', 1), 0);

// buildAnchor:UTF-16 选区 → 码点范围 + quote + 上下文
const anchor = core.buildAnchor('slide_001_beat_001', MIXED, 12, 17);
assert.equal(anchor.beat_id, 'slide_001_beat_001');
assert.deepEqual(anchor.range, [9, 14]);
assert.equal(anchor.quote, '9月30日');
assert.equal(anchor.occurrence, 1);
assert.ok(anchor.context_before.length > 0 && anchor.context_after.length > 0);

// ------------------------------------------------------------ 几何

assert.deepEqual(
  core.rectangleToPolygon({ x: 100.4, y: 200.6 }, { x: 400.2, y: 260 }, { width: 1920, height: 1080 }),
  [[100, 201], [400, 201], [400, 260], [100, 260]]
);
// 反向拖拽同样规范化
assert.deepEqual(
  core.rectangleToPolygon({ x: 400, y: 260 }, { x: 100, y: 200 }, { width: 1920, height: 1080 }),
  [[100, 200], [400, 200], [400, 260], [100, 260]]
);
// 超出画布夹取
const clamped = core.rectangleToPolygon({ x: -50, y: -50 }, { x: 3000, y: 2000 }, { width: 1920, height: 1080 });
assert.equal(clamped[2][0], 1920);
assert.equal(clamped[2][1], 1080);
// 过小选区返回 null
assert.equal(core.rectangleToPolygon({ x: 10, y: 10 }, { x: 10.4, y: 10.4 }, { width: 1920, height: 1080 }), null);

const bounds = core.polygonBounds([[[10, 20], [30, 20], [30, 60], [10, 60]], [[100, 200], [150, 200], [150, 240], [100, 240]]]);
assert.deepEqual(bounds, { left: 10, top: 20, width: 140, height: 220 });
assert.equal(core.polygonBounds([]), null);

assert.equal(core.pointInPolygon({ x: 20, y: 30 }, [[10, 20], [30, 20], [30, 60], [10, 60]]), true);
assert.equal(core.pointInPolygon({ x: 31, y: 30 }, [[10, 20], [30, 20], [30, 60], [10, 60]]), false);

// ------------------------------------------------------------ 撤销/重做

const history = core.createPageHistory(3);
assert.equal(history.canUndo(), false);
history.push([{ id: 'a' }]);
history.push([{ id: 'a' }, { id: 'b' }]);
assert.equal(history.canUndo(), true);
const undone = history.undo([{ id: 'a' }, { id: 'b' }, { id: 'c' }]);
assert.deepEqual(undone, [{ id: 'a' }, { id: 'b' }]);
const redone = history.redo([{ id: 'a' }, { id: 'b' }]);
assert.deepEqual(redone, [{ id: 'a' }, { id: 'b' }, { id: 'c' }]);
// 深拷贝:撤销后修改当前快照不影响栈内历史
const snapshot = [{ id: 'a', nested: { v: 1 } }];
history.push(snapshot);
snapshot[0].nested.v = 99;
assert.deepEqual(history.undo([]), [{ id: 'a', nested: { v: 1 } }]);
// 上限淘汰最老记录
const bounded = core.createPageHistory(2);
bounded.push([{ id: 1 }]);
bounded.push([{ id: 2 }]);
bounded.push([{ id: 3 }]);
assert.deepEqual(bounded.undo([{ id: 4 }]), [{ id: 3 }]);
assert.deepEqual(bounded.undo([{ id: 3 }]), [{ id: 2 }]);
assert.equal(bounded.canUndo(), false);

// ------------------------------------------------------------ 操作构造

const addOp = core.buildAddOperation({ target: core.buildRegionTarget([[0, 0], [10, 0], [10, 10], [0, 10]]), style: { type: 'ellipse' } });
assert.equal(addOp.op, 'add');
assert.equal(addOp.item.target.kind, 'region');
assert.deepEqual(addOp.item.target.polygons, [[[0, 0], [10, 0], [10, 10], [0, 10]]]);

const updateOp = core.buildUpdateOperation('ann_001', { style: { color: '#00AA00' } });
assert.deepEqual(updateOp, { op: 'update', annotation_id: 'ann_001', patch: { style: { color: '#00AA00' } } });
assert.deepEqual(core.buildDeleteOperation('ann_002'), { op: 'delete', annotation_id: 'ann_002' });

const textTarget = core.buildTextTarget({ token_id: 'token_07', text: '9月30日', layout_revision: 3, granularity: 'word' }, [[[800, 400], [960, 400], [960, 445], [800, 445]]]);
assert.equal(textTarget.kind, 'text');
assert.deepEqual(textTarget.token_ids, ['token_07']);
assert.equal(textTarget.quote, '9月30日');

// ------------------------------------------------------------ 展示与浓度

assert.equal(core.annotationCardLabel({ style: { type: 'ellipse' }, status: { content: 'draft' } }, 2), '03 · 手写圈 · 待确认');
assert.equal(core.annotationCardLabel({ style: { type: 'highlighter' }, status: { content: 'confirmed' } }, 0), '01 · 荧光笔 · 已确认');
assert.equal(core.opacityToPercent(0.85), 85);
assert.equal(core.opacityToPercent(2), 100);
assert.equal(core.percentToOpacity(85), 0.85);
assert.equal(core.percentToOpacity(120), 1);

// ------------------------------------------------------------ 冲突分类

assert.deepEqual(
  core.classifyPatchFailure(409, { detail: { code: 'revision_conflict', current_revision: 7 } }),
  { kind: 'revision_conflict', currentRevision: 7, message: '页面已被其他窗口修改,请重载后重试。' }
);
const validation = core.classifyPatchFailure(422, { detail: { code: 'validation_failed', issues: [{ path: 'operations[0].item.anchor.quote', code: 'quote_mismatch', message: '锚点文本与讲稿码点切片不一致' }] } });
assert.equal(validation.kind, 'validation_failed');
assert.equal(validation.issues[0].code, 'quote_mismatch');
assert.equal(core.classifyPatchFailure(500, {}).kind, 'error');

console.log('annotation workspace core checks passed');
