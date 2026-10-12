"use strict";
// Actual shared renderer, finite temporal evidence; no alternative animation implementation.
const fs = require("fs"),
  path = require("path"),
  { pathToFileURL } = require("url");
const { chromium } = require("playwright");
const [scenePath, specPath, outDir] = process.argv.slice(2);
(async () => {
  const scene = JSON.parse(fs.readFileSync(scenePath, "utf8")),
    spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
  const dir = path.resolve(outDir);
  fs.mkdirSync(dir, { recursive: true });
  const range = spec.time_range_ms || [0, scene.durationMs],
    step = spec.step_ms || 250;
  if (
    range.length !== 2 ||
    !range.every(Number.isFinite) ||
    range[0] < 0 ||
    range[1] > scene.durationMs ||
    range[0] > range[1] ||
    !Number.isInteger(step) ||
    step < 16 ||
    step > 1000
  )
    throw Error("INVALID_TEMPORAL_RANGE");
  const times = new Set([range[0], range[1]]);
  for (let t = range[0]; t <= range[1]; t += step) times.add(t);
  for (const a of scene.motion)
    for (const t of [
      a.startMs - 1,
      a.startMs,
      a.startMs + a.durationMs / 2,
      a.startMs + a.durationMs,
      a.startMs + a.durationMs + 1,
    ])
      if (t >= range[0] && t <= range[1]) times.add(t);
  const sorted = [...times].sort((a, b) => a - b);
  if (sorted.length > 240) throw Error("TEMPORAL_SAMPLE_BUDGET");
  const pairs = spec.overlap_pairs || [],
    ids = new Set(scene.nodes.map((n) => n.id));
  for (const pair of pairs)
    if (
      !Array.isArray(pair) ||
      pair.length !== 2 ||
      pair[0] === pair[1] ||
      !pair.every((id) => ids.has(id))
    )
      throw Error("INVALID_OVERLAP_PAIR");
  const assets = require("./project-resources.cjs").loadProjectResources();
  const executablePath = require("./browser-runtime.cjs").resolveBrowser(chromium);
  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    const page = await browser.newPage({
        viewport: { width: 1648, height: 1200 },
      }),
      errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(
      pathToFileURL(path.resolve(__dirname, "../visual/preview/index.html"))
        .href,
    );
    await page.waitForFunction(
      () => window.visualPlayer?.ready,
      {},
      { timeout: 20000 },
    );
    const applied = await page.evaluate(
      async ({ scene, assets }) => window.visualPlayer.apply(scene, assets),
      { scene, assets },
    );
    if (!applied) throw Error(await page.locator("#status").innerText());
    const frames = [],
      issues = [],
      screenshots = [];
    const shotTimes = new Set([
      sorted[0],
      sorted[Math.floor(sorted.length / 2)],
      sorted.at(-1),
    ]);
    for (const t of sorted) {
      const frame = await page.evaluate((t) => {
        const r = window.visualPlayer.seek(t),
          visible = {};
        for (const e of document.querySelectorAll("[data-object-id]"))
          visible[e.dataset.objectId] = Number(e.style.opacity);
        return { ...r, visible };
      }, t);
      for (const [a, b] of pairs) {
        if (frame.visible[a] <= 0.01 || frame.visible[b] <= 0.01) continue;
        const x = frame.geometry[a]?.box,
          y = frame.geometry[b]?.box;
        if (!x || !y) throw Error("UNSUPPORTED_PAIR_GEOMETRY");
        if (
          Math.min(x.x + x.width, y.x + y.width) > Math.max(x.x, y.x) + 1 &&
          Math.min(x.y + x.height, y.y + y.height) > Math.max(x.y, y.y) + 1
        )
          issues.push({ code: "TEMPORAL_OVERLAP", timeMs: t, targets: [a, b] });
      }
      for (const n of scene.nodes) {
        if (n.type === "annotation" || frame.visible[n.id] <= 0.01) continue;
        const b = frame.geometry[n.id]?.box;
        if (
          b &&
          (b.x < -1 || b.y < -1 || b.x + b.width > 1601 || b.y + b.height > 801)
        )
          issues.push({
            code: "TEMPORAL_SAFE_ZONE",
            timeMs: t,
            targets: [n.id],
          });
      }
      frames.push(frame);
      if (
        shotTimes.has(t) ||
        (issues.some((i) => i.timeMs === t) && screenshots.length < 6)
      ) {
        const file = `frame-${t}.png`;
        await page
          .locator(".visual-stage")
          .screenshot({ path: path.join(dir, file) });
        screenshots.push({ timeMs: t, file });
      }
    }
    const report = {
      passed: issues.length === 0 && errors.length === 0,
      clock: spec.clock,
      rangeMs: range,
      stepMs: step,
      finiteSampling: true,
      overlapPairs: pairs,
      frames,
      issues,
      pageErrors: errors,
      screenshots,
    };
    fs.writeFileSync(
      path.join(dir, "report.json"),
      JSON.stringify(report, null, 2) + "\n",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(
    path.join(outDir, "report.json"),
    JSON.stringify({
      passed: false,
      code: "TEMPORAL_REVIEW_FAILED",
      message: e.message,
    }),
  );
  process.exitCode = 1;
});
