"use strict";
const { loadResources, fontPresent } = require("../src/resources.cjs");
const { imagePlacement, ease } = require("../src/timeline.cjs");
const { fail } = require("./compiler.cjs");
const { icon } = require("./icons.browser.cjs");
const variants = require("./presentation-variants.json").variants;
const { capacityEvidence } = require("./capacity.cjs");
const {frameFigure, dividedSummary, styleAnnotation, drawAnnotationLeader} = require("./presentation-structures.cjs");
const {drawRelation,chartElements} = require("./course-structures.cjs");
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
  const evidence = capacityEvidence({
    width: bounds.width / scale, height: bounds.height / scale,
    lines: lines.size, scrollWidth: el.scrollWidth, scrollHeight: el.scrollHeight,
    clientWidth: el.clientWidth, clientHeight: el.clientHeight,
    textRight: Math.max(0, ...rects.map(r => r.right - bounds.right)),
    textBottom: Math.max(0, ...rects.map(r => r.bottom - bounds.bottom)),
  }, { width: slot.box.width, height: slot.box.height, maxLines: slot.maxLines });
  assertCapacity(id, evidence);
  return { lines: lines.size, width: slot.box.width, height: slot.box.height };
}

// Deterministic theme stylesheet. Every visual value comes from the resolved
// theme; component CSS never hardcodes colors. Missing optional gradients
// degrade to the registered flat fallbacks.
function themeStylesheet(theme) {
  const c = theme.colors,
    g = theme.gradients,
    s = theme.shapes,
    editorialFlat = theme.id === "neutral-baseline",
    shadow = `0 ${s.shadowY}px ${s.shadowBlur}px rgb(${s.shadowRGB} / ${s.shadowOpacity})`;
  const bubbleBackground = (tone) =>
    g[tone] ? `linear-gradient(135deg, ${g[tone][0]}, ${g[tone][1]})` : c[tone];
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
      "border-bottom": editorialFlat ? "none" : `1px solid ${c.line}`,
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
      border: editorialFlat ? "none" : `1px solid ${c.line}`,
      "border-radius": px(s.cardRadius),
      background: editorialFlat
        ? `linear-gradient(115deg, ${c.pinkWash}, ${c.background})`
        : g.pink
        ? `linear-gradient(105deg, ${c.paper}, ${c.background})`
        : c.panel,
      "box-shadow": editorialFlat ? "none" : shadow,
      overflow: "hidden",
    }),
    rule(".v-icon-bubble", {
      flex: "0 0 64px",
      width: "64px",
      height: "64px",
      "border-radius": editorialFlat ? "50%" : px(s.iconRadius),
      display: "grid",
      "place-items": "center",
      "box-shadow": editorialFlat
        ? "none"
        : `inset 0 1px 1px rgb(255 255 255 / 0.7), 0 5px 14px rgb(${s.shadowRGB} / 0.06)`,
    }),
    rule(".v-icon-bubble svg", {
      width: "34px",
      height: "34px",
      color: editorialFlat ? c.body : "#ffffff",
    }),
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
      "border-radius": editorialFlat ? "0" : px(s.figureRadius),
      background: editorialFlat
        ? "transparent"
        : g.blue
        ? `linear-gradient(150deg, ${g.blue[0]}, ${c.paper} 46%, ${g.purple[0]})`
        : c.panel,
      border: editorialFlat ? "none" : `1px solid ${c.line}`,
      "box-shadow": editorialFlat ? "none" : shadow,
      overflow: editorialFlat ? "visible" : "hidden",
    }),
    rule(".v-figure-halo", {
      position: "absolute",
      width: "400px",
      height: "400px",
      "border-radius": "50%",
      background: `radial-gradient(circle, ${editorialFlat ? c.pinkWash : c.paper}, transparent 70%)`,
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
      border: editorialFlat ? "none" : `1px solid ${c.line}`,
      background: editorialFlat ? "rgb(255 255 255 / 0.78)" : "rgb(255 255 255 / 0.92)",
      "border-radius": editorialFlat ? "999px" : "12px",
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
      "border-radius": editorialFlat ? "999px" : "12px",
      border: editorialFlat ? "none" : `1px solid ${c.line}`,
      background: editorialFlat ? "rgb(255 255 255 / 0.85)" : "rgb(255 255 255 / 0.97)",
      "font-size": px(theme.text.caption.size),
      "line-height": String(theme.text.caption.lineHeight),
      color: c.body,
      "box-shadow": `0 4px 18px rgb(${s.shadowRGB} / 0.06)`,
    }),
    rule(".v-summary", {
      display: "flex",
      "align-items": "center",
      gap: "30px",
      padding: "18px 26px",
      background: editorialFlat
        ? `linear-gradient(105deg, ${c.pinkWash}, ${c.background})`
        : g.purple
        ? `linear-gradient(105deg, ${c.paper}, ${g.purple[0]})`
        : c.panel,
      border: editorialFlat ? "none" : `1px solid ${c.line}`,
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
  assertCapacity(id, capacityEvidence({
    width: bounds.width / scale, height: bounds.height / scale,
    scrollWidth: el.scrollWidth, scrollHeight: el.scrollHeight,
    clientWidth: el.clientWidth, clientHeight: el.clientHeight,
  }, { width }));
  return { lines: 1, width, height: bounds.height / scale };
}

function assertCapacity(id, evidence) {
  if (!evidence.triggers.length) return;
  try {
    fail("CONTENT_CAPACITY_EXCEEDED", id,
      `${id}: ${evidence.triggers.map(t => `${t.dimension}: ${t.actual} > ${t.limit} + ${t.tolerance} ${t.unit}`).join("; ")}`);
  } catch (error) {
    error.capacityEvidence = evidence;
    throw error;
  }
}

async function prepare(compiled, pack, host, { diagnostic = false } = {}) {
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
    measurements = {},
    capacityIssues = [];
  // Candidate diagnosis only: all schema/font/resource gates still execute.
  // Production callers retain strict capacity failure by default.
  function checkedMeasure(fn, el, limit, id) {
    try {
      return fn(el, limit, id, stage);
    } catch (error) {
      if (!diagnostic || error.code !== "CONTENT_CAPACITY_EXCEEDED") throw error;
      const style = getComputedStyle(el);
      const box = el.getBoundingClientRect();
      const scale = stage.getBoundingClientRect().width / 1600;
      const issue = {
        code: error.code, target: id, message: error.message,
        ...error.capacityEvidence,
        available: typeof limit === "number" ? { width: limit } : limit,
        measured: { width: box.width / scale, height: box.height / scale,
          scrollWidth: el.scrollWidth, scrollHeight: el.scrollHeight,
          clientWidth: el.clientWidth, clientHeight: el.clientHeight },
        typography: { fontSizePx: parseFloat(style.fontSize),
          lineHeight: style.lineHeight, weight: style.fontWeight },
      };
      const summary = el.closest('.v-summary');
      if (summary) {
        issue.internalParts = Object.entries({from:'.v-state-from',to:'.v-state-to',term:'.v-term',takeaway:'.v-takeaway'})
          .map(([part,selector]) => {
            const child = summary.querySelector(selector), css = getComputedStyle(child);
            return {part, width:child.getBoundingClientRect().width / scale,
              scrollWidth:child.scrollWidth,clientWidth:child.clientWidth,
              fontSizePx:parseFloat(css.fontSize),
              paddingX:parseFloat(css.paddingLeft)+parseFloat(css.paddingRight)};
          });
        issue.flowColumns = getComputedStyle(summary.querySelector('.v-flow')).gridTemplateColumns;
      }
      capacityIssues.push(issue);
      return { ...issue.measured, failed: true };
    }
  }
  const motionsByTarget = new Map();
  for (const action of scene.motion) {
    const list = motionsByTarget.get(action.targetId) || [];
    list.push(action);
    motionsByTarget.set(action.targetId, list);
  }
  const assetById = new Map(compiled.assets.map((a) => [a.id, a]));
  const textNodes = [],
    overflowChecks = [], minimumChecks = [];
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
      if (node.type === "shape") {
        el.style.background = theme.colors[node.fill];
        el.style.borderRadius =
          node.kind === "ellipse" ? "50%" : px(node.radius ?? 0);
        el.setAttribute("aria-hidden", "true");
      } else if (node.type === "text") {
        const variant = variants.find(v => v.id === node.presentation?.variant);
        const panel = variant && variant.id.startsWith("text-card-");
        const copy = panel ? document.createElement("div") : el;
        if (panel) {
          Object.assign(el.style, {display:"flex",alignItems:"center",gap:px(variant.gap),padding:`${variant.paddingY}px ${variant.paddingX}px`,
            border:`1px solid ${theme.colors.line}`,borderRadius:px(theme.shapes.cardRadius),background:theme.colors.background,
            boxShadow:variant.id==='text-card-soft' ? `0 8px 24px rgb(${theme.shapes.shadowRGB} / 0.06)` : 'none'});
          copy.className="v-panel-copy";
          Object.assign(copy.style,{flex:"1",minWidth:"0"});
          if (node.presentation.icon) {
            const bubble=document.createElement("span");
            Object.assign(bubble.style,{width:px(variant.iconSize),height:px(variant.iconSize),flexShrink:"0",borderRadius:"50%",background:theme.colors[variant.iconBackgroundToken || "panel"],display:"grid",placeItems:"center"});
            const pictogram=icon(node.presentation.icon);Object.assign(pictogram.style,{width:"38px",height:"38px",color:theme.colors.body});
            bubble.append(pictogram);el.append(bubble);
          }
          el.append(copy);
        }
        textStyle(copy, node.role, theme);
        copy.style.whiteSpace = "pre-wrap";
        const joined = node.runs.map(r => r.text).join("");
        const prefixEnd = variant?.labelDelimiter ? joined.search(/[:：]/) + 1 : 0;
        let labelBox, bodyBox;
        if (variant?.stackedLabel) {
          labelBox = document.createElement("div"); bodyBox = document.createElement("div");
          labelBox.className = "v-stacked-label"; bodyBox.className = "v-stacked-body";
          copy.append(labelBox, bodyBox);
        }
        let offset = 0;
        for (const run of node.runs) {
          const cut = Math.max(0, Math.min(run.text.length, prefixEnd - offset));
          const pieces = prefixEnd ? [[run.text.slice(0, cut), true], [run.text.slice(cut), false]] : [[run.text, null]];
          for (const [text, label] of pieces) {
            if (!text) continue;
            const span = document.createElement("span");
            span.textContent = text;
            if (run.emphasis) span.style.color = theme.colors.accent;
            if (variant?.emphasisWeight) span.style.fontWeight = String(run.emphasis ? variant.emphasisWeight : variant.normalWeight);
            if (label !== null) { span.dataset.textRole = label ? "label" : "body"; span.style.fontWeight = label ? "700" : "400"; }
            (variant?.stackedLabel ? (label ? labelBox : bodyBox) : copy).append(span);
          }
          offset += run.text.length;
        }
        const slot=layout.slots[node.slot];
        textNodes.push([copy,panel ? {...slot,box:{...slot.box,width:slot.box.width-variant.paddingX*2-(node.presentation.icon ? variant.iconSize+variant.gap : 0),height:slot.box.height-variant.paddingY*2}} : slot,node.id]);
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
            box: {
              ...layout.slots[node.slot].box,
              width: layout.slots[node.slot].box.width - 32,
            },
          },
          node.id,
        ]);
      } else if (node.type === "image") {
        el.classList.add("v-subject");
        // Keep bitmap compositing stable across direct and animated seeks.
        el.style.willChange = "transform, opacity";
        const asset = assetById.get(node.assetRef.id),
          p = imagePlacement(
            { ...node, box: layout.slots[node.slot].box },
            asset,
          );
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
        if (node.presentation?.variant === "header-badge") {
          const variant=variants.find(v=>v.id==='header-badge');
          Object.assign(number.style,{width:px(variant.badgeWidth),height:"100%",maxHeight:px(variant.badgeWidth),flexShrink:"0",display:"grid",placeItems:"center",borderRadius:px(variant.badgeRadius),background:theme.colors.ink,color:theme.colors.background,fontSize:"34px",lineHeight:"1"});
          Object.assign(el.style,{alignItems:"center",gap:"24px",borderBottom:"none"});
          title.style.maxWidth=px(layout.slots[node.slot].box.width-variant.badgeWidth-24);
        }
        textNodes.push([title, layout.slots[node.slot], node.id]);
      } else if (node.type === "card") {
        el.classList.add("v-card");
        if (node.presentation?.variant === "card-outline") Object.assign(el.style,{background:theme.colors.background,border:`1px solid ${theme.colors.line}`,boxShadow:"none"});
        const bubble = document.createElement("span");
        bubble.className = "v-icon-bubble";
        bubble.style.background = theme.id === "neutral-baseline"
          ? `linear-gradient(135deg, ${theme.colors.blueWash}, ${theme.colors.pinkWash})`
          : theme.gradients[node.tone]
          ? `linear-gradient(135deg, ${theme.gradients[node.tone][0]}, ${theme.gradients[node.tone][1]})`
          : theme.colors[node.tone];
        if (node.presentation?.variant === "card-outline") Object.assign(bubble.style,{borderRadius:"50%",background:theme.colors.blueWash});
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
        textNodes.push([
          title,
          { ...slot, box: { ...slot.box, height: 46 } },
          node.id,
        ]);
        textNodes.push([
          body,
          { ...slot, box: { ...slot.box, height: slot.box.height - 56 } },
          node.id,
        ]);
      } else if (node.type === "chart") {
        chartElements(el,node,layout.slots[node.slot].box,theme,textNodes);
      } else if (node.type === "figure") {
        const framed = ["figure-frame-top","figure-frame-dashed"].includes(node.presentation?.variant);
        const captionsTop = framed || node.presentation?.variant === "figure-caption-top";
        const captionVariant = variants.find(v => v.id === node.presentation?.variant);
        el.classList.add("v-figure");
        el.append(
          Object.assign(document.createElement("div"), {
            className: "v-figure-halo",
          }),
        );
        if (framed) {frameFigure(el, theme);if(node.presentation.variant === "figure-frame-dashed") el.style.borderStyle="dashed";}
        if (node.tag) {
          const tag = document.createElement("div");
          tag.className = "v-figure-tag";
          tag.append(icon(node.tag.icon));
          tag.append(
            Object.assign(document.createElement("span"), {
              textContent: node.tag.text,
            }),
          );
          el.append(tag);
          if (captionsTop) Object.assign(tag.style, {top:px(captionVariant.tagTop),left:px(captionVariant.captionInset),maxWidth:px(layout.slots[node.slot].box.width-2*captionVariant.captionInset),boxSizing:"border-box",border:framed?"none":`1px solid ${theme.colors.line}`,background:framed?theme.colors.background:theme.colors[captionVariant.tagBackgroundToken],borderRadius:framed?"0":"999px",fontSize:framed?"24px":"18px",fontWeight:"700"});
          textNodes.push([
            tag.querySelector("span"),
            {
              ...layout.slots[node.slot],
              box: { ...layout.slots[node.slot].box, width:layout.slots[node.slot].box.width-(captionsTop?94:0), height: 40 },
            },
            node.id + ":tag",
          ]);
        }
        if (node.note) {
          const note = document.createElement("div");
          note.className = "v-figure-note";
          note.append(icon(node.note.icon));
          note.append(
            Object.assign(document.createElement("span"), {
              textContent: node.note.text,
            }),
          );
          el.append(note);
          if (captionsTop) Object.assign(note.style, {top:px(captionVariant.noteTop),bottom:"auto",left:px(captionVariant.captionInset),right:px(captionVariant.captionInset),padding:"6px 10px",fontSize:"14px",lineHeight:"1.3",border:"none",background:theme.colors.background,borderRadius:"8px"});
          textNodes.push([
            note.querySelector("span"),
            {
              ...layout.slots[node.slot],
              box: { ...layout.slots[node.slot].box, width:layout.slots[node.slot].box.width-(captionsTop?86:0), height: captionsTop?44:40 },
              maxLines: 2,
            },
            node.id + ":note",
          ]);
        }
      } else if (node.type === "summary") {
        el.classList.add("v-summary");
        if (node.heading) {
          const heading = document.createElement("div");
          heading.className = "v-summary-heading";
          heading.append(icon(["summary-relationship-panel", "summary-relationship-compact", "summary-relationship-columns"].includes(node.presentation?.variant) ? node.presentation.icon || node.heading.icon : node.heading.icon));
          heading.append(
            Object.assign(document.createElement("span"), {
              textContent: node.heading.text,
            }),
          );
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
        term.textContent = ["summary-strip-divided", "summary-arrow-overlay", "summary-panel", "summary-relationship-panel", "summary-relationship-compact", "summary-relationship-columns"].includes(node.presentation?.variant) ? node.term : `这个过程叫${node.term}`;
        flow.append(from, arrow, to, term);
        el.append(flow);
        const takeaway = document.createElement("strong");
        takeaway.className = "v-takeaway";
        takeaway.textContent = node.takeaway;
        el.append(takeaway);
        if (node.presentation?.variant === "summary-panel") {
          Object.assign(el.style,{border:`1px solid ${theme.colors.line}`,background:theme.colors.panel,padding:"20px 24px",gap:"24px",borderRadius:px(theme.shapes.cardRadius)});
          const heading=el.querySelector('.v-summary-heading');
          if(heading) {heading.style.flexShrink="0"; const mark=heading.querySelector('svg');Object.assign(mark.style,{width:"64px",height:"64px",padding:"14px",borderRadius:"50%",background:theme.colors.ink,color:theme.colors.background});}
          Object.assign(flow.style,{display:"grid",gridTemplateColumns:"minmax(120px,max-content) 132px minmax(120px,max-content)",gap:"8px 14px",alignItems:"center",justifyItems:"center",flexShrink:"0"});
          Object.assign(from.style,{gridColumn:"1",gridRow:"1",background:theme.colors.background,border:`1px solid ${theme.colors.line}`,padding:"16px 28px"});
          Object.assign(to.style,{gridColumn:"3",gridRow:"1",background:theme.colors.background,border:`1px solid ${theme.colors.line}`,padding:"16px 28px"});
          Object.assign(arrow.style,{gridColumn:"2",gridRow:"1",width:"100px",height:"28px"});
          Object.assign(term.style,{gridColumn:"2",gridRow:"2",fontSize:"22px"});
          takeaway.style.whiteSpace="normal";
        }
        const slot = layout.slots[node.slot];
        if (node.presentation?.variant === "summary-strip-divided") {
          dividedSummary(el, {flow,from,to,arrow,term,takeaway}, slot, theme,
            variants.find(v=>v.id === node.presentation.variant), textNodes);
        } else if (node.presentation?.variant === "summary-arrow-overlay") {
          const width = slot.box.width - 48;
          Object.assign(el.style,{display:"flex",flexDirection:"column",justifyContent:"center",padding:"16px 24px",gap:"12px",border:`1px solid ${theme.colors.line}`,borderRadius:px(theme.shapes.cardRadius),background:theme.colors.panel});
          Object.assign(flow.style,{display:"grid",gridTemplateColumns:"1fr 2fr 1fr",width:"100%",gap:"0",alignItems:"center",justifyItems:"center",minHeight:"52px",flexShrink:"0"});
          Object.assign(from.style,{gridColumn:"1",gridRow:"1",maxWidth:"100%",boxSizing:"border-box"});
          Object.assign(to.style,{gridColumn:"3",gridRow:"1",maxWidth:"100%",boxSizing:"border-box"});
          Object.assign(arrow.style,{gridColumn:"2",gridRow:"1",width:"100%",height:"28px"});
          // A square icon's viewBox keeps its painted path narrow even when
          // its SVG element is wide. This relation owns an actual long path.
          attributes(arrow,{viewBox:"0 0 600 28",preserveAspectRatio:"none"});
          const line = vector('path');
          attributes(line,{d:"M 2 14 H 596 M 582 3 L 596 14 L 582 25",fill:"none",stroke:theme.colors.body,"stroke-width":2,"vector-effect":"non-scaling-stroke"});
          arrow.replaceChildren(line);
          Object.assign(term.style,{gridColumn:"2",gridRow:"1",zIndex:"1",padding:"6px 18px",borderRadius:"999px",background:theme.colors.ink,color:theme.colors.background,maxWidth:"100%",boxSizing:"border-box"});
          Object.assign(takeaway.style,{marginLeft:"0",maxWidth:"100%",textAlign:"center",whiteSpace:"normal",lineHeight:"1.3",fontSize:"24px"});
          const heading = el.querySelector('.v-summary-heading');
          if (heading) textNodes.push([heading,{...slot,maxLines:1,box:{...slot.box,width,height:40}},node.id+":heading"]);
          for (const [part,text,w,h,lines] of [["from",from,width/4,52,1],["to",to,width/4,52,1],["term",term,width/2,52,1],["takeaway",takeaway,width,64,2]])
            textNodes.push([text,{...slot,maxLines:lines,box:{...slot.box,width:w,height:h}},node.id+":"+part]);
          textNodes.push([el,{...slot,maxLines:node.heading?5:4},node.id+":container"]);
        } else if (["summary-relationship-panel", "summary-relationship-compact", "summary-relationship-columns"].includes(node.presentation?.variant)) {
          const variant = variants.find(v => v.id === node.presentation.variant);
          const columnsResult = variant.termPosition === "takeaway_column";
          const compact = node.presentation.variant !== "summary-relationship-panel";
          const width = slot.box.width - variant.paddingX * 2;
          const height = slot.box.height - variant.paddingY * 2;
          const heading = el.querySelector(".v-summary-heading");
          const fractions = variant.columns.reduce((a, b) => a + b, 0);
          const columns = variant.columns.map(f => (width - variant.gap * 2) * f / fractions);
          Object.assign(el.style, {display:"grid",gridTemplateColumns:columns.map(px).join(" "),gap:px(variant.gap),padding:`${variant.paddingY}px ${variant.paddingX}px`,background:theme.colors[variant.backgroundToken],border:"none",borderRadius:px(theme.shapes.cardRadius),boxShadow:"none"});
          Object.assign(heading.style, {minWidth:"0",height:"100%",borderRight:`1px solid ${theme.colors.line}`,paddingRight:compact?"12px":"18px",boxSizing:"border-box",whiteSpace:"normal",gap:compact?"10px":"14px"});
          const mark = heading.querySelector("svg");
          Object.assign(mark.style, {width:compact?"42px":"58px",height:compact?"42px":"58px",padding:compact?"9px":"13px",boxSizing:"border-box",flexShrink:"0",borderRadius:"50%",background:theme.colors.ink,color:theme.colors.background});
          Object.assign(flow.style, {minWidth:"0",height:"100%",display:"grid",gridTemplateColumns:"minmax(0,1fr) minmax(80px,1.3fr) minmax(0,1fr)",gridTemplateRows:"1fr auto",gap:compact?"3px 7px":"6px 8px",borderRight:`1px solid ${theme.colors.line}`,paddingRight:compact?"12px":"18px",boxSizing:"border-box",alignItems:"center",justifyItems:"center"});
          for (const state of [from,to]) Object.assign(state.style,{minWidth:"0",maxWidth:"100%",boxSizing:"border-box",padding:compact?"6px":"12px",border:`1px solid ${theme.colors.line}`,background:theme.colors.background,fontSize:compact?"20px":"26px"});
          const connector = vector("svg");
          attributes(connector, {viewBox:"0 0 160 28",preserveAspectRatio:"none",width:"100%",height:28});
          connector.dataset.connector = "relationship";
          Object.assign(connector.style,{width:"100%",height:"28px",display:"block"});
          const line = vector("path");
          attributes(line,{d:"M2 14H156M146 4L156 14L146 24",fill:"none",stroke:theme.colors.ink,"stroke-width":2,"stroke-linecap":"round","stroke-linejoin":"round","vector-effect":"non-scaling-stroke"});
          connector.append(line); arrow.replaceWith(connector);
          Object.assign(term.style,{gridColumn:"1 / 4",gridRow:"2",fontSize:compact?"17px":"22px"});
          Object.assign(takeaway.style,{minWidth:"0",maxWidth:"none",marginLeft:"0",whiteSpace:"normal",fontSize:compact?"20px":"26px",lineHeight:compact?"1.2":"1.4"});
          if (columnsResult) {
            const result = document.createElement("div");result.className="v-result-column";
            Object.assign(result.style,{minWidth:"0",height:"100%",display:"flex",flexDirection:"column",justifyContent:"center",alignItems:"center",gap:"6px"});
            Object.assign(flow.style,{gridTemplateRows:"1fr"});
            Object.assign(term.style,{fontSize:"24px",fontWeight:"700",lineHeight:"1.2",maxWidth:"100%"});
            Object.assign(takeaway.style,{fontSize:"17px",lineHeight:"1.2",padding:"6px 10px",border:`1px solid ${theme.colors.line}`,borderRadius:"999px",background:theme.colors.background,boxSizing:"border-box"});
            result.append(term,takeaway);el.append(result);
          }
          const parts = {heading:heading.querySelector("span"),from,to,term,takeaway};
          for (const [part, text] of Object.entries(parts)) {
            const available = part === "heading" ? columns[0]-(compact?12+42+10:18+58+14) : part === "takeaway" ? columns[2]-(columnsResult?22:0) : part === "term" ? (columnsResult?columns[2]:columns[1]-(compact?12:18)) : (columns[1]-(compact?12:18)-16)*1/3.3-(compact?12:24);
            const partHeight = part === "from" || part === "to" ? height-(compact?12+20:32+24) : part === "term" ? (columnsResult?30:compact?24:32) : columnsResult && part === "takeaway" ? height-48 : height;
            textNodes.push([text,{...slot,maxLines:variant.textBudgets[part],box:{...slot.box,width:available,height:partHeight}},node.id+":"+part]);
          }
          overflowChecks.push([el,slot.box.width,node.id]);
        } else {
          overflowChecks.push([flow, slot.box.width - 620, node.id]);
          textNodes.push([takeaway,{ ...slot, box: { ...slot.box, width: 540 } },node.id + ":takeaway"]);
        }
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
            d: node.presentation?.variant === "arrow-up" ? `M ${b.width/2} ${b.height-2} V 6 M 4 18 L ${b.width/2} 4 L ${b.width-4} 18` : `M 2 ${b.height / 2} H ${b.width - 14} M ${b.width - 28} 4 L ${b.width - 8} ${b.height / 2} L ${b.width - 28} ${b.height - 4}`,
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
          if (node.presentation?.variant) styleAnnotation(ring,leader,svg,theme,variants.find(v=>v.id===node.presentation.variant));
        }
        el.append(svg);
        if (node.type === "annotation") el.classList.add("v-annotation");
        if (node.type === "arrow") el.style.display = "flex";
      }
      const selectors = {
        text: { text: el.querySelector(".v-panel-copy") ? ".v-panel-copy" : null },
        label: { text: null },
        badge: { text: null },
        header: { title: ".v-page-title" },
        card: { title: ".v-card-title", body: ".v-card-body" },
        figure: { tag: ".v-figure-tag span", note: ".v-figure-note span" },
        summary: {
          heading: ".v-summary-heading span",
          from: ".v-state-from",
          to: ".v-state-to",
          term: ".v-term",
          takeaway: ".v-takeaway",
        },
      };
      for (const [part, style] of Object.entries(
        node.presentation?.typography || {},
      )) {
        const selector = selectors[node.type]?.[part];
        const target = selector ? el.querySelector(selector) : el;
        if (!target) fail("UNSUPPORTED_TEXT_PART", node.id, part);
        if (style.fontSizePx !== undefined)
          target.style.fontSize = px(style.fontSizePx);
        if (style.weight !== undefined)
          target.style.fontWeight = String(style.weight);
        if (style.lineHeight !== undefined)
          target.style.lineHeight = String(style.lineHeight);
        if (style.align !== undefined) target.style.textAlign = style.align;
      }
      const definition = variants.find(v => v.id === node.presentation?.variant);
      if (definition?.minWidth || definition?.minHeight) minimumChecks.push([el,definition,node.id,layout.slots[node.slot].box]);
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
    minimumChecks.forEach(([el,definition,id,box]) => checkedMeasure(() => {
      if (box.width < (definition.minWidth || 0) || box.height < (definition.minHeight || 0))
        fail("CONTENT_CAPACITY_EXCEEDED",id,`${id}: registered variant requires ${definition.minWidth}x${definition.minHeight}`);
      return {};
    },el,{width:definition.minWidth,height:definition.minHeight},id));
    textNodes.forEach(
      ([el, slot, id]) => (measurements[id] = checkedMeasure(measure, el, slot, id)),
    );
    overflowChecks.forEach(
      ([el, width, id]) =>
        (measurements[id] = checkedMeasure(measureOverflow, el, width, id)),
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
    function renderAt(ms, reduced = false, editorLayout = false) {
      if (!Number.isFinite(ms) || ms < 0 || ms > scene.durationMs)
        fail("INVALID_TIME", "timeMs", String(ms));
      time = ms;
      for (const node of scene.nodes) {
        const actions = motionsByTarget.get(node.id) || [];
        const enter = actions.find((a) => a.type === "enter");
        const p = enter ? ease("smoothstep", (ms - enter.startMs) / enter.durationMs) : 1;
        let opacity = p,
          lift = 0;
        for (const extra of actions) {
          if (extra.type === "exit") {
            const q = ease(
              "smoothstep",
              (ms - extra.startMs) / extra.durationMs,
            );
            opacity *= 1 - q;
          } else if (extra.type === "emphasize") {
            const half = extra.durationMs / 2;
            const rise = ease("smoothstep", (ms - extra.startMs) / half);
            const fall = ease(
              "smoothstep",
              (ms - (extra.startMs + half)) / half,
            );
            lift += -8 * rise * (1 - fall);
          }
        }
        const state = {
          opacity: editorLayout ? 1 : opacity,
          x: reduced || editorLayout ? 0 : (enter?.offsetX || 0) * (1 - p),
          y: editorLayout ? 0 : (reduced ? 0 : (enter?.offsetY || 0) * (1 - p)) + lift,
          lift: editorLayout ? 0 : lift,
        };
        states.set(node.id, state);
        const el = elements.get(node.id);
        if (editorLayout && opacity === 0) el.setAttribute('data-editor-hidden', 'true');
        else el.removeAttribute('data-editor-hidden');
        el.style.opacity = String(state.opacity);
        el.style.transform = `translate3d(${state.x}px,${state.y}px,0)`;
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
      for (const node of scene.nodes.filter(n=>n.type==='arrow'&&n.from)) {
        const enter=(motionsByTarget.get(node.id)||[]).find(a=>a.type==='enter');
        const progress=enter&&!editorLayout?ease('smoothstep',(ms-enter.startMs)/enter.durationMs):1;
        geometry[node.id]=drawRelation(elements.get(node.id).querySelector('svg'),node,scene,layout,states,geometry,progress);
        elements.get(node.id).style.opacity=String(Math.min(states.get(node.id).opacity,states.get(node.from.objectId).opacity,states.get(node.to.objectId).opacity));
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
        const annotationEnter = (motionsByTarget.get(node.id) || []).find(
          (a) => a.type === "enter",
        );
        const progress = annotationEnter && !editorLayout ? ease(
          "smoothstep",
          (ms - annotationEnter.startMs) / annotationEnter.durationMs,
        ) : 1;
        attributes(leader, {
          d: `M ${anchor.x - origin.x + towards * node.radius} ${anchor.y - origin.y} L ${endpoint.x - origin.x - towards * 14} ${endpoint.y - origin.y}`,
          "stroke-dashoffset": String(1 - progress),
        });
        if (node.presentation?.variant) drawAnnotationLeader(elements.get(node.id).querySelector("svg"),
          {x:anchor.x-origin.x+towards*node.radius,y:anchor.y-origin.y},
          {x:endpoint.x-origin.x-towards*14,y:endpoint.y-origin.y},progress,
          variants.find(v=>v.id===node.presentation.variant).arrowHead);
        elements.get(node.id).style.opacity = String(
          Math.min(
            states.get(node.id).opacity,
            states.get(node.targetId).opacity,
          ),
        );
        geometry[node.id] = { anchor, endpoint, radius: node.radius };
      }
      // D03: every node gets resolvable geometry — text/shape nodes carry
      // their moved box; annotation entries keep anchor/endpoint and gain
      // the full-content box used by target resolution.
      for (const node of scene.nodes) {
        const b = layout.slots[node.slot].box;
        const s = states.get(node.id);
        if (node.type === 'image') continue;
        geometry[node.id] = {
          ...(['annotation','arrow'].includes(node.type) ? geometry[node.id] : {}),
          kind: node.type,
          box: { x: b.x + s.x, y: b.y + s.y, width: b.width, height: b.height },
        };
      }
      const beat = scene.beats.find(
        (b) =>
          b.startMs <= ms &&
          (ms < b.endMs || (ms === scene.durationMs && b.endMs === ms)),
      );
      subtitleText.textContent = editorLayout ? "" : beat?.text || "";
      return { timeMs: ms, geometry, measurements, capacityIssues, subtitleFont: subtitleSize };
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
