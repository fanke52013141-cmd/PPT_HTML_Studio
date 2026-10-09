(function () {
  "use strict";
  const el = (tag, cls, text = "") => {
    const n = document.createElement(tag);
    n.className = cls;
    n.textContent = text;
    return n;
  };
  const catalogs = {
    component: window.ComponentCatalog.items,
    variant: window.PresentationVariants.items,
    effect: window.EffectsCatalog.items,
    composition: window.StaticCatalog.items,
    font: window.ComponentCatalog.fonts,
  };
  function render({ id, text, variantId, paletteId, role = "primary" } = {}) {
    const wrapper = el(
      "div",
      "standard-surface component-reference standard-instance",
    );
    for (const [key, value] of Object.entries(window.StandardTokens))
      wrapper.style.setProperty("--" + key, value);
    if (paletteId !== undefined) {
      const palette = window.StandardPalettes.palettes.find(
        (x) => x.id === paletteId,
      );
      const roles = ["primary", "secondary", "accent", "category"];
      if (!palette || !roles.includes(role))
        throw Error("UNKNOWN_PALETTE_OR_ROLE");
      wrapper.style.setProperty("--ink", palette.ink);
      wrapper.style.setProperty("--muted", palette.muted);
      wrapper.style.setProperty("--accent", palette[role]);
      wrapper.style.setProperty("--tint", palette.tints[roles.indexOf(role)]);
      wrapper.dataset.palette = paletteId;
    } else wrapper.classList.add("standard-neutral");
    let node;
    if (catalogs.component.some((x) => x.id === id))
      node = window.ComponentAtlas.render(id, text, variantId);
    else if (catalogs.variant.some((x) => x.id === id)) {
      if (variantId !== undefined) throw Error("DUPLICATE_VARIANT");
      const v = catalogs.variant.find((x) => x.id === id);
      node = window.ComponentAtlas.render(v.componentRef, text ?? v.value, id);
    } else if (catalogs.effect.some((x) => x.id === id)) {
      if (text !== undefined || variantId !== undefined)
        throw Error("UNSUPPORTED_EFFECT_OPTIONS");
      node = window.ReferenceEffects.renderEffect(id);
    } else if (catalogs.composition.some((x) => x.id === id)) {
      if (text !== undefined || variantId !== undefined)
        throw Error("FIXED_COMPOSITION");
      node = window.StaticReference.render(id);
      wrapper.dataset.standardContext = id.startsWith("V")
        ? "precision"
        : id.startsWith("X")
          ? "usage"
          : id.startsWith("H")
            ? "fusion"
            : "composition";
    } else if (catalogs.font.some((x) => x.id === id)) {
      if (
        variantId !== undefined ||
        (text !== undefined &&
          (typeof text !== "string" || [...text].length > 36))
      )
        throw Error("INVALID_FONT_OPTIONS");
      const f = catalogs.font.find((x) => x.id === id);
      node = el("div", "standard-font");
      const p = el(
        "p",
        "",
        text ??
          (id === "F04"
            ? "Aa 012345"
            : id === "F05"
              ? "const x = 128;"
              : "文字的气质"),
      );
      p.style.fontFamily = '"' + f.family + '"';
      node.append(p);
    } else throw Error("UNKNOWN_STANDARD_COMPONENT");
    wrapper.append(node);
    wrapper.dataset.referenceId = id;
    return wrapper;
  }
  function sample(kind, id) {
    if (kind === "font") {
      const f = catalogs.font.find((x) => x.id === id),
        n = el("div", "standard-font");
      const t = el(
        "p",
        "",
        id === "F04"
          ? "Aa 012345"
          : id === "F05"
            ? "const x = 128;"
            : "文字的气质",
      );
      t.style.fontFamily = '"' + f.family + '"';
      n.append(t);
      return n;
    }
    return render({ id });
  }
  function cell(kind, id) {
    const item = catalogs[kind].find((x) => x.id === id),
      n = el("section", "standard-cell");
    n.dataset.entryId = id;
    const heading = el("div", "standard-cell-heading", id + " / " + item.name);
    const stage = el("div", "standard-stage");
    stage.append(sample(kind, id));
    n.append(
      heading,
      stage,
      el("p", "standard-note", item.purpose || item.use || ""),
    );
    return n;
  }
  function overview() {
    const grid = el("div", "standard-grid overview-grid");
    const examples = [
      [
        "标题与副标题",
        [
          ["T01", "让重点被看见"],
          ["T02", "清楚的层次，舒适的阅读"],
        ],
      ],
      [
        "正文与解释",
        [
          ["T04", "准确的信息，需要清楚的表达。"],
          ["T05", "用留白、比例与层次帮助理解。"],
        ],
      ],
      ["普通卡片", [["PV11", "清楚的结构"]]],
      ["编号卡片", [["PV12", "建立重点"]]],
      ["箭头与关系", [["A01"], ["R01"]]],
      [
        "标签与强调",
        [
          ["N01", "分类标签"],
          ["T07", "重要的信息"],
        ],
      ],
    ];
    examples.forEach(([name, items], i) => {
      const n = el("section", "standard-cell");
      n.append(
        el(
          "div",
          "standard-cell-heading",
          String(i + 1).padStart(2, "0") + " / " + name,
        ),
      );
      const s = el("div", "standard-stage");
      items.forEach(([id, text]) => s.append(render({ id, text })));
      n.append(s);
      grid.append(n);
    });
    return grid;
  }
  const main = el("main", "standard-library");
  const nav = el("nav", "standard-navigation");
  nav.append(el("strong", "", "标准组件库 1.0"));
  for (const p of window.StandardPages.pages) {
    const a = el("a", "", p.title);
    a.href = "#" + p.id;
    nav.append(a);
    const board = el(
      "article",
      "standard-page standard-surface component-reference standard-neutral",
    );
    board.id = p.id;
    board.dataset.kind = p.kind;
    for (const [key, value] of Object.entries(window.StandardTokens))
      board.style.setProperty("--" + key, value);
    const h = el("header", "standard-header");
    const title = el("div", "");
    title.append(el("h1", "", p.title), el("p", "", p.note));
    h.append(
      title,
      el(
        "span",
        "standard-page-number",
        String(main.children.length + 1).padStart(2, "0") + " / 24",
      ),
    );
    board.append(h);
    if (p.kind === "overview") board.append(overview());
    else {
      const g = el("div", "standard-grid");
      g.dataset.count = p.ids.length;
      p.ids.forEach((id) => g.append(cell(p.kind, id)));
      board.append(g);
    }
    board.append(
      el(
        "footer",
        "standard-footer",
        "HTML · CSS · SVG   /   黑白灰结构参考   /   配色与图片风格独立输入",
      ),
    );
    main.append(board);
  }
  document.body.replaceChildren(nav, main);
  window.StandardLibrary = {
    render,
    catalog: window.StandardPages,
    ready: true,
  };
})();
