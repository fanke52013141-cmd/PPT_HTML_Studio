"use strict";

const { curve, matrix, imagePlacement } = require("./timeline.cjs");
const { registry } = require("./registry.cjs");

function transform(m, p) {
  return {
    x: m[0] * p.x + m[2] * p.y + m[4],
    y: m[1] * p.x + m[3] * p.y + m[5],
  };
}
function corners(rect, m = [1, 0, 0, 1, 0, 0]) {
  return [
    { x: rect.x, y: rect.y },
    { x: rect.x + rect.width, y: rect.y },
    { x: rect.x + rect.width, y: rect.y + rect.height },
    { x: rect.x, y: rect.y + rect.height },
  ].map((p) => transform(m, p));
}
function bounds(points) {
  const xs = points.map((p) => p.x),
    ys = points.map((p) => p.y);
  return {
    x: Math.min(...xs),
    y: Math.min(...ys),
    width: Math.max(...xs) - Math.min(...xs),
    height: Math.max(...ys) - Math.min(...ys),
  };
}

function textRects(element, stage, width) {
  if (!element.firstChild) return [];
  const range = document.createRange();
  range.selectNodeContents(element);
  const origin = stage.getBoundingClientRect(),
    scale = origin.width / width;
  return [...range.getClientRects()].map((r) => ({
    x: (r.left - origin.left) / scale,
    y: (r.top - origin.top) / scale,
    width: r.width / scale,
    height: r.height / scale,
  }));
}

function geometry(node, state, compiled, element, stage) {
  const common = {
    target: { nodeId: node.id, part: "self" },
    coordinateSpace: "canvas",
    opacity: state.opacity,
  };
  if (node.type === "image") {
    const asset = compiled.assets.get(node.assetRef.id),
      placement = imagePlacement(node, asset),
      m = matrix(node, state, asset);
    const localRect = {
        x: 0,
        y: 0,
        width: node.box.width,
        height: node.box.height,
      },
      polygon = corners(localRect, m);
    const a = asset.alphaBounds,
      visibleRect = {
        x: placement.x + a.x * placement.scale,
        y: placement.y + a.y * placement.scale,
        width: a.width * placement.scale,
        height: a.height * placement.scale,
      };
    const visiblePolygon = corners(visibleRect, m);
    return {
      ...common,
      localRect,
      localToCanvas: m,
      polygons: [polygon],
      rects: [bounds(polygon)],
      resourceRef: node.assetRef,
      anchor: { ...state.position },
      visibleContent: {
        meaning:
          "alphaBounds support rectangle, not pixel mask or semantic part",
        polygons: [visiblePolygon],
        rects: [bounds(visiblePolygon)],
      },
    };
  }
  if (node.type === "text") {
    const rects = textRects(element, stage, compiled.source.canvas.width);
    return {
      ...common,
      localRect: { x: 0, y: 0, width: node.box.width, height: node.box.height },
      localToCanvas: [1, 0, 0, 1, node.box.x, node.box.y],
      polygons: rects.map((r) => corners(r)),
      rects,
      layoutBox: node.box,
      text: state.text,
    };
  }
  if (node.type === "path") {
    const points = compiled.paths.get(node.pathId).points;
    const polyline = Array.from(
      { length: registry.limits.pathSamples + 1 },
      (_, i) =>
        curve(points, (state.progress * i) / registry.limits.pathSamples),
    );
    const r = bounds(points);
    return {
      ...common,
      localRect: r,
      localToCanvas: [1, 0, 0, 1, 0, 0],
      polygons: [corners(r)],
      rects: [r],
      boundsMeaning:
        "control-point hull; conservative, without stroke expansion",
      sampledPolyline: polyline,
      progress: state.progress,
    };
  }
  const r = node.box;
  return {
    ...common,
    localRect: { x: 0, y: 0, width: r.width, height: r.height },
    localToCanvas: [1, 0, 0, 1, r.x, r.y],
    polygons: [corners(r)],
    rects: [r],
    circle: {
      center: { x: r.x + r.width / 2, y: r.y + r.height / 2 },
      radius: Math.max(0, (Math.min(r.width, r.height) - node.strokeWidth) / 2),
    },
  };
}

module.exports = { transform, corners, bounds, textRects, geometry };
