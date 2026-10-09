"use strict";
const fs = require("fs"),
  path = require("path"),
  crypto = require("crypto"),
  assert = require("node:assert/strict");
const { pathToFileURL } = require("url");
const { chromium } = require("../node_modules/playwright");
const root = __dirname,
  repo = path.resolve(root, "../..");
const out = path.resolve(
  process.argv[2] ||
    path.join(repo, "outputs/static-reference/pair-03-roundtrip-v1"),
);
if (fs.existsSync(out))
  throw Error("OUTPUT_EXISTS: choose a new experiment directory");
const pairs = JSON.parse(
  fs.readFileSync(path.join(root, "style-pairs.json"), "utf8"),
);
const styles = JSON.parse(
  fs.readFileSync(path.join(root, "styles.json"), "utf8"),
);
const pairId = process.argv[3] || "PAIR-03";
const pair = pairs.pairs.find((p) => p.id === pairId);
assert(pair, "UNKNOWN_STYLE_PAIR");
const hash = (b) => crypto.createHash("sha256").update(b).digest("hex");
const write = (file, data) =>
  fs.writeFileSync(
    path.join(out, file),
    typeof data === "string" ? data : JSON.stringify(data, null, 2) + "\n",
  );
(async () => {
  const started = performance.now();
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.HPS_CHROME,
  });
  fs.mkdirSync(out, { recursive: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 2080, height: 1200 },
      deviceScaleFactor: 1,
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root, "components.html")).href);
    await page.waitForFunction(() => window.StylePairs?.ready);
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all(
        [...document.querySelectorAll(".pair-board img")].map((i) =>
          i.decode(),
        ),
      );
    });
    await page
      .locator(`#${pair.id.toLowerCase()} .pair-reference-grid`)
      .screenshot({ path: path.join(out, "reference-ab.png") });
    const baseline = await page.evaluate((id) => {
      const board = document.getElementById(id.toLowerCase());
      const specimen = board.querySelector(".pair-composition").cloneNode(true);
      board.replaceChildren(specimen);
      board.classList.add("experiment-board");
      const canvas = document.createElement("main");
      canvas.id = "experiment-canvas";
      canvas.append(board);
      document.body.replaceChildren(canvas);
      return {
        html: canvas.outerHTML,
        css: [...document.querySelectorAll("style")]
          .map((s) => s.textContent)
          .join("\n"),
      };
    }, pair.id);
    // Styles were in head; this scope is the only geometry adaptation for the static baseline.
    const geometry = `body{margin:0;background:white}#experiment-canvas{width:1920px;height:1080px;background:#fff;position:relative;overflow:hidden}.experiment-board{width:1920px;padding:0;margin:0;position:absolute;top:0}.experiment-board .pair-composition{width:1920px;height:960px;border:0;border-radius:0;padding:96px}.experiment-board .pair-hero-copy{width:820px}.experiment-board .pair-hero-title{font-size:76px;margin-top:30px}.experiment-board .pair-hero-description{font-size:26px;max-width:760px}.experiment-board .pair-keyline{font-size:20px;margin-top:30px}.experiment-board .pair-hero-image{left:1100px;right:80px;top:64px;height:480px}.experiment-board .pair-steps{left:96px;right:96px;bottom:60px;gap:80px}.experiment-board .pair-step{min-height:184px;padding-top:32px}.experiment-board .pair-step strong{font-size:26px}.experiment-board .pair-step p{font-size:21px}.experiment-board .pair-step-index{top:35px}.experiment-board .pair-connectors{top:50px}`;
    await page.addStyleTag({ content: geometry });
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page
      .locator("#experiment-canvas")
      .screenshot({ path: path.join(out, "code-baseline.png") });
    assert.equal(await page.locator(".pair-composition img").count(), 1);
    assert(
      await page.locator(".pair-composition").evaluate((e) => {
        return [
          ...e.querySelectorAll("h2,p,strong,.pair-eyebrow,.pair-keyline"),
        ].every((n) => {
          const r = document.createRange();
          r.selectNodeContents(n);
          return [...r.getClientRects()].every(
            (b) =>
              b.left >= 0 && b.right <= 1920 && b.top >= 0 && b.bottom <= 960,
          );
        });
      }),
    );
    const safeArea = await page.evaluate(
      () =>
        document.querySelector(".pair-composition").getBoundingClientRect()
          .bottom,
    );
    assert.equal(safeArea, 960);
    const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>${pair.id} 可编辑代码基准 · 非生成图还原</title><style>${baseline.css}\n${geometry}</style></head><body>${baseline.html}</body></html>`;
    write("code-baseline.html", html);
    // Verify saved artifact, then change actual text to demonstrate independent editability.
    await page.goto(pathToFileURL(path.join(out, "code-baseline.html")).href);
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map((i) => i.decode()));
    });
    const oldImage = await page.locator(".pair-subject").getAttribute("src");
    await page
      .locator(".pair-hero-title")
      .evaluate((e) => (e.textContent = "标题可以直接修改"));
    assert.equal(
      await page.locator(".pair-hero-title").innerText(),
      "标题可以直接修改",
    );
    assert.equal(
      await page.locator(".pair-subject").getAttribute("src"),
      oldImage,
    );
    assert.deepEqual(errors, []);
    const content = pairs.content;
    const objects = [
      { id: "title", implementation: "HTML", content: content.title },
      {
        id: "description",
        implementation: "HTML",
        content: content.description,
      },
      { id: "eyebrow", implementation: "HTML", content: content.eyebrow },
      { id: "keyline", implementation: "HTML", content: content.keyline },
      ...content.steps.map((s, i) => ({
        id: "step-" + (i + 1),
        implementation: "HTML/CSS",
        componentRef: "C04",
        content: s,
      })),
      {
        id: "relationships",
        implementation: "SVG",
        componentRef: "A01",
        topology: ["step-1 -> step-2", "step-2 -> step-3"],
      },
      { id: "subject", implementation: "PNG", assetRef: pair.asset.id },
    ];
    const definition = {
      format: "hps.static.roundtrip-experiment",
      version: "0.1.0",
      pairRef: pair.id,
      referenceVersion: pairs.version,
      canvas: {
        width: 1920,
        height: 1080,
        subtitleSafeArea: { top: 960, height: 120 },
      },
      generation: {
        size: "2048x1152",
        quality: "low",
        background: "opaque",
        reference: "reference-ab.png",
      },
      content,
      objects,
      codeStyle: styles.codeStyles.find((s) => s.id === pair.codeStyleRef),
      imageStyle: pair.imageStyle,
      shared: pair.shared,
      asset: pair.asset,
    };
    write("definition.json", definition);
    const text = `生成一张16:9完整页面设计参考，2048×1152，low，不透明纯白背景。\n所附图只包含A图片风格与B代码外观：A约束${pair.imageStyle.rendering}、${pair.imageStyle.material}、${pair.imageStyle.lighting}、${pair.imageStyle.perspective}；B约束${pair.codeDescription}。保持参考中主体色彩与代码配色协调。不要画参考图中的A/B标签、说明、色板和样例文案。\n准确页面内容如下，逐字保留，不增删事实：\n${JSON.stringify(content, null, 2)}\n关系：三个步骤由左到右依次连接。采用一个独立${pair.asset.alt}主体，文字与几何能由HTML/CSS/SVG还原，主体不嵌入文字。标题与说明在左，主体在右，下方三个步骤；以比例、字阶和留白体现精致。底部约11.1%画布保持纯白，供字幕使用。只输出完整页面图片，不输出代码、解释、图板或额外页。\n`;
    write("generation-prompt.txt", text);
    const files = [
      "definition.json",
      "reference-ab.png",
      "code-baseline.html",
      "code-baseline.png",
      "generation-prompt.txt",
    ];
    write("experiment-status.json", {
      format: definition.format,
      version: definition.version,
      pairRef: pair.id,
      preparation: {
        status: "passed",
        elapsedSeconds: Math.round((performance.now() - started) / 10) / 100,
        checks: [
          "one independent image",
          "editable title without changing image",
          "actual DOM screenshot",
          "all text above subtitle area",
          "saved offline HTML reopened",
          "zero browser errors",
        ],
      },
      generation: {
        status: "not_executed",
        reason: "no configured credential",
        requests: 0,
      },
      reconstruction: {
        status: "not_executed",
        reason:
          "requires actual generated design and explicit reconstruction changes",
      },
      comparison: {
        status: "pending",
        generationSeconds: null,
        reconstructionSeconds: null,
        reworkCount: null,
        aestheticApproval: "pending",
      },
      inputs: Object.fromEntries(
        files.map((f) => [f, hash(fs.readFileSync(path.join(out, f)))]),
      ),
    });
    write(
      "README.md",
      `# ${pair.id} 静态往返实验准备\n\nreference-ab.png与generation-prompt.txt是最小生成输入。definition.json保存权威文案、对象与风格。code-baseline.html为可编辑静态基准，code-baseline.png是实际DOM截图。它不是生成图的代码还原。\n\n当前生成与还原未执行；不得计算成功率或效率提升。生图需可用配置；收到generated-design.png后，按实际设计更新实例几何，保留原基准，产出reconstructed.html/PNG，并登记耗时、改动与返工。准确文案与关系不从OCR反向覆盖。\n\n验收：逐字内容、三个步骤顺序、一个独立主体、字幕安全区、标题字形与图文比例、图像边缘、容器层次。通过几何检查不等于美感通过。\n`,
    );
    console.log(
      JSON.stringify({
        status: "prepared",
        out,
        generation: "not_executed",
        reconstruction: "not_executed",
      }),
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
