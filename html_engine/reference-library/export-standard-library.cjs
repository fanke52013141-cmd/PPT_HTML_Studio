const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict"),
  crypto = require("crypto");
const { pathToFileURL } = require("url");
const { chromium } = require("../node_modules/playwright");
const root = __dirname,
  out = path.join(root, "standard");
const sha = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
async function writeShot(locator, name) {
  const bytes = await locator.screenshot({ animations: "disabled" });
  const target = path.join(out, name);
  fs.writeFileSync(target + ".tmp", bytes);
  fs.renameSync(target + ".tmp", target);
  return {
    filename: name,
    sha256: sha(bytes),
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
  };
}
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.HPS_CHROME,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 2000, height: 1200 },
      deviceScaleFactor: 1,
    });
    const errors = [],
      remote = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => {
      if (/^https?:/.test(r.url())) remote.push(r.url());
    });
    await page.goto(
      pathToFileURL(path.join(root, "standard-library.html")).href,
    );
    await page.waitForFunction(() => window.StandardLibrary?.ready);
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() =>
      Promise.all([...document.images].map((i) => i.decode())),
    );
    const catalog = JSON.parse(
      fs.readFileSync(path.join(root, "standard-pages.json"), "utf8"),
    );
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("DOM.enable");
    await cdp.send("CSS.enable");
    const { root: domRoot } = await cdp.send("DOM.getDocument");
    const actualFonts = [];
    for (const font of catalog.pages.find((p) => p.kind === "font").ids) {
      const { nodeId } = await cdp.send("DOM.querySelector", {
        nodeId: domRoot.nodeId,
        selector: `#fonts [data-entry-id="${font}"] .standard-font p`,
      });
      const { fonts } = await cdp.send("CSS.getPlatformFontsForNode", {
        nodeId,
      });
      assert.ok(
        fonts.some((f) => f.glyphCount > 0),
        font + ":missing actual glyphs",
      );
      actualFonts.push({ id: font, fonts });
    }
    const validation = await page.evaluate(() => {
      const issues = [];
      for (const list of [
        window.ComponentCatalog.items,
        window.PresentationVariants.items,
        window.EffectsCatalog.items,
        window.StaticCatalog.items,
        window.ComponentCatalog.fonts,
      ])
        for (const item of list) {
          try {
            const node = window.StandardLibrary.render({ id: item.id });
            if (node.dataset.referenceId !== item.id)
              issues.push("API identity:" + item.id);
          } catch (e) {
            issues.push("API render:" + item.id + ":" + e.message);
          }
        }
      for (const board of document.querySelectorAll(".standard-page")) {
        const b = board.getBoundingClientRect();
        if (b.width !== 1920 || b.height !== 1080)
          issues.push(board.id + ":canvas");
        for (const node of board.querySelectorAll(
          ".standard-cell,.standard-header,.standard-footer,.component,.specimen,.fusion-image",
        )) {
          const r = node.getBoundingClientRect();
          if (
            r.left < b.left - 0.5 ||
            r.top < b.top - 0.5 ||
            r.right > b.right + 0.5 ||
            r.bottom > b.bottom + 0.5
          )
            issues.push(board.id + ":overflow:" + node.className);
        }
        for (const node of board.querySelectorAll(
          ".sample-text,.sample-card strong,.sample-card p,.spec-heading,.spec-copy,.standard-note",
        )) {
          if (node.scrollWidth > node.clientWidth + 1 && node.clientWidth > 0)
            issues.push(board.id + ":text-overflow:" + node.textContent);
        }
      }
      const donut = document.querySelector(
        '[data-reference-id="D02"] circle[stroke-dasharray]',
      );
      if (getComputedStyle(donut).strokeWidth !== "12px")
        issues.push("D02:stroke");
      const bad = [
        { id: "missing" },
        { id: "T01", variantId: "PV09" },
        { id: "T01", text: "x".repeat(37) },
        { id: "T01", paletteId: "missing" },
      ];
      for (const args of bad) {
        let rejected = false;
        try {
          window.StandardLibrary.render(args);
        } catch {
          rejected = true;
        }
        if (!rejected) issues.push("API accepted invalid input");
      }
      const safe = window.StandardLibrary.render({
        id: "T01",
        text: "<img src=x onerror=alert(1)>",
      });
      if (safe.querySelector("img")) issues.push("API unsafe text");
      return {
        issues,
        coverage: {
          components: window.ComponentCatalog.items.length,
          variants: window.PresentationVariants.items.length,
          effects: window.EffectsCatalog.items.length,
          compositions: window.StaticCatalog.items.length,
          fonts: window.ComponentCatalog.fonts.length,
        },
        fonts: window.ComponentCatalog.fonts.map((f) => ({
          family: f.family,
          available: document.fonts.check('20px "' + f.family + '"'),
        })),
      };
    });
    assert.deepEqual(errors, []);
    assert.deepEqual(remote, []);
    assert.deepEqual(validation.issues, []);
    assert.equal(catalog.pages.length, 24);
    for (const p of catalog.pages.filter((p) => p.kind !== "overview"))
      assert.deepEqual(
        await page
          .locator("#" + p.id + " [data-entry-id]")
          .evaluateAll((nodes) => nodes.map((n) => n.dataset.entryId)),
        p.ids,
      );
    const files = [];
    for (const p of catalog.pages)
      files.push({
        id: p.id,
        ids: p.ids,
        ...(await writeShot(page.locator("#" + p.id), p.id + ".png")),
      });
    for (const f of files) {
      assert.equal(f.width, 1920);
      assert.equal(f.height, 1080);
    }
    await page.setContent(
      '<html><body style="margin:0;background:white"><main style="filter:grayscale(1);color:#222;width:fit-content;display:grid;grid-template-columns:repeat(4,480px);gap:12px;padding:12px">' +
        files
          .map(
            (f) =>
              '<div><img style="display:block;width:480px;height:270px" src="data:image/png;base64,' +
              fs.readFileSync(path.join(out, f.filename)).toString("base64") +
              '"><p style="font:14px Arial;margin:4px">' +
              f.id +
              "</p></div>",
          )
          .join("") +
        "</main></body></html>",
    );
    await page.evaluate(() =>
      Promise.all([...document.images].map((i) => i.decode())),
    );
    await writeShot(page.locator("main"), "contact-sheet.png");
    fs.writeFileSync(
      path.join(out, "manifest.json"),
      JSON.stringify(
        {
          version: "1.0.0",
          scope: "static-reference-only",
          sourceSha256: sha(
            fs.readFileSync(path.join(root, "standard-library.html")),
          ),
          files,
          validation,
          actualFonts,
          visualReview: "pending",
          productionAdapter: "not_integrated",
        },
        null,
        2,
      ) + "\n",
    );
    console.log(JSON.stringify({ pages: files.length, ...validation }));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
