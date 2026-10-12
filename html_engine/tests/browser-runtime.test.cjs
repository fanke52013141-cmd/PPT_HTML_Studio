const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { resolveBrowser } = require("../tools/browser-runtime.cjs");
test("explicit invalid browser does not silently switch", () => {
  assert.throws(() => resolveBrowser({ executablePath: () => "bundled" }, { HPS_CHROME: "missing" }, () => false), /OVERRIDE/);
});
test("missing bundled browser uses installed Edge from environment roots", () => {
  const expected = path.join("local-root", "Microsoft", "Edge", "Application", "msedge.exe");
  assert.equal(resolveBrowser({ executablePath: () => "missing" }, { LOCALAPPDATA: "local-root" }, p => p === expected), expected);
});
test("bundled browser has precedence without override", () => {
  assert.equal(resolveBrowser({ executablePath: () => "bundled" }, {}, p => p === "bundled"), "bundled");
});
