"use strict";
// AC11: object-process actions — enter/exit/emphasize evaluation, boundary
// visibility (gone after exit), deterministic seek with actions, and the
// relation line tracking its target. Run: node visual/tests/actions.test.cjs
const assert = require("node:assert/strict"),
  fs = require("fs"),
  path = require("path");
const { pathToFileURL } = require("url"),
  { chromium } = require("playwright");
const { compile } = require("../compiler.cjs");
const root = path.resolve(__dirname, ".."),
  read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));
const catalog = read("generated/catalog.json"),
  scene = read("scenes/evaporation-process.json");

async function main() {
  compile(scene, catalog);
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.HPS_CHROME ||
      "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
  });
  const page = await browser.newPage({
    viewport: { width: 1648, height: 1200 },
    deviceScaleFactor: 1,
  });
  const evidence = {
    format: "hps.visual.actions.ac11",
    version: "0.1.0",
    checks: [],
  };
  try {
    await page.goto(pathToFileURL(path.join(root, "preview/index.html")).href);
    await page.waitForFunction(
      () => window.visualPlayer?.ready,
      {},
      { timeout: 15000 },
    );
    assert.equal(
      await page.evaluate((s) => window.visualPlayer.apply(s), scene),
      true,
      await page.locator("#status").innerText(),
    );
    evidence.checks.push("apply-with-exit-and-emphasize");

    const opacityOf = (id) =>
      page.evaluate(
        (t) =>
          Number(
            document.querySelector(`[data-object-id="${t}"]`)?.style.opacity,
          ),
        id,
      );
    // 进入前/在场/退出后边界：exit 后必须不可见。
    assert.equal(await opacityOf("badge-2"), 0); // enter 尚未开始（4500ms 前）
    await page.evaluate((t) => window.visualPlayer.seek(t), 8000);
    assert.equal(await opacityOf("badge-2"), 1); // 在场
    await page.evaluate((t) => window.visualPlayer.seek(t), 12300);
    const mid = await opacityOf("badge-2"); // 退出中
    assert.ok(mid > 0 && mid < 1, `mid-exit opacity ${mid}`);
    await page.evaluate((t) => window.visualPlayer.seek(t), 12700);
    assert.equal(await opacityOf("badge-2"), 0); // 退出后不可见
    evidence.checks.push("exit boundary: hidden before / visible / fade / gone");

    // 强调提升：窗口中点位移到 -8px，窗口外为 0。
    const transformAt = (t) =>
      page.evaluate(
        (ms) =>
          document.querySelector('[data-object-id="subject"]').style.transform,
        t,
      );
    await page.evaluate((t) => window.visualPlayer.seek(t), 3450);
    assert.ok(transformAt && (await transformAt(3450)).includes("-8"), await transformAt(3450));
    await page.evaluate((t) => window.visualPlayer.seek(t), 2000);
    assert.ok(!(await transformAt(2000)).includes("-8"));
    evidence.checks.push("emphasize bounded lift");

    // 关系线追踪目标：目标带强调位移时圈注仍跟随锚点。
    await page.evaluate((t) => window.visualPlayer.seek(t), 3450);
    const tracked = await page.evaluate(() => {
      const stage = document
          .querySelector(".visual-stage")
          .getBoundingClientRect(),
        ring = document
          .querySelector('[data-object-id="annotation"] circle')
          .getBoundingClientRect(),
        result = window.visualPlayer.seek(3450);
      return {
        dx: Math.abs(
          (ring.x + ring.width / 2 - stage.x) * (1600 / stage.width) -
            result.geometry.subject.anchors.focus.x,
        ),
        dy: Math.abs(
          (ring.y + ring.height / 2 - stage.y) * (1600 / stage.width) -
            result.geometry.subject.anchors.focus.y,
        ),
      };
    });
    assert.ok(tracked.dx < 0.02 && tracked.dy < 0.02, JSON.stringify(tracked));
    evidence.checks.push("relation line tracks emphasized target");

    // 随机乱序 seek 像素一致（动作存在时）。
    await page.evaluate((t) => window.visualPlayer.seek(t), 15000);
    const first = await page.locator(".visual-stage").screenshot();
    for (const t of [3450, 8000, 12250, 0]) await page.evaluate((x) => window.visualPlayer.seek(x), t);
    await page.evaluate((t) => window.visualPlayer.seek(t), 15000);
    assert(first.equals(await page.locator(".visual-stage").screenshot()));
    evidence.checks.push("random seek pixel equality with actions");

    fs.mkdirSync(path.join(root, "evidence"), { recursive: true });
    fs.writeFileSync(
      path.join(root, "evidence/actions-ac11.json"),
      JSON.stringify(evidence, null, 2) + "\n",
    );
    console.log(JSON.stringify({ passed: evidence.checks.length, scene: scene.id }));
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
