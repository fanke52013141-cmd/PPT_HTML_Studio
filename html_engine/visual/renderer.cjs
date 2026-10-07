"use strict";
const { loadResources, fontPresent } = require("../src/resources.cjs");
const { imagePlacement, ease } = require("../src/timeline.cjs");
const { fail } = require("./compiler.cjs");
const { icon } = require("./icons.browser.cjs");
const SVG = "http://www.w3.org/2000/svg";
const vector = (tag) => document.createElementNS(SVG, tag);
const attributes = (el, values) =>
  Object.entries(values).forEach(([k, v]) => el.setAttribute(k, String(v)));
const px = (n) => `${n}px`;
const alpha = (opacity) =>
  Math.round(opacity * 255)
    .toString(16)
    .padStart(2, "0");

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

// Deterministic theme stylesheet. Every visual value comes from the resolved
// theme; component CSS never hardcodes colors. Missing optional gradients
// degrade to the registered flat fallbacks.
function themeStylesheet(theme) {
  const c = theme.colors,
    g = theme.gradients,
    s = theme.shapes,
    shadow = `0 ${s.shadowY}px ${s.shadowBlur}px rgb(${s.shadowRGB} / ${s.shadowOpacity})`;
  const bubbleBackground = (tone) =>
    g[tone]
      ? `linear-gradient(135deg, ${g[tone][0]}, ${g[tone][1]})`
      : c[tone];
  const rule = (selector, declarations) =>
    `${selector}{${Object.entries(declarations)
      .map(([k, v]) => `${k}:${v}`)
      .join(";")}}`;
  return [
    rule(".visual-stage", {
      position: "relative",
      width: "1600px",
      height: "900px",
      background: c.background,
      color: c.ink,
      "font-family": `"${theme.font.family}"`,
      "transform-origin": "top left",
      overflow: "hidden",
    }),
    rule(".visual-stage [data-object-id]", {
      position: "absolute",
      "box-sizing": "border-box",
    }),
    rule(".v-header", {
      display: "flex",
      "align-items": "flex-start",
      "border-bottom": `1px solid ${c.line}`,
      gap: "16px",
    }),
    rule(".v-page-number", {
      color: c.pink,
      "font-size": px(theme.text.title.size),
      "line-height": String(theme.text.title.lineHeight),
      "font-weight": "700",
    }),
    rule(".v-page-title", {
      "font-size": px(theme.text.title.size),
      "font-weight": String(theme.text.title.weight),
      "line-height": String(theme.text.title.lineHeight),
      margin: "0",
      "max-width": "1100px",
      "white-space": "nowrap",
    }),
    rule(".v-card", {
      display: "flex",
      "align-items": "center",
      gap: "22px",
      padding: "10px 24px",
      border: `1px solid ${c.line}`,
      "border-radius": px(s.cardRadius),
      background: g.pink
        ? `linear-gradient(105deg, ${c.paper}, ${c.background})`
        : c.panel,
      "box-shadow": shadow,
      overflow: "hidden",
    }),
    rule(".v-icon-bubble", {
      flex: "0 0 64px",
      width: "64px",
      height: "64px",
      "border-radius": px(s.iconRadius),
      display: "grid",
      "place-items": "center",
      "box-shadow":
        "inset 0 1px 1px rgb(255 255 255 / 0.7), 0 5px 14px rgb(69 91 121 / 0.06)",
    }),
    rule(".v-icon-bubble svg", { width: "34px", height: "34px", color: "#ffffff" }),
    rule(".v-card-copy", { flex: "1", "min-width": "0", "max-height": "80px" }),
    rule(".v-card-title", {
      margin: "0 0 4px",
      "font-size": px(theme.text.cardTitle.size),
      "font-weight": String(theme.text.cardTitle.weight),
      "line-height": String(theme.text.cardTitle.lineHeight),
    }),
    rule(".v-card-body", {
      margin: "0",
      "font-size": px(theme.text.cardBody.size),
      "font-weight": String(theme.text.cardBody.weight),
      "line-height": String(theme.text.cardBody.lineHeight),
      color: c.body,
    }),
    rule(".v-figure", {
      "border-radius": px(s.figureRadius),
      background: g.blue
        ? `linear-gradient(150deg, ${g.blue[0]}, ${c.paper} 46%, ${g.purple[0]})`
        : c.panel,
      border: `1px solid ${c.line}`,
      "box-shadow": shadow,
      overflow: "hidden",
    }),
    rule(".v-figure-halo", {
      position: "absolute",
      width: "400px",
      height: "400px",
      "border-radius": "50%",
      background: `radial-gradient(circle, ${c.paper}, transparent 70%)`,
      left: "98px",
      top: "-5px",
    }),
    rule(".v-figure-tag", {
      position: "absolute",
      left: "22px",
      top: "20px",
      "z-index": "1",
      display: "flex",
      "align-items": "center",
      gap: "7px",
      color: c.ink,
      "font-size": "14px",
      background: "rgb(255 255 255 / 0.75)",
      padding: "8px 12px",
      "border-radius": "10px",
    }),
    rule(".v-figure-tag svg, .v-figure-note svg", {
      width: "21px",
      height: "21px",
      color: c.blue,
    }),
    rule(".v-figure-note", {
      position: "absolute",
      left: "24px",
      right: "24px",
      bottom: "16px",
      padding: "11px 14px",
      border: `1px solid ${c.line}`,
      background: "rgb(255 255 255 / 0.92)",
      "border-radius": "12px",
      display: "flex",
      gap: "9px",
      "align-items": "center",
      color: c.body,
      "font-size": px(theme.text.caption.size),
      "z-index": "4",
    }),
    rule(".v-subject", { "z-index": "2", "pointer-events": "none" }),
    rule(".v-annotation", { "z-index": "5", "pointer-events": "none" }),
    rule(".v-anchor-label", {
      "z-index": "6",
      "white-space": "pre-line",
      display: "flex",
      "align-items": "center",
      padding: "10px 12px",
      "border-radius": "12px",
      border: `1px solid ${c.line}`,
      background: "rgb(255 255 255 / 0.97)",
      "font-size": px(theme.text.caption.size),
      "line-height": String(theme.text.caption.lineHeight),
      color: c.body,
      "box-shadow": "0 4px 18px rgb(69 91 121 / 0.06)",
    }),
    rule(".v-summary", {
      display: "flex",
      "align-items": "center",
      gap: "30px",
      padding: "18px 26px",
      background: g.purple
        ? `linear-gradient(105deg, ${c.paper}, ${g.purple[0]})`
        : c.panel,
      border: `1px solid ${c.line}`,
      "border-radius": "16px",
    }),
    rule(".v-summary-heading", {
      display: "flex",
      gap: "13px",
      "align-items": "center",
      "font-size": "25px",
      "font-weight": "700",
      "white-space": "nowrap",
    }),
    rule(".v-summary-heading svg", {
      width: "38px",
      height: "38px",
      color: c.yellow,
    }),
    rule(".v-flow", {
      display: "flex",
      "align-items": "center",
      gap: "20px",
      "white-space": "nowrap",
    }),
    rule(".v-state", {
      "font-size": "26px",
      "font-weight": "700",
      padding: "9px 20px",
      "border-radius": "14px",
    }),
    rule(".v-state-from", { background: g.blue ? g.blue[0] : c.blueWash }),
    rule(".v-state-to", { background: g.green ? g.green[0] : c.greenWash }),
    rule(".v-flow svg", { width: "44px", height: "25px", color: c.blue }),
    rule(".v-term", { "font-size": "20px", color: c.body }),
    rule(".v-takeaway", {
      "margin-left": "auto",
      "max-width": "540px",
      "font-size": px(theme.text.summary.size),
      "font-weight": String(theme.text.summary.weight),
      "line-height": String(theme.text.summary.lineHeight),
      color: c.ink,
      "white-space": "nowrap",
    }),
  ].join("\n");
}

function measureOverflow(el, width, id, stage) {
  const scale = stage.getBoundingClientRect().width / 1600;
  const bounds = el.getBoundingClientRect();
  if (
    bounds.width / scale > width + 1 ||
    el.scrollWidth > el.clientWidth + 1 ||
    el.scrollHeight > el.clientHeight + 1
  )
    fail(
      "CONTENT_CAPACITY_EXCEEDED",
      id,
      `${id}: composite content exceeds its slot width (${bounds.width / scale} > ${width})`,
    );
  return { lines: 1, width, height: bounds.height / scale };
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
  const stylesheet = document.createElement("style");
  stylesheet.textContent = themeStylesheet(theme);
  const stage = document.createElement("div");
  stage.className = "visual-stage";
  const elements = new Map(),
    states = new Map(),
    geometry = {},
    measurements = {};
  const motions = new Map(scene.motion.map((a) => [a.targetId, a]));
  const assetById = new Map(compiled.assets.map((a) => [a.id, a]));
  const textNodes = [],
    overflowChecks = [];
  try {
    const place = (node, el) => {
      const b = layout.slots[node.slot].box;
      Object.assign(el.style, {
        left: px(b.x),
        top: px(b.y),
        width: px(b.width),
        height: px(b.height),
        zIndex: String(layout.slots[node.slot].z),
        textAlign: layout.slots[node.slot].align,
      });
    };
    for (const node of scene.nodes) {
      const el = document.createElement("div");
      el.dataset.objectId = node.id;
      el.dataset.backend = ["arrow", "annotation"].includes(node.type)
        ? "SVG"
        : node.type === "image"
          ? "image"
          : "CSS";
      place(node, el);
      if (node.type === "text") {
        textStyle(el, node.role, theme);
        el.style.whiteSpace = "pre-wrap";
        for (const run of node.runs) {
          const span = document.createElement("span");
          span.textContent = run.text;
          if (run.emphasis) span.style.color = theme.colors.accent;
          el.append(span);
        }
        textNodes.push([el, layout.slots[node.slot], node.id]);
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
          boxShadow: `0 ${theme.shapes.shadow.y}px ${theme.shapes.shadow.blur}px ${theme.colors.ink}${alpha(theme.shapes.shadow.opacity)}`,
        });
        const span = document.createElement("span");
        span.textContent = node.text;
        el.append(span);
        textNodes.push([
          span,
          {
            ...layout.slots[node.slot],
            box: { ...layout.slots[node.slot].box, width: layout.slots[node.slot].box.width - 32 },
          },
          node.id,
        ]);
      } else if (node.type === "image") {
        el.classList.add("v-subject");
        const asset = assetById.get(node.assetRef.id),
          p = imagePlacement({ ...node, box: layout.slots[node.slot].box }, asset);
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
      } else if (node.type === "header") {
        el.classList.add("v-header");
        const number = document.createElement("span");
        number.className = "v-page-number";
        number.textContent = node.number;
        const title = document.createElement("h1");
        title.className = "v-page-title";
        title.textContent = node.title;
        el.append(number, title);
        textNodes.push([title, layout.slots[node.slot], node.id]);
      } else if (node.type === "card") {
        el.classList.add("v-card");
        const bubble = document.createElement("span");
        bubble.className = "v-icon-bubble";
        bubble.style.background = theme.gradients[node.tone]
          ? `linear-gradient(135deg, ${theme.gradients[node.tone][0]}, ${theme.gradients[node.tone][1]})`
          : theme.colors[node.tone];
        bubble.append(icon(node.icon, { width: theme.shapes.iconStroke }));
        const copy = document.createElement("div");
        copy.className = "v-card-copy";
        const title = document.createElement("h2");
        title.className = "v-card-title";
        title.textContent = node.title;
        const body = document.createElement("p");
        body.className = "v-card-body";
        body.textContent = node.body;
        copy.append(title, body);
        el.append(bubble, copy);
        const slot = layout.slots[node.slot];
        textNodes.push([title, { ...slot, box: { ...slot.box, height: 46 } }, node.id]);
        textNodes.push([body, { ...slot, box: { ...slot.box, height: slot.box.height - 56 } }, node.id]);
      } else if (node.type === "figure") {
        el.classList.add("v-figure");
        el.append(Object.assign(document.createElement("div"), { className: "v-figure-halo" }));
        if (node.tag) {
          const tag = document.createElement("div");
          tag.className = "v-figure-tag";
          tag.append(icon(node.tag.icon));
          tag.append(Object.assign(document.createElement("span"), { textContent: node.tag.text }));
          el.append(tag);
          textNodes.push([
            tag.querySelector("span"),
            { ...layout.slots[node.slot], box: { ...layout.slots[node.slot].box, height: 40 } },
            node.id + ":tag",
          ]);
        }
        if (node.note) {
          const note = document.createElement("div");
          note.className = "v-figure-note";
          note.append(icon(node.note.icon));
          note.append(Object.assign(document.createElement("span"), { textContent: node.note.text }));
          el.append(note);
          textNodes.push([
            note.querySelector("span"),
            { ...layout.slots[node.slot], box: { ...layout.slots[node.slot].box, height: 40 }, maxLines: 2 },
            node.id + ":note",
          ]);
        }
      } else if (node.type === "summary") {
        el.classList.add("v-summary");
        if (node.heading) {
          const heading = document.createElement("div");
          heading.className = "v-summary-heading";
          heading.append(icon(node.heading.icon));
          heading.append(Object.assign(document.createElement("span"), { textContent: node.heading.text }));
          el.append(heading);
        }
        const flow = document.createElement("div");
        flow.className = "v-flow";
        const from = document.createElement("span");
        from.className = "v-state v-state-from";
        from.textContent = node.from.text;
        const arrow = icon("arrow");
        const to = document.createElement("span");
        to.className = "v-state v-state-to";
        to.textContent = node.to.text;
        const term = document.createElement("span");
        term.className = "v-term";
        term.textContent = `这个过程叫${node.term}`;
        flow.append(from, arrow, to, term);
        el.append(flow);
        const takeaway = document.createElement("strong");
        takeaway.className = "v-takeaway";
        takeaway.textContent = node.takeaway;
        el.append(takeaway);
        const slot = layout.slots[node.slot];
        overflowChecks.push([flow, slot.box.width - 620, node.id]);
        textNodes.push([takeaway, { ...slot, box: { ...slot.box, width: 540 } }, node.id + ":takeaway"]);
      } else {
        const svg = vector("svg");
        attributes(svg, {
          viewBox: `0 0 ${layout.slots[node.slot].box.width} ${layout.slots[node.slot].box.height}`,
          width: layout.slots[node.slot].box.width,
          height: layout.slots[node.slot].box.height,
        });
        svg.style.overflow = "visible";
        if (node.type === "arrow") {
          const b = layout.slots[node.slot].box;
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
          leader.setAttribute("pathLength", "1");
          leader.style.strokeDasharray = "1";
          svg.append(ring, leader);
        }
        el.append(svg);
        if (node.type === "annotation") el.classList.add("v-annotation");
        if (node.type === "arrow") el.style.display = "flex";
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
    host.append(stylesheet, stage);
    const resize = () => {
      const scale = host.clientWidth / 1600;
      stage.style.transform = `scale(${scale})`;
      host.style.height = px(900 * scale);
    };
    resize();
    textNodes.forEach(
      ([el, slot, id]) => (measurements[id] = measure(el, slot, id, stage)),
    );
    overflowChecks.forEach(
      ([el, width, id]) => (measurements[id] = measureOverflow(el, width, id, stage)),
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
        const progress = ease(
          "smoothstep",
          (ms - motions.get(node.id).startMs) / motions.get(node.id).durationMs,
        );
        attributes(leader, {
          d: `M ${anchor.x - origin.x + towards * node.radius} ${anchor.y - origin.y} L ${endpoint.x - origin.x - towards * 14} ${endpoint.y - origin.y}`,
          "stroke-dashoffset": String(1 - progress),
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
        stylesheet.remove();
        resources.release();
      },
    };
  } catch (e) {
    stage.remove();
    stylesheet.remove();
    resources.release();
    throw e;
  }
}
module.exports = { prepare, themeStylesheet };
