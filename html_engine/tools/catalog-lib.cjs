const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const FORMAT_VERSION = "1.0.0";
const STANDARD_LIBRARY_PATH = "html_engine/reference-library";
const DOC_ASSET_PATH = "docs/assets/code-art-references/catalog-v1";
const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

class CatalogError extends Error {
  constructor(code, detail = "") {
    super(detail ? `${code}: ${detail}` : code);
    this.name = "CatalogError";
    this.code = code;
  }
}

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function stableHash(value) {
  return sha256(Buffer.from(stableStringify(value), "utf8"));
}

function safeResolve(root, relative) {
  if (typeof relative !== "string" || path.isAbsolute(relative))
    throw new CatalogError("INVALID_SOURCE_PATH", String(relative));
  const base = path.resolve(root);
  const target = path.resolve(base, relative);
  if (target !== base && !target.startsWith(`${base}${path.sep}`))
    throw new CatalogError("SOURCE_PATH_ESCAPES_ROOT", relative);
  return target;
}

function readBytes(root, relative) {
  const absolute = safeResolve(root, relative);
  if (!fs.existsSync(absolute))
    throw new CatalogError("MISSING_SOURCE", relative);
  return fs.readFileSync(absolute);
}

function readJson(root, relative) {
  try {
    return JSON.parse(readBytes(root, relative).toString("utf8"));
  } catch (error) {
    if (error instanceof CatalogError) throw error;
    throw new CatalogError("INVALID_SOURCE_JSON", `${relative}: ${error.message}`);
  }
}

function fileHash(root, relative) {
  return sha256(readBytes(root, relative));
}

function pngInfo(bytes, source) {
  if (
    bytes.length < 24 ||
    !bytes.subarray(0, 8).equals(PNG_SIGNATURE) ||
    bytes.toString("ascii", 12, 16) !== "IHDR"
  )
    throw new CatalogError("INVALID_PNG_SOURCE", source);
  const width = bytes.readUInt32BE(16);
  const height = bytes.readUInt32BE(20);
  if (!width || !height) throw new CatalogError("INVALID_PNG_DIMENSIONS", source);
  return { width, height };
}

function verifiedPng(root, relative, expected = {}) {
  const bytes = readBytes(root, relative);
  const dimensions = pngInfo(bytes, relative);
  if (
    (expected.sha256 && sha256(bytes) !== expected.sha256) ||
    (expected.width && dimensions.width !== expected.width) ||
    (expected.height && dimensions.height !== expected.height)
  )
    throw new CatalogError("SOURCE_IMAGE_MISMATCH", relative);
  return { sha256: sha256(bytes), ...dimensions, bytes };
}

function sourceRef(root, relative, record) {
  return {
    path: relative,
    fileSha256: fileHash(root, relative),
    recordSha256: stableHash(record),
  };
}

function safeSummary(item) {
  const allowed = [
    "id",
    "name",
    "kind",
    "category",
    "categoryNote",
    "purpose",
    "componentRef",
    "family",
    "use",
    "type",
  ];
  return Object.fromEntries(
    allowed.filter((key) => item[key] !== undefined).map((key) => [key, item[key]]),
  );
}

function mappingFor(id, mappings) {
  const rule = mappings.rules.find((item) => new RegExp(item.pattern).test(id));
  if (!rule) {
    return {
      status: "none",
      directAdapter: false,
      candidateRuntimeIds: [],
      gap: "没有可核实的生产映射；此参考 ID 不会转换为 scene、theme 或 template。",
    };
  }
  return {
    status: rule.candidateRuntimeIds.length ? "candidate-only" : "none",
    directAdapter: false,
    candidateRuntimeIds: rule.candidateRuntimeIds,
    gap: rule.gap,
  };
}

function referenceParameterRange(type, item) {
  if (type === "base-component") {
    return {
      interface: "ComponentAtlas reference renderer",
      maxTextCharacters: 36,
      values: "reference preview only; fit still depends on the rendered slot",
      topology: "not configurable from this reference entry",
    };
  }
  if (type === "presentation-variant") {
    return {
      interface: "static presentation variant",
      parentComponentId: item.componentRef,
      maxTextCharacters: 36,
      values: "appearance example only; not a production parameter",
    };
  }
  if (type === "fixed-structure-example") {
    return {
      interface: "fixed static example",
      values: "no arbitrary topology, data, scale, or timing input",
    };
  }
  if (type === "static-effect") {
    return {
      interface: "static visual effect sample",
      values: "no public production parameter range; see source record and screenshot",
    };
  }
  if (type === "composition-example") {
    return {
      interface: "fixed composition example",
      values: "example geometry only; no arbitrary content or production layout input",
    };
  }
  if (type === "font") {
    return {
      interface: "host font specimen",
      family: item.family,
      values: "fixed family; availability depends on host installation",
    };
  }
  return { interface: "reference image only", values: "not parameterized" };
}

function collectRuntimeNodes(root, schemaPath, schema) {
  const sourceHash = fileHash(root, schemaPath);
  const branches = schema.$defs?.node?.oneOf || [];
  return branches
    .map((branch) => {
      const nodeType = branch.properties?.type?.const;
      if (!nodeType) return null;
      const parameters = {};
      for (const [name, property] of Object.entries(branch.properties || {})) {
        if (["id", "slot", "type"].includes(name)) continue;
        parameters[name] = Object.fromEntries(
          [
            "const",
            "enum",
            "type",
            "minimum",
            "maximum",
            "minLength",
            "maxLength",
            "pattern",
            "$ref",
          ]
            .filter((key) => property[key] !== undefined)
            .map((key) => [key, property[key]]),
        );
      }
      return {
        id: `runtime-node:${nodeType}`,
        version: schema.$defs?.version?.const || "unknown",
        type: "runtime-node",
        category: "production-runtime",
        name: `运行时节点 ${nodeType}`,
        purpose: "当前 V1 scene schema 接受的节点类型。",
        parameterRange: {
          required: branch.required.filter((key) => !["id", "slot", "type"].includes(key)),
          schema: parameters,
        },
        status: "available",
        implementationStatus: "registered-runtime",
        approvalStatus: "not-inferred-from-registration",
        themeAllowance: {
          source: "schema-bound; requires a compatible registered theme and layout",
          colors: "semantic roles only; no arbitrary CSS or reference-image mapping",
        },
        technicalConclusion: "Registered in the current V1 node schema; the parameter schema is included verbatim as bounded summaries.",
        visualConclusion: "No user aesthetic approval is inferred from schema registration.",
        referenceAttachmentEligible: false,
        source: { path: schemaPath, fileSha256: sourceHash, recordSha256: stableHash(branch) },
        screenshot: null,
        productionMapping: {
          status: "registered",
          directAdapter: true,
          candidateRuntimeIds: [`runtime-node:${nodeType}`],
          gap: "该条目本身是运行时 schema 节点定义，不是标准库截图或生成能力保证。",
        },
      };
    })
    .filter(Boolean);
}

function collectRuntimeFiles(root, directory, type, category, parameterize) {
  const absolute = safeResolve(root, directory);
  const names = fs
    .readdirSync(absolute)
    .filter((name) => name.endsWith(".json"))
    .sort();
  return names.map((name) => {
    const relative = `${directory}/${name}`;
    const raw = readJson(root, relative);
    const id = raw.id || path.basename(name, ".json");
    const idPrefix = type === "runtime-layout" ? "runtime-layout" :
      type === "runtime-template" ? "runtime-template" : "runtime-theme";
    return {
      id: `${idPrefix}:${id}`,
      version: raw.version || "unknown",
      type,
      category,
      name: raw.name || id,
      purpose: `${category} 的实际运行时登记源。`,
      parameterRange: parameterize(raw),
      status: "available",
      implementationStatus: "registered-runtime",
      approvalStatus: "not-inferred-from-registration",
      themeAllowance: {
        source: "defined by this runtime record's compatible theme/layout references",
        colors: "no reference-library palette is implicitly converted into this runtime record",
      },
      technicalConclusion: "Definition is present in the current V1 runtime source directory; catalog does not render or execute it.",
      visualConclusion: "No user aesthetic approval is inferred from runtime registration.",
      referenceAttachmentEligible: false,
      source: sourceRef(root, relative, raw),
      screenshot: null,
      productionMapping: {
        status: "registered",
        directAdapter: true,
        candidateRuntimeIds: [`${idPrefix}:${id}`],
        gap: "该条目本身是生产运行时定义；注册状态不代表视觉批准或任意输入均被支持。",
      },
    };
  });
}

function buildCatalog({ root = path.resolve(__dirname, "../..") } = {}) {
  const lib = `${STANDARD_LIBRARY_PATH}/`;
  const sourcePaths = [
    `${lib}STANDARD-LIBRARY.md`,
    `${lib}standard-library.html`,
    `${lib}standard-pages.json`,
    `${lib}standard/manifest.json`,
    `${lib}standard/review.json`,
    `${lib}components.json`,
    `${lib}components-extensions.json`,
    `${lib}presentation-variants.json`,
    `${lib}effects.json`,
    `${lib}static-catalog.json`,
    `${lib}palettes.json`,
    `${lib}reference-input-v2/manifest.json`,
    `${lib}reference-input-v2/style-description.json`,
    `${lib}reference-input-v2/style-verification.json`,
    `${lib}samples/output/verification.json`,
    "html_engine/visual/schema.json",
    "html_engine/visual/effects/registry.json",
    "html_engine/visual/catalog/neutral-style.json",
    "html_engine/visual/catalog/production-mapping.json",
    "html_engine/visual/catalog/historical-issues.json",
  ];
  const standardPages = readJson(root, `${lib}standard-pages.json`);
  const standardManifest = readJson(root, `${lib}standard/manifest.json`);
  const review = readJson(root, `${lib}standard/review.json`);
  const components = readJson(root, `${lib}components.json`);
  const extensions = readJson(root, `${lib}components-extensions.json`);
  const variants = readJson(root, `${lib}presentation-variants.json`);
  const effects = readJson(root, `${lib}effects.json`);
  const compositions = readJson(root, `${lib}static-catalog.json`);
  const palettes = readJson(root, `${lib}palettes.json`);
  const referenceManifest = readJson(root, `${lib}reference-input-v2/manifest.json`);
  const sourceStyle = readJson(root, `${lib}reference-input-v2/style-description.json`);
  const sampleVerification = readJson(root, `${lib}samples/output/verification.json`);
  const neutralStyle = readJson(root, "html_engine/visual/catalog/neutral-style.json");
  const mappingRules = readJson(root, "html_engine/visual/catalog/production-mapping.json");
  const historicalSource = readJson(root, "html_engine/visual/catalog/historical-issues.json");
  const schemaPath = "html_engine/visual/schema.json";
  const runtimeSchema = readJson(root, schemaPath);

  const actualHtmlHash = fileHash(root, `${lib}standard-library.html`);
  if (standardManifest.sourceSha256 !== actualHtmlHash)
    throw new CatalogError("STANDARD_SOURCE_HASH_MISMATCH", "standard-library.html");
  if (standardPages.version !== standardManifest.version)
    throw new CatalogError("STANDARD_VERSION_MISMATCH");
  if (standardPages.pages.length !== standardManifest.files.length)
    throw new CatalogError("STANDARD_PAGE_COUNT_MISMATCH");
  if (!Array.isArray(standardPages.pages) || !Array.isArray(standardManifest.files))
    throw new CatalogError("INVALID_STANDARD_MANIFEST");

  const pages = [];
  const pageById = new Map();
  const pageByReferenceId = new Map();
  for (const page of standardPages.pages) {
    if (pageById.has(page.id)) throw new CatalogError("DUPLICATE_PAGE_ID", page.id);
    const manifestFile = standardManifest.files.find((item) => item.id === page.id);
    if (!manifestFile || stableStringify(page.ids) !== stableStringify(manifestFile.ids))
      throw new CatalogError("PAGE_MANIFEST_MAPPING_MISMATCH", page.id);
    const relative = `${lib}standard/${manifestFile.filename}`;
    const image = verifiedPng(root, relative, manifestFile);
    const pageEntry = {
      id: `page:${page.id}`,
      version: standardPages.version,
      type: "standard-reference-page",
      category: page.kind,
      name: page.title,
      purpose: page.note,
      parameterRange: { canvas: standardPages.canvas, values: "fixed monochrome reference page" },
      status: "available",
      implementationStatus: "static-reference-implemented",
      approvalStatus: review.userAestheticApproval || "unknown",
      themeAllowance: {
        palette: "black/gray/white pixels in the source PNG; optional palette is a separate visual input",
        production: "reference-only; no theme adapter or production template approval",
      },
      technicalConclusion: "PNG bytes, dimensions, manifest IDs, and source HTML hash match the current standard-library manifests.",
      visualConclusion: `Static agent review: ${review.agentStaticReview}; user aesthetic approval: ${review.userAestheticApproval}; not a production template approval.`,
      referenceAttachmentEligible: true,
      source: {
        path: `${lib}standard-pages.json`,
        fileSha256: fileHash(root, `${lib}standard-pages.json`),
        recordSha256: stableHash(page),
      },
      screenshot: {
        path: relative,
        sha256: image.sha256,
        width: image.width,
        height: image.height,
      },
      productionMapping: {
        status: "none",
        directAdapter: false,
        candidateRuntimeIds: [],
        gap: "分类参考图用于视觉对照；不对应生产 scene、layout 或 template 身份。",
      },
      referenceIds: page.ids,
    };
    pages.push(pageEntry);
    pageById.set(page.id, pageEntry);
    for (const id of page.ids) {
      const existing = pageByReferenceId.get(id) || [];
      existing.push(pageEntry);
      pageByReferenceId.set(id, existing);
    }
  }
  for (const [id, owningPages] of pageByReferenceId) {
    if (owningPages.length !== 1)
      throw new CatalogError("REFERENCE_PAGE_OWNERSHIP_INVALID", id);
  }

  const makeReference = (item, type, sourcePath, sourceVersion, extra = {}) => {
    const owners = pageByReferenceId.get(item.id) || [];
    if (owners.length !== 1)
      throw new CatalogError("REFERENCE_PAGE_MISSING", item.id);
    const page = owners[0];
    return {
      ...safeSummary(item),
      id: item.id,
      version: sourceVersion || standardPages.version,
      catalogVersion: standardPages.version,
      type,
      category: item.category || page.category,
      purpose: item.purpose || item.categoryNote || item.use || item.name,
      parameterRange: referenceParameterRange(type, item),
      status: "available",
      implementationStatus: "static-reference-implemented",
      approvalStatus: review.userAestheticApproval || "pending",
      themeAllowance: {
        palette: "neutral grayscale reference; explicit palette images remain independent inputs",
        production: "not registered as a production theme or component adapter",
      },
      technicalConclusion: "Reference screenshot and defining source record are hash-addressed; component query remains separate from production scene IDs.",
      visualConclusion: `Static agent review: ${review.agentStaticReview}; user aesthetic approval: ${review.userAestheticApproval}; not a production capability approval.`,
      referenceAttachmentEligible: true,
      screenshot: page.screenshot,
      pageId: page.id,
      source: sourceRef(root, sourcePath, item),
      productionMapping: mappingFor(item.id, mappingRules),
      tags: [item.id, item.name, item.category, item.purpose, item.categoryNote]
        .filter(Boolean)
        .join(" "),
      ...extra,
    };
  };

  const references = [];
  for (const font of components.fonts)
    references.push(
      makeReference(font, "font", `${lib}components.json`, components.version),
    );
  for (const item of components.items)
    references.push(
      makeReference(item, "base-component", `${lib}components.json`, components.version),
    );
  for (const item of extensions.items)
    references.push(
      makeReference(
        item,
        "fixed-structure-example",
        `${lib}components-extensions.json`,
        extensions.version,
      ),
    );
  for (const item of variants.items)
    references.push(
      makeReference(
        item,
        "presentation-variant",
        `${lib}presentation-variants.json`,
        variants.version,
      ),
    );
  for (const item of effects.items)
    references.push(
      makeReference(item, "static-effect", `${lib}effects.json`, effects.version),
    );
  for (const item of compositions.items)
    references.push(
      makeReference(item, "composition-example", `${lib}static-catalog.json`, compositions.version),
    );
  if (new Set(references.map((item) => item.id)).size !== references.length)
    throw new CatalogError("DUPLICATE_REFERENCE_ID");

  const paletteEntries = palettes.palettes.map((palette) => {
    const relative = `${lib}reference-input-v2/palette-${palette.id}.png`;
    const image = verifiedPng(root, relative);
    return {
      id: palette.id,
      version: palettes.version,
      type: "palette",
      name: palette.name,
      purpose: "独立的多角色配色参考；不替换中性标准组件结构。",
      parameterRange: { roles: Object.fromEntries(Object.entries(palette).filter(([key]) => !["id", "name"].includes(key))) },
      status: "available",
      implementationStatus: "palette-reference-only",
      approvalStatus: "reference-only; not a production theme approval",
      themeAllowance: { roleValues: "independent palette roles; only attach when explicitly selected" },
      technicalConclusion: "Palette roles and screenshot are read from the palette source and reference-input asset.",
      visualConclusion: "Reference palette only; not a production theme or user-approved production style.",
      productionMapping: {
        status: "candidate-only",
        directAdapter: false,
        candidateRuntimeIds: [],
        gap: "Palettes.json is not the V1 theme schema; no role-name adapter or theme visual approval is asserted.",
      },
      default: false,
      roles: Object.fromEntries(
        ["ink", "muted", "background", "primary", "secondary", "accent", "category", "tints"]
          .filter((key) => palette[key] !== undefined)
          .map((key) => [key, palette[key]]),
      ),
      source: sourceRef(root, `${lib}palettes.json`, palette),
      screenshot: {
        path: relative,
        sha256: image.sha256,
        width: image.width,
        height: image.height,
      },
    };
  });

  const styleImagePath = `${lib}reference-input-v2/style-description.png`;
  const styleImage = verifiedPng(root, styleImagePath);
  const originalStyle = {
    id: "unified-light-3d",
    version: sourceStyle.version,
    type: "unified-style-description",
    name: sourceStyle.name,
    status: "experimental",
    parameterRange: { styleProperties: Object.keys(sourceStyle), palette: "separate explicit input" },
    approvalStatus: "pending",
    themeAllowance: { paletteIndependent: true, production: "not a runtime theme" },
    technicalConclusion: "Style source JSON and illustration screenshot are hash-addressed; illustration image is not included by default.",
    visualConclusion: "Exploratory style example; user aesthetic approval is not inferred.",
    productionMapping: {
      status: "none",
      directAdapter: false,
      candidateRuntimeIds: [],
      gap: "Style description and screenshot are not a registered V1 runtime theme; the blue example must not be mistaken for a neutral default.",
    },
    default: false,
    source: sourceRef(root, `${lib}reference-input-v2/style-description.json`, sourceStyle),
    screenshot: {
      path: styleImagePath,
      sha256: styleImage.sha256,
      width: styleImage.width,
      height: styleImage.height,
    },
    descriptor: sourceStyle,
    reasonNotDefault: "示意图含蓝色主体和配色；只能在明确风格探索中选择，不能充当默认黑灰白基线。",
  };
  const neutralStyleEntry = {
    id: neutralStyle.id,
    version: neutralStyle.version,
    type: neutralStyle.type,
    name: neutralStyle.name,
    status: "available",
    parameterRange: { styleProperties: Object.keys(neutralStyle), palette: "black/gray/white only unless a separate palette is explicitly selected" },
    approvalStatus: "user-specified-default-baseline",
    themeAllowance: { palette: "neutral grayscale only by default", colorPaletteImage: "none" },
    technicalConclusion: "Local descriptor is versioned and hashed independently of optional color-palette sources.",
    visualConclusion: "Default instruction from the user; the descriptor is not an approved production template.",
    productionMapping: {
      status: "none",
      directAdapter: false,
      candidateRuntimeIds: [],
      gap: "This offline descriptor is not registered in the V1 runtime theme directory or application settings.",
    },
    default: true,
    source: sourceRef(root, "html_engine/visual/catalog/neutral-style.json", neutralStyle),
    sourceStyle: sourceRef(root, `${lib}reference-input-v2/style-description.json`, sourceStyle),
    screenshot: null,
    descriptor: neutralStyle,
  };

  const sampleEntries = [];
  if (sampleVerification.status !== "passed" || !Array.isArray(sampleVerification.pages))
    throw new CatalogError("SAMPLE_VERIFICATION_SOURCE_INVALID");
  for (const page of sampleVerification.pages) {
    const sampleId = page.id === "course-everyday" ? "sample:course-everyday" :
      page.id === "paper-plane" ? "sample:paper-plane" : `sample:${page.id}`;
    const screenshots = [];
    for (const palette of page.palettes || []) {
      const relative = `${lib}samples/output/${palette.image.filename}`;
      const image = verifiedPng(root, relative, palette.image);
      screenshots.push({
        paletteId: palette.id,
        name: palette.name,
        path: relative,
        sha256: image.sha256,
        width: image.width,
        height: image.height,
      });
    }
    const isExperimental = page.id === "paper-plane";
    const sampleSourceRecord = Object.fromEntries(
      ["id", "source", "sourceStatus", "titleCharacters", "longestBodyCharacters", "assetCount", "componentIds", "instanceIds"]
        .filter((key) => page[key] !== undefined)
        .map((key) => [key, page[key]]),
    );
    sampleEntries.push({
      id: sampleId,
      version: standardPages.version,
      catalogVersion: standardPages.version,
      type: "sample-page",
      category: "review-sample",
      name: page.id === "course-everyday" ? "水的状态变化（待审样页）" : "纸飞机主题复用（实验演示）",
      purpose:
        page.id === "course-everyday"
          ? "静态内容样页；B 线用户视觉审阅待完成。"
          : "E1 设计探索复用与容量测试；不是已批准 production template。",
      parameterRange: { interface: "fixed static page", paletteVariants: screenshots.map((item) => item.paletteId) },
      status: isExperimental ? "experimental" : "pending-review",
      implementationStatus: "static-sample-only",
      approvalStatus: sampleVerification.userVisualApproval || "pending",
      themeAllowance: {
        paletteVariants: screenshots.map((item) => item.paletteId),
        production: "static sample only; palette variant must be explicit; not a production theme mapping",
      },
      technicalConclusion: "B sample verification records offline rendering, page bounds, local assets, font loading, and palette-specific PNG hashes.",
      visualConclusion: "User visual approval remains pending; the paper-plane page is an E1 exploration/capacity sample, not a production template.",
      referenceAttachmentEligible: true,
      source: sourceRef(root, `${lib}samples/output/verification.json`, sampleSourceRecord),
      screenshots,
      sampleMetrics: {
        titleCharacters: page.titleCharacters,
        longestBodyCharacters: page.longestBodyCharacters,
        independentAssetCount: page.assetCount,
      },
      productionMapping: {
        status: "none",
        directAdapter: false,
        candidateRuntimeIds: [],
        gap: "静态样页不是 production template；任何映射须另定义、接线并经过工程与用户视觉审阅。",
      },
      tags: `${sampleId} ${page.id} ${page.source || ""}`,
    });
  }

  const effectsRegistryPath = "html_engine/visual/effects/registry.json";
  const effectsRegistry = readJson(root, effectsRegistryPath);
  const productionCapabilities = [
    ...collectRuntimeNodes(root, schemaPath, runtimeSchema),
    ...collectRuntimeFiles(
      root,
      "html_engine/visual/layouts",
      "runtime-layout",
      "production-layout",
      (raw) => ({
        canvas: raw.canvas,
        slotCount: Object.keys(raw.slots || {}).length,
        slots: Object.keys(raw.slots || {}),
        slotFieldConstraints: "coordinates 0..1600; maxLines 1..6; align left|center|right; z 0..20 (schema bounds)",
      }),
    ),
    ...collectRuntimeFiles(
      root,
      "html_engine/visual/templates",
      "runtime-template",
      "production-template",
      (raw) => ({ structure: raw.structure, layoutRef: raw.layoutRef, slots: raw.slots }),
    ),
    ...collectRuntimeFiles(
      root,
      "html_engine/visual/themes",
      "runtime-theme",
      "production-theme",
      (raw) => ({
        font: raw.font,
        colorRoles: Object.keys(raw.colors || {}),
        textRoles: Object.keys(raw.text || {}),
        compatibleLayouts: raw.compatibleLayouts,
        shapeTokens: raw.shapes,
        gradients: raw.gradients || null,
      }),
    ),
    ...effectsRegistry.effects.map((effect) => ({
      id: `runtime-effect:${effect.id}`,
      version: effectsRegistry.version,
      type: "runtime-effect",
      category: "production-effect",
      name: effect.id,
      purpose: effect.purpose,
      parameterRange: { declaredParameters: effect.params, backend: effect.backend },
      status: "available",
      implementationStatus: "registered-runtime",
      approvalStatus: "not-inferred-from-registration",
      themeAllowance: {
        source: "runtime theme values consumed only through the listed registered effect",
        colors: "bounded by runtime theme and effect implementation; no reference palette auto-mapping",
      },
      technicalConclusion: "Effect ID and parameter description are read from the live V1 effects registry.",
      visualConclusion: "No user aesthetic approval is inferred from effect registration.",
      referenceAttachmentEligible: false,
      source: sourceRef(root, effectsRegistryPath, effect),
      screenshot: null,
      productionMapping: {
        status: "registered",
        directAdapter: true,
        candidateRuntimeIds: [`runtime-effect:${effect.id}`],
        gap: "该条目本身是运行时效果注册项；不是一张截图或视觉批准。",
      },
    })),
  ];

  for (const entry of productionCapabilities) {
    if (!entry.source?.fileSha256 || !entry.source?.recordSha256)
      throw new CatalogError("PRODUCTION_SOURCE_HASH_MISSING", entry.id);
  }
  const allIds = [...references, ...sampleEntries, ...productionCapabilities].map((item) => item.id);
  if (new Set(allIds).size !== allIds.length)
    throw new CatalogError("DUPLICATE_CATALOG_ID");

  for (const relative of [
    ...sourcePaths,
    ...standardManifest.files.map((item) => `${lib}standard/${item.filename}`),
    ...paletteEntries.map((item) => item.screenshot.path),
    styleImagePath,
    ...sampleEntries.flatMap((item) => item.screenshots.map((image) => image.path)),
    ...productionCapabilities.map((item) => item.source.path),
  ]) {
    if (!sourcePaths.includes(relative)) sourcePaths.push(relative);
  }
  const generatedFrom = [...new Set(sourcePaths)]
    .sort()
    .map((source) => ({ path: source, sha256: fileHash(root, source) }));
  const historicalIssues = historicalSource.items.map((issue) => ({
    ...issue,
    preservedSourceHashes: issue.preserveSourcePaths.map((source) => ({
      path: source,
      sha256: fileHash(root, source),
    })),
  }));

  const taxonomy = {
    standardLibraryVersion: standardPages.version,
    counts: {
      referencePages: pages.length,
      baseComponents: references.filter((item) => item.type === "base-component" || item.type === "fixed-structure-example").length,
      presentationVariants: references.filter((item) => item.type === "presentation-variant").length,
      staticEffects: references.filter((item) => item.type === "static-effect").length,
      compositions: references.filter((item) => item.type === "composition-example").length,
      fonts: references.filter((item) => item.type === "font").length,
      palettes: paletteEntries.length,
      pendingOrExperimentalSamples: sampleEntries.length,
      runtimeNodeTypes: productionCapabilities.filter((item) => item.type === "runtime-node").length,
      runtimeEffects: productionCapabilities.filter((item) => item.type === "runtime-effect").length,
      runtimeLayouts: productionCapabilities.filter((item) => item.type === "runtime-layout").length,
      runtimeTemplates: productionCapabilities.filter((item) => item.type === "runtime-template").length,
      runtimeThemes: productionCapabilities.filter((item) => item.type === "runtime-theme").length,
    },
    sourceOfCounts: "counted from standard-pages.json, components.json, components-extensions.json, presentation-variants.json, effects.json, static-catalog.json, and live V1 runtime sources",
  };

  const catalog = {
    format: "hps.visual.reference-catalog",
    version: FORMAT_VERSION,
    generatedAtPolicy: "deterministic; no wall-clock field",
    scope: "offline visual reference catalog and request-package assembler; not a production API or renderer",
    taxonomy,
    sourceVersions: {
      standardLibrary: standardPages.version,
      baseComponents: components.version,
      fixedStructureExamples: extensions.version,
      presentationVariants: variants.version,
      staticEffects: effects.version,
      compositions: compositions.version,
      palettes: palettes.version,
      runtimeSchema: runtimeSchema.$defs?.version?.const || "unknown",
      runtimeEffects: effectsRegistry.version,
    },
    sourceManifest: generatedFrom,
    referencePages: pages,
    references: references.sort((a, b) => a.id.localeCompare(b.id)),
    palettes: paletteEntries,
    styles: [neutralStyleEntry, originalStyle],
    samplePages: sampleEntries,
    historicalIssues,
    productionCapabilities: productionCapabilities.sort((a, b) => a.id.localeCompare(b.id)),
    generation: {
      providerRequestCreated: false,
      providerCallMade: false,
      note: "离线装配参考包；不调用生图供应商，不代表真实生图请求已接入。",
    },
  };
  catalog.snapshotSha256 = stableHash(catalog);
  return { catalog, sources: { standardManifest, standardPages, palettes, sourceStyle, neutralStyle } };
}

function cacheIdentity({ request, selectedReferences, selectedPalette, selectedStyle, attachments }) {
  const chosenPaletteId = selectedPalette?.id || null;
  return stableHash({
    format: "hps.catalog.assembler-cache-key",
    version: "1",
    task: request.task,
    contentSha256: stableHash(request.content),
    mode: request.mode || "standard",
    referenceOrder: selectedReferences.map((entry) => entry.id),
    references: selectedReferences
      .map((entry) => ({
        id: entry.id,
        version: entry.version,
        catalogVersion: entry.catalogVersion || null,
        sourceRecordSha256: entry.source.recordSha256,
        screenshots: (entry.screenshots || [entry.screenshot])
          .filter(Boolean)
          .filter((shot) => entry.type !== "sample-page" || shot.paletteId === chosenPaletteId)
          .map((shot) => ({
            paletteId: shot.paletteId || null,
            sha256: shot.sha256,
          }))
          .sort((a, b) => `${a.paletteId}:${a.sha256}`.localeCompare(`${b.paletteId}:${b.sha256}`)),
      }))
      .sort((a, b) => a.id.localeCompare(b.id)),
    palette: selectedPalette
      ? { id: selectedPalette.id, version: selectedPalette.version, sourceRecordSha256: selectedPalette.source.recordSha256, screenshotSha256: selectedPalette.screenshot.sha256 }
      : { id: "neutral", version: "1.0.0", noColorImage: true },
    style: {
      id: selectedStyle.id,
      version: selectedStyle.version,
      sourceRecordSha256: selectedStyle.source.recordSha256,
      sourceStyleRecordSha256: selectedStyle.sourceStyle?.recordSha256 || null,
      screenshotSha256: selectedStyle.screenshot?.sha256 || null,
    },
    reasons: request.selectionReasons || {},
    attachments: attachments
      .map((item) => ({ path: item.packagePath, sha256: item.sha256 }))
      .sort((a, b) => a.path.localeCompare(b.path)),
  });
}

function suggestReferencePages(task, pages) {
  const text = task.toLocaleLowerCase();
  const rules = [
    { pageId: "component-01", terms: ["文字", "正文", "标题", "副标题", "讲解", "术语", "文本", "text", "title"] },
    { pageId: "component-02", terms: ["箭头", "连接", "方向", "因果", "变化", "过程", "流向", "路径", "arrow", "flow"] },
    { pageId: "component-03", terms: ["卡片", "分组", "概念", "对比", "比较", "说明", "容器", "card", "compare"] },
    { pageId: "component-04", terms: ["形状", "几何", "节点", "对象", "shape", "geometry"] },
    { pageId: "component-05", terms: ["标注", "注释", "圈注", "引线", "label", "annotation"] },
    { pageId: "component-06", terms: ["关系", "分支", "循环", "往返", "相反方向", "方向相反", "层级", "组织", "关联", "relationship"] },
    { pageId: "component-07", terms: ["数据", "数量", "比例", "数值", "时间线", "阶段", "chart", "data"] },
    { pageId: "variant-08", terms: ["标题变体", "标题样式", "标题呈现"] },
    { pageId: "variant-09", terms: ["重点", "强调", "解释样式"] },
    { pageId: "variant-10", terms: ["容器层次", "卡片变体"] },
    { pageId: "variant-11", terms: ["标签变体", "编号样式"] },
    { pageId: "effect-12", terms: ["渐变"] },
    { pageId: "effect-13", terms: ["阴影", "投影"] },
    { pageId: "effect-14", terms: ["描边", "边框"] },
    { pageId: "effect-15", terms: ["透明", "玻璃", "高光"] },
    { pageId: "effect-16", terms: ["裁切", "遮罩"] },
    { pageId: "effect-17", terms: ["纹理", "网格", "点阵"] },
    { pageId: "effect-18", terms: ["文字效果", "文字渐变", "文字投影"] },
    { pageId: "composition-19", terms: ["排版", "版式"] },
    { pageId: "composition-20", terms: ["关系图", "结构图"] },
    { pageId: "composition-21", terms: ["效果组合", "效果用法"] },
    { pageId: "composition-22", terms: ["图片融合", "插画融合", "主体图片"] },
    { pageId: "fonts", terms: ["字体", "字形", "font"] },
  ];
  const matches = rules
    .filter((rule) => rule.terms.some((term) => text.includes(term.toLocaleLowerCase())))
    .map((rule) => rule.pageId)
    .filter((id) => pages.some((page) => page.id === id || page.id === `page:${id}`));
  return [...new Set(matches)].slice(0, 3);
}

function validateContent(content) {
  if (!content || typeof content !== "object" || Array.isArray(content))
    throw new CatalogError("EXACT_CONTENT_REQUIRED");
  if (typeof content.title !== "string" || !content.title.trim())
    throw new CatalogError("CONTENT_TITLE_REQUIRED");
  if (
    !Array.isArray(content.exactText) ||
    !content.exactText.length ||
    content.exactText.some((item) => typeof item !== "string" || !item.trim())
  )
    throw new CatalogError("CONTENT_EXACT_TEXT_REQUIRED");
  if (
    content.relationships !== undefined &&
    (!Array.isArray(content.relationships) ||
      content.relationships.some(
        (item) =>
          !item ||
          typeof item.from !== "string" ||
          typeof item.to !== "string" ||
          typeof item.relation !== "string",
      ))
  )
    throw new CatalogError("CONTENT_RELATIONSHIPS_INVALID");
}

function createGuidance({ style, palette, request }) {
  return {
    format: "hps.visual.reference-guidance",
    version: "1.0.0",
    style: style.descriptor,
    palette: palette
      ? { id: palette.id, name: palette.name, roles: palette.roles, source: palette.source }
      : {
          id: "neutral",
          name: "黑灰白中性默认",
          roles: {
            background: "#FFFFFF",
            ink: "#222222",
            body: "#555555",
            muted: "#888888",
            surface: "#F4F4F4",
            line: "#DDDDDD",
          },
          source: "user-specified default; no independent color palette attached",
        },
    referenceHandling: {
      classificationImagesAreVisualOnly: true,
      doNotCopySampleTextOrNumbers: true,
      doNotCopyIdsOrLabels: true,
      doNotTreatReferenceGeometryAsProductionTemplate: true,
      exactTextAndRelationshipsSource: "content.json",
    },
    selectionRationale: {
      references: request.selectionReasons || {},
      palette: palette
        ? `Explicit palette selection: ${palette.id}.`
        : "No palette selected; use the black, gray, and white baseline.",
      style: `Style descriptor selected: ${style.id}.`,
    },
  };
}

function inspectOwnedPackage(outDir, { allowLegacyManifest = false } = {}) {
  const manifestPath = path.join(outDir, "manifest.json");
  if (!fs.existsSync(manifestPath)) return null;
  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  } catch {
    return null;
  }
  if (
    manifest.format !== "hps.visual.reference-request-package" ||
    manifest.createdBy !== "offline-catalog-assembler" ||
    !Array.isArray(manifest.files) ||
    (!allowLegacyManifest && typeof manifest.manifestSha256 !== "string")
  )
    return null;
  if (manifest.manifestSha256) {
    const { manifestSha256, ...manifestBody } = manifest;
    if (stableHash(manifestBody) !== manifestSha256) return null;
  }
  const expectedFiles = new Set(["manifest.json"]);
  for (const item of manifest.files) {
    if (typeof item.path !== "string" || path.isAbsolute(item.path)) return null;
    const file = path.resolve(outDir, item.path);
    if (
      !file.startsWith(`${path.resolve(outDir)}${path.sep}`) ||
      !fs.existsSync(file) ||
      fs.lstatSync(file).isSymbolicLink() ||
      !fs.lstatSync(file).isFile()
    )
      return null;
    expectedFiles.add(item.path.replaceAll("\\", "/"));
    if (sha256(fs.readFileSync(file)) !== item.sha256) return null;
  }
  const actualFiles = new Set();
  const visit = (directory, prefix = "") => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
      const absolute = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) return false;
      if (entry.isDirectory()) {
        if (!visit(absolute, relative)) return false;
      } else if (entry.isFile()) {
        actualFiles.add(relative.replaceAll("\\", "/"));
      } else {
        return false;
      }
    }
    return true;
  };
  if (!visit(outDir) || actualFiles.size !== expectedFiles.size) return null;
  for (const file of expectedFiles) if (!actualFiles.has(file)) return null;
  return { manifest };
}

function validatePackageCache(outDir, cacheKey) {
  const owned = inspectOwnedPackage(outDir);
  return Boolean(owned && owned.manifest.cacheKey === cacheKey);
}

function uniqueAttachments(selectedReferences, palette, style) {
  const attachments = new Map();
  const add = (sourcePath, expected, packagePath, role) => {
    const fileName = path.basename(sourcePath);
    const image = verifiedPng(expected.root, sourcePath, expected);
    const output = packagePath || `attachments/${role}/${fileName}`;
    const existing = attachments.get(output);
    if (existing && existing.sha256 !== image.sha256)
      throw new CatalogError("ATTACHMENT_PATH_COLLISION", output);
    attachments.set(output, {
      packagePath: output,
      sourcePath,
      sha256: image.sha256,
      width: image.width,
      height: image.height,
      role,
      bytes: image.bytes,
    });
  };
  for (const entry of selectedReferences) {
    const shots = entry.screenshots || (entry.screenshot ? [entry.screenshot] : []);
    let chosen = shots;
    if (entry.type === "sample-page") {
      const paletteId = palette?.id;
      if (!paletteId || paletteId === "neutral")
        throw new CatalogError("SAMPLE_REQUIRES_EXPLICIT_PALETTE", entry.id);
      chosen = shots.filter((shot) => shot.paletteId === paletteId);
      if (!chosen.length) throw new CatalogError("SAMPLE_PALETTE_VARIANT_MISSING", entry.id);
    }
    for (const shot of chosen) {
      const role = entry.type === "sample-page" ? "samples" : "classification";
      const pkg = `attachments/${role}/${path.basename(shot.path)}`;
      add(shot.path, { root: entry.__root, sha256: shot.sha256, width: shot.width, height: shot.height }, pkg, role);
    }
  }
  if (palette) {
    add(
      palette.screenshot.path,
      { root: palette.__root, sha256: palette.screenshot.sha256, width: palette.screenshot.width, height: palette.screenshot.height },
      `attachments/palettes/palette-${palette.id}.png`,
      "palette",
    );
  }
  if (style.screenshot) {
    add(
      style.screenshot.path,
      { root: style.__root, sha256: style.screenshot.sha256, width: style.screenshot.width, height: style.screenshot.height },
      `attachments/styles/style-${style.id}.png`,
      "style",
    );
  }
  return [...attachments.values()].sort((a, b) => a.packagePath.localeCompare(b.packagePath));
}

function assembleRequest({ request, root = path.resolve(__dirname, "../.."), outDir, replaceExisting = false }) {
  if (!request || typeof request !== "object") throw new CatalogError("REQUEST_REQUIRED");
  if (typeof request.task !== "string" || !request.task.trim())
    throw new CatalogError("TASK_REQUIRED");
  validateContent(request.content);
  const mode = request.mode || "standard";
  if (!["standard", "review", "exploration"].includes(mode))
    throw new CatalogError("UNKNOWN_ASSEMBLY_MODE", mode);

  const { catalog } = buildCatalog({ root });
  let ids = request.referenceIds;
  let normalizedRequest = { ...request, mode };
  if (ids === undefined && Array.isArray(request.referencePages)) {
    ids = request.referencePages.map((pageId) => `page:${pageId}`);
  }
  if (ids === undefined) {
    const inferredPages = suggestReferencePages(request.task, catalog.referencePages);
    if (!inferredPages.length)
      throw new CatalogError("NO_RELEVANT_REFERENCE_MATCH", "supply referenceIds or referencePages");
    ids = inferredPages.map((pageId) => `page:${pageId}`);
    normalizedRequest = {
      ...normalizedRequest,
      selectionReasons: {
        ...(request.selectionReasons || {}),
        ...Object.fromEntries(
          ids.map((id) => [id, "由离线任务关键词规则匹配的分类页建议；请在真实视觉任务前确认相关性。"]),
        ),
      },
    };
  }
  if (!Array.isArray(ids) || ids.length === 0)
    throw new CatalogError("REFERENCE_IDS_REQUIRED");
  if (new Set(ids).size !== ids.length)
    throw new CatalogError("DUPLICATE_REFERENCE_ID");
  if (ids.length > 12) throw new CatalogError("TOO_MANY_REFERENCE_IDS");
  const referenceMap = new Map(
    [...catalog.referencePages, ...catalog.references, ...catalog.samplePages].map((entry) => [entry.id, entry]),
  );
  const runtimeMap = new Map(catalog.productionCapabilities.map((entry) => [entry.id, entry]));
  const selectedReferences = ids.map((id) => {
    const entry = referenceMap.get(id);
    if (!entry) {
      if (runtimeMap.has(id)) throw new CatalogError("UNSUPPORTED_PRODUCTION_REFERENCE", id);
      throw new CatalogError("UNKNOWN_REFERENCE_ID", id);
    }
    if (!entry.referenceAttachmentEligible)
      throw new CatalogError("UNSUPPORTED_PRODUCTION_REFERENCE", id);
    if (entry.status === "experimental") {
      if (mode !== "exploration" || request.allowUnreviewedReferences !== true)
        throw new CatalogError("EXPERIMENTAL_REFERENCE_REQUIRES_OPT_IN", id);
    }
    if (entry.status === "pending-review") {
      if (mode !== "review" || request.allowUnreviewedReferences !== true)
        throw new CatalogError("PENDING_REFERENCE_REQUIRES_REVIEW_MODE", id);
    }
    return { ...entry, __root: root };
  });

  const requestedPalette = request.paletteId;
  let palette = null;
  if (requestedPalette && requestedPalette !== "neutral") {
    if (!["exploration", "review"].includes(mode))
      throw new CatalogError("PALETTE_SELECTION_REQUIRES_EXPLORATION", requestedPalette);
    palette = catalog.palettes.find((item) => item.id === requestedPalette);
    if (!palette) throw new CatalogError("UNKNOWN_PALETTE_ID", requestedPalette);
    palette = { ...palette, __root: root };
  }
  const styleId = request.styleId || "neutral-baseline";
  const style = catalog.styles.find((item) => item.id === styleId);
  if (!style) throw new CatalogError("UNKNOWN_STYLE_ID", styleId);
  if (style.status === "experimental") {
    if (mode !== "exploration" || request.allowUnreviewedReferences !== true)
      throw new CatalogError("EXPERIMENTAL_STYLE_REQUIRES_OPT_IN", styleId);
  }
  const selectedStyle = { ...style, __root: root };

  const attachments = uniqueAttachments(selectedReferences, palette, selectedStyle);
  const key = cacheIdentity({
    request: normalizedRequest,
    selectedReferences,
    selectedPalette: palette,
    selectedStyle,
    attachments,
  });
  if (!outDir) throw new CatalogError("OUTPUT_DIRECTORY_REQUIRED");
  const output = path.resolve(outDir);
  if (output === path.resolve(root))
    throw new CatalogError("OUTPUT_MUST_NOT_BE_WORKSPACE_ROOT", output);
  if (validatePackageCache(output, key))
    return { status: "cache-hit", cacheKey: key, outputDir: output, fileCount: JSON.parse(fs.readFileSync(path.join(output, "manifest.json"), "utf8")).files.length + 1 };
  let ownedPreviousPackage = null;
  if (fs.existsSync(output)) {
    if (fs.readdirSync(output).length) {
      ownedPreviousPackage = inspectOwnedPackage(output, { allowLegacyManifest: true });
      if (!replaceExisting || !ownedPreviousPackage)
        throw new CatalogError("OUTPUT_DIRECTORY_NOT_EMPTY_OR_NOT_OWNED", output);
    }
  }

  const guidance = createGuidance({ style: selectedStyle, palette, request: normalizedRequest });
  const contentBytes = Buffer.from(`${JSON.stringify(request.content, null, 2)}\n`, "utf8");
  const guidanceBytes = Buffer.from(`${JSON.stringify(guidance, null, 2)}\n`, "utf8");
  const noProviderBytes = Buffer.from(
    "# 离线参考请求包\n\n本目录只整理视觉参考与独立内容数据。没有调用模型或图像供应商，也没有创建真实生图请求。分类图、配色图和风格图只提供视觉线索；不要复制其中的样例文字、数字、编号、标签或布局身份。唯一准确文字与关系来源是 `content.json`。\n",
    "utf8",
  );
  const stageParent = path.dirname(output);
  fs.mkdirSync(stageParent, { recursive: true });
  const stage = fs.mkdtempSync(path.join(stageParent, ".catalog-package-"));
  try {
    fs.mkdirSync(stage, { recursive: true });
    const packaged = [
      { path: "content.json", bytes: contentBytes },
      { path: "visual-guidance.json", bytes: guidanceBytes },
      { path: "NOT-A-MODEL-REQUEST.md", bytes: noProviderBytes },
      ...attachments.map((item) => ({ path: item.packagePath, bytes: item.bytes })),
    ];
    for (const file of packaged) {
      const destination = path.join(stage, file.path);
      fs.mkdirSync(path.dirname(destination), { recursive: true });
      fs.writeFileSync(destination, file.bytes);
    }
    const selectedManifest = selectedReferences.map((entry) => ({
      id: entry.id,
      version: entry.version,
      type: entry.type,
      name: entry.name,
      category: entry.category,
      status: entry.status,
      pageId: entry.pageId || null,
      source: entry.source,
      screenshots: (entry.screenshots || [entry.screenshot])
        .filter(Boolean)
        .filter((shot) => entry.type !== "sample-page" || shot.paletteId === palette?.id)
        .map((shot) => ({
        packagePath: attachments.find((asset) => asset.sourcePath === shot.path)?.packagePath || null,
        sourcePath: shot.path,
        sha256: shot.sha256,
        paletteId: shot.paletteId || null,
        })),
      rationale: normalizedRequest.selectionReasons?.[entry.id] || `显式选择了目录 ID ${entry.id}。`,
      productionMapping: entry.productionMapping,
    }));
    const files = packaged.map((file) => ({
      path: file.path,
      sha256: sha256(file.bytes),
      size: file.bytes.length,
    }));
    const manifest = {
      format: "hps.visual.reference-request-package",
      version: "1.0.0",
      mode,
      createdBy: "offline-catalog-assembler",
      catalogVersion: catalog.version,
      catalogSnapshotSha256: catalog.snapshotSha256,
      cacheKey: key,
      exactContent: { path: "content.json", sha256: sha256(contentBytes) },
      visualGuidance: { path: "visual-guidance.json", sha256: sha256(guidanceBytes) },
      selectionRationale: {
        task: request.task,
        references: selectedManifest.map(({ id, rationale }) => ({ id, rationale })),
        palette: palette
          ? { id: palette.id, rationale: `显式选择配色 ${palette.id}；独立附加，不改变组件身份。` }
          : { id: "neutral", rationale: "未选择配色，按黑灰白中性基础标准组包。" },
        style: { id: selectedStyle.id, rationale: `使用风格描述 ${selectedStyle.id}。` },
      },
      palette: palette ? { id: palette.id, version: palette.version, source: palette.source } : { id: "neutral", version: "1.0.0" },
      style: { id: selectedStyle.id, version: selectedStyle.version, source: selectedStyle.source },
      selectedReferences: selectedManifest,
      attachments: attachments.map(({ packagePath, sourcePath, sha256: digest, width, height, role }) => ({
        path: packagePath,
        sourcePath,
        role,
        sha256: digest,
        width,
        height,
      })),
      provider: { requestCreated: false, callMade: false },
      files,
    };
    manifest.manifestSha256 = stableHash(manifest);
    fs.writeFileSync(path.join(stage, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    if (ownedPreviousPackage) {
      const backupSeed = fs.mkdtempSync(path.join(stageParent, ".catalog-backup-"));
      fs.rmdirSync(backupSeed);
      fs.renameSync(output, backupSeed);
      try {
        fs.renameSync(stage, output);
      } catch (error) {
        fs.renameSync(backupSeed, output);
        throw error;
      }
      fs.rmSync(backupSeed, { recursive: true, force: true });
    } else {
      if (fs.existsSync(output) && !fs.readdirSync(output).length) fs.rmdirSync(output);
      fs.renameSync(stage, output);
    }
    return { status: "assembled", cacheKey: key, outputDir: output, fileCount: files.length + 1, attachments: manifest.attachments.length };
  } catch (error) {
    if (fs.existsSync(stage)) fs.rmSync(stage, { recursive: true, force: true });
    throw error;
  }
}

module.exports = {
  CatalogError,
  DOC_ASSET_PATH,
  FORMAT_VERSION,
  assembleRequest,
  buildCatalog,
  cacheIdentity,
  fileHash,
  inspectOwnedPackage,
  pngInfo,
  safeResolve,
  sha256,
  suggestReferencePages,
  stableHash,
  stableStringify,
  verifiedPng,
};
