"use strict";
const assert = require("node:assert/strict");
const { capacityEvidence } = require("../capacity.cjs");
// Equal DOM scroll/client dimensions do not imply the external slot fits.
const box = capacityEvidence({ width: 100, height: 75.125,
  scrollWidth: 100, clientWidth: 100, scrollHeight: 75, clientHeight: 75,
  lines: 2 }, { width: 100, height: 48, maxLines: 3 });
assert.deepEqual(box.triggers, [{ dimension: "box_height", actual: 75.125,
  limit: 48, tolerance: 1, unit: "canvas_px" }]);
assert.equal(box.effectiveLimits.height, 48);
const lines = capacityEvidence({width: 100, height: 48, lines: 3}, {width: 100, height: 48, maxLines: 2});
assert.equal(lines.triggers[0].dimension, "line_count");
assert.equal(capacityEvidence({width:101, height:49}, {width:100,height:48}).triggers.length, 0);
assert.equal(capacityEvidence({width:101.0001}, {width:100}).triggers[0].actual, 101.0001);
const scroll = capacityEvidence({scrollHeight:80, clientHeight:48}, {width:100});
assert.equal(scroll.triggers[0].dimension, "scroll_height");
assert.equal(scroll.triggers[0].unit, "css_px");
assert.equal(capacityEvidence({textRight:1.01,textBottom:2}, {}).triggers.length, 2);
console.log("capacity diagnostics: passed (slot, lines, scroll, range, tolerance, precision)");
