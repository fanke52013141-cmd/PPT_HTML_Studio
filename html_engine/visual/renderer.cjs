"use strict";
const { loadResources, fontPresent } = require("../src/resources.cjs");
const { imagePlacement, ease } = require("../src/timeline.cjs");
const { fail } = require("./compiler.cjs");
const SVG = "http://www.w3.org/2000/svg";
const vector = (tag) => document.createElementNS(SVG, tag);
const attributes = (el, values) =>
  Object.entries(values).forEach(([k, v]) => el.setAttribute(k, String(v)));
const px = (n) => `${n}px`;

function textStyle(el, role, theme) {
  const style = theme.text[role];
  Object.assign(el.style, {
    fontSize: px(style.size),
    fontWeight: String(style.weight),
    lineHeight: String(style.lineHeight),
    letterSpacing: px(style.letterSpacing),
    color: theme.colors[style.color],
  });
}
function measure(el, slot, id, stage) {
  const range = document.createRange();
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const rects = [];
  let text;
  while ((text = walker.nextNode())) {
    range.selectNodeContents(text);
    rects.push(
      ...[...range.getClientRects()].filter((r) => r.width && r.height),
    );
  }
  const scale = stage.getBoundingClientRect().width / 1600;
  const bounds = el.getBoundingClientRect();

  const lines = new Set(
    rects.map((r) => Math.round((r.top - bounds.top) / scale)),
  );
  if (
    bounds.width / scale > slot.box.width + 1 ||
    bounds.height / scale > slot.box.height + 1 ||
    lines.size > slot.maxLines ||
    el.scrollHeight > el.clientHeight + 1 ||
    el.scrollWidth > el.clientWidth + 1 ||
    rects.some(
      (r) => r.right > bounds.right + 1 || r.bottom > bounds.bottom + 1,
    )
  )
    fail(
      "CONTENT_CAPACITY_EXCEEDED",
      id,
      `${id}: text exceeds ${slot.maxLines} line(s) or its slot (${lines.size} lines; ${el.scrollWidth}x${el.scrollHeight}/${el.clientWidth}x${el.clientHeight})`,
    );
  return { lines: lines.size, width: slot.box.width, height: slot.box.height };
}

async function prepare(compiled, pack, host) {
  const { source: scene, theme, layout } = compiled;
  if (!fontPresent(theme.font.family))
    fail("FONT_UNAVAILABLE", "/theme/font", theme.font.family);
  await document.fonts.load(`700 66px "${theme.font.family}"`);
  await document.fonts.ready;
  const resources = await loadResources(
    { source: { assets: compiled.assets } },
    pack,
  );
  const stage = document.createElement("div");
  stage.className = "visual-stage";
  Object.assign(stage.style, {
    position: "relative",
    width: "1600px",
    height: "900px",
    background: theme.colors.background,
    fontFamily: `"${theme.font.family}"`,
    transformOrigin: "top left",
    overflow: "hidden",
  });
  const elements = new Map(),
    states = new Map(),
    geometry = {},
    measurements = {};
  const motions = new Map(scene.motion.map((a) => [a.targetId, a]));
  const assetById = new Map(compiled.assets.map((a) => [a.id, a]));
  const textNodes = [];
  try {
    for (const node of scene.nodes) {
      const slot = layout.slots[node.slot],
        b = slot.box;
      const el = document.createElement("div");
      el.dataset.objectId = node.id;
      el.dataset.backend = ["arrow", "annotation"].includes(node.type)
        ? "SVG"
        : node.type === "image"
          ? "image"
          : "CSS";
      Object.assign(el.style, {
        position: "absolute",
        left: px(b.x),
        top: px(b.y),
        width: px(b.width),
        height: px(b.height),
        zIndex: String(slot.z),
        boxSizing: "border-box",
        textAlign: slot.align,
      });
      if (node.type === "text") {
        textStyle(el, node.role, theme);
        el.style.whiteSpace = "pre-wrap";
        for (const run of node.runs) {
          const span = document.createElement("span");
          span.textContent = run.text;
          if (run.emphasis) span.style.color = theme.colors.accent;
          el.append(span);
        }
        textNodes.push([el, slot, node.id]);
      } else if (node.type === "label" || node.type === "badge") {
        const badge = node.type === "badge";
        textStyle(el, badge ? "number" : node.role, theme);
        Object.assign(el.style, {
          borderRadius: px(
            badge ? theme.shapes.badgeRadius : theme.shapes.labelRadius,
          ),
          background:
            theme.colors[
              node.tone === "accent" ? "pinkWash" : `${node.tone}Wash`
            ],
          color: theme.colors[node.tone],
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 16px",
          boxShadow: `0 ${theme.shapes.shadow.y}px ${theme.shapes.shadow.blur}px ${theme.colors.ink}${Math.round(
            theme.shapes.shadow.opacity * 255,
          )
            .toString(16)
            .padStart(2, "0")}`,
        });
        const span = document.createElement("span");
        span.textContent = node.text;
        el.append(span);
        textNodes.push([
          span,
          { ...slot, box: { ...b, width: b.width - 32 } },
          node.id,
        ]);
      } else if (node.type === "image") {
        const asset = assetById.get(node.assetRef.id),
          p = imagePlacement({ ...node, box: b }, asset);
        const img = resources.images.get(asset.id);
        Object.assign(img.style, {
          position: "absolute",
          left: px(p.x),
          top: px(p.y),
          width: px(p.width),
          height: px(p.height),
        });
        img.alt = "";
        el.append(img);
      } else {
        const svg = vector("svg");
        attributes(svg, {
          viewBox: `0 0 ${b.width} ${b.height}`,
          width: b.width,
          height: b.height,
        });
        svg.style.overflow = "visible";
        if (node.type === "arrow") {
          const line = vector("path");
          attributes(line, {
            d: `M 2 ${b.height / 2} H ${b.width - 14} M ${b.width - 28} 4 L ${b.width - 8} ${b.height / 2} L ${b.width - 28} ${b.height - 4}`,
            fill: "none",
            stroke: theme.colors.blue,
            "stroke-width": theme.shapes.strokeWidth,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
          });
          svg.append(line);
        } else {
          const ring = vector("circle"),
            leader = vector("path");
          for (const v of [ring, leader])
            attributes(v, {
              fill: "none",
              stroke: theme.colors.accent,
              "stroke-width": theme.shapes.strokeWidth,
              "stroke-linecap": "round",
            });
          svg.append(ring, leader);
        }
        el.append(svg);
      }
      elements.set(node.id, el);
      stage.append(el);
    }
    const subtitle = document.createElement("div");
    subtitle.dataset.track = "subtitle";
    Object.assign(subtitle.style, {
      position: "absolute",
      left: "0",
      top: "800px",
      width: "1600px",
      height: "100px",
      boxSizing: "border-box",
      padding: "8px 80px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      zIndex: "30",
    });
    const subtitleText = document.createElement("span");
    textStyle(subtitleText, "subtitle", theme);
    subtitleText.style.fontSize = "32px";
    subtitle.append(subtitleText);
    stage.append(subtitle);
    host.append(stage);
    const resize = () => {
      const scale = host.clientWidth / 1600;
      stage.style.transform = `scale(${scale})`;
      host.style.height = px(900 * scale);
    };
    resize();
    textNodes.forEach(
      ([el, slot, id]) => (measurements[id] = measure(el, slot, id, stage)),
    );
    function checkSubtitles(size) {
      subtitleText.style.fontSize = px(size);
      for (const beat of scene.beats) {
        subtitleText.textContent = beat.text;
        measure(
          subtitleText,
          { box: { width: 1440, height: 84 }, maxLines: 2 },
          "subtitle",
          stage,
        );
        if (
          subtitleText.getBoundingClientRect().height /
            (stage.getBoundingClientRect().width / 1600) >
          84
        )
          fail("CONTENT_CAPACITY_EXCEEDED", "subtitle", "Subtitle is too tall");
      }
    }
    checkSubtitles(32);
    let time = 0,
      subtitleSize = 32;
    function renderAt(ms, reduced = false) {
      if (!Number.isFinite(ms) || ms < 0 || ms > scene.durationMs)
        fail("INVALID_TIME", "timeMs", String(ms));
      time = ms;
      for (const node of scene.nodes) {
        const a = motions.get(node.id),
          p = ease("smoothstep", (ms - a.startMs) / a.durationMs);
        const state = {
          opacity: p,
          x: reduced ? 0 : a.offsetX * (1 - p),
          y: reduced ? 0 : a.offsetY * (1 - p),
        };
        states.set(node.id, state);
        const el = elements.get(node.id);
        el.style.opacity = String(p);
        el.style.transform = `translate(${state.x}px,${state.y}px)`;
        if (node.type === "image") {
          const asset = assetById.get(node.assetRef.id),
            b = layout.slots[node.slot].box,
            placement = imagePlacement({ ...node, box: b }, asset);
          geometry[node.id] = {
            box: b,
            placement,
            anchors: Object.fromEntries(
              asset.anchors.map((anchor) => [
                anchor.id,
                {
                  x: b.x + placement.x + anchor.x * placement.width + state.x,
                  y: b.y + placement.y + anchor.y * placement.height + state.y,
                },
              ]),
            ),
          };
        }
      }
      for (const node of scene.nodes.filter((n) => n.type === "annotation")) {
        const anchor = geometry[node.targetId].anchors[node.anchorId];
        const label = scene.nodes.find((n) => n.id === node.labelId),
          b = layout.slots[label.slot].box,
          s = states.get(label.id);
        const endpoint = {
          x: (anchor.x > b.x + b.width / 2 ? b.x + b.width : b.x) + s.x,
          y: b.y + b.height / 2 + s.y,
        };
        const towards = endpoint.x >= anchor.x ? 1 : -1;
        const [ring, leader] = elements
          .get(node.id)
          .querySelector("svg").children;
        const origin = layout.slots[node.slot].box;
        attributes(ring, {
          cx: anchor.x - origin.x,
          cy: anchor.y - origin.y,
          r: node.radius,
        });
        attributes(leader, {
          d: `M ${anchor.x - origin.x + towards * node.radius} ${anchor.y - origin.y} L ${endpoint.x - origin.x - towards * 14} ${endpoint.y - origin.y}`,
        });
        elements.get(node.id).style.opacity = String(
          Math.min(
            states.get(node.id).opacity,
            states.get(node.targetId).opacity,
          ),
        );
        geometry[node.id] = { anchor, endpoint, radius: node.radius };
      }
      const beat = scene.beats.find(
        (b) =>
          b.startMs <= ms &&
          (ms < b.endMs || (ms === scene.durationMs && b.endMs === ms)),
      );
      subtitleText.textContent = beat?.text || "";
      return { timeMs: ms, geometry, measurements, subtitleFont: subtitleSize };
    }
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    renderAt(0);
    return {
      stage,
      scene,
      renderAt,
      get timeMs() {
        return time;
      },
      setSubtitleFont(size) {
        if (!Number.isFinite(size) || size < 20 || size > 44)
          fail("INVALID_SUBTITLE_SIZE", "font", String(size));
        try {
          checkSubtitles(size);
        } catch (e) {
          subtitleText.style.fontSize = px(subtitleSize);
          renderAt(time);
          throw e;
        }
        subtitleSize = size;
        renderAt(time);
      },
      release() {
        observer.disconnect();
        stage.remove();
        resources.release();
      },
    };
  } catch (e) {
    stage.remove();
    resources.release();
    throw e;
  }
}
module.exports = { prepare };
