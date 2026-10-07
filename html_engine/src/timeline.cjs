"use strict";

const clamp = (p) => Math.max(0, Math.min(1, p));
function ease(kind, p) {
  p = clamp(p);
  if (kind === "smoothstep") return p * p * (3 - 2 * p);
  if (kind === "ease-out-cubic") return 1 - (1 - p) ** 3;
  return p;
}

function curve(points, u) {
  const v = 1 - u;
  return {
    x:
      v ** 3 * points[0].x +
      3 * v * v * u * points[1].x +
      3 * v * u * u * points[2].x +
      u ** 3 * points[3].x,
    y:
      v ** 3 * points[0].y +
      3 * v * v * u * points[1].y +
      3 * v * u * u * points[2].y +
      u ** 3 * points[3].y,
  };
}

function tangent(points, u, orientation, fallback) {
  const v = 1 - u;
  const dx =
    3 * v * v * (points[1].x - points[0].x) +
    6 * v * u * (points[2].x - points[1].x) +
    3 * u * u * (points[3].x - points[2].x);
  const dy =
    3 * v * v * (points[1].y - points[0].y) +
    6 * v * u * (points[2].y - points[1].y) +
    3 * u * u * (points[3].y - points[2].y);
  if (Math.hypot(dx, dy) < 1e-9) return fallback;
  return Math.max(
    orientation.minDeg,
    Math.min(orientation.maxDeg, (Math.atan2(dy, dx) * 180) / Math.PI),
  );
}

function progress(action, timeMs) {
  return action.startMs === action.endMs
    ? 1
    : ease(
        action.easing,
        (timeMs - action.startMs) / (action.endMs - action.startMs),
      );
}

function imagePlacement(node, asset) {
  const scale = Math.min(
    node.box.width / asset.intrinsic.width,
    node.box.height / asset.intrinsic.height,
  );
  const width = asset.intrinsic.width * scale,
    height = asset.intrinsic.height * scale;
  const x = (node.box.width - width) / 2,
    y = (node.box.height - height) / 2;
  const anchor = asset.anchors.find((a) => a.id === node.anchorId);
  return {
    scale,
    x,
    y,
    width,
    height,
    anchor: { x: x + anchor.x * width, y: y + anchor.y * height },
  };
}

function matrix(node, state, asset) {
  const placement = imagePlacement(node, asset);
  const rad = (state.rotationDeg * Math.PI) / 180,
    c = Math.cos(rad),
    s = Math.sin(rad);
  const a = placement.anchor;
  return [
    c,
    s,
    -s,
    c,
    state.position.x - c * a.x + s * a.y,
    state.position.y - s * a.x - c * a.y,
  ];
}

function activeBeat(scene, t) {
  return scene.beats.find(
    (b) =>
      b.startMs <= t &&
      (t < b.endMs || (t === scene.durationMs && b.endMs === t)),
  );
}

function channels(action) {
  if (action.type === "opacity") return ["opacity"];
  if (action.type === "rotate") return ["rotation"];
  if (action.type === "path-progress") return ["progress"];
  return action.orientation.kind === "tangent"
    ? ["position", "rotation"]
    : ["position"];
}

function evaluate(compiled, timeMs) {
  const scene = compiled.source;
  if (!Number.isFinite(timeMs) || timeMs < 0 || timeMs > scene.durationMs)
    throw new RangeError("timeMs must be finite and inside scene duration");
  const beat = activeBeat(scene, timeMs);
  const nodes = {};
  for (const node of compiled.nodes) {
    const state = { opacity: node.initialOpacity };
    if (node.type === "text")
      state.text =
        node.content.kind === "static"
          ? node.content.text
          : beat?.screenText || "";
    if (node.type === "path") state.progress = node.initialProgress;
    if (node.type === "image") {
      const p = imagePlacement(node, compiled.assets.get(node.assetRef.id));
      state.position = {
        x: node.box.x + p.anchor.x,
        y: node.box.y + p.anchor.y,
      };
      state.rotationDeg = node.rotationDeg;
    }
    nodes[node.id] = state;
  }
  // A sorted action updates only its declared channel. Later actions replace held end values.
  for (const action of compiled.actions) {
    if (timeMs < action.startMs) continue;
    const state = nodes[action.target.nodeId],
      p = progress(action, timeMs);
    if (action.type === "opacity")
      state.opacity = action.from + (action.to - action.from) * p;
    if (action.type === "rotate")
      state.rotationDeg = action.fromDeg + (action.toDeg - action.fromDeg) * p;
    if (action.type === "path-progress")
      state.progress = action.from + (action.to - action.from) * p;
    if (action.type === "move-path") {
      const points = compiled.paths.get(action.pathId).points;
      state.position = curve(points, p);
      if (action.orientation.kind === "tangent")
        state.rotationDeg = tangent(
          points,
          p,
          action.orientation,
          compiled.nodeMap.get(action.target.nodeId).rotationDeg,
        );
    }
  }
  return { timeMs, beatId: beat?.id || null, nodes };
}

module.exports = {
  ease,
  curve,
  tangent,
  progress,
  channels,
  evaluate,
  imagePlacement,
  matrix,
};
