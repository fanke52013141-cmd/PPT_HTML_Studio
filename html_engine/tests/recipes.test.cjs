"use strict";
const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict"),
  crypto = require("crypto");
const { chromium } = require("playwright");
const { pathToFileURL } = require("url");
const root = path.resolve(__dirname, "..");
const { compileRecipe } = require(root + "/src/recipes.cjs");
const { compile } = require(root + "/src/compiler.cjs");
const { evaluate } = require(root + "/src/timeline.cjs");
const names = ["course-water", "course-everyday", "e2-cloud"];
const inputs = names.map((n) =>
  JSON.parse(fs.readFileSync(root + "/recipes/" + n + ".recipe.json", "utf8")),
);
const evidence = {
  scope: "E2 recipes 0.1.0",
  unit: [],
  browser: [],
  visualStatus: "pending-user-review",
};
function test(name, fn) {
  fn();
  evidence.unit.push({ name, passed: true });
}
test("Content does not mutate; shared template for two course inputs", () => {
  for (const i of inputs) {
    const before = JSON.stringify(i);
    compileRecipe(i);
    assert.equal(before, JSON.stringify(i));
  }
  assert.equal(
    compileRecipe(inputs[0]).trace.recipe,
    compileRecipe(inputs[1]).trace.recipe,
  );
});
for (const [name, change, code] of [
  ["Long title", (i) => (i.title = "水".repeat(19)), "RECIPE_CAPACITY"],
  ["Unknown layout override", (i) => (i.box = { x: 0 }), "RECIPE_FIELD"],
  ["Unknown version", (i) => (i.version = "9"), "RECIPE_VERSION"],
  ["Missing slot", (i) => i.concepts.pop(), "RECIPE_FIELD"],
  [
    "Asset traversal",
    (i) => (i.concepts[0].asset = "../x.png"),
    "RECIPE_ASSET",
  ],
])
  test(name, () => {
    const i = structuredClone(inputs[0]);
    change(i);
    assert.throws(
      () => compileRecipe(i),
      (e) => e.code === code,
    );
  });
test("Asset swap keeps object identity and motion", () => {
  const first = compileRecipe(inputs[2]).scene,
    other = structuredClone(inputs[2]);
  other.mainAsset = "assets/cloud-small.png";
  const second = compileRecipe(other).scene;
  assert.deepEqual(first.actions, second.actions);
  assert.deepEqual(
    evaluate(compile(first), 4000).nodes["main.object"],
    evaluate(compile(second), 4000).nodes["main.object"],
  );
});
const { diagnoseOverlap } = require("../src/recipe-diagnostics.cjs");
const { audit, crop } = require("../scripts/asset-tool.cjs");
test("Missing local resource has slot diagnostic", () => {
  const i = structuredClone(inputs[0]);
  i.concepts[0].asset = "assets/not-present.png";
  assert.throws(
    () => compileRecipe(i),
    (e) => e.code === "RECIPE_ASSET",
  );
});
test("Foreground occlusion warning and invisible exclusion", () => {
  const a = {
      opacity: 1,
      target: { nodeId: "subject" },
      rects: [{ x: 0, y: 0, width: 10, height: 10 }],
    },
    b = {
      opacity: 1,
      target: { nodeId: "foreground" },
      rects: [{ x: 5, y: 5, width: 10, height: 10 }],
    };
  assert.equal(diagnoseOverlap(a, b)[0].code, "POSSIBLE_FOREGROUND_OCCLUSION");
  assert.deepEqual(diagnoseOverlap(a, { ...b, opacity: 0 }), []);
});
test("Immutable fixed rectangle extraction and overwrite rejection", () => {
  const output = "assets/e2-crop-" + crypto.randomUUID() + ".png";
  const manifest = {
    version: "0.1.0",
    source: "assets/cloud-small-v2.png",
    slots: [
      {
        id: "cloud",
        output,
        rect: { x: 100, y: 100, width: 900, height: 900 },
      },
    ],
  };
  try {
    const result = crop(manifest);
    assert.equal(result[0].resource.intrinsic.width, 900);
    assert.deepEqual(result[0].rect, manifest.slots[0].rect);
    assert.throws(() => crop(manifest), /CROP_OUTPUT_EXISTS/);
  } finally {
    if (fs.existsSync(path.join(root, output)))
      fs.unlinkSync(path.join(root, output));
  }
  assert.throws(
    () =>
      crop({
        ...manifest,
        slots: [
          { id: "bad", output, rect: { x: -1, y: 0, width: 10, height: 10 } },
        ],
      }),
    /CROP_RECT/,
  );
});
async function main() {
  const browser = await chromium.launch({
    executablePath:
      process.env.CHROME_PATH ||
      "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
    headless: true,
    args: ["--disable-gpu"],
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1600, height: 1120 },
      deviceScaleFactor: 1,
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(pathToFileURL(root + "/preview/index.html").href);
    await page.evaluate(() => window.e1Ready);
    for (const name of names) {
      const scene = JSON.parse(
        fs.readFileSync(root + "/examples/" + name + ".scene.json", "utf8"),
      );
      await page.evaluate((s) => window.e1.applyInput(s), scene);
      const frames = [];
      for (const k of scene.keyframes) {
        await page.evaluate((t) => window.e1.seek(t), k.tMs);
        const bytes = await page.locator("#frame").screenshot();
        fs.writeFileSync(
          root + "/evidence/e2/" + name + "-" + k.id + ".png",
          bytes,
        );
        await page.evaluate((t) => window.e1.seek(t), scene.durationMs);
        await page.evaluate((t) => window.e1.seek(t), k.tMs);
        assert.equal(
          crypto
            .createHash("sha256")
            .update(await page.locator("#frame").screenshot())
            .digest("hex"),
          crypto.createHash("sha256").update(bytes).digest("hex"),
        );
        frames.push({ keyframe: k.id, timeMs: k.tMs, repeat: true });
      }
      evidence.browser.push({ name, frames });
    }
    const water = JSON.parse(
      fs.readFileSync(root + "/examples/course-water.scene.json", "utf8"),
    );
    await page.evaluate((s) => window.e1.applyInput(s), water);
    const invalid = structuredClone(water);
    invalid.nodes.find((n) => n.id === "page.title").content.text = "水".repeat(
      70,
    );
    await assert.rejects(
      page.evaluate((s) => window.e1.applyInput(s), invalid),
    );
    assert.equal(
      await page.evaluate(
        () => window.e1.controller.current.compiled.source.id,
      ),
      water.id,
    );
    const missing = structuredClone(water);
    missing.assets[0].file.path = "assets/missing.png";
    await assert.rejects(
      page.evaluate((s) => window.e1.applyInput(s), missing),
    );
    const geometries = await page.evaluate(() => {
      window.e1.seek(12000);
      return [
        "left.illustration",
        "left.name",
        "right.illustration",
        "right.name",
      ].map((id) =>
        window.e1.controller.getGeometry({ nodeId: id, part: "self" }, 12000),
      );
    });
    evidence.geometry = geometries;
    const cloud = JSON.parse(
      fs.readFileSync(root + "/examples/e2-cloud.scene.json", "utf8"),
    );
    await page.evaluate((s) => window.e1.applyInput(s), cloud);
    const g = await page.evaluate(() => {
      window.e1.seek(4000);
      return ["main.object", "cloud.front"].map((id) =>
        window.e1.controller.getGeometry({ nodeId: id, part: "self" }, 4000),
      );
    });
    evidence.occlusion = {
      kind: "conservative-AABB-warning",
      diagnostics: diagnoseOverlap(g[0], g[1]),
      limitations: "bounding boxes, not pixel occlusion",
    };
    assert.deepEqual(errors, []);
    evidence.pageErrors = errors;
  } finally {
    await browser.close();
  }
  fs.writeFileSync(
    root + "/evidence/e2/checks.json",
    JSON.stringify(evidence, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      unit: evidence.unit.length,
      scenes: evidence.browser.length,
    }),
  );
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
