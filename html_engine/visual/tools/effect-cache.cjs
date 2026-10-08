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
    theme: crypto.createHash("sha256").update(JSON.stringify(theme)).digest("hex"),
    catalog: crypto.createHash("sha256").update(JSON.stringify(catalog)).digest("hex"),
    scene: crypto.createHash("sha256").update(JSON.stringify(scenes[0])).digest("hex"),
    atlasBuilder: crypto.createHash("sha256").update(fs.readFileSync(__filename)).digest("hex"),
    layout: scenes[0].layoutRef.id,
    font,
    fontFiles: Object.fromEntries(["msyh.ttc","msyhbd.ttc","msyhl.ttc"].map(name=>{
      const file=path.join(process.env.WINDIR||"C:/Windows","Fonts",name);
      return [name,fs.existsSync(file)?crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"):null];
    })),
    effects: crypto
      .createHash("sha256")
      .update(JSON.stringify(registry))
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
    const samples = [];
    for (const effect of registry.effects) {
      const type = effect.usedBy.find(t => scenes[0].nodes.some(n => n.type === t)) || "card";
      const node = scenes[0].nodes.find(n => n.type === type);
      if (!node) throw new Error(`ATLAS_SAMPLE_MISSING: ${effect.id}`);
      await page.evaluate(id=>{
        document.querySelectorAll('[data-object-id]').forEach(el=>{el.style.visibility=el.dataset.objectId===id?'visible':'hidden';});
      },node.id);
      let locator=page.locator(`[data-object-id="${node.id}"]`);
      if(effect.id==="icon-bubble-gradient") locator=locator.locator('.v-icon-bubble');
      let shot;
      if(effect.backend==="SVG"){
        const clip=await locator.locator('svg').evaluate(el=>{
          const b=el.getBBox(),r=el.getBoundingClientRect(),v=el.viewBox.baseVal;
          const sx=r.width/v.width,sy=r.height/v.height;
          return {x:r.x+b.x*sx-12,y:r.y+b.y*sy-12,width:b.width*sx+24,height:b.height*sy+24};
        });
        shot=await page.screenshot({clip});
      }else shot=await locator.screenshot();
      samples.push({ ...effect, png: shot.toString("base64") });
      await page.evaluate(()=>document.querySelectorAll('[data-object-id]').forEach(el=>{el.style.visibility='';}));
    }
    await page.setContent('<html><head><meta charset="utf-8"><style>body{margin:0;padding:32px;background:#f7f8fb;color:#455b79;font:20px "Microsoft YaHei",sans-serif}h1{font-size:30px}main{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}article{background:white;border:1px solid #dfe5ee;border-radius:16px;padding:20px}h2{font-size:22px;margin:0 0 8px}p{font-size:18px;margin:8px 0}img{width:100%;height:160px;object-fit:contain;object-position:left center}</style></head><body><h1>科普效果库 · 已实现的效果与用途</h1><main></main></body></html>');
    await page.evaluate(items => {
      for (const item of items) {
        const card = document.createElement("article");
        const title = document.createElement("h2"); title.textContent = `${item.backend} · ${item.id}`;
        const purpose = document.createElement("p"); purpose.textContent = item.purpose;
        const image = document.createElement("img"); image.src = `data:image/png;base64,${item.png}`;
        card.append(title,purpose,image); document.querySelector("main").append(card);
      }
    },samples);
    await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
    fs.writeFileSync(path.join(CACHE, file), await page.screenshot({fullPage:true}));
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
    .then((r) => console.log(JSON.stringify({cache:r.cache,key:r.key,file:r.file,generated:r.generated,registry:r.registry})))
    .catch((e) => {
      console.error(e);
      process.exitCode = 1;
    });
