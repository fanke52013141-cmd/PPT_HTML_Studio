const fs = require("node:fs");
const path = require("node:path");
const {
  CatalogError,
  DOC_ASSET_PATH,
  buildCatalog,
  safeResolve,
  sha256,
} = require("./catalog-lib.cjs");

const ROOT = path.resolve(__dirname, "../..");
const CATALOG_PATH = "html_engine/visual/catalog/catalog.json";

function makeArtifacts(root = ROOT) {
  const { catalog } = buildCatalog({ root });
  const outputFiles = [];
  const addCopy = (sourcePath, destination, role, status = "available") => {
    const bytes = fs.readFileSync(safeResolve(root, sourcePath));
    outputFiles.push({
      path: destination,
      sourcePath,
      role,
      status,
      sha256: sha256(bytes),
      bytes,
    });
  };

  for (const page of catalog.referencePages)
    addCopy(page.screenshot.path, `assets/standard-pages/${path.basename(page.screenshot.path)}`, "classification-page");
  for (const palette of catalog.palettes)
    addCopy(palette.screenshot.path, `assets/palettes/palette-${palette.id}.png`, "palette-reference");
  const sourceStyle = catalog.styles.find((item) => item.id === "unified-light-3d");
  addCopy(sourceStyle.screenshot.path, "assets/style-experiments/style-description.png", "experimental-style", "experimental");
  addCopy(sourceStyle.source.path, "assets/style-experiments/style-description.json", "experimental-style-description", "experimental");
  const neutralStyle = catalog.styles.find((item) => item.id === "neutral-baseline");
  addCopy(neutralStyle.source.path, "assets/styles/neutral-style.json", "default-style-description");
  addCopy("html_engine/visual/catalog/historical-issues.json", "assets/historical-issues.json", "historical-issue-register");
  for (const sample of catalog.samplePages) {
    const sampleStatus = sample.status;
    for (const shot of sample.screenshots)
      addCopy(shot.path, `assets/samples/${path.basename(shot.path)}`, "sample-page", sampleStatus);
  }

  const catalogBytes = Buffer.from(`${JSON.stringify(catalog, null, 2)}\n`, "utf8");
  outputFiles.push({
    path: "catalog.json",
    sourcePath: CATALOG_PATH,
    role: "machine-catalog",
    status: "available",
    sha256: sha256(catalogBytes),
    bytes: catalogBytes,
  });
  const counts = catalog.taxonomy.counts;
  const pageLinks = catalog.referencePages
    .map((page) => `| ${page.id} | ${page.name} | ${page.referenceIds.length} | [PNG](assets/standard-pages/${path.basename(page.screenshot.path)}) | ${page.screenshot.sha256} |`)
    .join("\n");
  const paletteLinks = catalog.palettes
    .map((palette) => `| ${palette.id} | ${palette.name} | [PNG](assets/palettes/palette-${palette.id}.png) | ${palette.status} |`)
    .join("\n");
  const sampleLinks = catalog.samplePages
    .map((sample) => `| ${sample.id} | ${sample.name} | ${sample.status} | ${sample.screenshots.map((shot) => `[${shot.paletteId}](assets/samples/${path.basename(shot.path)})`).join(" · ")} |`)
    .join("\n");
  const historyRows = catalog.historicalIssues
    .map((item) => `| ${item.id} | ${item.status} | ${item.currentObservation} |`)
    .join("\n");
  const indexText = `# Code art reference catalog 1.0\n\nThis catalog is generated from the current source manifests. The standard pages are static visual references. They are not production templates or runtime capabilities. User aesthetic approval remains pending where the source records say so.\n\n## Counted from source\n\n- ${counts.referencePages} static PNG pages at 1920×1080\n- ${counts.baseComponents} base and fixed-structure component references, ${counts.presentationVariants} presentation variants, ${counts.staticEffects} static effects, ${counts.compositions} composition examples, ${counts.fonts} font specimens\n- Runtime registration is inventoried separately: ${counts.runtimeNodeTypes} node types, ${counts.runtimeEffects} effects, ${counts.runtimeLayouts} layouts, ${counts.runtimeTemplates} templates, ${counts.runtimeThemes} themes. Registration does not imply visual approval.\n- ${counts.pendingOrExperimentalSamples} B sample pages are marked pending or experimental; neither is a default recommendation.\n\n## Standard grayscale pages\n\n| Page | Topic | IDs | Attachment | Source image SHA-256 |\n|---|---|---:|---|---|\n${pageLinks}\n\n## Independent palettes\n\nNo palette is selected by default. The assembler uses the user-specified black, gray, and white baseline unless an explicit palette is chosen for exploration/review.\n\n| ID | Name | Reference | Status |\n|---|---|---|---|\n${paletteLinks}\n\n## Samples kept outside the default set\n\n| ID | Page | Status | Palette screenshot |\n|---|---|---|---|\n${sampleLinks}\n\n## Historical issues (separate from current capability)\n\n| Record | Status | Evidence summary |\n|---|---|---|\n${historyRows}\n\nSee [historical-issues.json](assets/historical-issues.json) for current source hashes. The F01 gradient note has no recoverable original file pointer in the current handoff; current F01 is a font specimen and E01–E04 are gradient references. The paper-plane title wrap was fixed in that sample only.\n\n## Runtime registration and source lineage\n\nSee [catalog.json](catalog.json) for IDs, versions, parameter bounds, status, screenshot/source hashes, candidate mappings, and explicit gaps. The [neutral style descriptor](assets/styles/neutral-style.json) is the default. The source [light 3D style description](assets/style-experiments/style-description.json) and its blue illustration are exploratory and are not attached by default.\n\nThe source image files are byte copies; their hashes are listed in [manifest.json](manifest.json). The catalog assembler is offline-only and does not call an image provider.\n`;
  const indexBytes = Buffer.from(indexText, "utf8");
  outputFiles.push({
    path: "README.md",
    sourcePath: CATALOG_PATH,
    role: "human-index",
    status: "available",
    sha256: sha256(indexBytes),
    bytes: indexBytes,
  });
  const manifest = {
    format: "hps.visual.reference-catalog-assets",
    version: "1.0.0",
    catalogVersion: catalog.version,
    catalogSnapshotSha256: catalog.snapshotSha256,
    source: "generated from current source files; copied PNGs are unmodified",
    files: outputFiles
      .map(({ path: relative, sourcePath, role, status, sha256: digest, bytes }) => ({
        path: relative,
        sourcePath,
        role,
        status,
        sha256: digest,
        size: bytes.length,
      }))
      .sort((a, b) => a.path.localeCompare(b.path)),
  };
  const manifestBytes = Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  return {
    catalogBytes,
    catalogPath: CATALOG_PATH,
    outputFiles,
    manifestBytes,
    manifestPath: `${DOC_ASSET_PATH}/manifest.json`,
    docsRoot: DOC_ASSET_PATH,
    catalog,
  };
}

function writeArtifacts(artifacts, root = ROOT) {
  for (const file of artifacts.outputFiles) {
    const destination = safeResolve(root, `${artifacts.docsRoot}/${file.path}`);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, file.bytes);
  }
  const manifestDestination = safeResolve(root, artifacts.manifestPath);
  fs.mkdirSync(path.dirname(manifestDestination), { recursive: true });
  fs.writeFileSync(manifestDestination, artifacts.manifestBytes);
  const catalogDestination = safeResolve(root, artifacts.catalogPath);
  fs.mkdirSync(path.dirname(catalogDestination), { recursive: true });
  fs.writeFileSync(catalogDestination, artifacts.catalogBytes);
}

function checkArtifacts(artifacts, root = ROOT) {
  const expected = [
    { path: artifacts.catalogPath, bytes: artifacts.catalogBytes },
    ...artifacts.outputFiles.map((file) => ({ path: `${artifacts.docsRoot}/${file.path}`, bytes: file.bytes })),
    { path: artifacts.manifestPath, bytes: artifacts.manifestBytes },
  ];
  const stale = [];
  for (const item of expected) {
    const target = safeResolve(root, item.path);
    if (!fs.existsSync(target) || sha256(fs.readFileSync(target)) !== sha256(item.bytes))
      stale.push(item.path);
  }
  if (stale.length) throw new CatalogError("CATALOG_ARTIFACTS_STALE", stale.join(", "));
  return { checkedFiles: expected.length, status: "current" };
}

function main() {
  const check = process.argv.includes("--check");
  const artifacts = makeArtifacts();
  const result = check ? checkArtifacts(artifacts) : (writeArtifacts(artifacts), { checkedFiles: artifacts.outputFiles.length + 2, status: "built" });
  console.log(JSON.stringify({ ...result, catalogSnapshotSha256: artifacts.catalog.snapshotSha256, counts: artifacts.catalog.taxonomy.counts }, null, 2));
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(JSON.stringify({ error: error.code || "BUILD_FAILED", detail: error.message }, null, 2));
    process.exitCode = 1;
  }
}

module.exports = { checkArtifacts, makeArtifacts, writeArtifacts };
