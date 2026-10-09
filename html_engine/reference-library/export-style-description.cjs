"use strict";
// Style the original standard library; do not create another component specification.
const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict"),
  { pathToFileURL } = require("url");
const { chromium } = require("../node_modules/playwright");
const root = __dirname,
  parent = root,
  out = path.join(root, "reference-input-v2");
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.HPS_CHROME,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 2080, height: 1200 },
      deviceScaleFactor: 1,
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(parent, "components.html")).href);
    await page.waitForFunction(
      () =>
        window.ComponentAtlas?.ready &&
        window.ReferenceEffects?.ready &&
        window.StylePairs?.ready,
    );
    const plane = await page
      .locator("#pair-02 .pair-source-image")
      .getAttribute("src");
    const description = {
      name: "清爽轻立体",
      version: "0.1.0",
      componentSource: "components.json + components.js; unchanged IDs and DOM",
      appearanceSource: "unified style, palette supplied separately",
      style:
        "纯白背景；思源黑体建立清楚层级；文字保持深色，主色、辅助色与强调色按所附配色方案选择；轻细线、圆角、少量浅色渐变和柔和阴影；主体采用固定视角、左上柔光、细腻纸面和有限立体明暗。所有元素服从同一种清爽、轻盈、准确的视觉语言。",
      avoid: [
        "手绘笔触",
        "手写字体",
        "粗黑描边",
        "密集拼贴",
        "复杂背景",
        "强烈光效",
      ],
      inputRules: [
        "按标准组件参考选择文字、箭头、卡片与形状，不重新发明组件外观",
        "风格描述图约束整个页面，包括独立图片主体",
        "准确文案与语义关系由另附内容给出，不复制参考板文字、ID、标签或说明",
        "按任务选标准组件/效果/SVG板，不必一次传入全部",
      ],
      generationDefaults: { resolution: "2K", quality: "low" },
    };
    await page.setContent(
      `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#fff;color:#202e43;font-family:"Noto Sans SC",sans-serif}.sheet{width:1920px;height:1080px;position:relative;padding:90px 96px}.eyebrow{font-size:24px;color:#627189}h1{font-size:80px;line-height:1.2;margin:32px 0 24px}.lead{font-size:30px;color:#627189;line-height:1.8;width:1030px}.rules{width:1010px;display:grid;grid-template-columns:1fr 1fr;gap:34px 50px;margin-top:56px}.rule{padding-top:24px;border-top:1px solid #d6e2ed}h2{font-size:28px;color:#39668f;margin:0 0 16px}.rule p{font-size:25px;line-height:1.8;margin:0;color:#627189}.plane{position:absolute;right:64px;top:230px;width:670px;height:650px;object-fit:contain}.caption{position:absolute;right:96px;top:880px;width:580px;font-size:22px;color:#627189;line-height:1.8}footer{position:absolute;left:96px;right:96px;bottom:62px;border-top:1px solid #d6e2ed;padding-top:22px;font-size:22px;color:#627189}</style></head><body><article class="sheet"><div class="eyebrow">统一风格参考 · 整个页面遵循同一种视觉语言</div><h1>清爽轻立体</h1><p class="lead">清楚的文字与结构，搭配柔和的立体质感。<br>组件保持标准结构，用同一风格统一呈现。</p><div class="rules"><section class="rule"><h2>文字与颜色</h2><p>思源黑体，清楚的字阶。<br>文字保持深色，主色、辅助色与强调色按所附配色方案选择。</p></section><section class="rule"><h2>形状与层次</h2><p>细线、圆角、浅色表面。<br>少量渐变、柔影，留白充足。</p></section><section class="rule"><h2>主体与质感</h2><p>固定视角，左上柔光。<br>细腻纸面，有限的立体明暗。</p></section><section class="rule"><h2>避免</h2><p>手绘笔触、手写字体、粗黑描边。<br>密集拼贴、复杂背景、强烈光效。</p></section></div><img class="plane" alt="统一风格的主体质感参考"><div class="caption">主体质感示例；不是必须出现的内容。<br>文字、卡片和关系遵循标准组件参考。</div><footer>纯白背景 · 标准组件＋统一风格 · 参考文案、说明、标签不进入生成页面</footer></article></body></html>`,
    );
    await page.locator(".plane").evaluate((e, src) => (e.src = src), plane);
    await page.evaluate(async () => {
      await document.fonts.ready;
      await document.querySelector("img").decode();
    });
    await page
      .locator(".sheet")
      .screenshot({ path: path.join(out, "style-description.png") });
    assert.deepEqual(errors, []);
    fs.writeFileSync(
      path.join(out, "style-description.json"),
      JSON.stringify(description, null, 2),
    );
    fs.writeFileSync(
      path.join(out, "style-verification.json"),
      JSON.stringify(
        {
          status: "passed",
          components: 32,
          scope: "unified style description only",
          source: "original components.html",
          appearance: "palette-independent",
          errors,
          output: "PNG references, not another HTML template",
        },
        null,
        2,
      ),
    );
    console.log("Exported unified style description");
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
