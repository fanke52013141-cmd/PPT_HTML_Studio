const fs = require("fs");
const path = require("path");
const read = (name) =>
  JSON.parse(fs.readFileSync(path.join(__dirname, name), "utf8"));
const components = read("components.json"),
  effects = read("effects.json"),
  styles = read("styles.json");
const staticCatalog = read("static-catalog.json");
const pairCatalog = read("style-pairs.json");
const extensionCatalog = read("components-extensions.json");
const all = [
  ...components.items,
  ...extensionCatalog.items.map((item) => ({
    ...item,
    status: "implemented-reference",
    productionAdapter: "not_integrated",
  })),
  ...effects.items,
  ...staticCatalog.items,

];
const args = process.argv.slice(2);
const id = args.includes("--id") ? args[args.indexOf("--id") + 1] : null;
const task = args.includes("--task") ? args[args.indexOf("--task") + 1] : null;
if ((args.includes("--id") && !id) || (args.includes("--task") && !task))
  throw Error("MISSING_ARGUMENT");
const entries = all.filter(
  (item) =>
    (!id || item.id === id) && (!task || JSON.stringify(item).includes(task)),
);
if (id && !entries.length) throw Error("UNKNOWN_REFERENCE_ID");
console.log(
  JSON.stringify(
    {
      version: "0.4.0",
      visualApproval: "pending",
      productionAdapter: "not_integrated",
      entries: entries.map((item) => ({
        ...item,
        call: item.id.startsWith("PAIR-")
          ? `StylePairs.render('${item.id}')`
          : item.id.startsWith("E")
            ? `ReferenceEffects.renderEffect('${item.id}')`
            : item.id.startsWith("M")
              ? `ReferenceEffects.renderMotion('${item.id}', 600)`
              : item.id.startsWith("P") ||
                  item.id.startsWith("V") ||
                  item.id.startsWith("H") ||
                  item.id.startsWith("X")
                ? `StaticReference.render('${item.id}')`
                : `ComponentAtlas.render('${item.id}')`,
      })),
      workflow: "neutral components + one role palette + unified style + exact content",
      unifiedStyle: "reference-input-v2/style-description.json",
      fonts: components.fonts,
      palettes: read("palettes.json"),
      referencePage: "html_engine/reference-library/components.html",
      guidance:
        "标准组件中性呈现，配色按角色另选，统一风格描述约束整体。参考标签不进入成图。R/D是固定结构示例，不是任意关系或图表引擎。",
    },
    null,
    2,
  ),
);
