"use strict";
// Content-independent authoring recipe; all coordinates and actions are template owned.
function compileHeroSteps(input, base, recipe, { keys, text, asset, fail }) {
  if (!Array.isArray(input.steps) || input.steps.length !== 3)
    fail("RECIPE_FIELD", "steps", "exactly three steps required");
  const resource = asset(input.heroAsset, "heroAsset");
  base.durationMs = 18000;
  base.assets = [resource];
  base.nodes = [];
  base.actions = [];
  base.beats = [];
  base.style.textRoles.title.fontSize = 64;
  base.style.textRoles.subtitle.fontSize = 26;
  base.style.textRoles.caption.fontSize = 38;
  base.style.textRoles.caption.align = "left";
  function addText(id, role, content, box, opacity = 1, beat = false) {
    base.nodes.push({
      id,
      type: "text",
      typeVersion: "0.1.0",
      zIndex: 100,
      initialOpacity: opacity,
      box,
      role,
      content: beat
        ? { kind: "beat-summary" }
        : { kind: "static", text: content },
    });
  }
  addText("page.title", "title", input.title, {
    x: 100,
    y: 65,
    width: 1400,
    height: 100,
  });
  addText("page.subtitle", "subtitle", input.subtitle, {
    x: 104,
    y: 175,
    width: 1390,
    height: 55,
  });
  addText(
    "page.caption",
    "subtitle",
    "",
    { x: 100, y: 805, width: 1400, height: 55 },
    1,
    true,
  );
  base.nodes.push({
    id: "hero",
    type: "image",
    typeVersion: "0.1.0",
    zIndex: 10,
    initialOpacity: 1,
    box: { x: 70, y: 260, width: 560, height: 560 },
    assetRef: { id: resource.id, version: resource.version },
    anchorId: "frame-center",
    fit: "contain",
    rotationDeg: 0,
  });
  input.steps.forEach((step, i) => {
    keys(step, ["label", "detail", "narration", "summary"], "steps." + i);
    for (const field of ["label", "detail", "narration", "summary"])
      text(step[field], recipe.budgets[field], "steps." + i + "." + field);
    const id = "step." + (i + 1),
      y = 285 + i * 170;
    addText(
      id + ".label",
      "caption",
      `${String(i + 1).padStart(2, "0")}  ${step.label}`,
      { x: 730, y, width: 800, height: 64 },
      0,
    );
    addText(
      id + ".detail",
      "subtitle",
      step.detail,
      { x: 730, y: y + 70, width: 800, height: 55 },
      0,
    );
    for (const [j, part] of ["label", "detail"].entries())
      base.actions.push({
        id: "show." + id + "." + part,
        type: "opacity",
        typeVersion: "0.1.0",
        target: { nodeId: id + "." + part, part: "self" },
        startMs: i * 6000 + j * 500,
        endMs: i * 6000 + j * 500 + 400,
        easing: "smoothstep",
        from: 0,
        to: 1,
      });
    base.beats.push({
      id: "beat." + (i + 1),
      startMs: i * 6000,
      endMs: (i + 1) * 6000,
      text: step.narration,
      screenText: step.summary,
      targetIds: [id + ".label", id + ".detail"],
    });
  });
  base.keyframes = [
    { id: "K0", tMs: 0, purpose: "开场" },
    { id: "K1", tMs: 2500, purpose: "第一步" },
    { id: "K2", tMs: 8500, purpose: "第二步" },
    { id: "K3", tMs: 14500, purpose: "第三步" },
    { id: "K4", tMs: 18000, purpose: "终态" },
  ];
}
module.exports = { compileHeroSteps };
