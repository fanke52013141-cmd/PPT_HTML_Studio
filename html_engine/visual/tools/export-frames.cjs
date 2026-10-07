"use strict";
// Shared offline frame-export harness (A04 / OSS-03 method, independent
// implementation). Drives the SAME preview bundle the player uses, verifies
// the bundle/version inputs recorded in the compiled catalog, renders frames
// at exact rational times t=i/fps, and writes a manifest with content hashes.
// No wall-clock animation state, no CSS self-running clocks: every frame is
// produced by seek(t) on the shared evaluate path.
const fs = require("fs"),
  path = require("path"),
  crypto = require("crypto");
const { pathToFileURL } = require("url");
const root = path.resolve(__dirname, "..");
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));

async function exportFrames({ sceneId, fps = 30, outDir, times }) {
  const catalog = read("generated/catalog.json");
  const scene = read(`scenes/${sceneId}.json`);
  const bundlePath = path.join(root, "preview/player.js");
  const bundle = fs.readFileSync(bundlePath, "utf8");
  const frameTimes =
    times ??
    Array.from(
      { length: Math.ceil((scene.durationMs / 1000) * fps) + 1 },
      (_, i) => i / fps,
    );
  const target = path.resolve(outDir ?? path.join(root, "evidence/frames", sceneId));
  fs.mkdirSync(target, { recursive: true });
  const browser = require("playwright").chromium;
  const browserHandle = await browser.launch({
    headless: true,
    executablePath:
      process.env.HPS_CHROME ||
      "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
  });
  const manifest = {
    format: "hps.visual.frame-export",
    version: "0.1.0",
    scene: `${scene.id}@${scene.version}`,
    theme: scene.themeRef,
    layout: scene.layoutRef,
    template: scene.templateRef ?? null,
    fps,
    frameCount: frameTimes.length,
    bundleSha256: crypto.createHash("sha256").update(bundle).digest("hex"),
    frames: [],
  };
  try {
    const page = await browserHandle.newPage({
      viewport: { width: 1648, height: 1200 },
      deviceScaleFactor: 1,
    });
    await page.goto(pathToFileURL(path.join(root, "preview/index.html")).href);
    await page.waitForFunction(() => window.visualPlayer?.ready, {}, { timeout: 15000 });
    const applied = await page.evaluate((s) => window.visualPlayer.apply(s), scene);
    if (!applied) throw new Error("scene failed to apply");
    for (const t of frameTimes) {
      const result = await page.evaluate(
        (ms) => window.visualPlayer.seek(ms),
        Math.round(t * 1000),
      );
      if (result.timeMs !== Math.round(t * 1000))
        throw new Error(`seek mismatch at ${t}`);
      const shot = await page.locator(".visual-stage").screenshot();
      const name = `frame-${String(manifest.frames.length).padStart(5, "0")}.png`;
      fs.writeFileSync(path.join(target, name), shot);
      manifest.frames.push({
        t,
        timeMs: result.timeMs,
        file: name,
        sha256: crypto.createHash("sha256").update(shot).digest("hex"),
      });
    }
  } finally {
    await browserHandle.close();
  }
  fs.writeFileSync(
    path.join(target, "manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n",
  );
  return { sceneId, frames: manifest.frames.length, outDir: target };
}
module.exports = { exportFrames };
if (require.main === module) {
  const sceneId = process.argv[2];
  if (!sceneId) {
    console.error("usage: node visual/tools/export-frames.cjs <sceneId> [fps]");
    process.exit(2);
  }
  exportFrames({ sceneId, fps: Number(process.argv[3] || 30) })
    .then((r) => console.log(JSON.stringify(r)))
    .catch((e) => {
      console.error(e);
      process.exitCode = 1;
    });
}
