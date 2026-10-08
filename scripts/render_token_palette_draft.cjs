"use strict";
// Review-only palette experiment. Uses existing compiler/player; no production registration.
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const { pathToFileURL } = require("url");
const root = path.resolve(__dirname, "..");
const engine = path.join(root, "html_engine");
const input = path.join(root, "outputs/image25-sheet/closure-token-v1");
const output = path.join(root, "outputs/image25-sheet/token-palette-v2");
if (fs.existsSync(output)) throw new Error("Refusing to replace palette evidence");
fs.mkdirSync(output, { recursive: true });
const theme = JSON.parse(fs.readFileSync(path.join(engine, "visual/themes/soft-science.json"), "utf8"));
theme.id = "amber-science-draft";
theme.name = "暖白琥珀（配色审阅稿，未注册生产）";
Object.assign(theme.colors, {
  background: "#FCFAF5", ink: "#29261F", body: "#625D53", accent: "#A66D14",
  blue: "#8D692F", green: "#A87823", muted: "#8A8377", panel: "#FFFFFF",
  pinkWash: "#F4EBD9", blueWash: "#F5F0E6", greenWash: "#F2E5C9",
  line: "#D8D0C0", paper: "#FFFFFF", purple: "#EDE6D8", yellow: "#B48028", pink: "#B48028",
});
theme.gradients = {
  pink: ["#C28D32", "#9D6B20"], blue: ["#F5F0E6", "#EFE9DE"],
  green: ["#F2DEAD", "#EAD3A0"], purple: ["#F5F0E6", "#EDE6D8"],
  yellow: ["#BD892D", "#97651A"],
};
const scene = JSON.parse(fs.readFileSync(path.join(input, "planning/html_visual/scene-token-closure.json"), "utf8"));
scene.themeRef.id = theme.id;
for (const node of scene.nodes) if (node.type === "card") node.tone = "yellow";
const write = (name, data) => fs.writeFileSync(path.join(output, name), JSON.stringify(data, null, 2));
write("theme-draft.json", theme);
write("scene-draft.json", scene);
process.env.HPS_HTML_RESOURCES = path.join(input, "planning/draft_preview/resources.json");
const resources = require(path.join(engine, "tools/project-resources.cjs")).loadProjectResources();
const { chromium } = require(path.join(engine, "node_modules/playwright"));
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.HPS_CHROME || "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe" });
  try {
    const page = await browser.newPage({ viewport: { width: 1648, height: 1200 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(engine, "visual/preview/index.html")).href);
    await page.waitForFunction(() => window.visualPlayer?.ready);
    const result = await page.evaluate(async ({ scene, theme, resources }) => {
      // Isolated browser session only; the on-disk registry and generated bundles stay unchanged.
      window.VisualData.catalog.themes.push(theme);
      const ok = await window.visualPlayer.apply(scene, resources);
      if (!ok) return { passed: false, error: document.getElementById("status").textContent };
      window.visualPlayer.seek(scene.durationMs);
      return { passed: true, timeMs: window.visualPlayer.timeMs, themeId: window.visualPlayer.scene.themeRef.id };
    }, { scene, theme, resources });
    if (!result.passed) throw new Error(result.error);
    const frames = [];
    for (const timeMs of [1200, 7000, 18000]) {
      await page.evaluate(t => window.visualPlayer.seek(t), timeMs);
      const bytes = await page.locator(".visual-stage").screenshot();
      const name = `draft-${timeMs}.png`;
      fs.writeFileSync(path.join(output, name), bytes);
      frames.push({ timeMs, file: name, sha256: crypto.createHash("sha256").update(bytes).digest("hex") });
    }
    if (errors.length) throw new Error(errors.join("\n"));
    write("evidence.json", { ...result, frames, pageErrors: errors, productionRegistered: false, visualApproval: "pending", layoutAndTimingChanged: false, additionalImageCalls: 0, sourceRun: "closure-token-v1" });
    console.log(JSON.stringify({ ...result, snapshots: frames.length, output }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
