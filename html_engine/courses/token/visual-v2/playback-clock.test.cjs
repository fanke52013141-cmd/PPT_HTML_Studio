// Exercise the actual player clock functions without browser/file-page access.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, 'player.js'), 'utf8');
function functionSource(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0);
  const end = source.indexOf('\n  function ', start + 1);
  return source.slice(start, end);
}
function setup() {
  const state = { now: 100, frames: [], rendered: [], status: {textContent: ''} };
  const context = vm.createContext({
    state, performance: { now: () => state.now },
    document: {querySelector: () => state.status},
    requestAnimationFrame: fn => (state.frames.push(fn), state.frames.length),
    cancelAnimationFrame() {},
    renderAtCourse(t) { assert.ok(Number.isFinite(t) && t >= 0 && t <= 79000, `Invalid playback time: ${t}`); state.rendered.push(t); context.time = t; },
    setMode() { context.pause(); }, mode: { value: 'actual' },
    ready: true, playing: false, raf: 0, current: 0, time: 15999,
    prefixes: [0, 16000, 31000, 47000, 65000, 79000], total: 79000, last: 0, playLimit: 0,
  });
  vm.runInContext([functionSource('pause'), functionSource('tick'), functionSource('play')].join('\n'), context);
  return {state, context};
}
{
  const {state, context} = setup();
  context.play(true);
  context.tick(95); // Same rendering cycle: frame timestamp predates the click.
  assert.equal(context.time, 0);
  context.tick(112);
  assert.equal(context.time, 12);
  assert.ok(context.playing);
  context.pause(); const t = context.time; context.tick(200);
  assert.equal(context.time, t);
}
{
  const {context} = setup();
  context.current = 2;
  context.play(false);
  assert.equal(context.time, 31000);
  context.tick(94); assert.equal(context.time, 31000);
  context.tick(116); assert.equal(context.time, 31016);
  context.tick(20000); assert.equal(context.time, 46999); assert.equal(context.playing, false);
}
{
  const {context} = setup();
  context.play(true); context.tick(80100);
  assert.equal(context.time, 79000); assert.equal(context.playing, false);
}
{
  const {state, context} = setup();
  context.ready = false; context.play(true);
  assert.equal(context.playing, false);
  assert.match(state.status.textContent, /尚未准备/);
  context.ready = true; context.play(true);
  context.renderAtCourse = () => {throw new Error('test render failure');};
  context.tick(116);
  assert.equal(context.playing, false);
  assert.match(state.status.textContent, /播放失败：test render failure/);
}
console.log('Playback clock: early frame, advancement, pause, scene/course endpoints, readiness and failure feedback passed.');
