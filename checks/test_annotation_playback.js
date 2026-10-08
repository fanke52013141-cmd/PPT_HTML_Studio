// annotation_playback 共享采样单测:同帧一致性、弧长推进、暂停/seek、
// 退出淡出、无随机性、时间量化。
const assert = require('node:assert/strict');
const playback = require('../static/annotation_playback.js');

const EVENT = {
  annotation_id: 'ann_001',
  start_sec: 1.0,
  draw_end_sec: 2.0,
  hold_end_sec: 4.0,
  exit_end_sec: 4.3,
  style: { color: '#F46A38', opacity: 0.85, width: 5, padding: 8, seed: 1382 },
  strokes: [
    { kind: 'polyline', points: [[100, 200], [300, 200], [300, 260], [100, 260], [100, 200]] },
  ],
};

// ------------------------------------------------------------ 帧量化

assert.equal(playback.quantize(1.011), 1.0);
assert.equal(playback.quantize(1.049), 1.0333333333333333); // 帧 31 起点
assert.equal(playback.quantize(-5), 0);

// ------------------------------------------------------------ 阶段采样

// 起笔前隐藏
assert.deepEqual(playback.sampleEvent(EVENT, 0.99), { phase: 'hidden', pathProgress: 0, opacityScale: 0, drawProgress: 0 });
// 半程:绘制进度 0.5
const mid = playback.sampleEvent(EVENT, 1.5);
assert.equal(mid.phase, 'drawing');
assert.ok(Math.abs(mid.pathProgress - 0.5) < 0.001);
// hold:满进度
assert.deepEqual(playback.sampleEvent(EVENT, 3.0), { phase: 'hold', pathProgress: 1, opacityScale: 1, drawProgress: 1 });
// exit:线性淡出
const exit = playback.sampleEvent(EVENT, 4.15);
assert.equal(exit.phase, 'exit');
// 帧量化后时间落在帧起点:fade = 1 - (q(4.15)-4.0)/0.3
assert.ok(Math.abs(exit.opacityScale - 0.5556) < 0.01);
// 结束后隐藏
assert.equal(playback.sampleEvent(EVENT, 4.31).phase, 'hidden');

// 同帧一致性:同一帧内任意时刻采样相同(浏览器/Remotion 同帧像素一致)
const a = playback.sampleEvent(EVENT, playback.quantize(1.234));
const b = playback.sampleEvent(EVENT, playback.quantize(1.26)); // 均落在帧 37
assert.equal(a.phase, b.phase);
assert.equal(a.pathProgress, b.pathProgress);

// 暂停/seek 无状态依赖:任意顺序、重复采样结果一致(纯函数)
assert.deepEqual(playback.sampleEvent(EVENT, 2.0), playback.sampleEvent(EVENT, 2.0));
assert.deepEqual(playback.sampleEvent(EVENT, 3.0), playback.sampleEvent(EVENT, 0.0 + 3.0));

// ------------------------------------------------------------ 弧长推进

const line = [[0, 0], [100, 0]];
assert.equal(playback.polylineTotalLength(line), 100);
// progress 0.5 → 弧长 50 处(不是点数一半)
const half = playback.polylinePathUpTo(line, 0.5);
assert.ok(half.includes('L 50 0'), half);
// 密集采样同弧长(推进按弧长而非点数)
const dense = [[0, 0], [25, 0], [50, 0], [75, 0], [100, 0]];
assert.equal(Math.abs(playback.polylineTotalLength(dense) - 100) < 1e-9, true);
const denseHalf = playback.polylinePathUpTo(dense, 0.5);
assert.ok(denseHalf.includes('L 50 0'), denseHalf);
// 越界钳制
assert.equal(playback.polylinePathUpTo(line, 1.5), playback.polylinePathUpTo(line, 1));
assert.equal(playback.polylinePathUpTo(line, -1), '');
assert.equal(playback.polylinePathUpTo([], 0.5), '');

// ------------------------------------------------------------ 场景渲染

const sceneDrawing = playback.renderScene([EVENT], 1.5);
assert.equal(sceneDrawing.length, 1);
assert.equal(sceneDrawing[0].kind, 'polyline');
assert.equal(sceneDrawing[0].opacity, 0.85); // hold 浓度 = 样式浓度
const sceneExit = playback.renderScene([EVENT], 4.15);
assert.ok(sceneExit[0].opacity < 0.85);
const sceneHidden = playback.renderScene([EVENT], 0.5);
assert.equal(sceneHidden.length, 0);

// highlighter → rect 覆盖
const rectEvent = {
  ...EVENT,
  strokes: [{ kind: 'rect', x: 10, y: 20, width: 30, height: 40 }],
};
const rectScene = playback.renderScene([rectEvent], 3.0);
assert.equal(rectScene[0].kind, 'rect');
// v2:浓度合成移到消费端(fill-opacity),采样输出基础浓度
assert.ok(Math.abs(rectScene[0].opacity - 0.85) < 0.001);

// 无随机性:两次渲染同一时刻结果一致
assert.deepEqual(playback.renderScene([EVENT], 1.7), playback.renderScene([EVENT], 1.7));

console.log('annotation playback checks passed');

// Future strokes remain absent, then reach their complete final raster.
const multi = {...EVENT, strokes: [
  {kind:'path',points:[[0,0],[100,0]],draw_start_offset_sec:0,draw_end_offset_sec:.3},
  {kind:'path',points:[[0,0],[0,100]],draw_start_offset_sec:.4,draw_end_offset_sec:1}
]};
assert.equal(playback.rasterFrameIndex(multi,multi.strokes[1],1,.2,18),-1);
assert.equal(playback.rasterFrameIndex(multi,multi.strokes[1],1,1,18),17);
assert.equal(playback.sampleEvent({...EVENT,start_sec:1.011},1.0).phase,'hidden');
