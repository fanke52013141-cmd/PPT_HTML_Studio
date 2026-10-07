"use strict";
(() => {
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __commonJS = (cb, mod) => function __require() {
    try {
      return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
    } catch (e) {
      throw mod = 0, e;
    }
  };

  // src/registry.cjs
  var require_registry = __commonJS({
    "src/registry.cjs"(exports, module) {
      "use strict";
      var VERSION = "0.1.0";
      var registry = Object.freeze({
        format: "hps.e1.scene",
        schemaVersion: VERSION,
        contractVersion: "0.7.1",
        template: { id: "layout.open-stage.e1", version: VERSION },
        nodes: ["text", "image", "path", "ring"],
        actions: ["opacity", "move-path", "rotate", "path-progress"],
        scope: "single-scene design-exploration; manual timing; fixed camera",
        limits: {
          canvasPixels: 32e6,
          resourcePixels: 16e6,
          pathSamples: 128
        },
        output: {
          HTML: "prototype",
          video: "same-time-evaluator; standalone export",
          PPTX: "unsupported"
        }
      });
      var EngineError = class extends Error {
        constructor(diagnostics) {
          super(diagnostics.map((d) => `${d.code}: ${d.message}`).join("\n"));
          this.name = "EngineError";
          this.diagnostics = diagnostics;
          this.code = diagnostics[0]?.code || "ENGINE_ERROR";
        }
      };
      function diagnostic(code, path, message, nodeId) {
        return {
          code,
          severity: "error",
          path,
          message,
          ...nodeId ? { nodeId } : {}
        };
      }
      module.exports = { registry, EngineError, diagnostic };
    }
  });

  // node_modules/ajv/dist/runtime/ucs2length.js
  var require_ucs2length = __commonJS({
    "node_modules/ajv/dist/runtime/ucs2length.js"(exports) {
      "use strict";
      Object.defineProperty(exports, "__esModule", { value: true });
      function ucs2length(str) {
        const len = str.length;
        let length = 0;
        let pos = 0;
        let value;
        while (pos < len) {
          length++;
          value = str.charCodeAt(pos++);
          if (value >= 55296 && value <= 56319 && pos < len) {
            value = str.charCodeAt(pos);
            if ((value & 64512) === 56320)
              pos++;
          }
        }
        return length;
      }
      exports.default = ucs2length;
      ucs2length.code = 'require("ajv/dist/runtime/ucs2length").default';
    }
  });

  // src/generated/validate-scene.cjs
  var require_validate_scene = __commonJS({
    "src/generated/validate-scene.cjs"(exports, module) {
      "use strict";
      module.exports = validate20;
      module.exports.default = validate20;
      var schema31 = { "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:hps:e1:scene:0.1.0", "title": "HPS E1 single scene (independent from P01)", "description": "Finite single-scene authoring format; not P01 scene 0.1.0. Strict structural validation plus compiler semantic checks.", "type": "object", "properties": { "format": { "const": "hps.e1.scene" }, "schemaVersion": { "const": "0.1.0" }, "contractVersion": { "const": "0.7.1" }, "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "revision": { "type": "integer", "minimum": 1, "maximum": 9007199254740991 }, "title": { "type": "string", "minLength": 1, "maxLength": 2e3 }, "authoringMode": { "const": "design-exploration" }, "canvas": { "type": "object", "properties": { "width": { "type": "integer", "minimum": 320, "maximum": 3840 }, "height": { "type": "integer", "minimum": 180, "maximum": 2160 }, "safeInsets": { "type": "object", "properties": { "top": { "type": "number", "minimum": 0, "maximum": 500 }, "right": { "type": "number", "minimum": 0, "maximum": 500 }, "bottom": { "type": "number", "minimum": 0, "maximum": 500 }, "left": { "type": "number", "minimum": 0, "maximum": 500 } }, "required": ["top", "right", "bottom", "left"], "additionalProperties": false } }, "required": ["width", "height", "safeInsets"], "additionalProperties": false }, "durationMs": { "type": "integer", "minimum": 1, "maximum": 6e5 }, "timingMode": { "const": "manual" }, "templateRef": { "$ref": "#/$defs/versionRef" }, "style": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "version": { "const": "0.1.0" }, "fontFamily": { "const": "Microsoft YaHei" }, "background": { "type": "object", "properties": { "base": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }, "leftGlow": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }, "rightGlow": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" } }, "required": ["base", "leftGlow", "rightGlow"], "additionalProperties": false }, "colors": { "type": "object", "properties": { "accent": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }, "path": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" } }, "required": ["accent", "path"], "additionalProperties": false }, "textRoles": { "type": "object", "properties": { "title": { "$ref": "#/$defs/textRole" }, "subtitle": { "$ref": "#/$defs/textRole" }, "caption": { "$ref": "#/$defs/textRole" } }, "required": ["title", "subtitle", "caption"], "additionalProperties": false } }, "required": ["id", "version", "fontFamily", "background", "colors", "textRoles"], "additionalProperties": false }, "assets": { "type": "array", "items": { "$ref": "#/$defs/asset" }, "minItems": 1, "maxItems": 20 }, "paths": { "type": "array", "items": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "points": { "type": "array", "items": { "$ref": "#/$defs/point" }, "minItems": 4, "maxItems": 4 } }, "required": ["id", "points"], "additionalProperties": false }, "minItems": 1, "maxItems": 20 }, "nodes": { "type": "array", "items": { "oneOf": [{ "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "zIndex": { "type": "integer", "minimum": -100, "maximum": 100 }, "initialOpacity": { "type": "number", "minimum": 0, "maximum": 1 }, "type": { "const": "text" }, "box": { "$ref": "#/$defs/rect" }, "role": { "enum": ["title", "subtitle", "caption"] }, "content": { "oneOf": [{ "type": "object", "properties": { "kind": { "const": "static" }, "text": { "type": "string", "minLength": 1, "maxLength": 2e3 } }, "required": ["kind", "text"], "additionalProperties": false }, { "type": "object", "properties": { "kind": { "const": "beat-summary" } }, "required": ["kind"], "additionalProperties": false }] } }, "required": ["id", "typeVersion", "zIndex", "initialOpacity", "type", "box", "role", "content"], "additionalProperties": false }, { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "zIndex": { "type": "integer", "minimum": -100, "maximum": 100 }, "initialOpacity": { "type": "number", "minimum": 0, "maximum": 1 }, "type": { "const": "image" }, "box": { "$ref": "#/$defs/rect" }, "assetRef": { "$ref": "#/$defs/versionRef" }, "anchorId": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "fit": { "const": "contain" }, "rotationDeg": { "type": "number", "minimum": -180, "maximum": 180 } }, "required": ["id", "typeVersion", "zIndex", "initialOpacity", "type", "box", "assetRef", "anchorId", "fit", "rotationDeg"], "additionalProperties": false }, { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "zIndex": { "type": "integer", "minimum": -100, "maximum": 100 }, "initialOpacity": { "type": "number", "minimum": 0, "maximum": 1 }, "type": { "const": "path" }, "pathId": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "initialProgress": { "type": "number", "minimum": 0, "maximum": 1 }, "colorRole": { "enum": ["path", "accent"] }, "strokeWidth": { "type": "number", "minimum": 0.1, "maximum": 20 }, "dash": { "type": "array", "items": { "type": "number", "minimum": 0, "maximum": 100 }, "minItems": 0, "maxItems": 10 } }, "required": ["id", "typeVersion", "zIndex", "initialOpacity", "type", "pathId", "initialProgress", "colorRole", "strokeWidth", "dash"], "additionalProperties": false }, { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "zIndex": { "type": "integer", "minimum": -100, "maximum": 100 }, "initialOpacity": { "type": "number", "minimum": 0, "maximum": 1 }, "type": { "const": "ring" }, "box": { "$ref": "#/$defs/rect" }, "colorRole": { "enum": ["accent", "path"] }, "strokeWidth": { "type": "number", "minimum": 0.1, "maximum": 20 }, "innerRatio": { "type": "number", "minimum": 0, "maximum": 0.9 } }, "required": ["id", "typeVersion", "zIndex", "initialOpacity", "type", "box", "colorRole", "strokeWidth", "innerRatio"], "additionalProperties": false }] }, "minItems": 1, "maxItems": 80 }, "beats": { "type": "array", "items": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "startMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "endMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "text": { "type": "string", "minLength": 1, "maxLength": 2e3 }, "screenText": { "type": "string", "minLength": 1, "maxLength": 2e3 }, "targetIds": { "type": "array", "items": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "minItems": 1, "maxItems": 30 } }, "required": ["id", "startMs", "endMs", "text", "screenText", "targetIds"], "additionalProperties": false }, "minItems": 1, "maxItems": 40 }, "actions": { "type": "array", "items": { "oneOf": [{ "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "target": { "type": "object", "properties": { "nodeId": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "part": { "const": "self" } }, "required": ["nodeId", "part"], "additionalProperties": false }, "startMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "endMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "easing": { "enum": ["linear", "smoothstep", "ease-out-cubic"] }, "type": { "const": "opacity" }, "from": { "type": "number", "minimum": 0, "maximum": 1 }, "to": { "type": "number", "minimum": 0, "maximum": 1 } }, "required": ["id", "typeVersion", "target", "startMs", "endMs", "easing", "type", "from", "to"], "additionalProperties": false }, { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "target": { "type": "object", "properties": { "nodeId": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "part": { "const": "self" } }, "required": ["nodeId", "part"], "additionalProperties": false }, "startMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "endMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "easing": { "enum": ["linear", "smoothstep", "ease-out-cubic"] }, "type": { "const": "path-progress" }, "from": { "type": "number", "minimum": 0, "maximum": 1 }, "to": { "type": "number", "minimum": 0, "maximum": 1 } }, "required": ["id", "typeVersion", "target", "startMs", "endMs", "easing", "type", "from", "to"], "additionalProperties": false }, { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "target": { "type": "object", "properties": { "nodeId": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "part": { "const": "self" } }, "required": ["nodeId", "part"], "additionalProperties": false }, "startMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "endMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "easing": { "enum": ["linear", "smoothstep", "ease-out-cubic"] }, "type": { "const": "rotate" }, "fromDeg": { "type": "number", "minimum": -180, "maximum": 180 }, "toDeg": { "type": "number", "minimum": -180, "maximum": 180 } }, "required": ["id", "typeVersion", "target", "startMs", "endMs", "easing", "type", "fromDeg", "toDeg"], "additionalProperties": false }, { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "typeVersion": { "const": "0.1.0" }, "target": { "type": "object", "properties": { "nodeId": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "part": { "const": "self" } }, "required": ["nodeId", "part"], "additionalProperties": false }, "startMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "endMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "easing": { "enum": ["linear", "smoothstep", "ease-out-cubic"] }, "type": { "const": "move-path" }, "pathId": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "orientation": { "oneOf": [{ "type": "object", "properties": { "kind": { "const": "fixed" } }, "required": ["kind"], "additionalProperties": false }, { "type": "object", "properties": { "kind": { "const": "tangent" }, "minDeg": { "type": "number", "minimum": -180, "maximum": 180 }, "maxDeg": { "type": "number", "minimum": -180, "maximum": 180 } }, "required": ["kind", "minDeg", "maxDeg"], "additionalProperties": false }] } }, "required": ["id", "typeVersion", "target", "startMs", "endMs", "easing", "type", "pathId", "orientation"], "additionalProperties": false }] }, "minItems": 0, "maxItems": 160 }, "keyframes": { "type": "array", "items": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "tMs": { "type": "integer", "minimum": 0, "maximum": 6e5 }, "purpose": { "type": "string", "minLength": 1, "maxLength": 2e3 } }, "required": ["id", "tMs", "purpose"], "additionalProperties": false }, "minItems": 2, "maxItems": 20 } }, "required": ["format", "schemaVersion", "contractVersion", "id", "revision", "title", "authoringMode", "canvas", "durationMs", "timingMode", "templateRef", "style", "assets", "paths", "nodes", "beats", "actions", "keyframes"], "additionalProperties": false, "$defs": { "rect": { "type": "object", "properties": { "x": { "type": "number", "minimum": -1e5, "maximum": 1e5 }, "y": { "type": "number", "minimum": -1e5, "maximum": 1e5 }, "width": { "type": "number", "minimum": 1, "maximum": 1e4 }, "height": { "type": "number", "minimum": 1, "maximum": 1e4 } }, "required": ["x", "y", "width", "height"], "additionalProperties": false }, "point": { "type": "object", "properties": { "x": { "type": "number", "minimum": -1e5, "maximum": 1e5 }, "y": { "type": "number", "minimum": -1e5, "maximum": 1e5 } }, "required": ["x", "y"], "additionalProperties": false }, "versionRef": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "version": { "const": "0.1.0" } }, "required": ["id", "version"], "additionalProperties": false }, "textRole": { "type": "object", "properties": { "fontSize": { "type": "number", "minimum": 12, "maximum": 150 }, "fontWeight": { "enum": [400, 700] }, "lineHeight": { "type": "number", "minimum": 1, "maximum": 2 }, "color": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }, "maxLines": { "type": "integer", "minimum": 1, "maximum": 4 }, "align": { "enum": ["left", "center", "right"] } }, "required": ["fontSize", "fontWeight", "lineHeight", "color", "maxLines", "align"], "additionalProperties": false }, "asset": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "version": { "const": "0.1.0" }, "kind": { "const": "image" }, "file": { "type": "object", "properties": { "path": { "type": "string", "pattern": "^assets/[A-Za-z0-9._/-]+\\.png$", "maxLength": 200 }, "mimeType": { "const": "image/png" }, "sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" } }, "required": ["path", "mimeType", "sha256"], "additionalProperties": false }, "intrinsic": { "type": "object", "properties": { "width": { "type": "integer", "minimum": 1, "maximum": 4096 }, "height": { "type": "integer", "minimum": 1, "maximum": 4096 } }, "required": ["width", "height"], "additionalProperties": false }, "alphaBounds": { "$ref": "#/$defs/rect" }, "anchors": { "type": "array", "items": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "x": { "type": "number", "minimum": 0, "maximum": 1 }, "y": { "type": "number", "minimum": 0, "maximum": 1 } }, "required": ["id", "x", "y"], "additionalProperties": false }, "minItems": 1, "maxItems": 20 }, "provenance": { "type": "object", "properties": { "kind": { "const": "generated" }, "source": { "type": "string", "minLength": 1, "maxLength": 2e3 } }, "required": ["kind", "source"], "additionalProperties": false }, "quality": { "const": "conditional-experiment" } }, "required": ["id", "version", "kind", "file", "intrinsic", "alphaBounds", "anchors", "provenance", "quality"], "additionalProperties": false } } };
      var schema33 = { "type": "object", "properties": { "fontSize": { "type": "number", "minimum": 12, "maximum": 150 }, "fontWeight": { "enum": [400, 700] }, "lineHeight": { "type": "number", "minimum": 1, "maximum": 2 }, "color": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }, "maxLines": { "type": "integer", "minimum": 1, "maximum": 4 }, "align": { "enum": ["left", "center", "right"] } }, "required": ["fontSize", "fontWeight", "lineHeight", "color", "maxLines", "align"], "additionalProperties": false };
      var func1 = Object.prototype.hasOwnProperty;
      var func2 = require_ucs2length().default;
      var pattern4 = new RegExp("^[A-Za-z][A-Za-z0-9._-]{0,95}$", "u");
      var pattern7 = new RegExp("^#[0-9a-fA-F]{6}$", "u");
      var schema36 = { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "version": { "const": "0.1.0" }, "kind": { "const": "image" }, "file": { "type": "object", "properties": { "path": { "type": "string", "pattern": "^assets/[A-Za-z0-9._/-]+\\.png$", "maxLength": 200 }, "mimeType": { "const": "image/png" }, "sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" } }, "required": ["path", "mimeType", "sha256"], "additionalProperties": false }, "intrinsic": { "type": "object", "properties": { "width": { "type": "integer", "minimum": 1, "maximum": 4096 }, "height": { "type": "integer", "minimum": 1, "maximum": 4096 } }, "required": ["width", "height"], "additionalProperties": false }, "alphaBounds": { "$ref": "#/$defs/rect" }, "anchors": { "type": "array", "items": { "type": "object", "properties": { "id": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, "x": { "type": "number", "minimum": 0, "maximum": 1 }, "y": { "type": "number", "minimum": 0, "maximum": 1 } }, "required": ["id", "x", "y"], "additionalProperties": false }, "minItems": 1, "maxItems": 20 }, "provenance": { "type": "object", "properties": { "kind": { "const": "generated" }, "source": { "type": "string", "minLength": 1, "maxLength": 2e3 } }, "required": ["kind", "source"], "additionalProperties": false }, "quality": { "const": "conditional-experiment" } }, "required": ["id", "version", "kind", "file", "intrinsic", "alphaBounds", "anchors", "provenance", "quality"], "additionalProperties": false };
      var pattern16 = new RegExp("^assets/[A-Za-z0-9._/-]+\\.png$", "u");
      var pattern17 = new RegExp("^[a-f0-9]{64}$", "u");
      function validate21(data, { instancePath = "", parentData, parentDataProperty, rootData = data, dynamicAnchors = {} } = {}) {
        let vErrors = null;
        let errors = 0;
        const evaluated0 = validate21.evaluated;
        if (evaluated0.dynamicProps) {
          evaluated0.props = void 0;
        }
        if (evaluated0.dynamicItems) {
          evaluated0.items = void 0;
        }
        if (data && typeof data == "object" && !Array.isArray(data)) {
          if (data.id === void 0) {
            const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
            if (vErrors === null) {
              vErrors = [err0];
            } else {
              vErrors.push(err0);
            }
            errors++;
          }
          if (data.version === void 0) {
            const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "version" }, message: "must have required property 'version'" };
            if (vErrors === null) {
              vErrors = [err1];
            } else {
              vErrors.push(err1);
            }
            errors++;
          }
          if (data.kind === void 0) {
            const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "kind" }, message: "must have required property 'kind'" };
            if (vErrors === null) {
              vErrors = [err2];
            } else {
              vErrors.push(err2);
            }
            errors++;
          }
          if (data.file === void 0) {
            const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "file" }, message: "must have required property 'file'" };
            if (vErrors === null) {
              vErrors = [err3];
            } else {
              vErrors.push(err3);
            }
            errors++;
          }
          if (data.intrinsic === void 0) {
            const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "intrinsic" }, message: "must have required property 'intrinsic'" };
            if (vErrors === null) {
              vErrors = [err4];
            } else {
              vErrors.push(err4);
            }
            errors++;
          }
          if (data.alphaBounds === void 0) {
            const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "alphaBounds" }, message: "must have required property 'alphaBounds'" };
            if (vErrors === null) {
              vErrors = [err5];
            } else {
              vErrors.push(err5);
            }
            errors++;
          }
          if (data.anchors === void 0) {
            const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "anchors" }, message: "must have required property 'anchors'" };
            if (vErrors === null) {
              vErrors = [err6];
            } else {
              vErrors.push(err6);
            }
            errors++;
          }
          if (data.provenance === void 0) {
            const err7 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "provenance" }, message: "must have required property 'provenance'" };
            if (vErrors === null) {
              vErrors = [err7];
            } else {
              vErrors.push(err7);
            }
            errors++;
          }
          if (data.quality === void 0) {
            const err8 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "quality" }, message: "must have required property 'quality'" };
            if (vErrors === null) {
              vErrors = [err8];
            } else {
              vErrors.push(err8);
            }
            errors++;
          }
          for (const key0 in data) {
            if (!func1.call(schema36.properties, key0)) {
              const err9 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
              if (vErrors === null) {
                vErrors = [err9];
              } else {
                vErrors.push(err9);
              }
              errors++;
            }
          }
          if (data.id !== void 0) {
            let data0 = data.id;
            if (typeof data0 === "string") {
              if (!pattern4.test(data0)) {
                const err10 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                if (vErrors === null) {
                  vErrors = [err10];
                } else {
                  vErrors.push(err10);
                }
                errors++;
              }
            } else {
              const err11 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
              if (vErrors === null) {
                vErrors = [err11];
              } else {
                vErrors.push(err11);
              }
              errors++;
            }
          }
          if (data.version !== void 0) {
            if ("0.1.0" !== data.version) {
              const err12 = { instancePath: instancePath + "/version", schemaPath: "#/properties/version/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err12];
              } else {
                vErrors.push(err12);
              }
              errors++;
            }
          }
          if (data.kind !== void 0) {
            if ("image" !== data.kind) {
              const err13 = { instancePath: instancePath + "/kind", schemaPath: "#/properties/kind/const", keyword: "const", params: { allowedValue: "image" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err13];
              } else {
                vErrors.push(err13);
              }
              errors++;
            }
          }
          if (data.file !== void 0) {
            let data3 = data.file;
            if (data3 && typeof data3 == "object" && !Array.isArray(data3)) {
              if (data3.path === void 0) {
                const err14 = { instancePath: instancePath + "/file", schemaPath: "#/properties/file/required", keyword: "required", params: { missingProperty: "path" }, message: "must have required property 'path'" };
                if (vErrors === null) {
                  vErrors = [err14];
                } else {
                  vErrors.push(err14);
                }
                errors++;
              }
              if (data3.mimeType === void 0) {
                const err15 = { instancePath: instancePath + "/file", schemaPath: "#/properties/file/required", keyword: "required", params: { missingProperty: "mimeType" }, message: "must have required property 'mimeType'" };
                if (vErrors === null) {
                  vErrors = [err15];
                } else {
                  vErrors.push(err15);
                }
                errors++;
              }
              if (data3.sha256 === void 0) {
                const err16 = { instancePath: instancePath + "/file", schemaPath: "#/properties/file/required", keyword: "required", params: { missingProperty: "sha256" }, message: "must have required property 'sha256'" };
                if (vErrors === null) {
                  vErrors = [err16];
                } else {
                  vErrors.push(err16);
                }
                errors++;
              }
              for (const key1 in data3) {
                if (!(key1 === "path" || key1 === "mimeType" || key1 === "sha256")) {
                  const err17 = { instancePath: instancePath + "/file", schemaPath: "#/properties/file/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                  if (vErrors === null) {
                    vErrors = [err17];
                  } else {
                    vErrors.push(err17);
                  }
                  errors++;
                }
              }
              if (data3.path !== void 0) {
                let data4 = data3.path;
                if (typeof data4 === "string") {
                  if (func2(data4) > 200) {
                    const err18 = { instancePath: instancePath + "/file/path", schemaPath: "#/properties/file/properties/path/maxLength", keyword: "maxLength", params: { limit: 200 }, message: "must NOT have more than 200 characters" };
                    if (vErrors === null) {
                      vErrors = [err18];
                    } else {
                      vErrors.push(err18);
                    }
                    errors++;
                  }
                  if (!pattern16.test(data4)) {
                    const err19 = { instancePath: instancePath + "/file/path", schemaPath: "#/properties/file/properties/path/pattern", keyword: "pattern", params: { pattern: "^assets/[A-Za-z0-9._/-]+\\.png$" }, message: 'must match pattern "^assets/[A-Za-z0-9._/-]+\\.png$"' };
                    if (vErrors === null) {
                      vErrors = [err19];
                    } else {
                      vErrors.push(err19);
                    }
                    errors++;
                  }
                } else {
                  const err20 = { instancePath: instancePath + "/file/path", schemaPath: "#/properties/file/properties/path/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                  if (vErrors === null) {
                    vErrors = [err20];
                  } else {
                    vErrors.push(err20);
                  }
                  errors++;
                }
              }
              if (data3.mimeType !== void 0) {
                if ("image/png" !== data3.mimeType) {
                  const err21 = { instancePath: instancePath + "/file/mimeType", schemaPath: "#/properties/file/properties/mimeType/const", keyword: "const", params: { allowedValue: "image/png" }, message: "must be equal to constant" };
                  if (vErrors === null) {
                    vErrors = [err21];
                  } else {
                    vErrors.push(err21);
                  }
                  errors++;
                }
              }
              if (data3.sha256 !== void 0) {
                let data6 = data3.sha256;
                if (typeof data6 === "string") {
                  if (!pattern17.test(data6)) {
                    const err22 = { instancePath: instancePath + "/file/sha256", schemaPath: "#/properties/file/properties/sha256/pattern", keyword: "pattern", params: { pattern: "^[a-f0-9]{64}$" }, message: 'must match pattern "^[a-f0-9]{64}$"' };
                    if (vErrors === null) {
                      vErrors = [err22];
                    } else {
                      vErrors.push(err22);
                    }
                    errors++;
                  }
                } else {
                  const err23 = { instancePath: instancePath + "/file/sha256", schemaPath: "#/properties/file/properties/sha256/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                  if (vErrors === null) {
                    vErrors = [err23];
                  } else {
                    vErrors.push(err23);
                  }
                  errors++;
                }
              }
            } else {
              const err24 = { instancePath: instancePath + "/file", schemaPath: "#/properties/file/type", keyword: "type", params: { type: "object" }, message: "must be object" };
              if (vErrors === null) {
                vErrors = [err24];
              } else {
                vErrors.push(err24);
              }
              errors++;
            }
          }
          if (data.intrinsic !== void 0) {
            let data7 = data.intrinsic;
            if (data7 && typeof data7 == "object" && !Array.isArray(data7)) {
              if (data7.width === void 0) {
                const err25 = { instancePath: instancePath + "/intrinsic", schemaPath: "#/properties/intrinsic/required", keyword: "required", params: { missingProperty: "width" }, message: "must have required property 'width'" };
                if (vErrors === null) {
                  vErrors = [err25];
                } else {
                  vErrors.push(err25);
                }
                errors++;
              }
              if (data7.height === void 0) {
                const err26 = { instancePath: instancePath + "/intrinsic", schemaPath: "#/properties/intrinsic/required", keyword: "required", params: { missingProperty: "height" }, message: "must have required property 'height'" };
                if (vErrors === null) {
                  vErrors = [err26];
                } else {
                  vErrors.push(err26);
                }
                errors++;
              }
              for (const key2 in data7) {
                if (!(key2 === "width" || key2 === "height")) {
                  const err27 = { instancePath: instancePath + "/intrinsic", schemaPath: "#/properties/intrinsic/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key2 }, message: "must NOT have additional properties" };
                  if (vErrors === null) {
                    vErrors = [err27];
                  } else {
                    vErrors.push(err27);
                  }
                  errors++;
                }
              }
              if (data7.width !== void 0) {
                let data8 = data7.width;
                if (!(typeof data8 == "number" && (!(data8 % 1) && !isNaN(data8)) && isFinite(data8))) {
                  const err28 = { instancePath: instancePath + "/intrinsic/width", schemaPath: "#/properties/intrinsic/properties/width/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                  if (vErrors === null) {
                    vErrors = [err28];
                  } else {
                    vErrors.push(err28);
                  }
                  errors++;
                }
                if (typeof data8 == "number" && isFinite(data8)) {
                  if (data8 > 4096 || isNaN(data8)) {
                    const err29 = { instancePath: instancePath + "/intrinsic/width", schemaPath: "#/properties/intrinsic/properties/width/maximum", keyword: "maximum", params: { comparison: "<=", limit: 4096 }, message: "must be <= 4096" };
                    if (vErrors === null) {
                      vErrors = [err29];
                    } else {
                      vErrors.push(err29);
                    }
                    errors++;
                  }
                  if (data8 < 1 || isNaN(data8)) {
                    const err30 = { instancePath: instancePath + "/intrinsic/width", schemaPath: "#/properties/intrinsic/properties/width/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                    if (vErrors === null) {
                      vErrors = [err30];
                    } else {
                      vErrors.push(err30);
                    }
                    errors++;
                  }
                }
              }
              if (data7.height !== void 0) {
                let data9 = data7.height;
                if (!(typeof data9 == "number" && (!(data9 % 1) && !isNaN(data9)) && isFinite(data9))) {
                  const err31 = { instancePath: instancePath + "/intrinsic/height", schemaPath: "#/properties/intrinsic/properties/height/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                  if (vErrors === null) {
                    vErrors = [err31];
                  } else {
                    vErrors.push(err31);
                  }
                  errors++;
                }
                if (typeof data9 == "number" && isFinite(data9)) {
                  if (data9 > 4096 || isNaN(data9)) {
                    const err32 = { instancePath: instancePath + "/intrinsic/height", schemaPath: "#/properties/intrinsic/properties/height/maximum", keyword: "maximum", params: { comparison: "<=", limit: 4096 }, message: "must be <= 4096" };
                    if (vErrors === null) {
                      vErrors = [err32];
                    } else {
                      vErrors.push(err32);
                    }
                    errors++;
                  }
                  if (data9 < 1 || isNaN(data9)) {
                    const err33 = { instancePath: instancePath + "/intrinsic/height", schemaPath: "#/properties/intrinsic/properties/height/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                    if (vErrors === null) {
                      vErrors = [err33];
                    } else {
                      vErrors.push(err33);
                    }
                    errors++;
                  }
                }
              }
            } else {
              const err34 = { instancePath: instancePath + "/intrinsic", schemaPath: "#/properties/intrinsic/type", keyword: "type", params: { type: "object" }, message: "must be object" };
              if (vErrors === null) {
                vErrors = [err34];
              } else {
                vErrors.push(err34);
              }
              errors++;
            }
          }
          if (data.alphaBounds !== void 0) {
            let data10 = data.alphaBounds;
            if (data10 && typeof data10 == "object" && !Array.isArray(data10)) {
              if (data10.x === void 0) {
                const err35 = { instancePath: instancePath + "/alphaBounds", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "x" }, message: "must have required property 'x'" };
                if (vErrors === null) {
                  vErrors = [err35];
                } else {
                  vErrors.push(err35);
                }
                errors++;
              }
              if (data10.y === void 0) {
                const err36 = { instancePath: instancePath + "/alphaBounds", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "y" }, message: "must have required property 'y'" };
                if (vErrors === null) {
                  vErrors = [err36];
                } else {
                  vErrors.push(err36);
                }
                errors++;
              }
              if (data10.width === void 0) {
                const err37 = { instancePath: instancePath + "/alphaBounds", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "width" }, message: "must have required property 'width'" };
                if (vErrors === null) {
                  vErrors = [err37];
                } else {
                  vErrors.push(err37);
                }
                errors++;
              }
              if (data10.height === void 0) {
                const err38 = { instancePath: instancePath + "/alphaBounds", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "height" }, message: "must have required property 'height'" };
                if (vErrors === null) {
                  vErrors = [err38];
                } else {
                  vErrors.push(err38);
                }
                errors++;
              }
              for (const key3 in data10) {
                if (!(key3 === "x" || key3 === "y" || key3 === "width" || key3 === "height")) {
                  const err39 = { instancePath: instancePath + "/alphaBounds", schemaPath: "#/$defs/rect/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key3 }, message: "must NOT have additional properties" };
                  if (vErrors === null) {
                    vErrors = [err39];
                  } else {
                    vErrors.push(err39);
                  }
                  errors++;
                }
              }
              if (data10.x !== void 0) {
                let data11 = data10.x;
                if (typeof data11 == "number" && isFinite(data11)) {
                  if (data11 > 1e5 || isNaN(data11)) {
                    const err40 = { instancePath: instancePath + "/alphaBounds/x", schemaPath: "#/$defs/rect/properties/x/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                    if (vErrors === null) {
                      vErrors = [err40];
                    } else {
                      vErrors.push(err40);
                    }
                    errors++;
                  }
                  if (data11 < -1e5 || isNaN(data11)) {
                    const err41 = { instancePath: instancePath + "/alphaBounds/x", schemaPath: "#/$defs/rect/properties/x/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                    if (vErrors === null) {
                      vErrors = [err41];
                    } else {
                      vErrors.push(err41);
                    }
                    errors++;
                  }
                } else {
                  const err42 = { instancePath: instancePath + "/alphaBounds/x", schemaPath: "#/$defs/rect/properties/x/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                  if (vErrors === null) {
                    vErrors = [err42];
                  } else {
                    vErrors.push(err42);
                  }
                  errors++;
                }
              }
              if (data10.y !== void 0) {
                let data12 = data10.y;
                if (typeof data12 == "number" && isFinite(data12)) {
                  if (data12 > 1e5 || isNaN(data12)) {
                    const err43 = { instancePath: instancePath + "/alphaBounds/y", schemaPath: "#/$defs/rect/properties/y/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                    if (vErrors === null) {
                      vErrors = [err43];
                    } else {
                      vErrors.push(err43);
                    }
                    errors++;
                  }
                  if (data12 < -1e5 || isNaN(data12)) {
                    const err44 = { instancePath: instancePath + "/alphaBounds/y", schemaPath: "#/$defs/rect/properties/y/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                    if (vErrors === null) {
                      vErrors = [err44];
                    } else {
                      vErrors.push(err44);
                    }
                    errors++;
                  }
                } else {
                  const err45 = { instancePath: instancePath + "/alphaBounds/y", schemaPath: "#/$defs/rect/properties/y/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                  if (vErrors === null) {
                    vErrors = [err45];
                  } else {
                    vErrors.push(err45);
                  }
                  errors++;
                }
              }
              if (data10.width !== void 0) {
                let data13 = data10.width;
                if (typeof data13 == "number" && isFinite(data13)) {
                  if (data13 > 1e4 || isNaN(data13)) {
                    const err46 = { instancePath: instancePath + "/alphaBounds/width", schemaPath: "#/$defs/rect/properties/width/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                    if (vErrors === null) {
                      vErrors = [err46];
                    } else {
                      vErrors.push(err46);
                    }
                    errors++;
                  }
                  if (data13 < 1 || isNaN(data13)) {
                    const err47 = { instancePath: instancePath + "/alphaBounds/width", schemaPath: "#/$defs/rect/properties/width/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                    if (vErrors === null) {
                      vErrors = [err47];
                    } else {
                      vErrors.push(err47);
                    }
                    errors++;
                  }
                } else {
                  const err48 = { instancePath: instancePath + "/alphaBounds/width", schemaPath: "#/$defs/rect/properties/width/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                  if (vErrors === null) {
                    vErrors = [err48];
                  } else {
                    vErrors.push(err48);
                  }
                  errors++;
                }
              }
              if (data10.height !== void 0) {
                let data14 = data10.height;
                if (typeof data14 == "number" && isFinite(data14)) {
                  if (data14 > 1e4 || isNaN(data14)) {
                    const err49 = { instancePath: instancePath + "/alphaBounds/height", schemaPath: "#/$defs/rect/properties/height/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                    if (vErrors === null) {
                      vErrors = [err49];
                    } else {
                      vErrors.push(err49);
                    }
                    errors++;
                  }
                  if (data14 < 1 || isNaN(data14)) {
                    const err50 = { instancePath: instancePath + "/alphaBounds/height", schemaPath: "#/$defs/rect/properties/height/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                    if (vErrors === null) {
                      vErrors = [err50];
                    } else {
                      vErrors.push(err50);
                    }
                    errors++;
                  }
                } else {
                  const err51 = { instancePath: instancePath + "/alphaBounds/height", schemaPath: "#/$defs/rect/properties/height/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                  if (vErrors === null) {
                    vErrors = [err51];
                  } else {
                    vErrors.push(err51);
                  }
                  errors++;
                }
              }
            } else {
              const err52 = { instancePath: instancePath + "/alphaBounds", schemaPath: "#/$defs/rect/type", keyword: "type", params: { type: "object" }, message: "must be object" };
              if (vErrors === null) {
                vErrors = [err52];
              } else {
                vErrors.push(err52);
              }
              errors++;
            }
          }
          if (data.anchors !== void 0) {
            let data15 = data.anchors;
            if (Array.isArray(data15)) {
              if (data15.length > 20) {
                const err53 = { instancePath: instancePath + "/anchors", schemaPath: "#/properties/anchors/maxItems", keyword: "maxItems", params: { limit: 20 }, message: "must NOT have more than 20 items" };
                if (vErrors === null) {
                  vErrors = [err53];
                } else {
                  vErrors.push(err53);
                }
                errors++;
              }
              if (data15.length < 1) {
                const err54 = { instancePath: instancePath + "/anchors", schemaPath: "#/properties/anchors/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                if (vErrors === null) {
                  vErrors = [err54];
                } else {
                  vErrors.push(err54);
                }
                errors++;
              }
              const len0 = data15.length;
              for (let i0 = 0; i0 < len0; i0++) {
                let data16 = data15[i0];
                if (data16 && typeof data16 == "object" && !Array.isArray(data16)) {
                  if (data16.id === void 0) {
                    const err55 = { instancePath: instancePath + "/anchors/" + i0, schemaPath: "#/properties/anchors/items/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err55];
                    } else {
                      vErrors.push(err55);
                    }
                    errors++;
                  }
                  if (data16.x === void 0) {
                    const err56 = { instancePath: instancePath + "/anchors/" + i0, schemaPath: "#/properties/anchors/items/required", keyword: "required", params: { missingProperty: "x" }, message: "must have required property 'x'" };
                    if (vErrors === null) {
                      vErrors = [err56];
                    } else {
                      vErrors.push(err56);
                    }
                    errors++;
                  }
                  if (data16.y === void 0) {
                    const err57 = { instancePath: instancePath + "/anchors/" + i0, schemaPath: "#/properties/anchors/items/required", keyword: "required", params: { missingProperty: "y" }, message: "must have required property 'y'" };
                    if (vErrors === null) {
                      vErrors = [err57];
                    } else {
                      vErrors.push(err57);
                    }
                    errors++;
                  }
                  for (const key4 in data16) {
                    if (!(key4 === "id" || key4 === "x" || key4 === "y")) {
                      const err58 = { instancePath: instancePath + "/anchors/" + i0, schemaPath: "#/properties/anchors/items/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key4 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err58];
                      } else {
                        vErrors.push(err58);
                      }
                      errors++;
                    }
                  }
                  if (data16.id !== void 0) {
                    let data17 = data16.id;
                    if (typeof data17 === "string") {
                      if (!pattern4.test(data17)) {
                        const err59 = { instancePath: instancePath + "/anchors/" + i0 + "/id", schemaPath: "#/properties/anchors/items/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err59];
                        } else {
                          vErrors.push(err59);
                        }
                        errors++;
                      }
                    } else {
                      const err60 = { instancePath: instancePath + "/anchors/" + i0 + "/id", schemaPath: "#/properties/anchors/items/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err60];
                      } else {
                        vErrors.push(err60);
                      }
                      errors++;
                    }
                  }
                  if (data16.x !== void 0) {
                    let data18 = data16.x;
                    if (typeof data18 == "number" && isFinite(data18)) {
                      if (data18 > 1 || isNaN(data18)) {
                        const err61 = { instancePath: instancePath + "/anchors/" + i0 + "/x", schemaPath: "#/properties/anchors/items/properties/x/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err61];
                        } else {
                          vErrors.push(err61);
                        }
                        errors++;
                      }
                      if (data18 < 0 || isNaN(data18)) {
                        const err62 = { instancePath: instancePath + "/anchors/" + i0 + "/x", schemaPath: "#/properties/anchors/items/properties/x/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err62];
                        } else {
                          vErrors.push(err62);
                        }
                        errors++;
                      }
                    } else {
                      const err63 = { instancePath: instancePath + "/anchors/" + i0 + "/x", schemaPath: "#/properties/anchors/items/properties/x/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err63];
                      } else {
                        vErrors.push(err63);
                      }
                      errors++;
                    }
                  }
                  if (data16.y !== void 0) {
                    let data19 = data16.y;
                    if (typeof data19 == "number" && isFinite(data19)) {
                      if (data19 > 1 || isNaN(data19)) {
                        const err64 = { instancePath: instancePath + "/anchors/" + i0 + "/y", schemaPath: "#/properties/anchors/items/properties/y/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err64];
                        } else {
                          vErrors.push(err64);
                        }
                        errors++;
                      }
                      if (data19 < 0 || isNaN(data19)) {
                        const err65 = { instancePath: instancePath + "/anchors/" + i0 + "/y", schemaPath: "#/properties/anchors/items/properties/y/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err65];
                        } else {
                          vErrors.push(err65);
                        }
                        errors++;
                      }
                    } else {
                      const err66 = { instancePath: instancePath + "/anchors/" + i0 + "/y", schemaPath: "#/properties/anchors/items/properties/y/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err66];
                      } else {
                        vErrors.push(err66);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err67 = { instancePath: instancePath + "/anchors/" + i0, schemaPath: "#/properties/anchors/items/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err67];
                  } else {
                    vErrors.push(err67);
                  }
                  errors++;
                }
              }
            } else {
              const err68 = { instancePath: instancePath + "/anchors", schemaPath: "#/properties/anchors/type", keyword: "type", params: { type: "array" }, message: "must be array" };
              if (vErrors === null) {
                vErrors = [err68];
              } else {
                vErrors.push(err68);
              }
              errors++;
            }
          }
          if (data.provenance !== void 0) {
            let data20 = data.provenance;
            if (data20 && typeof data20 == "object" && !Array.isArray(data20)) {
              if (data20.kind === void 0) {
                const err69 = { instancePath: instancePath + "/provenance", schemaPath: "#/properties/provenance/required", keyword: "required", params: { missingProperty: "kind" }, message: "must have required property 'kind'" };
                if (vErrors === null) {
                  vErrors = [err69];
                } else {
                  vErrors.push(err69);
                }
                errors++;
              }
              if (data20.source === void 0) {
                const err70 = { instancePath: instancePath + "/provenance", schemaPath: "#/properties/provenance/required", keyword: "required", params: { missingProperty: "source" }, message: "must have required property 'source'" };
                if (vErrors === null) {
                  vErrors = [err70];
                } else {
                  vErrors.push(err70);
                }
                errors++;
              }
              for (const key5 in data20) {
                if (!(key5 === "kind" || key5 === "source")) {
                  const err71 = { instancePath: instancePath + "/provenance", schemaPath: "#/properties/provenance/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key5 }, message: "must NOT have additional properties" };
                  if (vErrors === null) {
                    vErrors = [err71];
                  } else {
                    vErrors.push(err71);
                  }
                  errors++;
                }
              }
              if (data20.kind !== void 0) {
                if ("generated" !== data20.kind) {
                  const err72 = { instancePath: instancePath + "/provenance/kind", schemaPath: "#/properties/provenance/properties/kind/const", keyword: "const", params: { allowedValue: "generated" }, message: "must be equal to constant" };
                  if (vErrors === null) {
                    vErrors = [err72];
                  } else {
                    vErrors.push(err72);
                  }
                  errors++;
                }
              }
              if (data20.source !== void 0) {
                let data22 = data20.source;
                if (typeof data22 === "string") {
                  if (func2(data22) > 2e3) {
                    const err73 = { instancePath: instancePath + "/provenance/source", schemaPath: "#/properties/provenance/properties/source/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
                    if (vErrors === null) {
                      vErrors = [err73];
                    } else {
                      vErrors.push(err73);
                    }
                    errors++;
                  }
                  if (func2(data22) < 1) {
                    const err74 = { instancePath: instancePath + "/provenance/source", schemaPath: "#/properties/provenance/properties/source/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                    if (vErrors === null) {
                      vErrors = [err74];
                    } else {
                      vErrors.push(err74);
                    }
                    errors++;
                  }
                } else {
                  const err75 = { instancePath: instancePath + "/provenance/source", schemaPath: "#/properties/provenance/properties/source/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                  if (vErrors === null) {
                    vErrors = [err75];
                  } else {
                    vErrors.push(err75);
                  }
                  errors++;
                }
              }
            } else {
              const err76 = { instancePath: instancePath + "/provenance", schemaPath: "#/properties/provenance/type", keyword: "type", params: { type: "object" }, message: "must be object" };
              if (vErrors === null) {
                vErrors = [err76];
              } else {
                vErrors.push(err76);
              }
              errors++;
            }
          }
          if (data.quality !== void 0) {
            if ("conditional-experiment" !== data.quality) {
              const err77 = { instancePath: instancePath + "/quality", schemaPath: "#/properties/quality/const", keyword: "const", params: { allowedValue: "conditional-experiment" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err77];
              } else {
                vErrors.push(err77);
              }
              errors++;
            }
          }
        } else {
          const err78 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
          if (vErrors === null) {
            vErrors = [err78];
          } else {
            vErrors.push(err78);
          }
          errors++;
        }
        validate21.errors = vErrors;
        return errors === 0;
      }
      validate21.evaluated = { "props": true, "dynamicProps": false, "dynamicItems": false };
      function validate20(data, { instancePath = "", parentData, parentDataProperty, rootData = data, dynamicAnchors = {} } = {}) {
        ;
        let vErrors = null;
        let errors = 0;
        const evaluated0 = validate20.evaluated;
        if (evaluated0.dynamicProps) {
          evaluated0.props = void 0;
        }
        if (evaluated0.dynamicItems) {
          evaluated0.items = void 0;
        }
        if (data && typeof data == "object" && !Array.isArray(data)) {
          if (data.format === void 0) {
            const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "format" }, message: "must have required property 'format'" };
            if (vErrors === null) {
              vErrors = [err0];
            } else {
              vErrors.push(err0);
            }
            errors++;
          }
          if (data.schemaVersion === void 0) {
            const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "schemaVersion" }, message: "must have required property 'schemaVersion'" };
            if (vErrors === null) {
              vErrors = [err1];
            } else {
              vErrors.push(err1);
            }
            errors++;
          }
          if (data.contractVersion === void 0) {
            const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "contractVersion" }, message: "must have required property 'contractVersion'" };
            if (vErrors === null) {
              vErrors = [err2];
            } else {
              vErrors.push(err2);
            }
            errors++;
          }
          if (data.id === void 0) {
            const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
            if (vErrors === null) {
              vErrors = [err3];
            } else {
              vErrors.push(err3);
            }
            errors++;
          }
          if (data.revision === void 0) {
            const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "revision" }, message: "must have required property 'revision'" };
            if (vErrors === null) {
              vErrors = [err4];
            } else {
              vErrors.push(err4);
            }
            errors++;
          }
          if (data.title === void 0) {
            const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "title" }, message: "must have required property 'title'" };
            if (vErrors === null) {
              vErrors = [err5];
            } else {
              vErrors.push(err5);
            }
            errors++;
          }
          if (data.authoringMode === void 0) {
            const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "authoringMode" }, message: "must have required property 'authoringMode'" };
            if (vErrors === null) {
              vErrors = [err6];
            } else {
              vErrors.push(err6);
            }
            errors++;
          }
          if (data.canvas === void 0) {
            const err7 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "canvas" }, message: "must have required property 'canvas'" };
            if (vErrors === null) {
              vErrors = [err7];
            } else {
              vErrors.push(err7);
            }
            errors++;
          }
          if (data.durationMs === void 0) {
            const err8 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "durationMs" }, message: "must have required property 'durationMs'" };
            if (vErrors === null) {
              vErrors = [err8];
            } else {
              vErrors.push(err8);
            }
            errors++;
          }
          if (data.timingMode === void 0) {
            const err9 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "timingMode" }, message: "must have required property 'timingMode'" };
            if (vErrors === null) {
              vErrors = [err9];
            } else {
              vErrors.push(err9);
            }
            errors++;
          }
          if (data.templateRef === void 0) {
            const err10 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "templateRef" }, message: "must have required property 'templateRef'" };
            if (vErrors === null) {
              vErrors = [err10];
            } else {
              vErrors.push(err10);
            }
            errors++;
          }
          if (data.style === void 0) {
            const err11 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "style" }, message: "must have required property 'style'" };
            if (vErrors === null) {
              vErrors = [err11];
            } else {
              vErrors.push(err11);
            }
            errors++;
          }
          if (data.assets === void 0) {
            const err12 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "assets" }, message: "must have required property 'assets'" };
            if (vErrors === null) {
              vErrors = [err12];
            } else {
              vErrors.push(err12);
            }
            errors++;
          }
          if (data.paths === void 0) {
            const err13 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "paths" }, message: "must have required property 'paths'" };
            if (vErrors === null) {
              vErrors = [err13];
            } else {
              vErrors.push(err13);
            }
            errors++;
          }
          if (data.nodes === void 0) {
            const err14 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "nodes" }, message: "must have required property 'nodes'" };
            if (vErrors === null) {
              vErrors = [err14];
            } else {
              vErrors.push(err14);
            }
            errors++;
          }
          if (data.beats === void 0) {
            const err15 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "beats" }, message: "must have required property 'beats'" };
            if (vErrors === null) {
              vErrors = [err15];
            } else {
              vErrors.push(err15);
            }
            errors++;
          }
          if (data.actions === void 0) {
            const err16 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "actions" }, message: "must have required property 'actions'" };
            if (vErrors === null) {
              vErrors = [err16];
            } else {
              vErrors.push(err16);
            }
            errors++;
          }
          if (data.keyframes === void 0) {
            const err17 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "keyframes" }, message: "must have required property 'keyframes'" };
            if (vErrors === null) {
              vErrors = [err17];
            } else {
              vErrors.push(err17);
            }
            errors++;
          }
          for (const key0 in data) {
            if (!func1.call(schema31.properties, key0)) {
              const err18 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
              if (vErrors === null) {
                vErrors = [err18];
              } else {
                vErrors.push(err18);
              }
              errors++;
            }
          }
          if (data.format !== void 0) {
            if ("hps.e1.scene" !== data.format) {
              const err19 = { instancePath: instancePath + "/format", schemaPath: "#/properties/format/const", keyword: "const", params: { allowedValue: "hps.e1.scene" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err19];
              } else {
                vErrors.push(err19);
              }
              errors++;
            }
          }
          if (data.schemaVersion !== void 0) {
            if ("0.1.0" !== data.schemaVersion) {
              const err20 = { instancePath: instancePath + "/schemaVersion", schemaPath: "#/properties/schemaVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err20];
              } else {
                vErrors.push(err20);
              }
              errors++;
            }
          }
          if (data.contractVersion !== void 0) {
            if ("0.7.1" !== data.contractVersion) {
              const err21 = { instancePath: instancePath + "/contractVersion", schemaPath: "#/properties/contractVersion/const", keyword: "const", params: { allowedValue: "0.7.1" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err21];
              } else {
                vErrors.push(err21);
              }
              errors++;
            }
          }
          if (data.id !== void 0) {
            let data3 = data.id;
            if (typeof data3 === "string") {
              if (!pattern4.test(data3)) {
                const err22 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                if (vErrors === null) {
                  vErrors = [err22];
                } else {
                  vErrors.push(err22);
                }
                errors++;
              }
            } else {
              const err23 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
              if (vErrors === null) {
                vErrors = [err23];
              } else {
                vErrors.push(err23);
              }
              errors++;
            }
          }
          if (data.revision !== void 0) {
            let data4 = data.revision;
            if (!(typeof data4 == "number" && (!(data4 % 1) && !isNaN(data4)) && isFinite(data4))) {
              const err24 = { instancePath: instancePath + "/revision", schemaPath: "#/properties/revision/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
              if (vErrors === null) {
                vErrors = [err24];
              } else {
                vErrors.push(err24);
              }
              errors++;
            }
            if (typeof data4 == "number" && isFinite(data4)) {
              if (data4 > 9007199254740991 || isNaN(data4)) {
                const err25 = { instancePath: instancePath + "/revision", schemaPath: "#/properties/revision/maximum", keyword: "maximum", params: { comparison: "<=", limit: 9007199254740991 }, message: "must be <= 9007199254740991" };
                if (vErrors === null) {
                  vErrors = [err25];
                } else {
                  vErrors.push(err25);
                }
                errors++;
              }
              if (data4 < 1 || isNaN(data4)) {
                const err26 = { instancePath: instancePath + "/revision", schemaPath: "#/properties/revision/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                if (vErrors === null) {
                  vErrors = [err26];
                } else {
                  vErrors.push(err26);
                }
                errors++;
              }
            }
          }
          if (data.title !== void 0) {
            let data5 = data.title;
            if (typeof data5 === "string") {
              if (func2(data5) > 2e3) {
                const err27 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
                if (vErrors === null) {
                  vErrors = [err27];
                } else {
                  vErrors.push(err27);
                }
                errors++;
              }
              if (func2(data5) < 1) {
                const err28 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                if (vErrors === null) {
                  vErrors = [err28];
                } else {
                  vErrors.push(err28);
                }
                errors++;
              }
            } else {
              const err29 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/type", keyword: "type", params: { type: "string" }, message: "must be string" };
              if (vErrors === null) {
                vErrors = [err29];
              } else {
                vErrors.push(err29);
              }
              errors++;
            }
          }
          if (data.authoringMode !== void 0) {
            if ("design-exploration" !== data.authoringMode) {
              const err30 = { instancePath: instancePath + "/authoringMode", schemaPath: "#/properties/authoringMode/const", keyword: "const", params: { allowedValue: "design-exploration" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err30];
              } else {
                vErrors.push(err30);
              }
              errors++;
            }
          }
          if (data.canvas !== void 0) {
            let data7 = data.canvas;
            if (data7 && typeof data7 == "object" && !Array.isArray(data7)) {
              if (data7.width === void 0) {
                const err31 = { instancePath: instancePath + "/canvas", schemaPath: "#/properties/canvas/required", keyword: "required", params: { missingProperty: "width" }, message: "must have required property 'width'" };
                if (vErrors === null) {
                  vErrors = [err31];
                } else {
                  vErrors.push(err31);
                }
                errors++;
              }
              if (data7.height === void 0) {
                const err32 = { instancePath: instancePath + "/canvas", schemaPath: "#/properties/canvas/required", keyword: "required", params: { missingProperty: "height" }, message: "must have required property 'height'" };
                if (vErrors === null) {
                  vErrors = [err32];
                } else {
                  vErrors.push(err32);
                }
                errors++;
              }
              if (data7.safeInsets === void 0) {
                const err33 = { instancePath: instancePath + "/canvas", schemaPath: "#/properties/canvas/required", keyword: "required", params: { missingProperty: "safeInsets" }, message: "must have required property 'safeInsets'" };
                if (vErrors === null) {
                  vErrors = [err33];
                } else {
                  vErrors.push(err33);
                }
                errors++;
              }
              for (const key1 in data7) {
                if (!(key1 === "width" || key1 === "height" || key1 === "safeInsets")) {
                  const err34 = { instancePath: instancePath + "/canvas", schemaPath: "#/properties/canvas/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                  if (vErrors === null) {
                    vErrors = [err34];
                  } else {
                    vErrors.push(err34);
                  }
                  errors++;
                }
              }
              if (data7.width !== void 0) {
                let data8 = data7.width;
                if (!(typeof data8 == "number" && (!(data8 % 1) && !isNaN(data8)) && isFinite(data8))) {
                  const err35 = { instancePath: instancePath + "/canvas/width", schemaPath: "#/properties/canvas/properties/width/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                  if (vErrors === null) {
                    vErrors = [err35];
                  } else {
                    vErrors.push(err35);
                  }
                  errors++;
                }
                if (typeof data8 == "number" && isFinite(data8)) {
                  if (data8 > 3840 || isNaN(data8)) {
                    const err36 = { instancePath: instancePath + "/canvas/width", schemaPath: "#/properties/canvas/properties/width/maximum", keyword: "maximum", params: { comparison: "<=", limit: 3840 }, message: "must be <= 3840" };
                    if (vErrors === null) {
                      vErrors = [err36];
                    } else {
                      vErrors.push(err36);
                    }
                    errors++;
                  }
                  if (data8 < 320 || isNaN(data8)) {
                    const err37 = { instancePath: instancePath + "/canvas/width", schemaPath: "#/properties/canvas/properties/width/minimum", keyword: "minimum", params: { comparison: ">=", limit: 320 }, message: "must be >= 320" };
                    if (vErrors === null) {
                      vErrors = [err37];
                    } else {
                      vErrors.push(err37);
                    }
                    errors++;
                  }
                }
              }
              if (data7.height !== void 0) {
                let data9 = data7.height;
                if (!(typeof data9 == "number" && (!(data9 % 1) && !isNaN(data9)) && isFinite(data9))) {
                  const err38 = { instancePath: instancePath + "/canvas/height", schemaPath: "#/properties/canvas/properties/height/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                  if (vErrors === null) {
                    vErrors = [err38];
                  } else {
                    vErrors.push(err38);
                  }
                  errors++;
                }
                if (typeof data9 == "number" && isFinite(data9)) {
                  if (data9 > 2160 || isNaN(data9)) {
                    const err39 = { instancePath: instancePath + "/canvas/height", schemaPath: "#/properties/canvas/properties/height/maximum", keyword: "maximum", params: { comparison: "<=", limit: 2160 }, message: "must be <= 2160" };
                    if (vErrors === null) {
                      vErrors = [err39];
                    } else {
                      vErrors.push(err39);
                    }
                    errors++;
                  }
                  if (data9 < 180 || isNaN(data9)) {
                    const err40 = { instancePath: instancePath + "/canvas/height", schemaPath: "#/properties/canvas/properties/height/minimum", keyword: "minimum", params: { comparison: ">=", limit: 180 }, message: "must be >= 180" };
                    if (vErrors === null) {
                      vErrors = [err40];
                    } else {
                      vErrors.push(err40);
                    }
                    errors++;
                  }
                }
              }
              if (data7.safeInsets !== void 0) {
                let data10 = data7.safeInsets;
                if (data10 && typeof data10 == "object" && !Array.isArray(data10)) {
                  if (data10.top === void 0) {
                    const err41 = { instancePath: instancePath + "/canvas/safeInsets", schemaPath: "#/properties/canvas/properties/safeInsets/required", keyword: "required", params: { missingProperty: "top" }, message: "must have required property 'top'" };
                    if (vErrors === null) {
                      vErrors = [err41];
                    } else {
                      vErrors.push(err41);
                    }
                    errors++;
                  }
                  if (data10.right === void 0) {
                    const err42 = { instancePath: instancePath + "/canvas/safeInsets", schemaPath: "#/properties/canvas/properties/safeInsets/required", keyword: "required", params: { missingProperty: "right" }, message: "must have required property 'right'" };
                    if (vErrors === null) {
                      vErrors = [err42];
                    } else {
                      vErrors.push(err42);
                    }
                    errors++;
                  }
                  if (data10.bottom === void 0) {
                    const err43 = { instancePath: instancePath + "/canvas/safeInsets", schemaPath: "#/properties/canvas/properties/safeInsets/required", keyword: "required", params: { missingProperty: "bottom" }, message: "must have required property 'bottom'" };
                    if (vErrors === null) {
                      vErrors = [err43];
                    } else {
                      vErrors.push(err43);
                    }
                    errors++;
                  }
                  if (data10.left === void 0) {
                    const err44 = { instancePath: instancePath + "/canvas/safeInsets", schemaPath: "#/properties/canvas/properties/safeInsets/required", keyword: "required", params: { missingProperty: "left" }, message: "must have required property 'left'" };
                    if (vErrors === null) {
                      vErrors = [err44];
                    } else {
                      vErrors.push(err44);
                    }
                    errors++;
                  }
                  for (const key2 in data10) {
                    if (!(key2 === "top" || key2 === "right" || key2 === "bottom" || key2 === "left")) {
                      const err45 = { instancePath: instancePath + "/canvas/safeInsets", schemaPath: "#/properties/canvas/properties/safeInsets/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key2 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err45];
                      } else {
                        vErrors.push(err45);
                      }
                      errors++;
                    }
                  }
                  if (data10.top !== void 0) {
                    let data11 = data10.top;
                    if (typeof data11 == "number" && isFinite(data11)) {
                      if (data11 > 500 || isNaN(data11)) {
                        const err46 = { instancePath: instancePath + "/canvas/safeInsets/top", schemaPath: "#/properties/canvas/properties/safeInsets/properties/top/maximum", keyword: "maximum", params: { comparison: "<=", limit: 500 }, message: "must be <= 500" };
                        if (vErrors === null) {
                          vErrors = [err46];
                        } else {
                          vErrors.push(err46);
                        }
                        errors++;
                      }
                      if (data11 < 0 || isNaN(data11)) {
                        const err47 = { instancePath: instancePath + "/canvas/safeInsets/top", schemaPath: "#/properties/canvas/properties/safeInsets/properties/top/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err47];
                        } else {
                          vErrors.push(err47);
                        }
                        errors++;
                      }
                    } else {
                      const err48 = { instancePath: instancePath + "/canvas/safeInsets/top", schemaPath: "#/properties/canvas/properties/safeInsets/properties/top/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err48];
                      } else {
                        vErrors.push(err48);
                      }
                      errors++;
                    }
                  }
                  if (data10.right !== void 0) {
                    let data12 = data10.right;
                    if (typeof data12 == "number" && isFinite(data12)) {
                      if (data12 > 500 || isNaN(data12)) {
                        const err49 = { instancePath: instancePath + "/canvas/safeInsets/right", schemaPath: "#/properties/canvas/properties/safeInsets/properties/right/maximum", keyword: "maximum", params: { comparison: "<=", limit: 500 }, message: "must be <= 500" };
                        if (vErrors === null) {
                          vErrors = [err49];
                        } else {
                          vErrors.push(err49);
                        }
                        errors++;
                      }
                      if (data12 < 0 || isNaN(data12)) {
                        const err50 = { instancePath: instancePath + "/canvas/safeInsets/right", schemaPath: "#/properties/canvas/properties/safeInsets/properties/right/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err50];
                        } else {
                          vErrors.push(err50);
                        }
                        errors++;
                      }
                    } else {
                      const err51 = { instancePath: instancePath + "/canvas/safeInsets/right", schemaPath: "#/properties/canvas/properties/safeInsets/properties/right/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err51];
                      } else {
                        vErrors.push(err51);
                      }
                      errors++;
                    }
                  }
                  if (data10.bottom !== void 0) {
                    let data13 = data10.bottom;
                    if (typeof data13 == "number" && isFinite(data13)) {
                      if (data13 > 500 || isNaN(data13)) {
                        const err52 = { instancePath: instancePath + "/canvas/safeInsets/bottom", schemaPath: "#/properties/canvas/properties/safeInsets/properties/bottom/maximum", keyword: "maximum", params: { comparison: "<=", limit: 500 }, message: "must be <= 500" };
                        if (vErrors === null) {
                          vErrors = [err52];
                        } else {
                          vErrors.push(err52);
                        }
                        errors++;
                      }
                      if (data13 < 0 || isNaN(data13)) {
                        const err53 = { instancePath: instancePath + "/canvas/safeInsets/bottom", schemaPath: "#/properties/canvas/properties/safeInsets/properties/bottom/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err53];
                        } else {
                          vErrors.push(err53);
                        }
                        errors++;
                      }
                    } else {
                      const err54 = { instancePath: instancePath + "/canvas/safeInsets/bottom", schemaPath: "#/properties/canvas/properties/safeInsets/properties/bottom/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err54];
                      } else {
                        vErrors.push(err54);
                      }
                      errors++;
                    }
                  }
                  if (data10.left !== void 0) {
                    let data14 = data10.left;
                    if (typeof data14 == "number" && isFinite(data14)) {
                      if (data14 > 500 || isNaN(data14)) {
                        const err55 = { instancePath: instancePath + "/canvas/safeInsets/left", schemaPath: "#/properties/canvas/properties/safeInsets/properties/left/maximum", keyword: "maximum", params: { comparison: "<=", limit: 500 }, message: "must be <= 500" };
                        if (vErrors === null) {
                          vErrors = [err55];
                        } else {
                          vErrors.push(err55);
                        }
                        errors++;
                      }
                      if (data14 < 0 || isNaN(data14)) {
                        const err56 = { instancePath: instancePath + "/canvas/safeInsets/left", schemaPath: "#/properties/canvas/properties/safeInsets/properties/left/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err56];
                        } else {
                          vErrors.push(err56);
                        }
                        errors++;
                      }
                    } else {
                      const err57 = { instancePath: instancePath + "/canvas/safeInsets/left", schemaPath: "#/properties/canvas/properties/safeInsets/properties/left/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err57];
                      } else {
                        vErrors.push(err57);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err58 = { instancePath: instancePath + "/canvas/safeInsets", schemaPath: "#/properties/canvas/properties/safeInsets/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err58];
                  } else {
                    vErrors.push(err58);
                  }
                  errors++;
                }
              }
            } else {
              const err59 = { instancePath: instancePath + "/canvas", schemaPath: "#/properties/canvas/type", keyword: "type", params: { type: "object" }, message: "must be object" };
              if (vErrors === null) {
                vErrors = [err59];
              } else {
                vErrors.push(err59);
              }
              errors++;
            }
          }
          if (data.durationMs !== void 0) {
            let data15 = data.durationMs;
            if (!(typeof data15 == "number" && (!(data15 % 1) && !isNaN(data15)) && isFinite(data15))) {
              const err60 = { instancePath: instancePath + "/durationMs", schemaPath: "#/properties/durationMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
              if (vErrors === null) {
                vErrors = [err60];
              } else {
                vErrors.push(err60);
              }
              errors++;
            }
            if (typeof data15 == "number" && isFinite(data15)) {
              if (data15 > 6e5 || isNaN(data15)) {
                const err61 = { instancePath: instancePath + "/durationMs", schemaPath: "#/properties/durationMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                if (vErrors === null) {
                  vErrors = [err61];
                } else {
                  vErrors.push(err61);
                }
                errors++;
              }
              if (data15 < 1 || isNaN(data15)) {
                const err62 = { instancePath: instancePath + "/durationMs", schemaPath: "#/properties/durationMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                if (vErrors === null) {
                  vErrors = [err62];
                } else {
                  vErrors.push(err62);
                }
                errors++;
              }
            }
          }
          if (data.timingMode !== void 0) {
            if ("manual" !== data.timingMode) {
              const err63 = { instancePath: instancePath + "/timingMode", schemaPath: "#/properties/timingMode/const", keyword: "const", params: { allowedValue: "manual" }, message: "must be equal to constant" };
              if (vErrors === null) {
                vErrors = [err63];
              } else {
                vErrors.push(err63);
              }
              errors++;
            }
          }
          if (data.templateRef !== void 0) {
            let data17 = data.templateRef;
            if (data17 && typeof data17 == "object" && !Array.isArray(data17)) {
              if (data17.id === void 0) {
                const err64 = { instancePath: instancePath + "/templateRef", schemaPath: "#/$defs/versionRef/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                if (vErrors === null) {
                  vErrors = [err64];
                } else {
                  vErrors.push(err64);
                }
                errors++;
              }
              if (data17.version === void 0) {
                const err65 = { instancePath: instancePath + "/templateRef", schemaPath: "#/$defs/versionRef/required", keyword: "required", params: { missingProperty: "version" }, message: "must have required property 'version'" };
                if (vErrors === null) {
                  vErrors = [err65];
                } else {
                  vErrors.push(err65);
                }
                errors++;
              }
              for (const key3 in data17) {
                if (!(key3 === "id" || key3 === "version")) {
                  const err66 = { instancePath: instancePath + "/templateRef", schemaPath: "#/$defs/versionRef/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key3 }, message: "must NOT have additional properties" };
                  if (vErrors === null) {
                    vErrors = [err66];
                  } else {
                    vErrors.push(err66);
                  }
                  errors++;
                }
              }
              if (data17.id !== void 0) {
                let data18 = data17.id;
                if (typeof data18 === "string") {
                  if (!pattern4.test(data18)) {
                    const err67 = { instancePath: instancePath + "/templateRef/id", schemaPath: "#/$defs/versionRef/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                    if (vErrors === null) {
                      vErrors = [err67];
                    } else {
                      vErrors.push(err67);
                    }
                    errors++;
                  }
                } else {
                  const err68 = { instancePath: instancePath + "/templateRef/id", schemaPath: "#/$defs/versionRef/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                  if (vErrors === null) {
                    vErrors = [err68];
                  } else {
                    vErrors.push(err68);
                  }
                  errors++;
                }
              }
              if (data17.version !== void 0) {
                if ("0.1.0" !== data17.version) {
                  const err69 = { instancePath: instancePath + "/templateRef/version", schemaPath: "#/$defs/versionRef/properties/version/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                  if (vErrors === null) {
                    vErrors = [err69];
                  } else {
                    vErrors.push(err69);
                  }
                  errors++;
                }
              }
            } else {
              const err70 = { instancePath: instancePath + "/templateRef", schemaPath: "#/$defs/versionRef/type", keyword: "type", params: { type: "object" }, message: "must be object" };
              if (vErrors === null) {
                vErrors = [err70];
              } else {
                vErrors.push(err70);
              }
              errors++;
            }
          }
          if (data.style !== void 0) {
            let data20 = data.style;
            if (data20 && typeof data20 == "object" && !Array.isArray(data20)) {
              if (data20.id === void 0) {
                const err71 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                if (vErrors === null) {
                  vErrors = [err71];
                } else {
                  vErrors.push(err71);
                }
                errors++;
              }
              if (data20.version === void 0) {
                const err72 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/required", keyword: "required", params: { missingProperty: "version" }, message: "must have required property 'version'" };
                if (vErrors === null) {
                  vErrors = [err72];
                } else {
                  vErrors.push(err72);
                }
                errors++;
              }
              if (data20.fontFamily === void 0) {
                const err73 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/required", keyword: "required", params: { missingProperty: "fontFamily" }, message: "must have required property 'fontFamily'" };
                if (vErrors === null) {
                  vErrors = [err73];
                } else {
                  vErrors.push(err73);
                }
                errors++;
              }
              if (data20.background === void 0) {
                const err74 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/required", keyword: "required", params: { missingProperty: "background" }, message: "must have required property 'background'" };
                if (vErrors === null) {
                  vErrors = [err74];
                } else {
                  vErrors.push(err74);
                }
                errors++;
              }
              if (data20.colors === void 0) {
                const err75 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/required", keyword: "required", params: { missingProperty: "colors" }, message: "must have required property 'colors'" };
                if (vErrors === null) {
                  vErrors = [err75];
                } else {
                  vErrors.push(err75);
                }
                errors++;
              }
              if (data20.textRoles === void 0) {
                const err76 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/required", keyword: "required", params: { missingProperty: "textRoles" }, message: "must have required property 'textRoles'" };
                if (vErrors === null) {
                  vErrors = [err76];
                } else {
                  vErrors.push(err76);
                }
                errors++;
              }
              for (const key4 in data20) {
                if (!(key4 === "id" || key4 === "version" || key4 === "fontFamily" || key4 === "background" || key4 === "colors" || key4 === "textRoles")) {
                  const err77 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key4 }, message: "must NOT have additional properties" };
                  if (vErrors === null) {
                    vErrors = [err77];
                  } else {
                    vErrors.push(err77);
                  }
                  errors++;
                }
              }
              if (data20.id !== void 0) {
                let data21 = data20.id;
                if (typeof data21 === "string") {
                  if (!pattern4.test(data21)) {
                    const err78 = { instancePath: instancePath + "/style/id", schemaPath: "#/properties/style/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                    if (vErrors === null) {
                      vErrors = [err78];
                    } else {
                      vErrors.push(err78);
                    }
                    errors++;
                  }
                } else {
                  const err79 = { instancePath: instancePath + "/style/id", schemaPath: "#/properties/style/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                  if (vErrors === null) {
                    vErrors = [err79];
                  } else {
                    vErrors.push(err79);
                  }
                  errors++;
                }
              }
              if (data20.version !== void 0) {
                if ("0.1.0" !== data20.version) {
                  const err80 = { instancePath: instancePath + "/style/version", schemaPath: "#/properties/style/properties/version/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                  if (vErrors === null) {
                    vErrors = [err80];
                  } else {
                    vErrors.push(err80);
                  }
                  errors++;
                }
              }
              if (data20.fontFamily !== void 0) {
                if ("Microsoft YaHei" !== data20.fontFamily) {
                  const err81 = { instancePath: instancePath + "/style/fontFamily", schemaPath: "#/properties/style/properties/fontFamily/const", keyword: "const", params: { allowedValue: "Microsoft YaHei" }, message: "must be equal to constant" };
                  if (vErrors === null) {
                    vErrors = [err81];
                  } else {
                    vErrors.push(err81);
                  }
                  errors++;
                }
              }
              if (data20.background !== void 0) {
                let data24 = data20.background;
                if (data24 && typeof data24 == "object" && !Array.isArray(data24)) {
                  if (data24.base === void 0) {
                    const err82 = { instancePath: instancePath + "/style/background", schemaPath: "#/properties/style/properties/background/required", keyword: "required", params: { missingProperty: "base" }, message: "must have required property 'base'" };
                    if (vErrors === null) {
                      vErrors = [err82];
                    } else {
                      vErrors.push(err82);
                    }
                    errors++;
                  }
                  if (data24.leftGlow === void 0) {
                    const err83 = { instancePath: instancePath + "/style/background", schemaPath: "#/properties/style/properties/background/required", keyword: "required", params: { missingProperty: "leftGlow" }, message: "must have required property 'leftGlow'" };
                    if (vErrors === null) {
                      vErrors = [err83];
                    } else {
                      vErrors.push(err83);
                    }
                    errors++;
                  }
                  if (data24.rightGlow === void 0) {
                    const err84 = { instancePath: instancePath + "/style/background", schemaPath: "#/properties/style/properties/background/required", keyword: "required", params: { missingProperty: "rightGlow" }, message: "must have required property 'rightGlow'" };
                    if (vErrors === null) {
                      vErrors = [err84];
                    } else {
                      vErrors.push(err84);
                    }
                    errors++;
                  }
                  for (const key5 in data24) {
                    if (!(key5 === "base" || key5 === "leftGlow" || key5 === "rightGlow")) {
                      const err85 = { instancePath: instancePath + "/style/background", schemaPath: "#/properties/style/properties/background/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key5 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err85];
                      } else {
                        vErrors.push(err85);
                      }
                      errors++;
                    }
                  }
                  if (data24.base !== void 0) {
                    let data25 = data24.base;
                    if (typeof data25 === "string") {
                      if (!pattern7.test(data25)) {
                        const err86 = { instancePath: instancePath + "/style/background/base", schemaPath: "#/properties/style/properties/background/properties/base/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                        if (vErrors === null) {
                          vErrors = [err86];
                        } else {
                          vErrors.push(err86);
                        }
                        errors++;
                      }
                    } else {
                      const err87 = { instancePath: instancePath + "/style/background/base", schemaPath: "#/properties/style/properties/background/properties/base/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err87];
                      } else {
                        vErrors.push(err87);
                      }
                      errors++;
                    }
                  }
                  if (data24.leftGlow !== void 0) {
                    let data26 = data24.leftGlow;
                    if (typeof data26 === "string") {
                      if (!pattern7.test(data26)) {
                        const err88 = { instancePath: instancePath + "/style/background/leftGlow", schemaPath: "#/properties/style/properties/background/properties/leftGlow/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                        if (vErrors === null) {
                          vErrors = [err88];
                        } else {
                          vErrors.push(err88);
                        }
                        errors++;
                      }
                    } else {
                      const err89 = { instancePath: instancePath + "/style/background/leftGlow", schemaPath: "#/properties/style/properties/background/properties/leftGlow/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err89];
                      } else {
                        vErrors.push(err89);
                      }
                      errors++;
                    }
                  }
                  if (data24.rightGlow !== void 0) {
                    let data27 = data24.rightGlow;
                    if (typeof data27 === "string") {
                      if (!pattern7.test(data27)) {
                        const err90 = { instancePath: instancePath + "/style/background/rightGlow", schemaPath: "#/properties/style/properties/background/properties/rightGlow/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                        if (vErrors === null) {
                          vErrors = [err90];
                        } else {
                          vErrors.push(err90);
                        }
                        errors++;
                      }
                    } else {
                      const err91 = { instancePath: instancePath + "/style/background/rightGlow", schemaPath: "#/properties/style/properties/background/properties/rightGlow/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err91];
                      } else {
                        vErrors.push(err91);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err92 = { instancePath: instancePath + "/style/background", schemaPath: "#/properties/style/properties/background/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err92];
                  } else {
                    vErrors.push(err92);
                  }
                  errors++;
                }
              }
              if (data20.colors !== void 0) {
                let data28 = data20.colors;
                if (data28 && typeof data28 == "object" && !Array.isArray(data28)) {
                  if (data28.accent === void 0) {
                    const err93 = { instancePath: instancePath + "/style/colors", schemaPath: "#/properties/style/properties/colors/required", keyword: "required", params: { missingProperty: "accent" }, message: "must have required property 'accent'" };
                    if (vErrors === null) {
                      vErrors = [err93];
                    } else {
                      vErrors.push(err93);
                    }
                    errors++;
                  }
                  if (data28.path === void 0) {
                    const err94 = { instancePath: instancePath + "/style/colors", schemaPath: "#/properties/style/properties/colors/required", keyword: "required", params: { missingProperty: "path" }, message: "must have required property 'path'" };
                    if (vErrors === null) {
                      vErrors = [err94];
                    } else {
                      vErrors.push(err94);
                    }
                    errors++;
                  }
                  for (const key6 in data28) {
                    if (!(key6 === "accent" || key6 === "path")) {
                      const err95 = { instancePath: instancePath + "/style/colors", schemaPath: "#/properties/style/properties/colors/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key6 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err95];
                      } else {
                        vErrors.push(err95);
                      }
                      errors++;
                    }
                  }
                  if (data28.accent !== void 0) {
                    let data29 = data28.accent;
                    if (typeof data29 === "string") {
                      if (!pattern7.test(data29)) {
                        const err96 = { instancePath: instancePath + "/style/colors/accent", schemaPath: "#/properties/style/properties/colors/properties/accent/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                        if (vErrors === null) {
                          vErrors = [err96];
                        } else {
                          vErrors.push(err96);
                        }
                        errors++;
                      }
                    } else {
                      const err97 = { instancePath: instancePath + "/style/colors/accent", schemaPath: "#/properties/style/properties/colors/properties/accent/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err97];
                      } else {
                        vErrors.push(err97);
                      }
                      errors++;
                    }
                  }
                  if (data28.path !== void 0) {
                    let data30 = data28.path;
                    if (typeof data30 === "string") {
                      if (!pattern7.test(data30)) {
                        const err98 = { instancePath: instancePath + "/style/colors/path", schemaPath: "#/properties/style/properties/colors/properties/path/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                        if (vErrors === null) {
                          vErrors = [err98];
                        } else {
                          vErrors.push(err98);
                        }
                        errors++;
                      }
                    } else {
                      const err99 = { instancePath: instancePath + "/style/colors/path", schemaPath: "#/properties/style/properties/colors/properties/path/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err99];
                      } else {
                        vErrors.push(err99);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err100 = { instancePath: instancePath + "/style/colors", schemaPath: "#/properties/style/properties/colors/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err100];
                  } else {
                    vErrors.push(err100);
                  }
                  errors++;
                }
              }
              if (data20.textRoles !== void 0) {
                let data31 = data20.textRoles;
                if (data31 && typeof data31 == "object" && !Array.isArray(data31)) {
                  if (data31.title === void 0) {
                    const err101 = { instancePath: instancePath + "/style/textRoles", schemaPath: "#/properties/style/properties/textRoles/required", keyword: "required", params: { missingProperty: "title" }, message: "must have required property 'title'" };
                    if (vErrors === null) {
                      vErrors = [err101];
                    } else {
                      vErrors.push(err101);
                    }
                    errors++;
                  }
                  if (data31.subtitle === void 0) {
                    const err102 = { instancePath: instancePath + "/style/textRoles", schemaPath: "#/properties/style/properties/textRoles/required", keyword: "required", params: { missingProperty: "subtitle" }, message: "must have required property 'subtitle'" };
                    if (vErrors === null) {
                      vErrors = [err102];
                    } else {
                      vErrors.push(err102);
                    }
                    errors++;
                  }
                  if (data31.caption === void 0) {
                    const err103 = { instancePath: instancePath + "/style/textRoles", schemaPath: "#/properties/style/properties/textRoles/required", keyword: "required", params: { missingProperty: "caption" }, message: "must have required property 'caption'" };
                    if (vErrors === null) {
                      vErrors = [err103];
                    } else {
                      vErrors.push(err103);
                    }
                    errors++;
                  }
                  for (const key7 in data31) {
                    if (!(key7 === "title" || key7 === "subtitle" || key7 === "caption")) {
                      const err104 = { instancePath: instancePath + "/style/textRoles", schemaPath: "#/properties/style/properties/textRoles/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key7 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err104];
                      } else {
                        vErrors.push(err104);
                      }
                      errors++;
                    }
                  }
                  if (data31.title !== void 0) {
                    let data32 = data31.title;
                    if (data32 && typeof data32 == "object" && !Array.isArray(data32)) {
                      if (data32.fontSize === void 0) {
                        const err105 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "fontSize" }, message: "must have required property 'fontSize'" };
                        if (vErrors === null) {
                          vErrors = [err105];
                        } else {
                          vErrors.push(err105);
                        }
                        errors++;
                      }
                      if (data32.fontWeight === void 0) {
                        const err106 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "fontWeight" }, message: "must have required property 'fontWeight'" };
                        if (vErrors === null) {
                          vErrors = [err106];
                        } else {
                          vErrors.push(err106);
                        }
                        errors++;
                      }
                      if (data32.lineHeight === void 0) {
                        const err107 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "lineHeight" }, message: "must have required property 'lineHeight'" };
                        if (vErrors === null) {
                          vErrors = [err107];
                        } else {
                          vErrors.push(err107);
                        }
                        errors++;
                      }
                      if (data32.color === void 0) {
                        const err108 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "color" }, message: "must have required property 'color'" };
                        if (vErrors === null) {
                          vErrors = [err108];
                        } else {
                          vErrors.push(err108);
                        }
                        errors++;
                      }
                      if (data32.maxLines === void 0) {
                        const err109 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "maxLines" }, message: "must have required property 'maxLines'" };
                        if (vErrors === null) {
                          vErrors = [err109];
                        } else {
                          vErrors.push(err109);
                        }
                        errors++;
                      }
                      if (data32.align === void 0) {
                        const err110 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "align" }, message: "must have required property 'align'" };
                        if (vErrors === null) {
                          vErrors = [err110];
                        } else {
                          vErrors.push(err110);
                        }
                        errors++;
                      }
                      for (const key8 in data32) {
                        if (!(key8 === "fontSize" || key8 === "fontWeight" || key8 === "lineHeight" || key8 === "color" || key8 === "maxLines" || key8 === "align")) {
                          const err111 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key8 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err111];
                          } else {
                            vErrors.push(err111);
                          }
                          errors++;
                        }
                      }
                      if (data32.fontSize !== void 0) {
                        let data33 = data32.fontSize;
                        if (typeof data33 == "number" && isFinite(data33)) {
                          if (data33 > 150 || isNaN(data33)) {
                            const err112 = { instancePath: instancePath + "/style/textRoles/title/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/maximum", keyword: "maximum", params: { comparison: "<=", limit: 150 }, message: "must be <= 150" };
                            if (vErrors === null) {
                              vErrors = [err112];
                            } else {
                              vErrors.push(err112);
                            }
                            errors++;
                          }
                          if (data33 < 12 || isNaN(data33)) {
                            const err113 = { instancePath: instancePath + "/style/textRoles/title/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/minimum", keyword: "minimum", params: { comparison: ">=", limit: 12 }, message: "must be >= 12" };
                            if (vErrors === null) {
                              vErrors = [err113];
                            } else {
                              vErrors.push(err113);
                            }
                            errors++;
                          }
                        } else {
                          const err114 = { instancePath: instancePath + "/style/textRoles/title/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err114];
                          } else {
                            vErrors.push(err114);
                          }
                          errors++;
                        }
                      }
                      if (data32.fontWeight !== void 0) {
                        let data34 = data32.fontWeight;
                        if (!(data34 === 400 || data34 === 700)) {
                          const err115 = { instancePath: instancePath + "/style/textRoles/title/fontWeight", schemaPath: "#/$defs/textRole/properties/fontWeight/enum", keyword: "enum", params: { allowedValues: schema33.properties.fontWeight.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err115];
                          } else {
                            vErrors.push(err115);
                          }
                          errors++;
                        }
                      }
                      if (data32.lineHeight !== void 0) {
                        let data35 = data32.lineHeight;
                        if (typeof data35 == "number" && isFinite(data35)) {
                          if (data35 > 2 || isNaN(data35)) {
                            const err116 = { instancePath: instancePath + "/style/textRoles/title/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/maximum", keyword: "maximum", params: { comparison: "<=", limit: 2 }, message: "must be <= 2" };
                            if (vErrors === null) {
                              vErrors = [err116];
                            } else {
                              vErrors.push(err116);
                            }
                            errors++;
                          }
                          if (data35 < 1 || isNaN(data35)) {
                            const err117 = { instancePath: instancePath + "/style/textRoles/title/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err117];
                            } else {
                              vErrors.push(err117);
                            }
                            errors++;
                          }
                        } else {
                          const err118 = { instancePath: instancePath + "/style/textRoles/title/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err118];
                          } else {
                            vErrors.push(err118);
                          }
                          errors++;
                        }
                      }
                      if (data32.color !== void 0) {
                        let data36 = data32.color;
                        if (typeof data36 === "string") {
                          if (!pattern7.test(data36)) {
                            const err119 = { instancePath: instancePath + "/style/textRoles/title/color", schemaPath: "#/$defs/textRole/properties/color/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                            if (vErrors === null) {
                              vErrors = [err119];
                            } else {
                              vErrors.push(err119);
                            }
                            errors++;
                          }
                        } else {
                          const err120 = { instancePath: instancePath + "/style/textRoles/title/color", schemaPath: "#/$defs/textRole/properties/color/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err120];
                          } else {
                            vErrors.push(err120);
                          }
                          errors++;
                        }
                      }
                      if (data32.maxLines !== void 0) {
                        let data37 = data32.maxLines;
                        if (!(typeof data37 == "number" && (!(data37 % 1) && !isNaN(data37)) && isFinite(data37))) {
                          const err121 = { instancePath: instancePath + "/style/textRoles/title/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                          if (vErrors === null) {
                            vErrors = [err121];
                          } else {
                            vErrors.push(err121);
                          }
                          errors++;
                        }
                        if (typeof data37 == "number" && isFinite(data37)) {
                          if (data37 > 4 || isNaN(data37)) {
                            const err122 = { instancePath: instancePath + "/style/textRoles/title/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/maximum", keyword: "maximum", params: { comparison: "<=", limit: 4 }, message: "must be <= 4" };
                            if (vErrors === null) {
                              vErrors = [err122];
                            } else {
                              vErrors.push(err122);
                            }
                            errors++;
                          }
                          if (data37 < 1 || isNaN(data37)) {
                            const err123 = { instancePath: instancePath + "/style/textRoles/title/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err123];
                            } else {
                              vErrors.push(err123);
                            }
                            errors++;
                          }
                        }
                      }
                      if (data32.align !== void 0) {
                        let data38 = data32.align;
                        if (!(data38 === "left" || data38 === "center" || data38 === "right")) {
                          const err124 = { instancePath: instancePath + "/style/textRoles/title/align", schemaPath: "#/$defs/textRole/properties/align/enum", keyword: "enum", params: { allowedValues: schema33.properties.align.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err124];
                          } else {
                            vErrors.push(err124);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err125 = { instancePath: instancePath + "/style/textRoles/title", schemaPath: "#/$defs/textRole/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err125];
                      } else {
                        vErrors.push(err125);
                      }
                      errors++;
                    }
                  }
                  if (data31.subtitle !== void 0) {
                    let data39 = data31.subtitle;
                    if (data39 && typeof data39 == "object" && !Array.isArray(data39)) {
                      if (data39.fontSize === void 0) {
                        const err126 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "fontSize" }, message: "must have required property 'fontSize'" };
                        if (vErrors === null) {
                          vErrors = [err126];
                        } else {
                          vErrors.push(err126);
                        }
                        errors++;
                      }
                      if (data39.fontWeight === void 0) {
                        const err127 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "fontWeight" }, message: "must have required property 'fontWeight'" };
                        if (vErrors === null) {
                          vErrors = [err127];
                        } else {
                          vErrors.push(err127);
                        }
                        errors++;
                      }
                      if (data39.lineHeight === void 0) {
                        const err128 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "lineHeight" }, message: "must have required property 'lineHeight'" };
                        if (vErrors === null) {
                          vErrors = [err128];
                        } else {
                          vErrors.push(err128);
                        }
                        errors++;
                      }
                      if (data39.color === void 0) {
                        const err129 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "color" }, message: "must have required property 'color'" };
                        if (vErrors === null) {
                          vErrors = [err129];
                        } else {
                          vErrors.push(err129);
                        }
                        errors++;
                      }
                      if (data39.maxLines === void 0) {
                        const err130 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "maxLines" }, message: "must have required property 'maxLines'" };
                        if (vErrors === null) {
                          vErrors = [err130];
                        } else {
                          vErrors.push(err130);
                        }
                        errors++;
                      }
                      if (data39.align === void 0) {
                        const err131 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "align" }, message: "must have required property 'align'" };
                        if (vErrors === null) {
                          vErrors = [err131];
                        } else {
                          vErrors.push(err131);
                        }
                        errors++;
                      }
                      for (const key9 in data39) {
                        if (!(key9 === "fontSize" || key9 === "fontWeight" || key9 === "lineHeight" || key9 === "color" || key9 === "maxLines" || key9 === "align")) {
                          const err132 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key9 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err132];
                          } else {
                            vErrors.push(err132);
                          }
                          errors++;
                        }
                      }
                      if (data39.fontSize !== void 0) {
                        let data40 = data39.fontSize;
                        if (typeof data40 == "number" && isFinite(data40)) {
                          if (data40 > 150 || isNaN(data40)) {
                            const err133 = { instancePath: instancePath + "/style/textRoles/subtitle/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/maximum", keyword: "maximum", params: { comparison: "<=", limit: 150 }, message: "must be <= 150" };
                            if (vErrors === null) {
                              vErrors = [err133];
                            } else {
                              vErrors.push(err133);
                            }
                            errors++;
                          }
                          if (data40 < 12 || isNaN(data40)) {
                            const err134 = { instancePath: instancePath + "/style/textRoles/subtitle/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/minimum", keyword: "minimum", params: { comparison: ">=", limit: 12 }, message: "must be >= 12" };
                            if (vErrors === null) {
                              vErrors = [err134];
                            } else {
                              vErrors.push(err134);
                            }
                            errors++;
                          }
                        } else {
                          const err135 = { instancePath: instancePath + "/style/textRoles/subtitle/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err135];
                          } else {
                            vErrors.push(err135);
                          }
                          errors++;
                        }
                      }
                      if (data39.fontWeight !== void 0) {
                        let data41 = data39.fontWeight;
                        if (!(data41 === 400 || data41 === 700)) {
                          const err136 = { instancePath: instancePath + "/style/textRoles/subtitle/fontWeight", schemaPath: "#/$defs/textRole/properties/fontWeight/enum", keyword: "enum", params: { allowedValues: schema33.properties.fontWeight.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err136];
                          } else {
                            vErrors.push(err136);
                          }
                          errors++;
                        }
                      }
                      if (data39.lineHeight !== void 0) {
                        let data42 = data39.lineHeight;
                        if (typeof data42 == "number" && isFinite(data42)) {
                          if (data42 > 2 || isNaN(data42)) {
                            const err137 = { instancePath: instancePath + "/style/textRoles/subtitle/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/maximum", keyword: "maximum", params: { comparison: "<=", limit: 2 }, message: "must be <= 2" };
                            if (vErrors === null) {
                              vErrors = [err137];
                            } else {
                              vErrors.push(err137);
                            }
                            errors++;
                          }
                          if (data42 < 1 || isNaN(data42)) {
                            const err138 = { instancePath: instancePath + "/style/textRoles/subtitle/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err138];
                            } else {
                              vErrors.push(err138);
                            }
                            errors++;
                          }
                        } else {
                          const err139 = { instancePath: instancePath + "/style/textRoles/subtitle/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err139];
                          } else {
                            vErrors.push(err139);
                          }
                          errors++;
                        }
                      }
                      if (data39.color !== void 0) {
                        let data43 = data39.color;
                        if (typeof data43 === "string") {
                          if (!pattern7.test(data43)) {
                            const err140 = { instancePath: instancePath + "/style/textRoles/subtitle/color", schemaPath: "#/$defs/textRole/properties/color/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                            if (vErrors === null) {
                              vErrors = [err140];
                            } else {
                              vErrors.push(err140);
                            }
                            errors++;
                          }
                        } else {
                          const err141 = { instancePath: instancePath + "/style/textRoles/subtitle/color", schemaPath: "#/$defs/textRole/properties/color/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err141];
                          } else {
                            vErrors.push(err141);
                          }
                          errors++;
                        }
                      }
                      if (data39.maxLines !== void 0) {
                        let data44 = data39.maxLines;
                        if (!(typeof data44 == "number" && (!(data44 % 1) && !isNaN(data44)) && isFinite(data44))) {
                          const err142 = { instancePath: instancePath + "/style/textRoles/subtitle/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                          if (vErrors === null) {
                            vErrors = [err142];
                          } else {
                            vErrors.push(err142);
                          }
                          errors++;
                        }
                        if (typeof data44 == "number" && isFinite(data44)) {
                          if (data44 > 4 || isNaN(data44)) {
                            const err143 = { instancePath: instancePath + "/style/textRoles/subtitle/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/maximum", keyword: "maximum", params: { comparison: "<=", limit: 4 }, message: "must be <= 4" };
                            if (vErrors === null) {
                              vErrors = [err143];
                            } else {
                              vErrors.push(err143);
                            }
                            errors++;
                          }
                          if (data44 < 1 || isNaN(data44)) {
                            const err144 = { instancePath: instancePath + "/style/textRoles/subtitle/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err144];
                            } else {
                              vErrors.push(err144);
                            }
                            errors++;
                          }
                        }
                      }
                      if (data39.align !== void 0) {
                        let data45 = data39.align;
                        if (!(data45 === "left" || data45 === "center" || data45 === "right")) {
                          const err145 = { instancePath: instancePath + "/style/textRoles/subtitle/align", schemaPath: "#/$defs/textRole/properties/align/enum", keyword: "enum", params: { allowedValues: schema33.properties.align.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err145];
                          } else {
                            vErrors.push(err145);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err146 = { instancePath: instancePath + "/style/textRoles/subtitle", schemaPath: "#/$defs/textRole/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err146];
                      } else {
                        vErrors.push(err146);
                      }
                      errors++;
                    }
                  }
                  if (data31.caption !== void 0) {
                    let data46 = data31.caption;
                    if (data46 && typeof data46 == "object" && !Array.isArray(data46)) {
                      if (data46.fontSize === void 0) {
                        const err147 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "fontSize" }, message: "must have required property 'fontSize'" };
                        if (vErrors === null) {
                          vErrors = [err147];
                        } else {
                          vErrors.push(err147);
                        }
                        errors++;
                      }
                      if (data46.fontWeight === void 0) {
                        const err148 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "fontWeight" }, message: "must have required property 'fontWeight'" };
                        if (vErrors === null) {
                          vErrors = [err148];
                        } else {
                          vErrors.push(err148);
                        }
                        errors++;
                      }
                      if (data46.lineHeight === void 0) {
                        const err149 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "lineHeight" }, message: "must have required property 'lineHeight'" };
                        if (vErrors === null) {
                          vErrors = [err149];
                        } else {
                          vErrors.push(err149);
                        }
                        errors++;
                      }
                      if (data46.color === void 0) {
                        const err150 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "color" }, message: "must have required property 'color'" };
                        if (vErrors === null) {
                          vErrors = [err150];
                        } else {
                          vErrors.push(err150);
                        }
                        errors++;
                      }
                      if (data46.maxLines === void 0) {
                        const err151 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "maxLines" }, message: "must have required property 'maxLines'" };
                        if (vErrors === null) {
                          vErrors = [err151];
                        } else {
                          vErrors.push(err151);
                        }
                        errors++;
                      }
                      if (data46.align === void 0) {
                        const err152 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/required", keyword: "required", params: { missingProperty: "align" }, message: "must have required property 'align'" };
                        if (vErrors === null) {
                          vErrors = [err152];
                        } else {
                          vErrors.push(err152);
                        }
                        errors++;
                      }
                      for (const key10 in data46) {
                        if (!(key10 === "fontSize" || key10 === "fontWeight" || key10 === "lineHeight" || key10 === "color" || key10 === "maxLines" || key10 === "align")) {
                          const err153 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key10 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err153];
                          } else {
                            vErrors.push(err153);
                          }
                          errors++;
                        }
                      }
                      if (data46.fontSize !== void 0) {
                        let data47 = data46.fontSize;
                        if (typeof data47 == "number" && isFinite(data47)) {
                          if (data47 > 150 || isNaN(data47)) {
                            const err154 = { instancePath: instancePath + "/style/textRoles/caption/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/maximum", keyword: "maximum", params: { comparison: "<=", limit: 150 }, message: "must be <= 150" };
                            if (vErrors === null) {
                              vErrors = [err154];
                            } else {
                              vErrors.push(err154);
                            }
                            errors++;
                          }
                          if (data47 < 12 || isNaN(data47)) {
                            const err155 = { instancePath: instancePath + "/style/textRoles/caption/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/minimum", keyword: "minimum", params: { comparison: ">=", limit: 12 }, message: "must be >= 12" };
                            if (vErrors === null) {
                              vErrors = [err155];
                            } else {
                              vErrors.push(err155);
                            }
                            errors++;
                          }
                        } else {
                          const err156 = { instancePath: instancePath + "/style/textRoles/caption/fontSize", schemaPath: "#/$defs/textRole/properties/fontSize/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err156];
                          } else {
                            vErrors.push(err156);
                          }
                          errors++;
                        }
                      }
                      if (data46.fontWeight !== void 0) {
                        let data48 = data46.fontWeight;
                        if (!(data48 === 400 || data48 === 700)) {
                          const err157 = { instancePath: instancePath + "/style/textRoles/caption/fontWeight", schemaPath: "#/$defs/textRole/properties/fontWeight/enum", keyword: "enum", params: { allowedValues: schema33.properties.fontWeight.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err157];
                          } else {
                            vErrors.push(err157);
                          }
                          errors++;
                        }
                      }
                      if (data46.lineHeight !== void 0) {
                        let data49 = data46.lineHeight;
                        if (typeof data49 == "number" && isFinite(data49)) {
                          if (data49 > 2 || isNaN(data49)) {
                            const err158 = { instancePath: instancePath + "/style/textRoles/caption/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/maximum", keyword: "maximum", params: { comparison: "<=", limit: 2 }, message: "must be <= 2" };
                            if (vErrors === null) {
                              vErrors = [err158];
                            } else {
                              vErrors.push(err158);
                            }
                            errors++;
                          }
                          if (data49 < 1 || isNaN(data49)) {
                            const err159 = { instancePath: instancePath + "/style/textRoles/caption/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err159];
                            } else {
                              vErrors.push(err159);
                            }
                            errors++;
                          }
                        } else {
                          const err160 = { instancePath: instancePath + "/style/textRoles/caption/lineHeight", schemaPath: "#/$defs/textRole/properties/lineHeight/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err160];
                          } else {
                            vErrors.push(err160);
                          }
                          errors++;
                        }
                      }
                      if (data46.color !== void 0) {
                        let data50 = data46.color;
                        if (typeof data50 === "string") {
                          if (!pattern7.test(data50)) {
                            const err161 = { instancePath: instancePath + "/style/textRoles/caption/color", schemaPath: "#/$defs/textRole/properties/color/pattern", keyword: "pattern", params: { pattern: "^#[0-9a-fA-F]{6}$" }, message: 'must match pattern "^#[0-9a-fA-F]{6}$"' };
                            if (vErrors === null) {
                              vErrors = [err161];
                            } else {
                              vErrors.push(err161);
                            }
                            errors++;
                          }
                        } else {
                          const err162 = { instancePath: instancePath + "/style/textRoles/caption/color", schemaPath: "#/$defs/textRole/properties/color/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err162];
                          } else {
                            vErrors.push(err162);
                          }
                          errors++;
                        }
                      }
                      if (data46.maxLines !== void 0) {
                        let data51 = data46.maxLines;
                        if (!(typeof data51 == "number" && (!(data51 % 1) && !isNaN(data51)) && isFinite(data51))) {
                          const err163 = { instancePath: instancePath + "/style/textRoles/caption/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                          if (vErrors === null) {
                            vErrors = [err163];
                          } else {
                            vErrors.push(err163);
                          }
                          errors++;
                        }
                        if (typeof data51 == "number" && isFinite(data51)) {
                          if (data51 > 4 || isNaN(data51)) {
                            const err164 = { instancePath: instancePath + "/style/textRoles/caption/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/maximum", keyword: "maximum", params: { comparison: "<=", limit: 4 }, message: "must be <= 4" };
                            if (vErrors === null) {
                              vErrors = [err164];
                            } else {
                              vErrors.push(err164);
                            }
                            errors++;
                          }
                          if (data51 < 1 || isNaN(data51)) {
                            const err165 = { instancePath: instancePath + "/style/textRoles/caption/maxLines", schemaPath: "#/$defs/textRole/properties/maxLines/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err165];
                            } else {
                              vErrors.push(err165);
                            }
                            errors++;
                          }
                        }
                      }
                      if (data46.align !== void 0) {
                        let data52 = data46.align;
                        if (!(data52 === "left" || data52 === "center" || data52 === "right")) {
                          const err166 = { instancePath: instancePath + "/style/textRoles/caption/align", schemaPath: "#/$defs/textRole/properties/align/enum", keyword: "enum", params: { allowedValues: schema33.properties.align.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err166];
                          } else {
                            vErrors.push(err166);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err167 = { instancePath: instancePath + "/style/textRoles/caption", schemaPath: "#/$defs/textRole/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err167];
                      } else {
                        vErrors.push(err167);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err168 = { instancePath: instancePath + "/style/textRoles", schemaPath: "#/properties/style/properties/textRoles/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err168];
                  } else {
                    vErrors.push(err168);
                  }
                  errors++;
                }
              }
            } else {
              const err169 = { instancePath: instancePath + "/style", schemaPath: "#/properties/style/type", keyword: "type", params: { type: "object" }, message: "must be object" };
              if (vErrors === null) {
                vErrors = [err169];
              } else {
                vErrors.push(err169);
              }
              errors++;
            }
          }
          if (data.assets !== void 0) {
            let data53 = data.assets;
            if (Array.isArray(data53)) {
              if (data53.length > 20) {
                const err170 = { instancePath: instancePath + "/assets", schemaPath: "#/properties/assets/maxItems", keyword: "maxItems", params: { limit: 20 }, message: "must NOT have more than 20 items" };
                if (vErrors === null) {
                  vErrors = [err170];
                } else {
                  vErrors.push(err170);
                }
                errors++;
              }
              if (data53.length < 1) {
                const err171 = { instancePath: instancePath + "/assets", schemaPath: "#/properties/assets/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                if (vErrors === null) {
                  vErrors = [err171];
                } else {
                  vErrors.push(err171);
                }
                errors++;
              }
              const len0 = data53.length;
              for (let i0 = 0; i0 < len0; i0++) {
                if (!validate21(data53[i0], { instancePath: instancePath + "/assets/" + i0, parentData: data53, parentDataProperty: i0, rootData, dynamicAnchors })) {
                  vErrors = vErrors === null ? validate21.errors : vErrors.concat(validate21.errors);
                  errors = vErrors.length;
                }
              }
            } else {
              const err172 = { instancePath: instancePath + "/assets", schemaPath: "#/properties/assets/type", keyword: "type", params: { type: "array" }, message: "must be array" };
              if (vErrors === null) {
                vErrors = [err172];
              } else {
                vErrors.push(err172);
              }
              errors++;
            }
          }
          if (data.paths !== void 0) {
            let data55 = data.paths;
            if (Array.isArray(data55)) {
              if (data55.length > 20) {
                const err173 = { instancePath: instancePath + "/paths", schemaPath: "#/properties/paths/maxItems", keyword: "maxItems", params: { limit: 20 }, message: "must NOT have more than 20 items" };
                if (vErrors === null) {
                  vErrors = [err173];
                } else {
                  vErrors.push(err173);
                }
                errors++;
              }
              if (data55.length < 1) {
                const err174 = { instancePath: instancePath + "/paths", schemaPath: "#/properties/paths/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                if (vErrors === null) {
                  vErrors = [err174];
                } else {
                  vErrors.push(err174);
                }
                errors++;
              }
              const len1 = data55.length;
              for (let i1 = 0; i1 < len1; i1++) {
                let data56 = data55[i1];
                if (data56 && typeof data56 == "object" && !Array.isArray(data56)) {
                  if (data56.id === void 0) {
                    const err175 = { instancePath: instancePath + "/paths/" + i1, schemaPath: "#/properties/paths/items/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err175];
                    } else {
                      vErrors.push(err175);
                    }
                    errors++;
                  }
                  if (data56.points === void 0) {
                    const err176 = { instancePath: instancePath + "/paths/" + i1, schemaPath: "#/properties/paths/items/required", keyword: "required", params: { missingProperty: "points" }, message: "must have required property 'points'" };
                    if (vErrors === null) {
                      vErrors = [err176];
                    } else {
                      vErrors.push(err176);
                    }
                    errors++;
                  }
                  for (const key11 in data56) {
                    if (!(key11 === "id" || key11 === "points")) {
                      const err177 = { instancePath: instancePath + "/paths/" + i1, schemaPath: "#/properties/paths/items/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key11 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err177];
                      } else {
                        vErrors.push(err177);
                      }
                      errors++;
                    }
                  }
                  if (data56.id !== void 0) {
                    let data57 = data56.id;
                    if (typeof data57 === "string") {
                      if (!pattern4.test(data57)) {
                        const err178 = { instancePath: instancePath + "/paths/" + i1 + "/id", schemaPath: "#/properties/paths/items/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err178];
                        } else {
                          vErrors.push(err178);
                        }
                        errors++;
                      }
                    } else {
                      const err179 = { instancePath: instancePath + "/paths/" + i1 + "/id", schemaPath: "#/properties/paths/items/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err179];
                      } else {
                        vErrors.push(err179);
                      }
                      errors++;
                    }
                  }
                  if (data56.points !== void 0) {
                    let data58 = data56.points;
                    if (Array.isArray(data58)) {
                      if (data58.length > 4) {
                        const err180 = { instancePath: instancePath + "/paths/" + i1 + "/points", schemaPath: "#/properties/paths/items/properties/points/maxItems", keyword: "maxItems", params: { limit: 4 }, message: "must NOT have more than 4 items" };
                        if (vErrors === null) {
                          vErrors = [err180];
                        } else {
                          vErrors.push(err180);
                        }
                        errors++;
                      }
                      if (data58.length < 4) {
                        const err181 = { instancePath: instancePath + "/paths/" + i1 + "/points", schemaPath: "#/properties/paths/items/properties/points/minItems", keyword: "minItems", params: { limit: 4 }, message: "must NOT have fewer than 4 items" };
                        if (vErrors === null) {
                          vErrors = [err181];
                        } else {
                          vErrors.push(err181);
                        }
                        errors++;
                      }
                      const len2 = data58.length;
                      for (let i2 = 0; i2 < len2; i2++) {
                        let data59 = data58[i2];
                        if (data59 && typeof data59 == "object" && !Array.isArray(data59)) {
                          if (data59.x === void 0) {
                            const err182 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2, schemaPath: "#/$defs/point/required", keyword: "required", params: { missingProperty: "x" }, message: "must have required property 'x'" };
                            if (vErrors === null) {
                              vErrors = [err182];
                            } else {
                              vErrors.push(err182);
                            }
                            errors++;
                          }
                          if (data59.y === void 0) {
                            const err183 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2, schemaPath: "#/$defs/point/required", keyword: "required", params: { missingProperty: "y" }, message: "must have required property 'y'" };
                            if (vErrors === null) {
                              vErrors = [err183];
                            } else {
                              vErrors.push(err183);
                            }
                            errors++;
                          }
                          for (const key12 in data59) {
                            if (!(key12 === "x" || key12 === "y")) {
                              const err184 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2, schemaPath: "#/$defs/point/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key12 }, message: "must NOT have additional properties" };
                              if (vErrors === null) {
                                vErrors = [err184];
                              } else {
                                vErrors.push(err184);
                              }
                              errors++;
                            }
                          }
                          if (data59.x !== void 0) {
                            let data60 = data59.x;
                            if (typeof data60 == "number" && isFinite(data60)) {
                              if (data60 > 1e5 || isNaN(data60)) {
                                const err185 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2 + "/x", schemaPath: "#/$defs/point/properties/x/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                                if (vErrors === null) {
                                  vErrors = [err185];
                                } else {
                                  vErrors.push(err185);
                                }
                                errors++;
                              }
                              if (data60 < -1e5 || isNaN(data60)) {
                                const err186 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2 + "/x", schemaPath: "#/$defs/point/properties/x/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                                if (vErrors === null) {
                                  vErrors = [err186];
                                } else {
                                  vErrors.push(err186);
                                }
                                errors++;
                              }
                            } else {
                              const err187 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2 + "/x", schemaPath: "#/$defs/point/properties/x/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err187];
                              } else {
                                vErrors.push(err187);
                              }
                              errors++;
                            }
                          }
                          if (data59.y !== void 0) {
                            let data61 = data59.y;
                            if (typeof data61 == "number" && isFinite(data61)) {
                              if (data61 > 1e5 || isNaN(data61)) {
                                const err188 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2 + "/y", schemaPath: "#/$defs/point/properties/y/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                                if (vErrors === null) {
                                  vErrors = [err188];
                                } else {
                                  vErrors.push(err188);
                                }
                                errors++;
                              }
                              if (data61 < -1e5 || isNaN(data61)) {
                                const err189 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2 + "/y", schemaPath: "#/$defs/point/properties/y/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                                if (vErrors === null) {
                                  vErrors = [err189];
                                } else {
                                  vErrors.push(err189);
                                }
                                errors++;
                              }
                            } else {
                              const err190 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2 + "/y", schemaPath: "#/$defs/point/properties/y/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err190];
                              } else {
                                vErrors.push(err190);
                              }
                              errors++;
                            }
                          }
                        } else {
                          const err191 = { instancePath: instancePath + "/paths/" + i1 + "/points/" + i2, schemaPath: "#/$defs/point/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                          if (vErrors === null) {
                            vErrors = [err191];
                          } else {
                            vErrors.push(err191);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err192 = { instancePath: instancePath + "/paths/" + i1 + "/points", schemaPath: "#/properties/paths/items/properties/points/type", keyword: "type", params: { type: "array" }, message: "must be array" };
                      if (vErrors === null) {
                        vErrors = [err192];
                      } else {
                        vErrors.push(err192);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err193 = { instancePath: instancePath + "/paths/" + i1, schemaPath: "#/properties/paths/items/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err193];
                  } else {
                    vErrors.push(err193);
                  }
                  errors++;
                }
              }
            } else {
              const err194 = { instancePath: instancePath + "/paths", schemaPath: "#/properties/paths/type", keyword: "type", params: { type: "array" }, message: "must be array" };
              if (vErrors === null) {
                vErrors = [err194];
              } else {
                vErrors.push(err194);
              }
              errors++;
            }
          }
          if (data.nodes !== void 0) {
            let data62 = data.nodes;
            if (Array.isArray(data62)) {
              if (data62.length > 80) {
                const err195 = { instancePath: instancePath + "/nodes", schemaPath: "#/properties/nodes/maxItems", keyword: "maxItems", params: { limit: 80 }, message: "must NOT have more than 80 items" };
                if (vErrors === null) {
                  vErrors = [err195];
                } else {
                  vErrors.push(err195);
                }
                errors++;
              }
              if (data62.length < 1) {
                const err196 = { instancePath: instancePath + "/nodes", schemaPath: "#/properties/nodes/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                if (vErrors === null) {
                  vErrors = [err196];
                } else {
                  vErrors.push(err196);
                }
                errors++;
              }
              const len3 = data62.length;
              for (let i3 = 0; i3 < len3; i3++) {
                let data63 = data62[i3];
                const _errs131 = errors;
                let valid26 = false;
                let passing0 = null;
                const _errs132 = errors;
                if (data63 && typeof data63 == "object" && !Array.isArray(data63)) {
                  if (data63.id === void 0) {
                    const err197 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err197];
                    } else {
                      vErrors.push(err197);
                    }
                    errors++;
                  }
                  if (data63.typeVersion === void 0) {
                    const err198 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                    if (vErrors === null) {
                      vErrors = [err198];
                    } else {
                      vErrors.push(err198);
                    }
                    errors++;
                  }
                  if (data63.zIndex === void 0) {
                    const err199 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "zIndex" }, message: "must have required property 'zIndex'" };
                    if (vErrors === null) {
                      vErrors = [err199];
                    } else {
                      vErrors.push(err199);
                    }
                    errors++;
                  }
                  if (data63.initialOpacity === void 0) {
                    const err200 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "initialOpacity" }, message: "must have required property 'initialOpacity'" };
                    if (vErrors === null) {
                      vErrors = [err200];
                    } else {
                      vErrors.push(err200);
                    }
                    errors++;
                  }
                  if (data63.type === void 0) {
                    const err201 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                    if (vErrors === null) {
                      vErrors = [err201];
                    } else {
                      vErrors.push(err201);
                    }
                    errors++;
                  }
                  if (data63.box === void 0) {
                    const err202 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "box" }, message: "must have required property 'box'" };
                    if (vErrors === null) {
                      vErrors = [err202];
                    } else {
                      vErrors.push(err202);
                    }
                    errors++;
                  }
                  if (data63.role === void 0) {
                    const err203 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "role" }, message: "must have required property 'role'" };
                    if (vErrors === null) {
                      vErrors = [err203];
                    } else {
                      vErrors.push(err203);
                    }
                    errors++;
                  }
                  if (data63.content === void 0) {
                    const err204 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/required", keyword: "required", params: { missingProperty: "content" }, message: "must have required property 'content'" };
                    if (vErrors === null) {
                      vErrors = [err204];
                    } else {
                      vErrors.push(err204);
                    }
                    errors++;
                  }
                  for (const key13 in data63) {
                    if (!(key13 === "id" || key13 === "typeVersion" || key13 === "zIndex" || key13 === "initialOpacity" || key13 === "type" || key13 === "box" || key13 === "role" || key13 === "content")) {
                      const err205 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key13 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err205];
                      } else {
                        vErrors.push(err205);
                      }
                      errors++;
                    }
                  }
                  if (data63.id !== void 0) {
                    let data64 = data63.id;
                    if (typeof data64 === "string") {
                      if (!pattern4.test(data64)) {
                        const err206 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/0/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err206];
                        } else {
                          vErrors.push(err206);
                        }
                        errors++;
                      }
                    } else {
                      const err207 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/0/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err207];
                      } else {
                        vErrors.push(err207);
                      }
                      errors++;
                    }
                  }
                  if (data63.typeVersion !== void 0) {
                    if ("0.1.0" !== data63.typeVersion) {
                      const err208 = { instancePath: instancePath + "/nodes/" + i3 + "/typeVersion", schemaPath: "#/properties/nodes/items/oneOf/0/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err208];
                      } else {
                        vErrors.push(err208);
                      }
                      errors++;
                    }
                  }
                  if (data63.zIndex !== void 0) {
                    let data66 = data63.zIndex;
                    if (!(typeof data66 == "number" && (!(data66 % 1) && !isNaN(data66)) && isFinite(data66))) {
                      const err209 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/0/properties/zIndex/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err209];
                      } else {
                        vErrors.push(err209);
                      }
                      errors++;
                    }
                    if (typeof data66 == "number" && isFinite(data66)) {
                      if (data66 > 100 || isNaN(data66)) {
                        const err210 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/0/properties/zIndex/maximum", keyword: "maximum", params: { comparison: "<=", limit: 100 }, message: "must be <= 100" };
                        if (vErrors === null) {
                          vErrors = [err210];
                        } else {
                          vErrors.push(err210);
                        }
                        errors++;
                      }
                      if (data66 < -100 || isNaN(data66)) {
                        const err211 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/0/properties/zIndex/minimum", keyword: "minimum", params: { comparison: ">=", limit: -100 }, message: "must be >= -100" };
                        if (vErrors === null) {
                          vErrors = [err211];
                        } else {
                          vErrors.push(err211);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data63.initialOpacity !== void 0) {
                    let data67 = data63.initialOpacity;
                    if (typeof data67 == "number" && isFinite(data67)) {
                      if (data67 > 1 || isNaN(data67)) {
                        const err212 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/0/properties/initialOpacity/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err212];
                        } else {
                          vErrors.push(err212);
                        }
                        errors++;
                      }
                      if (data67 < 0 || isNaN(data67)) {
                        const err213 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/0/properties/initialOpacity/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err213];
                        } else {
                          vErrors.push(err213);
                        }
                        errors++;
                      }
                    } else {
                      const err214 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/0/properties/initialOpacity/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err214];
                      } else {
                        vErrors.push(err214);
                      }
                      errors++;
                    }
                  }
                  if (data63.type !== void 0) {
                    if ("text" !== data63.type) {
                      const err215 = { instancePath: instancePath + "/nodes/" + i3 + "/type", schemaPath: "#/properties/nodes/items/oneOf/0/properties/type/const", keyword: "const", params: { allowedValue: "text" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err215];
                      } else {
                        vErrors.push(err215);
                      }
                      errors++;
                    }
                  }
                  if (data63.box !== void 0) {
                    let data69 = data63.box;
                    if (data69 && typeof data69 == "object" && !Array.isArray(data69)) {
                      if (data69.x === void 0) {
                        const err216 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "x" }, message: "must have required property 'x'" };
                        if (vErrors === null) {
                          vErrors = [err216];
                        } else {
                          vErrors.push(err216);
                        }
                        errors++;
                      }
                      if (data69.y === void 0) {
                        const err217 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "y" }, message: "must have required property 'y'" };
                        if (vErrors === null) {
                          vErrors = [err217];
                        } else {
                          vErrors.push(err217);
                        }
                        errors++;
                      }
                      if (data69.width === void 0) {
                        const err218 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "width" }, message: "must have required property 'width'" };
                        if (vErrors === null) {
                          vErrors = [err218];
                        } else {
                          vErrors.push(err218);
                        }
                        errors++;
                      }
                      if (data69.height === void 0) {
                        const err219 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "height" }, message: "must have required property 'height'" };
                        if (vErrors === null) {
                          vErrors = [err219];
                        } else {
                          vErrors.push(err219);
                        }
                        errors++;
                      }
                      for (const key14 in data69) {
                        if (!(key14 === "x" || key14 === "y" || key14 === "width" || key14 === "height")) {
                          const err220 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key14 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err220];
                          } else {
                            vErrors.push(err220);
                          }
                          errors++;
                        }
                      }
                      if (data69.x !== void 0) {
                        let data70 = data69.x;
                        if (typeof data70 == "number" && isFinite(data70)) {
                          if (data70 > 1e5 || isNaN(data70)) {
                            const err221 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                            if (vErrors === null) {
                              vErrors = [err221];
                            } else {
                              vErrors.push(err221);
                            }
                            errors++;
                          }
                          if (data70 < -1e5 || isNaN(data70)) {
                            const err222 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                            if (vErrors === null) {
                              vErrors = [err222];
                            } else {
                              vErrors.push(err222);
                            }
                            errors++;
                          }
                        } else {
                          const err223 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err223];
                          } else {
                            vErrors.push(err223);
                          }
                          errors++;
                        }
                      }
                      if (data69.y !== void 0) {
                        let data71 = data69.y;
                        if (typeof data71 == "number" && isFinite(data71)) {
                          if (data71 > 1e5 || isNaN(data71)) {
                            const err224 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                            if (vErrors === null) {
                              vErrors = [err224];
                            } else {
                              vErrors.push(err224);
                            }
                            errors++;
                          }
                          if (data71 < -1e5 || isNaN(data71)) {
                            const err225 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                            if (vErrors === null) {
                              vErrors = [err225];
                            } else {
                              vErrors.push(err225);
                            }
                            errors++;
                          }
                        } else {
                          const err226 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err226];
                          } else {
                            vErrors.push(err226);
                          }
                          errors++;
                        }
                      }
                      if (data69.width !== void 0) {
                        let data72 = data69.width;
                        if (typeof data72 == "number" && isFinite(data72)) {
                          if (data72 > 1e4 || isNaN(data72)) {
                            const err227 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                            if (vErrors === null) {
                              vErrors = [err227];
                            } else {
                              vErrors.push(err227);
                            }
                            errors++;
                          }
                          if (data72 < 1 || isNaN(data72)) {
                            const err228 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err228];
                            } else {
                              vErrors.push(err228);
                            }
                            errors++;
                          }
                        } else {
                          const err229 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err229];
                          } else {
                            vErrors.push(err229);
                          }
                          errors++;
                        }
                      }
                      if (data69.height !== void 0) {
                        let data73 = data69.height;
                        if (typeof data73 == "number" && isFinite(data73)) {
                          if (data73 > 1e4 || isNaN(data73)) {
                            const err230 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                            if (vErrors === null) {
                              vErrors = [err230];
                            } else {
                              vErrors.push(err230);
                            }
                            errors++;
                          }
                          if (data73 < 1 || isNaN(data73)) {
                            const err231 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err231];
                            } else {
                              vErrors.push(err231);
                            }
                            errors++;
                          }
                        } else {
                          const err232 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err232];
                          } else {
                            vErrors.push(err232);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err233 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err233];
                      } else {
                        vErrors.push(err233);
                      }
                      errors++;
                    }
                  }
                  if (data63.role !== void 0) {
                    let data74 = data63.role;
                    if (!(data74 === "title" || data74 === "subtitle" || data74 === "caption")) {
                      const err234 = { instancePath: instancePath + "/nodes/" + i3 + "/role", schemaPath: "#/properties/nodes/items/oneOf/0/properties/role/enum", keyword: "enum", params: { allowedValues: schema31.properties.nodes.items.oneOf[0].properties.role.enum }, message: "must be equal to one of the allowed values" };
                      if (vErrors === null) {
                        vErrors = [err234];
                      } else {
                        vErrors.push(err234);
                      }
                      errors++;
                    }
                  }
                  if (data63.content !== void 0) {
                    let data75 = data63.content;
                    const _errs157 = errors;
                    let valid30 = false;
                    let passing1 = null;
                    const _errs158 = errors;
                    if (data75 && typeof data75 == "object" && !Array.isArray(data75)) {
                      if (data75.kind === void 0) {
                        const err235 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/required", keyword: "required", params: { missingProperty: "kind" }, message: "must have required property 'kind'" };
                        if (vErrors === null) {
                          vErrors = [err235];
                        } else {
                          vErrors.push(err235);
                        }
                        errors++;
                      }
                      if (data75.text === void 0) {
                        const err236 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/required", keyword: "required", params: { missingProperty: "text" }, message: "must have required property 'text'" };
                        if (vErrors === null) {
                          vErrors = [err236];
                        } else {
                          vErrors.push(err236);
                        }
                        errors++;
                      }
                      for (const key15 in data75) {
                        if (!(key15 === "kind" || key15 === "text")) {
                          const err237 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key15 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err237];
                          } else {
                            vErrors.push(err237);
                          }
                          errors++;
                        }
                      }
                      if (data75.kind !== void 0) {
                        if ("static" !== data75.kind) {
                          const err238 = { instancePath: instancePath + "/nodes/" + i3 + "/content/kind", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/properties/kind/const", keyword: "const", params: { allowedValue: "static" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err238];
                          } else {
                            vErrors.push(err238);
                          }
                          errors++;
                        }
                      }
                      if (data75.text !== void 0) {
                        let data77 = data75.text;
                        if (typeof data77 === "string") {
                          if (func2(data77) > 2e3) {
                            const err239 = { instancePath: instancePath + "/nodes/" + i3 + "/content/text", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/properties/text/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
                            if (vErrors === null) {
                              vErrors = [err239];
                            } else {
                              vErrors.push(err239);
                            }
                            errors++;
                          }
                          if (func2(data77) < 1) {
                            const err240 = { instancePath: instancePath + "/nodes/" + i3 + "/content/text", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/properties/text/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                            if (vErrors === null) {
                              vErrors = [err240];
                            } else {
                              vErrors.push(err240);
                            }
                            errors++;
                          }
                        } else {
                          const err241 = { instancePath: instancePath + "/nodes/" + i3 + "/content/text", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/properties/text/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err241];
                          } else {
                            vErrors.push(err241);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err242 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/0/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err242];
                      } else {
                        vErrors.push(err242);
                      }
                      errors++;
                    }
                    var _valid1 = _errs158 === errors;
                    if (_valid1) {
                      valid30 = true;
                      passing1 = 0;
                      var props0 = true;
                    }
                    const _errs164 = errors;
                    if (data75 && typeof data75 == "object" && !Array.isArray(data75)) {
                      if (data75.kind === void 0) {
                        const err243 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/1/required", keyword: "required", params: { missingProperty: "kind" }, message: "must have required property 'kind'" };
                        if (vErrors === null) {
                          vErrors = [err243];
                        } else {
                          vErrors.push(err243);
                        }
                        errors++;
                      }
                      for (const key16 in data75) {
                        if (!(key16 === "kind")) {
                          const err244 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/1/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key16 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err244];
                          } else {
                            vErrors.push(err244);
                          }
                          errors++;
                        }
                      }
                      if (data75.kind !== void 0) {
                        if ("beat-summary" !== data75.kind) {
                          const err245 = { instancePath: instancePath + "/nodes/" + i3 + "/content/kind", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/1/properties/kind/const", keyword: "const", params: { allowedValue: "beat-summary" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err245];
                          } else {
                            vErrors.push(err245);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err246 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf/1/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err246];
                      } else {
                        vErrors.push(err246);
                      }
                      errors++;
                    }
                    var _valid1 = _errs164 === errors;
                    if (_valid1 && valid30) {
                      valid30 = false;
                      passing1 = [passing1, 1];
                    } else {
                      if (_valid1) {
                        valid30 = true;
                        passing1 = 1;
                        if (props0 !== true) {
                          props0 = true;
                        }
                      }
                    }
                    if (!valid30) {
                      const err247 = { instancePath: instancePath + "/nodes/" + i3 + "/content", schemaPath: "#/properties/nodes/items/oneOf/0/properties/content/oneOf", keyword: "oneOf", params: { passingSchemas: passing1 }, message: "must match exactly one schema in oneOf" };
                      if (vErrors === null) {
                        vErrors = [err247];
                      } else {
                        vErrors.push(err247);
                      }
                      errors++;
                    } else {
                      errors = _errs157;
                      if (vErrors !== null) {
                        if (_errs157) {
                          vErrors.length = _errs157;
                        } else {
                          vErrors = null;
                        }
                      }
                    }
                  }
                } else {
                  const err248 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/0/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err248];
                  } else {
                    vErrors.push(err248);
                  }
                  errors++;
                }
                var _valid0 = _errs132 === errors;
                if (_valid0) {
                  valid26 = true;
                  passing0 = 0;
                  var props1 = true;
                }
                const _errs168 = errors;
                if (data63 && typeof data63 == "object" && !Array.isArray(data63)) {
                  if (data63.id === void 0) {
                    const err249 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err249];
                    } else {
                      vErrors.push(err249);
                    }
                    errors++;
                  }
                  if (data63.typeVersion === void 0) {
                    const err250 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                    if (vErrors === null) {
                      vErrors = [err250];
                    } else {
                      vErrors.push(err250);
                    }
                    errors++;
                  }
                  if (data63.zIndex === void 0) {
                    const err251 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "zIndex" }, message: "must have required property 'zIndex'" };
                    if (vErrors === null) {
                      vErrors = [err251];
                    } else {
                      vErrors.push(err251);
                    }
                    errors++;
                  }
                  if (data63.initialOpacity === void 0) {
                    const err252 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "initialOpacity" }, message: "must have required property 'initialOpacity'" };
                    if (vErrors === null) {
                      vErrors = [err252];
                    } else {
                      vErrors.push(err252);
                    }
                    errors++;
                  }
                  if (data63.type === void 0) {
                    const err253 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                    if (vErrors === null) {
                      vErrors = [err253];
                    } else {
                      vErrors.push(err253);
                    }
                    errors++;
                  }
                  if (data63.box === void 0) {
                    const err254 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "box" }, message: "must have required property 'box'" };
                    if (vErrors === null) {
                      vErrors = [err254];
                    } else {
                      vErrors.push(err254);
                    }
                    errors++;
                  }
                  if (data63.assetRef === void 0) {
                    const err255 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "assetRef" }, message: "must have required property 'assetRef'" };
                    if (vErrors === null) {
                      vErrors = [err255];
                    } else {
                      vErrors.push(err255);
                    }
                    errors++;
                  }
                  if (data63.anchorId === void 0) {
                    const err256 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "anchorId" }, message: "must have required property 'anchorId'" };
                    if (vErrors === null) {
                      vErrors = [err256];
                    } else {
                      vErrors.push(err256);
                    }
                    errors++;
                  }
                  if (data63.fit === void 0) {
                    const err257 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "fit" }, message: "must have required property 'fit'" };
                    if (vErrors === null) {
                      vErrors = [err257];
                    } else {
                      vErrors.push(err257);
                    }
                    errors++;
                  }
                  if (data63.rotationDeg === void 0) {
                    const err258 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/required", keyword: "required", params: { missingProperty: "rotationDeg" }, message: "must have required property 'rotationDeg'" };
                    if (vErrors === null) {
                      vErrors = [err258];
                    } else {
                      vErrors.push(err258);
                    }
                    errors++;
                  }
                  for (const key17 in data63) {
                    if (!func1.call(schema31.properties.nodes.items.oneOf[1].properties, key17)) {
                      const err259 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key17 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err259];
                      } else {
                        vErrors.push(err259);
                      }
                      errors++;
                    }
                  }
                  if (data63.id !== void 0) {
                    let data79 = data63.id;
                    if (typeof data79 === "string") {
                      if (!pattern4.test(data79)) {
                        const err260 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/1/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err260];
                        } else {
                          vErrors.push(err260);
                        }
                        errors++;
                      }
                    } else {
                      const err261 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/1/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err261];
                      } else {
                        vErrors.push(err261);
                      }
                      errors++;
                    }
                  }
                  if (data63.typeVersion !== void 0) {
                    if ("0.1.0" !== data63.typeVersion) {
                      const err262 = { instancePath: instancePath + "/nodes/" + i3 + "/typeVersion", schemaPath: "#/properties/nodes/items/oneOf/1/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err262];
                      } else {
                        vErrors.push(err262);
                      }
                      errors++;
                    }
                  }
                  if (data63.zIndex !== void 0) {
                    let data81 = data63.zIndex;
                    if (!(typeof data81 == "number" && (!(data81 % 1) && !isNaN(data81)) && isFinite(data81))) {
                      const err263 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/1/properties/zIndex/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err263];
                      } else {
                        vErrors.push(err263);
                      }
                      errors++;
                    }
                    if (typeof data81 == "number" && isFinite(data81)) {
                      if (data81 > 100 || isNaN(data81)) {
                        const err264 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/1/properties/zIndex/maximum", keyword: "maximum", params: { comparison: "<=", limit: 100 }, message: "must be <= 100" };
                        if (vErrors === null) {
                          vErrors = [err264];
                        } else {
                          vErrors.push(err264);
                        }
                        errors++;
                      }
                      if (data81 < -100 || isNaN(data81)) {
                        const err265 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/1/properties/zIndex/minimum", keyword: "minimum", params: { comparison: ">=", limit: -100 }, message: "must be >= -100" };
                        if (vErrors === null) {
                          vErrors = [err265];
                        } else {
                          vErrors.push(err265);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data63.initialOpacity !== void 0) {
                    let data82 = data63.initialOpacity;
                    if (typeof data82 == "number" && isFinite(data82)) {
                      if (data82 > 1 || isNaN(data82)) {
                        const err266 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/1/properties/initialOpacity/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err266];
                        } else {
                          vErrors.push(err266);
                        }
                        errors++;
                      }
                      if (data82 < 0 || isNaN(data82)) {
                        const err267 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/1/properties/initialOpacity/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err267];
                        } else {
                          vErrors.push(err267);
                        }
                        errors++;
                      }
                    } else {
                      const err268 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/1/properties/initialOpacity/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err268];
                      } else {
                        vErrors.push(err268);
                      }
                      errors++;
                    }
                  }
                  if (data63.type !== void 0) {
                    if ("image" !== data63.type) {
                      const err269 = { instancePath: instancePath + "/nodes/" + i3 + "/type", schemaPath: "#/properties/nodes/items/oneOf/1/properties/type/const", keyword: "const", params: { allowedValue: "image" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err269];
                      } else {
                        vErrors.push(err269);
                      }
                      errors++;
                    }
                  }
                  if (data63.box !== void 0) {
                    let data84 = data63.box;
                    if (data84 && typeof data84 == "object" && !Array.isArray(data84)) {
                      if (data84.x === void 0) {
                        const err270 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "x" }, message: "must have required property 'x'" };
                        if (vErrors === null) {
                          vErrors = [err270];
                        } else {
                          vErrors.push(err270);
                        }
                        errors++;
                      }
                      if (data84.y === void 0) {
                        const err271 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "y" }, message: "must have required property 'y'" };
                        if (vErrors === null) {
                          vErrors = [err271];
                        } else {
                          vErrors.push(err271);
                        }
                        errors++;
                      }
                      if (data84.width === void 0) {
                        const err272 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "width" }, message: "must have required property 'width'" };
                        if (vErrors === null) {
                          vErrors = [err272];
                        } else {
                          vErrors.push(err272);
                        }
                        errors++;
                      }
                      if (data84.height === void 0) {
                        const err273 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "height" }, message: "must have required property 'height'" };
                        if (vErrors === null) {
                          vErrors = [err273];
                        } else {
                          vErrors.push(err273);
                        }
                        errors++;
                      }
                      for (const key18 in data84) {
                        if (!(key18 === "x" || key18 === "y" || key18 === "width" || key18 === "height")) {
                          const err274 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key18 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err274];
                          } else {
                            vErrors.push(err274);
                          }
                          errors++;
                        }
                      }
                      if (data84.x !== void 0) {
                        let data85 = data84.x;
                        if (typeof data85 == "number" && isFinite(data85)) {
                          if (data85 > 1e5 || isNaN(data85)) {
                            const err275 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                            if (vErrors === null) {
                              vErrors = [err275];
                            } else {
                              vErrors.push(err275);
                            }
                            errors++;
                          }
                          if (data85 < -1e5 || isNaN(data85)) {
                            const err276 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                            if (vErrors === null) {
                              vErrors = [err276];
                            } else {
                              vErrors.push(err276);
                            }
                            errors++;
                          }
                        } else {
                          const err277 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err277];
                          } else {
                            vErrors.push(err277);
                          }
                          errors++;
                        }
                      }
                      if (data84.y !== void 0) {
                        let data86 = data84.y;
                        if (typeof data86 == "number" && isFinite(data86)) {
                          if (data86 > 1e5 || isNaN(data86)) {
                            const err278 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                            if (vErrors === null) {
                              vErrors = [err278];
                            } else {
                              vErrors.push(err278);
                            }
                            errors++;
                          }
                          if (data86 < -1e5 || isNaN(data86)) {
                            const err279 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                            if (vErrors === null) {
                              vErrors = [err279];
                            } else {
                              vErrors.push(err279);
                            }
                            errors++;
                          }
                        } else {
                          const err280 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err280];
                          } else {
                            vErrors.push(err280);
                          }
                          errors++;
                        }
                      }
                      if (data84.width !== void 0) {
                        let data87 = data84.width;
                        if (typeof data87 == "number" && isFinite(data87)) {
                          if (data87 > 1e4 || isNaN(data87)) {
                            const err281 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                            if (vErrors === null) {
                              vErrors = [err281];
                            } else {
                              vErrors.push(err281);
                            }
                            errors++;
                          }
                          if (data87 < 1 || isNaN(data87)) {
                            const err282 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err282];
                            } else {
                              vErrors.push(err282);
                            }
                            errors++;
                          }
                        } else {
                          const err283 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err283];
                          } else {
                            vErrors.push(err283);
                          }
                          errors++;
                        }
                      }
                      if (data84.height !== void 0) {
                        let data88 = data84.height;
                        if (typeof data88 == "number" && isFinite(data88)) {
                          if (data88 > 1e4 || isNaN(data88)) {
                            const err284 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                            if (vErrors === null) {
                              vErrors = [err284];
                            } else {
                              vErrors.push(err284);
                            }
                            errors++;
                          }
                          if (data88 < 1 || isNaN(data88)) {
                            const err285 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                            if (vErrors === null) {
                              vErrors = [err285];
                            } else {
                              vErrors.push(err285);
                            }
                            errors++;
                          }
                        } else {
                          const err286 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err286];
                          } else {
                            vErrors.push(err286);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err287 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err287];
                      } else {
                        vErrors.push(err287);
                      }
                      errors++;
                    }
                  }
                  if (data63.assetRef !== void 0) {
                    let data89 = data63.assetRef;
                    if (data89 && typeof data89 == "object" && !Array.isArray(data89)) {
                      if (data89.id === void 0) {
                        const err288 = { instancePath: instancePath + "/nodes/" + i3 + "/assetRef", schemaPath: "#/$defs/versionRef/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                        if (vErrors === null) {
                          vErrors = [err288];
                        } else {
                          vErrors.push(err288);
                        }
                        errors++;
                      }
                      if (data89.version === void 0) {
                        const err289 = { instancePath: instancePath + "/nodes/" + i3 + "/assetRef", schemaPath: "#/$defs/versionRef/required", keyword: "required", params: { missingProperty: "version" }, message: "must have required property 'version'" };
                        if (vErrors === null) {
                          vErrors = [err289];
                        } else {
                          vErrors.push(err289);
                        }
                        errors++;
                      }
                      for (const key19 in data89) {
                        if (!(key19 === "id" || key19 === "version")) {
                          const err290 = { instancePath: instancePath + "/nodes/" + i3 + "/assetRef", schemaPath: "#/$defs/versionRef/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key19 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err290];
                          } else {
                            vErrors.push(err290);
                          }
                          errors++;
                        }
                      }
                      if (data89.id !== void 0) {
                        let data90 = data89.id;
                        if (typeof data90 === "string") {
                          if (!pattern4.test(data90)) {
                            const err291 = { instancePath: instancePath + "/nodes/" + i3 + "/assetRef/id", schemaPath: "#/$defs/versionRef/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                            if (vErrors === null) {
                              vErrors = [err291];
                            } else {
                              vErrors.push(err291);
                            }
                            errors++;
                          }
                        } else {
                          const err292 = { instancePath: instancePath + "/nodes/" + i3 + "/assetRef/id", schemaPath: "#/$defs/versionRef/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err292];
                          } else {
                            vErrors.push(err292);
                          }
                          errors++;
                        }
                      }
                      if (data89.version !== void 0) {
                        if ("0.1.0" !== data89.version) {
                          const err293 = { instancePath: instancePath + "/nodes/" + i3 + "/assetRef/version", schemaPath: "#/$defs/versionRef/properties/version/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err293];
                          } else {
                            vErrors.push(err293);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err294 = { instancePath: instancePath + "/nodes/" + i3 + "/assetRef", schemaPath: "#/$defs/versionRef/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err294];
                      } else {
                        vErrors.push(err294);
                      }
                      errors++;
                    }
                  }
                  if (data63.anchorId !== void 0) {
                    let data92 = data63.anchorId;
                    if (typeof data92 === "string") {
                      if (!pattern4.test(data92)) {
                        const err295 = { instancePath: instancePath + "/nodes/" + i3 + "/anchorId", schemaPath: "#/properties/nodes/items/oneOf/1/properties/anchorId/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err295];
                        } else {
                          vErrors.push(err295);
                        }
                        errors++;
                      }
                    } else {
                      const err296 = { instancePath: instancePath + "/nodes/" + i3 + "/anchorId", schemaPath: "#/properties/nodes/items/oneOf/1/properties/anchorId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err296];
                      } else {
                        vErrors.push(err296);
                      }
                      errors++;
                    }
                  }
                  if (data63.fit !== void 0) {
                    if ("contain" !== data63.fit) {
                      const err297 = { instancePath: instancePath + "/nodes/" + i3 + "/fit", schemaPath: "#/properties/nodes/items/oneOf/1/properties/fit/const", keyword: "const", params: { allowedValue: "contain" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err297];
                      } else {
                        vErrors.push(err297);
                      }
                      errors++;
                    }
                  }
                  if (data63.rotationDeg !== void 0) {
                    let data94 = data63.rotationDeg;
                    if (typeof data94 == "number" && isFinite(data94)) {
                      if (data94 > 180 || isNaN(data94)) {
                        const err298 = { instancePath: instancePath + "/nodes/" + i3 + "/rotationDeg", schemaPath: "#/properties/nodes/items/oneOf/1/properties/rotationDeg/maximum", keyword: "maximum", params: { comparison: "<=", limit: 180 }, message: "must be <= 180" };
                        if (vErrors === null) {
                          vErrors = [err298];
                        } else {
                          vErrors.push(err298);
                        }
                        errors++;
                      }
                      if (data94 < -180 || isNaN(data94)) {
                        const err299 = { instancePath: instancePath + "/nodes/" + i3 + "/rotationDeg", schemaPath: "#/properties/nodes/items/oneOf/1/properties/rotationDeg/minimum", keyword: "minimum", params: { comparison: ">=", limit: -180 }, message: "must be >= -180" };
                        if (vErrors === null) {
                          vErrors = [err299];
                        } else {
                          vErrors.push(err299);
                        }
                        errors++;
                      }
                    } else {
                      const err300 = { instancePath: instancePath + "/nodes/" + i3 + "/rotationDeg", schemaPath: "#/properties/nodes/items/oneOf/1/properties/rotationDeg/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err300];
                      } else {
                        vErrors.push(err300);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err301 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/1/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err301];
                  } else {
                    vErrors.push(err301);
                  }
                  errors++;
                }
                var _valid0 = _errs168 === errors;
                if (_valid0 && valid26) {
                  valid26 = false;
                  passing0 = [passing0, 1];
                } else {
                  if (_valid0) {
                    valid26 = true;
                    passing0 = 1;
                    if (props1 !== true) {
                      props1 = true;
                    }
                  }
                  const _errs203 = errors;
                  if (data63 && typeof data63 == "object" && !Array.isArray(data63)) {
                    if (data63.id === void 0) {
                      const err302 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                      if (vErrors === null) {
                        vErrors = [err302];
                      } else {
                        vErrors.push(err302);
                      }
                      errors++;
                    }
                    if (data63.typeVersion === void 0) {
                      const err303 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                      if (vErrors === null) {
                        vErrors = [err303];
                      } else {
                        vErrors.push(err303);
                      }
                      errors++;
                    }
                    if (data63.zIndex === void 0) {
                      const err304 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "zIndex" }, message: "must have required property 'zIndex'" };
                      if (vErrors === null) {
                        vErrors = [err304];
                      } else {
                        vErrors.push(err304);
                      }
                      errors++;
                    }
                    if (data63.initialOpacity === void 0) {
                      const err305 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "initialOpacity" }, message: "must have required property 'initialOpacity'" };
                      if (vErrors === null) {
                        vErrors = [err305];
                      } else {
                        vErrors.push(err305);
                      }
                      errors++;
                    }
                    if (data63.type === void 0) {
                      const err306 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                      if (vErrors === null) {
                        vErrors = [err306];
                      } else {
                        vErrors.push(err306);
                      }
                      errors++;
                    }
                    if (data63.pathId === void 0) {
                      const err307 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "pathId" }, message: "must have required property 'pathId'" };
                      if (vErrors === null) {
                        vErrors = [err307];
                      } else {
                        vErrors.push(err307);
                      }
                      errors++;
                    }
                    if (data63.initialProgress === void 0) {
                      const err308 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "initialProgress" }, message: "must have required property 'initialProgress'" };
                      if (vErrors === null) {
                        vErrors = [err308];
                      } else {
                        vErrors.push(err308);
                      }
                      errors++;
                    }
                    if (data63.colorRole === void 0) {
                      const err309 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "colorRole" }, message: "must have required property 'colorRole'" };
                      if (vErrors === null) {
                        vErrors = [err309];
                      } else {
                        vErrors.push(err309);
                      }
                      errors++;
                    }
                    if (data63.strokeWidth === void 0) {
                      const err310 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "strokeWidth" }, message: "must have required property 'strokeWidth'" };
                      if (vErrors === null) {
                        vErrors = [err310];
                      } else {
                        vErrors.push(err310);
                      }
                      errors++;
                    }
                    if (data63.dash === void 0) {
                      const err311 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/required", keyword: "required", params: { missingProperty: "dash" }, message: "must have required property 'dash'" };
                      if (vErrors === null) {
                        vErrors = [err311];
                      } else {
                        vErrors.push(err311);
                      }
                      errors++;
                    }
                    for (const key20 in data63) {
                      if (!func1.call(schema31.properties.nodes.items.oneOf[2].properties, key20)) {
                        const err312 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key20 }, message: "must NOT have additional properties" };
                        if (vErrors === null) {
                          vErrors = [err312];
                        } else {
                          vErrors.push(err312);
                        }
                        errors++;
                      }
                    }
                    if (data63.id !== void 0) {
                      let data95 = data63.id;
                      if (typeof data95 === "string") {
                        if (!pattern4.test(data95)) {
                          const err313 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/2/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                          if (vErrors === null) {
                            vErrors = [err313];
                          } else {
                            vErrors.push(err313);
                          }
                          errors++;
                        }
                      } else {
                        const err314 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/2/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                        if (vErrors === null) {
                          vErrors = [err314];
                        } else {
                          vErrors.push(err314);
                        }
                        errors++;
                      }
                    }
                    if (data63.typeVersion !== void 0) {
                      if ("0.1.0" !== data63.typeVersion) {
                        const err315 = { instancePath: instancePath + "/nodes/" + i3 + "/typeVersion", schemaPath: "#/properties/nodes/items/oneOf/2/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                        if (vErrors === null) {
                          vErrors = [err315];
                        } else {
                          vErrors.push(err315);
                        }
                        errors++;
                      }
                    }
                    if (data63.zIndex !== void 0) {
                      let data97 = data63.zIndex;
                      if (!(typeof data97 == "number" && (!(data97 % 1) && !isNaN(data97)) && isFinite(data97))) {
                        const err316 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/2/properties/zIndex/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                        if (vErrors === null) {
                          vErrors = [err316];
                        } else {
                          vErrors.push(err316);
                        }
                        errors++;
                      }
                      if (typeof data97 == "number" && isFinite(data97)) {
                        if (data97 > 100 || isNaN(data97)) {
                          const err317 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/2/properties/zIndex/maximum", keyword: "maximum", params: { comparison: "<=", limit: 100 }, message: "must be <= 100" };
                          if (vErrors === null) {
                            vErrors = [err317];
                          } else {
                            vErrors.push(err317);
                          }
                          errors++;
                        }
                        if (data97 < -100 || isNaN(data97)) {
                          const err318 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/2/properties/zIndex/minimum", keyword: "minimum", params: { comparison: ">=", limit: -100 }, message: "must be >= -100" };
                          if (vErrors === null) {
                            vErrors = [err318];
                          } else {
                            vErrors.push(err318);
                          }
                          errors++;
                        }
                      }
                    }
                    if (data63.initialOpacity !== void 0) {
                      let data98 = data63.initialOpacity;
                      if (typeof data98 == "number" && isFinite(data98)) {
                        if (data98 > 1 || isNaN(data98)) {
                          const err319 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/2/properties/initialOpacity/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                          if (vErrors === null) {
                            vErrors = [err319];
                          } else {
                            vErrors.push(err319);
                          }
                          errors++;
                        }
                        if (data98 < 0 || isNaN(data98)) {
                          const err320 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/2/properties/initialOpacity/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                          if (vErrors === null) {
                            vErrors = [err320];
                          } else {
                            vErrors.push(err320);
                          }
                          errors++;
                        }
                      } else {
                        const err321 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/2/properties/initialOpacity/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                        if (vErrors === null) {
                          vErrors = [err321];
                        } else {
                          vErrors.push(err321);
                        }
                        errors++;
                      }
                    }
                    if (data63.type !== void 0) {
                      if ("path" !== data63.type) {
                        const err322 = { instancePath: instancePath + "/nodes/" + i3 + "/type", schemaPath: "#/properties/nodes/items/oneOf/2/properties/type/const", keyword: "const", params: { allowedValue: "path" }, message: "must be equal to constant" };
                        if (vErrors === null) {
                          vErrors = [err322];
                        } else {
                          vErrors.push(err322);
                        }
                        errors++;
                      }
                    }
                    if (data63.pathId !== void 0) {
                      let data100 = data63.pathId;
                      if (typeof data100 === "string") {
                        if (!pattern4.test(data100)) {
                          const err323 = { instancePath: instancePath + "/nodes/" + i3 + "/pathId", schemaPath: "#/properties/nodes/items/oneOf/2/properties/pathId/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                          if (vErrors === null) {
                            vErrors = [err323];
                          } else {
                            vErrors.push(err323);
                          }
                          errors++;
                        }
                      } else {
                        const err324 = { instancePath: instancePath + "/nodes/" + i3 + "/pathId", schemaPath: "#/properties/nodes/items/oneOf/2/properties/pathId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                        if (vErrors === null) {
                          vErrors = [err324];
                        } else {
                          vErrors.push(err324);
                        }
                        errors++;
                      }
                    }
                    if (data63.initialProgress !== void 0) {
                      let data101 = data63.initialProgress;
                      if (typeof data101 == "number" && isFinite(data101)) {
                        if (data101 > 1 || isNaN(data101)) {
                          const err325 = { instancePath: instancePath + "/nodes/" + i3 + "/initialProgress", schemaPath: "#/properties/nodes/items/oneOf/2/properties/initialProgress/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                          if (vErrors === null) {
                            vErrors = [err325];
                          } else {
                            vErrors.push(err325);
                          }
                          errors++;
                        }
                        if (data101 < 0 || isNaN(data101)) {
                          const err326 = { instancePath: instancePath + "/nodes/" + i3 + "/initialProgress", schemaPath: "#/properties/nodes/items/oneOf/2/properties/initialProgress/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                          if (vErrors === null) {
                            vErrors = [err326];
                          } else {
                            vErrors.push(err326);
                          }
                          errors++;
                        }
                      } else {
                        const err327 = { instancePath: instancePath + "/nodes/" + i3 + "/initialProgress", schemaPath: "#/properties/nodes/items/oneOf/2/properties/initialProgress/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                        if (vErrors === null) {
                          vErrors = [err327];
                        } else {
                          vErrors.push(err327);
                        }
                        errors++;
                      }
                    }
                    if (data63.colorRole !== void 0) {
                      let data102 = data63.colorRole;
                      if (!(data102 === "path" || data102 === "accent")) {
                        const err328 = { instancePath: instancePath + "/nodes/" + i3 + "/colorRole", schemaPath: "#/properties/nodes/items/oneOf/2/properties/colorRole/enum", keyword: "enum", params: { allowedValues: schema31.properties.nodes.items.oneOf[2].properties.colorRole.enum }, message: "must be equal to one of the allowed values" };
                        if (vErrors === null) {
                          vErrors = [err328];
                        } else {
                          vErrors.push(err328);
                        }
                        errors++;
                      }
                    }
                    if (data63.strokeWidth !== void 0) {
                      let data103 = data63.strokeWidth;
                      if (typeof data103 == "number" && isFinite(data103)) {
                        if (data103 > 20 || isNaN(data103)) {
                          const err329 = { instancePath: instancePath + "/nodes/" + i3 + "/strokeWidth", schemaPath: "#/properties/nodes/items/oneOf/2/properties/strokeWidth/maximum", keyword: "maximum", params: { comparison: "<=", limit: 20 }, message: "must be <= 20" };
                          if (vErrors === null) {
                            vErrors = [err329];
                          } else {
                            vErrors.push(err329);
                          }
                          errors++;
                        }
                        if (data103 < 0.1 || isNaN(data103)) {
                          const err330 = { instancePath: instancePath + "/nodes/" + i3 + "/strokeWidth", schemaPath: "#/properties/nodes/items/oneOf/2/properties/strokeWidth/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0.1 }, message: "must be >= 0.1" };
                          if (vErrors === null) {
                            vErrors = [err330];
                          } else {
                            vErrors.push(err330);
                          }
                          errors++;
                        }
                      } else {
                        const err331 = { instancePath: instancePath + "/nodes/" + i3 + "/strokeWidth", schemaPath: "#/properties/nodes/items/oneOf/2/properties/strokeWidth/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                        if (vErrors === null) {
                          vErrors = [err331];
                        } else {
                          vErrors.push(err331);
                        }
                        errors++;
                      }
                    }
                    if (data63.dash !== void 0) {
                      let data104 = data63.dash;
                      if (Array.isArray(data104)) {
                        if (data104.length > 10) {
                          const err332 = { instancePath: instancePath + "/nodes/" + i3 + "/dash", schemaPath: "#/properties/nodes/items/oneOf/2/properties/dash/maxItems", keyword: "maxItems", params: { limit: 10 }, message: "must NOT have more than 10 items" };
                          if (vErrors === null) {
                            vErrors = [err332];
                          } else {
                            vErrors.push(err332);
                          }
                          errors++;
                        }
                        if (data104.length < 0) {
                          const err333 = { instancePath: instancePath + "/nodes/" + i3 + "/dash", schemaPath: "#/properties/nodes/items/oneOf/2/properties/dash/minItems", keyword: "minItems", params: { limit: 0 }, message: "must NOT have fewer than 0 items" };
                          if (vErrors === null) {
                            vErrors = [err333];
                          } else {
                            vErrors.push(err333);
                          }
                          errors++;
                        }
                        const len4 = data104.length;
                        for (let i4 = 0; i4 < len4; i4++) {
                          let data105 = data104[i4];
                          if (typeof data105 == "number" && isFinite(data105)) {
                            if (data105 > 100 || isNaN(data105)) {
                              const err334 = { instancePath: instancePath + "/nodes/" + i3 + "/dash/" + i4, schemaPath: "#/properties/nodes/items/oneOf/2/properties/dash/items/maximum", keyword: "maximum", params: { comparison: "<=", limit: 100 }, message: "must be <= 100" };
                              if (vErrors === null) {
                                vErrors = [err334];
                              } else {
                                vErrors.push(err334);
                              }
                              errors++;
                            }
                            if (data105 < 0 || isNaN(data105)) {
                              const err335 = { instancePath: instancePath + "/nodes/" + i3 + "/dash/" + i4, schemaPath: "#/properties/nodes/items/oneOf/2/properties/dash/items/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                              if (vErrors === null) {
                                vErrors = [err335];
                              } else {
                                vErrors.push(err335);
                              }
                              errors++;
                            }
                          } else {
                            const err336 = { instancePath: instancePath + "/nodes/" + i3 + "/dash/" + i4, schemaPath: "#/properties/nodes/items/oneOf/2/properties/dash/items/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                            if (vErrors === null) {
                              vErrors = [err336];
                            } else {
                              vErrors.push(err336);
                            }
                            errors++;
                          }
                        }
                      } else {
                        const err337 = { instancePath: instancePath + "/nodes/" + i3 + "/dash", schemaPath: "#/properties/nodes/items/oneOf/2/properties/dash/type", keyword: "type", params: { type: "array" }, message: "must be array" };
                        if (vErrors === null) {
                          vErrors = [err337];
                        } else {
                          vErrors.push(err337);
                        }
                        errors++;
                      }
                    }
                  } else {
                    const err338 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/2/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                    if (vErrors === null) {
                      vErrors = [err338];
                    } else {
                      vErrors.push(err338);
                    }
                    errors++;
                  }
                  var _valid0 = _errs203 === errors;
                  if (_valid0 && valid26) {
                    valid26 = false;
                    passing0 = [passing0, 2];
                  } else {
                    if (_valid0) {
                      valid26 = true;
                      passing0 = 2;
                      if (props1 !== true) {
                        props1 = true;
                      }
                    }
                    const _errs225 = errors;
                    if (data63 && typeof data63 == "object" && !Array.isArray(data63)) {
                      if (data63.id === void 0) {
                        const err339 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                        if (vErrors === null) {
                          vErrors = [err339];
                        } else {
                          vErrors.push(err339);
                        }
                        errors++;
                      }
                      if (data63.typeVersion === void 0) {
                        const err340 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                        if (vErrors === null) {
                          vErrors = [err340];
                        } else {
                          vErrors.push(err340);
                        }
                        errors++;
                      }
                      if (data63.zIndex === void 0) {
                        const err341 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "zIndex" }, message: "must have required property 'zIndex'" };
                        if (vErrors === null) {
                          vErrors = [err341];
                        } else {
                          vErrors.push(err341);
                        }
                        errors++;
                      }
                      if (data63.initialOpacity === void 0) {
                        const err342 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "initialOpacity" }, message: "must have required property 'initialOpacity'" };
                        if (vErrors === null) {
                          vErrors = [err342];
                        } else {
                          vErrors.push(err342);
                        }
                        errors++;
                      }
                      if (data63.type === void 0) {
                        const err343 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                        if (vErrors === null) {
                          vErrors = [err343];
                        } else {
                          vErrors.push(err343);
                        }
                        errors++;
                      }
                      if (data63.box === void 0) {
                        const err344 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "box" }, message: "must have required property 'box'" };
                        if (vErrors === null) {
                          vErrors = [err344];
                        } else {
                          vErrors.push(err344);
                        }
                        errors++;
                      }
                      if (data63.colorRole === void 0) {
                        const err345 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "colorRole" }, message: "must have required property 'colorRole'" };
                        if (vErrors === null) {
                          vErrors = [err345];
                        } else {
                          vErrors.push(err345);
                        }
                        errors++;
                      }
                      if (data63.strokeWidth === void 0) {
                        const err346 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "strokeWidth" }, message: "must have required property 'strokeWidth'" };
                        if (vErrors === null) {
                          vErrors = [err346];
                        } else {
                          vErrors.push(err346);
                        }
                        errors++;
                      }
                      if (data63.innerRatio === void 0) {
                        const err347 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/required", keyword: "required", params: { missingProperty: "innerRatio" }, message: "must have required property 'innerRatio'" };
                        if (vErrors === null) {
                          vErrors = [err347];
                        } else {
                          vErrors.push(err347);
                        }
                        errors++;
                      }
                      for (const key21 in data63) {
                        if (!func1.call(schema31.properties.nodes.items.oneOf[3].properties, key21)) {
                          const err348 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key21 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err348];
                          } else {
                            vErrors.push(err348);
                          }
                          errors++;
                        }
                      }
                      if (data63.id !== void 0) {
                        let data106 = data63.id;
                        if (typeof data106 === "string") {
                          if (!pattern4.test(data106)) {
                            const err349 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/3/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                            if (vErrors === null) {
                              vErrors = [err349];
                            } else {
                              vErrors.push(err349);
                            }
                            errors++;
                          }
                        } else {
                          const err350 = { instancePath: instancePath + "/nodes/" + i3 + "/id", schemaPath: "#/properties/nodes/items/oneOf/3/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err350];
                          } else {
                            vErrors.push(err350);
                          }
                          errors++;
                        }
                      }
                      if (data63.typeVersion !== void 0) {
                        if ("0.1.0" !== data63.typeVersion) {
                          const err351 = { instancePath: instancePath + "/nodes/" + i3 + "/typeVersion", schemaPath: "#/properties/nodes/items/oneOf/3/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err351];
                          } else {
                            vErrors.push(err351);
                          }
                          errors++;
                        }
                      }
                      if (data63.zIndex !== void 0) {
                        let data108 = data63.zIndex;
                        if (!(typeof data108 == "number" && (!(data108 % 1) && !isNaN(data108)) && isFinite(data108))) {
                          const err352 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/3/properties/zIndex/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                          if (vErrors === null) {
                            vErrors = [err352];
                          } else {
                            vErrors.push(err352);
                          }
                          errors++;
                        }
                        if (typeof data108 == "number" && isFinite(data108)) {
                          if (data108 > 100 || isNaN(data108)) {
                            const err353 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/3/properties/zIndex/maximum", keyword: "maximum", params: { comparison: "<=", limit: 100 }, message: "must be <= 100" };
                            if (vErrors === null) {
                              vErrors = [err353];
                            } else {
                              vErrors.push(err353);
                            }
                            errors++;
                          }
                          if (data108 < -100 || isNaN(data108)) {
                            const err354 = { instancePath: instancePath + "/nodes/" + i3 + "/zIndex", schemaPath: "#/properties/nodes/items/oneOf/3/properties/zIndex/minimum", keyword: "minimum", params: { comparison: ">=", limit: -100 }, message: "must be >= -100" };
                            if (vErrors === null) {
                              vErrors = [err354];
                            } else {
                              vErrors.push(err354);
                            }
                            errors++;
                          }
                        }
                      }
                      if (data63.initialOpacity !== void 0) {
                        let data109 = data63.initialOpacity;
                        if (typeof data109 == "number" && isFinite(data109)) {
                          if (data109 > 1 || isNaN(data109)) {
                            const err355 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/3/properties/initialOpacity/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                            if (vErrors === null) {
                              vErrors = [err355];
                            } else {
                              vErrors.push(err355);
                            }
                            errors++;
                          }
                          if (data109 < 0 || isNaN(data109)) {
                            const err356 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/3/properties/initialOpacity/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                            if (vErrors === null) {
                              vErrors = [err356];
                            } else {
                              vErrors.push(err356);
                            }
                            errors++;
                          }
                        } else {
                          const err357 = { instancePath: instancePath + "/nodes/" + i3 + "/initialOpacity", schemaPath: "#/properties/nodes/items/oneOf/3/properties/initialOpacity/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err357];
                          } else {
                            vErrors.push(err357);
                          }
                          errors++;
                        }
                      }
                      if (data63.type !== void 0) {
                        if ("ring" !== data63.type) {
                          const err358 = { instancePath: instancePath + "/nodes/" + i3 + "/type", schemaPath: "#/properties/nodes/items/oneOf/3/properties/type/const", keyword: "const", params: { allowedValue: "ring" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err358];
                          } else {
                            vErrors.push(err358);
                          }
                          errors++;
                        }
                      }
                      if (data63.box !== void 0) {
                        let data111 = data63.box;
                        if (data111 && typeof data111 == "object" && !Array.isArray(data111)) {
                          if (data111.x === void 0) {
                            const err359 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "x" }, message: "must have required property 'x'" };
                            if (vErrors === null) {
                              vErrors = [err359];
                            } else {
                              vErrors.push(err359);
                            }
                            errors++;
                          }
                          if (data111.y === void 0) {
                            const err360 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "y" }, message: "must have required property 'y'" };
                            if (vErrors === null) {
                              vErrors = [err360];
                            } else {
                              vErrors.push(err360);
                            }
                            errors++;
                          }
                          if (data111.width === void 0) {
                            const err361 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "width" }, message: "must have required property 'width'" };
                            if (vErrors === null) {
                              vErrors = [err361];
                            } else {
                              vErrors.push(err361);
                            }
                            errors++;
                          }
                          if (data111.height === void 0) {
                            const err362 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/required", keyword: "required", params: { missingProperty: "height" }, message: "must have required property 'height'" };
                            if (vErrors === null) {
                              vErrors = [err362];
                            } else {
                              vErrors.push(err362);
                            }
                            errors++;
                          }
                          for (const key22 in data111) {
                            if (!(key22 === "x" || key22 === "y" || key22 === "width" || key22 === "height")) {
                              const err363 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key22 }, message: "must NOT have additional properties" };
                              if (vErrors === null) {
                                vErrors = [err363];
                              } else {
                                vErrors.push(err363);
                              }
                              errors++;
                            }
                          }
                          if (data111.x !== void 0) {
                            let data112 = data111.x;
                            if (typeof data112 == "number" && isFinite(data112)) {
                              if (data112 > 1e5 || isNaN(data112)) {
                                const err364 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                                if (vErrors === null) {
                                  vErrors = [err364];
                                } else {
                                  vErrors.push(err364);
                                }
                                errors++;
                              }
                              if (data112 < -1e5 || isNaN(data112)) {
                                const err365 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                                if (vErrors === null) {
                                  vErrors = [err365];
                                } else {
                                  vErrors.push(err365);
                                }
                                errors++;
                              }
                            } else {
                              const err366 = { instancePath: instancePath + "/nodes/" + i3 + "/box/x", schemaPath: "#/$defs/rect/properties/x/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err366];
                              } else {
                                vErrors.push(err366);
                              }
                              errors++;
                            }
                          }
                          if (data111.y !== void 0) {
                            let data113 = data111.y;
                            if (typeof data113 == "number" && isFinite(data113)) {
                              if (data113 > 1e5 || isNaN(data113)) {
                                const err367 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e5 }, message: "must be <= 100000" };
                                if (vErrors === null) {
                                  vErrors = [err367];
                                } else {
                                  vErrors.push(err367);
                                }
                                errors++;
                              }
                              if (data113 < -1e5 || isNaN(data113)) {
                                const err368 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/minimum", keyword: "minimum", params: { comparison: ">=", limit: -1e5 }, message: "must be >= -100000" };
                                if (vErrors === null) {
                                  vErrors = [err368];
                                } else {
                                  vErrors.push(err368);
                                }
                                errors++;
                              }
                            } else {
                              const err369 = { instancePath: instancePath + "/nodes/" + i3 + "/box/y", schemaPath: "#/$defs/rect/properties/y/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err369];
                              } else {
                                vErrors.push(err369);
                              }
                              errors++;
                            }
                          }
                          if (data111.width !== void 0) {
                            let data114 = data111.width;
                            if (typeof data114 == "number" && isFinite(data114)) {
                              if (data114 > 1e4 || isNaN(data114)) {
                                const err370 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                                if (vErrors === null) {
                                  vErrors = [err370];
                                } else {
                                  vErrors.push(err370);
                                }
                                errors++;
                              }
                              if (data114 < 1 || isNaN(data114)) {
                                const err371 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                                if (vErrors === null) {
                                  vErrors = [err371];
                                } else {
                                  vErrors.push(err371);
                                }
                                errors++;
                              }
                            } else {
                              const err372 = { instancePath: instancePath + "/nodes/" + i3 + "/box/width", schemaPath: "#/$defs/rect/properties/width/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err372];
                              } else {
                                vErrors.push(err372);
                              }
                              errors++;
                            }
                          }
                          if (data111.height !== void 0) {
                            let data115 = data111.height;
                            if (typeof data115 == "number" && isFinite(data115)) {
                              if (data115 > 1e4 || isNaN(data115)) {
                                const err373 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1e4 }, message: "must be <= 10000" };
                                if (vErrors === null) {
                                  vErrors = [err373];
                                } else {
                                  vErrors.push(err373);
                                }
                                errors++;
                              }
                              if (data115 < 1 || isNaN(data115)) {
                                const err374 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                                if (vErrors === null) {
                                  vErrors = [err374];
                                } else {
                                  vErrors.push(err374);
                                }
                                errors++;
                              }
                            } else {
                              const err375 = { instancePath: instancePath + "/nodes/" + i3 + "/box/height", schemaPath: "#/$defs/rect/properties/height/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err375];
                              } else {
                                vErrors.push(err375);
                              }
                              errors++;
                            }
                          }
                        } else {
                          const err376 = { instancePath: instancePath + "/nodes/" + i3 + "/box", schemaPath: "#/$defs/rect/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                          if (vErrors === null) {
                            vErrors = [err376];
                          } else {
                            vErrors.push(err376);
                          }
                          errors++;
                        }
                      }
                      if (data63.colorRole !== void 0) {
                        let data116 = data63.colorRole;
                        if (!(data116 === "accent" || data116 === "path")) {
                          const err377 = { instancePath: instancePath + "/nodes/" + i3 + "/colorRole", schemaPath: "#/properties/nodes/items/oneOf/3/properties/colorRole/enum", keyword: "enum", params: { allowedValues: schema31.properties.nodes.items.oneOf[3].properties.colorRole.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err377];
                          } else {
                            vErrors.push(err377);
                          }
                          errors++;
                        }
                      }
                      if (data63.strokeWidth !== void 0) {
                        let data117 = data63.strokeWidth;
                        if (typeof data117 == "number" && isFinite(data117)) {
                          if (data117 > 20 || isNaN(data117)) {
                            const err378 = { instancePath: instancePath + "/nodes/" + i3 + "/strokeWidth", schemaPath: "#/properties/nodes/items/oneOf/3/properties/strokeWidth/maximum", keyword: "maximum", params: { comparison: "<=", limit: 20 }, message: "must be <= 20" };
                            if (vErrors === null) {
                              vErrors = [err378];
                            } else {
                              vErrors.push(err378);
                            }
                            errors++;
                          }
                          if (data117 < 0.1 || isNaN(data117)) {
                            const err379 = { instancePath: instancePath + "/nodes/" + i3 + "/strokeWidth", schemaPath: "#/properties/nodes/items/oneOf/3/properties/strokeWidth/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0.1 }, message: "must be >= 0.1" };
                            if (vErrors === null) {
                              vErrors = [err379];
                            } else {
                              vErrors.push(err379);
                            }
                            errors++;
                          }
                        } else {
                          const err380 = { instancePath: instancePath + "/nodes/" + i3 + "/strokeWidth", schemaPath: "#/properties/nodes/items/oneOf/3/properties/strokeWidth/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err380];
                          } else {
                            vErrors.push(err380);
                          }
                          errors++;
                        }
                      }
                      if (data63.innerRatio !== void 0) {
                        let data118 = data63.innerRatio;
                        if (typeof data118 == "number" && isFinite(data118)) {
                          if (data118 > 0.9 || isNaN(data118)) {
                            const err381 = { instancePath: instancePath + "/nodes/" + i3 + "/innerRatio", schemaPath: "#/properties/nodes/items/oneOf/3/properties/innerRatio/maximum", keyword: "maximum", params: { comparison: "<=", limit: 0.9 }, message: "must be <= 0.9" };
                            if (vErrors === null) {
                              vErrors = [err381];
                            } else {
                              vErrors.push(err381);
                            }
                            errors++;
                          }
                          if (data118 < 0 || isNaN(data118)) {
                            const err382 = { instancePath: instancePath + "/nodes/" + i3 + "/innerRatio", schemaPath: "#/properties/nodes/items/oneOf/3/properties/innerRatio/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                            if (vErrors === null) {
                              vErrors = [err382];
                            } else {
                              vErrors.push(err382);
                            }
                            errors++;
                          }
                        } else {
                          const err383 = { instancePath: instancePath + "/nodes/" + i3 + "/innerRatio", schemaPath: "#/properties/nodes/items/oneOf/3/properties/innerRatio/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                          if (vErrors === null) {
                            vErrors = [err383];
                          } else {
                            vErrors.push(err383);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err384 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf/3/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err384];
                      } else {
                        vErrors.push(err384);
                      }
                      errors++;
                    }
                    var _valid0 = _errs225 === errors;
                    if (_valid0 && valid26) {
                      valid26 = false;
                      passing0 = [passing0, 3];
                    } else {
                      if (_valid0) {
                        valid26 = true;
                        passing0 = 3;
                        if (props1 !== true) {
                          props1 = true;
                        }
                      }
                    }
                  }
                }
                if (!valid26) {
                  const err385 = { instancePath: instancePath + "/nodes/" + i3, schemaPath: "#/properties/nodes/items/oneOf", keyword: "oneOf", params: { passingSchemas: passing0 }, message: "must match exactly one schema in oneOf" };
                  if (vErrors === null) {
                    vErrors = [err385];
                  } else {
                    vErrors.push(err385);
                  }
                  errors++;
                } else {
                  errors = _errs131;
                  if (vErrors !== null) {
                    if (_errs131) {
                      vErrors.length = _errs131;
                    } else {
                      vErrors = null;
                    }
                  }
                }
              }
            } else {
              const err386 = { instancePath: instancePath + "/nodes", schemaPath: "#/properties/nodes/type", keyword: "type", params: { type: "array" }, message: "must be array" };
              if (vErrors === null) {
                vErrors = [err386];
              } else {
                vErrors.push(err386);
              }
              errors++;
            }
          }
          if (data.beats !== void 0) {
            let data119 = data.beats;
            if (Array.isArray(data119)) {
              if (data119.length > 40) {
                const err387 = { instancePath: instancePath + "/beats", schemaPath: "#/properties/beats/maxItems", keyword: "maxItems", params: { limit: 40 }, message: "must NOT have more than 40 items" };
                if (vErrors === null) {
                  vErrors = [err387];
                } else {
                  vErrors.push(err387);
                }
                errors++;
              }
              if (data119.length < 1) {
                const err388 = { instancePath: instancePath + "/beats", schemaPath: "#/properties/beats/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                if (vErrors === null) {
                  vErrors = [err388];
                } else {
                  vErrors.push(err388);
                }
                errors++;
              }
              const len5 = data119.length;
              for (let i5 = 0; i5 < len5; i5++) {
                let data120 = data119[i5];
                if (data120 && typeof data120 == "object" && !Array.isArray(data120)) {
                  if (data120.id === void 0) {
                    const err389 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err389];
                    } else {
                      vErrors.push(err389);
                    }
                    errors++;
                  }
                  if (data120.startMs === void 0) {
                    const err390 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/required", keyword: "required", params: { missingProperty: "startMs" }, message: "must have required property 'startMs'" };
                    if (vErrors === null) {
                      vErrors = [err390];
                    } else {
                      vErrors.push(err390);
                    }
                    errors++;
                  }
                  if (data120.endMs === void 0) {
                    const err391 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/required", keyword: "required", params: { missingProperty: "endMs" }, message: "must have required property 'endMs'" };
                    if (vErrors === null) {
                      vErrors = [err391];
                    } else {
                      vErrors.push(err391);
                    }
                    errors++;
                  }
                  if (data120.text === void 0) {
                    const err392 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/required", keyword: "required", params: { missingProperty: "text" }, message: "must have required property 'text'" };
                    if (vErrors === null) {
                      vErrors = [err392];
                    } else {
                      vErrors.push(err392);
                    }
                    errors++;
                  }
                  if (data120.screenText === void 0) {
                    const err393 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/required", keyword: "required", params: { missingProperty: "screenText" }, message: "must have required property 'screenText'" };
                    if (vErrors === null) {
                      vErrors = [err393];
                    } else {
                      vErrors.push(err393);
                    }
                    errors++;
                  }
                  if (data120.targetIds === void 0) {
                    const err394 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/required", keyword: "required", params: { missingProperty: "targetIds" }, message: "must have required property 'targetIds'" };
                    if (vErrors === null) {
                      vErrors = [err394];
                    } else {
                      vErrors.push(err394);
                    }
                    errors++;
                  }
                  for (const key23 in data120) {
                    if (!(key23 === "id" || key23 === "startMs" || key23 === "endMs" || key23 === "text" || key23 === "screenText" || key23 === "targetIds")) {
                      const err395 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key23 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err395];
                      } else {
                        vErrors.push(err395);
                      }
                      errors++;
                    }
                  }
                  if (data120.id !== void 0) {
                    let data121 = data120.id;
                    if (typeof data121 === "string") {
                      if (!pattern4.test(data121)) {
                        const err396 = { instancePath: instancePath + "/beats/" + i5 + "/id", schemaPath: "#/properties/beats/items/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err396];
                        } else {
                          vErrors.push(err396);
                        }
                        errors++;
                      }
                    } else {
                      const err397 = { instancePath: instancePath + "/beats/" + i5 + "/id", schemaPath: "#/properties/beats/items/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err397];
                      } else {
                        vErrors.push(err397);
                      }
                      errors++;
                    }
                  }
                  if (data120.startMs !== void 0) {
                    let data122 = data120.startMs;
                    if (!(typeof data122 == "number" && (!(data122 % 1) && !isNaN(data122)) && isFinite(data122))) {
                      const err398 = { instancePath: instancePath + "/beats/" + i5 + "/startMs", schemaPath: "#/properties/beats/items/properties/startMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err398];
                      } else {
                        vErrors.push(err398);
                      }
                      errors++;
                    }
                    if (typeof data122 == "number" && isFinite(data122)) {
                      if (data122 > 6e5 || isNaN(data122)) {
                        const err399 = { instancePath: instancePath + "/beats/" + i5 + "/startMs", schemaPath: "#/properties/beats/items/properties/startMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                        if (vErrors === null) {
                          vErrors = [err399];
                        } else {
                          vErrors.push(err399);
                        }
                        errors++;
                      }
                      if (data122 < 0 || isNaN(data122)) {
                        const err400 = { instancePath: instancePath + "/beats/" + i5 + "/startMs", schemaPath: "#/properties/beats/items/properties/startMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err400];
                        } else {
                          vErrors.push(err400);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data120.endMs !== void 0) {
                    let data123 = data120.endMs;
                    if (!(typeof data123 == "number" && (!(data123 % 1) && !isNaN(data123)) && isFinite(data123))) {
                      const err401 = { instancePath: instancePath + "/beats/" + i5 + "/endMs", schemaPath: "#/properties/beats/items/properties/endMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err401];
                      } else {
                        vErrors.push(err401);
                      }
                      errors++;
                    }
                    if (typeof data123 == "number" && isFinite(data123)) {
                      if (data123 > 6e5 || isNaN(data123)) {
                        const err402 = { instancePath: instancePath + "/beats/" + i5 + "/endMs", schemaPath: "#/properties/beats/items/properties/endMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                        if (vErrors === null) {
                          vErrors = [err402];
                        } else {
                          vErrors.push(err402);
                        }
                        errors++;
                      }
                      if (data123 < 0 || isNaN(data123)) {
                        const err403 = { instancePath: instancePath + "/beats/" + i5 + "/endMs", schemaPath: "#/properties/beats/items/properties/endMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err403];
                        } else {
                          vErrors.push(err403);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data120.text !== void 0) {
                    let data124 = data120.text;
                    if (typeof data124 === "string") {
                      if (func2(data124) > 2e3) {
                        const err404 = { instancePath: instancePath + "/beats/" + i5 + "/text", schemaPath: "#/properties/beats/items/properties/text/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
                        if (vErrors === null) {
                          vErrors = [err404];
                        } else {
                          vErrors.push(err404);
                        }
                        errors++;
                      }
                      if (func2(data124) < 1) {
                        const err405 = { instancePath: instancePath + "/beats/" + i5 + "/text", schemaPath: "#/properties/beats/items/properties/text/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                        if (vErrors === null) {
                          vErrors = [err405];
                        } else {
                          vErrors.push(err405);
                        }
                        errors++;
                      }
                    } else {
                      const err406 = { instancePath: instancePath + "/beats/" + i5 + "/text", schemaPath: "#/properties/beats/items/properties/text/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err406];
                      } else {
                        vErrors.push(err406);
                      }
                      errors++;
                    }
                  }
                  if (data120.screenText !== void 0) {
                    let data125 = data120.screenText;
                    if (typeof data125 === "string") {
                      if (func2(data125) > 2e3) {
                        const err407 = { instancePath: instancePath + "/beats/" + i5 + "/screenText", schemaPath: "#/properties/beats/items/properties/screenText/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
                        if (vErrors === null) {
                          vErrors = [err407];
                        } else {
                          vErrors.push(err407);
                        }
                        errors++;
                      }
                      if (func2(data125) < 1) {
                        const err408 = { instancePath: instancePath + "/beats/" + i5 + "/screenText", schemaPath: "#/properties/beats/items/properties/screenText/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                        if (vErrors === null) {
                          vErrors = [err408];
                        } else {
                          vErrors.push(err408);
                        }
                        errors++;
                      }
                    } else {
                      const err409 = { instancePath: instancePath + "/beats/" + i5 + "/screenText", schemaPath: "#/properties/beats/items/properties/screenText/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err409];
                      } else {
                        vErrors.push(err409);
                      }
                      errors++;
                    }
                  }
                  if (data120.targetIds !== void 0) {
                    let data126 = data120.targetIds;
                    if (Array.isArray(data126)) {
                      if (data126.length > 30) {
                        const err410 = { instancePath: instancePath + "/beats/" + i5 + "/targetIds", schemaPath: "#/properties/beats/items/properties/targetIds/maxItems", keyword: "maxItems", params: { limit: 30 }, message: "must NOT have more than 30 items" };
                        if (vErrors === null) {
                          vErrors = [err410];
                        } else {
                          vErrors.push(err410);
                        }
                        errors++;
                      }
                      if (data126.length < 1) {
                        const err411 = { instancePath: instancePath + "/beats/" + i5 + "/targetIds", schemaPath: "#/properties/beats/items/properties/targetIds/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                        if (vErrors === null) {
                          vErrors = [err411];
                        } else {
                          vErrors.push(err411);
                        }
                        errors++;
                      }
                      const len6 = data126.length;
                      for (let i6 = 0; i6 < len6; i6++) {
                        let data127 = data126[i6];
                        if (typeof data127 === "string") {
                          if (!pattern4.test(data127)) {
                            const err412 = { instancePath: instancePath + "/beats/" + i5 + "/targetIds/" + i6, schemaPath: "#/properties/beats/items/properties/targetIds/items/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                            if (vErrors === null) {
                              vErrors = [err412];
                            } else {
                              vErrors.push(err412);
                            }
                            errors++;
                          }
                        } else {
                          const err413 = { instancePath: instancePath + "/beats/" + i5 + "/targetIds/" + i6, schemaPath: "#/properties/beats/items/properties/targetIds/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err413];
                          } else {
                            vErrors.push(err413);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err414 = { instancePath: instancePath + "/beats/" + i5 + "/targetIds", schemaPath: "#/properties/beats/items/properties/targetIds/type", keyword: "type", params: { type: "array" }, message: "must be array" };
                      if (vErrors === null) {
                        vErrors = [err414];
                      } else {
                        vErrors.push(err414);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err415 = { instancePath: instancePath + "/beats/" + i5, schemaPath: "#/properties/beats/items/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err415];
                  } else {
                    vErrors.push(err415);
                  }
                  errors++;
                }
              }
            } else {
              const err416 = { instancePath: instancePath + "/beats", schemaPath: "#/properties/beats/type", keyword: "type", params: { type: "array" }, message: "must be array" };
              if (vErrors === null) {
                vErrors = [err416];
              } else {
                vErrors.push(err416);
              }
              errors++;
            }
          }
          if (data.actions !== void 0) {
            let data128 = data.actions;
            if (Array.isArray(data128)) {
              if (data128.length > 160) {
                const err417 = { instancePath: instancePath + "/actions", schemaPath: "#/properties/actions/maxItems", keyword: "maxItems", params: { limit: 160 }, message: "must NOT have more than 160 items" };
                if (vErrors === null) {
                  vErrors = [err417];
                } else {
                  vErrors.push(err417);
                }
                errors++;
              }
              if (data128.length < 0) {
                const err418 = { instancePath: instancePath + "/actions", schemaPath: "#/properties/actions/minItems", keyword: "minItems", params: { limit: 0 }, message: "must NOT have fewer than 0 items" };
                if (vErrors === null) {
                  vErrors = [err418];
                } else {
                  vErrors.push(err418);
                }
                errors++;
              }
              const len7 = data128.length;
              for (let i7 = 0; i7 < len7; i7++) {
                let data129 = data128[i7];
                const _errs275 = errors;
                let valid51 = false;
                let passing2 = null;
                const _errs276 = errors;
                if (data129 && typeof data129 == "object" && !Array.isArray(data129)) {
                  if (data129.id === void 0) {
                    const err419 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err419];
                    } else {
                      vErrors.push(err419);
                    }
                    errors++;
                  }
                  if (data129.typeVersion === void 0) {
                    const err420 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                    if (vErrors === null) {
                      vErrors = [err420];
                    } else {
                      vErrors.push(err420);
                    }
                    errors++;
                  }
                  if (data129.target === void 0) {
                    const err421 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "target" }, message: "must have required property 'target'" };
                    if (vErrors === null) {
                      vErrors = [err421];
                    } else {
                      vErrors.push(err421);
                    }
                    errors++;
                  }
                  if (data129.startMs === void 0) {
                    const err422 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "startMs" }, message: "must have required property 'startMs'" };
                    if (vErrors === null) {
                      vErrors = [err422];
                    } else {
                      vErrors.push(err422);
                    }
                    errors++;
                  }
                  if (data129.endMs === void 0) {
                    const err423 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "endMs" }, message: "must have required property 'endMs'" };
                    if (vErrors === null) {
                      vErrors = [err423];
                    } else {
                      vErrors.push(err423);
                    }
                    errors++;
                  }
                  if (data129.easing === void 0) {
                    const err424 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "easing" }, message: "must have required property 'easing'" };
                    if (vErrors === null) {
                      vErrors = [err424];
                    } else {
                      vErrors.push(err424);
                    }
                    errors++;
                  }
                  if (data129.type === void 0) {
                    const err425 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                    if (vErrors === null) {
                      vErrors = [err425];
                    } else {
                      vErrors.push(err425);
                    }
                    errors++;
                  }
                  if (data129.from === void 0) {
                    const err426 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "from" }, message: "must have required property 'from'" };
                    if (vErrors === null) {
                      vErrors = [err426];
                    } else {
                      vErrors.push(err426);
                    }
                    errors++;
                  }
                  if (data129.to === void 0) {
                    const err427 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/required", keyword: "required", params: { missingProperty: "to" }, message: "must have required property 'to'" };
                    if (vErrors === null) {
                      vErrors = [err427];
                    } else {
                      vErrors.push(err427);
                    }
                    errors++;
                  }
                  for (const key24 in data129) {
                    if (!func1.call(schema31.properties.actions.items.oneOf[0].properties, key24)) {
                      const err428 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key24 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err428];
                      } else {
                        vErrors.push(err428);
                      }
                      errors++;
                    }
                  }
                  if (data129.id !== void 0) {
                    let data130 = data129.id;
                    if (typeof data130 === "string") {
                      if (!pattern4.test(data130)) {
                        const err429 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/0/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err429];
                        } else {
                          vErrors.push(err429);
                        }
                        errors++;
                      }
                    } else {
                      const err430 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/0/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err430];
                      } else {
                        vErrors.push(err430);
                      }
                      errors++;
                    }
                  }
                  if (data129.typeVersion !== void 0) {
                    if ("0.1.0" !== data129.typeVersion) {
                      const err431 = { instancePath: instancePath + "/actions/" + i7 + "/typeVersion", schemaPath: "#/properties/actions/items/oneOf/0/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err431];
                      } else {
                        vErrors.push(err431);
                      }
                      errors++;
                    }
                  }
                  if (data129.target !== void 0) {
                    let data132 = data129.target;
                    if (data132 && typeof data132 == "object" && !Array.isArray(data132)) {
                      if (data132.nodeId === void 0) {
                        const err432 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/0/properties/target/required", keyword: "required", params: { missingProperty: "nodeId" }, message: "must have required property 'nodeId'" };
                        if (vErrors === null) {
                          vErrors = [err432];
                        } else {
                          vErrors.push(err432);
                        }
                        errors++;
                      }
                      if (data132.part === void 0) {
                        const err433 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/0/properties/target/required", keyword: "required", params: { missingProperty: "part" }, message: "must have required property 'part'" };
                        if (vErrors === null) {
                          vErrors = [err433];
                        } else {
                          vErrors.push(err433);
                        }
                        errors++;
                      }
                      for (const key25 in data132) {
                        if (!(key25 === "nodeId" || key25 === "part")) {
                          const err434 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/0/properties/target/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key25 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err434];
                          } else {
                            vErrors.push(err434);
                          }
                          errors++;
                        }
                      }
                      if (data132.nodeId !== void 0) {
                        let data133 = data132.nodeId;
                        if (typeof data133 === "string") {
                          if (!pattern4.test(data133)) {
                            const err435 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/0/properties/target/properties/nodeId/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                            if (vErrors === null) {
                              vErrors = [err435];
                            } else {
                              vErrors.push(err435);
                            }
                            errors++;
                          }
                        } else {
                          const err436 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/0/properties/target/properties/nodeId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err436];
                          } else {
                            vErrors.push(err436);
                          }
                          errors++;
                        }
                      }
                      if (data132.part !== void 0) {
                        if ("self" !== data132.part) {
                          const err437 = { instancePath: instancePath + "/actions/" + i7 + "/target/part", schemaPath: "#/properties/actions/items/oneOf/0/properties/target/properties/part/const", keyword: "const", params: { allowedValue: "self" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err437];
                          } else {
                            vErrors.push(err437);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err438 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/0/properties/target/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err438];
                      } else {
                        vErrors.push(err438);
                      }
                      errors++;
                    }
                  }
                  if (data129.startMs !== void 0) {
                    let data135 = data129.startMs;
                    if (!(typeof data135 == "number" && (!(data135 % 1) && !isNaN(data135)) && isFinite(data135))) {
                      const err439 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/0/properties/startMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err439];
                      } else {
                        vErrors.push(err439);
                      }
                      errors++;
                    }
                    if (typeof data135 == "number" && isFinite(data135)) {
                      if (data135 > 6e5 || isNaN(data135)) {
                        const err440 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/0/properties/startMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                        if (vErrors === null) {
                          vErrors = [err440];
                        } else {
                          vErrors.push(err440);
                        }
                        errors++;
                      }
                      if (data135 < 0 || isNaN(data135)) {
                        const err441 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/0/properties/startMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err441];
                        } else {
                          vErrors.push(err441);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data129.endMs !== void 0) {
                    let data136 = data129.endMs;
                    if (!(typeof data136 == "number" && (!(data136 % 1) && !isNaN(data136)) && isFinite(data136))) {
                      const err442 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/0/properties/endMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err442];
                      } else {
                        vErrors.push(err442);
                      }
                      errors++;
                    }
                    if (typeof data136 == "number" && isFinite(data136)) {
                      if (data136 > 6e5 || isNaN(data136)) {
                        const err443 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/0/properties/endMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                        if (vErrors === null) {
                          vErrors = [err443];
                        } else {
                          vErrors.push(err443);
                        }
                        errors++;
                      }
                      if (data136 < 0 || isNaN(data136)) {
                        const err444 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/0/properties/endMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err444];
                        } else {
                          vErrors.push(err444);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data129.easing !== void 0) {
                    let data137 = data129.easing;
                    if (!(data137 === "linear" || data137 === "smoothstep" || data137 === "ease-out-cubic")) {
                      const err445 = { instancePath: instancePath + "/actions/" + i7 + "/easing", schemaPath: "#/properties/actions/items/oneOf/0/properties/easing/enum", keyword: "enum", params: { allowedValues: schema31.properties.actions.items.oneOf[0].properties.easing.enum }, message: "must be equal to one of the allowed values" };
                      if (vErrors === null) {
                        vErrors = [err445];
                      } else {
                        vErrors.push(err445);
                      }
                      errors++;
                    }
                  }
                  if (data129.type !== void 0) {
                    if ("opacity" !== data129.type) {
                      const err446 = { instancePath: instancePath + "/actions/" + i7 + "/type", schemaPath: "#/properties/actions/items/oneOf/0/properties/type/const", keyword: "const", params: { allowedValue: "opacity" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err446];
                      } else {
                        vErrors.push(err446);
                      }
                      errors++;
                    }
                  }
                  if (data129.from !== void 0) {
                    let data139 = data129.from;
                    if (typeof data139 == "number" && isFinite(data139)) {
                      if (data139 > 1 || isNaN(data139)) {
                        const err447 = { instancePath: instancePath + "/actions/" + i7 + "/from", schemaPath: "#/properties/actions/items/oneOf/0/properties/from/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err447];
                        } else {
                          vErrors.push(err447);
                        }
                        errors++;
                      }
                      if (data139 < 0 || isNaN(data139)) {
                        const err448 = { instancePath: instancePath + "/actions/" + i7 + "/from", schemaPath: "#/properties/actions/items/oneOf/0/properties/from/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err448];
                        } else {
                          vErrors.push(err448);
                        }
                        errors++;
                      }
                    } else {
                      const err449 = { instancePath: instancePath + "/actions/" + i7 + "/from", schemaPath: "#/properties/actions/items/oneOf/0/properties/from/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err449];
                      } else {
                        vErrors.push(err449);
                      }
                      errors++;
                    }
                  }
                  if (data129.to !== void 0) {
                    let data140 = data129.to;
                    if (typeof data140 == "number" && isFinite(data140)) {
                      if (data140 > 1 || isNaN(data140)) {
                        const err450 = { instancePath: instancePath + "/actions/" + i7 + "/to", schemaPath: "#/properties/actions/items/oneOf/0/properties/to/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err450];
                        } else {
                          vErrors.push(err450);
                        }
                        errors++;
                      }
                      if (data140 < 0 || isNaN(data140)) {
                        const err451 = { instancePath: instancePath + "/actions/" + i7 + "/to", schemaPath: "#/properties/actions/items/oneOf/0/properties/to/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err451];
                        } else {
                          vErrors.push(err451);
                        }
                        errors++;
                      }
                    } else {
                      const err452 = { instancePath: instancePath + "/actions/" + i7 + "/to", schemaPath: "#/properties/actions/items/oneOf/0/properties/to/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err452];
                      } else {
                        vErrors.push(err452);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err453 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/0/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err453];
                  } else {
                    vErrors.push(err453);
                  }
                  errors++;
                }
                var _valid2 = _errs276 === errors;
                if (_valid2) {
                  valid51 = true;
                  passing2 = 0;
                  var props2 = true;
                }
                const _errs298 = errors;
                if (data129 && typeof data129 == "object" && !Array.isArray(data129)) {
                  if (data129.id === void 0) {
                    const err454 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err454];
                    } else {
                      vErrors.push(err454);
                    }
                    errors++;
                  }
                  if (data129.typeVersion === void 0) {
                    const err455 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                    if (vErrors === null) {
                      vErrors = [err455];
                    } else {
                      vErrors.push(err455);
                    }
                    errors++;
                  }
                  if (data129.target === void 0) {
                    const err456 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "target" }, message: "must have required property 'target'" };
                    if (vErrors === null) {
                      vErrors = [err456];
                    } else {
                      vErrors.push(err456);
                    }
                    errors++;
                  }
                  if (data129.startMs === void 0) {
                    const err457 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "startMs" }, message: "must have required property 'startMs'" };
                    if (vErrors === null) {
                      vErrors = [err457];
                    } else {
                      vErrors.push(err457);
                    }
                    errors++;
                  }
                  if (data129.endMs === void 0) {
                    const err458 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "endMs" }, message: "must have required property 'endMs'" };
                    if (vErrors === null) {
                      vErrors = [err458];
                    } else {
                      vErrors.push(err458);
                    }
                    errors++;
                  }
                  if (data129.easing === void 0) {
                    const err459 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "easing" }, message: "must have required property 'easing'" };
                    if (vErrors === null) {
                      vErrors = [err459];
                    } else {
                      vErrors.push(err459);
                    }
                    errors++;
                  }
                  if (data129.type === void 0) {
                    const err460 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                    if (vErrors === null) {
                      vErrors = [err460];
                    } else {
                      vErrors.push(err460);
                    }
                    errors++;
                  }
                  if (data129.from === void 0) {
                    const err461 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "from" }, message: "must have required property 'from'" };
                    if (vErrors === null) {
                      vErrors = [err461];
                    } else {
                      vErrors.push(err461);
                    }
                    errors++;
                  }
                  if (data129.to === void 0) {
                    const err462 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/required", keyword: "required", params: { missingProperty: "to" }, message: "must have required property 'to'" };
                    if (vErrors === null) {
                      vErrors = [err462];
                    } else {
                      vErrors.push(err462);
                    }
                    errors++;
                  }
                  for (const key26 in data129) {
                    if (!func1.call(schema31.properties.actions.items.oneOf[1].properties, key26)) {
                      const err463 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key26 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err463];
                      } else {
                        vErrors.push(err463);
                      }
                      errors++;
                    }
                  }
                  if (data129.id !== void 0) {
                    let data141 = data129.id;
                    if (typeof data141 === "string") {
                      if (!pattern4.test(data141)) {
                        const err464 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/1/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err464];
                        } else {
                          vErrors.push(err464);
                        }
                        errors++;
                      }
                    } else {
                      const err465 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/1/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err465];
                      } else {
                        vErrors.push(err465);
                      }
                      errors++;
                    }
                  }
                  if (data129.typeVersion !== void 0) {
                    if ("0.1.0" !== data129.typeVersion) {
                      const err466 = { instancePath: instancePath + "/actions/" + i7 + "/typeVersion", schemaPath: "#/properties/actions/items/oneOf/1/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err466];
                      } else {
                        vErrors.push(err466);
                      }
                      errors++;
                    }
                  }
                  if (data129.target !== void 0) {
                    let data143 = data129.target;
                    if (data143 && typeof data143 == "object" && !Array.isArray(data143)) {
                      if (data143.nodeId === void 0) {
                        const err467 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/1/properties/target/required", keyword: "required", params: { missingProperty: "nodeId" }, message: "must have required property 'nodeId'" };
                        if (vErrors === null) {
                          vErrors = [err467];
                        } else {
                          vErrors.push(err467);
                        }
                        errors++;
                      }
                      if (data143.part === void 0) {
                        const err468 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/1/properties/target/required", keyword: "required", params: { missingProperty: "part" }, message: "must have required property 'part'" };
                        if (vErrors === null) {
                          vErrors = [err468];
                        } else {
                          vErrors.push(err468);
                        }
                        errors++;
                      }
                      for (const key27 in data143) {
                        if (!(key27 === "nodeId" || key27 === "part")) {
                          const err469 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/1/properties/target/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key27 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err469];
                          } else {
                            vErrors.push(err469);
                          }
                          errors++;
                        }
                      }
                      if (data143.nodeId !== void 0) {
                        let data144 = data143.nodeId;
                        if (typeof data144 === "string") {
                          if (!pattern4.test(data144)) {
                            const err470 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/1/properties/target/properties/nodeId/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                            if (vErrors === null) {
                              vErrors = [err470];
                            } else {
                              vErrors.push(err470);
                            }
                            errors++;
                          }
                        } else {
                          const err471 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/1/properties/target/properties/nodeId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err471];
                          } else {
                            vErrors.push(err471);
                          }
                          errors++;
                        }
                      }
                      if (data143.part !== void 0) {
                        if ("self" !== data143.part) {
                          const err472 = { instancePath: instancePath + "/actions/" + i7 + "/target/part", schemaPath: "#/properties/actions/items/oneOf/1/properties/target/properties/part/const", keyword: "const", params: { allowedValue: "self" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err472];
                          } else {
                            vErrors.push(err472);
                          }
                          errors++;
                        }
                      }
                    } else {
                      const err473 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/1/properties/target/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err473];
                      } else {
                        vErrors.push(err473);
                      }
                      errors++;
                    }
                  }
                  if (data129.startMs !== void 0) {
                    let data146 = data129.startMs;
                    if (!(typeof data146 == "number" && (!(data146 % 1) && !isNaN(data146)) && isFinite(data146))) {
                      const err474 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/1/properties/startMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err474];
                      } else {
                        vErrors.push(err474);
                      }
                      errors++;
                    }
                    if (typeof data146 == "number" && isFinite(data146)) {
                      if (data146 > 6e5 || isNaN(data146)) {
                        const err475 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/1/properties/startMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                        if (vErrors === null) {
                          vErrors = [err475];
                        } else {
                          vErrors.push(err475);
                        }
                        errors++;
                      }
                      if (data146 < 0 || isNaN(data146)) {
                        const err476 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/1/properties/startMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err476];
                        } else {
                          vErrors.push(err476);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data129.endMs !== void 0) {
                    let data147 = data129.endMs;
                    if (!(typeof data147 == "number" && (!(data147 % 1) && !isNaN(data147)) && isFinite(data147))) {
                      const err477 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/1/properties/endMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err477];
                      } else {
                        vErrors.push(err477);
                      }
                      errors++;
                    }
                    if (typeof data147 == "number" && isFinite(data147)) {
                      if (data147 > 6e5 || isNaN(data147)) {
                        const err478 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/1/properties/endMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                        if (vErrors === null) {
                          vErrors = [err478];
                        } else {
                          vErrors.push(err478);
                        }
                        errors++;
                      }
                      if (data147 < 0 || isNaN(data147)) {
                        const err479 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/1/properties/endMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err479];
                        } else {
                          vErrors.push(err479);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data129.easing !== void 0) {
                    let data148 = data129.easing;
                    if (!(data148 === "linear" || data148 === "smoothstep" || data148 === "ease-out-cubic")) {
                      const err480 = { instancePath: instancePath + "/actions/" + i7 + "/easing", schemaPath: "#/properties/actions/items/oneOf/1/properties/easing/enum", keyword: "enum", params: { allowedValues: schema31.properties.actions.items.oneOf[1].properties.easing.enum }, message: "must be equal to one of the allowed values" };
                      if (vErrors === null) {
                        vErrors = [err480];
                      } else {
                        vErrors.push(err480);
                      }
                      errors++;
                    }
                  }
                  if (data129.type !== void 0) {
                    if ("path-progress" !== data129.type) {
                      const err481 = { instancePath: instancePath + "/actions/" + i7 + "/type", schemaPath: "#/properties/actions/items/oneOf/1/properties/type/const", keyword: "const", params: { allowedValue: "path-progress" }, message: "must be equal to constant" };
                      if (vErrors === null) {
                        vErrors = [err481];
                      } else {
                        vErrors.push(err481);
                      }
                      errors++;
                    }
                  }
                  if (data129.from !== void 0) {
                    let data150 = data129.from;
                    if (typeof data150 == "number" && isFinite(data150)) {
                      if (data150 > 1 || isNaN(data150)) {
                        const err482 = { instancePath: instancePath + "/actions/" + i7 + "/from", schemaPath: "#/properties/actions/items/oneOf/1/properties/from/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err482];
                        } else {
                          vErrors.push(err482);
                        }
                        errors++;
                      }
                      if (data150 < 0 || isNaN(data150)) {
                        const err483 = { instancePath: instancePath + "/actions/" + i7 + "/from", schemaPath: "#/properties/actions/items/oneOf/1/properties/from/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err483];
                        } else {
                          vErrors.push(err483);
                        }
                        errors++;
                      }
                    } else {
                      const err484 = { instancePath: instancePath + "/actions/" + i7 + "/from", schemaPath: "#/properties/actions/items/oneOf/1/properties/from/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err484];
                      } else {
                        vErrors.push(err484);
                      }
                      errors++;
                    }
                  }
                  if (data129.to !== void 0) {
                    let data151 = data129.to;
                    if (typeof data151 == "number" && isFinite(data151)) {
                      if (data151 > 1 || isNaN(data151)) {
                        const err485 = { instancePath: instancePath + "/actions/" + i7 + "/to", schemaPath: "#/properties/actions/items/oneOf/1/properties/to/maximum", keyword: "maximum", params: { comparison: "<=", limit: 1 }, message: "must be <= 1" };
                        if (vErrors === null) {
                          vErrors = [err485];
                        } else {
                          vErrors.push(err485);
                        }
                        errors++;
                      }
                      if (data151 < 0 || isNaN(data151)) {
                        const err486 = { instancePath: instancePath + "/actions/" + i7 + "/to", schemaPath: "#/properties/actions/items/oneOf/1/properties/to/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err486];
                        } else {
                          vErrors.push(err486);
                        }
                        errors++;
                      }
                    } else {
                      const err487 = { instancePath: instancePath + "/actions/" + i7 + "/to", schemaPath: "#/properties/actions/items/oneOf/1/properties/to/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                      if (vErrors === null) {
                        vErrors = [err487];
                      } else {
                        vErrors.push(err487);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err488 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/1/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err488];
                  } else {
                    vErrors.push(err488);
                  }
                  errors++;
                }
                var _valid2 = _errs298 === errors;
                if (_valid2 && valid51) {
                  valid51 = false;
                  passing2 = [passing2, 1];
                } else {
                  if (_valid2) {
                    valid51 = true;
                    passing2 = 1;
                    if (props2 !== true) {
                      props2 = true;
                    }
                  }
                  const _errs320 = errors;
                  if (data129 && typeof data129 == "object" && !Array.isArray(data129)) {
                    if (data129.id === void 0) {
                      const err489 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                      if (vErrors === null) {
                        vErrors = [err489];
                      } else {
                        vErrors.push(err489);
                      }
                      errors++;
                    }
                    if (data129.typeVersion === void 0) {
                      const err490 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                      if (vErrors === null) {
                        vErrors = [err490];
                      } else {
                        vErrors.push(err490);
                      }
                      errors++;
                    }
                    if (data129.target === void 0) {
                      const err491 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "target" }, message: "must have required property 'target'" };
                      if (vErrors === null) {
                        vErrors = [err491];
                      } else {
                        vErrors.push(err491);
                      }
                      errors++;
                    }
                    if (data129.startMs === void 0) {
                      const err492 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "startMs" }, message: "must have required property 'startMs'" };
                      if (vErrors === null) {
                        vErrors = [err492];
                      } else {
                        vErrors.push(err492);
                      }
                      errors++;
                    }
                    if (data129.endMs === void 0) {
                      const err493 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "endMs" }, message: "must have required property 'endMs'" };
                      if (vErrors === null) {
                        vErrors = [err493];
                      } else {
                        vErrors.push(err493);
                      }
                      errors++;
                    }
                    if (data129.easing === void 0) {
                      const err494 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "easing" }, message: "must have required property 'easing'" };
                      if (vErrors === null) {
                        vErrors = [err494];
                      } else {
                        vErrors.push(err494);
                      }
                      errors++;
                    }
                    if (data129.type === void 0) {
                      const err495 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                      if (vErrors === null) {
                        vErrors = [err495];
                      } else {
                        vErrors.push(err495);
                      }
                      errors++;
                    }
                    if (data129.fromDeg === void 0) {
                      const err496 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "fromDeg" }, message: "must have required property 'fromDeg'" };
                      if (vErrors === null) {
                        vErrors = [err496];
                      } else {
                        vErrors.push(err496);
                      }
                      errors++;
                    }
                    if (data129.toDeg === void 0) {
                      const err497 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/required", keyword: "required", params: { missingProperty: "toDeg" }, message: "must have required property 'toDeg'" };
                      if (vErrors === null) {
                        vErrors = [err497];
                      } else {
                        vErrors.push(err497);
                      }
                      errors++;
                    }
                    for (const key28 in data129) {
                      if (!func1.call(schema31.properties.actions.items.oneOf[2].properties, key28)) {
                        const err498 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key28 }, message: "must NOT have additional properties" };
                        if (vErrors === null) {
                          vErrors = [err498];
                        } else {
                          vErrors.push(err498);
                        }
                        errors++;
                      }
                    }
                    if (data129.id !== void 0) {
                      let data152 = data129.id;
                      if (typeof data152 === "string") {
                        if (!pattern4.test(data152)) {
                          const err499 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/2/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                          if (vErrors === null) {
                            vErrors = [err499];
                          } else {
                            vErrors.push(err499);
                          }
                          errors++;
                        }
                      } else {
                        const err500 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/2/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                        if (vErrors === null) {
                          vErrors = [err500];
                        } else {
                          vErrors.push(err500);
                        }
                        errors++;
                      }
                    }
                    if (data129.typeVersion !== void 0) {
                      if ("0.1.0" !== data129.typeVersion) {
                        const err501 = { instancePath: instancePath + "/actions/" + i7 + "/typeVersion", schemaPath: "#/properties/actions/items/oneOf/2/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                        if (vErrors === null) {
                          vErrors = [err501];
                        } else {
                          vErrors.push(err501);
                        }
                        errors++;
                      }
                    }
                    if (data129.target !== void 0) {
                      let data154 = data129.target;
                      if (data154 && typeof data154 == "object" && !Array.isArray(data154)) {
                        if (data154.nodeId === void 0) {
                          const err502 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/2/properties/target/required", keyword: "required", params: { missingProperty: "nodeId" }, message: "must have required property 'nodeId'" };
                          if (vErrors === null) {
                            vErrors = [err502];
                          } else {
                            vErrors.push(err502);
                          }
                          errors++;
                        }
                        if (data154.part === void 0) {
                          const err503 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/2/properties/target/required", keyword: "required", params: { missingProperty: "part" }, message: "must have required property 'part'" };
                          if (vErrors === null) {
                            vErrors = [err503];
                          } else {
                            vErrors.push(err503);
                          }
                          errors++;
                        }
                        for (const key29 in data154) {
                          if (!(key29 === "nodeId" || key29 === "part")) {
                            const err504 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/2/properties/target/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key29 }, message: "must NOT have additional properties" };
                            if (vErrors === null) {
                              vErrors = [err504];
                            } else {
                              vErrors.push(err504);
                            }
                            errors++;
                          }
                        }
                        if (data154.nodeId !== void 0) {
                          let data155 = data154.nodeId;
                          if (typeof data155 === "string") {
                            if (!pattern4.test(data155)) {
                              const err505 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/2/properties/target/properties/nodeId/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                              if (vErrors === null) {
                                vErrors = [err505];
                              } else {
                                vErrors.push(err505);
                              }
                              errors++;
                            }
                          } else {
                            const err506 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/2/properties/target/properties/nodeId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                            if (vErrors === null) {
                              vErrors = [err506];
                            } else {
                              vErrors.push(err506);
                            }
                            errors++;
                          }
                        }
                        if (data154.part !== void 0) {
                          if ("self" !== data154.part) {
                            const err507 = { instancePath: instancePath + "/actions/" + i7 + "/target/part", schemaPath: "#/properties/actions/items/oneOf/2/properties/target/properties/part/const", keyword: "const", params: { allowedValue: "self" }, message: "must be equal to constant" };
                            if (vErrors === null) {
                              vErrors = [err507];
                            } else {
                              vErrors.push(err507);
                            }
                            errors++;
                          }
                        }
                      } else {
                        const err508 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/2/properties/target/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                        if (vErrors === null) {
                          vErrors = [err508];
                        } else {
                          vErrors.push(err508);
                        }
                        errors++;
                      }
                    }
                    if (data129.startMs !== void 0) {
                      let data157 = data129.startMs;
                      if (!(typeof data157 == "number" && (!(data157 % 1) && !isNaN(data157)) && isFinite(data157))) {
                        const err509 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/2/properties/startMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                        if (vErrors === null) {
                          vErrors = [err509];
                        } else {
                          vErrors.push(err509);
                        }
                        errors++;
                      }
                      if (typeof data157 == "number" && isFinite(data157)) {
                        if (data157 > 6e5 || isNaN(data157)) {
                          const err510 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/2/properties/startMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                          if (vErrors === null) {
                            vErrors = [err510];
                          } else {
                            vErrors.push(err510);
                          }
                          errors++;
                        }
                        if (data157 < 0 || isNaN(data157)) {
                          const err511 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/2/properties/startMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                          if (vErrors === null) {
                            vErrors = [err511];
                          } else {
                            vErrors.push(err511);
                          }
                          errors++;
                        }
                      }
                    }
                    if (data129.endMs !== void 0) {
                      let data158 = data129.endMs;
                      if (!(typeof data158 == "number" && (!(data158 % 1) && !isNaN(data158)) && isFinite(data158))) {
                        const err512 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/2/properties/endMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                        if (vErrors === null) {
                          vErrors = [err512];
                        } else {
                          vErrors.push(err512);
                        }
                        errors++;
                      }
                      if (typeof data158 == "number" && isFinite(data158)) {
                        if (data158 > 6e5 || isNaN(data158)) {
                          const err513 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/2/properties/endMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                          if (vErrors === null) {
                            vErrors = [err513];
                          } else {
                            vErrors.push(err513);
                          }
                          errors++;
                        }
                        if (data158 < 0 || isNaN(data158)) {
                          const err514 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/2/properties/endMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                          if (vErrors === null) {
                            vErrors = [err514];
                          } else {
                            vErrors.push(err514);
                          }
                          errors++;
                        }
                      }
                    }
                    if (data129.easing !== void 0) {
                      let data159 = data129.easing;
                      if (!(data159 === "linear" || data159 === "smoothstep" || data159 === "ease-out-cubic")) {
                        const err515 = { instancePath: instancePath + "/actions/" + i7 + "/easing", schemaPath: "#/properties/actions/items/oneOf/2/properties/easing/enum", keyword: "enum", params: { allowedValues: schema31.properties.actions.items.oneOf[2].properties.easing.enum }, message: "must be equal to one of the allowed values" };
                        if (vErrors === null) {
                          vErrors = [err515];
                        } else {
                          vErrors.push(err515);
                        }
                        errors++;
                      }
                    }
                    if (data129.type !== void 0) {
                      if ("rotate" !== data129.type) {
                        const err516 = { instancePath: instancePath + "/actions/" + i7 + "/type", schemaPath: "#/properties/actions/items/oneOf/2/properties/type/const", keyword: "const", params: { allowedValue: "rotate" }, message: "must be equal to constant" };
                        if (vErrors === null) {
                          vErrors = [err516];
                        } else {
                          vErrors.push(err516);
                        }
                        errors++;
                      }
                    }
                    if (data129.fromDeg !== void 0) {
                      let data161 = data129.fromDeg;
                      if (typeof data161 == "number" && isFinite(data161)) {
                        if (data161 > 180 || isNaN(data161)) {
                          const err517 = { instancePath: instancePath + "/actions/" + i7 + "/fromDeg", schemaPath: "#/properties/actions/items/oneOf/2/properties/fromDeg/maximum", keyword: "maximum", params: { comparison: "<=", limit: 180 }, message: "must be <= 180" };
                          if (vErrors === null) {
                            vErrors = [err517];
                          } else {
                            vErrors.push(err517);
                          }
                          errors++;
                        }
                        if (data161 < -180 || isNaN(data161)) {
                          const err518 = { instancePath: instancePath + "/actions/" + i7 + "/fromDeg", schemaPath: "#/properties/actions/items/oneOf/2/properties/fromDeg/minimum", keyword: "minimum", params: { comparison: ">=", limit: -180 }, message: "must be >= -180" };
                          if (vErrors === null) {
                            vErrors = [err518];
                          } else {
                            vErrors.push(err518);
                          }
                          errors++;
                        }
                      } else {
                        const err519 = { instancePath: instancePath + "/actions/" + i7 + "/fromDeg", schemaPath: "#/properties/actions/items/oneOf/2/properties/fromDeg/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                        if (vErrors === null) {
                          vErrors = [err519];
                        } else {
                          vErrors.push(err519);
                        }
                        errors++;
                      }
                    }
                    if (data129.toDeg !== void 0) {
                      let data162 = data129.toDeg;
                      if (typeof data162 == "number" && isFinite(data162)) {
                        if (data162 > 180 || isNaN(data162)) {
                          const err520 = { instancePath: instancePath + "/actions/" + i7 + "/toDeg", schemaPath: "#/properties/actions/items/oneOf/2/properties/toDeg/maximum", keyword: "maximum", params: { comparison: "<=", limit: 180 }, message: "must be <= 180" };
                          if (vErrors === null) {
                            vErrors = [err520];
                          } else {
                            vErrors.push(err520);
                          }
                          errors++;
                        }
                        if (data162 < -180 || isNaN(data162)) {
                          const err521 = { instancePath: instancePath + "/actions/" + i7 + "/toDeg", schemaPath: "#/properties/actions/items/oneOf/2/properties/toDeg/minimum", keyword: "minimum", params: { comparison: ">=", limit: -180 }, message: "must be >= -180" };
                          if (vErrors === null) {
                            vErrors = [err521];
                          } else {
                            vErrors.push(err521);
                          }
                          errors++;
                        }
                      } else {
                        const err522 = { instancePath: instancePath + "/actions/" + i7 + "/toDeg", schemaPath: "#/properties/actions/items/oneOf/2/properties/toDeg/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                        if (vErrors === null) {
                          vErrors = [err522];
                        } else {
                          vErrors.push(err522);
                        }
                        errors++;
                      }
                    }
                  } else {
                    const err523 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/2/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                    if (vErrors === null) {
                      vErrors = [err523];
                    } else {
                      vErrors.push(err523);
                    }
                    errors++;
                  }
                  var _valid2 = _errs320 === errors;
                  if (_valid2 && valid51) {
                    valid51 = false;
                    passing2 = [passing2, 2];
                  } else {
                    if (_valid2) {
                      valid51 = true;
                      passing2 = 2;
                      if (props2 !== true) {
                        props2 = true;
                      }
                    }
                    const _errs342 = errors;
                    if (data129 && typeof data129 == "object" && !Array.isArray(data129)) {
                      if (data129.id === void 0) {
                        const err524 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                        if (vErrors === null) {
                          vErrors = [err524];
                        } else {
                          vErrors.push(err524);
                        }
                        errors++;
                      }
                      if (data129.typeVersion === void 0) {
                        const err525 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "typeVersion" }, message: "must have required property 'typeVersion'" };
                        if (vErrors === null) {
                          vErrors = [err525];
                        } else {
                          vErrors.push(err525);
                        }
                        errors++;
                      }
                      if (data129.target === void 0) {
                        const err526 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "target" }, message: "must have required property 'target'" };
                        if (vErrors === null) {
                          vErrors = [err526];
                        } else {
                          vErrors.push(err526);
                        }
                        errors++;
                      }
                      if (data129.startMs === void 0) {
                        const err527 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "startMs" }, message: "must have required property 'startMs'" };
                        if (vErrors === null) {
                          vErrors = [err527];
                        } else {
                          vErrors.push(err527);
                        }
                        errors++;
                      }
                      if (data129.endMs === void 0) {
                        const err528 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "endMs" }, message: "must have required property 'endMs'" };
                        if (vErrors === null) {
                          vErrors = [err528];
                        } else {
                          vErrors.push(err528);
                        }
                        errors++;
                      }
                      if (data129.easing === void 0) {
                        const err529 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "easing" }, message: "must have required property 'easing'" };
                        if (vErrors === null) {
                          vErrors = [err529];
                        } else {
                          vErrors.push(err529);
                        }
                        errors++;
                      }
                      if (data129.type === void 0) {
                        const err530 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "type" }, message: "must have required property 'type'" };
                        if (vErrors === null) {
                          vErrors = [err530];
                        } else {
                          vErrors.push(err530);
                        }
                        errors++;
                      }
                      if (data129.pathId === void 0) {
                        const err531 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "pathId" }, message: "must have required property 'pathId'" };
                        if (vErrors === null) {
                          vErrors = [err531];
                        } else {
                          vErrors.push(err531);
                        }
                        errors++;
                      }
                      if (data129.orientation === void 0) {
                        const err532 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/required", keyword: "required", params: { missingProperty: "orientation" }, message: "must have required property 'orientation'" };
                        if (vErrors === null) {
                          vErrors = [err532];
                        } else {
                          vErrors.push(err532);
                        }
                        errors++;
                      }
                      for (const key30 in data129) {
                        if (!func1.call(schema31.properties.actions.items.oneOf[3].properties, key30)) {
                          const err533 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key30 }, message: "must NOT have additional properties" };
                          if (vErrors === null) {
                            vErrors = [err533];
                          } else {
                            vErrors.push(err533);
                          }
                          errors++;
                        }
                      }
                      if (data129.id !== void 0) {
                        let data163 = data129.id;
                        if (typeof data163 === "string") {
                          if (!pattern4.test(data163)) {
                            const err534 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/3/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                            if (vErrors === null) {
                              vErrors = [err534];
                            } else {
                              vErrors.push(err534);
                            }
                            errors++;
                          }
                        } else {
                          const err535 = { instancePath: instancePath + "/actions/" + i7 + "/id", schemaPath: "#/properties/actions/items/oneOf/3/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err535];
                          } else {
                            vErrors.push(err535);
                          }
                          errors++;
                        }
                      }
                      if (data129.typeVersion !== void 0) {
                        if ("0.1.0" !== data129.typeVersion) {
                          const err536 = { instancePath: instancePath + "/actions/" + i7 + "/typeVersion", schemaPath: "#/properties/actions/items/oneOf/3/properties/typeVersion/const", keyword: "const", params: { allowedValue: "0.1.0" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err536];
                          } else {
                            vErrors.push(err536);
                          }
                          errors++;
                        }
                      }
                      if (data129.target !== void 0) {
                        let data165 = data129.target;
                        if (data165 && typeof data165 == "object" && !Array.isArray(data165)) {
                          if (data165.nodeId === void 0) {
                            const err537 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/3/properties/target/required", keyword: "required", params: { missingProperty: "nodeId" }, message: "must have required property 'nodeId'" };
                            if (vErrors === null) {
                              vErrors = [err537];
                            } else {
                              vErrors.push(err537);
                            }
                            errors++;
                          }
                          if (data165.part === void 0) {
                            const err538 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/3/properties/target/required", keyword: "required", params: { missingProperty: "part" }, message: "must have required property 'part'" };
                            if (vErrors === null) {
                              vErrors = [err538];
                            } else {
                              vErrors.push(err538);
                            }
                            errors++;
                          }
                          for (const key31 in data165) {
                            if (!(key31 === "nodeId" || key31 === "part")) {
                              const err539 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/3/properties/target/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key31 }, message: "must NOT have additional properties" };
                              if (vErrors === null) {
                                vErrors = [err539];
                              } else {
                                vErrors.push(err539);
                              }
                              errors++;
                            }
                          }
                          if (data165.nodeId !== void 0) {
                            let data166 = data165.nodeId;
                            if (typeof data166 === "string") {
                              if (!pattern4.test(data166)) {
                                const err540 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/3/properties/target/properties/nodeId/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                                if (vErrors === null) {
                                  vErrors = [err540];
                                } else {
                                  vErrors.push(err540);
                                }
                                errors++;
                              }
                            } else {
                              const err541 = { instancePath: instancePath + "/actions/" + i7 + "/target/nodeId", schemaPath: "#/properties/actions/items/oneOf/3/properties/target/properties/nodeId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                              if (vErrors === null) {
                                vErrors = [err541];
                              } else {
                                vErrors.push(err541);
                              }
                              errors++;
                            }
                          }
                          if (data165.part !== void 0) {
                            if ("self" !== data165.part) {
                              const err542 = { instancePath: instancePath + "/actions/" + i7 + "/target/part", schemaPath: "#/properties/actions/items/oneOf/3/properties/target/properties/part/const", keyword: "const", params: { allowedValue: "self" }, message: "must be equal to constant" };
                              if (vErrors === null) {
                                vErrors = [err542];
                              } else {
                                vErrors.push(err542);
                              }
                              errors++;
                            }
                          }
                        } else {
                          const err543 = { instancePath: instancePath + "/actions/" + i7 + "/target", schemaPath: "#/properties/actions/items/oneOf/3/properties/target/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                          if (vErrors === null) {
                            vErrors = [err543];
                          } else {
                            vErrors.push(err543);
                          }
                          errors++;
                        }
                      }
                      if (data129.startMs !== void 0) {
                        let data168 = data129.startMs;
                        if (!(typeof data168 == "number" && (!(data168 % 1) && !isNaN(data168)) && isFinite(data168))) {
                          const err544 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/3/properties/startMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                          if (vErrors === null) {
                            vErrors = [err544];
                          } else {
                            vErrors.push(err544);
                          }
                          errors++;
                        }
                        if (typeof data168 == "number" && isFinite(data168)) {
                          if (data168 > 6e5 || isNaN(data168)) {
                            const err545 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/3/properties/startMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                            if (vErrors === null) {
                              vErrors = [err545];
                            } else {
                              vErrors.push(err545);
                            }
                            errors++;
                          }
                          if (data168 < 0 || isNaN(data168)) {
                            const err546 = { instancePath: instancePath + "/actions/" + i7 + "/startMs", schemaPath: "#/properties/actions/items/oneOf/3/properties/startMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                            if (vErrors === null) {
                              vErrors = [err546];
                            } else {
                              vErrors.push(err546);
                            }
                            errors++;
                          }
                        }
                      }
                      if (data129.endMs !== void 0) {
                        let data169 = data129.endMs;
                        if (!(typeof data169 == "number" && (!(data169 % 1) && !isNaN(data169)) && isFinite(data169))) {
                          const err547 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/3/properties/endMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                          if (vErrors === null) {
                            vErrors = [err547];
                          } else {
                            vErrors.push(err547);
                          }
                          errors++;
                        }
                        if (typeof data169 == "number" && isFinite(data169)) {
                          if (data169 > 6e5 || isNaN(data169)) {
                            const err548 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/3/properties/endMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                            if (vErrors === null) {
                              vErrors = [err548];
                            } else {
                              vErrors.push(err548);
                            }
                            errors++;
                          }
                          if (data169 < 0 || isNaN(data169)) {
                            const err549 = { instancePath: instancePath + "/actions/" + i7 + "/endMs", schemaPath: "#/properties/actions/items/oneOf/3/properties/endMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                            if (vErrors === null) {
                              vErrors = [err549];
                            } else {
                              vErrors.push(err549);
                            }
                            errors++;
                          }
                        }
                      }
                      if (data129.easing !== void 0) {
                        let data170 = data129.easing;
                        if (!(data170 === "linear" || data170 === "smoothstep" || data170 === "ease-out-cubic")) {
                          const err550 = { instancePath: instancePath + "/actions/" + i7 + "/easing", schemaPath: "#/properties/actions/items/oneOf/3/properties/easing/enum", keyword: "enum", params: { allowedValues: schema31.properties.actions.items.oneOf[3].properties.easing.enum }, message: "must be equal to one of the allowed values" };
                          if (vErrors === null) {
                            vErrors = [err550];
                          } else {
                            vErrors.push(err550);
                          }
                          errors++;
                        }
                      }
                      if (data129.type !== void 0) {
                        if ("move-path" !== data129.type) {
                          const err551 = { instancePath: instancePath + "/actions/" + i7 + "/type", schemaPath: "#/properties/actions/items/oneOf/3/properties/type/const", keyword: "const", params: { allowedValue: "move-path" }, message: "must be equal to constant" };
                          if (vErrors === null) {
                            vErrors = [err551];
                          } else {
                            vErrors.push(err551);
                          }
                          errors++;
                        }
                      }
                      if (data129.pathId !== void 0) {
                        let data172 = data129.pathId;
                        if (typeof data172 === "string") {
                          if (!pattern4.test(data172)) {
                            const err552 = { instancePath: instancePath + "/actions/" + i7 + "/pathId", schemaPath: "#/properties/actions/items/oneOf/3/properties/pathId/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                            if (vErrors === null) {
                              vErrors = [err552];
                            } else {
                              vErrors.push(err552);
                            }
                            errors++;
                          }
                        } else {
                          const err553 = { instancePath: instancePath + "/actions/" + i7 + "/pathId", schemaPath: "#/properties/actions/items/oneOf/3/properties/pathId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                          if (vErrors === null) {
                            vErrors = [err553];
                          } else {
                            vErrors.push(err553);
                          }
                          errors++;
                        }
                      }
                      if (data129.orientation !== void 0) {
                        let data173 = data129.orientation;
                        const _errs363 = errors;
                        let valid60 = false;
                        let passing3 = null;
                        const _errs364 = errors;
                        if (data173 && typeof data173 == "object" && !Array.isArray(data173)) {
                          if (data173.kind === void 0) {
                            const err554 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/0/required", keyword: "required", params: { missingProperty: "kind" }, message: "must have required property 'kind'" };
                            if (vErrors === null) {
                              vErrors = [err554];
                            } else {
                              vErrors.push(err554);
                            }
                            errors++;
                          }
                          for (const key32 in data173) {
                            if (!(key32 === "kind")) {
                              const err555 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/0/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key32 }, message: "must NOT have additional properties" };
                              if (vErrors === null) {
                                vErrors = [err555];
                              } else {
                                vErrors.push(err555);
                              }
                              errors++;
                            }
                          }
                          if (data173.kind !== void 0) {
                            if ("fixed" !== data173.kind) {
                              const err556 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/kind", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/0/properties/kind/const", keyword: "const", params: { allowedValue: "fixed" }, message: "must be equal to constant" };
                              if (vErrors === null) {
                                vErrors = [err556];
                              } else {
                                vErrors.push(err556);
                              }
                              errors++;
                            }
                          }
                        } else {
                          const err557 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/0/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                          if (vErrors === null) {
                            vErrors = [err557];
                          } else {
                            vErrors.push(err557);
                          }
                          errors++;
                        }
                        var _valid3 = _errs364 === errors;
                        if (_valid3) {
                          valid60 = true;
                          passing3 = 0;
                          var props3 = true;
                        }
                        const _errs368 = errors;
                        if (data173 && typeof data173 == "object" && !Array.isArray(data173)) {
                          if (data173.kind === void 0) {
                            const err558 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/required", keyword: "required", params: { missingProperty: "kind" }, message: "must have required property 'kind'" };
                            if (vErrors === null) {
                              vErrors = [err558];
                            } else {
                              vErrors.push(err558);
                            }
                            errors++;
                          }
                          if (data173.minDeg === void 0) {
                            const err559 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/required", keyword: "required", params: { missingProperty: "minDeg" }, message: "must have required property 'minDeg'" };
                            if (vErrors === null) {
                              vErrors = [err559];
                            } else {
                              vErrors.push(err559);
                            }
                            errors++;
                          }
                          if (data173.maxDeg === void 0) {
                            const err560 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/required", keyword: "required", params: { missingProperty: "maxDeg" }, message: "must have required property 'maxDeg'" };
                            if (vErrors === null) {
                              vErrors = [err560];
                            } else {
                              vErrors.push(err560);
                            }
                            errors++;
                          }
                          for (const key33 in data173) {
                            if (!(key33 === "kind" || key33 === "minDeg" || key33 === "maxDeg")) {
                              const err561 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key33 }, message: "must NOT have additional properties" };
                              if (vErrors === null) {
                                vErrors = [err561];
                              } else {
                                vErrors.push(err561);
                              }
                              errors++;
                            }
                          }
                          if (data173.kind !== void 0) {
                            if ("tangent" !== data173.kind) {
                              const err562 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/kind", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/properties/kind/const", keyword: "const", params: { allowedValue: "tangent" }, message: "must be equal to constant" };
                              if (vErrors === null) {
                                vErrors = [err562];
                              } else {
                                vErrors.push(err562);
                              }
                              errors++;
                            }
                          }
                          if (data173.minDeg !== void 0) {
                            let data176 = data173.minDeg;
                            if (typeof data176 == "number" && isFinite(data176)) {
                              if (data176 > 180 || isNaN(data176)) {
                                const err563 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/minDeg", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/properties/minDeg/maximum", keyword: "maximum", params: { comparison: "<=", limit: 180 }, message: "must be <= 180" };
                                if (vErrors === null) {
                                  vErrors = [err563];
                                } else {
                                  vErrors.push(err563);
                                }
                                errors++;
                              }
                              if (data176 < -180 || isNaN(data176)) {
                                const err564 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/minDeg", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/properties/minDeg/minimum", keyword: "minimum", params: { comparison: ">=", limit: -180 }, message: "must be >= -180" };
                                if (vErrors === null) {
                                  vErrors = [err564];
                                } else {
                                  vErrors.push(err564);
                                }
                                errors++;
                              }
                            } else {
                              const err565 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/minDeg", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/properties/minDeg/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err565];
                              } else {
                                vErrors.push(err565);
                              }
                              errors++;
                            }
                          }
                          if (data173.maxDeg !== void 0) {
                            let data177 = data173.maxDeg;
                            if (typeof data177 == "number" && isFinite(data177)) {
                              if (data177 > 180 || isNaN(data177)) {
                                const err566 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/maxDeg", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/properties/maxDeg/maximum", keyword: "maximum", params: { comparison: "<=", limit: 180 }, message: "must be <= 180" };
                                if (vErrors === null) {
                                  vErrors = [err566];
                                } else {
                                  vErrors.push(err566);
                                }
                                errors++;
                              }
                              if (data177 < -180 || isNaN(data177)) {
                                const err567 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/maxDeg", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/properties/maxDeg/minimum", keyword: "minimum", params: { comparison: ">=", limit: -180 }, message: "must be >= -180" };
                                if (vErrors === null) {
                                  vErrors = [err567];
                                } else {
                                  vErrors.push(err567);
                                }
                                errors++;
                              }
                            } else {
                              const err568 = { instancePath: instancePath + "/actions/" + i7 + "/orientation/maxDeg", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/properties/maxDeg/type", keyword: "type", params: { type: "number" }, message: "must be number" };
                              if (vErrors === null) {
                                vErrors = [err568];
                              } else {
                                vErrors.push(err568);
                              }
                              errors++;
                            }
                          }
                        } else {
                          const err569 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf/1/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                          if (vErrors === null) {
                            vErrors = [err569];
                          } else {
                            vErrors.push(err569);
                          }
                          errors++;
                        }
                        var _valid3 = _errs368 === errors;
                        if (_valid3 && valid60) {
                          valid60 = false;
                          passing3 = [passing3, 1];
                        } else {
                          if (_valid3) {
                            valid60 = true;
                            passing3 = 1;
                            if (props3 !== true) {
                              props3 = true;
                            }
                          }
                        }
                        if (!valid60) {
                          const err570 = { instancePath: instancePath + "/actions/" + i7 + "/orientation", schemaPath: "#/properties/actions/items/oneOf/3/properties/orientation/oneOf", keyword: "oneOf", params: { passingSchemas: passing3 }, message: "must match exactly one schema in oneOf" };
                          if (vErrors === null) {
                            vErrors = [err570];
                          } else {
                            vErrors.push(err570);
                          }
                          errors++;
                        } else {
                          errors = _errs363;
                          if (vErrors !== null) {
                            if (_errs363) {
                              vErrors.length = _errs363;
                            } else {
                              vErrors = null;
                            }
                          }
                        }
                      }
                    } else {
                      const err571 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf/3/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                      if (vErrors === null) {
                        vErrors = [err571];
                      } else {
                        vErrors.push(err571);
                      }
                      errors++;
                    }
                    var _valid2 = _errs342 === errors;
                    if (_valid2 && valid51) {
                      valid51 = false;
                      passing2 = [passing2, 3];
                    } else {
                      if (_valid2) {
                        valid51 = true;
                        passing2 = 3;
                        if (props2 !== true) {
                          props2 = true;
                        }
                      }
                    }
                  }
                }
                if (!valid51) {
                  const err572 = { instancePath: instancePath + "/actions/" + i7, schemaPath: "#/properties/actions/items/oneOf", keyword: "oneOf", params: { passingSchemas: passing2 }, message: "must match exactly one schema in oneOf" };
                  if (vErrors === null) {
                    vErrors = [err572];
                  } else {
                    vErrors.push(err572);
                  }
                  errors++;
                } else {
                  errors = _errs275;
                  if (vErrors !== null) {
                    if (_errs275) {
                      vErrors.length = _errs275;
                    } else {
                      vErrors = null;
                    }
                  }
                }
              }
            } else {
              const err573 = { instancePath: instancePath + "/actions", schemaPath: "#/properties/actions/type", keyword: "type", params: { type: "array" }, message: "must be array" };
              if (vErrors === null) {
                vErrors = [err573];
              } else {
                vErrors.push(err573);
              }
              errors++;
            }
          }
          if (data.keyframes !== void 0) {
            let data178 = data.keyframes;
            if (Array.isArray(data178)) {
              if (data178.length > 20) {
                const err574 = { instancePath: instancePath + "/keyframes", schemaPath: "#/properties/keyframes/maxItems", keyword: "maxItems", params: { limit: 20 }, message: "must NOT have more than 20 items" };
                if (vErrors === null) {
                  vErrors = [err574];
                } else {
                  vErrors.push(err574);
                }
                errors++;
              }
              if (data178.length < 2) {
                const err575 = { instancePath: instancePath + "/keyframes", schemaPath: "#/properties/keyframes/minItems", keyword: "minItems", params: { limit: 2 }, message: "must NOT have fewer than 2 items" };
                if (vErrors === null) {
                  vErrors = [err575];
                } else {
                  vErrors.push(err575);
                }
                errors++;
              }
              const len8 = data178.length;
              for (let i8 = 0; i8 < len8; i8++) {
                let data179 = data178[i8];
                if (data179 && typeof data179 == "object" && !Array.isArray(data179)) {
                  if (data179.id === void 0) {
                    const err576 = { instancePath: instancePath + "/keyframes/" + i8, schemaPath: "#/properties/keyframes/items/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
                    if (vErrors === null) {
                      vErrors = [err576];
                    } else {
                      vErrors.push(err576);
                    }
                    errors++;
                  }
                  if (data179.tMs === void 0) {
                    const err577 = { instancePath: instancePath + "/keyframes/" + i8, schemaPath: "#/properties/keyframes/items/required", keyword: "required", params: { missingProperty: "tMs" }, message: "must have required property 'tMs'" };
                    if (vErrors === null) {
                      vErrors = [err577];
                    } else {
                      vErrors.push(err577);
                    }
                    errors++;
                  }
                  if (data179.purpose === void 0) {
                    const err578 = { instancePath: instancePath + "/keyframes/" + i8, schemaPath: "#/properties/keyframes/items/required", keyword: "required", params: { missingProperty: "purpose" }, message: "must have required property 'purpose'" };
                    if (vErrors === null) {
                      vErrors = [err578];
                    } else {
                      vErrors.push(err578);
                    }
                    errors++;
                  }
                  for (const key34 in data179) {
                    if (!(key34 === "id" || key34 === "tMs" || key34 === "purpose")) {
                      const err579 = { instancePath: instancePath + "/keyframes/" + i8, schemaPath: "#/properties/keyframes/items/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key34 }, message: "must NOT have additional properties" };
                      if (vErrors === null) {
                        vErrors = [err579];
                      } else {
                        vErrors.push(err579);
                      }
                      errors++;
                    }
                  }
                  if (data179.id !== void 0) {
                    let data180 = data179.id;
                    if (typeof data180 === "string") {
                      if (!pattern4.test(data180)) {
                        const err580 = { instancePath: instancePath + "/keyframes/" + i8 + "/id", schemaPath: "#/properties/keyframes/items/properties/id/pattern", keyword: "pattern", params: { pattern: "^[A-Za-z][A-Za-z0-9._-]{0,95}$" }, message: 'must match pattern "^[A-Za-z][A-Za-z0-9._-]{0,95}$"' };
                        if (vErrors === null) {
                          vErrors = [err580];
                        } else {
                          vErrors.push(err580);
                        }
                        errors++;
                      }
                    } else {
                      const err581 = { instancePath: instancePath + "/keyframes/" + i8 + "/id", schemaPath: "#/properties/keyframes/items/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err581];
                      } else {
                        vErrors.push(err581);
                      }
                      errors++;
                    }
                  }
                  if (data179.tMs !== void 0) {
                    let data181 = data179.tMs;
                    if (!(typeof data181 == "number" && (!(data181 % 1) && !isNaN(data181)) && isFinite(data181))) {
                      const err582 = { instancePath: instancePath + "/keyframes/" + i8 + "/tMs", schemaPath: "#/properties/keyframes/items/properties/tMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                      if (vErrors === null) {
                        vErrors = [err582];
                      } else {
                        vErrors.push(err582);
                      }
                      errors++;
                    }
                    if (typeof data181 == "number" && isFinite(data181)) {
                      if (data181 > 6e5 || isNaN(data181)) {
                        const err583 = { instancePath: instancePath + "/keyframes/" + i8 + "/tMs", schemaPath: "#/properties/keyframes/items/properties/tMs/maximum", keyword: "maximum", params: { comparison: "<=", limit: 6e5 }, message: "must be <= 600000" };
                        if (vErrors === null) {
                          vErrors = [err583];
                        } else {
                          vErrors.push(err583);
                        }
                        errors++;
                      }
                      if (data181 < 0 || isNaN(data181)) {
                        const err584 = { instancePath: instancePath + "/keyframes/" + i8 + "/tMs", schemaPath: "#/properties/keyframes/items/properties/tMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                        if (vErrors === null) {
                          vErrors = [err584];
                        } else {
                          vErrors.push(err584);
                        }
                        errors++;
                      }
                    }
                  }
                  if (data179.purpose !== void 0) {
                    let data182 = data179.purpose;
                    if (typeof data182 === "string") {
                      if (func2(data182) > 2e3) {
                        const err585 = { instancePath: instancePath + "/keyframes/" + i8 + "/purpose", schemaPath: "#/properties/keyframes/items/properties/purpose/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
                        if (vErrors === null) {
                          vErrors = [err585];
                        } else {
                          vErrors.push(err585);
                        }
                        errors++;
                      }
                      if (func2(data182) < 1) {
                        const err586 = { instancePath: instancePath + "/keyframes/" + i8 + "/purpose", schemaPath: "#/properties/keyframes/items/properties/purpose/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                        if (vErrors === null) {
                          vErrors = [err586];
                        } else {
                          vErrors.push(err586);
                        }
                        errors++;
                      }
                    } else {
                      const err587 = { instancePath: instancePath + "/keyframes/" + i8 + "/purpose", schemaPath: "#/properties/keyframes/items/properties/purpose/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                      if (vErrors === null) {
                        vErrors = [err587];
                      } else {
                        vErrors.push(err587);
                      }
                      errors++;
                    }
                  }
                } else {
                  const err588 = { instancePath: instancePath + "/keyframes/" + i8, schemaPath: "#/properties/keyframes/items/type", keyword: "type", params: { type: "object" }, message: "must be object" };
                  if (vErrors === null) {
                    vErrors = [err588];
                  } else {
                    vErrors.push(err588);
                  }
                  errors++;
                }
              }
            } else {
              const err589 = { instancePath: instancePath + "/keyframes", schemaPath: "#/properties/keyframes/type", keyword: "type", params: { type: "array" }, message: "must be array" };
              if (vErrors === null) {
                vErrors = [err589];
              } else {
                vErrors.push(err589);
              }
              errors++;
            }
          }
        } else {
          const err590 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
          if (vErrors === null) {
            vErrors = [err590];
          } else {
            vErrors.push(err590);
          }
          errors++;
        }
        validate20.errors = vErrors;
        return errors === 0;
      }
      validate20.evaluated = { "props": true, "dynamicProps": false, "dynamicItems": false };
    }
  });

  // src/timeline.cjs
  var require_timeline = __commonJS({
    "src/timeline.cjs"(exports, module) {
      "use strict";
      var clamp = (p) => Math.max(0, Math.min(1, p));
      function ease(kind, p) {
        p = clamp(p);
        if (kind === "smoothstep") return p * p * (3 - 2 * p);
        if (kind === "ease-out-cubic") return 1 - (1 - p) ** 3;
        return p;
      }
      function curve(points, u) {
        const v = 1 - u;
        return {
          x: v ** 3 * points[0].x + 3 * v * v * u * points[1].x + 3 * v * u * u * points[2].x + u ** 3 * points[3].x,
          y: v ** 3 * points[0].y + 3 * v * v * u * points[1].y + 3 * v * u * u * points[2].y + u ** 3 * points[3].y
        };
      }
      function tangent(points, u, orientation, fallback) {
        const v = 1 - u;
        const dx = 3 * v * v * (points[1].x - points[0].x) + 6 * v * u * (points[2].x - points[1].x) + 3 * u * u * (points[3].x - points[2].x);
        const dy = 3 * v * v * (points[1].y - points[0].y) + 6 * v * u * (points[2].y - points[1].y) + 3 * u * u * (points[3].y - points[2].y);
        if (Math.hypot(dx, dy) < 1e-9) return fallback;
        return Math.max(
          orientation.minDeg,
          Math.min(orientation.maxDeg, Math.atan2(dy, dx) * 180 / Math.PI)
        );
      }
      function progress(action, timeMs) {
        return action.startMs === action.endMs ? 1 : ease(
          action.easing,
          (timeMs - action.startMs) / (action.endMs - action.startMs)
        );
      }
      function imagePlacement(node, asset) {
        const scale = Math.min(
          node.box.width / asset.intrinsic.width,
          node.box.height / asset.intrinsic.height
        );
        const width = asset.intrinsic.width * scale, height = asset.intrinsic.height * scale;
        const x = (node.box.width - width) / 2, y = (node.box.height - height) / 2;
        const anchor = asset.anchors.find((a) => a.id === node.anchorId);
        return {
          scale,
          x,
          y,
          width,
          height,
          anchor: { x: x + anchor.x * width, y: y + anchor.y * height }
        };
      }
      function matrix(node, state, asset) {
        const placement = imagePlacement(node, asset);
        const rad = state.rotationDeg * Math.PI / 180, c = Math.cos(rad), s = Math.sin(rad);
        const a = placement.anchor;
        return [
          c,
          s,
          -s,
          c,
          state.position.x - c * a.x + s * a.y,
          state.position.y - s * a.x - c * a.y
        ];
      }
      function activeBeat(scene, t) {
        return scene.beats.find(
          (b) => b.startMs <= t && (t < b.endMs || t === scene.durationMs && b.endMs === t)
        );
      }
      function channels(action) {
        if (action.type === "opacity") return ["opacity"];
        if (action.type === "rotate") return ["rotation"];
        if (action.type === "path-progress") return ["progress"];
        return action.orientation.kind === "tangent" ? ["position", "rotation"] : ["position"];
      }
      function evaluate(compiled, timeMs) {
        const scene = compiled.source;
        if (!Number.isFinite(timeMs) || timeMs < 0 || timeMs > scene.durationMs)
          throw new RangeError("timeMs must be finite and inside scene duration");
        const beat = activeBeat(scene, timeMs);
        const nodes = {};
        for (const node of compiled.nodes) {
          const state = { opacity: node.initialOpacity };
          if (node.type === "text")
            state.text = node.content.kind === "static" ? node.content.text : beat?.screenText || "";
          if (node.type === "path") state.progress = node.initialProgress;
          if (node.type === "image") {
            const p = imagePlacement(node, compiled.assets.get(node.assetRef.id));
            state.position = {
              x: node.box.x + p.anchor.x,
              y: node.box.y + p.anchor.y
            };
            state.rotationDeg = node.rotationDeg;
          }
          nodes[node.id] = state;
        }
        for (const action of compiled.actions) {
          if (timeMs < action.startMs) continue;
          const state = nodes[action.target.nodeId], p = progress(action, timeMs);
          if (action.type === "opacity")
            state.opacity = action.from + (action.to - action.from) * p;
          if (action.type === "rotate")
            state.rotationDeg = action.fromDeg + (action.toDeg - action.fromDeg) * p;
          if (action.type === "path-progress")
            state.progress = action.from + (action.to - action.from) * p;
          if (action.type === "move-path") {
            const points = compiled.paths.get(action.pathId).points;
            state.position = curve(points, p);
            if (action.orientation.kind === "tangent")
              state.rotationDeg = tangent(
                points,
                p,
                action.orientation,
                compiled.nodeMap.get(action.target.nodeId).rotationDeg
              );
          }
        }
        return { timeMs, beatId: beat?.id || null, nodes };
      }
      module.exports = {
        ease,
        curve,
        tangent,
        progress,
        channels,
        evaluate,
        imagePlacement,
        matrix
      };
    }
  });

  // src/compiler.cjs
  var require_compiler = __commonJS({
    "src/compiler.cjs"(exports, module) {
      "use strict";
      var validateSchema = require_validate_scene();
      var { registry, EngineError, diagnostic } = require_registry();
      var { channels, imagePlacement, tangent } = require_timeline();
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
          return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
        return JSON.stringify(value);
      }
      function overlaps(a, b) {
        const az = a.startMs === a.endMs, bz = b.startMs === b.endMs;
        if (az && bz) return a.startMs === b.startMs;
        if (az) return a.startMs >= b.startMs && a.startMs < b.endMs;
        if (bz) return b.startMs >= a.startMs && b.startMs < a.endMs;
        return a.startMs < b.endMs && b.startMs < a.endMs;
      }
      var samePoint = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) < 1e-6;
      function compile(input) {
        if (input?.format !== registry.format || input?.schemaVersion !== registry.schemaVersion || input?.contractVersion !== registry.contractVersion) {
          throw new EngineError([
            diagnostic(
              "UNSUPPORTED_VERSION",
              "/",
              "Expected hps.e1.scene 0.1.0 / contract 0.7.1; P01 is a separate format"
            )
          ]);
        }
        const unsupported = [];
        for (const [key, supported] of [
          ["nodes", registry.nodes],
          ["actions", registry.actions]
        ]) {
          if (!Array.isArray(input[key])) continue;
          input[key].forEach((item, index) => {
            if (item && (!supported.includes(item.type) || item.typeVersion !== "0.1.0"))
              unsupported.push(
                diagnostic(
                  "UNSUPPORTED_CAPABILITY",
                  `/${key}/${index}`,
                  "Unknown type or type version",
                  key === "nodes" ? item.id : void 0
                )
              );
          });
        }
        if (unsupported.length) throw new EngineError(unsupported);
        if (!validateSchema(input)) {
          throw new EngineError(
            validateSchema.errors.slice(0, 40).map(
              (e) => diagnostic(
                "INVALID_FIELD",
                e.instancePath + (e.keyword === "additionalProperties" ? "/" + e.params.additionalProperty : ""),
                e.message
              )
            )
          );
        }
        const source = deepFreeze(JSON.parse(JSON.stringify(input)));
        const errors = [];
        const add = (code, path, message, nodeId) => errors.push(diagnostic(code, path, message, nodeId));
        const maps = {};
        for (const key of [
          "nodes",
          "assets",
          "paths",
          "beats",
          "actions",
          "keyframes"
        ]) {
          maps[key] = /* @__PURE__ */ new Map();
          source[key].forEach((item, index) => {
            if (maps[key].has(item.id))
              add(
                "DUPLICATE_ID",
                `/${key}/${index}/id`,
                `Duplicate ${key} ID ${item.id}`
              );
            maps[key].set(item.id, item);
          });
        }
        if (source.templateRef.id !== registry.template.id)
          add(
            "UNSUPPORTED_CAPABILITY",
            "/templateRef",
            "Only the open-stage E1 recipe is implemented"
          );
        if (source.assets.reduce(
          (sum, a) => sum + a.intrinsic.width * a.intrinsic.height,
          0
        ) > registry.limits.resourcePixels)
          add("RESOURCE_BUDGET", "/assets", "Declared asset pixel budget exceeded");
        const safe = source.canvas.safeInsets, width = source.canvas.width, height = source.canvas.height;
        if (safe.left + safe.right >= width || safe.top + safe.bottom >= height)
          add("INVALID_LAYOUT", "/canvas/safeInsets", "Insets consume canvas");
        source.assets.forEach((asset, index) => {
          if (asset.file.path.split("/").some((p) => !p || p === "." || p === ".."))
            add(
              "INVALID_RESOURCE_PATH",
              `/assets/${index}/file/path`,
              "Asset path must be normalized inside package"
            );
          const r = asset.alphaBounds, sz = asset.intrinsic;
          if (r.x < 0 || r.y < 0 || r.x + r.width > sz.width || r.y + r.height > sz.height)
            add(
              "INVALID_ASSET_GEOMETRY",
              `/assets/${index}/alphaBounds`,
              "alphaBounds outside intrinsic size"
            );
          if (new Set(asset.anchors.map((a) => a.id)).size !== asset.anchors.length)
            add(
              "DUPLICATE_ID",
              `/assets/${index}/anchors`,
              "Duplicate resource anchor"
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
                node.id
              );
            else if (!asset.anchors.some((a) => a.id === node.anchorId))
              add(
                "MISSING_REFERENCE",
                path + "/anchorId",
                "Missing resource anchor",
                node.id
              );
          }
          if (node.type === "path" && !maps.paths.has(node.pathId))
            add("MISSING_REFERENCE", path + "/pathId", "Missing curve", node.id);
          if (node.type === "ring" && Math.min(node.box.width, node.box.height) <= node.strokeWidth)
            add(
              "INVALID_VECTOR_GEOMETRY",
              path + "/box",
              "Ring stroke does not fit its declared box",
              node.id
            );
          if (node.type === "text") {
            const b = node.box;
            if (b.x < safe.left || b.y < safe.top || b.x + b.width > width - safe.right || b.y + b.height > height - safe.bottom)
              add(
                "INVALID_LAYOUT",
                path + "/box",
                "Text box must fit declared reading safe area",
                node.id
              );
          }
        });
        const beats = [...source.beats].sort(
          (a, b) => a.startMs - b.startMs || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)
        );
        beats.forEach((beat, i) => {
          if (beat.startMs >= beat.endMs || beat.endMs > source.durationMs)
            add(
              "TIMING_OUT_OF_RANGE",
              `/beats/${source.beats.indexOf(beat)}`,
              "Beat must have positive duration inside scene"
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
        if (!source.keyframes.some((k) => k.tMs === 0) || !source.keyframes.some((k) => k.tMs === source.durationMs))
          add(
            "INCOMPLETE_KEYFRAMES",
            "/keyframes",
            "Initial and final keyframes required"
          );
        const actions = [...source.actions].sort(
          (a, b) => a.startMs - b.startMs || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)
        );
        const tracks = /* @__PURE__ */ new Map();
        actions.forEach((action) => {
          const node = maps.nodes.get(action.target.nodeId), path = `/actions/${source.actions.indexOf(action)}`;
          if (action.startMs > action.endMs || action.endMs > source.durationMs)
            add("TIMING_OUT_OF_RANGE", path, "Action interval outside scene");
          if (!node) {
            add("MISSING_REFERENCE", path + "/target", "Missing action target");
            return;
          }
          if ((action.type === "move-path" || action.type === "rotate") && node.type !== "image")
            add(
              "TARGET_CAPABILITY",
              path + "/target",
              "Position/rotation supports whole Image only",
              node.id
            );
          if (action.type === "path-progress" && node.type !== "path")
            add(
              "TARGET_CAPABILITY",
              path + "/target",
              "Progress requires a Path",
              node.id
            );
          if (action.type === "move-path") {
            if (!maps.paths.has(action.pathId))
              add(
                "MISSING_REFERENCE",
                path + "/pathId",
                "Missing motion curve",
                node.id
              );
            if (action.orientation.kind === "tangent" && action.orientation.minDeg > action.orientation.maxDeg)
              add(
                "INVALID_FIELD",
                path + "/orientation",
                "minDeg must not exceed maxDeg"
              );
          }
          for (const channel of channels(action)) {
            const key = node.id + ":" + channel;
            if (!tracks.has(key)) tracks.set(key, []);
            tracks.get(key).push(action);
          }
        });
        if (errors.length) throw new EngineError(errors);
        for (const [key, track] of tracks) {
          const separator = key.lastIndexOf(":"), node = maps.nodes.get(key.slice(0, separator)), channel = key.slice(separator + 1);
          for (let i = 0; i < track.length; i++) {
            const current = track[i], previous = track[i - 1];
            for (let j = 0; j < i; j++)
              if (overlaps(track[j], current))
                add(
                  "ACTION_CONFLICT",
                  "/actions",
                  `Overlapping ${channel} actions on ${node.id}`,
                  node.id
                );
            if (channel === "opacity" || channel === "progress") {
              const expected = previous ? previous.to : channel === "opacity" ? node.initialOpacity : node.initialProgress;
              if (Math.abs(current.from - expected) > 1e-6)
                add(
                  "STATE_DISCONTINUITY",
                  "/actions",
                  `Discontinuous ${channel} value`,
                  node.id
                );
            }
            if (channel === "position") {
              const placement = imagePlacement(
                node,
                maps.assets.get(node.assetRef.id)
              );
              const expected = previous ? maps.paths.get(previous.pathId).points[3] : {
                x: node.box.x + placement.anchor.x,
                y: node.box.y + placement.anchor.y
              };
              if (!samePoint(expected, maps.paths.get(current.pathId).points[0]))
                add(
                  "STATE_DISCONTINUITY",
                  "/actions",
                  "Curve starts away from held anchor position",
                  node.id
                );
            }
            if (channel === "rotation") {
              const terminal = (a) => a.type === "rotate" ? a.toDeg : tangent(
                maps.paths.get(a.pathId).points,
                1,
                a.orientation,
                node.rotationDeg
              );
              const expected = previous ? terminal(previous) : node.rotationDeg;
              const initial = current.type === "rotate" ? current.fromDeg : tangent(
                maps.paths.get(current.pathId).points,
                0,
                current.orientation,
                node.rotationDeg
              );
              if (Math.abs(initial - expected) > 1e-6)
                add(
                  "STATE_DISCONTINUITY",
                  "/actions",
                  "Rotation starts away from held angle",
                  node.id
                );
            }
          }
        }
        const nodes = [...source.nodes].sort(
          (a, b) => a.zIndex - b.zIndex || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)
        );
        let layers = 0, lastWasCanvas = false;
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
            canvasLayers: layers
          }
        };
      }
      module.exports = { compile, canonical, overlaps };
    }
  });

  // src/resources.cjs
  var require_resources = __commonJS({
    "src/resources.cjs"(exports, module) {
      "use strict";
      var { EngineError, diagnostic } = require_registry();
      async function sha256(bytes) {
        const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
        return [...new Uint8Array(digest)].map((v) => v.toString(16).padStart(2, "0")).join("");
      }
      async function loadResources(compiled, pack) {
        const images = /* @__PURE__ */ new Map(), objectUrls = [];
        try {
          for (const asset of compiled.source.assets) {
            const encoded = pack[asset.file.path];
            if (typeof encoded !== "string")
              throw new EngineError([
                diagnostic(
                  "ASSET_UNAVAILABLE",
                  "/assets",
                  `Missing packaged bytes: ${asset.file.path}`
                )
              ]);
            let raw;
            try {
              raw = atob(encoded);
            } catch {
              throw new EngineError([
                diagnostic(
                  "ASSET_BYTES_INVALID",
                  "/assets",
                  `Malformed packaged data for ${asset.id}`
                )
              ]);
            }
            const bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
            if (await sha256(bytes) !== asset.file.sha256)
              throw new EngineError([
                diagnostic(
                  "ASSET_HASH_MISMATCH",
                  "/assets",
                  `Resource bytes do not match ${asset.id}@${asset.version}`
                )
              ]);
            const url = URL.createObjectURL(
              new Blob([bytes], { type: asset.file.mimeType })
            );
            objectUrls.push(url);
            const image = new Image();
            image.src = url;
            try {
              await image.decode();
            } catch {
              throw new EngineError([
                diagnostic(
                  "ASSET_DECODE_FAILED",
                  "/assets",
                  `Cannot decode ${asset.id}`
                )
              ]);
            }
            if (image.naturalWidth !== asset.intrinsic.width || image.naturalHeight !== asset.intrinsic.height)
              throw new EngineError([
                diagnostic(
                  "ASSET_DIMENSION_MISMATCH",
                  "/assets",
                  `Dimensions do not match ${asset.id}`
                )
              ]);
            const canvas = document.createElement("canvas");
            canvas.width = image.naturalWidth;
            canvas.height = image.naturalHeight;
            const context = canvas.getContext("2d", { willReadFrequently: true });
            context.drawImage(image, 0, 0);
            const pixels = context.getImageData(
              0,
              0,
              canvas.width,
              canvas.height
            ).data;
            let left = canvas.width, top = canvas.height, right = -1, bottom = -1;
            for (let y = 0; y < canvas.height; y++)
              for (let x = 0; x < canvas.width; x++) {
                if (pixels[(y * canvas.width + x) * 4 + 3] > 0) {
                  left = Math.min(left, x);
                  top = Math.min(top, y);
                  right = Math.max(right, x);
                  bottom = Math.max(bottom, y);
                }
              }
            const measured = {
              x: left,
              y: top,
              width: right - left + 1,
              height: bottom - top + 1
            };
            const declared = asset.alphaBounds;
            if (Object.keys(measured).some((k) => measured[k] !== declared[k]))
              throw new EngineError([
                diagnostic(
                  "ASSET_ALPHA_BOUNDS_MISMATCH",
                  "/assets",
                  `alphaBounds do not match ${asset.id}`
                )
              ]);
            canvas.width = canvas.height = 0;
            images.set(asset.id, image);
          }
          return {
            images,
            release() {
              objectUrls.forEach((url) => URL.revokeObjectURL(url));
            }
          };
        } catch (error) {
          objectUrls.forEach((url) => URL.revokeObjectURL(url));
          throw error;
        }
      }
      function fontPresent(family) {
        const ctx = document.createElement("canvas").getContext("2d");
        const probe = "\u77E5\u8BC6\u79D1\u666E \u6C49\u5B57 \u6C34\u6EF4 WQilm 0123456789";
        return ["monospace", "serif"].some((fallback) => {
          ctx.font = `48px ${fallback}`;
          const baseline = ctx.measureText(probe).width;
          ctx.font = `48px "${family}", ${fallback}`;
          return Math.abs(ctx.measureText(probe).width - baseline) > 0.1;
        });
      }
      module.exports = { sha256, loadResources, fontPresent };
    }
  });

  // src/geometry.cjs
  var require_geometry = __commonJS({
    "src/geometry.cjs"(exports, module) {
      "use strict";
      var { curve, matrix, imagePlacement } = require_timeline();
      var { registry } = require_registry();
      function transform(m, p) {
        return {
          x: m[0] * p.x + m[2] * p.y + m[4],
          y: m[1] * p.x + m[3] * p.y + m[5]
        };
      }
      function corners(rect, m = [1, 0, 0, 1, 0, 0]) {
        return [
          { x: rect.x, y: rect.y },
          { x: rect.x + rect.width, y: rect.y },
          { x: rect.x + rect.width, y: rect.y + rect.height },
          { x: rect.x, y: rect.y + rect.height }
        ].map((p) => transform(m, p));
      }
      function bounds(points) {
        const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
        return {
          x: Math.min(...xs),
          y: Math.min(...ys),
          width: Math.max(...xs) - Math.min(...xs),
          height: Math.max(...ys) - Math.min(...ys)
        };
      }
      function textRects(element, stage, width) {
        if (!element.firstChild) return [];
        const range = document.createRange();
        range.selectNodeContents(element);
        const origin = stage.getBoundingClientRect(), scale = origin.width / width;
        return [...range.getClientRects()].map((r) => ({
          x: (r.left - origin.left) / scale,
          y: (r.top - origin.top) / scale,
          width: r.width / scale,
          height: r.height / scale
        }));
      }
      function geometry(node, state, compiled, element, stage) {
        const common = {
          target: { nodeId: node.id, part: "self" },
          coordinateSpace: "canvas",
          opacity: state.opacity
        };
        if (node.type === "image") {
          const asset = compiled.assets.get(node.assetRef.id), placement = imagePlacement(node, asset), m = matrix(node, state, asset);
          const localRect = {
            x: 0,
            y: 0,
            width: node.box.width,
            height: node.box.height
          }, polygon = corners(localRect, m);
          const a = asset.alphaBounds, visibleRect = {
            x: placement.x + a.x * placement.scale,
            y: placement.y + a.y * placement.scale,
            width: a.width * placement.scale,
            height: a.height * placement.scale
          };
          const visiblePolygon = corners(visibleRect, m);
          return {
            ...common,
            localRect,
            localToCanvas: m,
            polygons: [polygon],
            rects: [bounds(polygon)],
            resourceRef: node.assetRef,
            anchor: { ...state.position },
            visibleContent: {
              meaning: "alphaBounds support rectangle, not pixel mask or semantic part",
              polygons: [visiblePolygon],
              rects: [bounds(visiblePolygon)]
            }
          };
        }
        if (node.type === "text") {
          const rects = textRects(element, stage, compiled.source.canvas.width);
          return {
            ...common,
            localRect: { x: 0, y: 0, width: node.box.width, height: node.box.height },
            localToCanvas: [1, 0, 0, 1, node.box.x, node.box.y],
            polygons: rects.map((r2) => corners(r2)),
            rects,
            layoutBox: node.box,
            text: state.text
          };
        }
        if (node.type === "path") {
          const points = compiled.paths.get(node.pathId).points;
          const polyline = Array.from(
            { length: registry.limits.pathSamples + 1 },
            (_, i) => curve(points, state.progress * i / registry.limits.pathSamples)
          );
          const r2 = bounds(points);
          return {
            ...common,
            localRect: r2,
            localToCanvas: [1, 0, 0, 1, 0, 0],
            polygons: [corners(r2)],
            rects: [r2],
            boundsMeaning: "control-point hull; conservative, without stroke expansion",
            sampledPolyline: polyline,
            progress: state.progress
          };
        }
        const r = node.box;
        return {
          ...common,
          localRect: { x: 0, y: 0, width: r.width, height: r.height },
          localToCanvas: [1, 0, 0, 1, r.x, r.y],
          polygons: [corners(r)],
          rects: [r],
          circle: {
            center: { x: r.x + r.width / 2, y: r.y + r.height / 2 },
            radius: Math.max(0, (Math.min(r.width, r.height) - node.strokeWidth) / 2)
          }
        };
      }
      module.exports = { transform, corners, bounds, textRects, geometry };
    }
  });

  // src/renderer.cjs
  var require_renderer = __commonJS({
    "src/renderer.cjs"(exports, module) {
      "use strict";
      var { compile } = require_compiler();
      var { EngineError, diagnostic, registry } = require_registry();
      var { evaluate, curve, imagePlacement, matrix } = require_timeline();
      var { sha256, loadResources, fontPresent } = require_resources();
      var { geometry, textRects } = require_geometry();
      var SceneRenderer = class {
        constructor(host, compiled) {
          this.host = host;
          this.compiled = compiled;
          this.textElements = /* @__PURE__ */ new Map();
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
            background: `radial-gradient(ellipse at 82% 50%,${scene.style.background.rightGlow},transparent 48%),radial-gradient(ellipse at 15% 70%,${scene.style.background.leftGlow},transparent 42%),${scene.style.background.base}`
          });
          let canvasLayer = null;
          for (const node of compiled.nodes) {
            if (node.type === "text") {
              canvasLayer = null;
              const element = document.createElement("div"), role = scene.style.textRoles[node.role];
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
                overflowWrap: "anywhere"
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
                  pointerEvents: "none"
                });
                const context = canvas.getContext("2d", { willReadFrequently: true });
                if (!context)
                  throw new EngineError([
                    diagnostic("RENDERER_UNAVAILABLE", "/", "Canvas 2D unavailable")
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
                "Requested system font was not detected; no silent fallback"
              )
            ]);
          const errors = [];
          for (const node of this.compiled.nodes) {
            if (node.type !== "text") continue;
            const element = this.textElements.get(node.id), role = this.compiled.source.style.textRoles[node.role];
            const variants = node.content.kind === "static" ? [node.content.text] : [...new Set(this.compiled.source.beats.map((b) => b.screenText))];
            for (const text of variants) {
              element.textContent = text;
              const rects = textRects(
                element,
                this.root,
                this.compiled.source.canvas.width
              );
              const rows = new Set(rects.map((r) => Math.round(r.y * 10) / 10));
              const b = node.box;
              if (rows.size > role.maxLines || rects.some(
                (r) => r.x < b.x - 0.5 || r.x + r.width > b.x + b.width + 0.5 || r.y < b.y - 0.5 || r.y + r.height > b.y + b.height + 0.5
              )) {
                errors.push(
                  diagnostic(
                    "CONTENT_CAPACITY_EXCEEDED",
                    "/nodes/" + node.id,
                    `Text exceeds ${role.maxLines} lines or its box; revise content/layout without shrinking font`,
                    node.id
                  )
                );
                break;
              }
            }
          }
          if (errors.length) throw new EngineError(errors);
          this.fingerprint = await sha256(
            new TextEncoder().encode(this.compiled.canonicalInput)
          );
          this.renderAt(0);
        }
        renderAt(timeMs) {
          if (!this.resources)
            throw new EngineError([
              diagnostic("NOT_READY", "/", "Resource preparation incomplete")
            ]);
          const state = evaluate(this.compiled, timeMs);
          for (const node of this.compiled.nodes) {
            if (node.type !== "text") continue;
            const element = this.textElements.get(node.id), s = state.nodes[node.id];
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
                const asset = this.compiled.assets.get(node.assetRef.id), p = imagePlacement(node, asset);
                ctx.setTransform(...matrix(node, s, asset));
                ctx.drawImage(
                  this.resources.images.get(asset.id),
                  p.x,
                  p.y,
                  p.width,
                  p.height
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
                    s.progress * i / registry.limits.pathSamples
                  );
                  i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y);
                }
                ctx.stroke();
              }
              if (node.type === "ring") {
                const b = node.box, x = b.x + b.width / 2, y = b.y + b.height / 2, r = Math.max(
                  0,
                  (Math.min(b.width, b.height) - node.strokeWidth) / 2
                );
                ctx.strokeStyle = ctx.fillStyle = this.compiled.source.style.colors[node.colorRole];
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
          if (!node || target.part !== "self" || Object.keys(target).some((k) => !["nodeId", "part"].includes(k)))
            throw new EngineError([
              diagnostic(
                "MISSING_TARGET",
                "/target",
                "Only registered node self targets are supported"
              )
            ]);
          const state = this.renderAt(timeMs);
          return geometry(
            node,
            state.nodes[node.id],
            this.compiled,
            this.textElements.get(node.id),
            this.root
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
                fontProbe: "measurement-based; per-glyph coverage not proven"
              }
            }
          });
        }
        dispose() {
          this.root.remove();
          this.resources?.release();
        }
      };
      var SceneController = class {
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
                  "A newer scene request replaced this load"
                )
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
              diagnostic("NOT_READY", "/", "No accepted scene loaded")
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
      };
      module.exports = { SceneController };
    }
  });

  // src/browser-entry.cjs
  var require_browser_entry = __commonJS({
    "src/browser-entry.cjs"() {
      var { registry, EngineError } = require_registry();
      var { compile } = require_compiler();
      var { evaluate } = require_timeline();
      var { SceneController } = require_renderer();
      window.HPSE1 = { registry, EngineError, compile, evaluate, SceneController };
    }
  });
  require_browser_entry();
})();
