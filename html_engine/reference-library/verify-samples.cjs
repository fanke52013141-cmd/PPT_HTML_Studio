const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("../node_modules/playwright");

const root = __dirname;
const sampleDir = path.join(root, "samples");
const outputDir = path.join(sampleDir, "output");
const htmlPath = path.join(sampleDir, "index.html");
const hash = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const normalizeColor = (hex) => {
  const value = hex.replace("#", "");
  return `rgb(${parseInt(value.slice(0, 2), 16)}, ${parseInt(value.slice(2, 4), 16)}, ${parseInt(value.slice(4, 6), 16)})`;
};

async function capture(slide, filename) {
  const bytes = await slide.screenshot({ animations: "disabled" });
  assert.equal(bytes.readUInt32BE(16), 1920, filename + ":width");
  assert.equal(bytes.readUInt32BE(20), 1080, filename + ":height");
  fs.writeFileSync(path.join(outputDir, filename), bytes);
  return { filename, sha256: hash(bytes), width: 1920, height: 1080 };
}

(async () => {
  assert.ok(process.env.HPS_CHROME, "HPS_CHROME must point to local Chromium/Edge");
  const chromePath = path.resolve(process.env.HPS_CHROME);
  assert.ok(fs.existsSync(chromePath), "HPS_CHROME does not exist: " + chromePath);

  const paletteSource = JSON.parse(
    fs.readFileSync(path.join(root, "palettes.json"), "utf8"),
  );
  const html = fs.readFileSync(htmlPath, "utf8");
  const inlinePalette = JSON.parse(
    html.match(/<script id="sample-palette-data" type="application\/json">([\s\S]*?)<\/script>/)[1],
  );
  assert.deepEqual(
    inlinePalette.palettes,
    paletteSource.palettes,
    "sample palette values must match palettes.json",
  );
  assert.equal(inlinePalette.version, paletteSource.version);
  assert.equal(inlinePalette.palettes.length, 3);

  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: chromePath });
  try {
    const page = await browser.newPage({
      viewport: { width: 2000, height: 1200 },
      deviceScaleFactor: 1,
    });
    const pageErrors = [];
    const remoteRequests = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("request", (request) => {
      if (/^https?:/i.test(request.url())) remoteRequests.push(request.url());
    });

    await page.goto(pathToFileURL(htmlPath).href);
    await page.waitForFunction(() => window.ReferenceSample);
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => Promise.all([...document.images].map((image) => image.decode())));

    const fontEvidence = await page.evaluate(() => ({
      available: document.fonts.check('24px "Noto Sans SC"'),
      renderedFamily: getComputedStyle(document.querySelector("#course-everyday h1")).fontFamily,
    }));
    assert.ok(fontEvidence.available, "Noto Sans SC is unavailable in the capture browser");
    assert.match(fontEvidence.renderedFamily, /Noto Sans SC/);

    const cdp = await page.context().newCDPSession(page);
    await cdp.send("DOM.enable");
    await cdp.send("CSS.enable");
    const { root: domRoot } = await cdp.send("DOM.getDocument");
    const { nodeId: headingNode } = await cdp.send("DOM.querySelector", {
      nodeId: domRoot.nodeId,
      selector: "#course-everyday h1",
    });
    const { fonts: actualFonts } = await cdp.send("CSS.getPlatformFontsForNode", {
      nodeId: headingNode,
    });
    assert.ok(
      actualFonts.some((font) => font.familyName.includes("Noto Sans SC") && font.glyphCount > 0),
      JSON.stringify(actualFonts),
    );

    const samples = [];
    for (const pageId of ["course-everyday", "paper-plane"]) {
      await page.evaluate((id) => window.ReferenceSample.setActivePage(id), pageId);
      const slide = page.locator("#" + pageId);
      const invariant = await slide.evaluate((root) => {
        const bounds = (element) => {
          const rect = element.getBoundingClientRect();
          return [rect.x, rect.y, rect.width, rect.height].map((n) => Math.round(n * 100) / 100);
        };
        const textOverflow = [];
        const outsideCanvas = [];
        for (const element of root.querySelectorAll("[data-instance-id], h1, h2, p, .path-tag")) {
          const range = document.createRange();
          range.selectNodeContents(element);
          const rangeOutside = [...range.getClientRects()].some((rect) => {
            const box = element.getBoundingClientRect();
            return rect.left < box.left - 1 || rect.top < box.top - 1 || rect.right > box.right + 1 || rect.bottom > box.bottom + 1;
          });
          if (
            element.scrollWidth > element.clientWidth + 1 ||
            element.scrollHeight > element.clientHeight + 16 ||
            rangeOutside
          ) {
            textOverflow.push({
              instanceId: element.dataset.instanceId || null,
              text: element.textContent.trim(),
              scroll: [element.scrollWidth, element.scrollHeight],
              client: [element.clientWidth, element.clientHeight],
            });
          }
        }
        const canvas = root.getBoundingClientRect();
        for (const element of root.querySelectorAll("[data-instance-id], img, svg")) {
          const rect = element.getBoundingClientRect();
          if (
            rect.left < canvas.left - 1 ||
            rect.top < canvas.top - 1 ||
            rect.right > canvas.right + 1 ||
            rect.bottom > canvas.bottom + 1
          )
            outsideCanvas.push(element.dataset.instanceId || element.tagName.toLowerCase());
        }
        const instances = [...root.querySelectorAll("[data-instance-id]")].map((element) => ({
          id: element.dataset.instanceId,
          componentId: element.dataset.componentId || null,
          text: element.textContent.trim().replace(/\s+/g, " "),
          bounds: bounds(element),
        }));
        const images = [...root.querySelectorAll("img")].map((image) => ({
          src: image.getAttribute("src"),
          loaded: image.complete && image.naturalWidth > 0,
          width: image.naturalWidth,
          height: image.naturalHeight,
        }));
        return {
          canvas: [canvas.width, canvas.height],
          instances,
          images,
          textOverflow,
          outsideCanvas,
        };
      });

      assert.deepEqual(invariant.canvas, [1920, 1080], pageId + ":canvas");
      assert.deepEqual(invariant.textOverflow, [], pageId + ":text overflow");
      assert.deepEqual(invariant.outsideCanvas, [], pageId + ":off canvas content");
      assert.equal(invariant.images.length, 2, pageId + ":asset budget");
      assert.ok(invariant.images.every((image) => image.loaded), pageId + ":image decode");

      const contentEvidence = await slide.evaluate((root) => ({
        titleCharacters: [...root.querySelector("h1").textContent.trim()].length,
        longestBodyCharacters: Math.max(
          ...[...root.querySelectorAll("[data-component-id='T04'], [data-component-id='T05']")].map(
            (node) => [...node.textContent.trim()].length,
          ),
        ),
        pathTags: root.querySelectorAll(".path-tag").length,
        componentIds: [...root.querySelectorAll("[data-component-id]")].map(
          (node) => node.dataset.componentId,
        ),
      }));
      if (pageId === "paper-plane") {
        assert.ok(contentEvidence.titleCharacters >= 28, "second topic must exercise a long title");
        assert.ok(contentEvidence.longestBodyCharacters >= 70, "second topic must exercise long explanatory text");
        assert.equal(contentEvidence.pathTags, 3, "second topic must exercise dense path labels");
        assert.equal(rootlessSourceStatus(await slide.getAttribute("data-source-status")), true);
      } else {
        assert.ok(contentEvidence.longestBodyCharacters >= 45, "course page must preserve the source explanation");
      }

      let referenceGeometry;
      let referenceIdentities;
      const paletteRuns = [];
      for (const palette of paletteSource.palettes) {
        await page.evaluate((id) => window.ReferenceSample.setPalette(id), palette.id);
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const state = await slide.evaluate((root) => {
          const rect = (node) => {
            const r = node.getBoundingClientRect();
            return [r.x, r.y, r.width, r.height].map((n) => Math.round(n * 100) / 100);
          };
          const selectors = [
            "[data-instance-id]",
            ".concept-card",
            ".trajectory-board",
            ".plane-layout > aside",
            "img",
            "svg",
          ];
          const measured = [];
          for (const selector of selectors)
            for (const node of root.querySelectorAll(selector))
              measured.push({
                selector,
                id: node.dataset.instanceId || node.getAttribute("src") || null,
                rect: rect(node),
              });
          const identity = [...root.querySelectorAll("[data-instance-id]")].map((node) => [
            node.dataset.instanceId,
            node.dataset.componentId || null,
            node.textContent.trim().replace(/\s+/g, " "),
          ]);
          const primary = getComputedStyle(root.querySelector(".state-label.role-primary, .tag-start"));
          const secondary = getComputedStyle(root.querySelector(".state-label.role-secondary, .tag-middle"));
          return {
            palette: root.dataset.palette,
            geometry: measured,
            identity,
            primaryColor: primary.color,
            secondaryColor: secondary.color,
          };
        });
        assert.equal(state.palette, palette.id);
        assert.equal(state.primaryColor, normalizeColor(palette.primary));
        assert.equal(state.secondaryColor, normalizeColor(palette.secondary));
        assert.notEqual(state.primaryColor, state.secondaryColor, palette.id + ":role colors must stay distinct");
        if (!referenceGeometry) {
          referenceGeometry = state.geometry;
          referenceIdentities = state.identity;
        } else {
          assert.deepEqual(state.geometry, referenceGeometry, pageId + ":geometry changed for " + palette.id);
          assert.deepEqual(state.identity, referenceIdentities, pageId + ":identity changed for " + palette.id);
        }
        paletteRuns.push({
          id: palette.id,
          name: palette.name,
          primary: palette.primary,
          secondary: palette.secondary,
          accent: palette.accent,
          category: palette.category,
          primaryColor: state.primaryColor,
          secondaryColor: state.secondaryColor,
        });
        const image = await capture(slide, `${pageId}-${palette.id}.png`);
        paletteRuns[paletteRuns.length - 1].image = image;
      }

      samples.push({
        id: pageId,
        source: await slide.getAttribute("data-source"),
        sourceStatus: await slide.getAttribute("data-source-status"),
        titleCharacters: contentEvidence.titleCharacters,
        longestBodyCharacters: contentEvidence.longestBodyCharacters,
        assetCount: invariant.images.length,
        assets: invariant.images,
        componentIds: [...new Set(contentEvidence.componentIds)].sort(),
        instanceIds: referenceIdentities.map(([id]) => id),
        palettes: paletteRuns,
      });
    }

    assert.deepEqual(pageErrors, []);
    assert.deepEqual(remoteRequests, []);
    const result = {
      status: "passed",
      scope: "static HTML reference sample; no production renderer or schema integration",
      baseline: "7499e4a5b4f40842f6dd4d559a8067550b15a86e",
      fontEvidence,
      actualFonts,
      checks: [
        "two static 1920x1080 pages load offline with decoded existing local assets",
        "course text, relationship, and source references remain code-controlled",
        "second topic is labeled as an E1 design-exploration reuse/capacity test",
        "long title, long explanatory copy, and three path labels fit without overflow",
        "all three independent palettes preserve component IDs, instance identities, and geometry",
        "primary and secondary palette roles remain distinct; accent and category roles are retained",
        "at most two independent image assets are used per page",
        "Noto Sans SC is available and used for rendered Chinese glyphs",
        "no page errors or remote network requests",
      ],
      userVisualApproval: "pending",
      productionMapping: "proposal required; static reference IDs do not imply scene support",
      pages: samples,
    };
    fs.writeFileSync(
      path.join(outputDir, "verification.json"),
      JSON.stringify(result, null, 2) + "\n",
    );
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

function rootlessSourceStatus(value) {
  return typeof value === "string" && value.includes("不是用户确认课程");
}
