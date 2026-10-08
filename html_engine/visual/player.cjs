"use strict";
const { compile } = require("./compiler.cjs"),
  { prepare } = require("./renderer.cjs");
const { catalog, scenes, pack } = window.VisualData;
const $ = (id) => document.getElementById(id);
let current,
  playing = false,
  epoch = 0,
  frame = 0,
  generation = 0;
const status = (value) => ($("status").textContent = value);
function pause() {
  playing = false;
  cancelAnimationFrame(frame);
  $("play").textContent = "播放";
}
function seek(ms) {
  if (!current) return null;
  const result = current.renderAt(ms, $("reduced").checked);
  $("seek").value = ms;
  $("time").textContent = (ms / 1000).toFixed(1) + " s";
  return result;
}
function tick(now) {
  if (!playing) return;
  const ms = Math.min(current.scene.durationMs, now - epoch);
  seek(ms);
  if (ms === current.scene.durationMs) pause();
  else frame = requestAnimationFrame(tick);
}
function play() {
  if (!current) return;
  pause();
  if (current.timeMs === current.scene.durationMs) seek(0);
  playing = true;
  epoch = performance.now() - current.timeMs;
  $("play").textContent = "暂停";
  frame = requestAnimationFrame(tick);
}
async function apply(source, projectResources = null) {
  const request = ++generation;
  const staging = document.createElement("div");
  Object.assign(staging.style, {
    position: "absolute",
    left: "0",
    top: "0",
    width: `${$("viewport").clientWidth}px`,
    visibility: "hidden",
    pointerEvents: "none",
  });
  document.body.append(staging);
  let candidate;
  try {
    const activeCatalog = projectResources ?
      { ...catalog, assets: [...catalog.assets.filter(a =>
          !projectResources.assets.some(p => p.id === a.id)), ...projectResources.assets] } : catalog;
    candidate = await prepare(compile(source, activeCatalog),
      projectResources ? { ...pack, ...projectResources.pack } : pack, staging);
    candidate.setSubtitleFont(Number($("font").value));
    if (request !== generation) {
      candidate.release();
      return false;
    }
    pause();
    current?.release();
    // Keep the measurement host so the renderer observes the committed viewport.
    $("viewport").replaceChildren(staging);
    Object.assign(staging.style, {
      position: "relative",
      width: "100%",
      visibility: "visible",
      pointerEvents: "auto",
    });
    current = candidate;
    $("seek").max = source.durationMs;
    seek(0);
    status("就绪 · 定义、字体、资产与容量检查通过");
    return true;
  } catch (e) {
    candidate?.release();
    if (request === generation) status("未应用：" + e.message);
    return false;
  } finally {
    if (!candidate || request !== generation || current !== candidate)
      staging.remove();
  }
}
scenes.forEach((s) => {
  const o = document.createElement("option");
  o.value = s.id;
  o.textContent = s.name;
  $("scene").append(o);
});
catalog.themes.forEach((t) => {
  const o = document.createElement("option");
  o.value = t.id;
  o.textContent = t.name;
  $("theme").append(o);
});
function loadSelection() {
  const source = structuredClone(scenes.find((s) => s.id === $("scene").value));
  source.themeRef.id = $("theme").value;
  $("definition").value = JSON.stringify(source, null, 2);
  return apply(source);
}
$("scene").onchange = loadSelection;
$("theme").onchange = loadSelection;
$("apply").onclick = () => {
  try {
    apply(JSON.parse($("definition").value));
  } catch (e) {
    status("未应用：" + e.message);
  }
};
$("play").onclick = () => (playing ? pause() : play());
$("end").onclick = () => {
  if (!current) return;
  pause();
  seek(current.scene.durationMs);
};
$("seek").oninput = () => {
  pause();
  seek(Number($("seek").value));
};
$("reduced").onchange = () => {
  if (current) seek(current.timeMs);
};
$("font").oninput = () => {
  try {
    current.setSubtitleFont(Number($("font").value));
    $("font-value").textContent = $("font").value;
    status("字幕字号已更新");
  } catch (e) {
    status(e.message);
  }
};
const selected = new URLSearchParams(location.search).get("scene");
if (scenes.some((s) => s.id === selected)) $("scene").value = selected;
window.visualPlayer = {
  apply,
  play,
  pause,
  seek,
  get playing() {
    return playing;
  },
  get scene() {
    return current?.scene;
  },
  get ready() {
    return Boolean(current);
  },
  setSubtitleFont(size) {
    current.setSubtitleFont(size);
  },
  get timeMs() {
    return current?.timeMs;
  },
};
loadSelection();
