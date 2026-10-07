"use strict";
const cup = require("../scenes/condensation.json"),
  bowl = require("../scenes/evaporation.json");
function adapt(scene, overrides) {
  const node = (id) => scene.nodes.find((n) => n.id === id);
  const text = (id) =>
    node(id)
      .runs.map((r) => r.text)
      .join("");
  return {
    id: scene.id,
    title: scene.name,
    number: scene.id === "condensation" ? "01" : "02",
    headline: text("lead"),
    intro: overrides.intro,
    rows: [1, 2, 3].map((i) => ({
      title: text(`step-${i}`),
      body: text(`body-${i}`),
      icon: overrides.icons[i - 1],
      tone: ["pink", "green", "blue"][i - 1],
    })),
    from: node("from").text,
    to: node("to").text,
    summary: node("conclusion").text,
    assetRef: node("subject").assetRef,
    anchorId: "focus",
    term: overrides.term,
    annotation: overrides.annotation,
    figureTitle: overrides.figureTitle,
    figureNote: overrides.figureNote,
    durationMs: scene.durationMs,
    beats: scene.beats,
  };
}
module.exports = [
  adapt(cup, {
    intro: "从空气到杯壁，观察水的状态如何发生变化。",
    icons: ["air", "thermometer", "droplet"],
    term: "凝结",
    annotation: "杯壁上的\n小水滴",
    figureTitle: "观察冷杯表面",
    figureNote: "水滴来自空气中的水蒸气",
  }),
  adapt(bowl, {
    intro: "液态水变成水蒸气，画面中的小球仅作分子示意。",
    icons: ["droplet", "molecule", "check"],
    term: "蒸发",
    annotation: "水面变化\n示意",
    figureTitle: "观察一碗水",
    figureNote: "水蒸气通常不可见",
  }),
];
