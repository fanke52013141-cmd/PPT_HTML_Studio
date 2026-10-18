"use strict";
const assert = require("node:assert/strict"),
  fs = require("fs"),
  path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("../html_engine/node_modules/playwright");
const software = process.argv[3] !== "default";
const { PNG } = require("../html_engine/node_modules/pngjs");
const { compile } = require("../html_engine/visual/compiler.cjs");
const root = path.resolve(__dirname, ".."),
  directory = process.argv[2];
const catalog = JSON.parse(
  fs.readFileSync(path.join(root, "html_engine/visual/generated/catalog.json")),
);
const scenes = [1, 2, 3, 4].map((i) =>
  JSON.parse(fs.readFileSync(path.join(directory, `slide_00${i}.json`))),
);
for (const s of scenes) compile(s, catalog);
let bad = structuredClone(scenes[0]);
delete bad.nodes.find((n) => n.type === "arrow" && n.from).to;
assert.throws(() => compile(bad, catalog));
bad = structuredClone(scenes[0]);
bad.nodes.find((n) => n.type === "arrow" && n.from).from.objectId = "missing";
assert.throws(() => compile(bad, catalog), /INVALID_RELATION_ENDPOINT/);
bad = structuredClone(scenes[2]);
bad.nodes.find((n) => n.type === "chart").points[2].y = 0.8;
assert.throws(() => compile(bad, catalog), /INVALID_CHART_PLATEAU/);
bad = structuredClone(scenes[0]);
bad.motion.find((a) => a.targetId === "relation-1").offsetY = 10;
assert.throws(() => compile(bad, catalog), /RELATION_GEOMETRY_OWNED/);
bad = structuredClone(scenes[0]);
const zero = bad.nodes.find((n) => n.type === "arrow" && n.from);
zero.from = { objectId: "subject", point: { x: 0.5, y: 0.5 } };
zero.to = { objectId: "subject", point: { y: 0.5, x: 0.5 } };
assert.throws(() => compile(bad, catalog), /INVALID_RELATION_ENDPOINT/);
(async () => {
  const runtime = require("../html_engine/tools/browser-runtime.cjs");
  const browser = await chromium.launch(software
    ? runtime.captureLaunchOptions(chromium)
    : {headless: true, executablePath: runtime.resolveBrowser(chromium)});
  const results = [];
  try {
    for (const width of [1592, 1600])
      for (const dpr of [1, 2]) {
        const context = await browser.newContext({
          viewport: { width: 1660, height: 1100 },
          deviceScaleFactor: dpr,
        });
        const page = await context.newPage();
        const errors = [];
        page.on("pageerror", (e) => errors.push(e.message));
        await page.goto(
          pathToFileURL(
            path.join(root, "html_engine/visual/preview/index.html"),
          ).href,
        );
        await page.waitForFunction(() => window.visualPlayer?.ready);
        await page.addStyleTag({
          content: `#viewport{width:${width}px;max-width:none}main{max-width:none}`,
        });
        for (const scene of scenes) {
          assert.equal(
            await page.evaluate((s) => window.visualPlayer.apply(s), scene),
            true,
            await page.locator("#status").innerText(),
          );
          await page.evaluate(
            (t) => window.visualPlayer.seek(t),
            scene.durationMs,
          );
          for (const n of scene.nodes.filter((n) => n.type === "card")) {
            const b = await page
              .locator(`[data-object-id="${n.id}"]`)
              .evaluate((el) => ({
                border: getComputedStyle(el).borderTopWidth,
                bg: getComputedStyle(el).backgroundColor,
              }));
            assert.equal(b.border, "1px");
            assert.equal(b.bg, "rgb(255, 255, 255)");
          }
          if (scene.id === "slide_002") {
            assert.equal(
              await page
                .locator('[data-object-id="figure"]')
                .evaluate((el) => getComputedStyle(el).borderTopStyle),
              "dashed",
            );
            assert.equal(
              await page
                .locator('[data-object-id="annotation"] svg path')
                .last()
                .getAttribute("d"),
              "",
            );
          }
          if (scene.id === "slide_003")
            assert.equal(await page.locator("[data-chart-label]").count(), 5);
          await page.evaluate(
            () =>
              new Promise((r) =>
                requestAnimationFrame(() => requestAnimationFrame(r)),
              ),
          );
          const domBefore = await page
            .locator(".visual-stage")
            .evaluate((el) => el.outerHTML);
          const png = await page.locator(".visual-stage").screenshot();
          fs.writeFileSync(
            path.join(directory, `${scene.id}-${width}-dpr${dpr}.png`),
            png,
          );
          for (const t of [
            scene.durationMs * 0.6,
            0,
            scene.durationMs * 0.3,
            scene.durationMs,
          ])
            await page.evaluate((t) => window.visualPlayer.seek(t), t);
          await page.evaluate(
            () =>
              new Promise((r) =>
                requestAnimationFrame(() => requestAnimationFrame(r)),
              ),
          );
          assert.equal(
            await page.locator(".visual-stage").evaluate((el) => el.outerHTML),
            domBefore,
            "Seek changed final DOM state",
          );
          const second = await page.locator(".visual-stage").screenshot();
          const pixelExact = PNG.sync
            .read(png)
            .data.equals(PNG.sync.read(second).data);
          if (!pixelExact)
            fs.writeFileSync(
              path.join(directory, `${scene.id}-${width}-dpr${dpr}-after.png`),
              second,
            );
          // Verify a relation follows its moving endpoint in author coordinates.
          const relation = scene.nodes.find(
            (n) => n.type === "arrow" && n.from && n.from.point,
          );
          const target = scene.nodes.find(
              (n) => n.id === relation.from.objectId,
            ),
            motion = scene.motion.find((a) => a.targetId === target.id);
          await page.evaluate(
            (t) => window.visualPlayer.seek(t),
            motion.startMs,
          );
          const startPath = await page
            .locator(`[data-object-id="${relation.id}"] svg path`)
            .first()
            .getAttribute("d");
          const compiled = compile(scene, catalog),
            box = compiled.layout.slots[target.slot].box;
          const match = startPath.match(/^M ([^ ]+) ([^ ]+)/);
          assert(
            Math.abs(
              Number(match[1]) -
                (box.x + box.width * relation.from.point.x + motion.offsetX),
            ) < 0.001,
          );
          assert(
            Math.abs(
              Number(match[2]) -
                (box.y + box.height * relation.from.point.y + motion.offsetY),
            ) < 0.001,
          );
          results.push({
            slide: scene.id,
            width,
            dpr,
            structurePassed: true,
            pixelExact,
          });
        }
        assert.deepEqual(errors, []);
        await context.close();
      }
    fs.writeFileSync(
      path.join(directory, "browser-report.json"),
      JSON.stringify(
        {
          backend: software ? "software" : "default",
          structurePassed: true,
          pixelExact: results.every((r) => r.pixelExact),
          fixturesOnly: true,
          providerCalls: 0,
          results,
        },
        null,
        2,
      ),
    );
    console.log(
      JSON.stringify({
        structurePassed: true,
        pixelExact: results.every((r) => r.pixelExact),
        cases: results.length,
      }),
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
