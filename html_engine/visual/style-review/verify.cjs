"use strict";
const assert = require("assert/strict"),
  fs = require("fs"),
  path = require("path");
const { pathToFileURL } = require("url"),
  { chromium } = require("playwright");
async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.HPS_CHROME ||
      "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
  });
  const page = await browser.newPage({
      viewport: { width: 1648, height: 1200 },
    }),
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const evidence = {
    date: "2026-10-08",
    status: "technical-checks-passed; user-visual-review-pending",
    newImageGenerations: 0,
    scenes: [],
    checks: [],
  };
  try {
    await page.goto(pathToFileURL(path.join(__dirname, "index.html")).href);
    await page.waitForFunction(
      () => window.scienceStyleReview?.ready,
      {},
      { timeout: 15000 },
    );
    assert(
      await page
        .locator("details img")
        .evaluate((img) => img.complete && img.naturalWidth > 0),
      "Original reference must be available",
    );
    fs.mkdirSync(path.join(__dirname, "evidence"), { recursive: true });
    for (const id of ["condensation", "evaporation"]) {
      assert(
        await page.evaluate((id) => window.scienceStyleReview.load(id), id),
      );
      await page.evaluate(() => window.scienceStyleReview.seek(18000));
      const final = await page.locator(".scene").screenshot();
      fs.writeFileSync(path.join(__dirname, "evidence", id + ".png"), final);
      await page.evaluate(() => window.scienceStyleReview.seek(3000));
      await page.evaluate(() => window.scienceStyleReview.seek(18000));
      assert(
        final.equals(await page.locator(".scene").screenshot()),
        "Seeking must restore the same scene",
      );
      for (const width of [1648, 1048]) {
        await page.setViewportSize({ width, height: 1200 });
        await page.waitForTimeout(40);
        for (const time of [0, 1100, 12500, 18000]) {
          const state = await page.evaluate(
            (t) => window.scienceStyleReview.seek(t),
            time,
          );
          const mapped = await page.evaluate(() => {
            const stage = document
                .querySelector(".scene")
                .getBoundingClientRect(),
              ring = document
                .querySelector(".annotation circle")
                .getBoundingClientRect(),
              subtitle = document
                .querySelector(".subtitle")
                .getBoundingClientRect();
            const scale = 1600 / stage.width;
            return {
              x: (ring.x + ring.width / 2 - stage.x) * scale,
              y: (ring.y + ring.height / 2 - stage.y) * scale,
              subtitleY: (subtitle.y - stage.y) * scale,
              subtitleHeight: subtitle.height * scale,
            };
          });
          assert(
            Math.abs(mapped.x - state.anchor.x) < 0.02 &&
              Math.abs(mapped.y - state.anchor.y) < 0.02,
          );
          assert(
            Math.abs(mapped.subtitleY - 800) < 0.02 &&
              Math.abs(mapped.subtitleHeight - 100) < 0.02,
          );
        }
      }
      for (const size of [20, 32, 44])
        await page.evaluate(
          (s) => window.scienceStyleReview.setSubtitleFont(s),
          size,
        );
      await page.setViewportSize({ width: 1648, height: 1200 });
      await page.evaluate(() => window.scienceStyleReview.setSubtitleFont(32));
      await page.evaluate(() => window.scienceStyleReview.seek(7000));
      await page
        .locator(".scene")
        .screenshot({
          path: path.join(__dirname, "evidence", id + "-middle.png"),
        });
      evidence.scenes.push({
        id,
        codeIconCount: await page.locator(".icon-bubble svg").count(),
        imageSubjects: await page.locator(".subject img").count(),
      });
    }
    await page.evaluate(() => {
      window.scienceStyleReview.seek(18000);
      window.scienceStyleReview.play();
    });
    await page.waitForTimeout(250);
    const played = await page.evaluate(() => window.scienceStyleReview.timeMs);
    assert(played > 100 && played < 1000);
    await page.evaluate(() => window.scienceStyleReview.pause());
    const paused = await page.evaluate(() => window.scienceStyleReview.timeMs);
    await page.waitForTimeout(100);
    assert.equal(
      await page.evaluate(() => window.scienceStyleReview.timeMs),
      paused,
    );
    await page.evaluate(() => window.scienceStyleReview.play());
    await page.waitForTimeout(100);
    assert(
      (await page.evaluate(() => window.scienceStyleReview.timeMs)) > paused,
    );
    await page.evaluate(() => window.scienceStyleReview.pause());
    assert.deepEqual(errors, []);
    evidence.checks = [
      "two content substitutions",
      "actual reference loaded",
      "seek pixel repeatability",
      "asset anchor follows entry and viewport scale",
      "fixed subtitle zone with 20/32/44 font",
      "play pause and resume",
      "no page errors",
    ];
    fs.writeFileSync(
      path.join(__dirname, "evidence/verification.json"),
      JSON.stringify(evidence, null, 2) + "\n",
    );
    console.log(JSON.stringify(evidence));
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
