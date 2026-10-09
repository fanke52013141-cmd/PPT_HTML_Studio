"use strict";
// Bounded static instance reconstructions after inspecting their actual designs.
const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict");
const { pathToFileURL } = require("url");
const { chromium } = require("../node_modules/playwright");
const out = path.resolve(
  process.argv[2] || "outputs/static-reference/pair-03-roundtrip-v1",
);
const editorialCss = `
.experiment-board .pair-composition{padding:165px 147px;height:960px}
.experiment-board .pair-hero-copy{width:870px}
.experiment-board .pair-eyebrow{font-size:28px;letter-spacing:0;display:flex;align-items:center;gap:26px}
.pair-eyebrow:before{content:"";width:70px;height:2px;background:#c89989;display:block}
.experiment-board .pair-hero-title{font-size:96px;line-height:1.24;margin:42px 0 30px;letter-spacing:-1px;font-weight:700}
.experiment-board .pair-hero-description{font-size:28px;line-height:1.7;max-width:870px;color:var(--ink);white-space:nowrap}
.experiment-board .pair-keyline{font-size:25px;margin-top:13px;gap:0}
.pair-keyline-dot{display:none}
.experiment-board .pair-hero-image{left:991px;right:116px;top:164px;height:455px}
.experiment-board .pair-steps{left:106px;right:102px;bottom:146px;gap:153px}
.experiment-board .pair-step{min-height:150px;height:150px;padding:33px 14px 22px 117px;border-radius:12px;background:white;border:1.3px solid #e6d9ce}
.experiment-board .pair-step strong{font-family:var(--component-font);font-size:29px;font-weight:650;line-height:1.4;white-space:nowrap}
.experiment-board .pair-step p{font-size:24px;line-height:1.6;white-space:nowrap;margin-top:10px}
.experiment-board .pair-step-index{left:33px;top:32px;width:54px;height:54px;display:grid;place-items:center;background:#ad604c;border-radius:50%;color:white;font:600 30px Arial}
.experiment-board .pair-connectors{top:36px;height:80px}
`;
const depthCss = `
.experiment-board .pair-composition{padding:0;height:960px}
.experiment-board .pair-hero-copy{position:absolute;left:178px;top:144px;width:930px}
.experiment-board .pair-eyebrow{font-size:28px;letter-spacing:0;color:#627189}
.experiment-board .pair-hero-title{position:absolute;top:54px;font-size:92px;line-height:1.25;margin:0;letter-spacing:0;font-weight:750}
.experiment-board .pair-hero-description{position:absolute;top:320px;font-size:28px;line-height:1.7;max-width:none;white-space:nowrap}
.experiment-board .pair-keyline{position:absolute;top:378px;font-size:26px;margin:0;gap:0;white-space:nowrap}
.pair-keyline-dot{display:none}
.experiment-board .pair-hero-image{left:940px;right:50px;top:-50px;height:700px}
.experiment-board .pair-subject{filter:drop-shadow(0 28px 25px #24466a16)}
.experiment-board .pair-steps{left:112px;right:102px;bottom:146px;gap:116px}
.experiment-board .pair-step{min-height:170px;height:170px;padding:34px 18px 24px 142px;border-radius:30px;background:#fff;border:1.4px solid #d6e2ed;box-shadow:0 14px 22px #24466a08}
.experiment-board .pair-step strong{font-family:var(--component-font);font-size:32px;font-weight:650;line-height:1.4;white-space:nowrap}
.experiment-board .pair-step p{font-size:23px;line-height:1.6;white-space:nowrap;margin-top:13px}
.experiment-board .pair-step-index{left:33px;top:34px;width:74px;height:74px;display:grid;place-items:center;background:#e7f0fb;border-radius:50%;color:#2475bd;font:600 32px Arial}
.experiment-board .pair-connectors{top:49px;height:80px;color:#789bbd}
`;
const definition = JSON.parse(
  fs.readFileSync(path.join(out, "definition.json"), "utf8"),
);
assert(
  ["PAIR-02", "PAIR-03"].includes(definition.pairRef),
  "No inspected reconstruction for this pair",
);
const depth = definition.pairRef === "PAIR-02";
const css = depth ? depthCss : editorialCss;
(async () => {
  const started = performance.now();
  assert(
    fs.existsSync(path.join(out, "live-official/design-reference.png")),
    "Inspect actual generation first",
  );
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.HPS_CHROME,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(out, "code-baseline.html")).href);
    await page.addStyleTag({ content: css });
    await page.evaluate(
      ({ pairRef, depth }) => {
        document.title = `${pairRef} 生成设计的静态代码还原`;
        document
          .querySelectorAll(".pair-step-index")
          .forEach((e, i) => (e.textContent = String(i + 1)));
        document
          .querySelector(".pair-connectors")
          .setAttribute("viewBox", "0 0 1712 80");
        document
          .querySelector(".pair-connectors path")
          .setAttribute(
            "d",
            depth
              ? "M522 40H570M558 28L570 40L558 52M1134 40H1182M1170 28L1182 40L1170 52"
              : "M497 40H605M593 28L605 40L593 52M1114 40H1222M1210 28L1222 40L1210 52",
          );
      },
      { pairRef: definition.pairRef, depth },
    );
    const html = await page.content();
    fs.writeFileSync(path.join(out, "reconstructed.html"), html);
    await page.goto(pathToFileURL(path.join(out, "reconstructed.html")).href);
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map((i) => i.decode()));
    });
    assert.equal(
      await page.locator(".pair-hero-title").textContent(),
      definition.content.title,
    );
    for (const [selector, expected] of [
      [".pair-eyebrow", definition.content.eyebrow],
      [".pair-hero-description", definition.content.description],
      [".pair-keyline", definition.content.keyline],
    ])
      assert.equal(await page.locator(selector).textContent(), expected);
    for (const [i, step] of definition.content.steps.entries()) {
      assert.equal(
        await page.locator(".pair-step strong").nth(i).textContent(),
        step.title,
      );
      assert.equal(
        await page.locator(".pair-step p").nth(i).textContent(),
        step.copy,
      );
    }
    assert.equal(await page.locator("img").count(), 1);
    assert.equal(await page.locator("script").count(), 0);
    const bounds = await page.locator(".pair-composition").evaluate((e) =>
      [...e.querySelectorAll("h2,p,strong,.pair-eyebrow,.pair-keyline")]
        .map((n) => {
          const r = document.createRange();
          r.selectNodeContents(n);
          return [...r.getClientRects()].map((b) => ({
            left: b.left,
            right: b.right,
            top: b.top,
            bottom: b.bottom,
          }));
        })
        .flat(),
    );
    assert(
      bounds.every(
        (b) => b.left >= 0 && b.right <= 1920 && b.top >= 0 && b.bottom <= 960,
      ),
      "text safe area",
    );
    await page.screenshot({ path: path.join(out, "reconstructed.png") });
    const src = await page.locator("img").getAttribute("src");
    await page
      .locator(".pair-hero-title")
      .evaluate((e) => (e.textContent = "标题可以直接修改"));
    assert.equal(await page.locator("img").getAttribute("src"), src);
    assert.deepEqual(errors, []);
    fs.writeFileSync(
      path.join(out, "reconstruction-checks.json"),
      JSON.stringify(
        {
          status: "passed",
          captureAndVerificationSeconds:
            Math.round((performance.now() - started) / 10) / 100,
          checks: [
            "all authoritative content exact",
            "one independent image",
            "no scripts or motion",
            "editable text does not change image",
            "all text above subtitle area",
            "saved offline HTML reopened",
            "zero browser errors",
          ],
          bounds,
          limitations: [
            `Existing frozen ${definition.asset.id} reused; generated subject and shadow not extracted.`,
            "White code background replaces generated off-white background.",
            "Manual instance adaptation, not automatic production template.",
          ],
        },
        null,
        2,
      ),
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
