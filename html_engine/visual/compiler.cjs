"use strict";
const validators = require("./generated/validators.cjs");
const { EngineError, diagnostic } = require("../src/registry.cjs");
const { imagePlacement } = require("../src/timeline.cjs");
const icons = require("./icons.cjs");

const SCENE_VERSIONS = ["0.1.0", "0.2.0", "0.3.0", "0.4.0"];
const SCENE_VERSION = "0.3.0";
const DEFINITION_VERSION = "0.2.0";
const EXTENDED_TEXT_ROLES = [
  "headline",
  "cardTitle",
  "cardBody",
  "caption",
  "summary",
];

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
function toRGB(hex) {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(" ");
}
// Registered defaults for optional 0.2.0 theme fields. A 0.1.0-era theme or a
// 0.2.0 theme that omits them stays valid; the renderer consumes the resolved
// shape only, so defaults live in exactly one place.
function normalizeTheme(theme) {
  const colors = theme.colors;
  const resolved = {
    colors: {
      paper: colors.paper ?? colors.panel,
      purple: colors.purple ?? colors.muted,
      yellow: colors.yellow ?? colors.accent,
      pink: colors.pink ?? colors.accent,
      ...colors,
    },
    gradients: {},
    text: {
      headline: theme.text.headline ?? theme.text.lead,
      intro: theme.text.intro ?? theme.text.body,
      cardTitle: theme.text.cardTitle ?? theme.text.stepTitle,
      cardBody: theme.text.cardBody ?? theme.text.body,
      caption: theme.text.caption ?? theme.text.body,
      summary: theme.text.summary ?? theme.text.conclusion,
      ...theme.text,
    },
    shapes: {
      cardRadius: theme.shapes.cardRadius ?? theme.shapes.labelRadius,
      figureRadius: theme.shapes.figureRadius ?? theme.shapes.labelRadius,
      iconRadius: theme.shapes.iconRadius ?? theme.shapes.badgeRadius,
      iconStroke: theme.shapes.iconStroke ?? theme.shapes.strokeWidth,
      shadowRGB: theme.shapes.shadowRGB ?? toRGB(colors.ink),
      ...theme.shapes,
    },
  };
  for (const tone of ["pink", "blue", "green", "purple", "yellow"])
    if (theme.gradients?.[tone]) resolved.gradients[tone] = theme.gradients[tone];
  return { ...theme, ...resolved };
}
// Explicit adapter: 0.1.0 scene documents are upgraded to the 0.2.0 shape.
// Their node vocabulary is a strict subset; only definition reference
// versions move to the registered 0.2.0 catalog. The adaptation is recorded
// on the compiled snapshot.
function adaptScene(scene) {
  if (scene.version === SCENE_VERSION || scene.version === "0.4.0") return { scene, adaptedFrom: null };
  if (scene.version !== "0.1.0" && scene.version !== "0.2.0")
    fail("UNSUPPORTED_VERSION", "/version", scene.version);
  return {
    scene: {
      ...scene,
      version: SCENE_VERSION,
      themeRef: { ...scene.themeRef, version: DEFINITION_VERSION },
      layoutRef: { ...scene.layoutRef, version: DEFINITION_VERSION },
    },
    adaptedFrom: scene.version,
  };
}
function validateTemplate(scene, layout, catalog) {
  if (!scene.templateRef) return null;
  const template = resolve(catalog.templates, scene.templateRef, "/templateRef");
  validate("template", template);
  if (
    template.layoutRef.id !== layout.id ||
    template.layoutRef.version !== layout.version
  )
    fail("TEMPLATE_LAYOUT_MISMATCH", "/templateRef", template.id);
  const occupied = new Map();
  for (const node of scene.nodes) {
    const rule = template.slots[node.slot];
    if (!rule) fail("TEMPLATE_SLOT_KIND", "/nodes", `${node.id}:${node.slot}`);
    if (!rule.kinds.includes(node.type))
      fail(
        "TEMPLATE_SLOT_KIND",
        "/nodes",
        `${node.id}: ${node.type} not allowed in ${node.slot}`,
      );
    occupied.set(node.slot, node.type);
  }
  for (const [slot, rule] of Object.entries(template.slots))
    if (rule.required && !occupied.has(slot))
      fail("TEMPLATE_SLOT_REQUIRED", "/templateRef", slot);
  return template;
}
function checkIcon(name, path) {
  if (!icons.isRegistered(name)) fail("UNKNOWN_ICON", path, name);
}
function compile(input, catalog) {
  const { scene, adaptedFrom } = adaptScene(
    JSON.parse(JSON.stringify(input)),
  );
  if (scene.version !== "0.4.0" && Array.isArray(scene.nodes) && scene.nodes.some((node) => node?.type === "shape"))
    fail("UNSUPPORTED_NODE_VERSION", "/nodes", "shape requires scene 0.4.0");
  validate("scene", scene);
  const theme = normalizeTheme(
    structuredClone(resolve(catalog.themes, scene.themeRef, "/themeRef")),
  );
  const layout = structuredClone(
    resolve(catalog.layouts, scene.layoutRef, "/layoutRef"),
  );
  validate("theme", theme);
  validate("layout", layout);
  if (!theme.compatibleLayouts.includes(layout.id))
    fail("INCOMPATIBLE_THEME_LAYOUT", "/layoutRef", layout.id);
  for (const node of scene.nodes) {
    if (node.type === "card") checkIcon(node.icon, `/nodes/${node.id}/icon`);
    if (node.type === "figure")
      for (const caption of [node.tag, node.note])
        if (caption) checkIcon(caption.icon, `/nodes/${node.id}/icon`);
    if (node.type === "summary" && node.heading)
      checkIcon(node.heading.icon, `/nodes/${node.id}/icon`);
  }
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
  const template = validateTemplate(scene, layout, catalog);
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
  const byTarget = new Map();
  for (const action of scene.motion) {
    if (!ids.has(action.targetId))
      fail("INVALID_MOTION_TARGET", "/motion", action.targetId);
    const list = byTarget.get(action.targetId) || [];
    if (list.some((a) => a.type === action.type))
      fail(
        "ACTION_CHANNEL_CONFLICT",
        "/motion",
        `${action.targetId}:${action.type} defined twice`,
      );
    if (action.startMs + action.durationMs > scene.durationMs)
      fail("INVALID_TIME", "/motion", action.targetId);
    list.push(action);
    byTarget.set(action.targetId, list);
  }
  for (const [targetId, list] of byTarget) {
    const enter = list.find((a) => a.type === "enter");
    if (!enter)
      fail("MISSING_MOTION", "/motion", `${targetId} requires an enter action`);
    const node = scene.nodes.find((n) => n.id === targetId);
    if (node.type === "annotation" && (enter.offsetX || enter.offsetY))
      fail(
        "INVALID_RELATION",
        "/motion",
        "Annotation follows its target; no independent offset",
      );
    const enterEnd = enter.startMs + enter.durationMs;
    const extras = list.filter((a) => a.type !== "enter");
    for (const extra of extras) {
      if (extra.startMs < enterEnd)
        fail(
          "ACTION_WINDOW_OVERLAP",
          "/motion",
          `${targetId}:${extra.type} overlaps enter`,
        );
      const nodeBox = layout.slots[node.slot].box;
      if (extra.type === "emphasize") {
        if (
          nodeBox.y - 8 < 0 ||
          nodeBox.x - 8 < 0 ||
          nodeBox.x + nodeBox.width + 8 > 1600 ||
          nodeBox.y + nodeBox.height + 8 > 800
        )
          fail(
            "CONTENT_SAFE_ZONE",
            "/motion",
            `${targetId}: emphasize lift leaves the content zone`,
          );
      }
    }
    const sortedExtras = [...extras].sort((a, b) => a.startMs - b.startMs);
    for (const [a, b] of [
      [enter, sortedExtras[0]],
      ...sortedExtras.slice(0, -1).map((w, i) => [w, sortedExtras[i + 1]]),
    ]) {
      if (b && b.startMs < a.startMs + a.durationMs)
        fail(
          "ACTION_WINDOW_OVERLAP",
          "/motion",
          `${targetId}: action windows overlap`,
        );
    }
  }
  for (const action of scene.motion) {
    const node = scene.nodes.find((n) => n.id === action.targetId);
    const b = layout.slots[node.slot].box;
    if (
      action.type === "enter" &&
      (b.x + action.offsetX < 0 ||
        b.y + action.offsetY < 0 ||
        b.x + b.width + action.offsetX > 1600 ||
        b.y + b.height + action.offsetY > 800)
    )
      fail("CONTENT_SAFE_ZONE", "/motion", action.targetId);
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
  if (byTarget.size !== ids.size)
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
    theme,
    layout,
    assets: [...assets.values()].map((a) => structuredClone(a)),
    template: template ? structuredClone(template) : null,
    adaptedFrom,
  });
}
module.exports = { compile, validate, fail, normalizeTheme };
