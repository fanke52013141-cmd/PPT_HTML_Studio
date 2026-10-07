"use strict";
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const Ajv = require("ajv/dist/2020");
const standalone = require("ajv/dist/standalone");
const esbuild = require("esbuild");
const { PNG } = require("pngjs");
const root = path.resolve(__dirname, "..");

async function main() {
  const schema = JSON.parse(
    fs.readFileSync(path.join(root, "scene.schema.json"), "utf8"),
  );
  const ajv = new Ajv({
    allErrors: true,
    strict: true,
    code: { source: true },
    strictNumbers: true,
  });
  const validate = ajv.compile(schema);
  const generated = path.join(root, "src/generated");
  fs.mkdirSync(generated, { recursive: true });
  fs.writeFileSync(
    path.join(generated, "validate-scene.cjs"),
    "// Generated from scene.schema.json with Ajv. Do not edit.\n" +
      standalone(ajv, validate),
  );
  const { compile } = require("../src/compiler.cjs");
  const scenes = [
    "paper-plane",
    "cloud-drift",
    "course-water",
    "course-everyday",
    "e2-cloud",
  ].map((name) =>
    JSON.parse(
      fs.readFileSync(
        path.join(root, "examples", name + ".scene.json"),
        "utf8",
      ),
    ),
  );
  scenes.forEach(compile);
  const resources = {},
    audit = [];
  const seen = new Set();
  for (const scene of scenes) {
    for (const asset of scene.assets) {
      const file = path.resolve(root, asset.file.path);
      const assetDirectory = fs.realpathSync(path.join(root, "assets"));
      const actual = fs.realpathSync(file);
      const relative = path.relative(assetDirectory, actual);
      if (relative.startsWith("..") || path.isAbsolute(relative))
        throw new Error("Asset escapes package: " + asset.file.path);
      const bytes = fs.readFileSync(actual),
        hash = crypto.createHash("sha256").update(bytes).digest("hex");
      if (hash !== asset.file.sha256)
        throw new Error("ASSET_HASH_MISMATCH " + asset.id);
      if (
        bytes.length < 24 ||
        bytes.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a"
      )
        throw new Error("Expected PNG");
      if (
        bytes.readUInt32BE(16) !== asset.intrinsic.width ||
        bytes.readUInt32BE(20) !== asset.intrinsic.height
      )
        throw new Error("ASSET_DIMENSION_MISMATCH " + asset.id);
      const png = PNG.sync.read(bytes);
      let left = png.width,
        top = png.height,
        right = -1,
        bottom = -1;
      for (let y = 0; y < png.height; y++)
        for (let x = 0; x < png.width; x++) {
          if (png.data[(y * png.width + x) * 4 + 3] > 0) {
            left = Math.min(left, x);
            top = Math.min(top, y);
            right = Math.max(right, x);
            bottom = Math.max(bottom, y);
          }
        }
      const actualBounds = {
        x: left,
        y: top,
        width: right - left + 1,
        height: bottom - top + 1,
      };
      if (JSON.stringify(actualBounds) !== JSON.stringify(asset.alphaBounds))
        throw new Error("ASSET_ALPHA_BOUNDS_MISMATCH " + asset.id);
      resources[asset.file.path] = bytes.toString("base64");
      if (!seen.has(asset.file.path)) {
        seen.add(asset.file.path);
        audit.push({
          path: asset.file.path,
          hash,
          sizeBytes: bytes.length,
          intrinsic: asset.intrinsic,
          alphaBounds: actualBounds,
        });
      }
    }
  }
  const literal = JSON.stringify({ scenes, resources })
    .replace(/</g, "\\u003c")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
  fs.writeFileSync(
    path.join(root, "preview/fixtures.js"),
    "// Generated from examples/*.scene.json and assets. Do not edit.\nwindow.HPSE1Fixtures = " +
      literal +
      ";\n",
  );
  await esbuild.build({
    entryPoints: [path.join(root, "src/browser-entry.cjs")],
    bundle: true,
    platform: "browser",
    format: "iife",
    outfile: path.join(root, "preview/engine.js"),
    minify: false,
    legalComments: "inline",
  });
  fs.writeFileSync(
    path.join(root, "evidence/build.json"),
    JSON.stringify(
      {
        engineVersion: "0.1.0",
        schemaSha256: crypto
          .createHash("sha256")
          .update(fs.readFileSync(path.join(root, "scene.schema.json")))
          .digest("hex"),
        sceneCount: scenes.length,
        assets: audit,
        validator: "Ajv " + require("ajv/package.json").version,
        bundler: "esbuild " + esbuild.version,
        imageAudit: "pngjs " + require("pngjs/package.json").version,
      },
      null,
      2,
    ) + "\n",
  );
  console.log("Built validated scenes, audited resources and browser engine.");
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
