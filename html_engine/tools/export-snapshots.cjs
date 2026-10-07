"use strict";
// Render explicit snapshot times for one html-visual scene (E03). Shares the
// preview bundle and seek() evaluation path; writes snapshot-<i>.png files.
// Usage: node tools/export-snapshots.cjs <scene.json> <times.json> <out-dir>
const fs = require("fs"),
  path = require("path");
const { pathToFileURL } = require("url");

const [scenePath, timesPath, outDir] = process.argv.slice(2);
if (!scenePath || !timesPath || !outDir) {
  console.error("usage: export-snapshots.cjs <scene.json> <times.json> <out-dir>");
  process.exit(2);
}
const root = path.resolve(__dirname, "..");
const scene = JSON.parse(fs.readFileSync(scenePath, "utf8"));
const times = JSON.parse(fs.readFileSync(timesPath, "utf8"));
if (!Array.isArray(times) || !times.length) throw new Error("times invalid");

function resolveChromePath(playwright) {
  if (process.env.HPS_CHROME) return process.env.HPS_CHROME;
  const discovered = playwright.chromium.executablePath();
  if (discovered && fs.existsSync(discovered)) return discovered;
  return "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe";
}

(async () => {
  const playwright = require("playwright");
  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: resolveChromePath(playwright),
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1648, height: 1200 },
      deviceScaleFactor: 1,
    });
    await page.goto(pathToFileURL(path.join(root, "visual/preview/index.html")).href);
    await page.waitForFunction(() => window.visualPlayer?.ready, {}, { timeout: 20000 });
    const applied = await page.evaluate(
      async (s) => ({ ok: await window.visualPlayer.apply(s) }),
      scene,
    );
    if (!applied.ok) throw new Error("scene failed to compile/prepare");
    for (let i = 0; i < times.length; i += 1) {
      const result = await page.evaluate(
        (t) => window.visualPlayer.seek(t),
        times[i],
      );
      if (result.timeMs !== times[i])
        throw new Error(`seek mismatch at snapshot ${i}`);
      const shot = await page.locator(".visual-stage").screenshot();
      fs.writeFileSync(path.join(outDir, `snapshot-${String(i).padStart(3, "0")}.png`), shot);
    }
    console.log(JSON.stringify({ snapshots: times.length, sceneId: scene.id }));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
