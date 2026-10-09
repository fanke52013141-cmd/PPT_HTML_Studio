(function () {
  "use strict";
  const catalog = window.StylePairCatalog;
  const node = (tag, cls, value = "") => {
    const e = document.createElement(tag);
    e.className = cls;
    e.textContent = value;
    return e;
  };
  function pic(pair, cls) {
    const i = node("img", cls);
    i.src = window.StylePairAssets[pair.asset.id];
    i.alt = pair.asset.alt;
    return i;
  }
  function render(id) {
    const pair = catalog.pairs.find((p) => p.id === id);
    if (!pair) throw Error("UNKNOWN_STYLE_PAIR");
    const board = node("article", "board pair-board");
    board.id = pair.id.toLowerCase();
    board.dataset.pairId = pair.id;
    window.ReferenceEffects.applyCodeStyle(board, pair.codeStyleRef);
    const header = node("header", "board-header");
    const title = node("div", "");
    title.append(node("h1", "", pair.name), node("p", "", pair.summary));
    header.append(
      title,
      node("div", "version", pair.id + " / 静态配对 0.4\n图片 + 代码 + 融合"),
    );
    board.append(header);
    const split = node("div", "pair-reference-grid");
    const imagePanel = node("section", "pair-source-panel");
    imagePanel.append(
      node("h2", "panel-heading", "A / 图片风格"),
      pic(pair, "pair-source-image"),
    );
    const medium = node(
      "p",
      "source-note",
      pair.imageStyle.rendering + " · " + pair.imageStyle.material,
    );
    imagePanel.append(medium);
    const codePanel = node("section", "pair-code-panel");
    codePanel.append(node("h2", "panel-heading", "B / 代码风格"));
    const titleSample = window.ComponentAtlas.render(
      "T01",
      "清楚表达，留下余地",
    );
    titleSample.classList.add("pair-title-sample");
    codePanel.append(
      titleSample,
      node("p", "pair-subtitle", "统一字体、线宽、容器与视觉层次"),
    );
    const swatches = node("div", "pair-swatches");
    const tokens = window.StyleCatalog.codeStyles.find(
      (s) => s.id === pair.codeStyleRef,
    ).tokens;
    for (const [role, name] of [
      ["ink", "主文字"],
      ["accent", "强调"],
      ["tint", "浅面"],
      ["line", "边界"],
    ]) {
      const swatch = node("div", "swatch");
      const chip = node("span", "swatch-chip");
      chip.style.background = tokens[role];
      swatch.append(chip, node("span", "", name));
      swatches.append(swatch);
    }
    codePanel.append(swatches);
    const mini = node("div", "pair-mini-row");
    mini.append(
      window.ComponentAtlas.render("A04"),
      window.ComponentAtlas.render("C02", "清晰的信息容器"),
    );
    codePanel.append(mini);
    const structure = node("p", "source-note", pair.codeDescription);
    codePanel.append(structure);
    split.append(imagePanel, codePanel);
    board.append(split);
    const composition = node("section", "pair-composition");
    composition.dataset.layoutId = "PAIR-LAYOUT-01";
    const content = catalog.content;
    const copy = node("div", "pair-hero-copy");
    copy.append(
      node("span", "pair-eyebrow", content.eyebrow),
      node("h2", "pair-hero-title", content.title),
      node("p", "pair-hero-description", content.description),
    );
    const sub = node("div", "pair-keyline");
    sub.append(
      node("span", "pair-keyline-dot"),
      node("span", "", content.keyline),
    );
    copy.append(sub);
    composition.append(copy);
    const imageSlot = node("div", "pair-hero-image");
    imageSlot.append(pic(pair, "pair-subject"));
    composition.append(imageSlot);
    const steps = node("div", "pair-steps");
    for (const [index, entry] of content.steps.entries()) {
      const card = node("div", "pair-step");
      card.dataset.componentId = "C04";
      card.append(
        node("span", "pair-step-index", String(index + 1).padStart(2, "0")),
        node("strong", "", entry.title),
        node("p", "", entry.copy),
      );
      steps.append(card);
    }
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 1694 80");
    svg.setAttribute("aria-hidden", "true");
    svg.classList.add("pair-connectors");
    svg.innerHTML =
      '<path d="M518 40H586M576 32L586 40L576 48M1109 40H1177M1167 32L1177 40L1167 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
    steps.append(svg);
    composition.append(steps);
    board.append(composition);
    const rule = node("div", "pair-shared-rule");
    rule.append(
      node("strong", "", "组合规则"),
      node(
        "p",
        "",
        pair.shared.palette +
          "；" +
          pair.shared.weight +
          "；" +
          pair.shared.space,
      ),
    );
    board.append(rule);
    board.append(
      node(
        "footer",
        "board-footer",
        "按编号使用。示例文字与说明不进入成片；实际文案另附。基础结构相同，图片主体不同；新图片须遵循 A，文字与关系遵循 B。",
      ),
    );
    return board;
  }
  const target = document.getElementById("style-pairs");
  for (const pair of catalog.pairs) target.append(render(pair.id));
  // The global base-board selector changes only base boards; paired examples retain their registered style.
  document.getElementById("skin").addEventListener("change", () => {
    for (const pair of catalog.pairs)
      window.ReferenceEffects.applyCodeStyle(
        document.getElementById(pair.id.toLowerCase()),
        pair.codeStyleRef,
      );
  });
  window.StylePairs = { catalog, render, ready: true };
})();
