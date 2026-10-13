"use strict";
const fs = require("node:fs"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");
const { resolveBrowser } = require("../../tools/browser-runtime.cjs");
async function main() {
  const scene = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const out = path.resolve(process.argv[3]);
  const browser = await chromium.launch({
    headless: true,
    executablePath: resolveBrowser(chromium),
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1648, height: 1200 },
    });
    await page.goto(
      pathToFileURL(path.resolve(__dirname, "../preview/index.html")).href,
    );
    await page.waitForFunction(() => window.visualPlayer?.ready);
    assert.equal(
      await page.evaluate((s) => window.visualPlayer.apply(s), scene),
      true,
      await page.locator("#status").innerText(),
    );
    const states = async (t) =>
      page.evaluate((ms) => {
        window.visualPlayer.seek(ms);
        return Object.fromEntries(
          [...document.querySelectorAll("[data-object-id]")].map((el) => [
            el.dataset.objectId,
            {
              opacity: Number(el.style.opacity),
              transform: el.style.transform,
            },
          ]),
        );
      }, t);
    const initial = await states(0);
    assert.equal(initial.header.opacity, 1);
    assert.equal(initial["stat-1"].opacity, 0);
    const frames = [];
    const times = scene.beats.flatMap(b => [b.startMs, Math.round((b.startMs + b.endMs) / 2), b.endMs]);
    for (const [i, t] of times.entries()) {
      const state = await states(t);
      const filename = `beat-frame-${i}.png`;
      await page
        .locator("#viewport")
        .screenshot({ path: path.join(out, filename) });
      frames.push({ timeMs: t, state, file: filename });
    }
    const focus = scene.motion.find(a => a.targetId === "stat-1" && a.type === "emphasize");
    const focusTime = focus.startMs + focus.durationMs / 2;
    const first = await states(focusTime);
    await states(scene.durationMs);
    const again = await states(focusTime);
    assert.deepEqual(first, again);
    assert.ok(first["stat-1"].transform.includes("-"));
    fs.writeFileSync(
      path.join(out, "frames.json"),
      JSON.stringify(
        {
          initialContextVisible: true,
          instructionHiddenBeforeSpeech: true,
          seekRepeatEqual: true,
          frames,
        },
        null,
        2,
      ),
    );
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
