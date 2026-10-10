const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const {
  CatalogError,
  assembleRequest,
  buildCatalog,
  cacheIdentity,
  sha256,
  stableHash,
  suggestReferencePages,
  verifiedPng,
} = require("../tools/catalog-lib.cjs");
const { checkArtifacts, makeArtifacts } = require("../tools/catalog-build.cjs");

const ROOT = path.resolve(__dirname, "../..");
const EXAMPLE = path.join(ROOT, "html_engine/visual/catalog/examples/water-cycle-request.json");

function readExample() {
  return JSON.parse(fs.readFileSync(EXAMPLE, "utf8"));
}

function withTemp(callback) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "hps-catalog-test-"));
  try {
    return callback(directory);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

function assertCode(code, action) {
  assert.throws(action, (error) => error instanceof CatalogError && error.code === code);
}

test("catalog is source-backed and keeps reference counts separate from runtime registrations", () => {
  const { catalog } = buildCatalog({ root: ROOT });
  assert.deepEqual(catalog.taxonomy.counts, {
    referencePages: 24,
    baseComponents: 32,
    presentationVariants: 16,
    staticEffects: 28,
    compositions: 18,
    fonts: 5,
    palettes: 3,
    pendingOrExperimentalSamples: 2,
    runtimeNodeTypes: 11,
    runtimeEffects: 8,
    runtimeLayouts: 6,
    runtimeTemplates: 4,
    runtimeThemes: 4,
  });
  assert.equal(catalog.references.length, 99);
  assert.equal(catalog.styles.find((item) => item.default).id, "neutral-baseline");
  assert.equal(catalog.styles.find((item) => item.id === "unified-light-3d").status, "experimental");
  assert.equal(catalog.samplePages.find((item) => item.id === "sample:course-everyday").status, "pending-review");
  assert.equal(catalog.samplePages.find((item) => item.id === "sample:paper-plane").status, "experimental");
  const allEntries = [
    ...catalog.referencePages,
    ...catalog.references,
    ...catalog.palettes,
    ...catalog.styles,
    ...catalog.samplePages,
    ...catalog.productionCapabilities,
  ];
  for (const entry of allEntries) {
    assert.ok(entry.version, `${entry.id} missing version`);
    assert.ok(entry.type, `${entry.id} missing type`);
    assert.ok(entry.status, `${entry.id} missing availability status`);
    assert.ok(entry.parameterRange, `${entry.id} missing parameter range`);
    assert.ok(entry.productionMapping?.gap, `${entry.id} missing production mapping/gap`);
    assert.ok(entry.source?.recordSha256, `${entry.id} missing source hash`);
    if (entry.referenceAttachmentEligible) assert.ok(entry.screenshot || entry.screenshots?.length, `${entry.id} missing reference image`);
  }
  for (const entry of catalog.references) {
    assert.ok(entry.version);
    assert.ok(entry.type);
    assert.ok(entry.parameterRange);
    assert.ok(entry.screenshot.sha256);
    assert.ok(entry.source.recordSha256);
    assert.ok(entry.productionMapping.gap);
    assert.equal(entry.productionMapping.directAdapter, false);
    for (const forbidden of ["text", "value", "html", "css", "example"])
      assert.equal(Object.hasOwn(entry, forbidden), false, `${entry.id} leaked example field ${forbidden}`);
  }
  assert.ok(catalog.productionCapabilities.some((item) => item.id === "runtime-node:text"));
  assert.ok(catalog.productionCapabilities.some((item) => item.id === "runtime-effect:soft-shadow"));
  assert.ok(catalog.productionCapabilities.every((item) => item.referenceAttachmentEligible === false));
  assert.equal(catalog.historicalIssues.find((item) => item.id === "HIST-F01-GRADIENT-MISREFERENCE").status, "not-reproduced-from-current-source");
  assert.equal(catalog.historicalIssues.find((item) => item.id === "HIST-PAPER-PLANE-TITLE-WRAP").status, "fixed-in-current-sample-only");
  assert.ok(catalog.samplePages.find((item) => item.id === "sample:paper-plane").sampleMetrics.titleCharacters > 0);
});

test("build output and documentation asset package are current and hash-consistent", () => {
  const artifacts = makeArtifacts(ROOT);
  const result = checkArtifacts(artifacts, ROOT);
  assert.equal(result.status, "current");
  const manifest = JSON.parse(
    fs.readFileSync(path.join(ROOT, "docs/assets/code-art-references/catalog-v1/manifest.json"), "utf8"),
  );
  assert.equal(manifest.files.length, artifacts.outputFiles.length);
  for (const file of manifest.files) {
    const bytes = fs.readFileSync(path.join(ROOT, "docs/assets/code-art-references/catalog-v1", file.path));
    assert.equal(sha256(bytes), file.sha256, file.path);
  }
});

test("default assembly includes only selected grayscale page attachments and exact content", () => {
  const request = readExample();
  withTemp((temporary) => {
    const output = path.join(temporary, "package");
    const result = assembleRequest({ request, root: ROOT, outDir: output });
    assert.equal(result.status, "assembled");
    const manifest = JSON.parse(fs.readFileSync(path.join(output, "manifest.json"), "utf8"));
    const exactContent = JSON.parse(fs.readFileSync(path.join(output, "content.json"), "utf8"));
    const guidance = JSON.parse(fs.readFileSync(path.join(output, "visual-guidance.json"), "utf8"));
    assert.deepEqual(exactContent, request.content);
    assert.equal(manifest.palette.id, "neutral");
    assert.equal(manifest.style.id, "neutral-baseline");
    assert.equal(manifest.attachments.length, 4);
    assert.ok(manifest.attachments.every((item) => item.role === "classification"));
    assert.equal(manifest.attachments.some((item) => item.role === "palette" || item.role === "style"), false);
    assert.equal(guidance.palette.id, "neutral");
    assert.match(guidance.style.style, /纯白背景/);
    assert.match(guidance.style.style, /灰阶/);
    assert.equal(guidance.referenceHandling.doNotCopySampleTextOrNumbers, true);
    assert.equal(manifest.provider.requestCreated, false);
    assert.equal(manifest.provider.callMade, false);
    assert.equal(manifest.selectedReferences.length, 5);
    assert.equal(manifest.attachments.filter((item) => item.role === "classification").length, 4);
    for (const file of manifest.files) {
      const bytes = fs.readFileSync(path.join(output, file.path));
      assert.equal(sha256(bytes), file.sha256, file.path);
    }
    for (const item of manifest.attachments) {
      const bytes = fs.readFileSync(path.join(output, item.path));
      assert.equal(sha256(bytes), item.sha256, item.path);
      assert.equal(bytes.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
    }
    assert.equal(assembleRequest({ request, root: ROOT, outDir: output }).status, "cache-hit");
    const changedRequest = {
      ...request,
      content: { ...request.content, exactText: [...request.content.exactText, "新增的准确说明。"] },
    };
    assertCode("OUTPUT_DIRECTORY_NOT_EMPTY_OR_NOT_OWNED", () =>
      assembleRequest({ request: changedRequest, root: ROOT, outDir: output }),
    );
    assert.equal(
      assembleRequest({ request: changedRequest, root: ROOT, outDir: output, replaceExisting: true }).status,
      "assembled",
    );
    const replacedContent = JSON.parse(fs.readFileSync(path.join(output, "content.json"), "utf8"));
    assert.deepEqual(replacedContent, changedRequest.content);
  });
});

test("task-only assembly suggests relevant pages without attaching the full library", () => {
  const request = readExample();
  delete request.referenceIds;
  delete request.selectionReasons;
  withTemp((temporary) => {
    const output = path.join(temporary, "task-package");
    const result = assembleRequest({ request, root: ROOT, outDir: output });
    const manifest = JSON.parse(fs.readFileSync(path.join(output, "manifest.json"), "utf8"));
    assert.equal(result.status, "assembled");
    assert.deepEqual(
      manifest.attachments.map((item) => path.basename(item.sourcePath)).sort(),
      ["component-02.png", "component-03.png", "component-06.png"],
    );
    assert.ok(manifest.selectedReferences.every((item) => item.rationale.includes("关键词规则")));
  });
  assert.deepEqual(
    suggestReferencePages(request.task, buildCatalog({ root: ROOT }).catalog.referencePages),
    ["component-02", "component-03", "component-06"],
  );
});

test("explicit palette selection attaches a separate palette image and changes cache identity", () => {
  const request = readExample();
  const neutralRequest = { ...request };
  const colorRequest = { ...request, mode: "exploration", paletteId: "science" };
  withTemp((temporary) => {
    const neutralOut = path.join(temporary, "neutral");
    const colorOut = path.join(temporary, "science");
    const neutral = assembleRequest({ request: neutralRequest, root: ROOT, outDir: neutralOut });
    const color = assembleRequest({ request: colorRequest, root: ROOT, outDir: colorOut });
    assert.notEqual(neutral.cacheKey, color.cacheKey);
    const manifest = JSON.parse(fs.readFileSync(path.join(colorOut, "manifest.json"), "utf8"));
    assert.equal(manifest.palette.id, "science");
    assert.equal(manifest.attachments.filter((item) => item.role === "palette").length, 1);
    assert.equal(manifest.attachments.filter((item) => item.role === "classification").length, 4);
    assert.equal(assembleRequest({ request: colorRequest, root: ROOT, outDir: colorOut }).status, "cache-hit");
  });
  assertCode("PALETTE_SELECTION_REQUIRES_EXPLORATION", () =>
    assembleRequest({ request: { ...request, paletteId: "science" }, root: ROOT, outDir: path.join(os.tmpdir(), "unused-catalog-output") }),
  );
});

test("unknown IDs, runtime-only IDs, and unapproved samples are rejected", () => {
  const request = readExample();
  assertCode("UNKNOWN_REFERENCE_ID", () =>
    assembleRequest({ request: { ...request, referenceIds: ["T999"] }, root: ROOT, outDir: path.join(os.tmpdir(), "unused-catalog-output") }),
  );
  assertCode("UNSUPPORTED_PRODUCTION_REFERENCE", () =>
    assembleRequest({ request: { ...request, referenceIds: ["runtime-node:text"] }, root: ROOT, outDir: path.join(os.tmpdir(), "unused-catalog-output") }),
  );
  assertCode("PENDING_REFERENCE_REQUIRES_REVIEW_MODE", () =>
    assembleRequest({ request: { ...request, referenceIds: ["sample:course-everyday"] }, root: ROOT, outDir: path.join(os.tmpdir(), "unused-catalog-output") }),
  );
  assertCode("SAMPLE_REQUIRES_EXPLICIT_PALETTE", () =>
    assembleRequest({ request: { ...request, mode: "review", allowUnreviewedReferences: true, referenceIds: ["sample:course-everyday"] }, root: ROOT, outDir: path.join(os.tmpdir(), "unused-catalog-output") }),
  );
  withTemp((temporary) => {
    const requestWithSample = {
      ...request,
      mode: "review",
      allowUnreviewedReferences: true,
      paletteId: "science",
      referenceIds: ["sample:course-everyday"],
    };
    const output = path.join(temporary, "review-package");
    assembleRequest({ request: requestWithSample, root: ROOT, outDir: output });
    const manifest = JSON.parse(fs.readFileSync(path.join(output, "manifest.json"), "utf8"));
    assert.equal(manifest.selectedReferences[0].status, "pending-review");
    assert.ok(manifest.attachments.some((item) => item.role === "samples"));
  });
});

test("cache identity refreshes on selected versions or images but ignores unselected catalog edits", () => {
  const { catalog } = buildCatalog({ root: ROOT });
  const ref = catalog.references.find((item) => item.id === "T01");
  const style = catalog.styles.find((item) => item.id === "neutral-baseline");
  const request = { task: "title", content: { title: "x", exactText: ["x"] }, mode: "standard" };
  const attachments = [{ packagePath: "attachments/classification/component-01.png", sha256: ref.screenshot.sha256 }];
  const selectedRefs = (sourceCatalog) => sourceCatalog.references.filter((item) => item.id === "T01");
  const key = (sourceCatalog = catalog) => cacheIdentity({ request, selectedReferences: selectedRefs(sourceCatalog), selectedPalette: null, selectedStyle: style, attachments });
  const baseline = key();
  const unrelatedCatalogEdit = { ...catalog, references: catalog.references.map((item) => item.id === "T05" ? { ...item, version: "999" } : item) };
  assert.ok(unrelatedCatalogEdit.references.some((item) => item.id === "T05" && item.version === "999"));
  assert.equal(key(unrelatedCatalogEdit), baseline);
  assert.notEqual(
    cacheIdentity({ request, selectedReferences: [{ ...ref, version: "1.1.0", source: { ...ref.source, recordSha256: stableHash({ refreshed: true }) } }], selectedPalette: null, selectedStyle: style, attachments }),
    baseline,
  );
  assert.notEqual(
    cacheIdentity({ request, selectedReferences: [{ ...ref, catalogVersion: "2.0.0" }], selectedPalette: null, selectedStyle: style, attachments }),
    baseline,
  );
  assert.notEqual(
    cacheIdentity({ request, selectedReferences: [ref], selectedPalette: null, selectedStyle: style, attachments: [{ ...attachments[0], sha256: "a".repeat(64) }] }),
    baseline,
  );
  const clear = catalog.palettes.find((item) => item.id === "clear");
  const clearAttachments = [
    ...attachments,
    { packagePath: "attachments/palettes/palette-clear.png", sha256: clear.screenshot.sha256 },
  ];
  const clearKey = cacheIdentity({ request, selectedReferences: [ref], selectedPalette: clear, selectedStyle: style, attachments: clearAttachments });
  const unrelatedPaletteEdit = catalog.palettes.find((item) => item.id === "science");
  const catalogAfterUnrelatedPaletteEdit = {
    ...catalog,
    palettes: catalog.palettes.map((item) =>
      item.id === "science"
        ? { ...item, source: { ...item.source, recordSha256: stableHash({ unrelated: true }) } }
        : item,
    ),
  };
  const clearAfterUnrelatedEdit = catalogAfterUnrelatedPaletteEdit.palettes.find((item) => item.id === "clear");
  assert.ok(unrelatedPaletteEdit);
  assert.equal(
    cacheIdentity({ request, selectedReferences: [ref], selectedPalette: clearAfterUnrelatedEdit, selectedStyle: style, attachments: clearAttachments }),
    clearKey,
  );
  assert.notEqual(
    cacheIdentity({ request, selectedReferences: [ref], selectedPalette: { ...clear, source: { ...clear.source, recordSha256: stableHash({ palette: "changed" }) } }, selectedStyle: style, attachments: clearAttachments }),
    clearKey,
  );
});

test("missing, malformed, and hash-mismatched images fail closed", () => {
  withTemp((temporary) => {
    assertCode("MISSING_SOURCE", () => verifiedPng(temporary, "missing.png"));
    const malformed = path.join(temporary, "bad.png");
    fs.writeFileSync(malformed, Buffer.from("not a png"));
    assertCode("INVALID_PNG_SOURCE", () => verifiedPng(temporary, "bad.png"));
    const source = path.join(temporary, "header.png");
    const bytes = Buffer.alloc(24);
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).copy(bytes, 0);
    bytes.write("IHDR", 12, "ascii");
    bytes.writeUInt32BE(1920, 16);
    bytes.writeUInt32BE(1080, 20);
    fs.writeFileSync(source, bytes);
    assertCode("SOURCE_IMAGE_MISMATCH", () => verifiedPng(temporary, "header.png", { sha256: "0".repeat(64) }));
    assertCode("SOURCE_PATH_ESCAPES_ROOT", () => verifiedPng(temporary, "../outside.png"));
  });
});
