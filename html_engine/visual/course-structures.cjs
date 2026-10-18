"use strict";
// Shared data validation and stateless geometry; no course-specific content.
function validateStructures(scene, layout, template, fail) {
  const nodes = new Map(scene.nodes.map((n) => [n.id, n]));
  for (const n of scene.nodes) {
    if (n.type === "chart") {
      if (
        !(n.max > n.min) ||
        n.points.some((p, i) => i && p.x <= n.points[i - 1].x)
      )
        fail("INVALID_CHART", n.id, "Range and ordered x required");
      if (n.plateau) {
        const [a, b] = n.plateau;
        if (
          a >= b ||
          b >= n.points.length ||
          n.points.slice(a, b + 1).some((p) => p.y !== n.points[a].y)
        )
          fail(
            "INVALID_CHART_PLATEAU",
            n.id,
            "Declared plateau must be horizontal",
          );
      }
      const box = layout.slots[n.slot].box;
      if (box.width < 440 || box.height < 280)
        fail("CHART_CAPACITY", n.id, "Chart minimum 440x280");
    }
    if (n.type !== "arrow") continue;
    if (template?.relationPolicy === "explicit" && !n.from)
      fail("RELATION_ENDPOINT_REQUIRED", n.id, "Explicit relation template");
    if (!n.from) continue;
    if (n.presentation)
      fail(
        "RELATION_GEOMETRY_OWNED",
        n.id,
        "Endpoints own geometry; no presentation override",
      );
    const own = layout.slots[n.slot].box;
    if (own.x !== 0 || own.y !== 0 || own.width !== 1600 || own.height !== 800)
      fail("RELATION_COORDINATES", n.id, "Full content coordinates required");
    for (const e of [n.from, n.to]) {
      const t = nodes.get(e.objectId);
      if (!t || ["arrow", "annotation"].includes(t.type) || t.id === n.id)
        fail(
          "INVALID_RELATION_ENDPOINT",
          n.id,
          "Unknown or recursive endpoint",
        );
      if (e.anchorId && t.type !== "image")
        fail("INVALID_RELATION_ENDPOINT", n.id, "Only image anchors supported");
      if (e.anchorId && t.anchorId !== e.anchorId)
        fail(
          "INVALID_RELATION_ENDPOINT",
          n.id,
          "Anchor must match declared image focus",
        );
    }
    if (
      n.from.objectId === n.to.objectId &&
      ((n.from.anchorId && n.from.anchorId === n.to.anchorId) ||
        (n.from.point &&
          n.to.point &&
          n.from.point.x === n.to.point.x &&
          n.from.point.y === n.to.point.y))
    )
      fail("INVALID_RELATION_ENDPOINT", n.id, "Zero length relation");
    for (const a of scene.motion.filter((a) => a.targetId === n.id))
      if (a.type !== "enter" || a.offsetX || a.offsetY)
        fail(
          "RELATION_GEOMETRY_OWNED",
          n.id,
          "Relation only supports zero-offset enter",
        );
  }
}
function endpoint(e, scene, layout, states, geometry) {
  if (e.anchorId) return geometry[e.objectId].anchors[e.anchorId];
  const n = scene.nodes.find((n) => n.id === e.objectId),
    b = layout.slots[n.slot].box,
    s = states.get(n.id);
  return {
    x: b.x + b.width * e.point.x + s.x,
    y: b.y + b.height * e.point.y + s.y,
  };
}
function drawRelation(svg, node, scene, layout, states, geometry, progress) {
  const a = endpoint(node.from, scene, layout, states, geometry),
    b = endpoint(node.to, scene, layout, states, geometry);
  const x = a.x + (b.x - a.x) * progress,
    y = a.y + (b.y - a.y) * progress;
  let d = `M ${a.x} ${a.y} L ${x} ${y}`;
  const l = Math.hypot(b.x - a.x, b.y - a.y);
  if (node.head !== false && l > 1 && progress > 0.99) {
    const ux = (b.x - a.x) / l,
      uy = (b.y - a.y) / l;
    d += ` M ${x - ux * 12 - uy * 5} ${y - uy * 12 + ux * 5} L ${x} ${y} L ${x - ux * 12 + uy * 5} ${y - uy * 12 - ux * 5}`;
  }
  svg.firstChild.setAttribute("d", d);
  svg.firstChild.setAttribute(
    "stroke-dasharray",
    node.lineStyle === "dashed" ? "6 5" : "none",
  );
  return { from: a, to: b };
}
function chartElements(el, node, box, theme, textNodes) {
  const ns = "http://www.w3.org/2000/svg",
    svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${box.width} ${box.height}`);
  svg.setAttribute("width", box.width);
  svg.setAttribute("height", box.height);
  const left = 90,
    top = 52,
    right = box.width - 28,
    bottom = box.height - 70;
  function path(d, color, width) {
    const p = document.createElementNS(ns, "path");
    for (const [k, v] of Object.entries({
      d,
      fill: "none",
      stroke: color,
      "stroke-width": width,
    }))
      p.setAttribute(k, v);
    svg.append(p);
  }
  path(`M ${left} ${top} V ${bottom} H ${right}`, theme.colors.body, 2);
  path(
    node.points
      .map(
        (p, i) =>
          `${i ? "L" : "M"} ${left + p.x * (right - left)} ${bottom - p.y * (bottom - top)}`,
      )
      .join(" "),
    theme.colors.accent,
    3,
  );
  el.append(svg);
  el.dataset.chartPoints = JSON.stringify(node.points);
  const labels = [
    ["x", node.xLabel, left, bottom + 14, right - left, 40],
    ["y", `${node.yLabel} (${node.unit})`, 0, 0, box.width, 40],
    ["min", String(node.min), 0, bottom - 20, 78, 40],
    ["max", String(node.max), 0, top - 20, 78, 40],
  ];
  if (node.plateau) {
    const p = node.points[node.plateau[0]],
      value = Number((node.min + p.y * (node.max - node.min)).toPrecision(8));
    labels.push([
      "plateau",
      `${value} ${node.unit}`,
      left + 8,
      bottom - p.y * (bottom - top) - 40,
      160,
      36,
    ]);
  }
  for (const [id, text, x, y, w, h] of labels) {
    const label = document.createElement("div");
    label.textContent = text;
    label.dataset.chartLabel = id;
    Object.assign(label.style, {
      position: "absolute",
      left: x + "px",
      top: y + "px",
      width: w + "px",
      height: h + "px",
      fontSize: "24px",
      lineHeight: "1.4",
      whiteSpace: "nowrap",
      textAlign: id === "x" ? "center" : "left",
      color: theme.colors.body,
    });
    el.append(label);
    textNodes.push([
      label,
      { box: { width: w, height: h }, maxLines: 1 },
      node.id + ":" + id,
    ]);
  }
}
module.exports = { validateStructures, drawRelation, chartElements };
