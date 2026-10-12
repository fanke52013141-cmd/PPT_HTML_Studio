"use strict";
// Render explicit snapshot times for one html-visual scene (E03). Shares the
// preview bundle and seek() evaluation path; writes snapshot-<i>.png files.
// Usage: node tools/export-snapshots.cjs <scene.json> <times.json> <out-dir>
const fs = require("fs"),
  path = require("path");
const { pathToFileURL } = require("url");

const [scenePath, timesPath, outDir] = process.argv.slice(2);
if (!scenePath || !timesPath || !outDir) {
  console.error(
    "usage: export-snapshots.cjs <scene.json> <times.json> <out-dir>",
  );
  process.exit(2);
}
const root = path.resolve(__dirname, "..");
const snapshotRoot = process.env.HPS_HTML_SNAPSHOT;
const projectResources = snapshotRoot
  ? null
  : require("./project-resources.cjs").loadProjectResources();
const scene = JSON.parse(fs.readFileSync(scenePath, "utf8"));
const times = JSON.parse(fs.readFileSync(timesPath, "utf8"));
if (!Array.isArray(times) || !times.length) throw new Error("times invalid");

(async () => {
  const playwright = require("playwright");
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: require("./browser-runtime.cjs").resolveBrowser(
      playwright.chromium,
    ),
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1648, height: 1200 },
      deviceScaleFactor: 1,
    });
    if (snapshotRoot) await page.route(/^https?:/, (route) => route.abort());
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(
      pathToFileURL(
        snapshotRoot
          ? path.join(snapshotRoot, "preview/index.html")
          : path.join(root, "visual/preview/index.html"),
      ).href + (snapshotRoot ? "?export=1" : ""),
    );
    await page.waitForFunction(
      () => window.visualPlayer?.ready,
      {},
      { timeout: 20000 },
    );
    await page.evaluate(() => document.fonts.ready);
    // Export pixels are the canonical canvas, independent of review chrome padding.
    await page.addStyleTag({
      content:
        "main{max-width:none!important;width:1600px!important;padding:0!important;margin:0!important}#viewport{width:1600px!important;height:900px!important;border-radius:0!important}.visual-stage{transform:none!important;width:1600px!important;height:900px!important}",
    });
    if (snapshotRoot) {
      const frozen = await page.evaluate(() => window.visualPlayer.scene);
      if (JSON.stringify(frozen) !== JSON.stringify(scene))
        throw new Error("SNAPSHOT_SCENE_MISMATCH");
      await page.evaluate(() => window.visualPlayer.pause());
    } else {
      await page.evaluate((r) => {
        window.__projectResources = r;
      }, projectResources);
      const applied = await page.evaluate(
        (s) => window.visualPlayer.apply(s, window.__projectResources),
        scene,
      );
      if (!applied) throw new Error("scene failed to compile/prepare");
    }
    for (let i = 0; i < times.length; i += 1) {
      const result = await page.evaluate(
        (t) => window.visualPlayer.seek(t),
        times[i],
      );
      if (result.timeMs !== times[i])
        throw new Error(`seek mismatch at snapshot ${i}`);
      const shot = await page.locator(".visual-stage").screenshot();
      fs.writeFileSync(
        path.join(outDir, `snapshot-${String(i).padStart(3, "0")}.png`),
        shot,
      );
    }
    if (errors.length) throw new Error("page errors: " + errors[0]);
    console.log(JSON.stringify({ snapshots: times.length, sceneId: scene.id }));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
