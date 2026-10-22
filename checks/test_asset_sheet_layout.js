'use strict';
const assert = require('assert');
const { plan, dimensionsFor } = require('../static/asset_sheet_layout.js');

function overlaps(a, b) {
  const [ax, ay, aw, ah] = a;
  const [bx, by, bw, bh] = b;
  return ax < bx + bw && bx < ax + aw && ay < by + bh && by < ay + ah;
}

function inside(rect, width, height) {
  const [x, y, w, h] = rect;
  return x >= 0 && y >= 0 && w > 0 && h > 0 && x + w <= width && y + h <= height;
}

for (const orientation of ['landscape', 'portrait', 'square']) {
  const [width, height] = dimensionsFor(orientation);
  for (let count = 1; count <= 4; count += 1) {
    const sheet = plan(Array.from({ length: count }, (_, i) => `需求${i + 1}`), {
      orientation, stamp: 'stamp',
    });
    assert.strictEqual(sheet.width, width);
    assert.strictEqual(sheet.height, height);
    assert.strictEqual(sheet.slots.length, count);
    for (const slot of sheet.slots) {
      assert.ok(inside(slot.rect, width, height), `${orientation}/${count} slot outside`);
      assert.strictEqual(slot.method, 'source_alpha');
      assert.ok(slot.need.startsWith('需求'));
    }
    for (let i = 0; i < sheet.slots.length; i += 1) {
      for (let j = i + 1; j < sheet.slots.length; j += 1) {
        assert.ok(!overlaps(sheet.slots[i].rect, sheet.slots[j].rect), 'slots overlap');
      }
    }
    if (count === 4 && orientation === 'landscape') {
      // 16:9 sheet, 2x2 layout: cells stay wide rather than turning into blades.
      const [x, y, w, h] = sheet.slots[0].rect;
      assert.ok(w > h, 'landscape cells should stay wider than tall');
      assert.ok(x > 0 && y > 0, 'outer margin is required');
    }
  }
}

const two = plan(['a', 'b'], { orientation: 'portrait', stamp: 'stamp' });
assert.strictEqual(two.slots.length, 2);
assert.ok(two.slots[1].rect[1] >= two.slots[0].rect[1] + two.slots[0].rect[3], 'portrait two-up must be vertical');

const cleanup = plan(['a'], { orientation: 'square', stamp: 'stamp', cleanup: true });
assert.deepStrictEqual(cleanup.slots[0].alpha_cleanup, {
  threshold: 1, guard_radius: 2, max_removed_fraction: 0.02,
});

assert.throws(() => plan([]), /1至4/);
assert.throws(() => plan(['a', 'b', 'c', 'd', 'e']), /1至4/);
assert.throws(() => plan(['']), /1至1000/);
console.log('asset sheet layout ok');
