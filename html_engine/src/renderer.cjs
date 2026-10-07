"use strict";

const { compile } = require("./compiler.cjs");
const { EngineError, diagnostic, registry } = require("./registry.cjs");
const { evaluate, curve, imagePlacement, matrix } = require("./timeline.cjs");
const { sha256, loadResources, fontPresent } = require("./resources.cjs");
const { geometry, textRects } = require("./geometry.cjs");

class SceneRenderer {
  constructor(host, compiled) {
    this.host = host;
    this.compiled = compiled;
    this.textElements = new Map();
    this.layers = [];
    this.resources = null;
    const scene = compiled.source;
    this.root = document.createElement("section");
    this.root.className = "e1-stage";
    this.root.dataset.sceneId = scene.id;
    this.root.setAttribute("aria-label", scene.title);
    Object.assign(this.root.style, {
      width: `${scene.canvas.width}px`,
      height: `${scene.canvas.height}px`,
      position: "absolute",
      left: "0",
      top: "0",
      transformOrigin: "0 0",
      overflow: "hidden",
      visibility: "hidden",
      background: `radial-gradient(ellipse at 82% 50%,${scene.style.background.rightGlow},transparent 48%),radial-gradient(ellipse at 15% 70%,${scene.style.background.leftGlow},transparent 42%),${scene.style.background.base}`,
    });
    let canvasLayer = null;
    for (const node of compiled.nodes) {
      if (node.type === "text") {
        canvasLayer = null;
        const element = document.createElement("div"),
          role = scene.style.textRoles[node.role];
        element.dataset.target = node.id;
        element.className = "e1-text";
        Object.assign(element.style, {
          position: "absolute",
          left: `${node.box.x}px`,
          top: `${node.box.y}px`,
          width: `${node.box.width}px`,
          height: `${node.box.height}px`,
          fontFamily: `"${scene.style.fontFamily}"`,
          fontSize: `${role.fontSize}px`,
          fontWeight: String(role.fontWeight),
          lineHeight: String(role.lineHeight),
          color: role.color,
          textAlign: role.align,
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
        });
        this.root.appendChild(element);
        this.textElements.set(node.id, element);
      } else {
        if (!canvasLayer) {
          const canvas = document.createElement("canvas");
          canvas.width = scene.canvas.width;
          canvas.height = scene.canvas.height;
          canvas.setAttribute("aria-hidden", "true");
          Object.assign(canvas.style, {
            position: "absolute",
            inset: "0",
            pointerEvents: "none",
          });
          const context = canvas.getContext("2d", { willReadFrequently: true });
          if (!context)
            throw new EngineError([
              diagnostic("RENDERER_UNAVAILABLE", "/", "Canvas 2D unavailable"),
            ]);
          canvasLayer = { canvas, context, nodes: [] };
          this.layers.push(canvasLayer);
          this.root.appendChild(canvas);
        }
        canvasLayer.nodes.push(node);
      }
    }
    host.appendChild(this.root);
    this.fit();
  }

  fit() {
    const scale = this.host.clientWidth / this.compiled.source.canvas.width;
    this.root.style.transform = `scale(${scale})`;
  }

  async prepare(pack) {
    this.resources = await loadResources(this.compiled, pack);
    await document.fonts.ready;
    if (!fontPresent(this.compiled.source.style.fontFamily))
      throw new EngineError([
        diagnostic(
          "FONT_UNAVAILABLE",
          "/style/fontFamily",
          "Requested system font was not detected; no silent fallback",
        ),
      ]);
    const errors = [];
    for (const node of this.compiled.nodes) {
      if (node.type !== "text") continue;
      const element = this.textElements.get(node.id),
        role = this.compiled.source.style.textRoles[node.role];
      const variants =
        node.content.kind === "static"
          ? [node.content.text]
          : [...new Set(this.compiled.source.beats.map((b) => b.screenText))];
      for (const text of variants) {
        element.textContent = text;
        const rects = textRects(
          element,
          this.root,
          this.compiled.source.canvas.width,
        );
        const rows = new Set(rects.map((r) => Math.round(r.y * 10) / 10));
        const b = node.box;
        if (
          rows.size > role.maxLines ||
          rects.some(
            (r) =>
              r.x < b.x - 0.5 ||
              r.x + r.width > b.x + b.width + 0.5 ||
              r.y < b.y - 0.5 ||
              r.y + r.height > b.y + b.height + 0.5,
          )
        ) {
          errors.push(
            diagnostic(
              "CONTENT_CAPACITY_EXCEEDED",
              "/nodes/" + node.id,
              `Text exceeds ${role.maxLines} lines or its box; revise content/layout without shrinking font`,
              node.id,
            ),
          );
          break;
        }
      }
    }
    if (errors.length) throw new EngineError(errors);
    this.fingerprint = await sha256(
      new TextEncoder().encode(this.compiled.canonicalInput),
    );
    this.renderAt(0);
  }

  renderAt(timeMs) {
    if (!this.resources)
      throw new EngineError([
        diagnostic("NOT_READY", "/", "Resource preparation incomplete"),
      ]);
    const state = evaluate(this.compiled, timeMs);
    for (const node of this.compiled.nodes) {
      if (node.type !== "text") continue;
      const element = this.textElements.get(node.id),
        s = state.nodes[node.id];
      element.textContent = s.text;
      element.style.opacity = String(s.opacity);
    }
    for (const layer of this.layers) {
      const ctx = layer.context;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1;
      ctx.clearRect(0, 0, layer.canvas.width, layer.canvas.height);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      for (const node of layer.nodes) {
        const s = state.nodes[node.id];
        if (s.opacity === 0) continue;
        ctx.save();
        ctx.globalAlpha = s.opacity;
        if (node.type === "image") {
          const asset = this.compiled.assets.get(node.assetRef.id),
            p = imagePlacement(node, asset);
          ctx.setTransform(...matrix(node, s, asset));
          ctx.drawImage(
            this.resources.images.get(asset.id),
            p.x,
            p.y,
            p.width,
            p.height,
          );
        }
        if (node.type === "path") {
          ctx.lineWidth = node.strokeWidth;
          ctx.strokeStyle = this.compiled.source.style.colors[node.colorRole];
          ctx.setLineDash(node.dash);
          ctx.lineCap = "round";
          ctx.beginPath();
          const points = this.compiled.paths.get(node.pathId).points;
          for (let i = 0; i <= registry.limits.pathSamples; i++) {
            const p = curve(
              points,
              (s.progress * i) / registry.limits.pathSamples,
            );
            i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y);
          }
          ctx.stroke();
        }
        if (node.type === "ring") {
          const b = node.box,
            x = b.x + b.width / 2,
            y = b.y + b.height / 2,
            r = Math.max(
              0,
              (Math.min(b.width, b.height) - node.strokeWidth) / 2,
            );
          ctx.strokeStyle = ctx.fillStyle =
            this.compiled.source.style.colors[node.colorRole];
          ctx.lineWidth = node.strokeWidth;
          ctx.beginPath();
          ctx.arc(x, y, r, 0, Math.PI * 2);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(x, y, r * node.innerRatio, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }
    }
    this.lastState = state;
    return state;
  }

  getGeometry(target, timeMs) {
    const node = this.compiled.nodeMap.get(target?.nodeId);
    if (
      !node ||
      target.part !== "self" ||
      Object.keys(target).some((k) => !["nodeId", "part"].includes(k))
    )
      throw new EngineError([
        diagnostic(
          "MISSING_TARGET",
          "/target",
          "Only registered node self targets are supported",
        ),
      ]);
    const state = this.renderAt(timeMs);
    return geometry(
      node,
      state.nodes[node.id],
      this.compiled,
      this.textElements.get(node.id),
      this.root,
    );
  }

  snapshot() {
    return structuredClone({
      ...this.compiled.snapshot,
      inputFingerprint: this.fingerprint,
      readiness: {
        resources: "bytes-hash-decode-dimensions-alpha-verified",
        textCapacity: "all-variants-verified",
        font: {
          family: this.compiled.source.style.fontFamily,
          policy: "explicit-system-font-study",
          fontProbe: "measurement-based; per-glyph coverage not proven",
        },
      },
    });
  }

  dispose() {
    this.root.remove();
    this.resources?.release();
  }
}

class SceneController {
  constructor(host, pack) {
    this.host = host;
    this.pack = pack;
    this.current = null;
    this.loadSequence = 0;
    this.resizeObserver = new ResizeObserver(() => this.current?.fit());
    this.resizeObserver.observe(host);
  }

  async load(input) {
    const sequence = ++this.loadSequence;
    let candidate;
    try {
      const compiled = compile(input);
      candidate = new SceneRenderer(this.host, compiled);
      await candidate.prepare(this.pack);
      if (sequence !== this.loadSequence)
        throw new EngineError([
          diagnostic(
            "LOAD_SUPERSEDED",
            "/",
            "A newer scene request replaced this load",
          ),
        ]);
      this.current?.dispose();
      this.current = candidate;
      this.host.style.aspectRatio = `${compiled.source.canvas.width} / ${compiled.source.canvas.height}`;
      candidate.fit();
      candidate.root.style.visibility = "visible";
      return candidate.snapshot();
    } catch (error) {
      candidate?.dispose();
      throw error;
    }
  }

  requireCurrent() {
    if (!this.current)
      throw new EngineError([
        diagnostic("NOT_READY", "/", "No accepted scene loaded"),
      ]);
    return this.current;
  }
  renderAt(t) {
    return this.requireCurrent().renderAt(t);
  }
  getGeometry(target, t) {
    return this.requireCurrent().getGeometry(target, t);
  }
  getSnapshot() {
    return this.requireCurrent().snapshot();
  }
  get durationMs() {
    return this.requireCurrent().compiled.source.durationMs;
  }
  dispose() {
    this.loadSequence++;
    this.resizeObserver.disconnect();
    this.current?.dispose();
    this.current = null;
  }
}

module.exports = { SceneController };
