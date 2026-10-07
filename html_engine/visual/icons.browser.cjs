"use strict";
// Browser-side icon builder over the registered path data in icons.cjs.
const { paths } = require("./icons.cjs");
const SVG = "http://www.w3.org/2000/svg";
function icon(name, { color = "currentColor", width = 1.7 } = {}) {
  if (!Object.hasOwn(paths, name))
    throw new Error("Unknown registered icon: " + name);
  const svg = document.createElementNS(SVG, "svg");
  for (const [k, v] of Object.entries({
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    "stroke-width": width,
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
    "aria-hidden": "true",
  }))
    svg.setAttribute(k, String(v));
  for (const d of paths[name]) {
    const p = document.createElementNS(SVG, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}
module.exports = { icon };
