"use strict";
const validators = require("./generated/validators.cjs");
const { EngineError, diagnostic } = require("../src/registry.cjs");
const { imagePlacement } = require("../src/timeline.cjs");

function fail(code, path, message) {
  throw new EngineError([diagnostic(code, path, message)]);
}
function validate(kind, value) {
  if (!validators[kind](value))
    fail(
      "INVALID_VISUAL_DEFINITION",
      kind,
      JSON.stringify(validators[kind].errors),
    );
}
function resolve(collection, ref, kind) {
  const value = collection.find(
    (v) => v.id === ref.id && v.version === ref.version,
  );
  if (!value) fail("UNRESOLVED_REFERENCE", kind, `${ref.id}@${ref.version}`);
  return value;
}
function freeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}
function compile(input, catalog) {
  const scene = JSON.parse(JSON.stringify(input));
  validate("scene", scene);
  const theme = resolve(catalog.themes, scene.themeRef, "/themeRef");
  const layout = resolve(catalog.layouts, scene.layoutRef, "/layoutRef");
  validate("theme", theme);
  validate("layout", layout);
  if (!theme.compatibleLayouts.includes(layout.id))
    fail("INCOMPATIBLE_THEME_LAYOUT", "/layoutRef", layout.id);
  const ids = new Set(),
    slots = new Set(),
    assets = new Map();
  for (const node of scene.nodes) {
    if (ids.has(node.id) || slots.has(node.slot))
      fail("DUPLICATE_TARGET", "/nodes", node.id);
    ids.add(node.id);
    slots.add(node.slot);
    const slot = layout.slots[node.slot];
    if (!Object.hasOwn(layout.slots, node.slot))
      fail("UNRESOLVED_SLOT", "/nodes", node.slot);
    const b = slot.box;
    if (b.x + b.width > 1600 || b.y + b.height > 800)
      fail("CONTENT_SAFE_ZONE", "/layout/slots", node.slot);
    if (node.type === "image") {
      const asset = resolve(catalog.assets, node.assetRef, "/assetRef");
      if (!asset.anchors.some((a) => a.id === node.anchorId))
        fail("UNRESOLVED_ANCHOR", "/nodes", node.anchorId);
      assets.set(asset.id, asset);
    }
  }
  if (scene.nodes.filter((n) => n.type === "image").length > 1)
    fail(
      "ASSET_BUDGET_EXCEEDED",
      "/nodes",
      "This version allows one image subject",
    );
  for (const n of scene.nodes.filter((n) => n.type === "annotation")) {
    const target = scene.nodes.find((v) => v.id === n.targetId);
    const label = scene.nodes.find((v) => v.id === n.labelId);
    if (!target || target.type !== "image" || !label || label.type !== "text")
      fail("INVALID_RELATION", "/nodes", n.id);
    if (
      !assets.get(target.assetRef.id).anchors.some((a) => a.id === n.anchorId)
    )
      fail("UNRESOLVED_ANCHOR", "/nodes", n.anchorId);
  }
  const animated = new Set();
  for (const action of scene.motion) {
    if (!ids.has(action.targetId) || animated.has(action.targetId))
      fail("INVALID_MOTION_TARGET", "/motion", action.targetId);
    animated.add(action.targetId);
    if (action.startMs + action.durationMs > scene.durationMs)
      fail("INVALID_TIME", "/motion", action.targetId);
    const node = scene.nodes.find((n) => n.id === action.targetId);
    const b = layout.slots[node.slot].box;
    if (
      b.x + action.offsetX < 0 ||
      b.y + action.offsetY < 0 ||
      b.x + b.width + action.offsetX > 1600 ||
      b.y + b.height + action.offsetY > 800
    )
      fail("CONTENT_SAFE_ZONE", "/motion", action.targetId);
    if (node.type === "annotation" && (action.offsetX || action.offsetY))
      fail(
        "INVALID_RELATION",
        "/motion",
        "Annotation follows its target; no independent offset",
      );
  }
  for (const n of scene.nodes.filter((v) => v.type === "annotation")) {
    const own = layout.slots[n.slot].box;
    if (own.x !== 0 || own.y !== 0 || own.width !== 1600 || own.height !== 800)
      fail(
        "INVALID_RELATION",
        "/nodes",
        "Annotation uses the full content coordinate space",
      );
    const target = scene.nodes.find((v) => v.id === n.targetId);
    const asset = assets.get(target.assetRef.id),
      b = layout.slots[target.slot].box;
    const placement = imagePlacement(
      { ...target, box: b, anchorId: n.anchorId },
      asset,
    );
    const action = scene.motion.find((a) => a.targetId === target.id);
    for (const state of [
      { x: 0, y: 0 },
      { x: action.offsetX, y: action.offsetY },
    ]) {
      const x = b.x + placement.anchor.x + state.x,
        y = b.y + placement.anchor.y + state.y;
      if (
        x - n.radius < 0 ||
        x + n.radius > 1600 ||
        y - n.radius < 0 ||
        y + n.radius > 800
      )
        fail(
          "CONTENT_SAFE_ZONE",
          "/nodes",
          n.id + ": annotation circle leaves content zone",
        );
    }
  }
  if (animated.size !== ids.size)
    fail("MISSING_MOTION", "/motion", "Every node requires an enter action");
  let end = 0;
  for (const beat of scene.beats) {
    if (
      beat.startMs < end ||
      beat.endMs <= beat.startMs ||
      beat.endMs > scene.durationMs
    )
      fail(
        "INVALID_TIME",
        "/beats",
        "Beats must be ordered and non-overlapping",
      );
    end = beat.endMs;
  }
  return freeze({
    source: scene,
    theme: structuredClone(theme),
    layout: structuredClone(layout),
    assets: [...assets.values()].map((a) => structuredClone(a)),
  });
}
module.exports = { compile, validate, fail };
