"use strict";
// Review-only sampling through the production player, including reverse seeks.
const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const { pathToFileURL } = require("node:url");
const root = path.resolve(__dirname, "..");
const engine = path.join(root, "html_engine");
const out = path.join(root, "outputs/token-flow-audit-20261014");
const baseline = Boolean(process.env.AUDIT_BASELINE_PLAYER);
process.env.HPS_HTML_RESOURCES = path.join(out, "run/planning/html_visual/resources.json");
const resources = require(path.join(engine, "tools/project-resources.cjs")).loadProjectResources();
const playwright = require(path.join(engine, "node_modules/playwright"));
const hash = bytes => crypto.createHash("sha256").update(bytes).digest("hex");

(async () => {
  const browser = await playwright.chromium.launch({headless: true,
    executablePath: require(path.join(engine, "tools/browser-runtime.cjs")).resolveBrowser(playwright.chromium)});
  try {
    const page = await browser.newPage({viewport: {width: 1328, height: 1000}, deviceScaleFactor: 1});
    const errors = [];
    page.on("pageerror", error => errors.push(String(error)));
    await page.goto(pathToFileURL(process.env.AUDIT_BASELINE_PLAYER || path.join(engine, "visual/preview/index.html")).href);
    await page.waitForFunction(() => window.visualPlayer?.ready);
    const evidence = [];
    for (let number = 1; number <= 5; number++) {
      const slide = `token-${String(number).padStart(2, "0")}`;
      const folder = path.join(out, slide);
      const scene = JSON.parse(fs.readFileSync(path.join(folder, "after.scene.json")));
      await page.evaluate(async ({scene, resources}) => window.visualPlayer.apply(scene, resources), {scene, resources});
      const stage = page.locator(".visual-stage");
      const times = [...new Set([0, 250, 500, ...scene.motion.flatMap(a => [a.startMs, a.startMs + a.durationMs]), scene.durationMs])].sort((a,b) => a-b);
      const frames = [];
      for (const time of times) {
        await page.evaluate(time => window.visualPlayer.seek(time), time);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const bytes = await stage.screenshot();
        if (!baseline && [0, 500, scene.durationMs].includes(time)) fs.writeFileSync(path.join(folder, `frame-${time}.png`), bytes);
        const domHash = await page.evaluate(() => [...document.querySelectorAll('.visual-stage [data-object-id]')].map(el => el.outerHTML).join(''));
        frames.push({timeMs: time, sha256: hash(bytes), domSha256: hash(domHash)});
      }
      let deterministic = true, domDeterministic = true;
      const mismatches = [];
      for (const frame of [...frames].reverse()) {
        await page.evaluate(time => window.visualPlayer.seek(time), frame.timeMs);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const bytes = await stage.screenshot();
        const domHash = await page.evaluate(() => [...document.querySelectorAll('.visual-stage [data-object-id]')].map(el => el.outerHTML).join(''));
        if (hash(domHash) !== frame.domSha256) domDeterministic = false;
        if (hash(bytes) !== frame.sha256) {
          deterministic = false;
          mismatches.push(frame.timeMs);
          if (!baseline) fs.writeFileSync(path.join(folder, `reverse-${frame.timeMs}.png`), bytes);
        }
      }
      const geometryFailures = [];
      let snapshotImmutable = true;
      for (const action of scene.motion.filter(a => a.type === "enter" && (a.offsetX || a.offsetY) &&
        !["image", "annotation"].includes(scene.nodes.find(n=>n.id === a.targetId)?.type))) {
        const check = await page.evaluate(a => {
          const first = window.visualPlayer.seek(a.startMs).geometry;
          const original = JSON.stringify(first);
          const begin = {...first[a.targetId].box};
          const last = window.visualPlayer.seek(a.startMs + a.durationMs).geometry;
          const end = last[a.targetId].box;
          return {dx: begin.x-end.x, dy: begin.y-end.y, immutable: JSON.stringify(first) === original};
        }, action);
        if (!check.immutable) snapshotImmutable = false;
        if (Math.abs(check.dx-(action.offsetX||0)) > .001 || Math.abs(check.dy-(action.offsetY||0)) > .001)
          geometryFailures.push(action.targetId);
      }
      evidence.push({slide, samples: frames, reverseSeekDeterministic: deterministic,
                     geometryFailures, snapshotImmutable,
                     domDeterministic, mismatches,
                     distinctFrames: new Set(frames.map(f=>f.sha256)).size, pageErrors: [...errors],
                     semanticApproval: false, audioBindingVerified: false});
    }
    fs.writeFileSync(path.join(out, baseline ? "motion-evidence-before.json" : "motion-evidence.json"), JSON.stringify(evidence, null, 2));
    // Render newly generated design AFTER the actual image request completed.
    const scene = JSON.parse(fs.readFileSync(path.join(out, "token-01/before.scene.json")));
    await page.evaluate(async ({scene, resources}) => window.visualPlayer.apply(scene, resources), {scene, resources});
    await page.evaluate(time => window.visualPlayer.seek(time), scene.durationMs);
    if (!baseline) fs.writeFileSync(path.join(out, "new-reconstruction.png"), await page.locator(".visual-stage").screenshot());
    console.log(JSON.stringify(evidence.map(e => ({slide:e.slide, geometryFailures:e.geometryFailures.length, snapshotsImmutable:e.snapshotImmutable, errors:e.pageErrors.length}))));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
