"use strict";

const VERSION = "0.1.0";
const registry = Object.freeze({
  format: "hps.e1.scene",
  schemaVersion: VERSION,
  contractVersion: "0.7.1",
  template: { id: "layout.open-stage.e1", version: VERSION },
  nodes: ["text", "image", "path", "ring"],
  actions: ["opacity", "move-path", "rotate", "path-progress"],
  scope: "single-scene design-exploration; manual timing; fixed camera",
  limits: {
    canvasPixels: 32000000,
    resourcePixels: 16000000,
    pathSamples: 128,
  },
  output: {
    HTML: "prototype",
    video: "same-time-evaluator; standalone export",
    PPTX: "unsupported",
  },
});

class EngineError extends Error {
  constructor(diagnostics) {
    super(diagnostics.map((d) => `${d.code}: ${d.message}`).join("\n"));
    this.name = "EngineError";
    this.diagnostics = diagnostics;
    this.code = diagnostics[0]?.code || "ENGINE_ERROR";
  }
}

function diagnostic(code, path, message, nodeId) {
  return {
    code,
    severity: "error",
    path,
    message,
    ...(nodeId ? { nodeId } : {}),
  };
}

module.exports = { registry, EngineError, diagnostic };
