const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict"),
  { pathToFileURL } = require("url"),
  { chromium } = require("../node_modules/playwright");
const root = __dirname,
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
    await page.goto(pathToFileURL(path.join(root, "components.html")).href);
    await page.waitForFunction(
      () => window.ComponentAtlas?.ready && window.ReferenceEffects?.ready,
    );
    await page.evaluate(() => {
      const a = document.querySelector("#atlas");
      window.ReferenceEffects.applyCodeStyle(a, "neutral");
      a.querySelector(".fonts").remove();
      a.querySelector("h1").textContent = "标准组件 · 形态与层次";
      a.querySelector(".board-header p").textContent =
        "组件保持统一，配色按角色另选；中性展示比例、字阶、线条、容器和关系。";
      a.querySelector(".version").textContent =
        "32项 / 静态参考0.2\n24项精修＋8项扩展";
    });
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator("#atlas .cell").count(), 32);
    await page
      .locator("#atlas")
      .screenshot({ path: path.join(out, "standard-components.png") });
    for (const [i, name] of [
      "typography",
      "arrows",
      "cards",
      "shapes",
      "annotations",
      "relationships",
      "data-time",
    ].entries())
      await page
        .locator("#atlas > .section, #atlas-body > .section")
        .nth(i)
        .screenshot({ path: path.join(out, name + ".png") });
    const data = JSON.parse(
      fs.readFileSync(path.join(root, "palettes.json"), "utf8"),
    );
    for (const palette of data.palettes) {
      await page.evaluate((p) => {
        document.querySelector("#palette-preview")?.remove();
        const n = (tag, cls, text) => {
          const e = document.createElement(tag);
          e.className = cls;
          if (text) e.textContent = text;
          return e;
        };
        const board = n("article", "board component-reference");
        board.id = "palette-preview";
        board.style.cssText =
          "width:1920px;height:1080px;padding:76px 80px;margin:0 auto;--ink:" +
          p.ink +
          ";--muted:" +
          p.muted;
        const h = n("header", "board-header");
        h.append(
          n("h1", "", p.name + " · 一套配色，多个角色"),
          n("p", "", "同一标准组件，仅替换颜色变量"),
        );
        board.append(h);
        const row = n("div", "palette-row");
        const roles = [
          ["primary", "主色 / 主线索"],
          ["secondary", "辅助 / 第二类信息"],
          ["accent", "强调 / 少量重点"],
          ["category", "分类 / 并列分组"],
        ];
        roles.forEach(([key, label], i) => {
          const panel = n("section", "palette-panel");
          panel.style.cssText =
            "--ink:" +
            p.ink +
            ";--accent:" +
            p[key] +
            ";--tint:" +
            p.tints[i] +
            ";--line:" +
            p[key] +
            "40";
          const swatch = n("div", "palette-swatch");
          swatch.style.background = p[key];
          swatch.append(n("span", "", label), n("strong", "", p[key]));
          panel.append(swatch);
          const card = window.ComponentAtlas.render("C01", "同一个标准卡片");
          panel.append(
            card,
            window.ComponentAtlas.render("N01", "分类标签"),
            window.ComponentAtlas.render("T07", "重点关键词"),
          );
          row.append(panel);
        });
        board.append(row);
        const rules = n("div", "palette-rules");
        [
          "正文保持深色，颜色服务于分类与层级。",
          "单页用主色＋1至2个辅助角色，不必四种全用。",
          "同类跨页同色；参考图的标签与示例文案不进入成图。",
        ].forEach((s) => rules.append(n("p", "", s)));
        board.append(rules);
        document.body.append(board);
      }, palette);
      await page.addStyleTag({
        content:
          "#palette-preview .board-header{border-bottom:1px solid #e5e8ed;margin-bottom:60px}#palette-preview .board-header h1{font-size:52px}.palette-row{display:grid;grid-template-columns:repeat(4,1fr);gap:40px}.palette-panel{display:flex;flex-direction:column;gap:35px;align-items:center}.palette-swatch{height:142px;width:100%;border-radius:20px;color:white;padding:26px 28px}.palette-swatch span{display:block;font-size:22px;margin-bottom:14px}.palette-swatch strong{font:500 26px Arial}.palette-panel .sample-card{width:370px;padding:26px 28px;min-height:145px;border-radius:20px}.palette-panel .sample-card strong{font-size:26px}.palette-panel .sample-card p{font-size:20px}.palette-panel .highlight{font-size:28px}.palette-rules{border-top:1px solid #e5e8ed;margin-top:72px;padding-top:22px;color:var(--muted);font-size:25px;line-height:1.8}.palette-rules p{margin:5px 0}",
      });
      await page
        .locator("#palette-preview")
        .screenshot({ path: path.join(out, "palette-" + palette.id + ".png") });
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(
      path.join(out, "manifest.json"),
      JSON.stringify(
        {
          components: 32,
          base: "neutral",
          palettes: data,
          workflow: [
            "neutral standard component PNG",
            "one palette PNG",
            "unified style description plus exact content",
            "image generation 2K/low",
          ],
          errors,
          status: "reference_only_visual_review_pending",
        },
        null,
        2,
      ),
    );
    console.log(
      "Exported neutral components, detail sheets and 3 role-based palettes",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
