"use strict";
// Compile + measure + screenshot one html-visual scene (C04 static review).
// Uses the SAME preview bundle as the player: schema/resource validation and
// text measurement run first; failures come back as structured diagnostics
// with the offending object id. Exit code is always 0 when a report was
// written; report.passed carries the verdict.
// Usage: node tools/review-scene.cjs <scene.json> <out-report.json> <out.png> [rangeSpec.json]
// rangeSpec: {nodeId, start, end} — code-point range resolved via DOM Range
// (UTF-16 conversion per contract) and reported as viewport/client rects
// together with the deterministic geometry (D03 text targeting evidence).
const fs = require("fs"),
  path = require("path");
const { pathToFileURL } = require("url");

const [scenePath, reportPath, screenshotPath, rangeSpecPath] = process.argv.slice(2);
if (!scenePath || !reportPath || !screenshotPath) {
  console.error("usage: review-scene.cjs <scene.json> <out-report.json> <out.png> [rangeSpec.json]");
  process.exit(2);
}
const rangeSpec = rangeSpecPath
  ? JSON.parse(fs.readFileSync(rangeSpecPath, "utf8"))
  : null;
const root = path.resolve(__dirname, "..");
const scene = JSON.parse(fs.readFileSync(scenePath, "utf8"));

function resolveChromePath(playwright) {
  if (process.env.HPS_CHROME) return process.env.HPS_CHROME;
  const discovered = playwright.chromium.executablePath();
  if (discovered && fs.existsSync(discovered)) return discovered;
  // Validated Chromium on this machine; same fallback as visual/tests/verify.cjs.
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
    const pageErrors = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await page.goto(pathToFileURL(path.join(root, "visual/preview/index.html")).href);
    await page.waitForFunction(() => window.visualPlayer?.ready, {}, { timeout: 20000 });
    const applied = await page.evaluate(
      async (s) => {
        try {
          return { ok: await window.visualPlayer.apply(s) };
        } catch (e) {
          return { ok: false, error: String(e && e.message || e) };
        }
      },
      scene,
    );
    if (!applied.ok) {
      const status = await page.locator("#status").innerText();
      fs.writeFileSync(
        reportPath,
        JSON.stringify(
          {
            passed: false,
            sceneId: scene.id || null,
            code: "SCENE_PREPARE_FAILED",
            message: applied.error || status,
          },
          null,
          2,
        ) + "\n",
      );
      return;
    }
    const result = await page.evaluate(
      (t) => window.visualPlayer.seek(t),
      scene.durationMs,
    );
    const shot = await page.locator(".visual-stage").screenshot();
    fs.writeFileSync(screenshotPath, shot);
    const textRange = rangeSpec
      ? await page.evaluate(
          async (spec) => {
            const el = document.querySelector(
              `[data-object-id="${spec.nodeId}"]`,
            );
            if (!el) return { error: "node not found" };
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            const units = [];
            let node;
            while ((node = walker.nextNode()))
              for (const ch of node.data) units.push({ node, ch });
            let startNode = null, startOffset = 0, endNode = null, endOffset = 0;
            let codeIndex = 0;
            for (let i = 0; i < units.length; i += 1) {
              if (codeIndex === spec.start) { startNode = units[i].node; startOffset = i; }
              if (codeIndex === spec.end) { endNode = units[i].node; endOffset = i; }
              codeIndex += 1;
            }
            if (startNode === null || endNode === null)
              return { error: "range out of bounds" };
            const range = document.createRange();
            range.setStart(startNode, startOffset);
            range.setEnd(endNode, endOffset);
            const rects = [...range.getClientRects()]
              .filter((r) => r.width && r.height)
              .map((r) => ({ x: r.x, y: r.y, width: r.width, height: r.height }));
            const stage = document
              .querySelector(".visual-stage")
              .getBoundingClientRect();
            const scale = stage.width / 1600;
            return {
              rects,
              canvasRects: rects.map((r) => ({
                x: (r.x - stage.x) / scale,
                y: (r.y - stage.y) / scale,
                width: r.width / scale,
                height: r.height / scale,
              })),
            };
          },
          rangeSpec,
        )
      : null;
    fs.writeFileSync(
      reportPath,
      JSON.stringify(
        {
          passed: pageErrors.length === 0,
          sceneId: scene.id || null,
          durationMs: result.timeMs,
          measuredObjects: Object.keys(result.measurements || {}).length,
          geometryObjects: Object.keys(result.geometry || {}).length,
          geometry: result.geometry,
          measurements: result.measurements,
          textRange: textRange || undefined,
          pageErrors,
        },
        null,
        2,
      ) + "\n",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  try {
    fs.writeFileSync(
      reportPath,
      JSON.stringify(
        {
          passed: false,
          sceneId: scene.id || null,
          code: "REVIEW_INFRASTRUCTURE_ERROR",
          message: String(e && e.message || e),
        },
        null,
        2,
      ) + "\n",
    );
  } catch {}
  process.exitCode = 1;
});
