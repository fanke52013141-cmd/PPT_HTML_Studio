"use strict";
const assert = require("node:assert/strict");
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");
const { compile } = require("../src/compiler.cjs");
const { evaluate } = require("../src/timeline.cjs");
const root = path.resolve(__dirname, "..");
const fixtures = ["paper-plane", "cloud-drift"].map((name) =>
  JSON.parse(
    fs.readFileSync(path.join(root, "examples", name + ".scene.json"), "utf8"),
  ),
);
const clone = (value) => structuredClone(value);
const evidence = {
  date: "2026-10-07",
  scope: "E1 standalone prototype",
  unit: [],
  browser: null,
  visualReview:
    "new data-driven renderer pending; motion-02 acceptance not automatically inherited",
};
function test(name, fn) {
  fn();
  evidence.unit.push({ name, passed: true });
}
function rejects(name, change, code) {
  test(name, () => {
    const scene = clone(fixtures[0]);
    change(scene);
    assert.throws(
      () => compile(scene),
      (e) => e.diagnostics?.some((d) => d.code === code),
    );
  });
}

test("Both inputs compile without modifying source", () => {
  for (const source of fixtures) {
    const before = JSON.stringify(source);
    const result = compile(source);
    assert.equal(JSON.stringify(source), before);
    assert(Object.isFrozen(result.source));
  }
});
test("Analytical Bezier midpoint and exact final state", () => {
  const c = compile(fixtures[0]),
    mid = evaluate(c, 4600),
    end = evaluate(c, 10000);
  assert.equal(mid.nodes["main.object"].position.x, 748.75);
  assert.equal(mid.nodes["main.object"].position.y, 466.875);
  assert.deepEqual(end.nodes["main.object"].position, { x: 1270, y: 435 });
  assert.equal(end.nodes.trail.opacity, 0);
  assert.equal(end.nodes["page.caption"].text, fixtures[0].beats[2].screenText);
});
test("Time evaluation independent of access order and fractions", () => {
  const c = compile(fixtures[0]),
    before = evaluate(c, 4666.6666667);
  [10000, 0, 8200, 3500].forEach((t) => evaluate(c, t));
  assert.deepEqual(evaluate(c, 4666.6666667), before);
  for (const t of [-1, 10001, NaN, Infinity])
    assert.throws(() => evaluate(c, t), RangeError);
});
test("Second input changes resource, path and timing without renderer edits", () => {
  const a = compile(fixtures[0]),
    b = compile(fixtures[1]);
  assert.notEqual(
    a.nodeMap.get("main.object").assetRef.id,
    b.nodeMap.get("main.object").assetRef.id,
  );
  assert.notDeepEqual(
    evaluate(a, 4600).nodes["main.object"],
    evaluate(b, 3600).nodes["main.object"],
  );
  assert.equal(evaluate(b, 8000).nodes.trail.opacity, 0);
});
test("Zero-duration action takes final value at its start", () => {
  const s = clone(fixtures[0]);
  s.actions[0].endMs = 0;
  assert.equal(evaluate(compile(s), 0).nodes["main.object"].opacity, 1);
});
test("Adjacent opacity tracks keep then replace state", () => {
  const s = clone(fixtures[0]);
  s.actions.push({
    ...s.actions[0],
    id: "adjacent",
    startMs: 1000,
    endMs: 1500,
    from: 1,
    to: 0,
  });
  const c = compile(s);
  assert.equal(evaluate(c, 1000).nodes["main.object"].opacity, 1);
  assert.equal(evaluate(c, 2000).nodes["main.object"].opacity, 0);
});
test("Reordering source arrays preserves state by stable ID", () => {
  const s = clone(fixtures[0]);
  s.nodes.reverse();
  s.actions.reverse();
  s.beats.reverse();
  s.assets.reverse();
  assert.deepEqual(
    evaluate(compile(s), 4600),
    evaluate(compile(fixtures[0]), 4600),
  );
});
rejects(
  "Unknown document version",
  (s) => (s.schemaVersion = "9.0.0"),
  "UNSUPPORTED_VERSION",
);
rejects("Unknown root field", (s) => (s.script = "alert(1)"), "INVALID_FIELD");
rejects(
  "Unknown node capability",
  (s) => (s.nodes[0].type = "free-html"),
  "UNSUPPORTED_CAPABILITY",
);
rejects(
  "Unknown style CSS is rejected",
  (s) => (s.style.css = "body{display:none}"),
  "INVALID_FIELD",
);
rejects(
  "Duplicate object identity",
  (s) => (s.nodes[1].id = s.nodes[0].id),
  "DUPLICATE_ID",
);
rejects(
  "Missing image reference",
  (s) => (s.nodes[3].assetRef.id = "asset.missing"),
  "MISSING_REFERENCE",
);
rejects(
  "Missing anchor",
  (s) => (s.nodes[3].anchorId = "absent"),
  "MISSING_REFERENCE",
);
rejects(
  "Normalized resource path prevents traversal",
  (s) => (s.assets[0].file.path = "assets/../plane.png"),
  "INVALID_RESOURCE_PATH",
);
rejects(
  "Opacity overlap",
  (s) =>
    s.actions.push({
      ...s.actions[0],
      id: "overlap",
      startMs: 500,
      endMs: 900,
    }),
  "ACTION_CONFLICT",
);
rejects(
  "Tangent move and rotation collide on shared channel",
  (s) =>
    s.actions.push({
      id: "rotate.collision",
      type: "rotate",
      typeVersion: "0.1.0",
      target: { nodeId: "main.object", part: "self" },
      startMs: 2000,
      endMs: 3000,
      easing: "linear",
      fromDeg: -22,
      toDeg: -22,
    }),
  "ACTION_CONFLICT",
);
rejects(
  "Discontinuous motion path",
  (s) => (s.paths[0].points[0].x += 30),
  "STATE_DISCONTINUITY",
);
rejects(
  "Discontinuous opacity",
  (s) => (s.actions[0].from = 0.4),
  "STATE_DISCONTINUITY",
);
rejects(
  "Out of range action",
  (s) => (s.actions[0].endMs = 10001),
  "TIMING_OUT_OF_RANGE",
);
rejects(
  "Narration overlap",
  (s) => (s.beats[1].startMs = 1999),
  "BEAT_CONFLICT",
);
rejects(
  "Missing final keyframe",
  (s) => s.keyframes.pop(),
  "INCOMPLETE_KEYFRAMES",
);
rejects(
  "Text layout outside reading safe area",
  (s) => (s.nodes[0].box.x = 0),
  "INVALID_LAYOUT",
);
rejects(
  "Wrong target type",
  (s) => (s.actions[1].target.nodeId = "page.title"),
  "TARGET_CAPABILITY",
);
rejects(
  "Nonfinite input is rejected, not JSON-normalized away",
  (s) => (s.canvas.width = Infinity),
  "INVALID_FIELD",
);
rejects(
  "Asset bounds are actual resource coordinates",
  (s) => (s.assets[0].alphaBounds.width = 9000),
  "INVALID_ASSET_GEOMETRY",
);

rejects(
  "Resource pixel budget prevents oversized decode sets",
  (s) => {
    s.assets[0].intrinsic = { width: 4096, height: 4096 };
  },
  "RESOURCE_BUDGET",
);
rejects(
  "Canvas layer budget prevents unbounded raster allocations",
  (s) => {
    s.canvas.width = 3840;
    s.canvas.height = 2160;
    const map = new Map(s.nodes.map((n) => [n.id, n]));
    s.nodes = [
      "main.object",
      "page.title",
      "cloud.back",
      "page.subtitle",
      "trail",
      "page.caption",
      "destination",
      "cloud.front",
    ].map((id, i) => ({ ...map.get(id), zIndex: i }));
  },
  "CAPABILITY_BUDGET",
);

rejects(
  "Ring stroke must fit declared geometry",
  (s) => {
    const n = s.nodes.find((n) => n.type === "ring");
    n.box.width = n.strokeWidth;
  },
  "INVALID_VECTOR_GEOMETRY",
);

async function browserChecks() {
  const executable =
    process.env.CHROME_PATH ||
    path.join(
      os.homedir(),
      "AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
    );
  if (!fs.existsSync(executable))
    throw new Error("Set CHROME_PATH to a tested Chromium executable");
  const browser = await chromium.launch({
    headless: true,
    executablePath: executable,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1640, height: 1180 },
      deviceScaleFactor: 1,
    });
    const pageErrors = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await page.goto(pathToFileURL(path.join(root, "preview/index.html")).href);
    await page.evaluate(() => window.e1Ready);
    const output = path.join(root, "evidence/screenshots");
    fs.mkdirSync(output, { recursive: true });
    const snapshots = [],
      renders = [];
    const hash = (buffer) =>
      crypto.createHash("sha256").update(buffer).digest("hex");
    for (let index = 0; index < fixtures.length; index++) {
      await page.evaluate((i) => window.e1.loadScene(i), index);
      snapshots.push(
        await page.evaluate(() => window.e1.controller.getSnapshot()),
      );
      const frames = [];
      for (const frame of fixtures[index].keyframes) {
        const state = await page.evaluate((t) => window.e1.seek(t), frame.tMs);
        const picture = await page
          .locator("#frame")
          .screenshot({ path: path.join(output, `${index}-${frame.id}.png`) });
        const geometry = await page.evaluate(
          (t) =>
            window.e1.controller.getGeometry(
              { nodeId: "main.object", part: "self" },
              t,
            ),
          frame.tMs,
        );
        frames.push({
          id: frame.id,
          tMs: frame.tMs,
          hash: hash(picture),
          state,
          geometry,
        });
      }
      const repeated = [];
      for (const f of [...frames].reverse()) {
        await page.evaluate((t) => window.e1.seek(t), f.tMs);
        const same = hash(await page.locator("#frame").screenshot()) === f.hash;
        assert(same);
        repeated.push({ tMs: f.tMs, same });
      }
      renders.push({ index, frames, repeated });
    }
    // Cold load after another resource/content fixture must reproduce the original scene.
    await page.evaluate(() => window.e1.loadScene(0));
    await page.evaluate(() => window.e1.seek(4600));
    assert.equal(
      hash(await page.locator("#frame").screenshot()),
      renders[0].frames[1].hash,
    );
    const browserFailures = [];
    for (const scenario of [
      "capacity",
      "dynamic-capacity",
      "missing-bytes",
      "hash",
      "dimensions",
      "alpha-bounds",
    ]) {
      const result = await page.evaluate(async (scenario) => {
        const source = structuredClone(window.HPSE1Fixtures.scenes[0]);
        source.revision = 2;
        if (scenario === "capacity")
          source.nodes[0].content.text = "拥挤标题".repeat(100);
        if (scenario === "dynamic-capacity")
          source.beats[2].screenText = "过长的终态文字".repeat(100);
        if (scenario === "missing-bytes")
          source.assets[0].file.path = "assets/missing.png";
        if (scenario === "hash") source.assets[0].file.sha256 = "0".repeat(64);
        if (scenario === "dimensions") source.assets[0].intrinsic.width += 1;
        if (scenario === "alpha-bounds") {
          source.assets[0].alphaBounds.x += 1;
          source.assets[0].alphaBounds.width -= 1;
        }
        const before = window.e1.controller.getSnapshot().inputFingerprint;
        try {
          await window.e1.controller.load(source);
          return { accepted: true };
        } catch (error) {
          return {
            accepted: false,
            code: error.code,
            preserved:
              before === window.e1.controller.getSnapshot().inputFingerprint,
            stages: document.querySelectorAll(".e1-stage").length,
          };
        }
      }, scenario);
      const expected = {
        capacity: "CONTENT_CAPACITY_EXCEEDED",
        "dynamic-capacity": "CONTENT_CAPACITY_EXCEEDED",
        "missing-bytes": "ASSET_UNAVAILABLE",
        hash: "ASSET_HASH_MISMATCH",
        dimensions: "ASSET_DIMENSION_MISMATCH",
        "alpha-bounds": "ASSET_ALPHA_BOUNDS_MISMATCH",
      }[scenario];
      assert.equal(result.code, expected);
      assert(result.preserved);
      assert.equal(result.stages, 1);
      browserFailures.push({ scenario, ...result });
    }
    const edit = clone(fixtures[0]);
    edit.revision = 2;
    edit.nodes[1].content.text = "<img src=x onerror=alert(1)> 内容保持纯文本";
    await page
      .locator("#editor-panel")
      .evaluate((element) => (element.open = true));
    await page.locator("#editor").fill(JSON.stringify(edit));
    await page.locator("#apply").click();
    await page.waitForFunction(
      (text) =>
        window.e1.controller.current.compiled.source.nodes.find(
          (n) => n.id === "page.subtitle",
        ).content.text === text,
      edit.nodes[1].content.text,
    );
    await page
      .locator("#editor-panel")
      .evaluate((element) => (element.open = false));
    await page.evaluate(() => window.scrollTo(0, 0));
    assert.equal(
      await page.locator('[data-target="page.subtitle"]').textContent(),
      edit.nodes[1].content.text,
    );
    assert.equal(
      await page.locator(".e1-stage img,.e1-stage script").count(),
      0,
    );
    const quarterTurn = clone(fixtures[0]);
    quarterTurn.revision = 3;
    quarterTurn.nodes.find((n) => n.id === "main.object").rotationDeg = 90;
    quarterTurn.actions = quarterTurn.actions.filter(
      (a) => a.type !== "move-path",
    );
    await page.evaluate((source) => window.e1.applyInput(source), quarterTurn);
    const turned = await page.evaluate(() =>
      window.e1.controller.getGeometry(
        { nodeId: "main.object", part: "self" },
        1000,
      ),
    );
    const expectedCorners = [
      { x: 470, y: 380 },
      { x: 470, y: 760 },
      { x: 90, y: 760 },
      { x: 90, y: 380 },
    ];
    turned.polygons[0].forEach((p, i) => {
      assert(Math.abs(p.x - expectedCorners[i].x) < 1e-6);
      assert(Math.abs(p.y - expectedCorners[i].y) < 1e-6);
    });
    const race = await page.evaluate(async () => {
      const results = await Promise.allSettled([
        window.e1.controller.load(window.HPSE1Fixtures.scenes[0]),
        window.e1.controller.load(window.HPSE1Fixtures.scenes[1]),
      ]);
      return {
        results: results.map((r) => ({
          status: r.status,
          code: r.reason?.code,
        })),
        current: window.e1.controller.getSnapshot().source.id,
        stages: document.querySelectorAll(".e1-stage").length,
      };
    });
    assert.equal(race.results[0].code, "LOAD_SUPERSEDED");
    assert.equal(race.current, fixtures[1].id);
    assert.equal(race.stages, 1);
    await page.evaluate(() => window.e1.loadScene(0));
    await page.evaluate(() => window.e1.seek(4600));
    await page.locator("#play").click();
    await page.waitForTimeout(130);
    await page.locator("#play").click();
    const paused = await page.evaluate(() => window.e1.timeMs);
    await page.waitForTimeout(140);
    assert.equal(await page.evaluate(() => window.e1.timeMs), paused);
    await page.selectOption("#direction", "-1");
    await page.locator("#play").click();
    await page.waitForTimeout(140);
    await page.locator("#play").click();
    const reverse = await page.evaluate(() => window.e1.timeMs);
    assert(reverse < paused);
    const client = await page.context().newCDPSession(page);
    await client.send("DOM.enable");
    await client.send("CSS.enable");
    const { root: dom } = await client.send("DOM.getDocument");
    const fonts = [];
    for (const id of ["page.title", "page.caption"]) {
      const { nodeId } = await client.send("DOM.querySelector", {
        nodeId: dom.nodeId,
        selector: `[data-target="${id}"]`,
      });
      const result = await client.send("CSS.getPlatformFontsForNode", {
        nodeId,
      });
      fonts.push({ id, fonts: result.fonts });
      assert(result.fonts.some((f) => /Microsoft YaHei/i.test(f.familyName)));
    }
    const beforeScale = await page.evaluate(() =>
      window.e1.controller.getGeometry(
        { nodeId: "page.title", part: "self" },
        4600,
      ),
    );
    await page.setViewportSize({ width: 1366, height: 1050 });
    await page.waitForTimeout(50);
    const afterScale = await page.evaluate(() =>
      window.e1.controller.getGeometry(
        { nodeId: "page.title", part: "self" },
        4600,
      ),
    );
    assert(Math.abs(beforeScale.rects[0].x - afterScale.rects[0].x) < 0.1);
    assert(
      Math.abs(beforeScale.rects[0].width - afterScale.rects[0].width) < 0.1,
    );
    const viewport = await page.evaluate(() => ({
      width: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    assert(viewport.width === viewport.scrollWidth);
    await page.screenshot({ path: path.join(output, "viewer.png") });
    assert.deepEqual(pageErrors, []);
    evidence.browser = {
      version: browser.version(),
      frames: renders,
      failures: browserFailures,
      rotatedGeometry: turned,
      race,
      pauseStable: true,
      reverse: true,
      editorApply: "DOM textarea and apply button verified",
      textInjection: "rendered literally; no image/script nodes",
      platformFonts: fonts,
      scaledGeometryStable: true,
      viewport,
      pageErrors,
    };
    fs.writeFileSync(
      path.join(root, "evidence/compiled-snapshots.json"),
      JSON.stringify(snapshots, null, 2) + "\n",
    );
  } finally {
    await browser.close();
  }
}

browserChecks()
  .then(() => {
    fs.writeFileSync(
      path.join(root, "evidence/checks.json"),
      JSON.stringify(evidence, null, 2) + "\n",
    );
    console.log(
      JSON.stringify({
        unitCases: evidence.unit.length,
        scenes: 2,
        pixelRepeatable: true,
        resourceAndCapacityFailuresBlocked: true,
        geometryVerified: true,
        pageErrors: evidence.browser.pageErrors,
      }),
    );
  })
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
