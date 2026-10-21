"use strict";
// Same strict predicates as the renderer; values retain precision for diagnosis.
function capacityEvidence(measured, effectiveLimits) {
  const triggers = [];
  const check = (dimension, actual, limit, tolerance, unit) => {
    if (Number.isFinite(actual) && Number.isFinite(limit) && actual > limit + tolerance)
      triggers.push({ dimension, actual, limit, tolerance, unit });
  };
  check("box_width", measured.width, effectiveLimits.width, 1, "canvas_px");
  check("box_height", measured.height, effectiveLimits.height, 1, "canvas_px");
  check("line_count", measured.lines, effectiveLimits.maxLines, 0, "lines");
  check("scroll_width", measured.scrollWidth, measured.clientWidth, 1, "css_px");
  check("scroll_height", measured.scrollHeight, measured.clientHeight, 1, "css_px");
  check("text_right_overflow", measured.textRight, 0, 1, "css_px");
  check("text_bottom_overflow", measured.textBottom, 0, 1, "css_px");
  check("text_left_overflow", measured.textLeft, 0, 1, "css_px");
  check("text_top_overflow", measured.textTop, 0, 1, "css_px");
  return { triggers, effectiveLimits, tolerancePolicy: "existing-per-predicate/1" };
}
module.exports = { capacityEvidence };
