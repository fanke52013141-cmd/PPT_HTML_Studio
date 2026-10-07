"use strict";
const paths = {
  air: [
    "M3 8h13a3 3 0 1 0-3-3",
    "M2 12h18a3 3 0 1 1-3 3",
    "M4 16h6a3 3 0 1 1-3 3",
  ],
  thermometer: [
    "M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z",
    "M12 7v10",
    "M17 6h3M17 10h2",
  ],
  droplet: [
    "M12 2C9 7 4 11 4 15a8 8 0 0 0 16 0c0-4-5-8-8-13Z",
    "M8 15a4 4 0 0 0 4 4",
  ],
  molecule: [
    "M8 8l8 8M16 8l-8 8",
    "M9 5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
    "M23 5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
    "M16 19a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
  ],
  eye: [
    "M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z",
    "M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  ],
  check: [
    "M4 12l5 5L20 6",
    "M21 13v5a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3h9",
  ],
  lightbulb: [
    "M8 16c0-3-4-4-4-8a8 8 0 1 1 16 0c0 4-4 5-4 8Z",
    "M8 20h8M10 23h4M9 8l3 3 3-3M12 11v5",
  ],
  arrow: ["M3 12h17M15 6l6 6-6 6"],
};
function icon(name, { color = "currentColor", width = 1.7 } = {}) {
  if (!Object.hasOwn(paths, name))
    throw new Error("Unknown registered icon: " + name);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
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
    const p = document.createElementNS(svg.namespaceURI, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}
module.exports = { icon };
