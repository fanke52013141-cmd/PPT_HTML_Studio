(function () {
  "use strict";
  const catalog = window.PresentationVariants;
  const n = (tag, cls, value) => {
    const e = document.createElement(tag);
    e.className = cls;
    if (value) e.textContent = value;
    return e;
  };
  function section(category) {
    const root = n("section", "section variant-section");
    const heading = n("div", "section-head");
    heading.append(
      n("h2", "", category),
      n("p", "", "同一身份，按表达需要选择呈现。"),
    );
    const grid = n("div", "grid");
    for (const v of catalog.items.filter((v) => v.category === category)) {
      const cell = n("article", "cell");
      const sample = n("div", "sample");
      sample.append(
        window.ComponentAtlas.render(v.componentRef, v.value, v.id),
      );
      cell.append(
        sample,
        n("div", "cell-name", v.id + " · " + v.name),
        n("p", "cell-note", v.componentRef + " / " + v.purpose),
      );
      grid.append(cell);
    }
    root.append(heading, grid);
    return root;
  }
  for (const category of new Set(catalog.items.map((v) => v.category)))
    document.querySelector("#variants-body").append(section(category));
  window.ComponentPresentations = { catalog, section, ready: true };
})();
