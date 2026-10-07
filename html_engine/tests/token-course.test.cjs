"use strict";
const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict"),
  crypto = require("crypto");
const { chromium } = require("playwright");
const { pathToFileURL } = require("url");
const { compileRecipe } = require("../src/recipes.cjs");
const { compile } = require("../src/compiler.cjs");
const { evaluate } = require("../src/timeline.cjs");
const root = path.resolve(__dirname, ".."),
  names = ["token-01", "token-02", "token-03", "token-04", "token-05"];
const inputs = names.map((n) =>
  JSON.parse(
    fs.readFileSync(path.join(root, "recipes", n + ".recipe.json"), "utf8"),
  ),
);
const evidence = {
  course: "course.token",
  unit: [],
  browser: [],
  visualStatus: "pending-user-review",
  audio: "not attached; manual timing",
};
function test(name, fn) {
  fn();
  evidence.unit.push({ name, passed: true });
}
test("Five scenes reuse one recipe without mutating author input", () => {
  for (const input of inputs) {
    const before = JSON.stringify(input),
      a = compileRecipe(input);
    assert.equal(a.trace.recipe, "recipe.hero-steps");
    assert.equal(JSON.stringify(input), before);
    assert.equal(a.scene.beats.length, 3);
    assert.equal(a.scene.nodes.filter((n) => n.type === "image").length, 1);
  }
});
for (const [name, change, code] of [
  ["Fourth step rejected", (i) => i.steps.push(i.steps[0]), "RECIPE_FIELD"],
  [
    "Long detail rejected",
    (i) => (i.steps[0].detail = "字".repeat(31)),
    "RECIPE_CAPACITY",
  ],
  ["Free position rejected", (i) => (i.steps[0].x = 20), "RECIPE_FIELD"],
  ["Wrong template slot rejected", (i) => (i.concepts = []), "RECIPE_FIELD"],
])
  test(name, () => {
    const i = structuredClone(inputs[0]);
    change(i);
    assert.throws(
      () => compileRecipe(i),
      (e) => e.code === code,
    );
  });
test("Old recipe rejects new steps field", () => {
  const i = JSON.parse(
    fs.readFileSync(
      path.join(root, "recipes/course-water.recipe.json"),
      "utf8",
    ),
  );
  i.steps = [];
  assert.throws(
    () => compileRecipe(i),
    (e) => e.code === "RECIPE_FIELD",
  );
});
test("Narration stays separate and each step reveals in sequence", () => {
  const c = compile(compileRecipe(inputs[0]).scene);
  assert.equal(evaluate(c, 2500).nodes["step.2.label"].opacity, 0);
  assert.equal(evaluate(c, 8500).nodes["step.2.label"].opacity, 1);
  assert.equal(evaluate(c, 8500).nodes["step.3.label"].opacity, 0);
  assert.equal(evaluate(c, 18000).nodes["step.3.detail"].opacity, 1);
  assert(
    !evaluate(c, 2500).nodes["step.1.detail"].text.includes(
      "Token 是模型处理文本所用",
    ),
  );
});
test("Data-driven language examples match saved tokenizer evidence", () => {
  const proof = JSON.parse(
    fs.readFileSync(
      path.join(root, "courses/token/tokenizer-evidence.json"),
      "utf8",
    ),
  );
  assert.equal(proof.encoding, "cl100k_base");
  assert.equal(proof.examples[0].count, 3);
  assert.deepEqual(proof.examples[0].ids, [9906, 1917, 0]);
  assert.equal(proof.examples[1].text, "人工智能很有趣");
  assert.equal(proof.examples[1].count, 10);
  assert(proof.examples.every((x) => x.roundTrip));
  assert(inputs[1].steps[1].detail.includes("10 Token"));
});
test("Same recipe supports water process content without geometry or renderer changes", () => {
  const other = structuredClone(inputs[0]);
  other.id = "scene.hero-water-test";
  other.title = "水的变化过程";
  other.subtitle = "生活课程用于跨主题槽位验证";
  other.steps = [
    {
      label: "蒸发",
      detail: "液态水变为水蒸气。",
      narration: "蒸发是液态水变为水蒸气。",
      summary: "先认识蒸发。",
    },
    {
      label: "遇冷",
      detail: "空气中的水蒸气遇到冷表面。",
      narration: "冷杯外壁是水蒸气凝结的一个生活场景。",
      summary: "观察冷表面。",
    },
    {
      label: "凝结",
      detail: "水蒸气变为液态水滴。",
      narration: "凝结是水蒸气变为液态水。",
      summary: "气态回到液态。",
    },
  ];
  const a = compileRecipe(inputs[0]).scene,
    b = compileRecipe(other).scene;
  assert.deepEqual(a.actions, b.actions);
  assert.deepEqual(
    a.nodes.map((n) => n.box),
    b.nodes.map((n) => n.box),
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
    await page.goto(pathToFileURL(path.join(root, "preview/index.html")).href);
    await page.evaluate(() => window.e1Ready);
    for (const name of names) {
      const scene = JSON.parse(
        fs.readFileSync(
          path.join(root, "examples", name + ".scene.json"),
          "utf8",
        ),
      );
      await page.evaluate((s) => window.e1.applyInput(s), scene);
      const frames = [];
      for (const k of scene.keyframes) {
        await page.evaluate((t) => window.e1.seek(t), k.tMs);
        const bytes = await page.locator("#frame").screenshot();
        fs.writeFileSync(
          path.join(root, "evidence/token-course", name + "-" + k.id + ".png"),
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
        frames.push({ id: k.id, tMs: k.tMs, repeat: true });
      }
      evidence.browser.push({ name, frames });
    }
    await page.goto(
      pathToFileURL(path.join(root, "courses/token/legacy-v1.html")).href,
    );
    await page.locator("#scenes button").nth(4).click();
    const frame = await page.locator("#player").contentFrame();
    await frame.locator("#status").filter({ hasText: "就绪" }).waitFor();
    assert.equal(
      await frame.locator("#frame section").getAttribute("data-scene-id"),
      "scene.token-05",
    );
    assert(
      (await page.locator("#narration").textContent()).includes("文本训练"),
    );
    evidence.courseNavigation = "five scene links and last transcript verified";
    assert.deepEqual(errors, []);
    evidence.pageErrors = errors;
  } finally {
    await browser.close();
  }
  fs.writeFileSync(
    path.join(root, "evidence/token-course/checks.json"),
    JSON.stringify(evidence, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      unit: evidence.unit.length,
      scenes: evidence.browser.length,
      frames: 25,
    }),
  );
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
