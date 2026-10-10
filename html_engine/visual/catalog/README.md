# Offline visual reference catalog

This module is an offline, source-backed catalog and attachment packer. It does not change the shared V1 schema, compiler, renderer, player, registry, Agent contract, application entry point, or production prompt. It never calls an image or text model.

## Source and status model

The static reference inventory is generated from `html_engine/reference-library/standard-pages.json`, `standard/manifest.json`, `components.json`, `components-extensions.json`, `presentation-variants.json`, `effects.json`, `static-catalog.json`, and `palettes.json`. Every source page is checked against its manifest SHA-256 and PNG dimensions. IDs, versions, parameter notes, screenshot hashes, source hashes, status, and production gaps are written to `catalog.json`.

Counts are computed from these files on every build. The current checkout has 24 grayscale pages, 32 base/fixed-structure entries, 16 presentation variants, 28 static effects, 18 composition examples, and 5 font specimens. The fixed R/D examples count inside the 32-entry reference set, but remain fixed examples rather than arbitrary chart/graph engines.

Live runtime entries are enumerated separately from `html_engine/visual/schema.json`, its layout/template/theme directories, and `effects/registry.json`. At this baseline the source registers 11 node types, 8 effects, 6 layouts, 4 templates, and 4 themes. Runtime registration is recorded as such; it does not imply aesthetic approval or generic support for every input. Reference IDs only get candidate links and an explicit adapter gap. No adapter is asserted by this module.

`available` means that a source-backed reference or runtime definition is present. It does not mean user-approved. The two B pages remain separated: `sample:course-everyday` is `pending-review`; `sample:paper-plane` is an `experimental` E1 reuse/capacity demonstration. Neither is included in a standard request by default. Font specimens are queryable and visible on the fonts sheet, but are not recommended as production font packages: actual host font availability still applies, and current runtime themes use Microsoft YaHei on Windows.

## Default appearance

An omitted palette and style select `neutral-baseline` with a black, gray, and white descriptor derived for this user's explicit default. It contains no color palette screenshot. The existing `style-description.png` depicts a blue paper plane, so it is kept under the experimental style record `unified-light-3d` and is never attached by default. The three source palettes remain independent and require an explicit exploration/review selection.

The package keeps four things separate:

1. Exact task content and relationships in `content.json`.
2. Style and palette instructions in `visual-guidance.json`.
3. Only the selected classification PNGs, plus an explicitly selected palette/style reference if requested.
4. A machine-readable manifest with source paths, IDs, versions, reasons, hashes, attachment dimensions, and cache key.

Reference labels and sample text appear in the PNGs for visual explanation. The guidance explicitly forbids copying them; the package does not copy their example strings into `content.json`.

## Build and query

Run these commands from the repository root:

```powershell
node html_engine/tools/catalog-build.cjs
node html_engine/tools/catalog-build.cjs --check
node html_engine/tools/catalog-query.cjs --id T01
node html_engine/tools/catalog-query.cjs --query "循环"
node html_engine/tools/catalog-query.cjs --task "水的状态变化过程与相反方向"
```

`--task` uses local keyword rules to suggest up to three pages. It is a small deterministic helper, not semantic AI. The assembler accepts explicit `referenceIds`, explicit `referencePages`, or those task suggestions. If there is no match, it asks for IDs rather than sending the full library. The query output exposes current versions, attachment hashes, production registration data, and explicit gaps.

## Assemble a package

The request shape is `task`, `content.title`, `content.exactText[]`, optional `content.relationships[]` (`from`, `to`, `relation`), and either `referenceIds[]` or `referencePages[]`. See [water-cycle-request.json](examples/water-cycle-request.json). Assemble it with:

```powershell
node html_engine/tools/catalog-assemble.cjs `
  --input html_engine/visual/catalog/examples/water-cycle-request.json `
  --out html_engine/visual/catalog/examples/water-cycle-package
```

For a production-facing default, omit `paletteId` and `styleId`. Use a named color palette only in `mode: "exploration"` or `mode: "review"`. B samples require an explicit matching palette. Pending samples require review mode; experiments require exploration mode; both require `allowUnreviewedReferences: true`. Requesting a runtime ID as a reference attachment, an unknown ID, unknown palette/style, missing or hash-mismatched source image, or an ineligible sample fails with a stable error code.

Each output directory holds one package. Repeating the same request verifies package file hashes and returns `cache-hit`. A different request should use a new output directory; to replace a complete, unmodified package previously written by this tool, pass `--replace`. It refuses to replace unknown directories or packages whose files no longer match their manifest. Cache identity includes only selected item record/version hashes, selected screenshot hashes, exact content, selected palette/style, mode, and reasons. It excludes the whole catalog snapshot, so unrelated page, palette, or sample changes do not evict a package. A change to a selected page image changes the key for packages that attach that page.

## Integration boundary

The actual request package is readable and hash-verified, but it is not sent to E or another provider. A provider adapter needs an explicit provider/model/version, endpoint and credential source, image-count/format/size constraints, detail/resolution selection, timeout/retry/cost limits, retention behavior, and safe call-ID logging. Verification must capture the redacted outbound request and exact attachment hashes, confirm a real provider response, decode/hash returned imagery, and record provider call/billing IDs without storing secrets. A mock or this offline package cannot prove that E integration is complete.

The corresponding cross-module integration proposal is in `docs/plans/workflow-first-parallel-2026-10-09/deliveries/D.md`; shared runtime registration and application wiring remain with A.
