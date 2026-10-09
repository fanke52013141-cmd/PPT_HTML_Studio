(function () {
  "use strict";
  const { groups, items } = window.EffectsCatalog;
  const node = (tag, cls, value = "") => {
    const e = document.createElement(tag);
    e.className = cls;
    e.textContent = value;
    return e;
  };
  function applyCodeStyle(root, id) {
    const style = window.StyleCatalog.codeStyles.find((s) => s.id === id);
    if (!style) throw Error("UNKNOWN_CODE_STYLE");
    for (const [key, value] of Object.entries(style.tokens))
      root.style.setProperty("--" + key, value);
    root.dataset.skin = id;
  }
  function renderEffect(id) {
    if (!items.some((i) => i.id === id)) throw Error("UNKNOWN_EFFECT");
    const stage = node("div", "effect-stage");
    stage.dataset.effectId = id;
    stage.append(
      node(
        "div",
        "effect-object effect-" + id,
        Number(id.slice(1)) >= 25 ? "文字效果" : "",
      ),
    );
    return stage;
  }
  const body = document.getElementById("effects-body");
  for (const group of groups) {
    const section = node("section", "section");
    const head = node("div", "section-head");
    head.append(
      node("h2", "", group[0]),
      node("p", "", "中性效果示例；颜色可由代码风格替换。"),
    );
    section.append(head);
    const grid = node("div", "grid");
    for (const item of items.filter((i) => i.category === group[0])) {
      const card = node("article", "cell effect-cell");
      card.append(
        renderEffect(item.id),
        node("div", "cell-name", item.id + "  " + item.name),
      );
      const note = node("div", "use-note");
      note.append(
        node(
          "span",
          "",
          { recommended: "推荐 / ", local: "局部 / ", caution: "慎用 / " }[
            item.recommendation
          ] + item.purpose,
        ),
        node("span", "", item.implementation),
      );
      card.append(note);
      grid.append(card);
    }
    section.append(grid);
    body.append(section);
  }
  window.ReferenceEffects = {
    items,
    renderEffect,
    applyCodeStyle,
    ready: true,
  };
})();
