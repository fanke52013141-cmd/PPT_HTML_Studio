"use strict";
// Render copied shared bundle with frozen resource/font bytes, never live scene paths.
const fs = require("node:fs"), path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");
const { resolveBrowser } = require("./browser-runtime.cjs");
const [folder, output] = process.argv.slice(2);
(async () => {
  let browser;
  let report = { passed: false, code: "SNAPSHOT_RENDER_FAILED" };
  fs.mkdirSync(output, { recursive: true });
  try {
    browser = await chromium.launch({ headless: true, executablePath: resolveBrowser(chromium) });
    const page = await browser.newPage({ viewport: { width: 1648, height: 1200 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", e => errors.push(e.name));
    await page.route("**/*", route => /^https?:/.test(route.request().url()) ? route.abort() : route.continue());
    await page.goto(pathToFileURL(path.resolve(folder, "preview/index.html")).href);
    await page.evaluate(async () => { await Promise.all([...document.fonts].map(f => f.load())); });
    await page.waitForFunction(() => window.visualPlayer?.ready || document.querySelector("#status")?.textContent.startsWith("未应用"), {}, { timeout: 20000 });
    const ready = await page.evaluate(() => !!window.visualPlayer?.ready);
    const prepareStatus = await page.locator("#status").innerText();
    const scene = JSON.parse(fs.readFileSync(path.join(folder, "input/scene.json"), "utf8"));
    if (!ready) {
      await page.evaluate(async s => window.visualPlayer.diagnose(s), scene);
    }
    const result = await page.evaluate(t => window.visualPlayer.seek(t), scene.durationMs);
    if (!result) throw Error("SNAPSHOT_PREPARE_FAILED");
    const bytes = await page.locator(".visual-stage").screenshot();
    fs.writeFileSync(path.join(output, "end-frame.png"), bytes);
    report = { ...result, passed: ready && errors.length === 0, diagnosticOnly: !ready,
               pageErrors: errors, prepareStatus, browserVersion: browser.version(), timeMs: scene.durationMs };
  } catch {
    // Raw errors may contain sensitive author strings; keep a stable code.
  } finally {
    if (browser) await browser.close();
    fs.writeFileSync(path.join(output, "raw-report.json"), JSON.stringify(report, null, 2));
    if (!report.passed) process.exitCode = 1;
  }
})();
