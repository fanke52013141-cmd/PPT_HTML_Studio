(() => {
  "use strict";
  const data = window.TokenVisualDefinition,
    stage = document.querySelector("#stage"),
    frame = document.querySelector("#frame");
  const ns = "http://www.w3.org/2000/svg",
    scenes = [],
    registries = [],
    painters = [];
  const clamp = (x) => Math.max(0, Math.min(1, x)),
    ease = (x) => {
      x = clamp(x);
      return x * x * (3 - 2 * x);
    },
    phase = (t, start, duration = 700) => ease((t - start) / duration);
  function scene(id) {
    const s = document.createElement("section");
    s.className = "scene";
    s.dataset.sceneId = id;
    stage.append(s);
    scenes.push(s);
    const map = new Map();
    registries.push(map);
    return { s, map };
  }
  function node(ctx, id, box, cls = "", text, tag = "div") {
    const el = document.createElement(tag);
    el.className = "node " + cls;
    el.dataset.objectId = id;
    if (text !== undefined) el.textContent = text;
    Object.assign(el.style, {
      left: box[0] + "px",
      top: box[1] + "px",
      width: box[2] + "px",
      height: box[3] + "px",
    });
    ctx.s.append(el);
    ctx.map.set(id, el);
    return el;
  }
  function svg(ctx) {
    const el = document.createElementNS(ns, "svg");
    el.setAttribute("viewBox", "0 0 1600 900");
    el.classList.add("svg-layer");
    ctx.s.append(el);
    return el;
  }
  function shape(parent, tag, attrs, id, ctx) {
    const e = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    parent.append(e);
    if (id) {
      e.dataset.objectId = id;
      ctx.map.set(id, e);
    }
    return e;
  }
  function path(parent, d, color = "#c6cfdf", width = 3, id, ctx) {
    return shape(
      parent,
      "path",
      {
        d,
        fill: "none",
        stroke: color,
        "stroke-width": width,
        "stroke-linecap": "round",
      },
      id,
      ctx,
    );
  }
  function heading(ctx, title, subtitle) {
    const h = node(ctx, "heading", [100, 65, 1420, 110], "text title");
    const pos = title.indexOf("：");
    if (pos >= 0) {
      const a = document.createElement("span");
      a.className = "accent";
      a.textContent = title.slice(0, pos);
      h.append(a, document.createTextNode(title.slice(pos)));
    } else h.textContent = title;
    node(ctx, "subtitle", [104, 185, 1390, 55], "text subtitle", subtitle);
  }
  function image(ctx, id, box, asset) {
    const el = node(ctx, id, box, "hero", undefined, "img");
    el.src = "assets/" + asset;
    el.alt = "生图科普示意资产";
    return el;
  }
  function reveal(el, t, start, duration = 700) {
    const p = phase(t, start, duration);
    el.style.opacity = p;
    el.style.transform = `translateY(${(1 - p) * 12}px)`;
  }
  function opacity(el, value) {
    el.style.opacity = clamp(value);
  }
  function chip(ctx, id, box, text, color) {
    return node(ctx, id, box, "chip " + color, text);
  }
  function baseCaption(ctx) {
    return node(
      ctx,
      "narration.caption",
      [100, 839, 1400, 46],
      "text caption",
      "",
    );
  }
  function arrow(parent, x1, y, x2, color, id, ctx) {
    path(parent, `M ${x1} ${y} H ${x2}`, color, 3, id, ctx);
    path(
      parent,
      `M ${x2 - 13} ${y - 9} L ${x2} ${y} L ${x2 - 13} ${y + 9}`,
      color,
      3,
    );
  }
  function definition() {
    const ctx = scene("definition");
    heading(ctx, data.sceneList[0].title, "从自然语言，到机器可计算的表示");
    node(ctx, "source.panel", [100, 315, 410, 155], "panel");
    node(
      ctx,
      "source.text",
      [135, 350, 350, 90],
      "text title",
      "Hello world!",
    ).style.fontSize = "53px";
    const pieces = [
      ["Hello", "coral", 100, 160],
      ["␠world", "blue", 275, 190],
      ["!", "purple", 480, 80],
    ].map(([text, color, x, w], i) =>
      chip(ctx, "token." + i, [x, 535, w, 80], text, color),
    );
    const core = image(ctx, "model", [575, 255, 520, 400], "core-v1.png");
    const ids = chip(
      ctx,
      "token.ids",
      [630, 655, 410, 62],
      "9906 · 1917 · 0",
      "purple",
    );
    ids.style.fontSize = "28px";
    const layer = svg(ctx);
    arrow(layer, 525, 430, 610, "#b7c9ec", "flow.input", ctx);
    arrow(layer, 1020, 430, 1100, "#beb1e2", "flow.output", ctx);
    const vectors = node(ctx, "vectors", [1150, 320, 320, 285], "");
    const fills = ["#f4a2b2", "#9dbdf0", "#bdace8"];
    for (let c = 0; c < 3; c++) {
      const col = document.createElement("div");
      Object.assign(col.style, {
        position: "absolute",
        left: c * 108 + "px",
        width: "88px",
        height: "260px",
        borderRadius: "22px",
        background: ["#fff0f3", "#edf4ff", "#f2edfc"][c],
        border: "1px solid white",
        padding: "24px 14px",
      });
      for (let j = 0; j < 6; j++) {
        const bar = document.createElement("div");
        Object.assign(bar.style, {
          width: [54, 43, 61, 35, 49, 57][(j + c) % 6] + "px",
          height: "19px",
          background: fills[c],
          borderRadius: "5px",
          marginBottom: "13px",
        });
        col.append(bar);
      }
      vectors.append(col);
    }
    node(
      ctx,
      "vectors.label",
      [1140, 620, 350, 55],
      "text small",
      "向量示意 · 非测量值",
    );
    const band = node(
      ctx,
      "conclusion.band",
      [180, 745, 1240, 88],
      "note-band",
    );
    const conclusion = node(
      ctx,
      "conclusion",
      [225, 760, 1150, 66],
      "text label",
      "文字   →   Token 编号   →   向量表示",
    );
    conclusion.style.fontSize = "44px";
    conclusion.style.textAlign = "center";
    const moving = pieces.map((el, i) => {
      const copy = chip(
        ctx,
        "transient.token." + i,
        [0, 0, 100, 50],
        ["Hello", "␠world", "!"][i],
        ["coral", "blue", "purple"][i],
      );
      copy.style.fontSize = "21px";
      return copy;
    });
    const caption = baseCaption(ctx);
    painters.push((t) => {
      pieces.forEach((e, i) => reveal(e, t, 650 + i * 700));
      reveal(ids, t, 8000);
      reveal(vectors, t, 10300);
      reveal(conclusion, t, 11000);
      reveal(band, t, 11000);
      moving.forEach((e, i) => {
        const p = clamp((t - 4300 - i * 700) / 2800);
        opacity(e, t >= 4300 + i * 700 && p < 1 ? 1 : 0);
        e.style.transform = `translate(${140 + (660 - 140) * ease(p)}px,${540 - 100 * Math.sin(p * Math.PI) - 80 * ease(p)}px)`;
      });
      caption.textContent =
        captionAt(0, t) + "  ·  cl100k_base 示例，装置为示意";
    });
  }
  function splitting() {
    const ctx = scene("splitting");
    heading(ctx, data.sceneList[1].title, "固定分词器，才有准确的切分结果");
    node(ctx, "english.panel", [100, 285, 380, 185], "panel");
    node(
      ctx,
      "english.original",
      [125, 324, 340, 80],
      "text label",
      "Hello world!",
    ).style.fontSize = "46px";
    node(ctx, "english.label", [126, 406, 330, 42], "text small", "原始文本");
    const en = [
      chip(ctx, "english.token.0", [565, 300, 180, 105], "Hello", "coral"),
      chip(ctx, "english.token.1", [765, 300, 220, 105], "␠world", "purple"),
      chip(ctx, "english.token.2", [1005, 300, 110, 105], "!", "blue"),
    ];
    const count = node(
      ctx,
      "english.count",
      [1190, 294, 300, 160],
      "text metric",
      "3",
    );
    count.style.color = "#f47f94";
    node(ctx, "english.unit", [1300, 370, 190, 60], "text label", "Token");
    node(ctx, "divider", [100, 500, 1390, 1], "line");
    node(ctx, "chinese.panel", [100, 555, 410, 170], "panel");
    node(
      ctx,
      "chinese.original",
      [125, 590, 375, 65],
      "text label",
      "人工智能很有趣",
    ).style.fontSize = "40px";
    node(ctx, "chinese.label", [126, 671, 350, 40], "text small", "7 个汉字");
    const cn = data.facts.chineseIds.map((id, i) => {
      const el = chip(
        ctx,
        "chinese.token." + i,
        [565 + (i % 5) * 108, 555 + Math.floor(i / 5) * 82, 96, 65],
        String(id),
        ["coral", "purple", "blue", "mint", "purple"][i % 5],
      );
      el.classList.add("token-id");
      return el;
    });
    const contrast = node(
      ctx,
      "count.contrast",
      [1165, 550, 330, 130],
      "text metric",
      "7 ≠ 10",
    );
    contrast.style.fontSize = "83px";
    contrast.style.color = "#f47f94";
    const note = node(
      ctx,
      "chinese.note",
      [1110, 701, 380, 80],
      "text small",
      "实测编号 · 部分 Token 对应字节片段",
    );
    note.style.whiteSpace = "normal";
    const foot = node(
      ctx,
      "encoding.note",
      [100, 789, 1380, 55],
      "text small",
      "cl100k_base · ␠ 表示空格 · 十个色块对应十个 Token 编号",
    );
    const caption = baseCaption(ctx);
    painters.push((t) => {
      en.forEach((e, i) => reveal(e, t, 700 + i * 650));
      reveal(count, t, 2800);
      cn.forEach((e, i) => reveal(e, t, 5500 + i * 230));
      reveal(contrast, t, 8500);
      reveal(note, t, 9500);
      caption.textContent = captionAt(1, t);
    });
  }
  function billing() {
    const ctx = scene("billing");
    heading(
      ctx,
      data.sceneList[2].title,
      "用量与单价分别核对 · 下方数量仅作示意",
    );
    const input = node(ctx, "input.panel", [100, 300, 380, 280], "panel");
    input.style.background = "linear-gradient(140deg,#fff7f8,#ffe9ef)";
    node(ctx, "input.label", [140, 329, 300, 62], "text label", "输入");
    const iv = node(
      ctx,
      "input.amount",
      [138, 398, 320, 150],
      "text metric",
      "120",
    );
    iv.style.color = "#f47f94";
    node(ctx, "input.unit", [145, 530, 300, 45], "text body", "Token");
    image(ctx, "model", [480, 220, 640, 440], "billing-core-v1.png");
    const out = node(ctx, "output.panel", [1120, 300, 380, 280], "panel");
    out.style.background = "linear-gradient(140deg,#f4f8ff,#e5edff)";
    const ol = node(
        ctx,
        "output.label",
        [1160, 329, 300, 62],
        "text label",
        "输出",
      ),
      ov = node(
        ctx,
        "output.amount",
        [1158, 398, 320, 150],
        "text metric",
        "80",
      ),
      ou = node(ctx, "output.unit", [1165, 530, 300, 45], "text body", "Token");
    ov.style.color = "#80a5ec";
    const layer = svg(ctx);
    arrow(layer, 490, 440, 605, "#edb0be", "flow.input", ctx);
    arrow(layer, 995, 440, 1105, "#adbfec", "flow.output", ctx);
    const movers = [0, 1, 2, 3, 4, 5].map((i) => {
      const el = chip(
        ctx,
        "transient.packet." + i,
        [0, 0, 45, 37],
        i % 2 ? "···" : "≡",
        i < 3 ? "coral" : "blue",
      );
      el.style.fontSize = "24px";
      el.style.borderRadius = "10px";
      return el;
    });
    const formula = node(
      ctx,
      "formula.band",
      [160, 680, 1280, 125],
      "note-band",
    );
    node(
      ctx,
      "formula.title",
      [640, 645, 320, 55],
      "text label",
      "费用示意",
    ).style.textAlign = "center";
    const terms = [
      ["输入量", "coral", 210, 210],
      ["×", "", 445, 60],
      ["输入单价", "purple", 520, 250],
      ["＋", "", 790, 65],
      ["输出量", "blue", 875, 200],
      ["×", "", 1095, 55],
      ["输出单价", "purple", 1170, 230],
    ].map(([tx, color, x, w], i) =>
      color
        ? chip(ctx, "formula.term." + i, [x, 713, w, 60], tx, color)
        : node(ctx, "formula.term." + i, [x, 720, w, 60], "text label", tx),
    );
    terms.forEach((e) => (e.style.fontSize = "31px"));
    const caption = baseCaption(ctx);
    painters.push((t) => {
      [out, ol, ov, ou].forEach((e) => reveal(e, t, 5000));
      reveal(formula, t, 10500);
      terms.forEach((e, i) => reveal(e, t, 10500 + i * 100));
      movers.forEach((e, i) => {
        const start = i < 3 ? 1800 + i * 500 : 5500 + (i - 3) * 500,
          p = clamp((t - start) / 2900);
        opacity(e, t >= start && p < 1 ? 1 : 0);
        const x = i < 3 ? 480 + 230 * ease(p) : 890 + 230 * ease(p);
        e.style.transform = `translate(${x}px,${418 + Math.sin(p * Math.PI) * (i % 2 ? 35 : -35)}px)`;
      });
      caption.textContent = captionAt(2, t);
    });
  }
  // Remaining scene builders use the same atoms; no generated slide is used as a runtime background.

  function context() {
    const ctx = scene("context");
    heading(
      ctx,
      data.sceneList[3].title,
      "4k 仅教学假设 · 预留回答也需要占据预算",
    );
    const meter = node(
      ctx,
      "budget.meter",
      [1050, 235, 450, 65],
      "text label",
      "0 / 4,000",
    );
    meter.style.fontSize = "42px";
    meter.style.textAlign = "right";
    const layer = svg(ctx);
    const defs = shape(layer, "defs", {});
    const clip = shape(defs, "clipPath", { id: "capacity-clip" });
    shape(clip, "rect", { x: 160, y: 335, width: 1200, height: 150, rx: 30 });
    for (const [id, colors] of [
      ["glass", ["#ffffffcc", "#ffffff0c", "#ffffff99"]],
      ["hist", ["#f9c5d0", "#efa2b3"]],
      ["question", ["#e4d9fa", "#beabe5"]],
    ]) {
      const grad = shape(defs, "linearGradient", {
        id: "capacity-" + id,
        x1: "0",
        y1: "0",
        x2: "0",
        y2: "1",
      });
      colors.forEach((color, i) =>
        shape(grad, "stop", {
          offset: i / (colors.length - 1),
          "stop-color": color,
        }),
      );
    }
    const pattern = shape(defs, "pattern", {
      id: "reserve-hatch",
      width: 18,
      height: 18,
      patternUnits: "userSpaceOnUse",
      patternTransform: "rotate(35)",
    });
    shape(pattern, "rect", { width: 18, height: 18, fill: "#dae7fc" });
    shape(pattern, "line", {
      x1: 0,
      y1: 0,
      x2: 0,
      y2: 18,
      stroke: "#afc7ef",
      "stroke-width": 5,
    });
    shape(
      layer,
      "rect",
      {
        x: 160,
        y: 335,
        width: 1200,
        height: 150,
        rx: 30,
        fill: "#f0f2f7",
        stroke: "#dce3ef",
        "stroke-width": 2,
      },
      "capacity.frame",
      ctx,
    );
    const group = shape(layer, "g", { "clip-path": "url(#capacity-clip)" });
    const history = shape(
        group,
        "rect",
        { x: 160, y: 335, width: 0, height: 150, fill: "url(#capacity-hist)" },
        "capacity.history",
        ctx,
      ),
      question = shape(
        group,
        "rect",
        {
          x: 610,
          y: 335,
          width: 0,
          height: 150,
          fill: "url(#capacity-question)",
        },
        "capacity.question",
        ctx,
      ),
      reserve = shape(
        group,
        "rect",
        { x: 760, y: 335, width: 0, height: 150, fill: "url(#reserve-hatch)" },
        "capacity.reserve",
        ctx,
      );
    shape(layer, "rect", {
      x: 160,
      y: 335,
      width: 1200,
      height: 150,
      rx: 30,
      fill: "url(#capacity-glass)",
      stroke: "#c7d7ef",
      "stroke-width": 3,
    });
    shape(layer, "ellipse", {
      cx: 160,
      cy: 410,
      rx: 23,
      ry: 76,
      fill: "#ffffff40",
      stroke: "#c5d5eb",
      "stroke-width": 2,
    });
    shape(layer, "ellipse", {
      cx: 1360,
      cy: 410,
      rx: 23,
      ry: 76,
      fill: "#ffffff40",
      stroke: "#c5d5eb",
      "stroke-width": 2,
    });
    const legends = [
      ["历史 1,500", 160, 450],
      ["问题 500", 610, 150],
      ["预留输出 1,000", 785, 265],
      ["余量 1,000", 1080, 275],
    ].map(([tx, x, w], i) => {
      const e = node(
        ctx,
        "capacity.label." + i,
        [x, 388, w, 55],
        "text label",
        tx,
      );
      e.style.textAlign = "center";
      e.style.fontSize = i === 1 ? "24px" : "26px";
      return e;
    });
    const overflow = shape(
      layer,
      "rect",
      {
        x: 1060,
        y: 312,
        width: 0,
        height: 196,
        rx: 20,
        fill: "#ffebf0",
        stroke: "#f08ba0",
        "stroke-width": 3,
        "stroke-dasharray": "8 8",
      },
      "capacity.attempt",
      ctx,
    );
    const boundary = path(
      layer,
      "M 1360 306 V 515",
      "#e17791",
      4,
      "capacity.boundary",
      ctx,
    );
    const attempted = node(
      ctx,
      "capacity.attempt-label",
      [780, 530, 720, 60],
      "text label",
      "再加 1,500 → 总预算 4,500，超限",
    );
    attempted.style.color = "#d56c86";
    attempted.style.fontSize = "30px";
    const policies = [
      ["报错", "超限请求可能被拒绝", "coral"],
      ["截断", "按接口策略移除部分输入", "purple"],
      ["应用压缩", "由应用摘要整理历史", "blue"],
    ].map(([title, body, color], i) => {
      const panel = node(
        ctx,
        "policy." + i,
        [160 + i * 425, 642, 380, 125],
        "panel",
      );
      panel.style.background = ["#fff0f4", "#f3efff", "#eff5ff"][i];
      const h = node(
        ctx,
        "policy.title." + i,
        [188 + i * 425, 660, 335, 48],
        "text label",
        title,
      );
      const b = node(
        ctx,
        "policy.body." + i,
        [188 + i * 425, 717, 335, 40],
        "text small",
        body,
      );
      b.style.fontSize = "20px";
      return [panel, h, b];
    });
    const caption = baseCaption(ctx);
    painters.push((t) => {
      const h = phase(t, 800, 2400) * 1500,
        q = phase(t, 3300, 1700) * 500,
        o = phase(t, 6200, 2300) * 1000,
        a = phase(t, 11300, 2400) * 1500;
      history.setAttribute("width", (h / 4000) * 1200);
      question.setAttribute("width", (q / 4000) * 1200);
      reserve.setAttribute("width", (o / 4000) * 1200);
      meter.textContent = `${Math.round(h + q + o + a).toLocaleString("en-US")} / 4,000`;
      meter.style.color = a > 1000 ? "#d56c86" : "#465b73";
      legends.forEach((e, i) => reveal(e, t, [2100, 4200, 7100, 7900][i]));
      legends[3].textContent = a > 0 ? "新增 1,500" : "余量 1,000";
      overflow.setAttribute("width", (a / 4000) * 1200);
      opacity(overflow, phase(t, 11300));
      opacity(boundary, phase(t, 11300));
      reveal(attempted, t, 13900);
      policies.forEach((parts, i) =>
        parts.forEach((e) => reveal(e, t, 14100 + i * 400)),
      );
      caption.textContent = captionAt(3, t);
    });
  }
  function takeaways() {
    const ctx = scene("takeaways");
    heading(ctx, data.sceneList[4].title, "一套单位，连接阅读、用量与上下文");
    image(ctx, "brain", [520, 255, 570, 430], "brain-v1.png");
    const layer = svg(ctx);
    const lines = [
      path(
        layer,
        "M 590 430 C 520 385 510 395 460 395",
        "#edb6c4",
        3,
        "relation.unit",
        ctx,
      ),
      path(
        layer,
        "M 1000 430 C 1040 380 1090 395 1120 395",
        "#acc2eb",
        3,
        "relation.usage",
        ctx,
      ),
      path(
        layer,
        "M 800 600 C 800 640 800 650 800 683",
        "#c2b4e5",
        3,
        "relation.window",
        ctx,
      ),
    ];
    const lengths = lines.map((e) => e.getTotalLength());
    lines.forEach((e, i) => (e.style.strokeDasharray = lengths[i]));
    const left = [
      node(
        ctx,
        "unit.title",
        [115, 325, 430, 70],
        "text title accent",
        "文本单元",
      ),
      node(
        ctx,
        "unit.body",
        [119, 417, 410, 100],
        "text body",
        "不等于一个字或一个词",
      ),
    ];
    left[0].style.fontSize = "48px";
    const right = [
      node(ctx, "usage.title", [1120, 325, 385, 70], "text title", "用量计量"),
      node(
        ctx,
        "usage.body",
        [1124, 417, 380, 100],
        "text body",
        "输入、输出分别核对",
      ),
    ];
    right[0].style.fontSize = "48px";
    right[0].style.color = "#83a7e2";
    const bottom = [
      node(ctx, "window.title", [540, 685, 520, 70], "text title", "容量预算"),
      node(
        ctx,
        "window.body",
        [440, 754, 720, 60],
        "text body",
        "上下文不等于永久记忆",
      ),
    ];
    bottom[0].style.fontSize = "45px";
    bottom.forEach((e) => (e.style.textAlign = "center"));
    const caption = baseCaption(ctx);
    painters.push((t) => {
      [left, right, bottom].forEach((els, i) =>
        els.forEach((e) => reveal(e, t, [450, 4500, 9000][i])),
      );
      lines.forEach(
        (e, i) =>
          (e.style.strokeDashoffset =
            lengths[i] * (1 - phase(t, [450, 4500, 9000][i], 900))),
      );
      caption.textContent =
        t >= 12500
          ? "练习：固定分词器，比较文字、数字、emoji 与空格的 Token 数。"
          : captionAt(4, t);
    });
  }
  function captionAt(index, t) {
    const beats = data.sceneList[index].beats;
    const beat =
      beats.find((b) => t >= b.atMs && t < b.untilMs) ||
      beats[beats.length - 1];
    return beat.caption;
  }
  definition();
  splitting();
  billing();
  context();
  takeaways();
  const prefixes = [0];
  for (const s of data.sceneList)
    prefixes.push(prefixes[prefixes.length - 1] + s.durationMs);
  const total = prefixes[prefixes.length - 1];
  const chapters = document.querySelector("#chapters"),
    scrub = document.querySelector("#scrub"),
    clock = document.querySelector("#clock"),
    ref = document.querySelector("#reference"),
    mode = document.querySelector("#mode");
  const refs = [
    "01-definition",
    "02-splitting",
    "03-billing",
    "04-context",
    "05-takeaways",
  ];
  let current = 0,
    time = 0,
    playing = false,
    raf = 0,
    last = 0,
    ready = false,
    playLimit = total;
  const buttons = [];
  function resize() {
    stage.style.transform = `scale(${frame.clientWidth / 1600})`;
  }
  new ResizeObserver(resize).observe(frame);
  resize();
  function pause() {
    playing = false;
    cancelAnimationFrame(raf);
  }
  function locate(t) {
    if (!Number.isFinite(t) || t < 0 || t > total)
      throw new RangeError("Time outside course");
    let i = data.sceneList.length - 1;
    for (let j = 0; j < data.sceneList.length; j++)
      if (t < prefixes[j + 1]) {
        i = j;
        break;
      }
    return { index: i, local: t - prefixes[i] };
  }
  function renderAtCourse(t) {
    if (!ready) throw new Error("Resources not ready");
    const { index, local } = locate(t);
    current = index;
    time = t;
    scenes.forEach((s, i) => (s.hidden = i !== index));
    painters[index](local);
    buttons.forEach((b, i) =>
      b.setAttribute("aria-current", String(i === index)),
    );
    scrub.value = t;
    clock.textContent = `${(t / 1000).toFixed(1)} / ${(total / 1000).toFixed(0)} s`;
    ref.src = "designs/" + refs[index] + ".png";
    document.querySelector("#transcript").textContent = data.sceneList[
      index
    ].beats
      .map((b) => b.narration)
      .join("\n\n");
    return snapshot();
  }
  function snapshot() {
    const { local } = locate(time);
    return {
      scene: data.sceneList[current].id,
      timeMs: local,
      courseTimeMs: time,
      format: data.format,
      revision: data.revision,
    };
  }
  function tick(now) {
    if (!playing) return;
    // A frame timestamp may predate a click in the same rendering cycle.
    const next = Math.min(playLimit, time + Math.max(0, now - last));
    last = Math.max(last, now);
    try {
      renderAtCourse(next);
    } catch (error) {
      pause();
      document.querySelector("#status").textContent = "播放失败：" + error.message;
      return;
    }
    if (next >= playLimit) {
      pause();
      return;
    }
    raf = requestAnimationFrame(tick);
  }
  function play(all = false) {
    if (!ready) {
      document.querySelector("#status").textContent = "字体和资产尚未准备完成，请稍候。";
      return;
    }
    pause();
    mode.value = "actual";
    setMode();
    if (all) {
      renderAtCourse(0);
      playLimit = total;
    } else {
      const i = current;
      renderAtCourse(prefixes[i]);
      playLimit = prefixes[i + 1] - 1;
    }
    playing = true;
    last = performance.now();
    raf = requestAnimationFrame(tick);
  }
  function setMode() {
    pause();
    const design = mode.value === "design";
    stage.hidden = design;
    ref.hidden = !design;
    document.querySelector("#status").textContent = design
      ? "生图代表设计帧：其中的文字/数字仅为参考，实际HTML使用核对数据。"
      : "实际 HTML/SVG + 独立生图资产 · 可拖动时间，支持整段连续播放。";
  }
  for (let i = 0; i < data.sceneList.length; i++) {
    const b = document.createElement("button");
    b.textContent =
      String(i + 1).padStart(2, "0") +
      " " +
      ["处理链", "分词对照", "用量流", "容量预算", "总结"][i];
    b.disabled = true;
    b.onclick = () => {
      pause();
      mode.value = "actual";
      setMode();
      renderAtCourse(prefixes[i + 1] - 1);
    };
    chapters.append(b);
    buttons.push(b);
  }
  scrub.max = total;
  scrub.oninput = () => {
    pause();
    renderAtCourse(Number(scrub.value));
  };
  document.querySelector("#play").onclick = () => play(false);
  document.querySelector("#all").onclick = () => play(true);
  document.querySelector("#pause").onclick = pause;
  document.querySelector("#reset").onclick = () => {
    pause();
    renderAtCourse(prefixes[current]);
  };
  mode.onchange = setMode;
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
  });
  function geometry(id) {
    const el = registries[current].get(id);
    if (!el) throw new Error("Unknown object " + id);
    const a = el.getBoundingClientRect(),
      b = frame.getBoundingClientRect(),
      scale = b.width / 1600;
    return {
      id,
      scene: data.sceneList[current].id,
      rect: {
        x: (a.x - b.x) / scale,
        y: (a.y - b.y) / scale,
        width: a.width / scale,
        height: a.height / scale,
      },
      opacity: Number(getComputedStyle(el).opacity),
    };
  }
  window.visualV2 = {
    renderAtCourse,
    snapshot,
    geometry,
    pause,
    play,
    totalMs: total,
    get playing() {
      return playing;
    },
  };
  window.visualV2Ready = (async () => {
    await document.fonts.ready;
    await Promise.all(
      [...stage.querySelectorAll("img")].map((img) => img.decode()),
    );
    for (const img of stage.querySelectorAll("img"))
      if (!img.naturalWidth) throw new Error("Missing asset");
    const probe = document.createElement("canvas").getContext("2d");
    probe.font = "32px monospace";
    const baseline = probe.measureText("Wim012科学").width;
    probe.font = '32px "Microsoft YaHei", monospace';
    if (probe.measureText("Wim012科学").width === baseline)
      throw new Error("Microsoft YaHei not available");
    ready = true;
    document.querySelectorAll("#chapters button, #play, #all, #reset, #scrub, #mode")
      .forEach((control) => (control.disabled = false));
    setMode();
    renderAtCourse(prefixes[1] - 1);
    return snapshot();
  })();
  window.visualV2Ready.catch((e) => {
    document.querySelector("#status").textContent = "准备失败：" + e.message;
  });
})();
