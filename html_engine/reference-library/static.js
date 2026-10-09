(function () {
  "use strict";
  const catalog = window.StaticCatalog;
  const el = (tag, cls, value = "") => {
    const n = document.createElement(tag);
    n.className = cls;
    n.textContent = value;
    return n;
  };
  const label = (value) => el("span", "spec-kicker", value);
  const paragraph = (value) => el("p", "spec-copy", value);
  function svg(markup) {
    const n = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    n.setAttribute("viewBox", "0 0 500 200");
    n.setAttribute("aria-hidden", "true");
    n.innerHTML = markup;
    return n;
  }
  const path = (d) =>
    `<path d="${d}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
  const arrow = (d) => path(d);
  const dot = (x, y) =>
    `<circle cx="${x}" cy="${y}" r="3.5" fill="currentColor"/>`;
  function image(cls = "fusion-image") {
    const n = el("img", cls);
    n.src = window.StaticAsset;
    n.alt = "复用的蓝色纸飞机独立图片，静态融合示例";
    return n;
  }
  function render(id) {
    const item = catalog.items.find((x) => x.id === id);
    if (!item) throw Error("UNKNOWN_STATIC_REFERENCE");
    const n = el("div", "specimen specimen-" + id);
    n.dataset.referenceId = id;
    if (id === "P01") {
      n.append(
        label("标题 / 导语 / 分隔"),
        el("h3", "spec-heading", "让信息自然展开"),
        paragraph("明确的主次关系，让阅读从标题开始，沿着解释与留白继续。"),
        el("div", "spec-rule"),
        el("span", "spec-footnote", "简洁层级 · 清晰行长 · 统一基线"),
      );
    }
    if (id === "P02") {
      n.append(
        label("01 / 编号与两行标题"),
        el("h3", "spec-heading", "先看见重点，\n再理解关系。"),
        paragraph("编号建立顺序，标题形成重心；解释语靠近所说明的内容。"),
      );
    }
    if (id === "P03") {
      n.append(label("数字 / 单位 / 说明"));
      const row = el("div", "spec-number");
      row.append(el("strong", "", "128"), el("span", "", "单位"));
      n.append(
        row,
        el("h3", "spec-small-heading", "数字成为视觉焦点"),
        paragraph("数据示例。数字、单位与说明分别控制大小，并对齐共同基线。"),
      );
    }
    const graphs = {
      V01: arrow("M38 100H456M446 91L456 100L446 109") + dot(38, 100),
      V02:
        arrow("M38 147C160 147 180 58 455 58M445 49L455 58L445 67") +
        dot(38, 147),
      V03:
        path(
          "M80 100H222Q232 100 232 90V58Q232 48 242 48H424M232 100V142Q232 152 242 152H424",
        ) +
        dot(80, 100) +
        dot(424, 48) +
        dot(424, 152),
      V04:
        path("M55 53V43H445V53M55 147V157H445V147") +
        '<rect x="90" y="72" width="130" height="56" rx="8"/><rect x="280" y="72" width="130" height="56" rx="8"/>',
      V05:
        '<circle class="ring-track" cx="145" cy="100" r="63"/><path d="M145 37A63 63 0 1 1 85 120" fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round"/>' +
        path("M245 75H445M245 105H399M245 135H345"),
      V06:
        path("M75 160L150 82H320M320 82H440") +
        dot(75, 160) +
        '<circle cx="75" cy="160" r="14" fill="none" stroke="currentColor" stroke-opacity=".2"/>',
    };
    if (graphs[id]) {
      n.append(svg(graphs[id]));
      const a = el(
        "span",
        "graph-label",
        {
          V01: "留白与方向",
          V02: "平滑曲线",
          V03: "共同起点",
          V04: "同一组信息",
          V05: "刻度与层次",
          V06: "观察位置",
        }[id],
      );
      n.append(a);
      if (id === "V03")
        n.append(el("span", "graph-secondary", "分支 A / 分支 B"));
      if (id === "V05") n.append(el("strong", "ring-value", "示意"));
    }
    if (id.startsWith("X")) {
      const effect = {
        X01: "E05",
        X02: "E08",
        X03: "E01",
        X04: "E19",
        X05: "E21",
        X06: "E28",
      }[id];
      if (id === "X06") {
        n.append(
          label("局部强调"),
          el("h3", "spec-heading", "重要信息，\n恰好被看见。"),
        );
        const heading = n.querySelector("h3");
        heading.firstChild.textContent = "重要信息，";
        const word = el("span", "effect-E28", "恰好被看见。");
        heading.append(el("br", ""), word);
        n.append(paragraph("强调只作用于关键词，保留其余文字的阅读秩序。"));
      } else {
        const stage = window.ReferenceEffects.renderEffect(effect);
        stage.classList.add("effect-usage");
        const obj = stage.querySelector(".effect-object");
        obj.append(
          label(
            id === "X01" ? "轻层次" : id === "X02" ? "重点层次" : "效果与内容",
          ),
          el("h3", "spec-small-heading", item.sample),
          paragraph(item.copy),
        );
        n.append(stage);
      }
    }
    if (id.startsWith("H")) {
      n.append(image());
      if (id === "H01") {
        const copy = el("div", "fusion-copy");
        copy.append(
          label("图片 + 文字"),
          el("h3", "spec-heading", "让想法\n拥有方向"),
          paragraph("清晰文字与独立主体，共享留白和视觉重心。"),
        );
        n.append(copy);
      }
      if (id === "H02") {
        const overlay = svg(
          path("M350 118L420 63H465M115 171L72 182H35") +
            dot(350, 118) +
            dot(115, 171),
        );
        overlay.classList.add("fusion-leaders");
        n.append(
          overlay,
          el("span", "fusion-label label-top", "方向留白"),
          el("span", "fusion-label label-bottom", "主体轮廓"),
        );
      }
      if (id === "H03") {
        const card = el("div", "fusion-card");
        card.append(
          label("图片 + 容器"),
          el("h3", "spec-small-heading", "保留主体，承接信息"),
          paragraph("卡片靠近主体，文字获得稳定的阅读区域。"),
        );
        n.append(card);
      }
    }
    return n;
  }
  for (const [category, target] of [
    ["排版", "composition-body"],
    ["关系", "precision-body"],
    ["效果用法", "usage-body"],
    ["图片融合", "fusion-body"],
  ]) {
    const container = document.getElementById(target);
    for (const item of catalog.items.filter((x) => x.category === category)) {
      const card = el("article", "spec-card");
      card.append(render(item.id));
      const caption = el("div", "spec-caption");
      caption.append(
        el("strong", "", item.id + " / " + item.name),
        el("p", "", item.purpose),
      );
      card.append(caption);
      container.append(card);
    }
  }
  const allBoards = () => document.querySelectorAll(".board");
  for (const board of allBoards())
    window.ReferenceEffects.applyCodeStyle(board, "neutral");
  document.getElementById("skin").addEventListener("change", (e) => {
    for (const board of allBoards())
      window.ReferenceEffects.applyCodeStyle(board, e.target.value);
  });
  window.StaticReference = { catalog, render, ready: true };
})();
