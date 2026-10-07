"use strict";
// Conservative engineering warning only. Transparent support boxes can overlap harmlessly.
function diagnoseOverlap(a, b) {
  if (a.opacity <= 0 || b.opacity <= 0) return [];
  const ar = a.visibleContent?.rects || a.rects,
    br = b.visibleContent?.rects || b.rects;
  let area = 0;
  for (const x of ar)
    for (const y of br)
      area +=
        Math.max(
          0,
          Math.min(x.x + x.width, y.x + y.width) - Math.max(x.x, y.x),
        ) *
        Math.max(
          0,
          Math.min(x.y + x.height, y.y + y.height) - Math.max(x.y, y.y),
        );
  return area > 0
    ? [
        {
          code: "POSSIBLE_FOREGROUND_OCCLUSION",
          targets: [a.target, b.target],
          area,
          meaning:
            "visible support boxes; confirm visually, not pixel occlusion",
        },
      ]
    : [];
}
module.exports = { diagnoseOverlap };
