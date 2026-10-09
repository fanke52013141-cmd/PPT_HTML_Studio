const fs = require("fs"),
  path = require("path"),
  crypto = require("crypto");
const root = __dirname,
  read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const staticCatalog = JSON.parse(read("static-catalog.json"));
const componentCatalog = JSON.parse(read("components.json"));
const extensions = JSON.parse(read("components-extensions.json"));
componentCatalog.version = extensions.version;
componentCatalog.items.push(
  ...extensions.items.map((item) => ({
    ...item,
    text: "",
    status: "implemented-reference",
    productionAdapter: "not_integrated",
  })),
);
const staticAsset = fs.readFileSync(
  path.resolve(root, "../..", staticCatalog.asset.path),
);
if (
  crypto.createHash("sha256").update(staticAsset).digest("hex") !==
  staticCatalog.asset.sha256
)
  throw Error("STATIC_ASSET_HASH_MISMATCH");
const pairCatalog = JSON.parse(read("style-pairs.json"));
const pairAssets = {};
for (const pair of pairCatalog.pairs) {
  const bytes = fs.readFileSync(path.resolve(root, "../..", pair.asset.path));
  if (
    crypto.createHash("sha256").update(bytes).digest("hex") !==
    pair.asset.sha256
  )
    throw Error("PAIR_ASSET_HASH_MISMATCH");
  pairAssets[pair.asset.id] =
    "data:image/png;base64," + bytes.toString("base64");
}
let html = read("components.template.html");
for (const [key, value] of Object.entries({
  STYLE: read("components.css"),
  STATIC_STYLE: read("static.css"),
  STATIC: read("static.js"),
  PAIR_STYLE: read("style-pairs.css"),
  PAIRS: read("style-pairs.js"),
  DATA:
    "window.StylePairCatalog=" +
    JSON.stringify(pairCatalog).replace(/</g, "\\u003c") +
    ";window.StylePairAssets=" +
    JSON.stringify(pairAssets) +
    ";" +
    "window.ComponentCatalog=" +
    JSON.stringify(componentCatalog).replace(/</g, "\\u003c") +
    ";window.StyleCatalog=" +
    read("styles.json").replace(/</g, "\\u003c") +
    ";window.EffectsCatalog=" +
    read("effects.json").replace(/</g, "\\u003c") +
    ";window.StaticCatalog=" +
    JSON.stringify(staticCatalog).replace(/</g, "\\u003c") +
    ";window.StaticAsset=" +
    JSON.stringify("data:image/png;base64," + staticAsset.toString("base64")) +
    ";",
  SCRIPT: read("components.js"),
  EFFECTS: read("effects-static.js"),
}))
  html = html.replace(`/*${key}*/`, () => value);
fs.writeFileSync(path.join(root, "components.html"), html);
fs.writeFileSync(
  path.join(root, "components-build.json"),
  JSON.stringify(
    {
      version: "0.4.0",
      sha256: crypto.createHash("sha256").update(html).digest("hex"),
      effects: JSON.parse(read("effects.json")).items.length,
      motions: 0,
      stylePairs: pairCatalog.pairs.map((p) => ({
        id: p.id,
        codeStyleRef: p.codeStyleRef,
        imageStyleRef: p.imageStyle.id,
        sha256: p.asset.sha256,
      })),
      staticCompositions: staticCatalog.items.length,
      asset: staticCatalog.asset,
      components: componentCatalog.items.length,
      fonts: JSON.parse(read("components.json")).fonts.map((f) => f.family),
      productionAdapter: "not_integrated",
    },
    null,
    2,
  ) + "\n",
);
for (const pair of pairCatalog.pairs) {
  const spec = {
    referenceVersion: pairCatalog.version,
    pairRef: pair.id,
    codeStyleRef: pair.codeStyleRef,
    imageStyle: pair.imageStyle,
    shared: pair.shared,
    componentRefs: pair.components,
    contentSource: "必须附准确文案与关系，不使用图板样例文字",
    canvas: "按当前项目画布比例",
    subtitleSafeArea: "按当前项目要求另附",
    status: "reference_only_pending_visual_review",
  };
  fs.writeFileSync(
    path.join(root, pair.id.toLowerCase() + "-ai-input.json"),
    JSON.stringify(spec, null, 2) + "\n",
  );
}
console.log("Built static component boards and three style pairs");
