"use strict";
const assert = require("node:assert/strict"),
  fs = require("fs"),
  path = require("path");
const { pathToFileURL } = require("url"),
  { chromium } = require("playwright");
const { compile } = require("../compiler.cjs");
const root = path.resolve(__dirname, ".."),
  read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));
const catalog = read("generated/catalog.json"),
  scenes = fs
    .readdirSync(path.join(root, "scenes"))
    .filter((p) => p.endsWith(".json"))
    .sort()
    .map((p) => read(`scenes/${p}`)),
  byId = Object.fromEntries(scenes.map((s) => [s.id, s])),
  cup = byId.condensation,
  facts = byId["water-facts"];
const clone = (v) => structuredClone(v);
function rejected(change, code) {
  const s = clone(cup);
  change(s);
  assert.throws(() => compile(s, catalog), new RegExp(code));
}
async function main() {
  // Node-side structural checks (no browser required).
  assert(Object.isFrozen(compile(cup, catalog).source));
  for (const s of scenes) compile(s, catalog);
  // Legacy 0.1.0 documents stay readable through the explicit adapter.
  for (const name of ["condensation", "evaporation"])
    compile(read(`fixtures/legacy-0.1.0/${name}.json`), catalog);
  rejected((s) => (s.style = { color: "red" }), "INVALID_VISUAL_DEFINITION");
  rejected((s) => (s.themeRef.id = "missing"), "UNRESOLVED_REFERENCE");
  rejected((s) => (s.version = "9.9.9"), "UNSUPPORTED_VERSION");
  rejected((s) => (s.nodes[0].slot = "missing"), "UNRESOLVED_SLOT");
  rejected((s) => (s.nodes[0].slot = "constructor"), "UNRESOLVED_SLOT");
  rejected((s) => (s.nodes[1].id = s.nodes[0].id), "DUPLICATE_TARGET");
  rejected(
    (s) => (s.nodes.find((n) => n.type === "annotation").anchorId = "missing"),
    "UNRESOLVED_ANCHOR",
  );
  rejected((s) => (s.motion[0].startMs = s.durationMs), "INVALID_TIME");
  rejected((s) => (s.motion[0].offsetX = -100), "CONTENT_SAFE_ZONE");
  rejected((s) => (s.beats[1].startMs = 0), "INVALID_TIME");
  rejected(
    (s) => (s.nodes.find((n) => n.type === "card").icon = "rocket"),
    "UNKNOWN_ICON",
  );
  rejected((s) => (s.templateRef = { id: "missing", version: "0.1.0" }), "UNRESOLVED_REFERENCE");
  rejected(
    (s) => (s.templateRef = { id: "process-stage-v1", version: "0.1.0" }),
    "TEMPLATE_LAYOUT_MISMATCH",
  );
  const kindSwap = clone(facts);
  const caption = kindSwap.nodes.find((n) => n.id === "caption");
  const captionText = caption.runs.map((r) => r.text).join("");
  delete caption.runs;
  caption.type = "label";
  caption.role = "phase";
  caption.tone = "blue";
  caption.text = captionText;
  assert.throws(() => compile(kindSwap, catalog), /TEMPLATE_SLOT_KIND/);
  const withoutCard = clone(cup);
  withoutCard.nodes = withoutCard.nodes.filter((n) => n.id !== "card-2");
  withoutCard.motion = withoutCard.motion.filter((a) => a.targetId !== "card-2");
  assert.throws(
    () => compile(withoutCard, catalog),
    /TEMPLATE_SLOT_REQUIRED/,
  );
  const withTemplate = clone(facts);
  delete withTemplate.templateRef;
  compile(withTemplate, catalog);
  rejected((s) => {
    delete s.templateRef;
    s.nodes = s.nodes.filter((n) => n.id !== "headline");
    s.motion = s.motion.filter((a) => a.targetId !== "headline");
    s.nodes.push({
      ...clone(s.nodes.find((n) => n.type === "image")),
      id: "second",
      slot: "headline",
    });
    s.motion.push({
      targetId: "second",
      type: "enter",
      startMs: 0,
      durationMs: 850,
      offsetX: 0,
      offsetY: 0,
    });
  }, "ASSET_BUDGET_EXCEEDED");
  const styledCatalog = clone(catalog);
  styledCatalog.themes.find((t) => t.id === cup.themeRef.id).position = {
    x: 100,
  };
  assert.throws(() => compile(cup, styledCatalog), /INVALID_VISUAL_DEFINITION/);
  const incompatible = clone(catalog);
  incompatible.themes.find((t) => t.id === cup.themeRef.id).compatibleLayouts =
    ["object-left"];
  assert.throws(() => compile(cup, incompatible), /INCOMPATIBLE_THEME_LAYOUT/);
  // Browser checks share one page across every registered scene.
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.HPS_CHROME ||
      "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
  });
  const page = await browser.newPage({
    viewport: { width: 1648, height: 1200 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const evidence = {
    format: "hps.visual.stage1.evidence",
    checks: [],
    scenes: [],
  };
  try {
    await page.goto(pathToFileURL(path.join(root, "preview/index.html")).href);
    await page.waitForFunction(
      () => window.visualPlayer?.ready,
      {},
      { timeout: 15000 },
    );
    const apply = async (s) =>
      assert.equal(
        await page.evaluate((v) => window.visualPlayer.apply(v), s),
        true,
        await page.locator("#status").innerText(),
      );
    for (const s of scenes) {
      await apply(s);
      const final = await page.evaluate(
        (t) => window.visualPlayer.seek(t),
        s.durationMs,
      );
      const first = await page.locator(".visual-stage").screenshot();
      await page.evaluate((t) => window.visualPlayer.seek(t), Math.floor(s.durationMs / 3));
      await page.evaluate((t) => window.visualPlayer.seek(t), s.durationMs);
      assert(
        first.equals(await page.locator(".visual-stage").screenshot()),
        "Random seeking must return identical pixels",
      );
      fs.mkdirSync(path.join(root, "evidence"), { recursive: true });
      fs.writeFileSync(path.join(root, "evidence", s.id + "-final.png"), first);
      evidence.scenes.push({
        id: s.id,
        layout: s.layoutRef,
        template: s.templateRef ?? null,
        measurements: final.measurements,
        geometry: final.geometry,
      });
      for (const size of [20, 32, 44]) {
        await page.evaluate(
          (n) => window.visualPlayer.setSubtitleFont(n),
          size,
        );
        const zone = await page.evaluate(() => {
          const stage = document
              .querySelector(".visual-stage")
              .getBoundingClientRect(),
            b = document
              .querySelector('[data-track="subtitle"]')
              .getBoundingClientRect();
          return {
            y: ((b.y - stage.y) * 1600) / stage.width,
            height: (b.height * 1600) / stage.width,
          };
        });
        assert(
          Math.abs(zone.y - 800) < 0.01 && Math.abs(zone.height - 100) < 0.01,
        );
      }
    }
    const moving = clone(cup);
    const enter = moving.motion.find((a) => a.targetId === "subject");
    enter.startMs = 0;
    enter.durationMs = 5000;
    enter.offsetY = 40;
    moving.motion.find((a) => a.targetId === "annotation").startMs = 0;
    await apply(moving);
    for (const width of [1648, 1048]) {
      await page.setViewportSize({ width, height: 1200 });
      await page.waitForTimeout(50);
      for (const time of [0, 2500, 5000, 18000]) {
        const r = await page.evaluate((t) => window.visualPlayer.seek(t), time);
        const dom = await page.evaluate(() => {
          const stage = document
              .querySelector(".visual-stage")
              .getBoundingClientRect(),
            c = document
              .querySelector('[data-object-id="annotation"] circle')
              .getBoundingClientRect();
          return {
            x: ((c.x + c.width / 2 - stage.x) * 1600) / stage.width,
            y: ((c.y + c.height / 2 - stage.y) * 1600) / stage.width,
          };
        });
        assert(
          Math.abs(dom.x - r.geometry.subject.anchors.focus.x) < 0.02 &&
            Math.abs(dom.y - r.geometry.subject.anchors.focus.y) < 0.02,
          "Anchor must follow transformed image at both viewport sizes",
        );
      }
    }
    await page.setViewportSize({ width: 1648, height: 1200 });
    await apply(cup);
    const themed = clone(cup);
    themed.themeRef.id = "neutral-science";
    const before = await page.evaluate(
      (t) => window.visualPlayer.seek(t),
      cup.durationMs,
    );
    await apply(themed);
    const after = await page.evaluate(
      (t) => window.visualPlayer.seek(t),
      cup.durationMs,
    );
    assert.deepEqual(before.geometry, after.geometry);
    assert.deepEqual(before.measurements, after.measurements);
    assert.deepEqual(themed.nodes, cup.nodes);
    const old = await page.evaluate(() => window.visualPlayer.scene.id);
    const long = clone(cup);
    long.nodes.find((n) => n.id === "headline").runs[0].text =
      "超长内容".repeat(40);
    assert.equal(
      await page.evaluate((s) => window.visualPlayer.apply(s), long),
      false,
    );
    assert.equal(await page.evaluate(() => window.visualPlayer.scene.id), old);
    assert.match(
      await page.locator("#status").innerText(),
      /CONTENT_CAPACITY_EXCEEDED/,
    );
    const malicious = clone(cup);
    malicious.nodes.find((n) => n.id === "intro").runs[0].text =
      "<img src=x onerror=alert(1)>";
    await apply(malicious);
    assert.equal(
      await page.locator('[data-object-id="intro"] img').count(),
      0,
    );
    await apply(cup);
    await page.evaluate(() => window.visualPlayer.play());
    await page.waitForTimeout(250);
    assert((await page.evaluate(() => window.visualPlayer.timeMs)) > 100);
    await page.evaluate(() => window.visualPlayer.pause());
    const paused = await page.evaluate(() => window.visualPlayer.timeMs);
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(() => window.visualPlayer.timeMs), paused);
    const gap = clone(cup);
    gap.beats[0].endMs = 1000;
    await apply(gap);
    await page.evaluate(() => window.visualPlayer.seek(2000));
    assert.equal(await page.locator('[data-track="subtitle"]').innerText(), "");
    await apply(cup);
    const assetKey = catalog.assets[0].file.path;
    await page.evaluate(
      (key) => (window.VisualData.pack[key] = "AA=="),
      assetKey,
    );
    assert.equal(
      await page.evaluate((s) => window.visualPlayer.apply(s), cup),
      false,
    );
    assert.match(
      await page.locator("#status").innerText(),
      /ASSET_HASH_MISMATCH/,
    );
    assert.equal(
      await page.evaluate(() => window.visualPlayer.scene.id),
      cup.id,
    );
    assert.deepEqual(errors, []);
    evidence.checks = [
      "strict fields and ownership",
      "references, icons, templates and time",
      "legacy 0.1.0 adapter",
      "four contents / three structures / two themes",
      "seek pixel determinism",
      "transformed anchor / two viewport sizes",
      "theme preserves semantics and geometry",
      "text capacity blocks atomic commit",
      "safe text content",
      "play and pause",
      "subtitle 20/32/44 fixed safe zone and empty gap",
      "asset hash blocks commit",
      "no page errors",
    ];
    fs.writeFileSync(
      path.join(root, "evidence/verification.json"),
      JSON.stringify(evidence, null, 2) + "\n",
    );
    console.log(
      JSON.stringify({
        passed: evidence.checks.length,
        scenes: scenes.length,
        pageErrors: 0,
      }),
    );
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
