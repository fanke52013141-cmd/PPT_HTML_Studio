(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const fixtures = window.HPSE1Fixtures;
  const controller = new window.HPSE1.SceneController(
    $("#frame"),
    fixtures.resources,
  );
  let timeMs = 0,
    playing = false,
    lastTick = 0,
    raf = 0,
    requestSequence = 0;
  for (let i = 0; i < fixtures.scenes.length; i++) {
    const option = document.createElement("option");
    option.value = i;
    option.textContent = fixtures.scenes[i].title;
    $("#scene").appendChild(option);
  }
  function status(text, error = false) {
    $("#status").textContent = text;
    $("#status").dataset.error = String(error);
  }
  function report(error) {
    const diagnostics = error.diagnostics || [
      { code: "INPUT_ERROR", message: error.message },
    ];
    status(
      diagnostics
        .map((d) => `${d.code} ${d.nodeId || ""}: ${d.message}`)
        .join("\n"),
      true,
    );
    $("#result").textContent = JSON.stringify(diagnostics, null, 2);
  }
  function pause() {
    playing = false;
    cancelAnimationFrame(raf);
    $("#play").textContent = "播放";
  }
  function renderClock() {
    $("#scrub").value = timeMs;
    $("#clock").textContent =
      `${(timeMs / 1000).toFixed(2)} / ${(controller.durationMs / 1000).toFixed(2)} 秒`;
  }
  function seek(t) {
    const state = controller.renderAt(t);
    pause();
    timeMs = t;
    renderClock();
    return state;
  }
  function tick(now) {
    if (!playing) return;
    timeMs = Math.max(
      0,
      Math.min(
        controller.durationMs,
        timeMs + (now - lastTick) * Number($("#direction").value),
      ),
    );
    lastTick = now;
    controller.renderAt(timeMs);
    renderClock();
    if (timeMs === 0 || timeMs === controller.durationMs) {
      pause();
      return;
    }
    raf = requestAnimationFrame(tick);
  }
  function play() {
    if (!controller.current) return;
    if (Number($("#direction").value) === 1 && timeMs === controller.durationMs)
      timeMs = 0;
    if (Number($("#direction").value) === -1 && timeMs === 0)
      timeMs = controller.durationMs;
    playing = true;
    lastTick = performance.now();
    $("#play").textContent = "暂停";
    raf = requestAnimationFrame(tick);
  }
  async function applyInput(input) {
    const request = ++requestSequence;
    pause();
    status("正在校验输入与准备素材…");
    try {
      const snapshot = await controller.load(input);
      if (request !== requestSequence) return snapshot;
      timeMs = 0;
      $("#scrub").max = controller.durationMs;
      $("#editor").value = JSON.stringify(snapshot.source, null, 2);
      $("#keyframes").replaceChildren();
      for (const frame of snapshot.source.keyframes) {
        const button = document.createElement("button");
        button.textContent = `${(frame.tMs / 1000).toFixed(1)} 秒`;
        button.title = frame.purpose;
        button.dataset.time = frame.tMs;
        button.onclick = () => seek(frame.tMs);
        $("#keyframes").appendChild(button);
      }
      $("#target").replaceChildren();
      for (const node of snapshot.source.nodes) {
        const option = document.createElement("option");
        option.value = node.id;
        option.textContent = node.id;
        $("#target").appendChild(option);
      }
      $("#play").disabled = false;
      $("#restart").disabled = false;
      seek(0);
      status(
        `已就绪 · ${snapshot.source.title} · 修订 ${snapshot.source.revision} · ${snapshot.source.nodes.length} 个对象`,
      );
      $("#result").textContent = "";
      return snapshot;
    } catch (error) {
      if (request === requestSequence) report(error);
      throw error;
    }
  }
  const loadScene = (index) =>
    applyInput(structuredClone(fixtures.scenes[index]));
  $("#scene").onchange = () => {
    loadScene(Number($("#scene").value)).catch(() => {});
  };
  $("#play").onclick = () => (playing ? pause() : play());
  $("#restart").onclick = () => {
    seek(0);
    play();
  };
  $("#scrub").oninput = (event) => seek(Number(event.target.value));
  $("#apply").onclick = () => {
    try {
      if ($("#editor").value.length > 524288)
        throw new Error("场景输入超过 512 KiB");
      const input = JSON.parse($("#editor").value);
      if (
        controller.current &&
        input.id === controller.current.compiled.source.id &&
        Number.isSafeInteger(input.revision)
      )
        input.revision = Math.max(
          input.revision,
          controller.current.compiled.source.revision + 1,
        );
      applyInput(input).catch(() => {});
    } catch (error) {
      report(error);
    }
  };
  $("#file").onchange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      if (file.size > 524288) throw new Error("场景文件超过 512 KiB");
      const input = JSON.parse(await file.text());
      await applyInput(input);
    } catch (error) {
      report(error);
    }
    event.target.value = "";
  };
  $("#download").onclick = () => {
    if (!controller.current) return;
    const source = controller.getSnapshot().source,
      url = URL.createObjectURL(
        new Blob([JSON.stringify(source, null, 2)], {
          type: "application/json",
        }),
      );
    const link = document.createElement("a");
    link.href = url;
    link.download = source.id + ".scene.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  $("#snapshot").onclick = () => {
    if (controller.current)
      $("#result").textContent = JSON.stringify(
        controller.getSnapshot(),
        null,
        2,
      );
  };
  $("#geometry").onclick = () => {
    if (controller.current)
      $("#result").textContent = JSON.stringify(
        controller.getGeometry(
          { nodeId: $("#target").value, part: "self" },
          timeMs,
        ),
        null,
        2,
      );
  };
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
  });
  window.e1 = {
    controller,
    applyInput,
    loadScene,
    seek,
    play,
    pause,
    get timeMs() {
      return timeMs;
    },
    get playing() {
      return playing;
    },
  };
  window.e1Ready = loadScene(0);
  // Error reporting is already done by applyInput; the original readiness promise stays rejecting.
  window.e1Ready.catch(() => {});
})();
