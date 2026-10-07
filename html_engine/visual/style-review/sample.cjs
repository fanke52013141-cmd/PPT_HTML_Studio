"use strict";
const style = require("./style.json"),
  layout = require("./layout.json"),
  contents = require("./content.cjs");
const { icon } = require("./icons.cjs");
const { loadResources, fontPresent } = require("../../src/resources.cjs");
const { imagePlacement, ease } = require("../../src/timeline.cjs");
const { catalog, pack } = window.VisualData;
const $ = (id) => document.getElementById(id),
  svgNS = "http://www.w3.org/2000/svg";
let current,
  playing = false,
  request = 0,
  frame = 0,
  epoch = 0;
const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
const setBox = (node, box) =>
  Object.assign(node.style, {
    left: `${box.x}px`,
    top: `${box.y}px`,
    width: `${box.width}px`,
    height: `${box.height}px`,
  });
const svg = (tag, attrs) => {
  const node = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  return node;
};
function pause() {
  playing = false;
  cancelAnimationFrame(frame);
  $("play").textContent = "播放讲解";
}

async function prepare(content, host) {
  if (!fontPresent(style.font)) throw new Error("缺少字体：" + style.font);
  await document.fonts.ready;
  const asset = catalog.assets.find(
    (a) =>
      a.id === content.assetRef.id && a.version === content.assetRef.version,
  );
  if (!asset) throw new Error("资产引用无效");
  const resources = await loadResources({ source: { assets: [asset] } }, pack);
  const stage = el("div", "scene");
  stage.dataset.sceneId = content.id;
  stage.style.fontFamily = `"${style.font}"`;
  for (const [key, value] of Object.entries(style.colors))
    stage.style.setProperty(`--${key}`, value);
  for (const [key, values] of Object.entries(style.gradients))
    values.forEach((v, i) => stage.style.setProperty(`--${key}-${i}`, v));
  for (const [key, value] of Object.entries(style.shapes))
    stage.style.setProperty(`--${key}`, String(value));
  for (const [key, value] of Object.entries(style.typography)) {
    stage.style.setProperty(`--${key}-size`, `${value.size}px`);
    stage.style.setProperty(`--${key}-weight`, String(value.weight));
    stage.style.setProperty(`--${key}-height`, String(value.height));
  }
  const targets = new Map();
  function add(id, className, box, start = 0) {
    const node = el("div", className);
    node.dataset.objectId = id;
    setBox(node, box);
    stage.append(node);
    targets.set(id, { node, start });
    return node;
  }
  try {
    const header = add("header", "header", layout.header);
    header.append(
      el("span", "page-number", content.number),
      el("h1", "page-title", content.title),
    );
    const headline = add("headline", "headline", layout.headline, 350);
    headline.textContent = content.headline;
    const intro = add("intro", "intro", layout.intro, 600);
    intro.textContent = content.intro;
    content.rows.forEach((row, i) => {
      const node = add(
        `fact-${i}`,
        "fact",
        layout.rows[i],
        [2000, 5000, 8500][i],
      );
      node.dataset.tone = row.tone;
      const bubble = el("span", "icon-bubble");
      bubble.append(icon(row.icon, { width: style.shapes.iconStroke }));
      const copy = el("div", "fact-copy");
      copy.append(
        el("h2", "fact-title", row.title),
        el("p", "fact-body", row.body),
      );
      node.append(bubble, copy);
    });
    const figure = add("figure", "figure", layout.figure, 700);
    const tag = el("div", "figure-tag");
    tag.append(icon("eye"), el("span", "", content.figureTitle));
    figure.append(tag);
    const halo = el("div", "figure-halo");
    figure.append(halo);
    const note = el("div", "figure-note");
    note.append(icon("droplet"), el("span", "", content.figureNote));
    figure.append(note);
    const subject = add("subject", "subject", layout.subject, 700);
    const placement = imagePlacement(
        { box: layout.subject, anchorId: content.anchorId },
        asset,
      ),
      img = resources.images.get(asset.id);
    Object.assign(img.style, {
      position: "absolute",
      left: `${placement.x}px`,
      top: `${placement.y}px`,
      width: `${placement.width}px`,
      height: `${placement.height}px`,
    });
    img.alt = "";
    subject.append(img);
    const relation = add(
      "annotation",
      "annotation",
      { x: 0, y: 0, width: 1600, height: 800 },
      12000,
    );
    const relationSvg = svg("svg", {
      viewBox: "0 0 1600 800",
      width: 1600,
      height: 800,
    });
    const ring = svg("circle", {
      r: 21,
      fill: "none",
      stroke: style.colors.pink,
      "stroke-width": style.shapes.strokeWidth,
    });
    const leader = svg("path", {
      fill: "none",
      stroke: style.colors.pink,
      "stroke-width": style.shapes.strokeWidth,
      "stroke-linecap": "round",
    });
    relationSvg.append(ring, leader);
    relation.append(relationSvg);
    const anchorLabel = add(
      "anchor-label",
      "anchor-label",
      layout.anchorLabel,
      12300,
    );
    anchorLabel.textContent = content.annotation;
    const summary = add("summary", "summary", layout.summary, 14000);
    const summaryHeading = el("div", "summary-heading");
    summaryHeading.append(icon("lightbulb"), el("span", "", "关键结论"));
    const flow = el("div", "flow");
    const from = el("span", "state from", content.from),
      arrow = icon("arrow"),
      to = el("span", "state to", content.to),
      term = el("span", "term", `这个过程叫${content.term}`);
    flow.append(from, arrow, to, term);
    summary.append(
      summaryHeading,
      flow,
      el("strong", "takeaway", content.summary),
    );
    const subtitle = el("div", "subtitle");
    subtitle.dataset.track = "subtitle";
    subtitle.style.fontSize = $("font").value + "px";
    stage.append(subtitle);
    host.append(stage);
    const resize = () => {
      const scale = host.clientWidth / 1600;
      stage.style.transform = `scale(${scale})`;
      host.style.height = `${scale * 900}px`;
    };
    resize();
    for (const selector of [
      ".page-title",
      ".headline",
      ".intro",
      ".fact-copy",
      ".anchor-label",
      ".flow",
      ".takeaway",
    ]) {
      for (const node of stage.querySelectorAll(selector))
        if (
          node.scrollWidth > node.clientWidth + 1 ||
          node.scrollHeight > node.clientHeight + 1
        )
          throw new Error("文字容量超出：" + selector);
    }
    let time = 18000;
    function renderAt(ms) {
      if (!Number.isFinite(ms) || ms < 0 || ms > content.durationMs)
        throw new Error("时间超出范围");
      time = ms;
      const reduced = $("reduced").checked;
      for (const [id, { node, start }] of targets) {
        const p = ease("smoothstep", (ms - start) / 800);
        node.style.opacity = String(p);
        node.style.transform = `translateY(${reduced || ["annotation", "anchor-label"].includes(id) ? 0 : (1 - p) * 12}px)`;
      }
      const subjectProgress = ease("smoothstep", (ms - 700) / 800),
        dy = reduced ? 0 : (1 - subjectProgress) * 12;
      const anchor = {
        x: layout.subject.x + placement.anchor.x,
        y: layout.subject.y + placement.anchor.y + dy,
      };
      ring.setAttribute("cx", anchor.x);
      ring.setAttribute("cy", anchor.y);
      const b = layout.anchorLabel,
        end = { x: b.x - 12, y: b.y + b.height / 2 };
      leader.setAttribute(
        "d",
        `M ${anchor.x + 21} ${anchor.y} L ${end.x - 22} ${anchor.y} L ${end.x} ${end.y}`,
      );
      const p = ease("smoothstep", (ms - 12000) / 600);
      leader.setAttribute("pathLength", 1);
      leader.style.strokeDasharray = "1";
      leader.style.strokeDashoffset = String(1 - p);
      const beat = content.beats.find(
        (b) =>
          ms >= b.startMs &&
          (ms < b.endMs || (ms === content.durationMs && b.endMs === ms)),
      );
      subtitle.textContent = beat?.text || "";
      return { timeMs: ms, anchor, subject: layout.subject, placement };
    }
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    renderAt(time);
    return {
      content,
      stage,
      renderAt,
      get timeMs() {
        return time;
      },
      setSubtitleFont(size) {
        if (!Number.isFinite(size) || size < 20 || size > 44)
          throw new Error("字幕字号范围20—44");
        const previous = subtitle.style.fontSize;
        subtitle.style.fontSize = size + "px";
        try {
          for (const b of content.beats) {
            subtitle.textContent = b.text;
            if (subtitle.scrollHeight > 100 || subtitle.scrollWidth > 1600)
              throw new Error("字幕超出固定区域");
          }
        } catch (e) {
          subtitle.style.fontSize = previous;
          renderAt(time);
          throw e;
        }
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
function seek(ms) {
  if (!current) return;
  const result = current.renderAt(ms);
  $("seek").value = ms;
  $("time").textContent = (ms / 1000).toFixed(1) + " s";
  return result;
}
function tick(now) {
  if (!playing) return;
  const ms = Math.min(current.content.durationMs, now - epoch);
  seek(ms);
  if (ms === current.content.durationMs) pause();
  else frame = requestAnimationFrame(tick);
}
function play() {
  if (!current) return;
  pause();
  if (current.timeMs === current.content.durationMs) seek(0);
  playing = true;
  epoch = performance.now() - current.timeMs;
  $("play").textContent = "暂停";
  frame = requestAnimationFrame(tick);
}
async function load(id) {
  const generation = ++request,
    content = contents.find((c) => c.id === id);
  if (!content) throw new Error("Unknown content");
  const host = el("div", "mount");
  host.style.width = $("viewport").clientWidth + "px";
  host.style.position = "absolute";
  host.style.visibility = "hidden";
  document.body.append(host);
  let candidate;
  try {
    candidate = await prepare(content, host);
    if (generation !== request) {
      candidate.release();
      return false;
    }
    pause();
    current?.release();
    $("viewport").replaceChildren(host);
    host.style.position = "relative";
    host.style.width = "100%";
    host.style.visibility = "visible";
    current = candidate;
    seek(18000);
    $("status").textContent = "实际 CSS/SVG＋原插画 · 风格视觉审阅中";
    return true;
  } catch (e) {
    candidate?.release();
    $("status").textContent = "未应用：" + e.message;
    return false;
  } finally {
    if (!candidate || current !== candidate) host.remove();
  }
}
for (const c of contents) {
  const option = el("option", "", c.title);
  option.value = c.id;
  $("scene").append(option);
}
$("scene").onchange = () => load($("scene").value);
$("play").onclick = () => (playing ? pause() : play());
$("end").onclick = () => {
  pause();
  seek(18000);
};
$("seek").oninput = () => {
  pause();
  seek(Number($("seek").value));
};
$("reduced").onchange = () => seek(current?.timeMs || 0);
$("font").oninput = () => {
  try {
    current?.setSubtitleFont(Number($("font").value));
    $("font-value").textContent = $("font").value;
  } catch (e) {
    $("status").textContent = e.message;
  }
};
window.scienceStyleReview = {
  load,
  seek,
  play,
  pause,
  setSubtitleFont: (size) => current.setSubtitleFont(size),
  get ready() {
    return Boolean(current);
  },
  get timeMs() {
    return current?.timeMs;
  },
  get content() {
    return current?.content;
  },
};
load(contents[0].id);
