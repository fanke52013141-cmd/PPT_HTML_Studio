"use strict";
const fs = require("node:fs"), path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require("playwright");
const {resolveBrowser} = require("./browser-runtime.cjs");
const [snapshot, specPath, output] = process.argv.slice(2);
(async () => {
  let browser;
  const raw = {frames: [], pageErrors: []};
  try {
    const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
    browser = await chromium.launch({headless: true, executablePath: resolveBrowser(chromium)});
    const page = await browser.newPage({viewport: {width: 1648, height: 1200}, deviceScaleFactor: 1});
    page.on("pageerror", e => raw.pageErrors.push(e.name));
    await page.route("**/*", route => /^https?:/.test(route.request().url()) ? route.abort() : route.continue());
    await page.goto(pathToFileURL(path.resolve(snapshot, "preview/index.html")).href + "?export");
    await page.waitForFunction(() => window.visualPlayer?.ready, {}, {timeout: 20000});
    for (const [beatIndex, beat] of spec.entries()) {
      for (const [frameIndex, timeMs] of beat.times.entries()) {
        const states = await page.evaluate(t => {
          window.visualPlayer.seek(t);
          return Object.fromEntries([...document.querySelectorAll("[data-object-id]")].map(el => {
            const style = getComputedStyle(el);
            return [el.dataset.objectId, {opacity: style.display === "none" || style.visibility === "hidden" ? 0 : Number(style.opacity), transform: style.transform}];
          }));
        }, timeMs);
        const file = `beat-${beatIndex}-${frameIndex}.png`;
        await page.locator(".visual-stage").screenshot({path: path.join(output, file)});
        raw.frames.push({beatId: beat.beatId, frameIndex, timeMs, file, states});
      }
    }
  } catch (e) {
    raw.pageErrors.push(e.name + ":" + e.message);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    fs.writeFileSync(path.join(output, "semantic-frames.json"), JSON.stringify(raw));
  }
})();
