"use strict";
const fs = require("fs"),
  path = require("path"),
  crypto = require("crypto");
const Ajv = require("ajv/dist/2020"),
  standalone = require("ajv/dist/standalone");
const esbuild = require("esbuild"),
  { PNG } = require("pngjs");
const root = __dirname,
  project = path.resolve(root, "../..");
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));
const folder = (name) =>
  fs
    .readdirSync(path.join(root, name))
    .filter((p) => p.endsWith(".json"))
    .sort()
    .map((p) => read(`${name}/${p}`));

async function main() {
  const ajv = new Ajv({
    strict: true,
    allErrors: true,
    code: { source: true },
  });
  ajv.addSchema(read("schema.json"));
  fs.writeFileSync(
    path.join(root, "generated/validators.cjs"),
    "// Generated; edit schema.json and rebuild.\n" +
      standalone(ajv, {
        scene: "hps.visual.v1#/$defs/scene",
        theme: "hps.visual.v1#/$defs/theme",
        layout: "hps.visual.v1#/$defs/layout",
        template: "hps.visual.v1#/$defs/template",
        assetRecords: "hps.visual.v1#/$defs/assetRecords",
      }),
  );
  const { compile, validate } = require("./compiler.cjs");
  const records = read("assets.json");
  validate("assetRecords", records);
  if (new Set(records.map((a) => a.id)).size !== records.length)
    throw new Error("Duplicate asset id");
  const pack = {},
    assets = [];
  for (const record of records) {
    const { id, version, path: relative, anchors } = record;
    if (new Set(anchors.map((a) => a.id)).size !== anchors.length)
      throw new Error("Duplicate anchor id");
    const actual = fs.realpathSync(path.join(project, relative));
    if (!actual.startsWith(fs.realpathSync(project) + path.sep))
      throw new Error("Asset escapes project");
    const bytes = fs.readFileSync(actual);
    if (bytes.length > 8 * 1024 * 1024)
      throw new Error("Asset byte budget exceeded");
    const hash = crypto.createHash("sha256").update(bytes).digest("hex");
    if (hash !== record.sha256) throw new Error("ASSET_HASH_MISMATCH: " + id);
    const png = PNG.sync.read(bytes);
    if (png.width * png.height > 16e6)
      throw new Error("Asset pixel budget exceeded");
    let x = png.width,
      y = png.height,
      right = -1,
      bottom = -1;
    for (let py = 0; py < png.height; py++)
      for (let px = 0; px < png.width; px++)
        if (png.data[(py * png.width + px) * 4 + 3] > 0) {
          x = Math.min(x, px);
          y = Math.min(y, py);
          right = Math.max(right, px);
          bottom = Math.max(bottom, py);
        }
    if (
      right < 0 ||
      anchors.some(
        (a) =>
          a.x >= png.width ||
          a.y >= png.height ||
          !png.data[(a.y * png.width + a.x) * 4 + 3],
      )
    )
      throw new Error("Invalid asset anchor");
    assets.push({
      id,
      version,
      file: { path: relative, mimeType: "image/png", sha256: hash },
      intrinsic: { width: png.width, height: png.height },
      alphaBounds: { x, y, width: right - x + 1, height: bottom - y + 1 },
      anchors: anchors.map((a) => ({
        id: a.id,
        x: a.x / png.width,
        y: a.y / png.height,
      })),
    });
    pack[relative] = bytes.toString("base64");
  }
  const catalog = {
    themes: folder("themes"),
    layouts: folder("layouts"),
    templates: folder("templates"),
    assets,
  };
  const scenes = folder("scenes");
  for (const items of [catalog.themes, catalog.layouts, catalog.templates, scenes]) {
    if (new Set(items.map((v) => `${v.id}@${v.version}`)).size !== items.length)
      throw new Error("Duplicate registered definition");
  }
  catalog.themes.forEach((v) => validate("theme", v));
  catalog.layouts.forEach((v) => validate("layout", v));
  catalog.templates.forEach((v) => validate("template", v));
  scenes.forEach((s) => compile(s, catalog));
  const data = { catalog, scenes, pack };
  fs.writeFileSync(
    path.join(root, "generated/catalog.json"),
    JSON.stringify(catalog, null, 2) + "\n",
  );
  fs.writeFileSync(
    path.join(root, "preview/data.js"),
    "// Generated from registered source definitions.\nwindow.VisualData=" +
      JSON.stringify(data).replace(/</g, "\\u003c") +
      ";\n",
  );
  await esbuild.build({
    entryPoints: [path.join(root, "player.cjs")],
    bundle: true,
    platform: "browser",
    outfile: path.join(root, "preview/player.js"),
    minify: true,
    legalComments: "none",
  });
  console.log(
    JSON.stringify({
      scenes: scenes.length,
      themes: catalog.themes.length,
      layouts: catalog.layouts.length,
      newImageGenerations: 0,
    }),
  );
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
