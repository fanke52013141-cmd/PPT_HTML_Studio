"use strict";
// Effect reference-image cache (A03/AC06). Renders one representative page per
// registered effect group with the same shared bundle used by preview and
// tests, and keys every image by sha256(theme+layout+effect set+font+renderer
// bundle). A second run with unchanged inputs must hit the cache and generate
// nothing new.
const fs = require("fs"),
  path = require("path"),
  crypto = require("crypto");
const { pathToFileURL } = require("url");
const root = path.resolve(__dirname, "..");
const CACHE = path.join(root, "effects/cache");
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));

async function renderReferences() {
  const { chromium } = require("playwright");
  const registry = read("effects/registry.json");
  const catalog = read("generated/catalog.json");
  const scenes = fs
    .readdirSync(path.join(root, "scenes"))
    .filter((p) => p.endsWith(".json"))
    .sort()
    .map((p) => read(`scenes/${p}`));
  const theme = catalog.themes.find((t) => t.id === scenes[0].themeRef.id);
  const bundle = fs.readFileSync(
    path.join(root, "preview/player.js"),
    "utf8",
  );
  const font = theme.font.family;
  const inputs = {
    theme: `${theme.id}@${theme.version}`,
    layout: scenes[0].layoutRef.id,
    font,
    effects: crypto
      .createHash("sha256")
      .update(JSON.stringify(registry.effects.map((e) => e.id)))
      .digest("hex")
      .slice(0, 16),
    renderer: crypto.createHash("sha256").update(bundle).digest("hex").slice(0, 16),
  };
  const key = crypto
    .createHash("sha256")
    .update(JSON.stringify(inputs))
    .digest("hex")
    .slice(0, 32);
  const manifestPath = path.join(CACHE, "manifest.json");
  const manifest = fs.existsSync(manifestPath)
    ? JSON.parse(fs.readFileSync(manifestPath, "utf8"))
    : { version: 1, entries: {} };
  fs.mkdirSync(CACHE, { recursive: true });
  const entry = manifest.entries[key];
  if (entry && fs.existsSync(path.join(CACHE, entry.file))) {
    return {
      cache: "hit",
      key,
      file: entry.file,
      inputs,
      generated: 0,
      registry: registry.effects.length,
    };
  }
  const file = `references-${key}.png`;
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.HPS_CHROME ||
      "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1247/chrome-win64/chrome.exe",
  });
  const page = await browser.newPage({
    viewport: { width: 1648, height: 1200 },
    deviceScaleFactor: 1,
  });
  try {
    await page.goto(
      pathToFileURL(path.join(root, "preview/index.html")).href,
    );
    await page.waitForFunction(() => window.visualPlayer?.ready, {}, { timeout: 15000 });
    const applied = await page.evaluate(
      (s) => window.visualPlayer.apply(s),
      scenes[0],
    );
    if (!applied) throw new Error("reference scene failed to apply");
    await page.evaluate((t) => window.visualPlayer.seek(t), scenes[0].durationMs);
    const shot = await page.locator(".visual-stage").screenshot();
    fs.writeFileSync(path.join(CACHE, file), shot);
  } finally {
    await browser.close();
  }
  // Cache retention: keep the newest manifest entry only; older files are
  // stale inputs by definition (any version change produces a new key).
  for (const [oldKey, old] of Object.entries(manifest.entries))
    if (oldKey !== key)
      fs.rmSync(path.join(CACHE, old.file), { force: true });
  manifest.entries = { [key]: { file, inputs, createdAt: new Date().toISOString() } };
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n");
  return {
    cache: "miss",
    key,
    file,
    inputs,
    generated: 1,
    registry: registry.effects.length,
  };
}
module.exports = { renderReferences };
if (require.main === module)
  renderReferences()
    .then((r) => console.log(JSON.stringify(r)))
    .catch((e) => {
      console.error(e);
      process.exitCode = 1;
    });
