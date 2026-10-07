"use strict";
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { PNG } = require("pngjs");
const { compile } = require("./compiler.cjs");
const catalog = require("../recipes/catalog.json");
const { compileHeroSteps } = require("./hero-steps.cjs");
const root = path.resolve(__dirname, "..");
function fail(code, field, message) {
  const error = new Error(`${code} ${field}: ${message}`);
  error.code = code;
  error.field = field;
  throw error;
}
function keys(value, allowed, field) {
  if (!value || typeof value !== "object" || Array.isArray(value))
    fail("RECIPE_FIELD", field, "expected object");
  for (const key of Object.keys(value))
    if (!allowed.includes(key))
      fail("RECIPE_FIELD", field + "." + key, "unknown field");
}
function text(value, limit, field) {
  if (typeof value !== "string" || !value.trim() || [...value].length > limit)
    fail(
      "RECIPE_CAPACITY",
      field,
      `required text; maximum ${limit} code points`,
    );
  return value;
}
function asset(file, id) {
  if (typeof file !== "string" || !/^assets\/[a-zA-Z0-9._-]+\.png$/.test(file))
    fail("RECIPE_ASSET", id, "local PNG required");
  let actual;
  try {
    actual = fs.realpathSync(path.join(root, file));
  } catch {
    fail("RECIPE_ASSET", id, "missing local asset: " + file);
  }
  const base = fs.realpathSync(path.join(root, "assets"));
  if (path.dirname(actual) !== base)
    fail("RECIPE_ASSET", id, "asset must stay in package");
  const bytes = fs.readFileSync(actual);
  if (
    bytes.length < 24 ||
    bytes.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a" ||
    bytes.readUInt32BE(16) * bytes.readUInt32BE(20) > 16000000
  )
    fail("RECIPE_ASSET", id, "invalid PNG or pixel budget");
  const png = PNG.sync.read(bytes);
  let x = png.width,
    y = png.height,
    right = -1,
    bottom = -1;
  for (let row = 0; row < png.height; row++)
    for (let col = 0; col < png.width; col++)
      if (png.data[(row * png.width + col) * 4 + 3]) {
        x = Math.min(x, col);
        y = Math.min(y, row);
        right = Math.max(right, col);
        bottom = Math.max(bottom, row);
      }
  if (right < 0) fail("RECIPE_ASSET", id, "empty transparent asset");
  return {
    id: "asset." + path.basename(file, ".png"),
    version: "0.1.0",
    kind: "image",
    file: {
      path: file,
      mimeType: "image/png",
      sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
    },
    intrinsic: { width: png.width, height: png.height },
    alphaBounds: { x, y, width: right - x + 1, height: bottom - y + 1 },
    anchors: [{ id: "frame-center", x: 0.5, y: 0.5 }],
    provenance: {
      kind: "generated",
      source:
        "E2 asset manifest; original generation and quality review retained",
    },
    quality: "conditional-experiment",
  };
}
function compileRecipe(input) {
  keys(
    input,
    [
      "format",
      "version",
      "id",
      "revision",
      "template",
      "variant",
      "title",
      "subtitle",
      "steps",
      "heroAsset",
      "concepts",
      "mainAsset",
      "narration",
      "source",
    ],
    "/",
  );
  if (input.format !== "hps.e2.recipe" || input.version !== "0.1.0")
    fail("RECIPE_VERSION", "/", "expected hps.e2.recipe 0.1.0");
  const recipe = catalog.templates.find((r) => r.id === input.template);
  if (!recipe || !recipe.variants.includes(input.variant))
    fail("RECIPE_TEMPLATE", "template", "unknown template or variant");
  text(input.title, recipe.budgets.title, "title");
  text(input.subtitle, recipe.budgets.subtitle, "subtitle");
  text(input.source, 1000, "source");
  const extraFields = {
    "recipe.dual-concept": ["concepts"],
    "recipe.open-process": ["mainAsset", "narration"],
    "recipe.hero-steps": ["heroAsset", "steps"],
  }[input.template];
  for (const field of [
    "concepts",
    "mainAsset",
    "narration",
    "heroAsset",
    "steps",
  ])
    if (input[field] !== undefined && !extraFields.includes(field))
      fail("RECIPE_FIELD", field, "field not accepted by this recipe");
  const basisName = input.variant === "drift" ? "cloud-drift" : "paper-plane";
  const basisBytes = fs.readFileSync(
    path.join(root, "examples", basisName + ".scene.json"),
  );
  if (
    crypto.createHash("sha256").update(basisBytes).digest("hex") !==
    catalog.basisSha256[basisName]
  )
    fail(
      "RECIPE_BASIS_VERSION",
      basisName,
      "template basis changed; review and version recipe before adoption",
    );
  const base = JSON.parse(basisBytes.toString("utf8"));
  base.id = input.id;
  base.revision = input.revision;
  base.title = input.title;
  if (input.template === "recipe.open-process") {
    base.nodes.find((n) => n.id === "page.title").content.text = input.title;
    base.nodes.find((n) => n.id === "page.subtitle").content.text =
      input.subtitle;
    const replacement = asset(input.mainAsset, "asset.replacement");
    if (!base.assets.some((a) => a.id === replacement.id))
      base.assets.push(replacement);
    base.nodes.find((n) => n.id === "main.object").assetRef = {
      id: replacement.id,
      version: replacement.version,
    };
    if (!Array.isArray(input.narration) || input.narration.length !== 3)
      fail("RECIPE_FIELD", "narration", "exactly three beats required");
    input.narration.forEach((b, i) => {
      keys(b, ["text", "screenText"], "narration." + i);
      base.beats[i].text = text(b.text, 1000, "narration.text");
      base.beats[i].screenText = text(b.screenText, 38, "narration.screenText");
    });
  } else if (input.template === "recipe.hero-steps") {
    compileHeroSteps(input, base, recipe, { keys, text, asset, fail });
  } else {
    if (input.narration !== undefined)
      fail("RECIPE_FIELD", "narration", "use concepts.narration");
    if (!Array.isArray(input.concepts) || input.concepts.length !== 2)
      fail("RECIPE_FIELD", "concepts", "exactly two slots required");
    base.durationMs = 12000;
    base.assets = [];
    base.nodes = [];
    base.actions = [];
    base.beats = [];
    base.style.textRoles.title.fontSize = 64;
    base.style.textRoles.caption.fontSize = 36;
    base.style.textRoles.caption.align = "left";
    const addText = (id, role, text, box, opacity = 1) =>
      base.nodes.push({
        id,
        type: "text",
        typeVersion: "0.1.0",
        zIndex: 100,
        initialOpacity: opacity,
        box,
        role,
        content: { kind: "static", text },
      });
    addText("page.title", "title", input.title, {
      x: 100,
      y: 65,
      width: 1400,
      height: 100,
    });
    addText("page.subtitle", "subtitle", input.subtitle, {
      x: 104,
      y: 175,
      width: 1390,
      height: 55,
    });
    input.concepts.forEach((c, i) => {
      keys(
        c,
        ["name", "relation", "body", "asset", "narration"],
        "concepts." + i,
      );
      for (const field of ["name", "relation", "body"])
        text(c[field], recipe.budgets[field], "concepts." + i + "." + field);
      text(c.narration, 1000, "concepts." + i + ".narration");
      const side = i ? "right" : "left",
        x = i ? 870 : 130,
        a = asset(c.asset, "asset." + side);
      if (!base.assets.some((existing) => existing.id === a.id))
        base.assets.push(a);
      base.nodes.push({
        id: side + ".illustration",
        type: "image",
        typeVersion: "0.1.0",
        zIndex: 10,
        initialOpacity: 0,
        box: { x: x + 65, y: 255, width: 450, height: 450 },
        assetRef: { id: a.id, version: a.version },
        anchorId: "frame-center",
        fit: "contain",
        rotationDeg: 0,
      });
      addText(
        side + ".name",
        "caption",
        c.name,
        { x, y: 700, width: 570, height: 58 },
        0,
      );
      addText(
        side + ".relation",
        "caption",
        c.relation,
        { x, y: 760, width: 570, height: 58 },
        0,
      );
      addText(
        side + ".body",
        "subtitle",
        c.body,
        { x, y: 815, width: 650, height: 45 },
        0,
      );
      for (const [index, part] of [
        "illustration",
        "name",
        "relation",
        "body",
      ].entries())
        base.actions.push({
          id: "show." + side + "." + part,
          type: "opacity",
          typeVersion: "0.1.0",
          target: { nodeId: side + "." + part, part: "self" },
          startMs: i * 6000 + index * 250,
          endMs: i * 6000 + index * 250 + 400,
          easing: "smoothstep",
          from: 0,
          to: 1,
        });
      base.beats.push({
        id: "beat." + side,
        startMs: i * 6000,
        endMs: (i + 1) * 6000,
        text: c.narration,
        screenText: c.body,
        targetIds: [
          side + ".illustration",
          side + ".name",
          side + ".relation",
          side + ".body",
        ],
      });
    });
    base.keyframes = [
      { id: "K0", tMs: 0, purpose: "开场" },
      { id: "K1", tMs: 1600, purpose: "左概念" },
      { id: "K2", tMs: 7600, purpose: "双概念" },
      { id: "K3", tMs: 12000, purpose: "终态" },
    ];
  }
  compile(base);
  return {
    scene: base,
    trace: {
      recipe: recipe.id,
      version: recipe.version,
      visualStatus: recipe.visualStatus,
      source: input.source,
      authorSha256: crypto
        .createHash("sha256")
        .update(JSON.stringify(input))
        .digest("hex"),
    },
  };
}
module.exports = { compileRecipe, catalog };
