const fs = require("node:fs");
const path = require("node:path");
const { CatalogError, assembleRequest } = require("./catalog-lib.cjs");

const ROOT = path.resolve(__dirname, "../..");

function readArgument(name) {
  const index = process.argv.indexOf(name);
  return index < 0 ? null : process.argv[index + 1] || null;
}

function main() {
  const inputPath = readArgument("--input");
  const outPath = readArgument("--out");
  if (!inputPath || !outPath) throw new CatalogError("USAGE", "--input request.json --out output-directory");
  const request = JSON.parse(fs.readFileSync(path.resolve(inputPath), "utf8"));
  const output = path.resolve(ROOT, outPath);
  const result = assembleRequest({
    request,
    root: ROOT,
    outDir: output,
    replaceExisting: process.argv.includes("--replace"),
  });
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(JSON.stringify({ error: error.code || "ASSEMBLY_FAILED", detail: error.message }, null, 2));
    process.exitCode = 1;
  }
}

module.exports = { main };
