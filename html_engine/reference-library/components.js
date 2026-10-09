(function () {
  "use strict";
  const catalog = window.ComponentCatalog;
  const text = (tag, cls, value) => {
    const el = document.createElement(tag);
    el.className = cls;
    el.textContent = value;
    return el;
  };
  function svg(content) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    el.setAttribute("viewBox", "0 0 300 100");
    el.setAttribute("aria-hidden", "true");
    el.innerHTML = content;
    return el;
  }
  const line = (d) =>
    `<path d="${d}" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`;
  function render(id, value, variantId) {
    const item = catalog.items.find((x) => x.id === id);
    if (!item) throw Error("UNKNOWN_COMPONENT");
    if (
      value !== undefined &&
      (typeof value !== "string" || [...value].length > 36)
    )
      throw Error("TEXT_CAPACITY");
    const variant =
      variantId === undefined
        ? null
        : window.PresentationVariants.items.find((v) => v.id === variantId);
    if (variantId !== undefined && !variant)
      throw Error("UNKNOWN_PRESENTATION_VARIANT");
    if (variant && variant.componentRef !== id)
      throw Error("VARIANT_COMPONENT_MISMATCH");
    const el = text("div", "component " + item.kind, "");
    if (variant) {
      el.classList.add("presentation-variant", variant.className);
      el.dataset.variantId = variant.id;
    }
    const v = value ?? item.text;
    const shapes = {
      branch:
        line(
          "M74 50H145V20H214M145 50V80H214M204 12L214 20L204 28M204 72L214 80L204 88",
        ) +
        '<circle cx="55" cy="50" r="18" fill="var(--tint)" stroke="currentColor"/><rect x="226" y="7" width="52" height="26" rx="8" fill="var(--tint)" stroke="currentColor"/><rect x="226" y="67" width="52" height="26" rx="8" fill="var(--tint)" stroke="currentColor"/>',
      merge:
        line("M51 20H130V50H222M51 80H130V50M212 42L222 50L212 58") +
        '<circle cx="35" cy="20" r="12" fill="var(--tint)" stroke="currentColor"/><circle cx="35" cy="80" r="12" fill="var(--tint)" stroke="currentColor"/><rect x="236" y="34" width="46" height="32" rx="9" fill="var(--tint)" stroke="currentColor"/>',
      cycle:
        line(
          "M108 26Q150 0 193 26M181 13L193 26L177 28M213 44Q239 77 181 84M194 72L181 84L198 91M119 83Q58 72 89 38M75 43L89 38L91 52",
        ) +
        '<circle cx="101" cy="24" r="7" fill="currentColor"/><circle cx="209" cy="34" r="7" fill="currentColor"/><circle cx="162" cy="86" r="7" fill="currentColor"/>',
      hierarchy:
        line("M150 35V56M60 76V56H240V76M150 56V76") +
        '<rect x="121" y="8" width="58" height="26" rx="9" fill="var(--tint)" stroke="currentColor"/><g fill="var(--tint)" stroke="currentColor"><rect x="33" y="76" width="54" height="20" rx="7"/><rect x="123" y="76" width="54" height="20" rx="7"/><rect x="213" y="76" width="54" height="20" rx="7"/></g>',
      bars: '<g fill="var(--tint)"><rect x="40" y="10" width="210" height="19" rx="6"/><rect x="40" y="40" width="210" height="19" rx="6"/><rect x="40" y="70" width="210" height="19" rx="6"/></g><g fill="currentColor"><rect x="40" y="10" width="168" height="19" rx="6"/><rect x="40" y="40" width="126" height="19" rx="6"/><rect x="40" y="70" width="84" height="19" rx="6"/></g><g font-size="13" fill="var(--ink)"><text x="260" y="25">80</text><text x="260" y="55">60</text><text x="260" y="85">40</text></g>',
      proportion:
        '<circle cx="84" cy="50" r="34" fill="none" stroke="var(--tint)" stroke-width="12"/><circle cx="84" cy="50" r="34" fill="none" stroke="currentColor" stroke-width="12" stroke-dasharray="128.177 213.628" transform="rotate(-90 84 50)"/><text x="146" y="58" font-size="32" font-weight="600" fill="var(--ink)">60%</text>',
      matrix:
        '<rect x="25" y="6" width="250" height="88" rx="10" fill="var(--tint)"/><path d="M25 36H275M150 6V94M25 65H275" fill="none" stroke="var(--line)"/><g font-size="14" fill="var(--ink)" text-anchor="middle"><text x="87" y="27">对象 A</text><text x="210" y="27">对象 B</text><text x="87" y="57">相同维度</text><text x="210" y="57">相同维度</text><text x="87" y="85">特征一</text><text x="210" y="85">特征二</text></g>',
      timeline:
        line("M42 42H258") +
        '<g fill="var(--tint)"><circle cx="45" cy="42" r="12"/><circle cx="150" cy="42" r="12"/><circle cx="255" cy="42" r="12"/></g><g fill="currentColor"><circle cx="45" cy="42" r="5"/><circle cx="150" cy="42" r="5"/><circle cx="255" cy="42" r="5"/></g><g font-size="14" fill="var(--ink)" text-anchor="middle"><text x="45" y="76">开始</text><text x="150" y="76">发展</text><text x="255" y="76">完成</text></g>',
      arrow: line("M30 50H266M254 38L266 50L254 62"),
      "double-arrow": line("M32 50H268M44 38L32 50L44 62M256 38L268 50L256 62"),
      elbow: line("M35 75H155V25H266M254 13L266 25L254 37"),
      curve: line("M30 78C90 78 125 22 265 22M253 10L265 22L253 34"),
      rects:
        '<rect x="40" y="18" width="90" height="64"/><rect x="168" y="18" width="90" height="64" rx="16"/>',
      circles:
        '<circle cx="85" cy="50" r="34"/><ellipse cx="215" cy="50" rx="55" ry="32"/>',
      polygons:
        '<path d="M85 15L125 83H45Z"/><path d="M193 16H233L254 50L233 84H193L172 50Z"/>',
      lines: line("M35 50H130M188 77A38 38 0 0 1 264 77"),
    };
    if (shapes[item.kind]) el.append(svg(shapes[item.kind]));
    else if (item.kind.includes("card")) {
      const card = text("div", "sample-card", "");
      if (item.kind === "number-card")
        card.append(text("span", "card-index", "01"));
      card.append(text("strong", "", v), text("p", "", "层级清楚，信息易读。"));
      el.append(card);
    } else if (item.kind === "number") {
      el.append(text("strong", "", v), text("span", "unit", "单位"));
    } else if (item.kind === "leader") {
      el.append(
        svg(
          line("M35 75H105L148 28") +
            '<circle cx="35" cy="75" r="4" fill="currentColor"/>',
        ),
        text("span", "leader-text", v),
      );
    } else el.append(text("span", "sample-text", v));
    el.dataset.componentId = id;
    return el;
  }
  function row(item) {
    const card = text("article", "cell", "");
    const preview = text("div", "sample", "");
    preview.append(render(item.id));
    card.append(
      preview,
      text("div", "cell-name", item.id + "  " + item.name),
      text("p", "cell-note", item.purpose),
    );
    return card;
  }
  function section(title, note, items) {
    const s = text("section", "section", "");
    const h = text("div", "section-head", "");
    h.append(text("h2", "", title), text("p", "", note));
    s.append(h);
    const grid = text("div", "grid", "");
    items.forEach((i) => grid.append(row(i)));
    s.append(grid);
    return s;
  }
  function fontStrip() {
    const strip = text("section", "fonts", "");
    for (const f of catalog.fonts) {
      const card = text("article", "font-cell", "");
      const sample = text(
        "p",
        "",
        f.id === "F04"
          ? "Aa 012345"
          : f.id === "F05"
            ? "const x = 128;"
            : "文字的气质",
      );
      sample.style.fontFamily = '"' + f.family + '"';
      card.append(
        sample,
        text("strong", "", f.id + " " + f.name),
        text("span", "", f.use),
      );
      strip.append(card);
    }
    return strip;
  }
  const atlas = document.getElementById("atlas-body");
  atlas.append(fontStrip());
  for (const category of [...new Set(catalog.items.map((x) => x.category))]) {
    const items = catalog.items.filter((x) => x.category === category);
    atlas.append(section(category, items[0].categoryNote, items));
  }
  const type = document.getElementById("type-body");
  type.append(
    fontStrip(),
    section(
      "文字层级",
      "同一种字体，通过层级与间距组织信息。",
      catalog.items.filter((x) => x.category === "文字层级"),
    ),
  );
  for (const style of window.StyleCatalog.codeStyles.slice(0, 3)) {
    const skin = style.id;
    const box = text("div", "skin-example " + skin, "");
    for (const [key, value] of Object.entries(style.tokens))
      box.style.setProperty("--" + key, value);
    box.append(
      text("p", "skin-label", style.name),
      render("T03", "同一个组件"),
      render("A01"),
      render("C02", "结构保持不变"),
    );
    document.getElementById("skins").append(box);
  }
  document.getElementById("image-file").onchange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const status = document.getElementById("upload-status");
    if (
      !["image/png", "image/jpeg", "image/webp"].includes(file.type) ||
      file.size > 12 * 1024 * 1024
    ) {
      status.textContent = "请选择12MB以内的PNG、JPEG或WebP图片。";
      return;
    }
    const url = URL.createObjectURL(file);
    const image = new Image();
    try {
      image.src = url;
      await image.decode();
      image.alt = "用户选择的图片风格参考";
      document.getElementById("image-slot").replaceChildren(image);
      status.textContent = "图片仅在本地显示。组合板现在可以截图。";
    } catch {
      status.textContent = "图片无法读取，保留原参考。";
    } finally {
      URL.revokeObjectURL(url);
    }
  };
  document.getElementById("skin").onchange = (e) => {
    document.getElementById("atlas").dataset.skin = e.target.value;
    document.getElementById("typography").dataset.skin = e.target.value;
  };
  window.ComponentAtlas = { render, catalog, ready: true };
})();
