"use strict";

const validateSchema = require("./generated/validate-scene.cjs");
const { registry, EngineError, diagnostic } = require("./registry.cjs");
const { channels, imagePlacement, tangent } = require("./timeline.cjs");

function deepFreeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object")
    return (
      "{" +
      Object.keys(value)
        .sort()
        .map((k) => JSON.stringify(k) + ":" + canonical(value[k]))
        .join(",") +
      "}"
    );
  return JSON.stringify(value);
}

function overlaps(a, b) {
  const az = a.startMs === a.endMs,
    bz = b.startMs === b.endMs;
  if (az && bz) return a.startMs === b.startMs;
  if (az) return a.startMs >= b.startMs && a.startMs < b.endMs;
  if (bz) return b.startMs >= a.startMs && b.startMs < a.endMs;
  return a.startMs < b.endMs && b.startMs < a.endMs;
}

const samePoint = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) < 1e-6;

function compile(input) {
  if (
    input?.format !== registry.format ||
    input?.schemaVersion !== registry.schemaVersion ||
    input?.contractVersion !== registry.contractVersion
  ) {
    throw new EngineError([
      diagnostic(
        "UNSUPPORTED_VERSION",
        "/",
        "Expected hps.e1.scene 0.1.0 / contract 0.7.1; P01 is a separate format",
      ),
    ]);
  }
  const unsupported = [];
  for (const [key, supported] of [
    ["nodes", registry.nodes],
    ["actions", registry.actions],
  ]) {
    if (!Array.isArray(input[key])) continue;
    input[key].forEach((item, index) => {
      if (
        item &&
        (!supported.includes(item.type) || item.typeVersion !== "0.1.0")
      )
        unsupported.push(
          diagnostic(
            "UNSUPPORTED_CAPABILITY",
            `/${key}/${index}`,
            "Unknown type or type version",
            key === "nodes" ? item.id : undefined,
          ),
        );
    });
  }
  if (unsupported.length) throw new EngineError(unsupported);
  if (!validateSchema(input)) {
    throw new EngineError(
      validateSchema.errors
        .slice(0, 40)
        .map((e) =>
          diagnostic(
            "INVALID_FIELD",
            e.instancePath +
              (e.keyword === "additionalProperties"
                ? "/" + e.params.additionalProperty
                : ""),
            e.message,
          ),
        ),
    );
  }
  const source = deepFreeze(JSON.parse(JSON.stringify(input)));
  const errors = [];
  const add = (code, path, message, nodeId) =>
    errors.push(diagnostic(code, path, message, nodeId));
  const maps = {};
  for (const key of [
    "nodes",
    "assets",
    "paths",
    "beats",
    "actions",
    "keyframes",
  ]) {
    maps[key] = new Map();
    source[key].forEach((item, index) => {
      if (maps[key].has(item.id))
        add(
          "DUPLICATE_ID",
          `/${key}/${index}/id`,
          `Duplicate ${key} ID ${item.id}`,
        );
      maps[key].set(item.id, item);
    });
  }
  if (source.templateRef.id !== registry.template.id)
    add(
      "UNSUPPORTED_CAPABILITY",
      "/templateRef",
      "Only the open-stage E1 recipe is implemented",
    );
  if (
    source.assets.reduce(
      (sum, a) => sum + a.intrinsic.width * a.intrinsic.height,
      0,
    ) > registry.limits.resourcePixels
  )
    add("RESOURCE_BUDGET", "/assets", "Declared asset pixel budget exceeded");
  const safe = source.canvas.safeInsets,
    width = source.canvas.width,
    height = source.canvas.height;
  if (safe.left + safe.right >= width || safe.top + safe.bottom >= height)
    add("INVALID_LAYOUT", "/canvas/safeInsets", "Insets consume canvas");
  source.assets.forEach((asset, index) => {
    if (asset.file.path.split("/").some((p) => !p || p === "." || p === ".."))
      add(
        "INVALID_RESOURCE_PATH",
        `/assets/${index}/file/path`,
        "Asset path must be normalized inside package",
      );
    const r = asset.alphaBounds,
      sz = asset.intrinsic;
    if (
      r.x < 0 ||
      r.y < 0 ||
      r.x + r.width > sz.width ||
      r.y + r.height > sz.height
    )
      add(
        "INVALID_ASSET_GEOMETRY",
        `/assets/${index}/alphaBounds`,
        "alphaBounds outside intrinsic size",
      );
    if (new Set(asset.anchors.map((a) => a.id)).size !== asset.anchors.length)
      add(
        "DUPLICATE_ID",
        `/assets/${index}/anchors`,
        "Duplicate resource anchor",
      );
  });
  source.nodes.forEach((node, index) => {
    const path = `/nodes/${index}`;
    if (node.type === "image") {
      const asset = maps.assets.get(node.assetRef.id);
      if (!asset || asset.version !== node.assetRef.version)
        add(
          "MISSING_REFERENCE",
          path + "/assetRef",
          "Missing exact resource version",
          node.id,
        );
      else if (!asset.anchors.some((a) => a.id === node.anchorId))
        add(
          "MISSING_REFERENCE",
          path + "/anchorId",
          "Missing resource anchor",
          node.id,
        );
    }
    if (node.type === "path" && !maps.paths.has(node.pathId))
      add("MISSING_REFERENCE", path + "/pathId", "Missing curve", node.id);
    if (
      node.type === "ring" &&
      Math.min(node.box.width, node.box.height) <= node.strokeWidth
    )
      add(
        "INVALID_VECTOR_GEOMETRY",
        path + "/box",
        "Ring stroke does not fit its declared box",
        node.id,
      );
    if (node.type === "text") {
      const b = node.box;
      if (
        b.x < safe.left ||
        b.y < safe.top ||
        b.x + b.width > width - safe.right ||
        b.y + b.height > height - safe.bottom
      )
        add(
          "INVALID_LAYOUT",
          path + "/box",
          "Text box must fit declared reading safe area",
          node.id,
        );
    }
  });
  const beats = [...source.beats].sort(
    (a, b) => a.startMs - b.startMs || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
  );
  beats.forEach((beat, i) => {
    if (beat.startMs >= beat.endMs || beat.endMs > source.durationMs)
      add(
        "TIMING_OUT_OF_RANGE",
        `/beats/${source.beats.indexOf(beat)}`,
        "Beat must have positive duration inside scene",
      );
    if (i && beats[i - 1].endMs > beat.startMs)
      add("BEAT_CONFLICT", "/beats", "Narration beat intervals overlap");
    if (new Set(beat.targetIds).size !== beat.targetIds.length)
      add("DUPLICATE_REFERENCE", "/beats", "Duplicate beat target");
    for (const id of beat.targetIds)
      if (!maps.nodes.has(id))
        add("MISSING_REFERENCE", "/beats", `Missing beat target ${id}`);
  });
  for (const frame of source.keyframes)
    if (frame.tMs > source.durationMs)
      add("TIMING_OUT_OF_RANGE", "/keyframes", "Keyframe exceeds scene");
  if (
    !source.keyframes.some((k) => k.tMs === 0) ||
    !source.keyframes.some((k) => k.tMs === source.durationMs)
  )
    add(
      "INCOMPLETE_KEYFRAMES",
      "/keyframes",
      "Initial and final keyframes required",
    );
  const actions = [...source.actions].sort(
    (a, b) => a.startMs - b.startMs || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
  );
  const tracks = new Map();
  actions.forEach((action) => {
    const node = maps.nodes.get(action.target.nodeId),
      path = `/actions/${source.actions.indexOf(action)}`;
    if (action.startMs > action.endMs || action.endMs > source.durationMs)
      add("TIMING_OUT_OF_RANGE", path, "Action interval outside scene");
    if (!node) {
      add("MISSING_REFERENCE", path + "/target", "Missing action target");
      return;
    }
    if (
      (action.type === "move-path" || action.type === "rotate") &&
      node.type !== "image"
    )
      add(
        "TARGET_CAPABILITY",
        path + "/target",
        "Position/rotation supports whole Image only",
        node.id,
      );
    if (action.type === "path-progress" && node.type !== "path")
      add(
        "TARGET_CAPABILITY",
        path + "/target",
        "Progress requires a Path",
        node.id,
      );
    if (action.type === "move-path") {
      if (!maps.paths.has(action.pathId))
        add(
          "MISSING_REFERENCE",
          path + "/pathId",
          "Missing motion curve",
          node.id,
        );
      if (
        action.orientation.kind === "tangent" &&
        action.orientation.minDeg > action.orientation.maxDeg
      )
        add(
          "INVALID_FIELD",
          path + "/orientation",
          "minDeg must not exceed maxDeg",
        );
    }
    for (const channel of channels(action)) {
      const key = node.id + ":" + channel;
      if (!tracks.has(key)) tracks.set(key, []);
      tracks.get(key).push(action);
    }
  });
  // Validate references first; channel continuity needs complete images and paths.
  if (errors.length) throw new EngineError(errors);
  for (const [key, track] of tracks) {
    const separator = key.lastIndexOf(":"),
      node = maps.nodes.get(key.slice(0, separator)),
      channel = key.slice(separator + 1);
    for (let i = 0; i < track.length; i++) {
      const current = track[i],
        previous = track[i - 1];
      for (let j = 0; j < i; j++)
        if (overlaps(track[j], current))
          add(
            "ACTION_CONFLICT",
            "/actions",
            `Overlapping ${channel} actions on ${node.id}`,
            node.id,
          );
      if (channel === "opacity" || channel === "progress") {
        const expected = previous
          ? previous.to
          : channel === "opacity"
            ? node.initialOpacity
            : node.initialProgress;
        if (Math.abs(current.from - expected) > 1e-6)
          add(
            "STATE_DISCONTINUITY",
            "/actions",
            `Discontinuous ${channel} value`,
            node.id,
          );
      }
      if (channel === "position") {
        const placement = imagePlacement(
          node,
          maps.assets.get(node.assetRef.id),
        );
        const expected = previous
          ? maps.paths.get(previous.pathId).points[3]
          : {
              x: node.box.x + placement.anchor.x,
              y: node.box.y + placement.anchor.y,
            };
        if (!samePoint(expected, maps.paths.get(current.pathId).points[0]))
          add(
            "STATE_DISCONTINUITY",
            "/actions",
            "Curve starts away from held anchor position",
            node.id,
          );
      }
      if (channel === "rotation") {
        const terminal = (a) =>
          a.type === "rotate"
            ? a.toDeg
            : tangent(
                maps.paths.get(a.pathId).points,
                1,
                a.orientation,
                node.rotationDeg,
              );
        const expected = previous ? terminal(previous) : node.rotationDeg;
        const initial =
          current.type === "rotate"
            ? current.fromDeg
            : tangent(
                maps.paths.get(current.pathId).points,
                0,
                current.orientation,
                node.rotationDeg,
              );
        if (Math.abs(initial - expected) > 1e-6)
          add(
            "STATE_DISCONTINUITY",
            "/actions",
            "Rotation starts away from held angle",
            node.id,
          );
      }
    }
  }
  const nodes = [...source.nodes].sort(
    (a, b) => a.zIndex - b.zIndex || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
  );
  let layers = 0,
    lastWasCanvas = false;
  for (const n of nodes) {
    if (n.type !== "text" && !lastWasCanvas) layers++;
    lastWasCanvas = n.type !== "text";
  }
  if (layers * width * height > registry.limits.canvasPixels)
    add("CAPABILITY_BUDGET", "/nodes", "Canvas layer pixel budget exceeded");
  if (errors.length) throw new EngineError(errors);
  return {
    source,
    nodes,
    nodeMap: maps.nodes,
    assets: maps.assets,
    paths: maps.paths,
    actions,
    canonicalInput: canonical(source),
    snapshot: {
      format: "hps.e1.compiled",
      engineVersion: "0.1.0",
      source,
      orderedNodeIds: nodes.map((n) => n.id),
      orderedActionIds: actions.map((a) => a.id),
      timingMode: "manual",
      canvasLayers: layers,
    },
  };
}

module.exports = { compile, canonical, overlaps };
