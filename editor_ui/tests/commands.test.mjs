import { test } from 'node:test';
import assert from 'node:assert/strict';
import { authorDelta, presentationOperation, bindingEdit, applyPresentationOperations, timelineEdit } from '../src/commands.mjs';

for (const scale of [0.5, 1, 1.5, 2]) test(`author delta at ${scale}x ignores viewport origin/scroll`, () => {
  const delta = authorDelta(13 * scale, -21 * scale,
    { width: 1600 * scale, height: 900 * scale, x: -84, y: 400 }, { width: 1600, height: 900 });
  assert.deepEqual(delta, { x: 13, y: -21 });
  assert.deepEqual(presentationOperation({ id: 'card', type: 'card', presentation: { offsetX: 7, offsetY: 30 } }, delta),
    { kind: 'set_presentation', targetId: 'card', values: { offsetX: 20, offsetY: 9 } });
});
test('resize uses author dimensions and preserves other author properties', () => {
  const node = { id: 'text', type: 'text', presentation: { typography: { text: { fontSizePx: 32 } } } };
  const before = structuredClone(node);
  assert.deepEqual(presentationOperation(node, { x: 0, y: 0 }, { width: 200, height: 120 }).values,
    { offsetX: 0, offsetY: 0, width: 200, height: 120 });
  assert.deepEqual(node, before);
});
test('invalid geometry fails closed without clamping', () => {
  for (const value of [NaN, Infinity, 0, -1]) assert.throws(() =>
    authorDelta(1, 1, { width: value, height: 900 }, { width: 1600, height: 900 }));
  assert.throws(() => presentationOperation({ id: 'a', type: 'annotation' }, { x: 0, y: 0 }));
  assert.throws(() => presentationOperation({ id: 'a', type: 'card' }, { x: 401, y: 0 }));
  assert.throws(() => presentationOperation({ id: 'a', type: 'card' }, { x: 0, y: 0 }, { width: 10, height: 40 }));
});
const action = { actionId: 'a1', targetId: 'header', type: 'enter', startMs: 0, durationMs: 800 };
const binding = { beatId: 'b1', edge: 'end', offsetMs: -1000, sourceHash: 'preserved' };
const input = { action, binding, window: { beatId: 'b1', startMs: 0, endMs: 6000 },
  startMs: 5300, endMs: 6000, effectiveStartMs: 5000 };
test('timeline edits relative binding and duration, preserving identity and source hash', () => {
  const before = structuredClone(input), result = bindingEdit(input);
  assert.deepEqual(result.binding, { ...binding, offsetMs: -700 });
  assert.deepEqual(result.action, { ...action, durationMs: 700 });
  assert.deepEqual(input, before);
});
test('cross-beat, short duration, missing binding and nonfinite times are rejected', () => {
  for (const patch of [{ startMs: -1 }, { endMs: 6001 }, { endMs: 5301 },
    { startMs: NaN }, { effectiveStartMs: Infinity }, { binding: null },
    { binding: { ...binding, beatId: 'b2' } },
    { window: { ...input.window, endMs: NaN } }]) assert.throws(() => bindingEdit({ ...input, ...patch }));
});

const scene = { version: '0.6.0', initialVisibleIds: ['card-1'], nodes: [
  { id: 'card-1', type: 'card', slot: 'c1' }, { id: 'card-2', type: 'card', slot: 'c2' },
  { id: 'annotation', type: 'annotation', slot: 'a1' }],
  motion: [{ actionId: 'a1', targetId: 'card-2', type: 'enter', startMs: 800, durationMs: 600 }],
  beats: [{ text: '原讲稿' }] };
const operation = (id, values) => ({ kind: 'set_presentation', targetId: id, values });
test('timeline move preserves clipped author duration; resize changes duration and keeps identities', () => {
  const source = structuredClone(scene); source.motion[0].durationMs = 5000;
  const links = { version: '0.2.0', sourceBeats: [{ id: 'b1', spoken_text_sha256: 'keep' }], actions: { a1: { beatId: 'b1', edge: 'end', offsetMs: -5000 } } };
  const timing = { beats: [{ beatId: 'b1', startMs: 0, endMs: 6000 }], actions: [{ id: 'a1', effectiveStartMs: 1000, effectiveDurationMs: 800, editable: true }] };
  const before = structuredClone({ source, links });
  const moved = timelineEdit(source, links, timing, 'a1', 1300, 2100);
  assert.equal(moved.scene.motion[0].durationMs, 5000); assert.equal(moved.binding.actions.a1.offsetMs, -4700);
  const resized = timelineEdit(source, links, timing, 'a1', 900, 2100, true);
  assert.equal(resized.scene.motion[0].durationMs, 1200); assert.equal(resized.binding.actions.a1.offsetMs, -5100);
  assert.deepEqual(resized.binding.sourceBeats, links.sourceBeats);
  assert.deepEqual({ source, links }, before);
  assert.throws(() => timelineEdit(source, links, timing, 'a1', 5900, 6500));
  assert.throws(() => timelineEdit(source, links, null, 'a1', 1000, 1800));
  const withNext = { ...timing, actions: [...timing.actions.map(a => ({ ...a, targetId: 'card-2' })),
    { id: 'a2', targetId: 'card-2', effectiveStartMs: 2000 }] };
  assert.throws(() => timelineEdit(source, links, withNext, 'a1', 2100, 2900), /动作顺序/);
});
test('group transaction changes only presentation and preserves semantic identities', () => {
  const before = structuredClone(scene);
  const next = applyPresentationOperations(scene, [operation('card-1', { offsetX: 15 }), operation('card-2', { offsetY: 12 })]);
  assert.equal(next.version, '0.6.0'); assert.deepEqual(next.motion, scene.motion);
  assert.deepEqual(next.initialVisibleIds, scene.initialVisibleIds);
  assert.deepEqual(next.beats, scene.beats); assert.deepEqual(scene, before);
  assert.equal(next.nodes[0].presentation.offsetX, 15); assert.equal(next.nodes[1].presentation.offsetY, 12);
});
test('one rejected member rejects the entire group without changing input', () => {
  const before = structuredClone(scene);
  for (const bad of [operation('card-2', { width: 5 }), operation('annotation', { offsetX: 1 }),
    operation('gone', { offsetX: 1 }), operation('card-2', { rotate: 12 })])
    assert.throws(() => applyPresentationOperations(scene, [operation('card-1', { offsetX: 15 }), bad]));
  assert.deepEqual(scene, before);
});
test('no-op preserves legacy version, editing upgrades only old formats', () => {
  const old = { ...scene, version: '0.3.0' };
  assert.deepEqual(applyPresentationOperations(old, [operation('card-1', { offsetX: 0, offsetY: 0 })]), old);
  assert.equal(applyPresentationOperations(old, [operation('card-1', { width: 200 })]).version, '0.5.0');
  assert.throws(() => applyPresentationOperations(scene, [operation('card-1', { width: 200 }), operation('card-1', { width: 300 })]));
  assert.throws(() => applyPresentationOperations(scene, []));
  assert.throws(() => applyPresentationOperations(scene, Array.from({ length: 21 }, () => operation('card-1', { offsetX: 1 }))));
});
