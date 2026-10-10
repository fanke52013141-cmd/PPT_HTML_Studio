const path = require("node:path");
const { CatalogError, buildCatalog, suggestReferencePages } = require("./catalog-lib.cjs");

const ROOT = path.resolve(__dirname, "../..");

function argument(name) {
  const index = process.argv.indexOf(name);
  return index < 0 ? null : process.argv[index + 1] || null;
}

function queryCatalog({ id, query, category, status, task } = {}) {
  const { catalog } = buildCatalog({ root: ROOT });
  const all = [
    ...catalog.referencePages,
    ...catalog.references,
    ...catalog.palettes,
    ...catalog.styles,
    ...catalog.samplePages,
    ...catalog.productionCapabilities,
  ];
  if (id) {
    const result = all.find((item) => item.id === id);
    if (!result) throw new CatalogError("UNKNOWN_CATALOG_ID", id);
    return { catalogVersion: catalog.version, snapshotSha256: catalog.snapshotSha256, results: [result] };
  }
  const search = (query || "").toLocaleLowerCase();
  let results = all.filter((item) => {
    const searchable = [item.id, item.name, item.type, item.category, item.purpose, item.tags]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!search || searchable.includes(search)) &&
      (!category || item.category === category) &&
      (!status || item.status === status)
    );
  });
  const inferredPageIds = task ? suggestReferencePages(task, catalog.referencePages) : [];
  const suggestedPages = task
    ? inferredPageIds.map((pageId) => {
        const page = catalog.referencePages.find((item) => item.id === pageId || item.id === `page:${pageId}`);
        return {
          id: page.id,
          title: page.name,
          screenshot: page.screenshot,
          reason: "offline keyword match; verify relevance before attaching",
        };
      })
    : [];
  if (task && !id && !query && !category && !status) {
    const matchingPageIds = new Set(inferredPageIds.map((pageId) => `page:${pageId}`));
    results = all.filter(
      (item) =>
        matchingPageIds.has(item.id) ||
        matchingPageIds.has(`page:${item.pageId}`),
    );
  } else if (!id && !query && !category && !status && !task) {
    results = [];
  }
  return {
    catalogVersion: catalog.version,
    snapshotSha256: catalog.snapshotSha256,
    query: query || null,
    category: category || null,
    status: status || null,
    task: task || null,
    suggestedPages,
    resultCount: results.length,
    inventoryCount: all.length,
    results,
  };
}

function main() {
  const args = {
    id: argument("--id"),
    query: argument("--query"),
    category: argument("--category"),
    status: argument("--status"),
    task: argument("--task"),
  };
  console.log(JSON.stringify(queryCatalog(args), null, 2));
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(JSON.stringify({ error: error.code || "QUERY_FAILED", detail: error.message }, null, 2));
    process.exitCode = 1;
  }
}

module.exports = { queryCatalog };
