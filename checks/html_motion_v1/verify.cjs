"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { createTimeline } = require("../../html_engine/motion-research/node_modules/animejs");
const { chromium } = require("../../html_engine/node_modules/playwright");
const { PNG } = require("../../html_engine/node_modules/pngjs");
const { compile } = require("../../html_engine/visual/compiler.cjs");

const repo = path.resolve(__dirname, "../..");
const visual = path.join(repo, "html_engine/visual");
const output = path.join(repo, "html_engine/motion-research/results");
const fixturePath = path.join(__dirname, "fixtures/neutral-actions.json");
const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const catalog = JSON.parse(
  fs.readFileSync(path.join(visual, "generated/catalog.json"), "utf8"),
);
const themeOverrides = JSON.parse(
  fs.readFileSync(
    path.join(repo, "html_engine/motion-research/neutral-theme-overrides.json"),
    "utf8",
  ),
);
const neutralTheme = structuredClone(
  catalog.themes.find((item) => item.id === "amber-editorial"),
);
Object.assign(neutralTheme, themeOverrides);
catalog.themes.push(neutralTheme);
const fixtureHash = crypto
  .createHash("sha256")
  .update(fs.readFileSync(fixturePath))
  .digest("hex");
const sha256File = (file) =>
  crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const smoothstep = (p) => {
  const x = Math.max(0, Math.min(1, p));
  return x * x * (3 - 2 * x);
};
const samples = [
  0,
  336.999,
  337,
  337.001,
  1113.999,
  1114,
  1102.999,
  1103,
  1453.5,
  1804,
  2500.999,
  2501,
  2951,
  3401,
  6000.999,
  6001,
  6301.5,
  6602,
  7300,
  2501,
  337,
  0,
];

function makeAnimeScene(scene) {
  const timeline = createTimeline({ autoplay: false });
  const states = {};
  for (const node of scene.nodes) {
    const actions = scene.motion.filter((item) => item.targetId === node.id);
    const enter = actions.find((item) => item.type === "enter");
    assert(enter, "the fixed fixture requires an enter action per object");
    const state = {
      opacity: 0,
      x: enter.offsetX,
      y: enter.offsetY,
    };
    states[node.id] = state;
    timeline.add(
      state,
      {
        opacity: [0, 1],
        x: [enter.offsetX, 0],
        y: [enter.offsetY, 0],
        duration: enter.durationMs,
        ease: smoothstep,
      },
      enter.startMs,
    );
    for (const action of actions) {
      if (action.type === "emphasize") {
        const half = action.durationMs / 2;
        timeline.add(
          state,
          { y: [0, -8], duration: half, ease: smoothstep },
          action.startMs,
        );
        timeline.add(
          state,
          { y: [-8, 0], duration: half, ease: smoothstep },
          action.startMs + half,
        );
      } else if (action.type === "exit") {
        timeline.add(
          state,
          {
            opacity: [1, 0],
            duration: action.durationMs,
            ease: smoothstep,
          },
          action.startMs,
        );
      }
    }
  }
  return { timeline, states };
}

function compareStates(runtime, candidate, scene) {
  let maxAbsError = 0;
  for (const node of scene.nodes) {
    const expected = candidate[node.id];
    const actual = runtime[node.id];
    for (const key of ["opacity", "x", "y"]) {
      const error = Math.abs(actual[key] - expected[key]);
      maxAbsError = Math.max(maxAbsError, error);
      assert(
        error < 1e-4,
        node.id +
          "." +
          key +
          " differs by " +
          error +
          " at " +
          runtime.timeMs +
          " (current=" +
          actual[key] +
          ", anime=" +
          expected[key] +
          ")",
      );
    }
  }
  return maxAbsError;
}

function comparePixelBuffers(currentBuffer, candidateBuffer) {
  const current = PNG.sync.read(currentBuffer);
  const candidate = PNG.sync.read(candidateBuffer);
  assert.equal(candidate.width, current.width);
  assert.equal(candidate.height, current.height);
  let changedChannels = 0;
  let maxChannelDelta = 0;
  for (let index = 0; index < current.data.length; index += 1) {
    const delta = Math.abs(current.data[index] - candidate.data[index]);
    if (delta) changedChannels += 1;
    maxChannelDelta = Math.max(maxChannelDelta, delta);
  }
  return { changedChannels, maxChannelDelta, width: current.width, height: current.height };
}

async function compareRenderedFrames(page, scene, states) {
  const currentBuffer = await page.locator(".visual-stage").screenshot();
  await page.evaluate(
    ({ nodes, values }) => {
      const actual = window.__hpsCurrentStage;
      const candidate = window.__hpsCandidateStage;
      actual.replaceWith(candidate);
      for (const node of nodes) {
        const element = candidate.querySelector(
          '[data-object-id="' + node.id + '"]',
        );
        const state = values[node.id];
        element.style.opacity = String(state.opacity);
        element.style.transform =
          "translate(" + state.x + "px, " + state.y + "px)";
      }
    },
    { nodes: scene.nodes, values: states },
  );
  try {
    const candidateBuffer = await page.locator(".visual-stage").screenshot();
    return comparePixelBuffers(currentBuffer, candidateBuffer);
  } finally {
    await page.evaluate(() => {
      if (window.__hpsCandidateStage.parentNode)
        window.__hpsCandidateStage.replaceWith(window.__hpsCurrentStage);
    });
  }
}

async function neutralizeTheme(page) {
  await page.evaluate(() => {
    const theme = window.VisualData.catalog.themes.find(
      (item) => item.id === "neutral-science",
    );
    if (!theme) throw new Error("neutral-science theme missing from test catalog");
    Object.assign(theme.colors, {
      background: "#FFFFFF",
      ink: "#111111",
      body: "#333333",
      accent: "#111111",
      blue: "#444444",
      green: "#666666",
      muted: "#777777",
      panel: "#FFFFFF",
      pinkWash: "#EEEEEE",
      blueWash: "#DDDDDD",
      greenWash: "#F5F5F5",
      line: "#999999",
      paper: "#FFFFFF",
      purple: "#555555",
      yellow: "#BBBBBB",
      pink: "#888888",
    });
    theme.gradients = {
      pink: ["#EEEEEE", "#BBBBBB"],
      blue: ["#DDDDDD", "#999999"],
      green: ["#F5F5F5", "#AAAAAA"],
      purple: ["#CCCCCC", "#888888"],
      yellow: ["#E5E5E5", "#AAAAAA"],
    };
  });
}

async function registerNeutralTheme(page) {
  await page.evaluate((theme) => {
    window.VisualData.catalog.themes.push(theme);
  }, neutralTheme);
}

async function readCurrentState(page, timeMs, scene) {
  return page.evaluate(
    ({ time, nodes }) => {
      const result = window.visualPlayer.seek(time);
      const value = { timeMs: result.timeMs };
      for (const node of nodes) {
        const element = document.querySelector(
          '[data-object-id="' + node.id + '"]',
        );
        if (!element) throw new Error("rendered target missing: " + node.id);
        const computed = getComputedStyle(element);
        const matrix =
          computed.transform === "none"
            ? null
            : new DOMMatrixReadOnly(computed.transform);
        value[node.id] = {
          opacity: Number(computed.opacity),
          x: matrix?.m41 || 0,
          y: matrix?.m42 || 0,
        };
      }
      return value;
    },
    {
      time: timeMs,
      nodes: scene.nodes,
    },
  );
}

async function main() {
  fs.mkdirSync(output, { recursive: true });
  fs.copyFileSync(
    path.join(
      repo,
      "html_engine/motion-research/node_modules/animejs/LICENSE.md",
    ),
    path.join(repo, "html_engine/motion-research/ANIMEJS-LICENSE.md"),
  );

  assert.deepEqual(
    new Set(fixture.nodes.map((node) => node.type)),
    new Set(["text", "shape"]),
  );
  assert.equal(fixture.nodes.some((node) => node.type === "image"), false);
  compile(fixture, catalog);
  const layout = catalog.layouts.find(
    (item) => item.id === fixture.layoutRef.id,
  );
  assert(layout, "fixture layout must resolve in the current V1 catalog");

  const executablePath =
    process.env.HPS_CHROME ||
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const browser = await chromium.launch({ headless: true, executablePath });
  let page;
  try {
    page = await browser.newPage({
      viewport: { width: 1648, height: 1100 },
      deviceScaleFactor: 1,
    });
    await page.goto(
      pathToFileURL(path.join(visual, "preview/index.html")).href,
    );
    await page.waitForFunction(() => window.visualPlayer?.ready);
    await registerNeutralTheme(page);
    await neutralizeTheme(page);

    assert.equal(
      await page.evaluate((source) => window.visualPlayer.apply(source), fixture),
      true,
      "the fixed text/shape scene must compile in the current renderer",
    );
    await page.evaluate(() => window.visualPlayer.pause());
    await page.evaluate(() => {
      window.__hpsCurrentStage = document.querySelector(".visual-stage");
      window.__hpsCandidateStage = window.__hpsCurrentStage.cloneNode(true);
    });

    const candidate = makeAnimeScene(fixture);
    const currentStates = [];
    const pixelComparisons = [];
    let maxAbsError = 0;
    let totalChangedChannels = 0;
    let maximumChannelDelta = 0;
    for (const timeMs of samples) {
      candidate.timeline.reset();
      candidate.timeline.seek(timeMs, true);
      const current = await readCurrentState(page, timeMs, fixture);
      maxAbsError = Math.max(
        maxAbsError,
        compareStates(current, candidate.states, fixture),
      );
      const pixelComparison = await compareRenderedFrames(
        page,
        fixture,
        candidate.states,
      );
      totalChangedChannels += pixelComparison.changedChannels;
      maximumChannelDelta = Math.max(
        maximumChannelDelta,
        pixelComparison.maxChannelDelta,
      );
      pixelComparisons.push({ timeMs, ...pixelComparison });
      currentStates.push(current);
    }
    const rawSeekCandidate = makeAnimeScene(fixture);
    rawSeekCandidate.timeline.seek(7300, true);
    rawSeekCandidate.timeline.seek(2501, true);
    const rawSeekAt2501 = structuredClone(rawSeekCandidate.states);
    const runtimeAt2501 = await readCurrentState(page, 2501, fixture);
    const rawBackwardSeekError = Math.abs(
      runtimeAt2501.headline.opacity - rawSeekAt2501.headline.opacity,
    );
    assert(
      rawBackwardSeekError > 0.99,
      "the raw anime.js backward-seek limitation should be reproducible",
    );

    for (const [file, timeMs] of [
      ["enter-middle.png", 725.5],
      ["emphasize-peak.png", 2951],
      ["exit-middle.png", 6301.5],
    ]) {
      await readCurrentState(page, timeMs, fixture);
      await page.locator(".visual-stage").screenshot({
        path: path.join(output, file),
      });
    }

    await page.evaluate(() => window.visualPlayer.pause());
    const pausedSnapshot = await readCurrentState(page, 2951, fixture);
    await page.waitForTimeout(80);
    assert.equal(await page.evaluate(() => window.visualPlayer.timeMs), 2951);
    assert.deepEqual(
      await readCurrentState(page, 2951, fixture),
      pausedSnapshot,
      "the paused frame must remain unchanged",
    );

    await page.evaluate(() => {
      window.visualPlayer.seek(0);
      window.visualPlayer.play();
    });
    await page.waitForTimeout(350);
    await page.evaluate(() => window.visualPlayer.pause());
    const replayedTime = await page.evaluate(() => window.visualPlayer.timeMs);
    assert(replayedTime > 0, "play must advance when explicitly resumed");
    await page.waitForTimeout(80);
    assert.equal(await page.evaluate(() => window.visualPlayer.timeMs), replayedTime);
    await readCurrentState(page, 2951, fixture);
    assert.deepEqual(
      await readCurrentState(page, 2951, fixture),
      pausedSnapshot,
      "replaying and seeking back must restore the same frame",
    );

    const strokeScene = JSON.parse(
      fs.readFileSync(
        path.join(visual, "scenes/evaporation-process.json"),
        "utf8",
      ),
    );
    strokeScene.themeRef = { id: "neutral-science", version: "0.2.0" };
    assert.equal(
      await page.evaluate((source) => window.visualPlayer.apply(source), strokeScene),
      true,
      "the current SVG annotation scene must compile",
    );
    const annotation = strokeScene.motion.find(
      (action) =>
        action.targetId === "annotation" && action.type === "enter",
    );
    assert(annotation, "the fixed production scene must have an annotation enter");
    const strokeState = { offset: 1 };
    const strokeTimeline = createTimeline({ autoplay: false });
    strokeTimeline.add(
      strokeState,
      {
        offset: [1, 0],
        duration: annotation.durationMs,
        ease: smoothstep,
      },
      annotation.startMs,
    );
    const strokeTimes = [
      annotation.startMs - 0.001,
      annotation.startMs,
      annotation.startMs + 200.5,
      annotation.startMs + annotation.durationMs / 2,
      annotation.startMs + annotation.durationMs,
      annotation.startMs + 100,
      annotation.startMs + annotation.durationMs / 2,
    ];
    const strokeResults = [];
    let strokeMaxAbsError = 0;
    for (const timeMs of strokeTimes) {
      strokeTimeline.reset();
      strokeTimeline.seek(timeMs, true);
      const actual = await page.evaluate((time) => {
        window.visualPlayer.seek(time);
        const svg = document.querySelector(
          '[data-object-id="annotation"] svg',
        );
        const path = svg?.children?.[1];
        if (!path) throw new Error("SVG leader path missing");
        return Number(path.getAttribute("stroke-dashoffset"));
      }, timeMs);
      const error = Math.abs(actual - strokeState.offset);
      strokeMaxAbsError = Math.max(strokeMaxAbsError, error);
      assert(
        error < 1e-6,
        "SVG stroke offset differs by " + error + " at " + timeMs,
      );
      strokeResults.push({
        timeMs,
        currentRendererOffset: actual,
        animeSeekOffset: strokeState.offset,
        absError: error,
      });
    }
    await page.evaluate((time) => window.visualPlayer.seek(time), strokeTimes[3]);
    await page.locator(".visual-stage").screenshot({
      path: path.join(output, "svg-annotation-middle.png"),
    });

    const packageData = JSON.parse(
      fs.readFileSync(
        path.join(repo, "html_engine/motion-research/node_modules/animejs/package.json"),
        "utf8",
      ),
    );
    const strokeScenePath = path.join(
      visual,
      "scenes/evaporation-process.json",
    );
    const screenshotNames = [
      "enter-middle.png",
      "emphasize-peak.png",
      "exit-middle.png",
      "svg-annotation-middle.png",
    ];
    const verification = {
      format: "hps.c.motion-verification",
      version: "0.1.0",
      environment: {
        node: process.version,
        browser: browser.version(),
        executablePath,
      },
      currentRuntime: {
        source: "html_engine/visual/renderer.cjs",
        publicSeek: "window.visualPlayer.seek(ms)",
        implementationTimeSampling: "renderAt(ms), recomputed from the input time",
      },
      candidate: {
        name: "Anime.js",
        version: packageData.version,
        license: packageData.license,
        seekControlled: true,
        productionDependency: false,
        npmPackage: "animejs@4.5.0",
      },
      fixture: {
        path: "checks/html_motion_v1/fixtures/neutral-actions.json",
        sha256: fixtureHash,
        nodeTypes: ["text", "shape"],
        nodeCount: fixture.nodes.length,
        actionTypes: [...new Set(fixture.motion.map((item) => item.type))],
        sampleTimesMs: samples,
        maxAbsError,
        tolerance: 0.0001,
        pixelComparisons,
        totalChangedChannels,
        maximumChannelDelta,
        pausedFrameStable: true,
        replaySeekStable: true,
      },
      svgAnnotation: {
        sourceScene: "html_engine/visual/scenes/evaporation-process.json",
        sourceSceneSha256: sha256File(strokeScenePath),
        target: "annotation",
        implementedAs: "SVG ring and leader path; leader stroke-dashoffset follows enter progress",
        sampleTimesMs: strokeTimes,
        maxAbsError: strokeMaxAbsError,
        tolerance: 0.000001,
        samples: strokeResults,
      },
      candidateSeek: {
        directBackwardSeekFromMs: 7300,
        directBackwardSeekToMs: 2501,
        directBackwardSeekAbsError: rawBackwardSeekError,
        resetBeforeSeek: true,
        resetThenSeekMatchesCurrentRuntime: true,
      },
      outputFiles: screenshotNames.map((name) => {
        const file = path.join(output, name);
        return {
          path: "html_engine/motion-research/results/" + name,
          bytes: fs.statSync(file).size,
          sha256: sha256File(file),
        };
      }),
      sourceHashes: {
        renderer: sha256File(path.join(visual, "renderer.cjs")),
        compiler: sha256File(path.join(visual, "compiler.cjs")),
        previewBundle: sha256File(
          path.join(visual, "preview/player.js"),
        ),
        catalog: sha256File(path.join(visual, "generated/catalog.json")),
        animePackageLock: sha256File(
          path.join(repo, "html_engine/motion-research/package-lock.json"),
        ),
        animeLicense: sha256File(
          path.join(repo, "html_engine/motion-research/ANIMEJS-LICENSE.md"),
        ),
      },
      observations: {
        fixtureSamples: currentStates.length,
        candidateSnapshots: currentStates.length,
        ttsInvocations: 0,
      },
    };
    fs.writeFileSync(
      path.join(output, "verification.json"),
      JSON.stringify(verification, null, 2) + "\n",
    );
    console.log(
      JSON.stringify({
        fixtureSamples: currentStates.length,
        maxAbsError,
        rawBackwardSeekError,
        strokeSamples: strokeResults.length,
        strokeMaxAbsError,
        screenshots: verification.outputFiles.length,
      }),
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
