"use strict";
// No network/provider calls. Probe actual browser/font loading, optionally renderer.
const fs = require("node:fs"), path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");
const { resolveBrowser } = require("./browser-runtime.cjs");
(async () => {
  let browser;
  try {
    const spec = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
    const executable = resolveBrowser(chromium);
    browser = await chromium.launch({ headless: true, executablePath: executable, timeout: 15000 });
    const page = await browser.newPage();
    await page.route("**/*", route => /^https?:/.test(route.request().url()) ? route.abort() : route.continue());
    await page.setContent("<html><body>字体检测</body></html>");
    // local() load fails for a missing face instead of silently measuring fallback.
    const font = await page.evaluate(async family => {
      try {
        const face = new FontFace("HPSPreflight", `local(${JSON.stringify(family)})`);
        await face.load();
        document.fonts.add(face);
        return face.status === "loaded";
      } catch { return false; }
    }, spec.font_family);
    let scenePassed = null;
    if (spec.scene) {
      const errors = [];
      page.on("pageerror", e => errors.push(e.name));
      await page.goto(pathToFileURL(path.resolve(__dirname, "../visual/preview/index.html")).href);
      await page.waitForFunction(() => window.visualPlayer?.ready, {}, { timeout: 15000 });
      const resources = require("./project-resources.cjs").loadProjectResources();
      scenePassed = await page.evaluate(async ({scene, resources}) => {
        try { return !!(await window.visualPlayer.apply(scene, resources)); }
        catch { return false; }
      }, { scene: spec.scene, resources });
      scenePassed = scenePassed && errors.length === 0;
    }
    console.log(JSON.stringify({ browser: true, executable, font, scene_passed: scenePassed }));
  } catch {
    // Do not print raw error messages containing user input or provider secrets.
    console.log(JSON.stringify({ browser: false, code: "BROWSER_OR_RENDER_PROBE_FAILED" }));
    process.exitCode = 1;
  } finally { if (browser) await browser.close(); }
})();
