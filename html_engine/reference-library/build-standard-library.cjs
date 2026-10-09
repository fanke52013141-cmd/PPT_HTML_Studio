const fs = require("fs");
const path = require("path");
const root = __dirname;
const read = (name) => fs.readFileSync(path.join(root, name), "utf8");
const json = (name) => JSON.parse(read(name));
const components = [
  ...json("components.json").items,
  ...json("components-extensions.json").items,
];
const variants = json("presentation-variants.json").items;
const effects = json("effects.json").items;
const compositions = json("static-catalog.json").items;
const pages = [
  {
    id: "overview",
    title: "标准组件 · 黑白灰基线",
    note: "真实文字、精确关系、柔和层次；配色由独立风格参考控制。",
    kind: "overview",
    ids: [],
  },
];
for (const [kind, items] of [
  ["component", components],
  ["variant", variants],
  ["effect", effects],
  ["composition", compositions],
]) {
  for (const category of [...new Set(items.map((x) => x.category))]) {
    pages.push({
      id: `${kind}-${pages.length.toString().padStart(2, "0")}`,
      title: category,
      note:
        kind === "effect"
          ? "以灰阶展示材质与层次，效果不替代信息结构。"
          : kind === "composition"
            ? "通用组合示例；文字、关系与图片保持独立。"
            : "按编号调用；组件结构与配色独立。",
      kind,
      ids: items.filter((x) => x.category === category).map((x) => x.id),
    });
  }
}
pages.push({
  id: "fonts",
  title: "字体 · 五种表达",
  note: "字体是文字气质的基础；本机字体可用性不等于跨平台已打包。",
  kind: "font",
  ids: json("components.json").fonts.map((x) => x.id),
});
if (pages.length !== 24) throw Error("EXPECTED_24_PAGES: " + pages.length);
const catalog = {
  version: "1.0.0",
  canvas: { width: 1920, height: 1080 },
  scope: "static-reference-only",
  pages,
};
fs.writeFileSync(
  path.join(root, "standard-pages.json"),
  JSON.stringify(catalog, null, 2) + "\n",
);
const tokens = {
  ink: "#222222",
  muted: "#666666",
  accent: "#444444",
  tint: "#f4f4f4",
  line: "#dddddd",
  "component-font": '"Noto Sans SC"',
  radius: "22px",
  stroke: "2px",
};
const injection = `<script>window.StandardPages=${JSON.stringify(catalog)};window.StandardTokens=${JSON.stringify(tokens)};window.StandardPalettes=${read("palettes.json")};</script><script>${read("standard-library.js")}</script>`;
fs.writeFileSync(
  path.join(root, "standard-library.html"),
  read("components.html")
    .replace(
      "</head>",
      "<style>" + read("standard-library.css") + "</style></head>",
    )
    .replace("</body>", injection + "</body>")
    .replace(
      "<title>通用代码组件 · 白底截图板</title>",
      "<title>标准组件库 · 黑白灰</title>",
    ),
);
console.log(
  "Built 24 standard pages: 32 components, 16 variants, 28 effects, 18 compositions, 5 fonts",
);
