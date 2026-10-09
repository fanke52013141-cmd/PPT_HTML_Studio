const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict");
const { pathToFileURL } = require("url");
const { chromium } = require("../node_modules/playwright");
async function capture(locator, target) {
  const temporary = target + ".tmp";
  fs.writeFileSync(temporary, await locator.screenshot());
  fs.renameSync(temporary, target);
}
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.HPS_CHROME,
  });
  const out =
    process.env.HPS_REFERENCE_EVIDENCE || path.join(__dirname, "evidence");
  fs.mkdirSync(out, { recursive: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 2080, height: 1100 },
      deviceScaleFactor: 1,
    });
    const errors = [];
    const networkRequests = [];
    page.on("request", (r) => {
      if (/^https?:/.test(r.url())) networkRequests.push(r.url());
    });
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(
      pathToFileURL(path.join(__dirname, "components.html")).href,
    );
    await page.waitForFunction(
      () =>
        window.ComponentAtlas?.ready &&
        window.ReferenceEffects?.ready &&
        window.StaticReference?.ready &&
        window.StylePairs?.ready,
    );
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator("#atlas .cell").count(), 32);
    assert.equal(await page.locator("#typography .font-cell").count(), 5);
    assert.equal(await page.locator("#variants [data-variant-id]").count(), 16);
    const variantChecks = await page.evaluate(() => {
      const samples = [...document.querySelectorAll("#variants .sample")];
      const failures = [];
      for (const sample of samples) {
        const component = sample.querySelector(".component");
        const box = sample.getBoundingClientRect();
        const rect = component.getBoundingClientRect();
        if (
          rect.left < box.left ||
          rect.top < box.top ||
          rect.right > box.right ||
          rect.bottom > box.bottom ||
          component.scrollWidth > component.clientWidth + 1
        )
          failures.push(component.dataset.variantId);
        for (const text of component.querySelectorAll("span,strong,p")) {
          const range = document.createRange();
          range.selectNodeContents(text);
          if (
            [...range.getClientRects()].some(
              (r) =>
                r.left < box.left ||
                r.right > box.right ||
                r.top < box.top ||
                r.bottom > box.bottom,
            )
          )
            failures.push(component.dataset.variantId + ":text");
        }
      }
      const style = (id) =>
        getComputedStyle(
          document.querySelector(`[data-variant-id="${id}"] .sample-text`),
        );
      const distinctEmphasis =
        style("PV06").borderBottomStyle === "solid" &&
        style("PV07").borderRadius === "40px" &&
        style("PV05").borderBottomStyle === "none";
      const parentMapping = window.PresentationVariants.items.every(
        (v) =>
          document.querySelector(`[data-variant-id="${v.id}"]`).dataset
            .componentId === v.componentRef,
      );
      const reject = (id, variant, expected) => {
        try {
          window.ComponentAtlas.render(id, "文字", variant);
          return false;
        } catch (e) {
          return e.message === expected;
        }
      };
      return {
        failures,
        distinctEmphasis,
        parentMapping,
        rejectUnknown: reject("T01", "BAD", "UNKNOWN_PRESENTATION_VARIANT"),
        rejectMismatch: reject("C01", "PV01", "VARIANT_COMPONENT_MISMATCH"),
        safeText:
          window.ComponentAtlas.render("T01", "<img src=x>", "PV02")
            .textContent === "<img src=x>" &&
          !window.ComponentAtlas.render(
            "T01",
            "<img src=x>",
            "PV02",
          ).querySelector("img"),
      };
    });
    assert.deepEqual(variantChecks.failures, []);
    for (const [name, value] of Object.entries(variantChecks))
      if (name !== "failures") assert.equal(value, true, name);

    const overflow = await page
      .locator("#atlas .sample")
      .evaluateAll((samples) =>
        samples.flatMap((s) => {
          const b = s.getBoundingClientRect();
          return [...s.querySelectorAll(".component")]
            .filter((e) => {
              const r = e.getBoundingClientRect();
              return (
                r.width > b.width + 1 ||
                r.height > b.height + 1 ||
                e.scrollWidth > e.clientWidth + 1
              );
            })
            .map((e) => e.dataset.componentId);
        }),
      );
    assert.deepEqual(overflow, []);
    for (const [id, name] of [
      ["atlas", "code-components"],
      ["variants", "presentation-variants"],
      ["typography", "typography"],
      ["pairing", "style-pairing"],
      ["effects", "visual-effects"],
      ["composition", "typography-compositions"],
      ["precision", "svg-precision"],
      ["usage", "effect-usage"],
      ["fusion", "image-fusion"],
      ["pair-01", "style-pair-outline"],
      ["pair-02", "style-pair-depth"],
      ["pair-03", "style-pair-editorial"],
    ])
      await capture(page.locator("#" + id), path.join(out, name + ".png"));
    assert.equal(await page.locator("#effects .effect-cell").count(), 28);
    assert.equal(await page.locator(".pair-board").count(), 3);
    await page.evaluate(async () => {
      await Promise.all(
        [...document.querySelectorAll(".pair-subject,.pair-source-image")].map(
          (i) => i.decode(),
        ),
      );
    });
    assert(
      await page.evaluate(() => {
        const pairs = window.StylePairs.catalog.pairs;
        return pairs.every(
          (p) =>
            document.getElementById(p.id.toLowerCase()).dataset.skin ===
            p.codeStyleRef,
        );
      }),
    );
    const pairOverflow = await page
      .locator(".pair-composition")
      .evaluateAll((es) =>
        es.flatMap((e) => {
          const box = e.getBoundingClientRect();
          return [
            ...e.querySelectorAll(
              "h2,p,strong,.pair-eyebrow,.pair-keyline,.pair-step-index",
            ),
          ]
            .filter((n) => {
              const r = document.createRange();
              r.selectNodeContents(n);
              return [...r.getClientRects()].some(
                (b) =>
                  b.left < box.left + 1 ||
                  b.top < box.top + 1 ||
                  b.right > box.right - 1 ||
                  b.bottom > box.bottom - 1,
              );
            })
            .map((n) => ({
              pair: e.closest(".pair-board").dataset.pairId,
              text: n.textContent,
            }));
        }),
      );
    assert.deepEqual(pairOverflow, []);
    const contents = await page
      .locator(".pair-composition")
      .evaluateAll((es) => es.map((e) => e.innerText));
    assert(contents.every((t) => t === contents[0]));
    assert(
      await page.evaluate(() => {
        try {
          window.StylePairs.render("unknown");
          return false;
        } catch (e) {
          return e.message === "UNKNOWN_STYLE_PAIR";
        }
      }),
    );
    assert.equal(await page.locator(".spec-card").count(), 18);
    assert.equal(
      await page.locator("#motion, #motion-play, video, canvas").count(),
      0,
    );
    await page.evaluate(async () => {
      await Promise.all(
        [...document.querySelectorAll(".fusion-image")].map((i) => i.decode()),
      );
    });
    const textOverflow = await page.locator(".specimen").evaluateAll((es) =>
      es.flatMap((e) => {
        const box = e.getBoundingClientRect();
        return [
          ...e.querySelectorAll(
            "h3,p,.spec-kicker,.spec-footnote,.fusion-label,.graph-label,.graph-secondary,.ring-value",
          ),
        ]
          .filter((n) => {
            const r = document.createRange();
            r.selectNodeContents(n);
            return [...r.getClientRects()].some(
              (b) =>
                b.left < box.left - 1 ||
                b.top < box.top - 1 ||
                b.right > box.right + 1 ||
                b.bottom > box.bottom + 1,
            );
          })
          .map((n) => ({ id: e.dataset.referenceId, text: n.textContent }));
      }),
    );
    assert.deepEqual(textOverflow, []);
    assert(
      await page.evaluate(() =>
        [...document.querySelectorAll(".fusion-image")].every(
          (i) =>
            i.complete &&
            i.naturalWidth === window.StaticReference.catalog.asset.width,
        ),
      ),
    );
    assert(
      await page.evaluate(() => {
        try {
          window.ReferenceEffects.applyCodeStyle(
            document.createElement("div"),
            "unknown",
          );
          return false;
        } catch (e) {
          return e.message === "UNKNOWN_CODE_STYLE";
        }
      }),
    );
    const fonts = await page.evaluate(() =>
      window.ComponentAtlas.catalog.fonts.map((f) => ({
        family: f.family,
        loaded: document.fonts.check(`20px "${f.family}"`),
      })),
    );
    assert(fonts.every((f) => f.loaded));
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("DOM.enable");
    await cdp.send("CSS.enable");
    const doc = await cdp.send("DOM.getDocument");
    const query = await cdp.send("DOM.querySelector", {
      nodeId: doc.root.nodeId,
      selector: "#composition h3",
    });
    const actualFonts = await cdp.send("CSS.getPlatformFontsForNode", {
      nodeId: query.nodeId,
    });
    assert(
      actualFonts.fonts.some(
        (f) => f.glyphCount > 0 && f.familyName.includes("Noto Sans SC"),
      ),
      JSON.stringify(actualFonts),
    );
    const variantFontQuery = await cdp.send("DOM.querySelector", {
      nodeId: doc.root.nodeId,
      selector: '[data-variant-id="PV03"] .sample-text',
    });
    const variantFonts = await cdp.send("CSS.getPlatformFontsForNode", {
      nodeId: variantFontQuery.nodeId,
    });
    assert(
      variantFonts.fonts.some(
        (f) => f.glyphCount > 0 && f.familyName.includes("Noto Serif SC"),
      ),
      "PV03 must use actual Noto Serif SC glyphs",
    );
    const before = await page
      .locator("#atlas .cell")
      .evaluateAll((es) =>
        es.map((e) => [
          e.clientWidth,
          e.clientHeight,
          e.querySelector("[data-component-id]").dataset.componentId,
        ]),
      );
    await page.selectOption("#skin", "blue");
    const after = await page
      .locator("#atlas .cell")
      .evaluateAll((es) =>
        es.map((e) => [
          e.clientWidth,
          e.clientHeight,
          e.querySelector("[data-component-id]").dataset.componentId,
        ]),
      );
    assert.deepEqual(after, before);
    for (const skin of ["amber", "blue"]) {
      await page.selectOption("#skin", skin);
      assert(
        await page
          .locator(".specimen")
          .evaluateAll((es) =>
            es.every(
              (e) =>
                e.scrollWidth <= e.clientWidth + 1 &&
                e.scrollHeight <= e.clientHeight + 1,
            ),
          ),
      );
      assert.equal(await page.locator(".spec-card").count(), 18);
    }
    await capture(
      page.locator("#fusion"),
      path.join(out, "image-fusion-blue.png"),
    );
    assert(
      await page.evaluate(() =>
        window.StylePairs.catalog.pairs.every(
          (p) =>
            document.getElementById(p.id.toLowerCase()).dataset.skin ===
            p.codeStyleRef,
        ),
      ),
    );
    const editorialQuery = await cdp.send("DOM.querySelector", {
      nodeId: doc.root.nodeId,
      selector: "#pair-03 .pair-hero-title",
    });
    const editorialFonts = await cdp.send("CSS.getPlatformFontsForNode", {
      nodeId: editorialQuery.nodeId,
    });
    assert(
      editorialFonts.fonts.some(
        (f) => f.glyphCount > 0 && f.familyName.includes("Noto Serif SC"),
      ),
      JSON.stringify(editorialFonts),
    );
    await page.selectOption("#skin", "neutral");
    assert(
      await page.evaluate(() => {
        const el = window.ComponentAtlas.render("T01", "<img src=x>");
        return !el.querySelector("img") && el.textContent === "<img src=x>";
      }),
    );
    await page.setInputFiles("#image-file", {
      name: "sample.png",
      mimeType: "image/png",
      buffer: fs.readFileSync(path.join(out, "typography.png")),
    });
    await page.waitForFunction(
      () => document.querySelector("#image-slot img")?.complete,
    );
    assert.match(await page.locator("#upload-status").innerText(), /本地/);
    assert.deepEqual(errors, []);
    assert.deepEqual(networkRequests, []);
    const result = {
      status: "passed",
      components: 32,
      presentationVariants: 16,
      variantChecks,
      effects: 28,
      motions: 0,
      staticCompositions: 18,
      stylePairs: 3,
      newImageCalls: 0,
      fontSamples: fonts,
      actualHeadingFonts: actualFonts.fonts,
      actualVariantFonts: variantFonts.fonts,
      actualEditorialFonts: editorialFonts.fonts,
      checks: [
        "white-background actual DOM/SVG screenshots",
        "32 previews fit",
        "16 presentation variants fit and preserve parent identity",
        "distinct emphasis appearances and invalid variant rejection",
        "style changes preserve IDs and geometry",
        "safe text",
        "local image style placement",
        "zero page errors",
        "18 static compositions fit text bounds",
        "actual image readiness",
        "no motion surface",
        "all three code styles fit static compositions",
        "zero network requests",
        "three frozen style pairs and shared content",
        "pair text bounds and image readiness",
        "registered style rejection",
      ],
      visualApproval: "pending",
      productionAdapter: "not_integrated",
      images: [
        "code-components.png",
        "presentation-variants.png",
        "typography.png",
        "style-pairing.png",
        "visual-effects.png",
        "typography-compositions.png",
        "svg-precision.png",
        "effect-usage.png",
        "image-fusion.png",
        "image-fusion-blue.png",
        "style-pair-outline.png",
        "style-pair-depth.png",
        "style-pair-editorial.png",
      ],
    };
    fs.writeFileSync(
      path.join(out, "components-verification.json"),
      JSON.stringify(result, null, 2) + "\n",
    );
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
