(function () {
  "use strict";

  const paletteSource = JSON.parse(
    document.getElementById("sample-palette-data").textContent,
  );
  const palettes = new Map(paletteSource.palettes.map((p) => [p.id, p]));
  const pages = [...document.querySelectorAll(".sample-slide")];
  const paletteSelect = document.getElementById("palette-select");

  function applyPalette(slide, paletteId) {
    const palette = palettes.get(paletteId);
    if (!palette) throw new Error("UNKNOWN_SAMPLE_PALETTE");
    slide.dataset.palette = paletteId;
    for (const [key, value] of Object.entries({
      "--ink": palette.ink,
      "--muted": palette.muted,
      "--palette-background": palette.background,
      "--accent": palette.primary,
      "--secondary": palette.secondary,
      "--warm": palette.accent,
      "--category": palette.category,
      "--tint": palette.tints[0],
      "--secondary-tint": palette.tints[1],
      "--warm-tint": palette.tints[2],
      "--category-tint": palette.tints[3],
    }))
      slide.style.setProperty(key, value);
  }

  function setActivePage(pageId) {
    const page = pages.find((candidate) => candidate.dataset.pageId === pageId);
    if (!page) throw new Error("UNKNOWN_SAMPLE_PAGE");
    for (const candidate of pages) candidate.hidden = candidate !== page;
    for (const button of document.querySelectorAll("[data-page-target]"))
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.pageTarget === pageId),
      );
  }

  const initialPalette = paletteSelect.value;
  for (const page of pages) applyPalette(page, initialPalette);

  paletteSelect.addEventListener("change", () => {
    for (const page of pages) applyPalette(page, paletteSelect.value);
  });

  for (const button of document.querySelectorAll("[data-page-target]"))
    button.addEventListener("click", () =>
      setActivePage(button.dataset.pageTarget),
    );

  window.ReferenceSample = {
    paletteSource,
    setActivePage,
    setPalette(paletteId) {
      if (!palettes.has(paletteId)) throw new Error("UNKNOWN_SAMPLE_PALETTE");
      paletteSelect.value = paletteId;
      paletteSelect.dispatchEvent(new Event("change", { bubbles: true }));
    },
  };
})();
